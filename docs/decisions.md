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
