import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from celery import Celery, signals
from .infra.db import SessionLocal, init_db
from .infra.models import TaskRun

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


# -----------------------------------------------------------------------------
# Signals: initialize DB and track task lifecycle
# -----------------------------------------------------------------------------
@signals.worker_ready.connect
def _on_worker_ready(**_: Any) -> None:
    init_db()


@signals.task_prerun.connect
def _on_task_prerun(sender=None, task_id: str | None = None, task=None, **_: Any) -> None:
    if not task_id:
        logger.warning("task_prerun called without task_id")
        return

    try:
        now = datetime.now(timezone.utc)
        with SessionLocal.begin() as db:
            tr = db.get(TaskRun, task_id) or TaskRun(id=task_id)
            req = getattr(task, "request", None)

            tr.name = getattr(sender, "name", tr.name) or "unknown"
            tr.status = "STARTED"
            tr.started_at = now
            # Simplified: just use the default queue name since you're not using complex routing
            tr.queue = "default"
            tr.retries = getattr(req, "retries", 0)

            tr.args_json = _json_cap(getattr(req, "args", None))
            tr.kwargs_json = _json_cap(getattr(req, "kwargs", None))

            db.add(tr)
    except Exception as e:
        logger.error(f"Failed to update task {task_id} in prerun: {e}")


@signals.task_postrun.connect
def _on_task_postrun(task_id: str | None = None, state: str | None = None, task=None, retval: Any = None, **_: Any) -> None:
    if not task_id:
        return

    try:
        now = datetime.now(timezone.utc)
        with SessionLocal.begin() as db:
            tr = db.get(TaskRun, task_id)
            if not tr:
                logger.warning(f"Task {task_id} not found in postrun")
                return

            tr.finished_at = now
            tr.status = "SUCCESS" if state == "SUCCESS" else (state or tr.status)
            req = getattr(task, "request", None)
            tr.retries = getattr(req, "retries", tr.retries or 0)

            if tr.started_at:
                tr.duration_ms = int((now - tr.started_at).total_seconds() * 1000)

            if state == "SUCCESS" and retval is not None:
                tr.result_json = _json_cap(retval)
                tr.error = None
    except Exception as e:
        logger.error(f"Failed to update task {task_id} in postrun: {e}")


@signals.task_failure.connect
def _on_task_failure(task_id: str | None = None, exception: BaseException | None = None, **_: Any) -> None:
    if not task_id:
        return

    try:
        now = datetime.now(timezone.utc)
        with SessionLocal.begin() as db:
            tr = db.get(TaskRun, task_id)
            if not tr:
                logger.warning(f"Task {task_id} not found in failure handler")
                return

            tr.finished_at = now
            tr.status = "FAILURE"
            if tr.started_at:
                tr.duration_ms = int((now - tr.started_at).total_seconds() * 1000)
            tr.error = repr(exception)[:2000] if exception else "UNKNOWN_ERROR"
    except Exception as e:
        logger.error(f"Failed to update task {task_id} in failure handler: {e}")
