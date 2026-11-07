# elvarsel

Forecasts every hourly day-ahead electricity price in the DK2 bidding zone (Eastern Denmark) for a delivery day D, using only information available before 12:00 Danish time on D-1, from Energinet price data. The features are lagged prices and calendar values. On the held-out test period, 2026-01-01 to 2026-09-30 (6551 hours), ridge regression has an MAE of 29.58 EUR/MWh against 31.61 for the best baseline, the mean of the 24-hour and 168-hour persistence forecasts.

## Results

Test MAE in EUR/MWh, 6551 scored hours, from [reports/test.md](reports/test.md):

| candidate | test MAE |
|---|---|
| persistence_24 | 33.05 |
| persistence_168 | 41.51 |
| mean_24_168 | 31.61 |
| ridge | 29.58 |

persistence_24 and persistence_168 are the price 24 and 168 elapsed hours earlier; mean_24_168 is their mean. Ridge uses alpha 1000, chosen on the 2025 validation year. The full write-up, including errors by hour, month, extreme prices and worst days, is in [reports/report.md](reports/report.md). Model and evaluation choices are recorded in [docs/decisions.md](docs/decisions.md), and every feature's publication time is in [docs/leakage-audit.md](docs/leakage-audit.md).

## Data

All data comes from the Energi Data Service API (`api.energidataservice.dk`), which is public and needs no key. Two datasets are used, filtered to DK2:

- `Elspotprices`: hourly prices from 2000-10-01 to 2025-09-30 local time. Discontinued.
- `DayAheadPrices`: 15-minute prices from 2025-10-01. The target for these hours is the mean of the four quarter-hour prices.

`src/elvarsel/fetch.py` requests one calendar year per call and writes one CSV per month to `data/raw/<dataset>/<YYYY-MM>.csv`. It checks the row count of each month, skips months that already exist (`--force` refetches them), and only fetches complete months. `Elspotprices` has returned HTTP 429 with a `Retry-After` of around 300 seconds; the fetcher waits and retries, printing each retry, so a full fetch can take several minutes. `data/` is gitignored.

## Setup

Requires Python 3.12 or later (`.python-version` pins 3.12) and [uv](https://docs.astral.sh/uv/). uv downloads Python 3.12 if it is not installed. The commands below were run with uv 0.13.5.

```
git clone <repo-url> elvarsel
cd elvarsel
uv sync --locked
```

Lint and tests, as run in CI:

```
uv run ruff check
uv run ruff format --check
uv run pytest
```

The same commands work in Git Bash on Windows and in a Linux shell. CI runs lint and tests on Ubuntu; the pipeline commands below were run on Windows in Git Bash.

## Reproducing

Run from the repository root, in this order:

```
uv run python -m elvarsel.fetch --end 2026-09
uv run python scripts/gap_report.py
uv run python scripts/clean.py
uv run python scripts/features.py
uv run python scripts/evaluate.py
uv run python scripts/final_run.py
```

| step | reads | writes |
|---|---|---|
| fetch | Energi Data Service API | `data/raw/` |
| gap_report | `data/raw/` | `reports/raw-data-gaps.md` |
| clean | `data/raw/` | `data/clean/dk2_hourly.csv` |
| features | `data/clean/` | `data/features/dk2_hourly.csv` |
| evaluate | `data/features/` | `reports/validation.md` (validation only; test rows are dropped) |
| final_run | `data/features/` | `reports/test.md` (test and validation) |

`--end 2026-09` stops at the last month used in the committed reports. Without it, fetch goes up to the last complete month; the split dates are fixed in `src/elvarsel/evaluate.py`, so later months do not change the scores, but `reports/raw-data-gaps.md` would differ. Fetch has no script in `scripts/` and is run as a module.

The test period was scored once for the committed `reports/test.md`. Running `final_run.py` again overwrites that file.

To check the pipeline without network access, every step except `final_run.py` accepts `--fixtures`, which reads the sample months in `tests/fixtures/` and writes to `data/fixtures/` and `reports/fixtures/` (gitignored):

```
uv run python -m elvarsel.fetch --fixtures
uv run python scripts/gap_report.py --fixtures
uv run python scripts/clean.py --fixtures
uv run python scripts/features.py --fixtures
uv run python scripts/evaluate.py --fixtures
```

## Repo layout

- `src/elvarsel/`: the package. Fetching, cleaning, features, baselines, models, evaluation, the gap report and the final test run.
- `scripts/`: thin entry points that call each module's `main()`.
- `tests/`: pytest tests; `tests/fixtures/` holds raw `Elspotprices` for 2024-10 and 2025-01 and one day of `DayAheadPrices`, 2025-10-26. Both October files include the 25-hour autumn day.
- `docs/`: design document, decision log and leakage audit.
- `reports/`: generated gap, validation and test tables, and the hand-written report.
- `notebooks/`: empty.
- `data/`: created by the pipeline, gitignored.

## Limitations

- No wind, solar or weather features: Energinet's day-ahead wind and solar forecasts are published after the 12:00 D-1 cutoff, and no verifiable archive of past DMI forecasts was found. The model cannot see the main driver of large price swings.
- The test period is nine months of a single year, 2026.
- No confidence intervals, because hourly errors are serially correlated, and no feature ablation, so the gain over the baselines is not attributed to any feature.
- The test period has no autumn daylight-saving day, so the 25-hour-day handling was exercised only in train and validation.

See the Limitations section of [reports/report.md](reports/report.md).
