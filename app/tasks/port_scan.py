import socket
from app.celery_app import celery
from ..infra.models import TaskRun
from ..schemas import PortScanRequest


def _is_port_open(domain: str, port: int, timeout_s: float) -> bool:
    """Check if a specific port is open on the given domain."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            result = s.connect_ex((domain, port))
            return result == 0
    except Exception:
        return False


@celery.task(name="net.port_scan")
def port_scan(domain: str, from_port: int, to_port: int, timeout_s: float) -> list[int]:
    """Scan TCP ports in [from_port, to_port] and return the list of open ports."""
    open_ports: list[int] = []

    for port in range(int(from_port), int(to_port) + 1):
        if _is_port_open(domain, port, timeout_s):
            open_ports.append(port)

    return open_ports


def enqueue_port_scan_task(payload: PortScanRequest, db) -> dict:
    """
    Enqueue port scan task and create database record.

    Args:
        payload: PortScanRequest schema object with validated data
        db: Database session

    Returns:
        dict: Task information including task_id and status
    """
    data = payload.model_dump()
    res = port_scan.apply_async(kwargs=data)

    tr = TaskRun(
        id=res.id,
        name="net.port_scan",
        status="PENDING",
        kwargs_json=data,
    )
    db.add(tr)
    db.commit()
    return {"task_id": res.id, "status": "queued", "name": "net.port_scan"}
