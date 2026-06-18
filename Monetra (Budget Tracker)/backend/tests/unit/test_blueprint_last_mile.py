def test_misc_blueprint_edges(client, app):
    class SettingsService:
        def list_monthly_income_records(self, before_month):
            return [{"month_key": before_month, "monthly_income": 100.0}]

        def update_monthly_budget(self, payload):
            return {"monthly_budget": payload.get("monthly_budget"), "budget_month": payload.get("month")}

        def update_monthly_income(self, payload):
            return {"monthly_income": payload.get("monthly_income"), "income_month": payload.get("month")}

        def get_settings(self, month=None):
            return {"month": month}

    class SavingsGoalService:
        def __init__(self):
            self.deleted = []

        def list_goals(self):
            return [{"id": 1}]

        def create_goal(self, payload):
            return {"id": 2, **payload}

        def update_goal(self, goal_id, payload):
            return {"id": goal_id, **payload}

        def delete_goal(self, goal_id):
            self.deleted.append(goal_id)

    class LatencyService:
        def __init__(self):
            self.records = []

        def report_for_user(self, user_id, limit):
            return {"user_id": user_id, "limit": limit}

        def record(self, **payload):
            self.records.append(payload)

    class ReportService:
        def generate_monthly_report(self, month=None):
            raise ValueError("bad month")

    savings_service = SavingsGoalService()
    latency_service = LatencyService()
    app.extensions["services"]["settings_service"] = SettingsService()
    app.extensions["services"]["savings_goal_service"] = savings_service
    app.extensions["services"]["latency_service"] = latency_service
    app.extensions["services"]["report_service"] = ReportService()

    assert client.get("/api/settings/income-records?before=2026-06").get_json()["data"][0]["month_key"] == "2026-06"
    assert client.put("/api/settings/budget", json={"monthly_budget": 700, "month": "2026-06"}).get_json()["data"]["budget_month"] == "2026-06"
    assert client.put("/api/settings/income", json={"monthly_income": 1400, "month": "2026-06"}).get_json()["data"]["income_month"] == "2026-06"

    assert client.put("/api/savings-goals/4", json={"name": "Buffer"}).get_json()["data"]["id"] == 4
    assert client.delete("/api/savings-goals/4").get_json()["data"]["message"] == "Savings goal deleted successfully."
    assert savings_service.deleted == [4]

    assert client.post("/api/observability/client-failure", json={"operation": "Bad Op!", "duration_ms": "bad"}).get_json()["data"] == {"recorded": True}
    client_failure = next(record for record in latency_service.records if record["method"] == "CLIENT")
    assert client_failure["duration_ms"] == 0.0
    assert client_failure["path"].endswith("/bad-op")

    response = client.get("/api/reports/monthly?month=bad")
    assert response.status_code == 400
    assert response.get_json()["error"] == "month must be in YYYY-MM format."


def test_delete_account_route_requires_login(client):
    response = client.delete("/api/auth/me")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Login required."


def test_reset_password_route_delegates_to_user_service(client, app):
    class UserService:
        def reset_password(self, payload):
            return {"message": f"reset {payload['token']}"}

    app.extensions["services"]["user_service"] = UserService()

    response = client.post("/api/auth/reset-password", json={"token": "abc123", "password": "NewPassword123"})

    assert response.status_code == 200
    assert response.get_json()["data"] == {"message": "reset abc123"}
