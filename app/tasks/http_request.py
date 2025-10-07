from typing import Optional, Dict, Any
import logging

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError

from ..celery_app import celery
from ..infra.models import TaskRun

logger = logging.getLogger(__name__)


def _build_url(domain: str, port: int, path: str, https: bool = False) -> str:
    """Build URL from pre-validated components."""
    scheme = "https" if https or port == 443 else "http"
    base = f"{scheme}://{domain}"

    # For HTTPS, omit port 443
    if scheme == "https":
        if port != 443:
            base = f"{base}:{port}"
    # For HTTP, omit port 80
    else:
        if port != 80:
            base = f"{base}:{port}"

    return base + path


@celery.task(name="net.http_request")
def http_request(
    method: str,
    domain: str,
    port: int,
    path: str,
    body: Optional[Dict[str, Any] | str] = None,
    headers: Optional[Dict[str, str]] = None,
    https: bool = False,
    timeout_s: float = 8.0,
    params: Optional[Dict[str, str]] = None,
):
    """
    Perform HTTP request with pre-validated inputs from Pydantic schema.
    Always returns the response body text.

    Note: All input validation is done at the API boundary via Pydantic,
    so this function assumes all inputs are already validated and safe.
    """
    # Build URL from pre-validated components
    url = _build_url(domain, port, path, https)
    logger.info(f"Making {method} request to: {url}")

    # Prepare request arguments
    request_kwargs = {
        'url': url,
        'timeout': timeout_s,
        'headers': headers or {},
        'params': params
    }

    # Add body for POST, PUT requests (methods that typically have bodies)
    if method in ["POST", "PUT"] and body is not None:
        if isinstance(body, dict):
            request_kwargs['json'] = body
        else:
            request_kwargs['data'] = body

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


def enqueue_http_request(payload, db) -> dict:
    """
    Enqueue HTTP request task and create database record.

    Args:
        payload: HTTPRequest schema object with validated data
        db: Database session

    Returns:
        dict: Task information including task_id and status
    """
    url = payload.build_url()

    res = http_request.apply_async(
        kwargs={
            "method": payload.method,
            "domain": payload.domain,
            "port": payload.port,
            "path": payload.path,
            "body": payload.body,
            "headers": payload.headers,
            "https": payload.https,
            "timeout_s": payload.timeout_s,
            "params": payload.params,
        }
    )
    tr = TaskRun(
        id=res.id,
        name="net.http_request",
        status="PENDING",
        kwargs_json={
            "method": payload.method,
            "domain": payload.domain,
            "port": payload.port,
            "path": payload.path,
            "https": payload.https,
            "url": url,
            "timeout_s": payload.timeout_s,
        },
    )
    db.add(tr)
    db.commit()
    return {"task_id": res.id, "status": "queued", "name": "net.http_request", "url": url}
