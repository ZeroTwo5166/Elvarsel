# Elvarsel: design and checklist

## What it is

An investigation into whether a learned model can predict every hourly day-ahead electricity price for a delivery day in the DK2 bidding zone (Eastern Denmark) better than simple historical baselines, using only information that was available before the day-ahead auction results were published.

It is a data-science project, not a platform. The deliverable is a reproducible experiment, a leakage audit, a result on an untouched test period, and a short report. A dashboard is optional.

The project is framed as an investigation, and a result where the model loses to the baselines is acceptable. A sound experiment with a negative result is worth more than a headline number from a questionable split.

DK2 is the Nordic-synchronised half of Denmark: Zealand, Lolland-Falster, Bornholm and the islands, including Copenhagen. It has its own hourly price on the day-ahead market, distinct from DK1 (Jutland and Funen), which is on the continental grid.

## Scope

In:

- DK2 hourly spot prices, as many years as Energi Data Service holds, down to a final held-out test period.
- Three baselines, two learned models, chronological evaluation.
- Lagged prices and calendar features. External features (wind/solar/consumption forecasts, weather) only where a historical *forecast* series with a known publication time exists, never actuals.
- A reproducible pipeline: fetch, clean, features, train, evaluate. From a clean clone: lint and tests, then the offline fixture pipeline as listed in the README. `final_run.py` has no `--fixtures` mode.
- Tests on cleaning and feature construction, including daylight-saving days.
- A leakage audit table and a two-page report.

Out, unless everything above is done:

- Weather from DMI.
- A dashboard.
- Spark, unless a measured benchmark says the data needs it.
- Probabilistic forecasts, deep learning, hyperparameter search beyond a small grid.
- DK1 or other zones.

## The forecasting contract

The contract was written down before any code.

**Target.** For delivery day D (a local Danish calendar day), the hourly day-ahead price for DK2 in EUR/MWh for every delivery hour of that day: 24 on an ordinary day, 23 on the spring transition day, 25 on the autumn one. Where the source is 15-minute, the hourly target is the arithmetic mean of the four quarter-hour prices in that delivery hour, and the report and README say so.

**Forecast cutoff.** 12:00 CET/CEST on day D-1. The day-ahead auction for day D closes at 12:00 on D-1 and results are published around 12:45 to 13:00 on D-1. Anything published after 12:00 on D-1 is not allowed.

**What that makes available at the cutoff:**

- All prices for day D-1 and earlier. Day D-1 prices were published on D-2, so they are fully known. A lag of 24 elapsed hours is therefore legitimate.
- Any forecast of wind, solar, consumption or weather for day D that was itself published before 12:00 on D-1.

**What it forbids:**

- Any price for day D.
- Actual (settled, measured) production, consumption or weather for day D or for day D-1 after 12:00. Actuals for D-1 before noon are known at the cutoff, but a feature built from them can easily take in the whole day, so no feature uses actuals from day D-1 or later.
- Any feature whose publication time cannot be established from the source's documentation.

**Leakage audit.** `docs/leakage-audit.md` holds one table row per feature: name, source dataset, what it measures, when it is published relative to the cutoff, and whether it is allowed. A feature not in the table is not in the model.

## Data sources

Dataset names, column names and history depth were checked first (`docs/decisions.md`, 2026-10-23), because Energinet renames datasets and changed the day-ahead market to 15-minute resolution in autumn 2025.

**Energi Data Service (Energinet).** Public REST API, no key, JSON, filterable by price area and date range.

- Day-ahead / spot prices for DK2. Expected columns: a UTC timestamp, a Danish local timestamp, price in DKK and EUR. Before any cleaning, `docs/decisions.md` records whether each part of the history is hourly or 15-minute; whether timestamps mark interval start or end; the earliest date; and the duplicate and gap counts. The cleaning step then produces one row per hourly delivery interval, keyed by UTC interval start, with 15-minute periods averaged into their delivery hour. Hourly and quarter-hour observations are never mixed in one series without this step.
- Forecast datasets for wind and solar production (Energinet publishes day-ahead forecasts at 18:00 on D-1, after the cutoff; see `docs/decisions.md`). A forecast series is usable only if each value carries an issue or publication timestamp, or the dataset's documentation guarantees when it is published. A historical forecast value with no evidence of when it became available is not a valid feature.
- Actual production and consumption: never a feature for day D or D-1 (see contract). Not downloaded.

**DMI Open Data.** Free API key. Observations archive is large and well documented. Historical *forecasts* are the uncertain part; if an archive of past forecasts cannot be obtained, weather stays out of the model and the report says why. Observations are never substituted for forecasts.

**Holidays.** The `holidays` Python package for Danish public holidays.

Raw downloads are stored as CSV under `data/raw/`, gitignored, with the fetch script able to recreate them. `data/clean/` and `data/features/` likewise. A small fixed sample is committed under `tests/fixtures/`: two months of `Elspotprices` (2024-10 and 2025-01) and one day of `DayAheadPrices` (2025-10-26); 2024-10 and 2025-10-26 include the 25-hour autumn day. Every step except `final_run.py` accepts `--fixtures`, which never calls an API and needs no key. Only fetch reads `tests/fixtures/`, copying it into `data/fixtures/`; the later steps read `data/fixtures/`. That is what tests and the clean-clone check use.

## Evaluation design

**Splits, chronological, delivery days kept whole.**

The exact boundaries are fixed in `docs/decisions.md` on the day the price history is inspected, before any model is trained, and never moved. The intended shape, assuming the source goes back far enough:

- Train: complete calendar years up to and including year N-2.
- Validation: calendar year N-1. Used for feature choices and the small hyperparameter grid.
- Test: the latest complete, contiguous period after validation, at least six months, untouched until the final run. One run on test. Its numbers go in the report; nothing is changed after seeing them.

The history is long enough for this shape; the dates are in `docs/decisions.md` (2026-10-29). Expanding-window validation on the train and validation range was planned if time allowed and was not done. No split is random.

**Metrics.** MAE in EUR/MWh is the headline. RMSE alongside it. Both are reported overall, by hour of day, and by month. MAPE is not reported: DK2 has zero and negative prices, which make percentage errors meaningless. `reports/report.md` gives the number of test hours at or below zero.

**Baselines.** All lags are elapsed hours in UTC, not "same local clock hour". Around a DST transition the two differ by one hour; the elapsed-hours definition is the one that is easy to test and reproduce, and `reports/test.md` and the README state it.

1. 24-hour persistence: the price 24 elapsed hours earlier.
2. 168-hour persistence: the price 168 elapsed hours earlier.
3. Mean of 1 and 2.

Where a lagged value does not exist (the first rows of the series, or a gap in the source), the row is excluded from evaluation for every candidate alike, and the count of excluded rows is reported.

**Learned models.**

1. Ridge regression on lagged prices and calendar features. Interpretable; coefficients go in the report.
2. `HistGradientBoostingRegressor` on the same features, then with any verified external forecast features added.

Features for both: price lags at 24, 48, 72, 168, 336 elapsed hours; rolling mean and standard deviation over the 168 elapsed hours ending 24 hours before the target hour (so the window is entirely within day D-1 and earlier); local hour of day, day of week, month, Danish public holiday flag, day-after-holiday flag. Lags and windows are in UTC so DST days don't shift them; hour-of-day is local time, because that is what drives demand. If a same-local-hour statistic is wanted later, it is a separately named feature with its own audit row. Tests prove that every window ends before the cutoff and never includes the target hour or anything after it.

**Error analysis.** During development, on validation only: error by hour and month; the 20 worst days; error at price spikes and at or below zero. After the single test run, the same analysis on test is diagnostic and goes in the report; nothing is tuned afterwards. This section is the heart of the report.

**Extreme-price diagnostic.** One small extra table: MAE and RMSE for hours above a high-price threshold and for hours at or below zero. The threshold is the 95th percentile of the training period, written into `decisions.md` (2026-10-31) before the test run. The table shows accuracy at price extremes, which the overall MAE can hide.

**Time handling.** All joins, lags and windows in UTC. Local time only for calendar features and plots. A delivery day is a local calendar day and has 24 hourly periods normally, 23 on the spring transition day and 25 on the autumn one; each period maps to exactly one UTC interval. Tests cover both transition days of a year: the right period count per local date, no missing or duplicated UTC intervals, and lag 24 on those days pointing at the UTC interval 24 elapsed hours earlier.

**Gaps and duplicates.** A gap-and-duplicate report is produced from the raw data before any resampling or aggregation and committed to `reports/`. Missing target prices are never filled; those hours are excluded and counted.

## Spark decision

The price data is small (a few hundred thousand rows). The only candidate for Spark is DMI observations, and only if weather enters the project. The plan was to time the same ingest and aggregation in pandas, DuckDB and PySpark (local) on the actual volume and keep the simplest tool that does it in acceptable time. Spark was not used: weather never entered the project because the external-features milestone was skipped (`docs/decisions.md`, 2026-11-05).

## Repository layout and conventions

```
elvarsel/
  src/elvarsel/
    fetch.py        pulls prices into data/raw, idempotent, retries, one request per calendar year (limit=0)
    clean.py        dedupe, resample, UTC index, gap handling
    features.py     lags, calendar, holiday flags
    baselines.py
    models.py
    evaluate.py     splits, metrics, by-hour and by-month tables
    gap_report.py   gap-and-duplicate report on the raw data
    final_run.py    the single test run, writes reports/test.md
  scripts/
    clean.py        one entry point per step; fetch runs as python -m elvarsel.fetch
    features.py
    evaluate.py
    gap_report.py
    final_run.py
  tests/
    fixtures/       two months and one day of raw data, committed
    test_clean.py
    test_evaluate.py
    test_features.py
    test_fetch.py
    test_final_run.py
    test_gap_report.py
    test_models.py
    test_package.py
  notebooks/          empty
  docs/
    design.md
    leakage-audit.md
    decisions.md
  reports/            generated tables and report.md, committed
  data/               gitignored
  README.md
  pyproject.toml
  .github/workflows/ci.yml
  .editorconfig
  .gitattributes
  .gitignore
```

Tooling: `uv` for environments and lockfile, Python 3.12, `ruff` for lint and format (checked in CI), `pytest`, GitHub Actions running lint and tests on the fixtures. Line endings LF via `.gitattributes`.

## Report outline (two pages, `reports/report.md`)

1. What was forecast: target, cutoff, splits and excluded rows.
2. Results: one table, rows are the four candidates run on test (three baselines and ridge; gradient boosting was not run on test, see `docs/decisions.md` 2026-11-03), columns are MAE and RMSE on test and validation. No figures.
3. Where the model fails: by hour, month, extreme prices and worst days. The full tables are in `reports/test.md`.
4. Model choice: why ridge and not gradient boosting.
5. Limitations.
6. Leakage: a summary, with a pointer to the leakage audit.

The report uses numbers and plain sentences, without adjectives.

## Milestones

**Milestone 1: Data in hand (Oct 24-27)**

- [x] Repo, `pyproject.toml`, `uv` lock, `ruff`, `pytest`, CI, `.gitignore`, `.gitattributes`, `.editorconfig`, `docs/design.md`.
- [x] Confirm the Energinet dataset names, columns, resolution per period of history, interval-start vs interval-end timestamps, and earliest date for DK2 prices and for the wind/solar forecast series (with their issue-time field, if any); record them in `docs/decisions.md` with the date checked.
- [x] Decision entries: why DK2 and not Denmark, the hourly-mean target definition, the cutoff.
- [x] `fetch.py` for prices: one request per calendar year with `limit=0`, retrying, idempotent into `data/raw/`. Fixtures committed: two months of `Elspotprices` and one day of `DayAheadPrices` (2025-10-26), including the 25-hour autumn day. `--fixtures` mode on every step except `final_run.py`.
- [x] Gap-and-duplicate report on the raw data, committed to `reports/`.
- [x] `clean.py`: one row per hourly delivery interval keyed by UTC start, quarter-hours averaged into hours, duplicates resolved, gaps left as gaps. Tests: `test_clean.py` covers the 25-hour autumn day; `test_features.py` covers the 23-hour spring day with synthetic data.
- [x] Decision entry: the split dates, fixed before any model exists.
- [x] `docs/leakage-audit.md` started with the price lags, rolling windows and calendar features.

**Milestone 2: Baselines and evaluation (Oct 29-31)**

- [x] `features.py` with the lag, rolling-window and calendar features. Tests that lag 24 on a DST day points at the UTC interval 24 elapsed hours earlier, and that every rolling window ends before the cutoff.
- [x] `evaluate.py`: chronological splits with delivery days kept whole, MAE and RMSE overall / by hour / by month, the extreme-price table, and the count of rows excluded for missing lags.
- [x] Three baselines evaluated on validation. Result table committed to `reports/`.
- [x] Decision entries: why MAPE is excluded, why splits are chronological, why lags are elapsed hours, the extreme-price threshold.

**Milestone 3: Models (Nov 1-3)**

- [x] Ridge on the feature set; coefficients inspected and sanity-checked.
- [x] Gradient boosting on the same set; small grid on validation only.
- [x] Error analysis on validation: by hour, by month, worst 20 days.
- [x] Decision entry: what the model learned that the baselines didn't, or didn't.

**Milestone 4: External features, if verifiable (Nov 5, skipped)** Energinet wind and solar forecasts are published after the 12:00 D-1 cutoff and are excluded, so this milestone is DMI-only or skipped. Skipped 2026-11-05: no verifiable DMI forecast archive; see `docs/decisions.md`.

- [ ] DMI: only if an archive of past forecasts can be found. Otherwise one paragraph in Limitations. (skipped, see decisions.md 2026-11-05)
- [ ] Spark benchmark, only if DMI data enters. (skipped, see decisions.md 2026-11-05)

**Milestone 5: Final run and report (Nov 6-8)**

- [x] One run on the untouched test period. Numbers frozen.
- [x] `reports/report.md` written from the tables.
- [x] README: what it is, how to run lint, tests and the fixture pipeline, the results table, the leakage audit link, limitations.
- [x] Fresh-eyes review, done cold: a check for features that use information from the delivery day or later, preprocessing fitted on validation or test rows, filling or interpolation of the target, and DST days that could misalign a lag. Findings are listed with file and line first, then fixed or noted.
- [ ] Optional: Streamlit page showing the test-period forecast vs actual, deployed to a free host.

**Nov 9: Buffer and verification**

- [x] Fresh-clone check: `uv sync`, `uv run pytest` and each pipeline step with `--fixtures`, run in a new directory as listed in the README.
- [x] CV bullet written from the results table only.
- [x] CI green on `master`.

## Definition of done

1. A clean clone runs lint and tests, then the offline fixture pipeline as listed in the README. `final_run.py` has no `--fixtures` mode, so the test run is not part of this check.
2. `docs/leakage-audit.md` lists every feature with its availability, and nothing else is in the model.
3. The report has one results table on an untouched test period, with MAE and RMSE for three baselines and ridge, the one model chosen on validation (gradient boosting was not run on test, see `docs/decisions.md` 2026-11-03), plus by-hour, by-month and extreme-price breakdowns in `reports/test.md`.
4. The error analysis names where the model fails.
5. The reasons for the cutoff, the 24-hour lag, the exclusion of D-1 actuals, the chronological split, the absence of MAPE and elapsed-hour lags, and the number of delivery periods on a transition day, are written down in this document and `docs/decisions.md`.
