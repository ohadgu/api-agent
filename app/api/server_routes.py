from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from ..infra.dynamic_http_server import get_http_server, _active_http_servers

# Single router for all dynamic HTTP server functionality
http_server_router = APIRouter(prefix="/server", tags=["Dynamic HTTP Server"])

@http_server_router.get("/logs/all")
async def get_all_server_logs():
    """View logs for all active HTTP servers."""

    all_logs = {}
    total_requests = 0
    unique_ips = set()

    for server_id, server in _active_http_servers.items():
        if not server.is_expired():
            all_logs[server_id] = {
                "page_uri": server.page_uri,
                "access_url": f"http://localhost:8000/server/{server_id}{server.page_uri}",
                "request_count": len(server.request_logs),
                "unique_clients": len(set(req["client_ip"] for req in server.request_logs)) if server.request_logs else 0,
                "latest_request": server.request_logs[-1] if server.request_logs else None,
                "recent_logs": server.request_logs[-5:] if server.request_logs else []
            }
            total_requests += len(server.request_logs)
            for req in server.request_logs:
                unique_ips.add(req["client_ip"])

    return {
        "summary": {
            "active_servers": len(all_logs),
            "total_requests": total_requests,
            "unique_clients": len(unique_ips)
        },
        "servers": all_logs
    }

@http_server_router.get("/{server_id}/logs")
async def get_server_logs(server_id: str):
    """View logs for a specific HTTP server."""

    server = get_http_server(server_id)
    if not server:
        return {"error": "Server not found or expired", "server_id": server_id}

    return {
        "server_id": server_id,
        "server_info": {
            "page_uri": server.page_uri,
            "created_at": server.get_results()["server_info"]["created_at"],
            "expires_at": server.get_results()["server_info"]["expires_at"],
            "time_remaining": server.get_results()["server_info"]["time_remaining"]
        },
        "tracking_logs": server.request_logs,
        "total_requests": len(server.request_logs),
        "unique_clients": len(set(req["client_ip"] for req in server.request_logs)) if server.request_logs else 0,
        "latest_request": server.request_logs[-1] if server.request_logs else None
    }

@http_server_router.get("/{server_id}/{path:path}")
async def handle_http_server_request(server_id: str, path: str, request: Request):
    """Serve HTTP server content and track requests."""

    server = get_http_server(server_id)
    if not server:
        return PlainTextResponse("Server not found or expired", status_code=status.HTTP_404_NOT_FOUND)

    # Handle the request and track it
    content, status_code = server.handle_request(request, f"/{path}")

    if status_code == status.HTTP_200_OK:
        return HTMLResponse(content=content)
    else:
        return PlainTextResponse(content=content, status_code=status_code)
