# DK2 day-ahead price forecast

## 1. What was forecast

The target is the DK2 day-ahead price in EUR/MWh for each hour of a delivery day; from 2025-10-01 it is the mean of the four quarter-hour prices. A forecast for day D uses only information published before 12:00 Danish time on D-1. Splits are chronological on whole local delivery days. A row is excluded when its target or a price feature is missing; the only exclusions are the lag_24 and rolling-window mask on the last period of the 25-hour autumn day.

| split | local delivery days | rows | excluded | scored |
|---|---|---|---|---|
| train | 2001-01-01 to 2024-12-31 | 210384 | 24 | 210360 |
| validation | 2025-01-01 to 2025-12-31 | 8760 | 1 | 8759 |
| test | 2026-01-01 to 2026-09-30 | 6551 | 0 | 6551 |

## 2. Results

| candidate | test MAE | test RMSE | validation MAE | validation RMSE |
|---|---|---|---|---|
| persistence_24 | 33.05 | 50.54 | 31.09 | 45.62 |
| persistence_168 | 41.51 | 61.28 | 39.05 | 55.52 |
| mean_24_168 | 31.61 | 46.42 | 30.23 | 42.04 |
| ridge | 29.58 | 42.65 | 28.06 | 38.66 |

EUR/MWh. Ridge MAE is 2.03 below the best baseline, mean_24_168, on test (29.58 against 31.61) and 2.17 below it on validation (28.06 against 30.23). Every candidate has a higher MAE and RMSE on test than on validation.

## 3. Where the model fails

By hour. Ridge MAE on test is highest at hours 20 (42.99), 19 (39.73) and 21 (34.68). In hours 0 to 4 persistence_24 is lower than ridge on test (22.37 against 23.13 at hour 2); on validation ridge is lowest in every hour.

By month. Ridge MAE on test is highest in September (45.02) and March (36.18). A baseline is lower than ridge in May (mean_24_168, 21.40 against 21.97) and July (persistence_24, 28.46 against 28.64).

Extreme prices. 2537 test hours, 38.73% of scored rows, are above the train p95 of 124.93 EUR/MWh, against 15.22% in validation. There ridge MAE is 33.10 against 34.74 for mean_24_168. 103 test hours (1.57%) are at or below zero. There ridge MAE is 29.67 against 11.06 for persistence_24, and only persistence_168 is higher (30.99).

Worst days. Eight of the 20 worst test days are in September 2026, including the worst, 2026-09-22 (126.20), and the run 2026-09-19 to 2026-09-22. Four are in March. Mean actual price on these days ranges from 13.66 to 258.39. On 18 of the 20 at least one baseline is lower than ridge; on 2026-09-22 persistence_168 is 56.71. The tables do not show what happened in the market on these days.

## 4. Model choice

Ridge (alpha 1000) and gradient boosting scored 28.06 and 28.01 MAE on validation; the 0.05 gap is not evidence of a difference, because hourly errors are serially correlated. Ridge was chosen because its coefficients can be read: lag_24 carries most of the signal, 28.41 EUR/MWh per train standard deviation. Gradient boosting was not run on test, so the test period was scored once, by one model fixed on validation.

## 5. Limitations

- No wind, solar or weather features. Energinet's day-ahead wind and solar forecasts are published at 18:00 on D-1, after the cutoff (decision 2026-10-23). No verifiable archive of past DMI forecasts was found, and observed weather is not known at the cutoff (decision 2026-11-05). The model cannot see wind and solar output, a main driver of the large price swings.
- The test period is nine months of one year, 2026.
- There are no confidence intervals: hourly errors are serially correlated, so the 6551 test rows are fewer independent observations than they appear. No feature ablation was run, so the gain is not attributed to any feature.
- The test period has no autumn DST day; the 25-hour day of 2026 is 2026-10-25. That mask was exercised in train and validation only.

## 6. Leakage

Every feature is a price from D-1 or earlier or a calendar value, a lag that would reach into the delivery day is masked and never filled, and scaling and encoding are fitted on train rows only. Each feature's source and publication time relative to the cutoff is listed in [docs/leakage-audit.md](../docs/leakage-audit.md).
