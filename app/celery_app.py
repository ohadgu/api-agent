import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Optional
from celery import Celery, signals
from app.infra.db import SessionLocal, init_db
from app.infra.models import TaskRun
import os

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Celery application
# -----------------------------------------------------------------------------
celery = Celery(
    "agents",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery.conf.update(
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_default_queue="default",
    task_track_started=True,
    task_send_sent_event=True,  # Send task-sent events
    worker_send_task_events=True,  # Enable worker to send events
)

# Make sure worker can find tasks under app/tasks
celery.autodiscover_tasks(packages=["app"], related_name="tasks")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _json_cap(obj: Any, max_len: int = 4000) -> Optional[dict]:
    """Serialize to JSON safely; cap very large results."""
    try:
        s = json.dumps(obj, default=str)
        if len(s) > max_len:
            return {"_truncated": True, "_approx_len": len(s)}
        # Return the original object if it's serializable and not too large
        return obj if isinstance(obj, dict) else {"result": obj}
    except Exception:
        return {"_unserializable": True}


def get_current_time():
    time_zone = os.getenv("TIMEZONE", "Asia/Jerusalem")
    return datetime.now(ZoneInfo(time_zone))

# -----------------------------------------------------------------------------
# Signals: initialize DB and track task lifecycle
# -----------------------------------------------------------------------------
@signals.worker_ready.connect
def _on_worker_ready(**_: Any) -> None:
    logger.info("worker_ready signal received, initializing database")
    init_db()


@signals.task_prerun.connect
def _on_task_prerun(sender=None, task_id: str | None = None, task=None, **_: Any) -> None:
    logger.info(f"task_prerun signal received for task_id: {task_id}")
    if not task_id:
        logger.warning("task_prerun called without task_id")
        return

    try:
        now = get_current_time()
        with SessionLocal() as db:
            # Query for existing record or create new one
            tr = db.query(TaskRun).filter(TaskRun.id == task_id).first()
            if not tr:
                tr = TaskRun(id=task_id)
                db.add(tr)

            tr.name = getattr(sender, "name", tr.name) or "unknown"
            tr.status = "STARTED"
            tr.started_at = now
            tr.queue = "default"

            req = getattr(task, "request", None)
            tr.args_json = _json_cap(getattr(req, "args", None))
            tr.kwargs_json = _json_cap(getattr(req, "kwargs", None))

            db.commit()
            logger.info(f"Task {task_id} status updated to STARTED in database")
    except Exception as e:
        logger.error(f"Failed to update task {task_id} in prerun: {e}", exc_info=True)


@signals.task_postrun.connect
def _on_task_postrun(task_id: str | None = None, state: str | None = None, task=None, retval: Any = None, **_: Any) -> None:
    logger.info(f"task_postrun signal received for task_id: {task_id}, state: {state}")
    if not task_id:
        return

    try:
        now = get_current_time()
        with SessionLocal() as db:
            tr = db.query(TaskRun).filter(TaskRun.id == task_id).first()
            if not tr:
                logger.warning(f"Task {task_id} not found in postrun")
                return

            tr.finished_at = now
            tr.status = "SUCCESS" if state == "SUCCESS" else (state or tr.status)

            if tr.started_at:
                tr.duration_ms = int((now - tr.started_at).total_seconds() * 1000)

            if state == "SUCCESS" and retval is not None:
                tr.result_json = _json_cap(retval)
                tr.error = None
            
            db.commit()
            logger.info(f"Task {task_id} status updated to {tr.status} in database")
    except Exception as e:
        logger.error(f"Failed to update task {task_id} in postrun: {e}", exc_info=True)


@signals.task_failure.connect
def _on_task_failure(task_id: str | None = None, exception: BaseException | None = None, **_: Any) -> None:
    logger.info(f"task_failure signal received for task_id: {task_id}")
    if not task_id:
        return

    try:
        now = get_current_time()
        with SessionLocal() as db:
            tr = db.query(TaskRun).filter(TaskRun.id == task_id).first()
            if not tr:
                logger.warning(f"Task {task_id} not found in failure handler")
                return

            tr.finished_at = now
            tr.status = "FAILURE"
            if tr.started_at:
                tr.duration_ms = int((now - tr.started_at).total_seconds() * 1000)
            tr.error = repr(exception)[:2000] if exception else "UNKNOWN_ERROR"
            if tr.result_json:
                tr.result_json = None  # Clear any partial result on failure
            
            db.commit()
            logger.info(f"Task {task_id} status updated to FAILURE in database")
    except Exception as e:
        logger.error(f"Failed to update task {task_id} in failure handler: {e}", exc_info=True)
