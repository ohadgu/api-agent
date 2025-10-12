from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
import psutil
import platform
from ..infra.db import get_db
from ..infra.dynamic_http_server import create_dynamic_http_server, get_http_server
from ..schemas import (HTTPRequest, PortScanRequest, ProcessTreeRequest, 
                       DNSQueryRequest, RegistryRequest, HTTPServerRequest)
from ..tasks.http_request import enqueue_http_request
from ..tasks.port_scan import enqueue_port_scan_task
from ..tasks.dns_query import enqueue_dns_query
from ..tasks.process_tree import process_tree_from_root
from ..tasks.registry_action import registry_action
from ..tasks.task_result import get_task_result


router = APIRouter(prefix="/tasks", tags=["Tasks"])


db_dependency = Annotated[Session, Depends(get_db)]


@router.get("/result/{task_id}", summary="Get Task Result and Status", status_code=status.HTTP_200_OK)
def get_result(task_id: str, db: db_dependency) -> dict:
    """Get task result and status, syncing with database if needed."""
    if not task_id or len(task_id.strip()) == 0:
        return {"error": "Invalid task_id"}
    try:
        return get_task_result(task_id, db)
    except Exception as e:
        return {"error": f"Failed to get task result: {str(e)}", "status": "ERROR"}


@router.post("/dns", summary="Enqueue DNS Query", status_code=status.HTTP_200_OK)
def enqueue_dns(payload: DNSQueryRequest, db: db_dependency):
    """Enqueue DNS query with Pydantic validation."""
    try:
        return enqueue_dns_query(payload.domain, db)
    except Exception as e:
        return {"error": f"Failed to enqueue DNS query: {str(e)}", "status": "ERROR"}


@router.post("/http/request", summary="Enqueue HTTP Request", status_code=status.HTTP_200_OK)
def enqueue_http(db: db_dependency, payload: HTTPRequest):
    """Enqueue HTTP request with Pydantic validation. Supports GET, POST, PUT, and DELETE methods."""
    try:
        return enqueue_http_request(payload, db)
    except Exception as e:
        return {"error": f"Failed to enqueue HTTP request: {str(e)}", "status": "ERROR"}


@router.post("/ports/scan", summary="Enqueue Port Scan", status_code=status.HTTP_200_OK)
def enqueue_port_scan(payload: PortScanRequest, db: db_dependency):
    """Enqueue port scan task with validation."""
    try:
        return enqueue_port_scan_task(payload, db)
    except Exception as e:
        return {"error": f"Failed to enqueue port scan: {str(e)}", "status": "ERROR"}


@router.post("/process/tree", summary="Get Process Tree from API Container", status_code=status.HTTP_200_OK)
def get_process_tree(payload: ProcessTreeRequest, db: db_dependency):
    """Get process tree directly from the API container (executes immediately)."""
    pid = payload.pid
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        raise ValueError(f"Process with PID {pid} not found")
    
    try:
        process_tree = process_tree_from_root(process)
        return {"order": "root --> child", "process_tree": process_tree}
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Failed to get process tree for PID '{pid}': {e}")


@router.post("/registry/action", summary="Enqueue Registry Action (Windows only)", status_code=status.HTTP_200_OK)
def registry_action_task(payload: RegistryRequest):
    """Make registry action (GET/SET/DELETE)."""
    if platform.system() != "Windows":
        return {"error": f"Registry operations are only supported on Windows systems. Current OS: {platform.system()}", "status": "ERROR"}
    
    data = payload.model_dump()
    try:
        action_message = registry_action(**data)
        return registry_action(**data, **action_message)
    except Exception as e:
        return {"error": f"Failed to execute registry action: {str(e)}", "status": "ERROR"}


@router.post("/http/server", summary="Create HTTP Server", status_code=status.HTTP_200_OK)
def create_http_server(payload: HTTPServerRequest):
    """Create an HTTP server that serves content and tracks who accesses it."""
    try:
        # Create the server immediately (no Celery task needed)
        data = payload.model_dump()
        server_id = create_dynamic_http_server(**data)
        server = get_http_server(server_id)
        if server:
            return server.get_results()
        else:
            return {"error": "Failed to create server"}

    except Exception as e:
        return {"error": f"Failed to create HTTP server: {str(e)}", "status": "ERROR"}
