from budget_tracker_api.errors import ApiError


def test_api_error_accepts_custom_status_code():
    error = ApiError("Service unavailable.", status_code=503)

    assert error.message == "Service unavailable."
    assert error.status_code == 503
