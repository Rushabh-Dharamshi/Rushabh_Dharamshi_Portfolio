import logging
import time

from flask import Blueprint, current_app, jsonify, request


agents_bp = Blueprint("agents", __name__, url_prefix="/api/agents")
logger = logging.getLogger(__name__)


def _service():
    return current_app.extensions["services"]["agent_service"]


def _automation_service():
    return current_app.extensions["services"]["automation_service"]


@agents_bp.post("/finance-briefing")
def start_finance_briefing():
    payload = request.get_json(silent=True) or {}
    task = str(payload.get("task", "")).strip()
    logger.info("Finance briefing requested | task_preview=%s", task[:120])
    job = _service().start_finance_briefing(payload, current_app._get_current_object())
    logger.info("Finance briefing queued | job_id=%s", job["id"])
    return jsonify({"data": job}), 202


@agents_bp.get("/finance-briefing/<job_id>")
def get_finance_briefing(job_id: str):
    started = time.perf_counter()
    job = _service().get_finance_briefing_job(job_id)
    logger.info(
        "Finance briefing status requested | job_id=%s status=%s duration_ms=%.1f",
        job_id,
        job.get("status"),
        (time.perf_counter() - started) * 1000,
    )
    return jsonify({"data": job})


@agents_bp.get("/workflows")
def list_workflows():
    logger.info("Listing agent workflows.")
    return jsonify({"data": _service().list_workflows()})


@agents_bp.get("/runs")
def list_runs():
    limit = request.args.get("limit", default=8, type=int)
    logger.info("Listing agent runs | limit=%s", limit)
    return jsonify({"data": _service().list_runs(limit)})


@agents_bp.post("/workflows/<workflow_name>/run")
def run_workflow(workflow_name: str):
    payload = request.get_json(silent=True) or {}
    logger.info("Workflow requested | workflow_name=%s", workflow_name)
    started = time.perf_counter()
    job = _service().start_workflow_run(workflow_name, payload, current_app._get_current_object())
    logger.info(
        "Workflow queued | workflow_name=%s duration_ms=%.1f job_id=%s",
        workflow_name,
        (time.perf_counter() - started) * 1000,
        job.get("id"),
    )
    return jsonify({"data": job}), 202


@agents_bp.get("/workflow-jobs/<job_id>")
def get_workflow_job(job_id: str):
    started = time.perf_counter()
    job = _service().get_workflow_job(job_id)
    logger.info(
        "Workflow status requested | job_id=%s status=%s duration_ms=%.1f",
        job_id,
        job.get("status"),
        (time.perf_counter() - started) * 1000,
    )
    return jsonify({"data": job})


@agents_bp.post("/automation/upcoming-bills-email")
def run_upcoming_bills_email_now():
    logger.info("Manual upcoming bills email dispatch requested.")
    started = time.perf_counter()
    result = _automation_service().run_upcoming_bills_email_now()
    logger.info(
        "Manual upcoming bills email dispatch completed | duration_ms=%.1f run_id=%s",
        (time.perf_counter() - started) * 1000,
        result.get("id"),
    )
    return jsonify({"data": result})


@agents_bp.post("/automation/month-end-email")
def run_month_end_email_now():
    logger.info("Manual month-end email dispatch requested.")
    started = time.perf_counter()
    result = _automation_service().run_month_end_email_now()
    logger.info(
        "Manual month-end email dispatch completed | duration_ms=%.1f run_id=%s",
        (time.perf_counter() - started) * 1000,
        result.get("id"),
    )
    return jsonify({"data": result})


@agents_bp.post("/bootstrap")
def run_bootstrap():
    logger.info("Automation bootstrap requested.")
    started = time.perf_counter()
    result = _automation_service().run_bootstrap_workflows_async(
        current_app._get_current_object()
    )
    logger.info(
        "Automation bootstrap accepted | duration_ms=%.1f existing_runs=%s",
        (time.perf_counter() - started) * 1000,
        len(result),
    )
    return jsonify({"data": result})


@agents_bp.post("/automation/refresh")
def refresh_automation_runs():
    payload = request.get_json(silent=True) or {}
    event_type = str(payload.get("event_type") or "finance_state_changed").strip() or "finance_state_changed"
    logger.info("Automation refresh requested | event_type=%s", event_type)
    started = time.perf_counter()
    jobs = _automation_service().queue_realtime_refresh(
        current_app._get_current_object(),
        event_type,
    )
    logger.info(
        "Automation refresh queued | event_type=%s duration_ms=%.1f jobs=%s",
        event_type,
        (time.perf_counter() - started) * 1000,
        len(jobs),
    )
    return jsonify({"data": jobs}), 202
