from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette import status
from ..infra.db import get_db
from ..schemas.http_request import HTTPRequest
from ..schemas.port_scan_request import PortScanRequest
from ..schemas.process_tree_request import ProcessTreeRequest
from ..schemas.dns_query_request import DNSQueryRequest
from ..schemas.registry_request import RegistryRequest
from ..schemas.http_server_request import HTTPServerRequest
from ..tasks.http_request import enqueue_http_request
from ..tasks.port_scan import enqueue_port_scan_task
from ..tasks.dns_query import enqueue_dns_query
from ..tasks.process_tree import execute_process_tree_with_error_handling
from ..tasks.registry_action import enqueue_registry_action
from .task_utils import get_task_result

# Import dynamic HTTP server functions
from ..infra.dynamic_http_server import (
    create_dynamic_http_server,
    get_http_server,
    cleanup_expired_servers
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Define the dependency type annotation once at module level
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


@router.post("/dns", summary="Enqueue DNS Query", status_code=status.HTTP_202_ACCEPTED)
def enqueue_dns(payload: DNSQueryRequest, db: db_dependency):
    """Enqueue DNS query with Pydantic validation."""
    try:
        return enqueue_dns_query(payload.domain, db)
    except Exception as e:
        return {"error": f"Failed to enqueue DNS query: {str(e)}", "status": "ERROR"}


@router.post("/http/request", summary="Enqueue HTTP Request", status_code=status.HTTP_202_ACCEPTED)
def enqueue_http(db: db_dependency, payload: HTTPRequest):
    """Enqueue HTTP request with Pydantic validation. Supports GET, POST, PUT, and DELETE methods."""
    try:
        return enqueue_http_request(payload, db)
    except Exception as e:
        return {"error": f"Failed to enqueue HTTP request: {str(e)}", "status": "ERROR"}


@router.post("/ports/scan", summary="Enqueue Port Scan", status_code=status.HTTP_202_ACCEPTED)
def enqueue_port_scan(payload: PortScanRequest, db: db_dependency):
    """Enqueue port scan task with validation."""
    try:
        return enqueue_port_scan_task(payload, db)
    except Exception as e:
        return {"error": f"Failed to enqueue port scan: {str(e)}", "status": "ERROR"}


@router.post("/process/tree", summary="Get Process Tree from API Container", status_code=status.HTTP_200_OK)
def get_process_tree(payload: ProcessTreeRequest, db: db_dependency):
    """Get process tree directly from the API container (executes immediately)."""
    try:
        return execute_process_tree_with_error_handling(payload.pid, db)
    except Exception as e:
        return {"error": f"Failed to get process tree: {str(e)}", "status": "ERROR"}


@router.post("/registry/action", summary="Enqueue Registry Action", status_code=status.HTTP_202_ACCEPTED)
def enqueue_registry(payload: RegistryRequest, db: db_dependency):
    """Enqueue registry action (GET/SET/DELETE) with validation."""
    try:
        return enqueue_registry_action(
            action=payload.action,
            key=payload.key,
            value_name=payload.value_name,
            value_data=payload.value_data,
            db=db
        )
    except Exception as e:
        return {"error": f"Failed to enqueue registry action: {str(e)}", "status": "ERROR"}


@router.post("/http/server", summary="Create HTTP Server", status_code=status.HTTP_201_CREATED)
def create_http_server(payload: HTTPServerRequest):
    """Create an HTTP server that serves content and tracks who accesses it."""
    try:
        # Create the server immediately (no Celery task needed)
        server_id = create_dynamic_http_server(
            page_uri=payload.page_uri,
            response_data=payload.response_data,
            timeout_seconds=payload.timeout_seconds
        )

        server = get_http_server(server_id)
        if server:
            return server.get_results()
        else:
            return {"error": "Failed to create server"}

    except Exception as e:
        return {"error": f"Failed to create HTTP server: {str(e)}", "status": "ERROR"}
