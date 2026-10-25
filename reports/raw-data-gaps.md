| dataset | key | rows | first | last | duplicate keys | missing intervals | null EUR prices | null DKK prices |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Elspotprices | HourUTC | 219144 | 2000-09-30T22:00 | 2025-09-30T21:00 | 0 | 0 | 0 | 0 |
| DayAheadPrices | TimeUTC | 35040 | 2025-09-30T22:00 | 2026-09-30T21:45 | 0 | 0 | 0 | 0 |

| dataset | duplicate key | rows |
| --- | --- | --- |

| dataset | gap start | gap end (next present) | missing intervals | length |
| --- | --- | --- | --- | --- |

| local date | dataset | DK2 rows | expected (decisions.md) |
| --- | --- | --- | --- |
| 2024-03-31 | Elspotprices | 23 | 23 |
| 2024-10-27 | Elspotprices | 25 | 25 |
| 2025-10-26 | DayAheadPrices | 100 | 100 |
| 2026-03-29 | DayAheadPrices | 92 | 92 |
