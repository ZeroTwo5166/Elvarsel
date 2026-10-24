# Elvarsel — design and checklist

## What it is

An investigation into whether a learned model can predict every hourly day-ahead electricity price for a delivery day in the DK2 bidding zone (Eastern Denmark) better than simple historical baselines, using only information that was available before the day-ahead auction results were published.

It is a data-science project, not a platform. The deliverable is a reproducible experiment, a leakage audit, an honest result, and a short report. A dashboard is optional.

Phrase it everywhere as an investigation. The model is allowed to lose. A sound experiment with a negative result is a better interview than a headline number with a questionable split.

DK2 is the Nordic-synchronised half of Denmark: Zealand, Lolland-Falster, Bornholm and the islands, including Copenhagen. It has its own hourly price on the day-ahead market, distinct from DK1 (Jutland and Funen), which is on the continental grid.

## Scope

In:

- DK2 hourly spot prices, as many years as Energi Data Service holds, down to a final held-out test period.
- Three baselines, two learned models, chronological evaluation.
- Lagged prices and calendar features. External features (wind/solar/consumption forecasts, weather) only where a historical *forecast* series with a known publication time exists, never actuals.
- A reproducible pipeline: fetch, clean, features, train, evaluate, from a clean clone with three commands.
- Tests on cleaning and feature construction, including daylight-saving days.
- A leakage audit table and a two-page report.

Out, unless everything above is done:

- Weather from DMI.
- A dashboard.
- Spark, unless a measured benchmark says the data needs it.
- Probabilistic forecasts, deep learning, hyperparameter search beyond a small grid.
- DK1 or other zones.

## The forecasting contract

This is the part interviewers will test. It is written down before any code.

**Target.** For delivery day D (a local Danish calendar day), the hourly day-ahead price for DK2 in EUR/MWh for every delivery hour of that day: 24 on an ordinary day, 23 on the spring transition day, 25 on the autumn one. Where the source is 15-minute, the hourly target is the arithmetic mean of the four quarter-hour prices in that delivery hour, and the report and README say so.

**Forecast cutoff.** 12:00 CET/CEST on day D-1. The day-ahead auction for day D closes at 12:00 on D-1 and results are published around 12:45–13:00 on D-1. Anything published after 12:00 on D-1 is not allowed.

**What that makes available at the cutoff:**

- All prices for day D-1 and earlier. Day D-1 prices were published on D-2, so they are fully known. A lag of 24 elapsed hours is therefore legitimate.
- Any forecast of wind, solar, consumption or weather for day D that was itself published before 12:00 on D-1.

**What it forbids:**

- Any price for day D.
- Actual (settled, measured) production, consumption or weather for day D or for day D-1 after 12:00. Actuals for D-1 before noon are technically known but are a trap: it's easy to accidentally use the whole day. The rule for this project is: no actuals from day D-1 or later, in any feature.
- Any feature whose publication time you cannot establish from the source's documentation.

**Leakage audit.** `docs/leakage-audit.md` holds one table row per feature: name, source dataset, what it measures, when it is published relative to the cutoff, and whether it is allowed. A feature not in the table is not in the model. This file is written by hand.

## Data sources

Verify all dataset names, column names and history depth on day one; Energinet renames datasets and changed the day-ahead market to 15-minute resolution in autumn 2025, so the price dataset and its granularity need checking before anything else.

**Energi Data Service (Energinet).** Public REST API, no key, JSON, filterable by price area and date range.

- Day-ahead / spot prices for DK2. Expected columns: a UTC timestamp, a Danish local timestamp, price in DKK and EUR. Before any cleaning, establish and record in `docs/decisions.md`: whether each part of the history is hourly or 15-minute; whether timestamps mark interval start or end; the earliest date; and the duplicate and gap counts. The cleaning step then produces one row per hourly delivery interval, keyed by UTC interval start, with 15-minute periods averaged into their delivery hour. Hourly and quarter-hour observations are never mixed in one series without this step.
- Forecast datasets for wind and solar production (Energinet publishes day-ahead forecasts, typically issued in the morning of D-1). A forecast series is usable only if each value carries an issue or publication timestamp, or the dataset's documentation guarantees when it is published. A historical forecast value with no evidence of when it became available is not a valid feature.
- Actual production and consumption: downloaded for analysis and plots only, never as a feature for day D or D-1 (see contract).

**DMI Open Data.** Free API key. Observations archive is large and well documented. Historical *forecasts* are the uncertain part; if an archive of past forecasts cannot be obtained, weather stays out of the model and the report says why. Do not substitute observations for forecasts.

**Holidays.** The `holidays` Python package for Danish public holidays.

Raw downloads are stored as Parquet under `data/raw/`, gitignored, with the fetch script able to recreate them. `data/processed/` likewise. A small fixed sample (one month, chosen to include a DST transition) is committed under `tests/fixtures/`. Every script accepts `--fixtures`, which reads only from `tests/fixtures/`, never calls an API and needs no key; that is what tests and the clean-clone check use.

## Evaluation design

**Splits, chronological, delivery days kept whole.**

The exact boundaries are fixed in `docs/decisions.md` on the day the price history is inspected, before any model is trained, and never moved. The intended shape, assuming the source goes back far enough:

- Train: complete calendar years up to and including year N-2.
- Validation: calendar year N-1. Used for feature choices and the small hyperparameter grid.
- Test: the latest complete, contiguous period after validation, at least six months, untouched until the final run. One run on test. Its numbers go in the report; nothing is changed after seeing them.

If the history is too short for that, the chosen dates and the reason go in the decision entry. Expanding-window validation on the train+validation range during development, if time allows. Never a random split.

**Metrics.** MAE in EUR/MWh is the headline. RMSE alongside it. Report both overall, by hour of day, and by month. MAPE is not reported: DK2 has zero and negative prices, which make percentage errors meaningless. The report states how many test hours are at or below zero so a reader sees the issue.

**Baselines.** All lags are elapsed hours in UTC, not "same local clock hour". Around a DST transition the two differ by one hour; the elapsed-hours definition is the one that is easy to test and reproduce, and the report says that is what was used.

1. 24-hour persistence: the price 24 elapsed hours earlier.
2. 168-hour persistence: the price 168 elapsed hours earlier.
3. Mean of 1 and 2.

Where a lagged value does not exist (the first rows of the series, or a gap in the source), the row is excluded from evaluation for every candidate alike, and the count of excluded rows is reported.

**Learned models.**

1. Ridge regression on lagged prices and calendar features. Interpretable; coefficients go in the report.
2. `HistGradientBoostingRegressor` on the same features, then with any verified external forecast features added.

Features for both: price lags at 24, 48, 72, 168, 336 elapsed hours; rolling mean and standard deviation over the 168 elapsed hours ending 24 hours before the target hour (so the window is entirely within day D-1 and earlier); local hour of day, day of week, month, Danish public holiday flag, day-after-holiday flag. Lags and windows are in UTC so DST days don't shift them; hour-of-day is local time, because that is what drives demand. If a same-local-hour statistic is wanted later, it is a separately named feature with its own audit row. Tests prove that every window ends before the cutoff and never includes the target hour or anything after it.

**Error analysis.** During development, on validation only: error by hour and month; the 20 worst days with what happened in the market that day where it's findable; whether failures cluster around spikes, negative prices, season changes or holidays. After the single test run, the same analysis on test is diagnostic and goes in the report; nothing is tuned afterwards. This section is the heart of the report.

**Extreme-price diagnostic.** One small extra table: MAE and RMSE for hours above a high-price threshold and for hours at or below zero. The threshold is fixed from the training period (for example its 95th percentile) and written into `decisions.md` before the test run. Average accuracy and accuracy when it matters are different questions; this table answers the second without becoming a dashboard of metrics.

**Time handling.** All joins, lags and windows in UTC. Local time only for calendar features and plots. A delivery day is a local calendar day and has 24 hourly periods normally, 23 on the spring transition day and 25 on the autumn one; each period maps to exactly one UTC interval. Tests cover both transition days of a year: the right period count per local date, no missing or duplicated UTC intervals, and lag 24 on those days pointing at the UTC interval 24 elapsed hours earlier.

**Gaps and duplicates.** A gap-and-duplicate report is produced from the raw data before any resampling or aggregation and committed to `reports/`. Missing target prices are never filled; those hours are excluded and counted.

## Spark decision

The price data is small (a few hundred thousand rows). The only candidate for Spark is DMI observations, and only if weather enters the project. The rule: time the same ingest and aggregation in pandas, DuckDB and PySpark (local) on the actual volume; keep the simplest tool that does it in acceptable time; write the three numbers and the decision into the README. A README line saying "Spark was not needed, DuckDB did it in 4 s" is a legitimate engineering conclusion and a better CV line than an unneeded cluster.

## Repository layout and conventions

```
elvarsel/
  src/elvarsel/
    fetch.py        pulls from the APIs into data/raw, idempotent, retries, pagination
    clean.py        dedupe, resample, UTC index, gap handling
    features.py     lags, calendar, holiday flags
    baselines.py
    models.py
    evaluate.py     splits, metrics, by-hour and by-month tables
    report.py       writes tables and figures to reports/
  scripts/
    run_all.py      fetch -> clean -> features -> train -> evaluate -> report
  tests/
    fixtures/       one month of raw data, committed
    test_clean.py
    test_features.py
    test_evaluate.py
  notebooks/
    exploration.ipynb   one notebook, outputs cleared before commit, exploration only
  docs/
    design.md
    leakage-audit.md
    decisions.md
  reports/            generated tables and figures; the final ones are committed
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

1. Question and forecasting contract, half a page.
2. Data: sources, period, resolution, how many hours at or below zero, DST handling.
3. Method: splits, baselines, models, features, with a pointer to the leakage audit.
4. Results: one table, rows are the five candidates, columns are MAE and RMSE on test. One figure: MAE by hour. One figure: MAE by month. The extreme-price table.
5. Error analysis: where the best model fails and why.
6. Limitations and what you would do next.

No adjectives. Numbers and sentences.

## Milestones

**Milestone 1 — Data in hand (Oct 24–27)**

- [ ] Repo, `pyproject.toml`, `uv` lock, `ruff`, `pytest`, CI, `.gitignore`, `.gitattributes`, `.editorconfig`, `docs/design.md`. First commit is these files only.
- [ ] Confirm the Energinet dataset names, columns, resolution per period of history, interval-start vs interval-end timestamps, and earliest date for DK2 prices and for the wind/solar forecast series (with their issue-time field, if any); record them in `docs/decisions.md` with the date checked.
- [ ] Decision entries by hand: why DK2 and not Denmark, the hourly-mean target definition, the cutoff.
- [ ] `fetch.py` for prices: paginated, retrying, idempotent into `data/raw/`. One-month fixture including a DST transition committed. `--fixtures` mode on every script.
- [ ] Gap-and-duplicate report on the raw data, committed to `reports/`.
- [ ] `clean.py` written by hand: one row per hourly delivery interval keyed by UTC start, quarter-hours averaged into hours, duplicates resolved, gaps left as gaps. Tests, including both DST days of one year with 23 and 25 periods.
- [ ] Decision entry: the split dates, fixed before any model exists.
- [ ] `docs/leakage-audit.md` started with the price lags, rolling windows and calendar features.

**Milestone 2 — Baselines and evaluation (Oct 29–31)**

- [ ] `features.py` with the lag, rolling-window and calendar features. Tests that lag 24 on a DST day points at the UTC interval 24 elapsed hours earlier, and that every rolling window ends before the cutoff.
- [ ] `evaluate.py`: chronological splits with delivery days kept whole, MAE and RMSE overall / by hour / by month, the extreme-price table, and the count of rows excluded for missing lags.
- [ ] Three baselines evaluated on validation. Result table committed to `reports/`.
- [ ] Decision entries: why MAPE is excluded, why splits are chronological, why lags are elapsed hours, the extreme-price threshold.

**Milestone 3 — Models (Nov 1–3)**

- [ ] Ridge on the feature set; coefficients inspected and sanity-checked.
- [ ] Gradient boosting on the same set; small grid on validation only.
- [ ] Error analysis on validation: by hour, by month, worst 20 days.
- [ ] Decision entry: what the model learned that the baselines didn't, or didn't.

**Milestone 4 — External features, if verifiable (Nov 5, skippable)** Energinet wind and solar forecasts are published after the 12:00 D-1 cutoff and are excluded, so this milestone is DMI-only or skipped.

- [ ] DMI: only if an archive of past forecasts can be found. Otherwise one paragraph in Limitations.
- [ ] Spark benchmark, only if DMI data enters. Three timings in the README.

**Milestone 5 — Final run and report (Nov 6–8)**

- [ ] One run on the untouched test period. Numbers frozen.
- [ ] `reports/report.md` written by hand from the tables.
- [ ] README by hand: what it is, how to run in three commands, the results table, the leakage audit link, limitations, what next.
- [ ] Fresh-eyes review, done cold: find any feature that uses information from the delivery day or later, any preprocessing fit on validation or test rows, any fillna or interpolation on the target, and any place where a DST day could misalign a lag. Do not fix anything; list them with file and line. Fix what is real, note what is not.
- [ ] Optional: Streamlit page showing the test-period forecast vs actual, deployed to a free host.

**Nov 9 — Buffer and verification**

- [ ] Clone into a fresh directory, run `uv sync`, `uv run pytest` and `uv run python scripts/run_all.py --fixtures`. It works, or the README is wrong.
- [ ] CV bullet written from the results table only.
- [ ] CI green on `master`.

## Definition of done

1. A clean clone runs lint, tests and the fixture pipeline with three commands.
2. `docs/leakage-audit.md` lists every feature with its availability, and nothing else is in the model.
3. The report has one results table on an untouched test period, with MAE and RMSE for three baselines and two models, plus by-hour, by-month and extreme-price breakdowns.
4. The error analysis names where the model fails.
5. You can explain, without notes: the cutoff, why a 24-hour lag is allowed, why actuals for D-1 are not, why the split is chronological, why MAPE is out, why lags are elapsed hours rather than local clock hours, and how many delivery periods a transition day has.

## Interview questions to be able to answer

1. What exactly is the forecast cutoff, and why is yesterday's price allowed but yesterday's wind production not?
2. Why is MAPE a bad metric here, and what did you report instead?
3. How did you split the data, and what would go wrong with a random split?
4. What did the gradient-boosting model learn that the baselines didn't? Where did it still lose?
5. How many delivery periods does the spring transition day have, how do your lags behave across it, and how do you know?
6. You mentioned Spark. Did you use it? Why or why not?
7. The target is an hourly mean of quarter-hour prices after autumn 2025. What does that change, and did you say so in the report?
