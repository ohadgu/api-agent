import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import Request
import uuid

logger = logging.getLogger(__name__)

# Global storage for active HTTP servers
_active_http_servers = {}
_http_server_logs = {}

class DynamicHTTPServer:
    """A dynamic HTTP server that creates tracked endpoints within FastAPI."""

    def __init__(self, server_id: str, page_uri: str, response_data: str, timeout_seconds: int):
        self.server_id = server_id
        self.page_uri = page_uri
        self.response_data = response_data
        self.timeout_seconds = timeout_seconds
        self.created_at = time.time()
        self.expires_at = time.time() + timeout_seconds
        self.request_logs = []

    def handle_request(self, request: Request, path: str = "") -> tuple[str, int]:
        """Handle an incoming HTTP request."""

        # Log the request
        client_ip = request.client.host if request.client else "unknown"
        timestamp = datetime.now(timezone.utc).isoformat()

        request_info = {
            "timestamp": timestamp,
            "client_ip": client_ip,
            "method": request.method,
            "path": f"/{path}" if path else "/",
            "user_agent": request.headers.get('user-agent', 'Unknown'),
            "query_params": dict(request.query_params),
        }

        self.request_logs.append(request_info)
        _http_server_logs[self.server_id] = self.request_logs

        logger.info(f"Dynamic HTTP server {self.server_id} request from {client_ip}: {request.method} {path}")

        # Check if this matches the target page - normalize both paths for comparison
        target_path = self.page_uri  # Keep the original page_uri as-is
        if path == target_path:
            return self.response_data, 200
        else:
            return f"Page not found. Available: {self.page_uri}", 404

    def is_expired(self) -> bool:
        """Check if the server has expired."""
        return time.time() > self.expires_at

    def get_results(self) -> Dict[str, Any]:
        """Get the server results and statistics."""
        return {
            "status": "SUCCESS" if not self.is_expired() else "EXPIRED",
            "server_info": {
                "server_id": self.server_id,
                "page_uri": self.page_uri,
                "response_data": self.response_data,
                "timeout_seconds": self.timeout_seconds,
                "created_at": datetime.fromtimestamp(self.created_at, timezone.utc).isoformat(),
                "expires_at": datetime.fromtimestamp(self.expires_at, timezone.utc).isoformat(),
                "access_url": f"http://localhost:8000/server/{self.server_id}{self.page_uri}",
                "time_remaining": max(0, int(self.expires_at - time.time()))
            },
            "request_logs": self.request_logs,
            "total_requests": len(self.request_logs),
            "unique_clients": len(set(req["client_ip"] for req in self.request_logs)) if self.request_logs else 0
        }

def create_dynamic_http_server(page_uri: str, response_data: str, timeout_seconds: int) -> str:
    """Create a new dynamic HTTP server and return its ID."""

    server_id = str(uuid.uuid4())[:8]
    server = DynamicHTTPServer(server_id, page_uri, response_data, timeout_seconds)
    _active_http_servers[server_id] = server
    _http_server_logs[server_id] = []
    logger.info(f"Created dynamic HTTP server {server_id} - Access at: http://localhost:8000/server/{server_id}{page_uri}")

    return server_id

def get_http_server(server_id: str) -> Optional[DynamicHTTPServer]:
    """Get a dynamic HTTP server by ID, cleaning up if expired."""

    if server_id not in _active_http_servers:
        return None

    server = _active_http_servers[server_id]

    if server.is_expired():
        # Clean up expired server
        del _active_http_servers[server_id]
        if server_id in _http_server_logs:
            del _http_server_logs[server_id]
        return None

    return server

def cleanup_expired_servers():
    """Clean up all expired servers."""

    expired_servers = []

    for server_id, server in _active_http_servers.items():
        if server.is_expired():
            expired_servers.append(server_id)

    for server_id in expired_servers:
        del _active_http_servers[server_id]
        if server_id in _http_server_logs:
            del _http_server_logs[server_id]

    return len(expired_servers)
