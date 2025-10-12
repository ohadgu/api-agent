import logging
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
from app.celery_app import celery
from ..infra.models import TaskRun
from ..schemas import HTTPRequest


logger = logging.getLogger(__name__)


def _build_url(domain: str, port: int, path: str) -> str:
    """Build URL from pre-validated components."""
    if port == 80:
        return f"http://{domain}{path}"
    elif port == 443:
        return f"https://{domain}{path}"
    else:
        return f"http://{domain}:{port}{path}"


@celery.task(name="net.http_request")
def http_request(
    method: str,
    domain: str,
    port: int,
    path: str,
    body: dict | None,
    params: dict | None,
    timeout_s: float = 8.0,
):
    """
    Perform HTTP request with pre-validated inputs from Pydantic schema.
    Always returns the response body text.

    Note: All input validation is done at the API boundary via Pydantic,
    so this function assumes all inputs are already validated and safe.
    """
    # Build URL from pre-validated components
    url = _build_url(domain, port, path)
    logger.info(f"Making {method} request to: {url}")

    # Prepare request arguments
    request_kwargs = {
        'url': url,
        'timeout': timeout_s,
        'params': params
    }

    # Add body for POST, PUT requests (methods that typically have bodies)
    if method in ["POST", "PUT"] and body is not None:
        request_kwargs['json'] = body

    # Make HTTP request with error handling
    try:
        request_method = getattr(requests, method.lower())
        resp = request_method(**request_kwargs)
        resp.raise_for_status()

        logger.info(f"Request successful: {resp.status_code} from {url}")

        # Always return just the response text
        return resp.text

    except Timeout:
        error_msg = f"Request timeout after {timeout_s}s for {url}"
        logger.warning(error_msg)
        raise RequestException(error_msg)

    except ConnectionError as e:
        error_msg = f"Connection failed to {url}: {e}"
        logger.warning(error_msg)
        raise RequestException(error_msg)

    except HTTPError as e:
        # Safely extract status code from the exception or fallback to the exception string
        status_code = getattr(getattr(e, 'response', None), 'status_code', None)
        if status_code is None:
            # Try to extract from the exception string (e.g., '404 Not Found')
            import re
            match = re.search(r'(\d{3})', str(e))
            status_code = match.group(1) if match else 'unknown'
        error_msg = f"HTTP error {status_code} from {url}"
        logger.warning(error_msg)
        raise RequestException(error_msg)

    except RequestException as e:
        error_msg = f"Request failed to {url}: {e}"
        logger.error(error_msg)
        raise
    
    except Exception as e:
        error_msg = f"Unexpected error requesting {url}: {e}"
        logger.error(error_msg)
        raise RequestException(error_msg)


def enqueue_http_request(payload: HTTPRequest, db) -> dict:
    """
    Enqueue HTTP request task and create database record.

    Args:
        payload: HTTPRequest schema object with validated data
        db: Database session

    Returns:
        dict: Task information including task_id and status
    """
    data = payload.model_dump()
    url = _build_url(data["domain"], data["port"], data["path"])

    result = http_request.apply_async(kwargs=data)

    tr = TaskRun(
        id=result.id,
        name="net.http_request",
        status="PENDING",
        kwargs_json={
            "method": data["method"],
            "domain": data["domain"],
            "port": data["port"],
            "path": data["path"],
            "url": url,
            "timeout_s": data["timeout_s"],
        },
    )
    db.add(tr)
    db.commit()
    return {"task_id": result.id, "status": "queued", "name": "net.http_request", "url": url}
