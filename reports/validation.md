# Baselines, ridge and gradient boosting on validation (2025)

EUR/MWh. All candidates are scored on the same rows. Lags are elapsed UTC hours; hour and month are local time. Ridge is fitted on train (2001-2024); its scaling and one-hot encoding are fitted inside the pipeline on train rows only. Gradient boosting is fitted on train with the calendar columns as categoricals and no scaling.

## Overall

| candidate | rows | MAE | RMSE |
|---|---|---|---|
| persistence_24 | 8759 | 31.09 | 45.62 |
| persistence_168 | 8759 | 39.05 | 55.52 |
| mean_24_168 | 8759 | 30.23 | 42.04 |
| ridge | 8759 | 28.06 | 38.66 |
| hgb | 8759 | 28.01 | 38.40 |

## By local hour of day

| hour | rows | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | MAE hgb | RMSE persistence_24 | RMSE persistence_168 | RMSE mean_24_168 | RMSE ridge | RMSE hgb |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 365 | 28.08 | 35.88 | 28.27 | 26.25 | 26.35 | 39.81 | 47.74 | 37.33 | 34.47 | 34.34 |
| 1 | 365 | 26.52 | 34.44 | 26.92 | 25.23 | 25.13 | 37.11 | 45.83 | 35.17 | 32.18 | 31.82 |
| 2 | 365 | 25.63 | 34.72 | 26.50 | 24.60 | 24.53 | 35.93 | 45.73 | 34.52 | 31.30 | 31.04 |
| 3 | 365 | 26.01 | 35.15 | 26.86 | 24.99 | 24.74 | 36.32 | 46.12 | 34.71 | 31.67 | 31.34 |
| 4 | 365 | 26.59 | 35.75 | 27.22 | 25.47 | 25.29 | 36.62 | 46.61 | 34.91 | 31.96 | 31.62 |
| 5 | 365 | 27.42 | 35.37 | 27.63 | 25.71 | 25.66 | 37.93 | 46.56 | 35.38 | 32.55 | 32.27 |
| 6 | 365 | 33.61 | 39.11 | 31.81 | 29.44 | 28.22 | 44.33 | 51.79 | 40.16 | 36.49 | 35.35 |
| 7 | 365 | 41.32 | 42.52 | 35.45 | 33.52 | 32.14 | 54.99 | 59.42 | 46.79 | 43.98 | 42.22 |
| 8 | 365 | 42.76 | 42.84 | 36.25 | 33.82 | 32.27 | 59.75 | 62.63 | 50.34 | 47.57 | 46.11 |
| 9 | 365 | 37.08 | 39.16 | 32.17 | 29.94 | 29.37 | 50.38 | 54.94 | 43.33 | 40.24 | 40.16 |
| 10 | 365 | 31.51 | 39.25 | 29.85 | 27.79 | 27.99 | 43.78 | 52.89 | 39.69 | 36.22 | 36.30 |
| 11 | 365 | 28.17 | 38.70 | 28.86 | 27.09 | 27.83 | 41.80 | 53.28 | 39.06 | 35.71 | 36.41 |
| 12 | 365 | 26.16 | 36.37 | 26.76 | 25.81 | 26.29 | 40.53 | 51.43 | 37.84 | 34.91 | 35.58 |
| 13 | 365 | 25.52 | 34.53 | 25.75 | 25.20 | 25.83 | 39.27 | 48.87 | 36.19 | 33.86 | 34.48 |
| 14 | 365 | 25.94 | 35.30 | 25.98 | 25.14 | 26.05 | 38.92 | 48.61 | 35.91 | 33.47 | 34.27 |
| 15 | 365 | 28.31 | 37.36 | 27.80 | 26.83 | 27.30 | 42.44 | 52.41 | 38.98 | 36.15 | 36.29 |
| 16 | 365 | 31.37 | 42.11 | 31.22 | 29.01 | 29.98 | 48.68 | 61.27 | 45.31 | 41.69 | 42.44 |
| 17 | 365 | 37.26 | 45.73 | 35.14 | 31.31 | 31.01 | 57.34 | 71.36 | 53.95 | 48.68 | 48.03 |
| 18 | 365 | 38.17 | 48.58 | 36.84 | 33.16 | 33.80 | 57.77 | 72.99 | 54.55 | 49.84 | 49.92 |
| 19 | 365 | 41.73 | 53.93 | 40.72 | 36.83 | 36.52 | 64.17 | 79.53 | 59.67 | 55.28 | 54.13 |
| 20 | 365 | 38.09 | 46.38 | 36.39 | 33.02 | 33.19 | 53.63 | 66.94 | 50.42 | 45.97 | 45.57 |
| 21 | 365 | 29.98 | 37.61 | 29.90 | 27.04 | 26.68 | 43.49 | 54.26 | 41.55 | 37.57 | 37.16 |
| 22 | 365 | 24.95 | 33.38 | 25.84 | 23.29 | 23.49 | 36.04 | 46.15 | 34.60 | 31.49 | 31.52 |
| 23 | 364 | 23.90 | 33.10 | 25.42 | 22.89 | 22.61 | 33.98 | 45.17 | 33.02 | 29.92 | 29.29 |

## By local month

| month | rows | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | MAE hgb | RMSE persistence_24 | RMSE persistence_168 | RMSE mean_24_168 | RMSE ridge | RMSE hgb |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 744 | 48.20 | 59.53 | 45.80 | 42.96 | 44.15 | 69.43 | 82.53 | 64.47 | 60.57 | 60.38 |
| 2 | 672 | 29.15 | 51.79 | 34.42 | 27.98 | 30.69 | 39.73 | 63.65 | 43.04 | 35.63 | 39.39 |
| 3 | 743 | 34.25 | 48.42 | 35.70 | 32.96 | 30.72 | 48.81 | 61.44 | 44.20 | 40.99 | 38.37 |
| 4 | 720 | 26.75 | 30.16 | 24.48 | 22.94 | 21.77 | 37.70 | 41.47 | 33.34 | 30.20 | 29.26 |
| 5 | 744 | 27.01 | 29.79 | 24.96 | 24.30 | 23.23 | 36.78 | 39.67 | 32.27 | 29.71 | 28.65 |
| 6 | 720 | 33.10 | 30.74 | 27.83 | 28.30 | 28.20 | 44.24 | 42.50 | 37.74 | 36.18 | 36.13 |
| 7 | 744 | 26.77 | 29.66 | 24.49 | 22.88 | 22.84 | 40.38 | 47.73 | 37.07 | 33.47 | 33.55 |
| 8 | 744 | 20.70 | 22.94 | 19.06 | 19.74 | 18.50 | 32.31 | 36.26 | 27.72 | 27.09 | 25.68 |
| 9 | 720 | 32.27 | 40.63 | 31.74 | 29.59 | 28.56 | 49.73 | 60.65 | 46.93 | 43.09 | 41.67 |
| 10 | 744 | 30.76 | 45.50 | 33.21 | 28.83 | 28.33 | 46.75 | 60.82 | 43.41 | 38.87 | 37.35 |
| 11 | 720 | 34.19 | 40.88 | 33.19 | 30.95 | 31.35 | 50.39 | 55.89 | 46.00 | 43.76 | 43.40 |
| 12 | 744 | 29.78 | 39.42 | 28.20 | 25.26 | 28.00 | 39.30 | 56.42 | 36.43 | 32.57 | 35.23 |

## Extreme prices, high threshold 124.93 EUR/MWh (train p95)

| band | rows | share of scored rows (%) | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | MAE hgb | RMSE persistence_24 | RMSE persistence_168 | RMSE mean_24_168 | RMSE ridge | RMSE hgb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| at or below 0 | 289 | 3.30 | 11.66 | 28.05 | 19.00 | 23.25 | 22.22 | 22.17 | 44.32 | 28.79 | 28.22 | 27.29 |
| above 124.93 | 1333 | 15.22 | 48.62 | 56.15 | 44.84 | 44.54 | 41.84 | 71.73 | 77.50 | 63.00 | 63.23 | 59.11 |

## Worst 20 days by ridge MAE

Local delivery days ranked by ridge daily MAE, highest first; ridge is the model chosen for the test run (see docs/decisions.md). Mean actual price and MAE are over the scored rows of each day.

| date | rows | mean actual price | MAE persistence_24 | MAE persistence_168 | MAE mean_24_168 | MAE ridge | MAE hgb |
|---|---|---|---|---|---|---|---|
| 2025-01-15 | 24 | 212.45 | 160.70 | 141.91 | 151.31 | 152.29 | 151.35 |
| 2025-01-20 | 24 | 231.35 | 105.15 | 133.80 | 118.21 | 112.07 | 95.10 |
| 2025-11-25 | 24 | 224.06 | 88.76 | 116.81 | 102.71 | 105.61 | 104.53 |
| 2025-03-24 | 24 | 129.92 | 117.23 | 34.71 | 75.97 | 75.42 | 57.00 |
| 2025-09-15 | 24 | 12.99 | 59.86 | 110.65 | 85.25 | 74.93 | 87.37 |
| 2025-01-27 | 24 | 48.21 | 55.24 | 183.14 | 117.70 | 73.27 | 100.58 |
| 2025-12-03 | 24 | 162.80 | 84.58 | 8.78 | 42.93 | 73.21 | 68.74 |
| 2025-10-04 | 24 | 0.56 | 65.83 | 89.27 | 77.55 | 70.69 | 60.21 |
| 2025-01-23 | 24 | 83.46 | 76.49 | 40.16 | 58.33 | 70.37 | 54.04 |
| 2025-11-27 | 24 | 67.78 | 93.74 | 57.65 | 75.70 | 69.75 | 75.34 |
| 2025-02-25 | 24 | 139.06 | 92.59 | 25.48 | 50.73 | 68.77 | 60.55 |
| 2025-07-01 | 24 | 138.28 | 40.62 | 117.90 | 79.23 | 65.77 | 59.80 |
| 2025-03-22 | 24 | 9.10 | 62.13 | 83.79 | 72.80 | 65.22 | 63.32 |
| 2025-01-04 | 24 | 119.21 | 54.55 | 10.84 | 27.73 | 63.35 | 59.37 |
| 2025-01-24 | 24 | 43.65 | 39.81 | 80.85 | 60.33 | 62.41 | 52.53 |
| 2025-08-05 | 24 | 5.53 | 52.94 | 37.60 | 43.90 | 59.15 | 58.67 |
| 2025-03-02 | 24 | 52.67 | 69.97 | 33.51 | 50.81 | 57.06 | 46.84 |
| 2025-02-20 | 24 | 70.76 | 39.71 | 95.07 | 67.39 | 56.50 | 37.22 |
| 2025-06-30 | 24 | 97.71 | 77.12 | 74.23 | 75.14 | 56.34 | 42.09 |
| 2025-11-28 | 24 | 46.30 | 26.57 | 98.69 | 60.09 | 56.02 | 47.22 |

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

## Gradient boosting grid

Gradient boosting is fitted on train for each parameter set and scored on validation; the chosen set, lr=0.05 iter=200 leaves=15, has the lowest validation MAE. Because validation chose it, its validation MAE is slightly optimistic for the same reason as the ridge alpha.

| parameters | rows | MAE | RMSE |
|---|---|---|---|
| lr=0.05 iter=200 leaves=15 | 8759 | 28.01 | 38.40 |
| lr=0.05 iter=200 leaves=31 | 8759 | 28.37 | 39.27 |
| lr=0.05 iter=500 leaves=15 | 8759 | 28.53 | 39.00 |
| lr=0.05 iter=500 leaves=31 | 8759 | 29.14 | 40.08 |
| lr=0.1 iter=200 leaves=15 | 8759 | 28.35 | 38.81 |
| lr=0.1 iter=200 leaves=31 | 8759 | 29.05 | 39.92 |
| lr=0.1 iter=500 leaves=15 | 8759 | 29.43 | 40.04 |
| lr=0.1 iter=500 leaves=31 | 8759 | 30.11 | 41.12 |

## Rows excluded for missing target or price features

| split | rows | missing target | missing lag_24 | missing lag_48 | missing lag_72 | missing lag_168 | missing lag_336 | missing roll_mean_168 | missing roll_std_168 | excluded | scored |
|---|---|---|---|---|---|---|---|---|---|---|---|
| train | 210384 | 0 | 24 | 0 | 0 | 0 | 0 | 24 | 24 | 24 | 210360 |
| validation | 8760 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 8759 |
| test | held out | held out | held out | held out | held out | held out | held out | held out | held out | held out | held out |
