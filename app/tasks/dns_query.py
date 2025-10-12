import socket
import logging
from app.celery_app import celery
from ..infra.models import TaskRun


logger = logging.getLogger(__name__)


def _resolve(domain: str) -> list[str]:
    """Return unique A/AAAA addresses for a domain using stdlib only."""
    try:
        infos = socket.getaddrinfo(domain, None)  # both IPv4/IPv6
        ip_set = set()
        for family, _, _, _, sockaddr in infos:
            ip = sockaddr[0]
            ip_set.add(ip)
        return list(ip_set)

    except socket.gaierror as e:
        logger.warning(f"DNS resolution failed for domain '{domain}': {e}")
        raise ValueError(f"Failed to resolve domain '{domain}': {e}")

    except socket.error as e:
        logger.error(f"Socket error while resolving '{domain}': {e}")
        raise ValueError(f"Network error while resolving '{domain}': {e}")

    except Exception as e:
        logger.error(f"Unexpected error resolving '{domain}': {e}")
        raise ValueError(f"Unexpected error resolving '{domain}': {e}")


@celery.task(name="net.dns_query")
def dns_query(domain: str):
    """
    Resolve domain to IP addresses.

    Parameters:
        domain (str): Domain name to resolve

    Returns:
        dict: Contains domain, list of IPs, and primary IP

    Raises:
        ValueError: If domain resolution fails
    """
    try:
        ips = _resolve(domain)
        result = {"domain": domain, "ips": ips, "ip_count": len(ips)}
        return result

    except ValueError:
        # Re-raise ValueError from _resolve with original message
        raise

    except Exception as e:
        logger.error(f"Unexpected error in dns_query for '{domain}': {e}")
        raise ValueError(f"DNS query failed for '{domain}': {e}")


def enqueue_dns_query(domain: str, db) -> dict:
    """
    Enqueue DNS query task and create database record.

    Args:
        domain: Domain name to query
        db: Database session

    Returns:
        dict: Task information including task_id and status
    """
    result = dns_query.apply_async(args=[domain])
    tr = TaskRun(id=result.id, name=dns_query.name, status="PENDING", args_json=[domain])
    db.add(tr)
    db.commit()
    return {"task_id": result.id, "status": "queued", "name": dns_query.name, "domain": domain}
