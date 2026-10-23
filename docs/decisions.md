# Decisions

## 2026-10-23 Price data source

Checked 2026-10-23 against api.energidataservice.dk.

Hourly history: Elspotprices, columns HourUTC, HourDK, PriceArea, SpotPriceEUR, SpotPriceDKK.
First DK2 price 2000-09-30T22:00 UTC (local 2000-10-01). Last row 2025-09-30T21:00 UTC. Discontinued, not updated.

15-minute history: DayAheadPrices, columns TimeUTC, TimeDK, PriceArea, DayAheadPriceEUR, DayAheadPriceDKK.
From 2025-10-01 local. Active.

Timestamps are interval start in both. UTC columns are unique; local columns repeat on autumn transition days, so UTC is the key.
Verified counts: 23 rows 2024-03-31, 25 rows 2024-10-27 (hourly); 96 rows 2025-10-02, 100 rows 2025-10-26, 92 rows 2026-03-29 (15-min).

EUR is the native price; DKK is derived from EUR since 2025-02-01.

## 2026-10-23 Why DK2 and not Denmark

(your sentences: separate bidding zone, own price, Nordic grid, Copenhagen)

## 2026-10-23 Target is the hourly mean across the resolution change

(your sentences: hourly price from Elspotprices up to 2025-09-30; from 2025-10-01 the arithmetic mean of the four DayAheadPriceEUR quarter-hours in each UTC hour; the report says so)

## 2026-10-23 Cutoff 12:00 on D-1

(your sentences: auction closes 12:00, results ~12:45-13:00; nothing published after 12:00 D-1)

## 2026-10-23 Energinet wind and solar forecasts are not usable

Forecasts_Hour, from 2019-10-31. ForecastDayAhead is generated 17:50 and published 18:00 Danish time on D-1. ForecastIntraday is issued 06:00 on the delivery day. Only ForecastCurrent carries a per-row issue timestamp. All columns are published after the 12:00 D-1 cutoff and are excluded. Recorded in the leakage audit as not allowed.