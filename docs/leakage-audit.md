# Leakage audit

The cutoff is 12:00 Danish time on D-1 for every hour of delivery day D. A feature is allowed only if every value it is built from was published before that time. Day-ahead prices for a delivery day are published about 13:00 the day before, so the latest price known at the cutoff is the last period of D-1.

Lags and windows are measured in elapsed UTC hours. Where an elapsed offset lands on the delivery day itself, which happens once a year for lag_24 and the rolling window at the last period of the 25-hour autumn transition day, the value is NaN and the row is excluded. Nothing is ever filled.

A feature not in this table is not in any model.

| Feature | Source | Measures | Published relative to cutoff | Allowed |
|---|---|---|---|---|
| lag_24, lag_48, lag_72, lag_168, lag_336 | Elspotprices, DayAheadPrices (hourly mean, see clean.py) | price_eur that many elapsed hours before the target interval | Source interval is on D-1 or earlier; published by 13:00 D-2 or earlier | Yes, masked when the source falls on D |
| roll_mean_168, roll_std_168 | same | Mean and sample standard deviation of price_eur over the 168 elapsed hours ending 24 hours before the target interval | Window ends on D-1 or earlier; published by 13:00 D-2 or earlier | Yes, masked when the window end falls on D |
| hour, day_of_week, month | Calendar, Europe/Copenhagen | Local hour of day, weekday (0 = Monday), month | Known in advance | Yes |
| is_holiday, is_day_after_holiday | holidays package, DK public holidays only | Flag on the local delivery date, and on the day after a holiday | Known in advance | Yes |
| ForecastDayAhead (wind and solar) | Energinet Forecasts_Hour | Day-ahead production forecast | 18:00 D-1, after the cutoff | No |
| ForecastIntraday, ForecastCurrent | Energinet Forecasts_Hour | Intraday production forecasts | On the delivery day | No |
| DMI weather forecasts | DMI | Weather forecast for D | No archive of past forecast issues found; observations would be actuals from D | No, until a forecast archive is found |
