# Seattle House Price Prediction in Python

## Objective

Predict Seattle house prices from property characteristics using a reproducible regression workflow. The project includes data validation, cleaning, feature engineering, exploratory analysis, statistical testing, leakage-aware encoding, model comparison, residual diagnostics, uncertainty analysis, and held-out test evaluation.

## Project Files

| File | Description |
|---|---|
| `House Price Prediction Seattle.ipynb` | End-to-end notebook for analysis, modeling, diagnostics, uncertainty testing, and prediction export |
| `train.csv` | Training data used for fitting and validation splitting |
| `test.csv` | Held-out test data used for final evaluation |
| `test_predictions_all_models.csv` | Test-set predictions from the baseline and trained models |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Ignores checkpoints, caches, virtual environments, and local environment files |

## Dataset Fields

| Feature | Description |
|---|---|
| `beds` | Number of bedrooms in the property |
| `baths` | Number of bathrooms. `0.5` represents a half-bath with a sink and toilet but no tub or shower |
| `size` | Total floor area of the property |
| `size_units` | Unit of measurement for `size` |
| `lot_size` | Total land area associated with the property |
| `lot_size_units` | Unit of measurement for `lot_size` |
| `zip_code` | ZIP code, a postal code used in the United States |
| `price` | Final sale price in US dollars |

Useful conversion: `1 acre = 43,560 sqft`.

## Methodology

1. Validated missing values, duplicate rows, expected units, positive prices, and positive sizes.
2. Converted acre-based lot sizes to square feet.
3. Imputed missing lot sizes using the training-set median after conversion.
4. Engineered size, layout, density, and interaction features.
5. Used EDA plots to assess skewness, correlations, and price relationships.
6. Used Pearson, Spearman, and Kruskal-Wallis tests to validate feature and location signals.
7. Used out-of-fold smoothed ZIP-code target encoding to prevent leakage.
8. Compared a median baseline, Linear Regression, Ridge, Lasso, Elastic Net, and Random Forest.
9. Evaluated residuals, uncertainty, and paired model errors.
10. Exported final predictions to `test_predictions_all_models.csv`.

## Statistical Tests

| Test | Purpose |
|---|---|
| Pearson correlation | Measures linear relationships with sale price |
| Spearman correlation | Measures monotonic relationships with sale price |
| Kruskal-Wallis H-test | Tests whether ZIP-code price distributions differ |
| One-sample residual t-test | Checks whether mean residual differs from zero |
| Residual normality test | Checks whether residuals are normally distributed |
| Spearman test on absolute residuals | Checks whether error increases with predicted price |
| Bootstrap RMSE confidence intervals | Estimates uncertainty around test RMSE |
| Paired Wilcoxon signed-rank tests | Compares row-level absolute errors between models |

## Results

### Validation Set

| Model | RMSE | MAE | R2 |
|---|---:|---:|---:|
| Random Forest | 387,132.67 | 202,397.12 | 0.5456 |
| Ridge | 402,712.71 | 212,548.01 | 0.5082 |
| Lasso | 402,791.96 | 212,786.34 | 0.5081 |
| Elastic Net | 403,026.69 | 212,544.54 | 0.5075 |
| Linear Regression | 408,242.56 | 212,965.79 | 0.4946 |
| Baseline Median | 584,416.11 | 356,457.50 | -0.0356 |

### Held-Out Test Set

| Model | RMSE | MAE | R2 |
|---|---:|---:|---:|
| Random Forest | 418,156.65 | 230,906.46 | 0.5268 |
| Linear Regression | 420,119.91 | 237,952.93 | 0.5223 |
| Lasso | 422,451.15 | 238,783.73 | 0.5170 |
| Ridge | 422,798.47 | 238,697.07 | 0.5162 |
| Elastic Net | 423,790.05 | 238,828.10 | 0.5140 |
| Baseline Median | 630,749.93 | 386,229.29 | -0.0767 |

## Key Takeaways

- Random Forest achieved the strongest validation and held-out test performance.
- All trained models clearly outperformed the median baseline.
- ZIP code is statistically meaningful and is encoded without validation or test leakage.
- Size-related variables and engineered property-density features are major predictors.
- Residual diagnostics show larger absolute errors for higher-priced homes.

## How to Run

```bash
pip install -r requirements.txt
```

Then open and run `House Price Prediction Seattle.ipynb` from top to bottom.
