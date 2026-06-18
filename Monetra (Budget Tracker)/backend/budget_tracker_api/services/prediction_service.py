from collections.abc import Callable
from datetime import datetime, timedelta

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.repositories.expense_repository import ExpenseRepository


class PredictionService:
    def __init__(self, repository: ExpenseRepository, budget_provider: Callable[[str | None], float]):
        self._repository = repository
        self._budget_provider = budget_provider

    def predict_next_month(self) -> dict:
        data = self._repository.monthly_spending("expense")
        if not data:
            raise ValidationError("No expense data available for prediction.")

        first_month = datetime.strptime(data[0][0], "%Y-%m")
        now = datetime.now()
        spending_lookup = {month: amount for month, amount in data}

        months: list[str] = []
        current = first_month
        while current <= now:
            months.append(current.strftime("%Y-%m"))
            current = (current.replace(day=1) + timedelta(days=32)).replace(day=1)

        if len(months) < 2:
            raise ValidationError("At least two months of data are required for prediction.")

        spending = [spending_lookup.get(month, 0.0) for month in months]
        features = np.array([[index] for index in range(len(months))])
        labels = np.array(spending)

        param_grid = {
            "n_estimators": [50, 100, 200],
            "max_depth": [None, 5, 10],
            "min_samples_split": [2, 5],
        }
        estimator = RandomForestRegressor(random_state=42)
        grid_search = GridSearchCV(
            estimator,
            param_grid,
            cv=2,
            scoring="neg_mean_squared_error",
            n_jobs=-1,
        )
        grid_search.fit(features, labels)

        next_month_index = len(months)
        predicted_spending = float(grid_search.best_estimator_.predict([[next_month_index]])[0])
        next_month_date = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        next_month_key = next_month_date.strftime("%Y-%m")
        monthly_budget = self._budget_provider(next_month_key)

        return {
            "next_month": next_month_date.strftime("%B %Y"),
            "predicted_spending": round(predicted_spending, 2),
            "is_budget_exceeded": predicted_spending > monthly_budget,
            "monthly_budget": round(monthly_budget, 2),
        }
