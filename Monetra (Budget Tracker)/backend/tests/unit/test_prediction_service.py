from datetime import datetime

import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.prediction_service import PredictionService


class FakeModel:
    def predict(self, values):
        assert values == [[3]]
        return [987.65]


class FakeGridSearch:
    def __init__(self, estimator, param_grid, cv, scoring, n_jobs):
        self.best_estimator_ = FakeModel()
        self.received = {
            "estimator": estimator,
            "param_grid": param_grid,
            "cv": cv,
            "scoring": scoring,
            "n_jobs": n_jobs,
        }

    def fit(self, features, labels):
        assert len(features) == len(labels)


class StubPredictionRepository:
    def __init__(self, rows):
        self._rows = rows

    def monthly_spending(self, entry_type="expense"):
        return self._rows


def test_prediction_requires_data():
    service = PredictionService(StubPredictionRepository([]), lambda: 1050.0)

    with pytest.raises(ValidationError, match="No expense data available"):
        service.predict_next_month()


def test_prediction_requires_two_months_of_data(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 3, 15)

        @classmethod
        def strptime(cls, value, fmt):
            return datetime.strptime(value, fmt)

    monkeypatch.setattr("budget_tracker_api.services.prediction_service.datetime", FakeDateTime)
    service = PredictionService(StubPredictionRepository([("2026-03", 120.0)]), lambda: 1050.0)

    with pytest.raises(ValidationError, match="At least two months"):
        service.predict_next_month()


def test_prediction_success(monkeypatch):
    class FakeDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 3, 15)

        @classmethod
        def strptime(cls, value, fmt):
            return datetime.strptime(value, fmt)

    monkeypatch.setattr(
        "budget_tracker_api.services.prediction_service.GridSearchCV",
        FakeGridSearch,
    )
    monkeypatch.setattr("budget_tracker_api.services.prediction_service.datetime", FakeDateTime)
    service = PredictionService(
        StubPredictionRepository(
            [("2026-01", 120.0), ("2026-02", 140.0), ("2026-03", 180.0)]
        ),
        lambda: 1050.0,
    )

    prediction = service.predict_next_month()

    assert prediction["predicted_spending"] == 987.65
    assert prediction["monthly_budget"] == 1050.0
    assert prediction["is_budget_exceeded"] is False
    assert prediction["next_month"] == "April 2026"
