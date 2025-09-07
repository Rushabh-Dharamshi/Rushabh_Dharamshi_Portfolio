# 🏠 Seattle House Price Prediction in Python

## 🎯 Objective
Predict house prices in Seattle based on property features.

## 📂 Files

- 🟢 **train.csv**  
  - Used **during model training**.  
  - Contains house listings with features:
    `beds`, `baths`, `size`, `size_units`, `lot_size`, `lot_size_units`, `zip_code`, `price`.

- 🔵 **test.csv**  
  - Used **for evaluating models and generating predictions**.  
  - Same features as `train.csv`.

- 🟡 **test_predictions_all_models.csv**  
  - Contains **predicted prices for the test set** from all trained models: Linear, Ridge, Lasso, and Random Forest.

- 📝 **House Price Prediction Seattle.ipynb**  
  - Jupyter Notebook containing all steps: data preprocessing, EDA, feature engineering, model training, hyperparameter tuning, evaluation, and test predictions.

## 🚀 Approach & Steps

1. **📥 Import Libraries & Load Data**  
   - Load `train.csv` and `test.csv` using pandas.  
   - Inspect first few rows to understand features and data types.

2. **🧹 Data Cleaning & Preprocessing**  
   - Round numeric values for consistency.  
   - Fill missing values in `lot_size` and `lot_size_units`.  
   - Convert lot sizes from acres to sqft.  
   - Drop `zip_code` for modeling simplicity.

3. **🛠 Feature Engineering**  
   - `size_lot_interaction`: house size × lot size.  
   - `beds_per_bath`: bedrooms per bathroom ratio.  
   - `lot_per_bed`: land area per bedroom.

4. **📊 Exploratory Data Analysis (EDA)**  
   - Histograms and log-transformations for skewed features.  
   - Correlation heatmap to identify strong predictors.  
   - Boxplots & scatterplots to visualize price relationships.

5. **⚙️ Feature Scaling & Data Preparation**  
   - Split `train.csv` into **training (80%) and validation (20%) sets**.  
   - Log-transform skewed features for linear models.  
   - Scale features for linear regression; Random Forest uses raw features.

6. **🤖 Model Training**  
   - Train Linear Regression, Ridge, Lasso, and Random Forest models.  
   - Evaluate using RMSE and R² on the validation set.

7. **🎯 Hyperparameter Tuning**  
   - Use GridSearchCV + SGDRegressor for Linear, Ridge, Lasso.  
   - GridSearchCV for Random Forest.  
   - Optimized hyperparameters improve model accuracy slightly.

8. **📈 Feature Importance Visualization**  
   - Plot coefficients for linear models.  
   - Plot feature importance for Random Forest.  
   - `size` and `lot_per_bed` consistently most influential across models.

9. **💻 Test Set Predictions**  
   - Use `test.csv` to predict prices with tuned models.  
   - Ridge Regression had lowest RMSE; Random Forest highest.  
   - Save predictions in `test_predictions_all_models.csv`.

## 📝 Notes
- Lot sizes standardized to **square feet** (`1 acre = 43,560 sqft`).  
- Skewed numeric features and target log-transformed for linear models.  
- Random Forest works better with raw features.
