from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

from budget_tracker_api.blueprints.agents import agents_bp
from budget_tracker_api.blueprints.analytics import analytics_bp
from budget_tracker_api.blueprints.auth import auth_bp
from budget_tracker_api.blueprints.expenses import expenses_bp
from budget_tracker_api.blueprints.health import health_bp
from budget_tracker_api.blueprints.predictions import predictions_bp
from budget_tracker_api.blueprints.recurring import recurring_bp
from budget_tracker_api.blueprints.reports import reports_bp
from budget_tracker_api.blueprints.settings import settings_bp
from budget_tracker_api.config import Config
from budget_tracker_api.db import close_db, get_db, init_db
from budget_tracker_api.errors import ApiError
from budget_tracker_api.logging_config import configure_logging, register_request_logging
from budget_tracker_api.repositories.agent_run_repository import AgentRunRepository
from budget_tracker_api.repositories.expense_repository import ExpenseRepository
from budget_tracker_api.repositories.recurring_repository import RecurringRepository
from budget_tracker_api.repositories.settings_repository import SettingsRepository
from budget_tracker_api.security import register_request_guards, should_expose_error_details
from budget_tracker_api.services.agent_service import AgentService
from budget_tracker_api.services.agent_memory_service import AgentMemoryService
from budget_tracker_api.services.analytics_service import AnalyticsService
from budget_tracker_api.services.automation_scheduler import AutomationScheduler
from budget_tracker_api.services.automation_service import AutomationService
from budget_tracker_api.services.email_service import EmailService
from budget_tracker_api.services.expense_service import ExpenseService
from budget_tracker_api.services.fastmcp_client_service import FastMcpClientService
from budget_tracker_api.services.ollama_client import OllamaClient
from budget_tracker_api.services.prediction_service import PredictionService
from budget_tracker_api.services.recurring_service import RecurringService
from budget_tracker_api.services.report_service import ReportService
from budget_tracker_api.services.settings_service import SettingsService


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    configure_logging(app)

    if app.config["CORS_ORIGINS"]:
        CORS(
            app,
            resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
            supports_credentials=True,
        )
    app.teardown_appcontext(close_db)
    register_request_guards(app)
    register_request_logging(app)

    with app.app_context():
        init_db()
        _register_services(app)

    _register_blueprints(app)
    _register_error_handlers(app)
    app.logger.info("Application startup complete.")
    return app


def _register_services(app: Flask) -> None:
    repository = ExpenseRepository(get_db)
    settings_repository = SettingsRepository(get_db)
    recurring_repository = RecurringRepository(get_db)
    agent_run_repository = AgentRunRepository(get_db)
    settings_service = SettingsService(settings_repository)
    expense_service = ExpenseService(repository)
    analytics_service = AnalyticsService(
        repository,
        settings_service.get_monthly_budget,
        settings_service.get_monthly_income,
    )
    prediction_service = PredictionService(repository, settings_service.get_monthly_budget)
    report_service = ReportService(
        repository,
        settings_service.get_monthly_budget,
        settings_service.get_monthly_income,
        app.config["GENERATED_REPORTS_DIR"],
    )
    recurring_service = RecurringService(recurring_repository, expense_service)
    ollama_client = OllamaClient(
        app.config["OLLAMA_BASE_URL"],
        app.config["OLLAMA_MODEL"],
        app.config["OLLAMA_TIMEOUT_SECONDS"],
    )
    email_service = EmailService(
        app.config["SMTP_HOST"],
        app.config["SMTP_PORT"],
        app.config["SMTP_USERNAME"],
        app.config["SMTP_PASSWORD"],
        app.config["SMTP_USE_TLS"],
        app.config["REPORT_EMAIL_TO"],
    )
    agent_memory_service = AgentMemoryService(app.config["AGENT_MEMORY_PATH"])
    mcp_client_service = FastMcpClientService(
        python_executable=str(Path(app.root_path).parent / ".venv" / "Scripts" / "python.exe"),
        backend_root=Path(app.root_path).parent,
        log_file_path=app.config["LOG_FILE_PATH"].with_name("fastmcp-server.log"),
    )
    agent_service = AgentService(
        ollama_client,
        analytics_service,
        prediction_service,
        recurring_service,
        report_service,
        expense_service,
        settings_service,
        agent_run_repository,
        agent_memory_service=agent_memory_service,
        mcp_tool_adapter=mcp_client_service,
    )
    automation_service = AutomationService(
        agent_service,
        report_service,
        email_service,
        agent_run_repository,
        recurring_service,
        analytics_service,
        app.config["MONTH_END_EMAIL_HOUR"],
        app.config["MONTH_END_EMAIL_MINUTE"],
    )
    agent_service.attach_automation_service(automation_service)
    app.extensions["services"] = {
        "expense_service": expense_service,
        "settings_service": settings_service,
        "analytics_service": analytics_service,
        "prediction_service": prediction_service,
        "report_service": report_service,
        "recurring_service": recurring_service,
        "agent_service": agent_service,
        "automation_service": automation_service,
        "email_service": email_service,
        "agent_memory_service": agent_memory_service,
    }
    if app.config["AUTOMATION_SCHEDULER_ENABLED"] and not app.testing:
        scheduler = AutomationScheduler(app, app.config["AUTOMATION_POLL_SECONDS"])
        scheduler.start()
        app.extensions["automation_scheduler"] = scheduler
        app.logger.info("Automation scheduler started with %s second poll interval.", app.config["AUTOMATION_POLL_SECONDS"])


def _register_blueprints(app: Flask) -> None:
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(recurring_bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        app.logger.warning("API error | type=%s message=%s path=%s", type(error).__name__, error.message, request.path)
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(404)
    def handle_not_found(_: Exception):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(500)
    def handle_internal_error(error: Exception):
        app.logger.exception("Unhandled server error.")
        payload = {"error": "Internal server error."}
        if should_expose_error_details(app):
            payload["details"] = str(error)
        return jsonify(payload), 500
