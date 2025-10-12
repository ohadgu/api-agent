"""
Task result handling utilities for API endpoints.

This module contains helper functions for processing Celery task results
and syncing task state with the database.
"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from ..infra.db import get_db
from ..infra.models import TaskRun
# from app.celery_app import celery

# Define the dependency type annotation consistent with api_endpoints.py
db_dependency = Annotated[Session, Depends(get_db)]


#
# def sync_task_to_db(db: db_dependency, task_id: str, status: str, result_json=None, error=None):
#     """
#     Helper function to sync task data to database.
#
#     Args:
#         db: Database session
#         task_id: Celery task ID
#         status: Task status (PENDING, STARTED, SUCCESS, FAILURE)
#         result_json: Task result data (for SUCCESS status)
#         error: Error message (for FAILURE status)
#     """
#     try:
#         tr = db.get(TaskRun, task_id)
#         if tr:
#             tr.status = status
#             if result_json is not None:
#                 tr.result_json = result_json
#             if error is not None:
#                 tr.error = error
#             if status == "SUCCESS":
#                 tr.error = None  # Clear previous errors
#             elif status == "FAILURE":
#                 tr.result_json = None  # Clear previous results
#             db.commit()
#     except Exception as e:
#         print(f"Warning: Failed to update database for task {task_id}: {e}")
#         db.rollback()
#
#
# def handle_failure_state(res, payload: dict, db: db_dependency, task_id: str):
#     """
#     Handle FAILURE state for task result.
#
#     Args:
#         res: Celery AsyncResult object
#         payload: Response payload to update
#         db: Database session
#         task_id: Celery task ID
#     """
#     payload["error"] = str(res.info) if res.info else "Unknown error"
#     # sync_task_to_db(db, task_id, "FAILURE", error=payload["error"])
#
#
# def handle_success_state(res, payload: dict, db: db_dependency, task_id: str):
#     """
#     Handle SUCCESS state for task result.
#
#     Args:
#         res: Celery AsyncResult object
#         payload: Response payload to update
#         db: Database session
#         task_id: Celery task ID
#     """
#     try:
#         payload["result"] = res.result
#         val = payload["result"]
#         result_json = val if isinstance(val, dict) else {"result": val}
#         sync_task_to_db(db, task_id, "SUCCESS", result_json=result_json)
#     except Exception as e:
#         # If getting result fails, treat as failure
#         payload["error"] = f"Failed to retrieve result: {str(e)}"
#         payload["status"] = "FAILURE"
#         sync_task_to_db(db, task_id, "FAILURE", error=payload["error"])
#

def get_task_result(task_id: str, db: db_dependency) -> dict:
    """
    Get task result and handle state synchronization.

    Args:
        task_id: Celery task ID
        db: Database session

    Returns:
        dict: Task status and result/error information
    """
    try:
        tr = db.get(TaskRun, task_id)
        if not tr:
            return {"status": "UNKNOWN", "error": f"Task {task_id} not found in database"}

        status = tr.status
        payload = {"status": status}
        if status == "SUCCESS":
            payload["result"] = tr.result_json
        elif status == "FAILURE":
            payload["error"] = tr.error
        return payload

    except Exception as e:
        return {"status": "UNKNOWN", "error": f"Failed to retrieve task {task_id} from database: {str(e)}"}



# def get_task_result(task_id: str, db: db_dependency) -> dict:
#     """
#     Get task result and handle state synchronization.
#
#     Args:
#         task_id: Celery task ID
#         db: Database session
#
#     Returns:
#         dict: Task status and result/error information
#     """
#     res = celery.AsyncResult(task_id)
#     state = res.state
#     payload = {"status": state}
#
#     match state:
#         case "FAILURE":
#
#             handle_failure_state(res, payload, db, task_id)
#         case "SUCCESS":
#             handle_success_state(res, payload, db, task_id)
#         case _:  # Handle any other states (PENDING, STARTED, etc.)
#             sync_task_to_db(db, task_id, state)
#     return payload

