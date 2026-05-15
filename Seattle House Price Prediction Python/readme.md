# 🏡 Seattle House Price Prediction in Python

## 🎯 Project Story

Buying a home is one of the biggest financial decisions a person can make, and property prices are shaped by a mix of size, layout, land, and location. This project tells the full machine learning story: starting with raw housing data, cleaning and validating it, exploring what drives value, testing signals statistically, building leakage-aware models, and evaluating final predictions on a held-out test set.

The goal is not only to predict sale prices, but to build a workflow that is explainable, reproducible, and portfolio-ready.

## 🧭 Full Project Lifecycle

```text
Raw CSV Data
    ↓
Data Validation
    ↓
Cleaning + Unit Standardisation
    ↓
Feature Engineering
    ↓
Exploratory Data Analysis
    ↓
Statistical Testing
    ↓
Leakage-Aware Data Preparation
    ↓
Model Training + Validation
    ↓
Residual Diagnostics + Uncertainty Testing
    ↓
Held-Out Test Evaluation
    ↓
Prediction Export
```

## 📌 Objective

Predict Seattle house prices using property-level features such as bedrooms, bathrooms, floor area, lot size, and ZIP code.

The final workflow includes:

- ✅ data validation
- ✅ missing-value handling
- ✅ acre-to-square-foot conversion
- ✅ feature engineering
- ✅ exploratory visual analysis
- ✅ statistical testing
- ✅ leakage-aware ZIP-code encoding
- ✅ model comparison
- ✅ residual diagnostics
- ✅ uncertainty testing
- ✅ final prediction export

## 📁 Project Files

| File | Purpose |
|---|---|
| `House Price Prediction Seattle.ipynb` | Main notebook containing the full lifecycle workflow |
| `train.csv` | Training data used for model fitting and validation splitting |
| `test.csv` | Held-out test data used for final evaluation |
| `test_predictions_all_models.csv` | Final predictions from the baseline and trained models |
| `requirements.txt` | Python dependencies needed to run the project |
| `.gitignore` | Keeps checkpoints, caches, environments, and local files out of version control |

## 🧾 Dataset Description

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

Useful conversion:

```text
1 acre = 43,560 sqft
```

## 🧹 Stage 1: Data Validation and Cleaning

The project begins by checking whether the raw data is reliable enough for modeling.

Validation checks include:

- missing values
- duplicate rows
- positive prices
- positive property sizes
- expected measurement units
- consistency between training and test schemas

The main cleaning challenge was `lot_size`, because the dataset contained both `sqft` and `acre` units, as well as missing values.

The cleaning decision was:

1. Fill missing `lot_size_units` using the training-set mode.
2. Convert acre-based lot sizes into square feet.
3. Calculate the training-set median lot size after conversion.
4. Use that median to impute missing lot sizes in both train and test data.

This avoids mixing incompatible units and prevents test-set leakage.

## 🛠️ Stage 2: Feature Engineering

Raw property features were expanded into real-estate-specific predictors.

| Engineered Feature | Why It Matters |
|---|---|
| `size_lot_interaction` | Captures the combined effect of house size and land size |
| `beds_per_bath` | Measures layout balance and possible crowding |
| `lot_per_bed` | Shows land availability relative to bedroom count |
| `bath_per_bed` | Captures bathroom availability and potential luxury signal |
| `total_rooms` | Summarises overall room count |
| `size_per_room` | Measures average room spaciousness |

These features help the models understand layout, density, and property quality beyond the raw columns.

## 📊 Stage 3: Exploratory Data Analysis

EDA was used to decide how the data should be modeled.

The notebook includes:

- distribution plots
- skewness analysis
- log-transformed feature plots
- correlation heatmap
- bedroom and bathroom price boxplots
- scatter plots for key price drivers
- ZIP-code price comparison

Key findings:

- house prices and several predictors are skewed
- larger homes generally sell for more
- ZIP code has a visible relationship with price
- some features are correlated, which supports using regularised models
- price relationships are not perfectly linear, which supports testing Random Forest

## 🧪 Stage 4: Statistical Testing

The project uses statistical tests to support the visual analysis rather than relying only on charts.

| Test | Purpose |
|---|---|
| Pearson correlation | Tests linear relationships between numeric features and price |
| Spearman correlation | Tests monotonic relationships, useful for skewed/non-linear data |
| Kruskal-Wallis H-test | Tests whether price distributions differ across ZIP codes |
| One-sample residual t-test | Checks whether the average residual differs from zero |
| Residual normality test | Checks whether residuals follow a normal distribution |
| Spearman test on absolute residuals | Checks whether errors increase for higher predicted prices |
| Bootstrap RMSE confidence intervals | Estimates uncertainty around test RMSE |
| Paired Wilcoxon signed-rank tests | Compares model errors row-by-row on the same test observations |

These tests help justify feature selection, ZIP-code encoding, residual interpretation, and final model comparison.

## 🔐 Stage 5: Leakage-Aware Modeling

ZIP code is highly relevant in real estate, but target encoding can easily cause leakage if done incorrectly.

To prevent this:

- the training data is split before target encoding
- training rows receive out-of-fold smoothed ZIP-code encodings
- validation and test rows use only training-fold encoding maps
- unseen ZIP codes fall back to the training global mean
- scaling is fitted only on the training data

This makes validation and test results more trustworthy.

## 🤖 Stage 6: Models Compared

The project compares a simple baseline against multiple regression models.

| Model | Role in the Project |
|---|---|
| Baseline Median | Minimum benchmark that real models must beat |
| Linear Regression | Simple interpretable regression baseline |
| Ridge | Handles correlated predictors using L2 regularisation |
| Lasso | Adds feature-selection pressure using L1 regularisation |
| Elastic Net | Combines Ridge and Lasso behaviour |
| Random Forest | Captures non-linear relationships and feature interactions |

## 📈 Stage 7: Results

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

## 🏆 Final Model

The best-performing model was:

```text
Random Forest
```

It achieved the lowest held-out test RMSE:

```text
Test RMSE: $418,156.65
Test R2:   0.5268
```

This means Random Forest produced the lowest overall prediction error on the test set, while explaining approximately 52.68% of the variance in held-out house prices.

## 🔍 Stage 8: Model Diagnostics

The notebook does not stop at leaderboard metrics. It also checks how the model behaves after prediction.

Diagnostics include:

- residuals vs predicted price
- residual distribution
- Q-Q plot
- residual mean test
- residual normality test
- error-size relationship testing
- feature importance analysis
- bootstrap confidence intervals
- paired Wilcoxon model comparison tests

The residual analysis shows that higher-priced homes tend to have larger absolute errors. This is realistic for housing data and suggests that future improvements would require richer property and location features.

## 💡 Key Takeaways

- Random Forest produced the strongest validation and test performance.
- All trained models clearly outperformed the median baseline.
- ZIP code is statistically meaningful and was encoded without validation/test leakage.
- Interior size and location are major drivers of price.
- Regularised linear models remained competitive and more interpretable.
- Larger errors on expensive homes suggest missing premium-property features.

## 🚀 How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Then open and run:

```text
House Price Prediction Seattle.ipynb
```

The notebook regenerates:

```text
test_predictions_all_models.csv
```

## 🔮 Future Improvements

Potential next steps include adding:

- sale date
- property condition
- renovation history
- school district
- waterfront/view indicators
- neighbourhood-level income or amenity data
- geospatial distance features

These would likely improve predictions, especially for higher-priced homes.
