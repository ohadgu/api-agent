import socket
from ..celery_app import celery
from .base import task_tracker
from ..infra.models import TaskRun


def _is_port_open(host: str, port: int, timeout_s: float) -> bool:
    """Check if a specific port is open on the given host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


@celery.task(name="net.port_scan")
@task_tracker
def port_scan(
    host: str,
    from_port: int,
    to_port: int,
    timeout_s: float = 0.15,
) -> list[int]:
    """Scan TCP ports in [from_port, to_port] and return the list of open ports."""
    open_ports: list[int] = []

    for port in range(int(from_port), int(to_port) + 1):
        if _is_port_open(host, port, timeout_s):
            open_ports.append(port)

    return open_ports


def enqueue_port_scan_task(payload, db) -> dict:
    """
    Enqueue port scan task and create database record.

    Args:
        payload: PortScanRequest schema object with validated data
        db: Database session

    Returns:
        dict: Task information including task_id and status
    """
    res = port_scan.apply_async(
        kwargs={"host": payload.host, "from_port": payload.from_port, "to_port": payload.to_port, "timeout_s": payload.timeout_s}
    )
    tr = TaskRun(
        id=res.id,
        name="net.port_scan",
        status="PENDING",
        kwargs_json={"host": payload.host, "from_port": payload.from_port, "to_port": payload.to_port},
    )
    db.add(tr)
    db.commit()
    return {"task_id": res.id, "status": "queued", "name": "net.port_scan"}
