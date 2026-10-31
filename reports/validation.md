# Baselines and ridge on validation (2025)

EUR/MWh. All candidates are scored on the same rows. Lags are elapsed UTC hours; hour and month are local time. Ridge is fitted on train (2001-2024); its scaling and one-hot encoding are fitted inside the pipeline on train rows only.

## Overall

| candidate | rows | MAE | RMSE |
|---|---|---|---|
| persistence_24 | 8759 | 31.09 | 45.62 |
| persistence_168 | 8759 | 39.05 | 55.52 |
| mean_24_168 | 8759 | 30.23 | 42.04 |
| ridge | 8759 | 28.06 | 38.66 |

## By local hour of day

| hour | rows | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | RMSE persistence_24 | RMSE persistence_168 | RMSE mean_24_168 | RMSE ridge |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 365 | 28.08 | 35.88 | 28.27 | 26.25 | 39.81 | 47.74 | 37.33 | 34.47 |
| 1 | 365 | 26.52 | 34.44 | 26.92 | 25.23 | 37.11 | 45.83 | 35.17 | 32.18 |
| 2 | 365 | 25.63 | 34.72 | 26.50 | 24.60 | 35.93 | 45.73 | 34.52 | 31.30 |
| 3 | 365 | 26.01 | 35.15 | 26.86 | 24.99 | 36.32 | 46.12 | 34.71 | 31.67 |
| 4 | 365 | 26.59 | 35.75 | 27.22 | 25.47 | 36.62 | 46.61 | 34.91 | 31.96 |
| 5 | 365 | 27.42 | 35.37 | 27.63 | 25.71 | 37.93 | 46.56 | 35.38 | 32.55 |
| 6 | 365 | 33.61 | 39.11 | 31.81 | 29.44 | 44.33 | 51.79 | 40.16 | 36.49 |
| 7 | 365 | 41.32 | 42.52 | 35.45 | 33.52 | 54.99 | 59.42 | 46.79 | 43.98 |
| 8 | 365 | 42.76 | 42.84 | 36.25 | 33.82 | 59.75 | 62.63 | 50.34 | 47.57 |
| 9 | 365 | 37.08 | 39.16 | 32.17 | 29.94 | 50.38 | 54.94 | 43.33 | 40.24 |
| 10 | 365 | 31.51 | 39.25 | 29.85 | 27.79 | 43.78 | 52.89 | 39.69 | 36.22 |
| 11 | 365 | 28.17 | 38.70 | 28.86 | 27.09 | 41.80 | 53.28 | 39.06 | 35.71 |
| 12 | 365 | 26.16 | 36.37 | 26.76 | 25.81 | 40.53 | 51.43 | 37.84 | 34.91 |
| 13 | 365 | 25.52 | 34.53 | 25.75 | 25.20 | 39.27 | 48.87 | 36.19 | 33.86 |
| 14 | 365 | 25.94 | 35.30 | 25.98 | 25.14 | 38.92 | 48.61 | 35.91 | 33.47 |
| 15 | 365 | 28.31 | 37.36 | 27.80 | 26.83 | 42.44 | 52.41 | 38.98 | 36.15 |
| 16 | 365 | 31.37 | 42.11 | 31.22 | 29.01 | 48.68 | 61.27 | 45.31 | 41.69 |
| 17 | 365 | 37.26 | 45.73 | 35.14 | 31.31 | 57.34 | 71.36 | 53.95 | 48.68 |
| 18 | 365 | 38.17 | 48.58 | 36.84 | 33.16 | 57.77 | 72.99 | 54.55 | 49.84 |
| 19 | 365 | 41.73 | 53.93 | 40.72 | 36.83 | 64.17 | 79.53 | 59.67 | 55.28 |
| 20 | 365 | 38.09 | 46.38 | 36.39 | 33.02 | 53.63 | 66.94 | 50.42 | 45.97 |
| 21 | 365 | 29.98 | 37.61 | 29.90 | 27.04 | 43.49 | 54.26 | 41.55 | 37.57 |
| 22 | 365 | 24.95 | 33.38 | 25.84 | 23.29 | 36.04 | 46.15 | 34.60 | 31.49 |
| 23 | 364 | 23.90 | 33.10 | 25.42 | 22.89 | 33.98 | 45.17 | 33.02 | 29.92 |

## By local month

| month | rows | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | RMSE persistence_24 | RMSE persistence_168 | RMSE mean_24_168 | RMSE ridge |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 744 | 48.20 | 59.53 | 45.80 | 42.96 | 69.43 | 82.53 | 64.47 | 60.57 |
| 2 | 672 | 29.15 | 51.79 | 34.42 | 27.98 | 39.73 | 63.65 | 43.04 | 35.63 |
| 3 | 743 | 34.25 | 48.42 | 35.70 | 32.96 | 48.81 | 61.44 | 44.20 | 40.99 |
| 4 | 720 | 26.75 | 30.16 | 24.48 | 22.94 | 37.70 | 41.47 | 33.34 | 30.20 |
| 5 | 744 | 27.01 | 29.79 | 24.96 | 24.30 | 36.78 | 39.67 | 32.27 | 29.71 |
| 6 | 720 | 33.10 | 30.74 | 27.83 | 28.30 | 44.24 | 42.50 | 37.74 | 36.18 |
| 7 | 744 | 26.77 | 29.66 | 24.49 | 22.88 | 40.38 | 47.73 | 37.07 | 33.47 |
| 8 | 744 | 20.70 | 22.94 | 19.06 | 19.74 | 32.31 | 36.26 | 27.72 | 27.09 |
| 9 | 720 | 32.27 | 40.63 | 31.74 | 29.59 | 49.73 | 60.65 | 46.93 | 43.09 |
| 10 | 744 | 30.76 | 45.50 | 33.21 | 28.83 | 46.75 | 60.82 | 43.41 | 38.87 |
| 11 | 720 | 34.19 | 40.88 | 33.19 | 30.95 | 50.39 | 55.89 | 46.00 | 43.76 |
| 12 | 744 | 29.78 | 39.42 | 28.20 | 25.26 | 39.30 | 56.42 | 36.43 | 32.57 |

## Extreme prices, high threshold 124.93 EUR/MWh (train p95)

| band | rows | share of scored rows (%) | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | RMSE persistence_24 | RMSE persistence_168 | RMSE mean_24_168 | RMSE ridge |
|---|---|---|---|---|---|---|---|---|---|---|
| at or below 0 | 289 | 3.30 | 11.66 | 28.05 | 19.00 | 23.25 | 22.17 | 44.32 | 28.79 | 28.22 |
| above 124.93 | 1333 | 15.22 | 48.62 | 56.15 | 44.84 | 44.54 | 71.73 | 77.50 | 63.00 | 63.23 |

## Ridge alpha grid

Ridge is fitted on train for each alpha and scored on validation. Chosen alpha: 1000, the lowest validation MAE. Because validation chose it, its validation MAE is slightly optimistic; the single test run is the unbiased number.

| alpha | rows | MAE | RMSE |
|---|---|---|---|
| 0.01 | 8759 | 28.06 | 38.67 |
| 0.1 | 8759 | 28.06 | 38.67 |
| 1 | 8759 | 28.06 | 38.67 |
| 10 | 8759 | 28.06 | 38.67 |
| 100 | 8759 | 28.06 | 38.67 |
| 1000 | 8759 | 28.06 | 38.66 |

## Ridge coefficients, alpha 1000

Lags and rolling statistics are standardised with train mean and standard deviation, so their coefficients are EUR/MWh per train standard deviation. Hour, weekday and month are one-hot and the holiday flags are 0/1, so their coefficients are EUR/MWh. Every level of each calendar column is encoded, so only differences within a column are meaningful.

| input | coefficient |
|---|---|
| intercept | 49.97 |
| lag_24 | 28.41 |
| lag_48 | 0.49 |
| lag_72 | 4.29 |
| lag_168 | 6.46 |
| lag_336 | 5.47 |
| roll_mean_168 | 6.89 |
| roll_std_168 | 0.24 |
| hour_0 | -1.33 |
| hour_1 | -1.78 |
| hour_2 | -2.06 |
| hour_3 | -2.19 |
| hour_4 | -2.11 |
| hour_5 | -1.61 |
| hour_6 | -0.47 |
| hour_7 | 1.11 |
| hour_8 | 1.74 |
| hour_9 | 1.33 |
| hour_10 | 0.93 |
| hour_11 | 0.66 |
| hour_12 | 0.14 |
| hour_13 | -0.20 |
| hour_14 | -0.37 |
| hour_15 | -0.22 |
| hour_16 | 0.27 |
| hour_17 | 1.60 |
| hour_18 | 2.10 |
| hour_19 | 1.92 |
| hour_20 | 1.17 |
| hour_21 | 0.46 |
| hour_22 | -0.10 |
| hour_23 | -0.98 |
| day_of_week_0 | 7.73 |
| day_of_week_1 | 2.42 |
| day_of_week_2 | 1.10 |
| day_of_week_3 | 0.25 |
| day_of_week_4 | -1.04 |
| day_of_week_5 | -6.07 |
| day_of_week_6 | -4.39 |
| month_1 | 0.33 |
| month_2 | -0.01 |
| month_3 | -0.58 |
| month_4 | 0.24 |
| month_5 | -0.16 |
| month_6 | 1.18 |
| month_7 | -0.73 |
| month_8 | 2.76 |
| month_9 | -1.64 |
| month_10 | -1.09 |
| month_11 | 1.62 |
| month_12 | -1.92 |
| is_holiday | -5.90 |
| is_day_after_holiday | 0.30 |

## Rows excluded for missing target or price features

| split | rows | missing target | missing lag_24 | missing lag_48 | missing lag_72 | missing lag_168 | missing lag_336 | missing roll_mean_168 | missing roll_std_168 | excluded | scored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 210384 | 0 | 24 | 0 | 0 | 0 | 0 | 24 | 24 | 24 | 210360 |
| validation | 8760 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 8759 |
| test | held out | held out | held out | held out | held out | held out | held out | held out | held out | held out | held out |
