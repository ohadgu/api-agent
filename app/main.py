from fastapi import FastAPI
from .api.api_endpoints import router as tasks_router
from .api.health import router as health_router
from .api.server_routes import http_server_router
from .infra.db import init_db

# def create_app() -> FastAPI:
#     app = FastAPI(title="Agent API", version="1.0.0")
#     app.include_router(health_router)
#     app.include_router(tasks_router)
#     app.include_router(http_server_router)
#     return app
#
# app = create_app()

app = FastAPI(title="Agent API", version="1.0.0")
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(http_server_router)

# @app.on_event("startup")
# def _startup():
#     init_db()