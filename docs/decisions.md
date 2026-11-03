# Decisions

## 2026-10-23 Price data source

Checked 2026-10-23 against api.energidataservice.dk.

Hourly history: Elspotprices, columns HourUTC, HourDK, PriceArea, SpotPriceDKK, SpotPriceEUR.
First DK2 price 2000-09-30T22:00 UTC (local 2000-10-01). Last row 2025-09-30T21:00 UTC. Discontinued, not updated.

15-minute history: DayAheadPrices, columns TimeUTC, TimeDK, PriceArea, DayAheadPriceEUR, DayAheadPriceDKK.
From 2025-10-01 local. Active.

Timestamps are interval start in both. UTC columns are unique; local columns repeat on autumn transition days, so UTC is the key.
Verified counts: 23 rows 2024-03-31, 25 rows 2024-10-27 (hourly); 96 rows 2025-10-02, 100 rows 2025-10-26, 92 rows 2026-03-29 (15-min).

EUR is the native price; DKK is derived from EUR since 2025-02-01.

## 2026-10-23 Why DK2 and not Denmark

Denmark has two bidding zones, DK1 west of the Great Belt and DK2 east of it, each with its own day-ahead price. There is no single Danish price to forecast. DK2 covers Zealand and Copenhagen and is coupled to Sweden (SE4) and to DK1, so its price moves with Nordic hydro and wind as much as with continental gas.

## 2026-10-23 Target is the hourly mean across the resolution change

The target is one price per hour. Up to 2025-09-30 it is SpotPriceEUR from Elspotprices. From 2025-10-01 it is the arithmetic mean of the four DayAheadPriceEUR values in each UTC hour. The quarter-hour structure is not modelled. The report states this.

## 2026-10-23 Cutoff 12:00 on D-1

The day-ahead auction closes at 12:00 CET on the day before delivery and results are published around 12:45 to 13:00. A feature is allowed only if it was available before 12:00 on D-1. Anything published after that, including the auction result itself, is excluded.

## 2026-10-23 Energinet wind and solar forecasts are not usable

Forecasts_Hour, from 2019-10-31. ForecastDayAhead is generated 17:50 and published 18:00 Danish time on D-1. ForecastIntraday is issued 06:00 on the delivery day. Only ForecastCurrent carries a per-row issue timestamp. All columns are published after the 12:00 D-1 cutoff and are excluded. Recorded in the leakage audit as not allowed.

## 2026-10-25 API rate limit and yearly requests

Elspotprices returned 429 after a few requests, with Retry-After around 300 seconds. DayAheadPrices was not throttled. The fetcher moved from one request per month to one per calendar year, still writing one file per month with the row-count check per month. A 429 is retried after waiting Retry-After, and each retry is printed. The full history is 300 hourly months, 219,144 rows, and 12 fifteen-minute months, 35,040 rows.

## 2026-10-29 Split dates

Fixed 2026-10-29, before any model exists. Delivery days are kept whole. The data begins 2000-10-01 local, so the first complete year is 2001; the last complete month is September 2026.

Train: calendar years 2001 through 2024.
Validation: 2025. Used for feature choices and the hyperparameter grid.
Test: 2026-01-01 through 2026-09-30. Untouched until the final run.

Why chronological: a random split puts hours from the same day, and from days adjacent to the test rows, into training. With lags of 24 and 168 hours the model would be scored on days it has already seen through their neighbours. The only honest question is whether the model predicts days that come after everything it was trained on.

## 2026-10-31 MAPE is not reported

DK2 has zero and negative prices. Percentage error is undefined at zero and blows up near it, so MAPE would be dominated by a handful of hours. Validation 2025 has 289 hours at or below 0 EUR/MWh (3.30% of scored rows). MAE in EUR/MWh is the headline metric; RMSE is reported alongside it to show the weight of large misses. The count of hours at or below zero is reported so the reader sees why.

## 2026-10-31 Splits are chronological, on whole delivery days

Split membership is decided by local delivery day, never by row, so a 23- or 25-period DST day always lands whole in one split. Test is not scored until the final run: evaluate.py raises if test rows are requested without an explicit flag, nothing passes it, and the report script drops test rows right after reading the features file.

## 2026-10-31 Lags are elapsed hours, not local clock hours

On DST transition days a local day has 23 or 25 delivery periods. A local-clock lag of 24 hours would point at the wrong interval, or at a local hour that does not exist or occurs twice. Lags are counted in elapsed UTC hours instead. Hour of day stays local, because local time drives demand. Consequence: on an autumn transition day, 24 elapsed hours before the last period (23:00 local) is 00:00 of the same delivery day, which is not known at the cutoff, so lag_24 is masked. This is the only source of excluded rows: 24 in train, 1 in validation.

## 2026-10-31 Extreme-price threshold

High prices are defined as above 124.93 EUR/MWh, the 95th percentile of hourly price over the train period (2001-2024, 210,384 hours). It is a fixed constant, not recomputed, so a re-fetch cannot move it, and it uses no validation or test data. The train period spans very different price levels: the yearly 95th percentile ranges from 34 (2001) to 503 (2022). As a result, 15.22% of scored validation hours (1,333) are above the threshold, against 5% in train. The share is reported next to every band. The 99th percentile (309.10) was considered and rejected because it leaves too few 2025 hours to score.

## 2026-11-01 Ridge alpha

Alpha is chosen from {0.01, 0.1, 1, 10, 100, 1000} by validation MAE. 1000 was chosen, but the grid is flat: MAE ranges from 28.058 to 28.062. Extending the grid would not change the result. Because validation chose alpha, the validation MAE for ridge is slightly optimistic. The test run in M5 gives the unbiased number.

## 2026-11-01 Encoding for ridge

Hour, weekday and month are one-hot encoded inside the pipeline, with categories learned on train only and unseen values ignored. All levels are kept, so coefficients are only comparable within one calendar column. Lags and rolling statistics are standardised on train. Holiday flags stay 0/1. Encoding is part of the model, so the feature set and leakage audit are unchanged.

## 2026-11-01 Common scoring rows

All candidates are scored on the same rows: those with a target and every model feature present. On the real data this is the same 8,759 validation rows as before, so baseline numbers did not change.

## 2026-11-01 Fixture month for 2025

Elspotprices 2025-01 is added to the fixtures, copied from the real raw data, so the fixture validation split has scored rows (408). The end-to-end fixture test then runs the same alpha grid and scoring as the real run, with no fixture-only code path.

## 2026-11-01 Empty validation split

A split with 0 scored rows raises an error naming the split, instead of falling back to a default alpha. A silent fallback would produce a report that looks valid but scores nothing.

## 2026-11-02 Gradient boosting grid

Eight parameter sets, learning rate {0.05, 0.1} by iterations {200, 500} by leaves {15, 31}, chosen by validation MAE. The smallest set won: lr 0.05, 200 iterations, 15 leaves, MAE 28.01, RMSE 38.40. Every increase in capacity made validation worse, in order, up to 30.11 for the largest set. The chosen point is on the edge of the grid. The grid is not extended downwards: the train period spans 2001-2024 with price levels from 34 to 503 EUR/MWh at the 95th percentile, so more fitting capacity fits old regimes that 2025 does not share, and a smaller model is the right direction for the final run. Because validation chose the parameters, the validation MAE is optimistic; the test run gives the unbiased number.

## 2026-11-02 Gradient boosting uses the raw features

Hour, weekday and month go in as native categorical columns, lags and rolling statistics unscaled, holiday flags as 0/1. Trees do not need scaling or one-hot encoding, and categorical splits let the model treat hours and weekdays as groups rather than ordered values. The feature set is identical to ridge, so the leakage audit is unchanged and both learned models and all baselines score the same 8,759 validation rows.

## 2026-11-03 Ridge goes to the test run

Ridge (alpha 1000) and gradient boosting (lr 0.05, 200 iterations, 15 leaves) score 28.06 and 28.01 MAE on the validation year, against 30.23 for the best baseline. The 0.05 gap is not evidence of a difference: hourly errors are serially correlated, so the 8759 rows are far fewer independent observations than they look, and settling it would need a paired block bootstrap that this project does not do. Gradient boosting is better above the train p95 price (41.84 against 44.54) and in hours 6 to 9. Ridge is better in January, February and December. On the 20 days where ridge does worst, gradient boosting is better on 17; on the 20 days where gradient boosting does worst, ridge is better on 9. Neither wins overall. Ridge is chosen because it matches the accuracy with a model whose coefficients can be read: lag_24 carries most of the signal (28.41 per train standard deviation), Saturday and Sunday are 8.16 and 6.48 EUR/MWh below the average weekday, and a holiday is 5.90 below. Both models beat the best baseline by about 2 EUR/MWh. No run removes features to show where the gain comes from, so the entry does not claim that. Ridge is frozen from here. The test set is run once, with no re-fitting.
