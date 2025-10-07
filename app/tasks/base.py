from datetime import datetime, timezone
from typing import Any, Optional
from functools import wraps
from ..infra.db import SessionLocal
from ..infra.models import TaskRun

def _now():
    return datetime.now(timezone.utc)

def mark_pending(task_id: str, name: str, args=None, kwargs=None):
    with SessionLocal.begin() as db:
        tr = db.get(TaskRun, task_id)
        if tr is None:
            tr = TaskRun(id=task_id, name=name, status="PENDING")
            db.add(tr)
        tr.status = "PENDING"
        tr.args_json = args if args is not None else tr.args_json
        tr.kwargs_json = kwargs if kwargs is not None else tr.kwargs_json

def mark_started(task_id: str, name: Optional[str] = None):
    with SessionLocal.begin() as db:
        tr = db.get(TaskRun, task_id)
        if tr is None:
            tr = TaskRun(id=task_id, name=name or "unknown", status="STARTED")
            db.add(tr)
        tr.status = "STARTED"
        tr.started_at = _now()
        if name:
            tr.name = name

def mark_success(task_id: str, result: Any):
    with SessionLocal.begin() as db:
        tr = db.get(TaskRun, task_id)
        if tr is None:
            return
        tr.finished_at = _now()
        tr.status = "SUCCESS"
        if tr.started_at:
            tr.duration_ms = int((tr.finished_at - tr.started_at).total_seconds() * 1000)
        tr.result_json = result if isinstance(result, dict) else {"result": result}

def mark_failure(task_id: str, exc: Exception):
    with SessionLocal.begin() as db:
        tr = db.get(TaskRun, task_id)
        if tr is None:
            return
        tr.finished_at = _now()
        tr.status = "FAILURE"
        if tr.started_at:
            tr.duration_ms = int((tr.finished_at - tr.started_at).total_seconds() * 1000)
        tr.error = repr(exc)[:2000]

def task_tracker(func):
    """Decorator that automatically tracks task execution lifecycle"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if this is a bound task (first arg is self with request)
        if args and hasattr(args[0], 'request') and hasattr(args[0].request, 'id'):
            # Bound task - first arg is self
            task_self = args[0]
            task_id = task_self.request.id
            task_name = getattr(task_self, 'name', func.__name__)
            func_args = args[1:]  # Skip self
        else:
            # Unbound task - need to get task context differently
            # For unbound tasks, we'll need the task_id passed as a parameter
            # or we skip tracking (fallback)
            return func(*args, **kwargs)

        try:
            mark_started(task_id, task_name)
            result = func(task_self, *func_args, **kwargs)
            mark_success(task_id, result)
            return result
        except Exception as exc:
            mark_failure(task_id, exc)
            raise

    return wrapper
