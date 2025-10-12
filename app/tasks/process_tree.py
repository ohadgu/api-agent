# import psutil
# from typing import Dict, Any, Optional
# from app.celery_app import celery
# # from .base import mark_started, mark_success, mark_failure


import psutil
from ..schemas import ProcessTreeRequest


def process_tree_from_root(process: psutil.Process) -> list[dict[str, int | str]]:
    process_tree = []
    while process is not None:
        try:
            process_tree.append({"pid": process.pid, "name": process.name()})
            process = process.parent()
        except Exception:
            break

    return process_tree[::-1]


# def enqueue_process_tree(payload: ProcessTreeRequest, db) -> dict:
#     pid = payload.pid
#     try:
#         process = psutil.Process(pid)
#     except psutil.NoSuchProcess:
#         raise ValueError(f"Process with PID {pid} not found")
    
#     try:
#         process_tree = process_tree_from_root(process)
#         return {"order": "root --> child", "process_tree": process_tree}
#     except ValueError:
#         raise
#     except Exception as e:
#         raise Exception(f"Failed to get process tree for PID '{pid}': {e}")


# def _get_process_info(pid: int) -> Optional[Dict[str, Any]]:
#     """Get basic information about a process."""
#     try:
#         proc = psutil.Process(pid)
#         return {
#             "pid": proc.pid,
#             "name": proc.name(),
#             "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "",
#             "status": proc.status(),
#             "create_time": proc.create_time(),
#             "memory_percent": round(proc.memory_percent(), 2),
#             "cpu_percent": round(proc.cpu_percent(), 2),
#         }
#     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
#         return None


# def _build_tree_recursive(proc: psutil.Process) -> Optional[Dict[str, Any]]:
#     """Recursively build the process tree for a given process."""
#     proc_info = _get_process_info(proc.pid)
#     if not proc_info:
#         return None

#     children = []
#     try:
#         for child in proc.children(recursive=False):
#             child_tree = _build_tree_recursive(child)
#             if child_tree:
#                 children.append(child_tree)
#     except (psutil.NoSuchProcess, psutil.AccessDenied):
#         pass

#     proc_info["children"] = children
#     return proc_info


# def _build_process_tree(root_pid: int) -> Dict[str, Any]:
#     """Build a process tree starting from the root PID."""
#     try:
#         root_proc = psutil.Process(root_pid)
#     except (psutil.NoSuchProcess, psutil.AccessDenied):
#         raise ValueError(f"Process with PID {root_pid} not found or access denied")

#     tree = _build_tree_recursive(root_proc)
#     if not tree:
#         raise ValueError(f"Unable to get information for process {root_pid}")

#     return tree


# def _count_processes(tree: Dict[str, Any]) -> int:
#     """Count total number of processes in the tree."""
#     if not tree:
#         return 0

#     count = 1  # Count the current process
#     for child in tree.get("children", []):
#         count += _count_processes(child)

#     return count


# @celery.task(bind=True, name="system.process_tree")
# def process_tree(self, pid: int):
#     """Get process tree starting from the given PID."""
#     task_id = self.request.id
#     mark_started(task_id, "system.process_tree")

#     try:
#         # Validate PID
#         if not isinstance(pid, int) or pid <= 0:
#             raise ValueError(f"Invalid PID: {pid}. PID must be a positive integer.")

#         # Build the process tree
#         tree = _build_process_tree(pid)

#         # Prepare the result
#         result = {
#             "root_pid": pid,
#             "tree": tree,
#             "total_processes": _count_processes(tree),
#             "container": "worker"
#         }

#         mark_success(task_id, result)
#         return result

#     except ValueError as e:
#         mark_failure(task_id, e)
#         raise
#     except Exception as e:
#         mark_failure(task_id, e)
#         raise Exception(f"Failed to get process tree: {str(e)}")


# def execute_process_tree(pid: int, db) -> dict:
#     """
#     Execute process tree directly on API container and create database record.

#     Args:
#         pid: Process ID to build tree from
#         db: Database session

#     Returns:
#         dict: Task information including task_id, status, and result
#     """
#     import time
#     from ..infra.models import TaskRun

#     tree = _build_process_tree(pid)
#     result = {
#         "root_pid": pid,
#         "tree": tree,
#         "total_processes": _count_processes(tree),
#         "container": "api"
#     }

#     tr = TaskRun(
#         id=f"sync-{pid}-{int(time.time())}",
#         name="system.process_tree",
#         status="SUCCESS",
#         kwargs_json={"pid": pid},
#         result_json=result
#     )
#     db.add(tr)
#     db.commit()

#     return {"task_id": tr.id, "status": "SUCCESS", "result": result, "name": "system.process_tree"}


# def execute_process_tree_with_error_handling(pid: int, db) -> dict:
#     """
#     Execute process tree with comprehensive error handling and database recording.

#     Args:
#         pid: Process ID to build tree from
#         db: Database session

#     Returns:
#         dict: Task information including task_id, status, and result/error
#     """
#     import time
#     from ..infra.models import TaskRun

#     try:
#         tree = _build_process_tree(pid)
#         result = {
#             "root_pid": pid,
#             "tree": tree,
#             "total_processes": _count_processes(tree),
#             "container": "api"
#         }

#         tr = TaskRun(
#             id=f"sync-{pid}-{int(time.time())}",
#             name="system.process_tree",
#             status="SUCCESS",
#             kwargs_json={"pid": pid},
#             result_json=result
#         )
#         db.add(tr)
#         db.commit()

#         return {"task_id": tr.id, "status": "SUCCESS", "result": result, "name": "system.process_tree"}

#     except ValueError as e:
#         tr = TaskRun(
#             id=f"sync-{pid}-{int(time.time())}",
#             name="system.process_tree",
#             status="FAILURE",
#             kwargs_json={"pid": pid},
#             error=str(e)
#         )
#         db.add(tr)
#         db.commit()
#         return {"task_id": tr.id, "status": "FAILURE", "error": str(e), "name": "system.process_tree"}
#     except Exception as e:
#         tr = TaskRun(
#             id=f"sync-{pid}-{int(time.time())}",
#             name="system.process_tree",
#             status="FAILURE",
#             kwargs_json={"pid": pid},
#             error=f"Failed to get process tree: {str(e)}"
#         )
#         db.add(tr)
#         db.commit()
#         return {"task_id": tr.id, "status": "FAILURE", "error": f"Failed to get process tree: {str(e)}", "name": "system.process_tree"}
