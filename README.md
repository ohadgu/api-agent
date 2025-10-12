# API Agent

A distributed task execution platform built with FastAPI, Celery, Redis, and PostgreSQL. Fully dockerized for easy deployment with asynchronous task processing and dynamic worker scaling. Execute network operations, system queries, and HTTP server deployments. Each API call returns a unique task_id which can be used to retrieve results via the tasks/result/{task_id} endpoint. All tasks are saved to database with dynamic status updates based on task progress.

In addition to direct API calls, an interactive console client is provided for user-friendly task management and monitoring.

The project includes unit tests to ensure reliability and correctness of core features.

## Repository

🔗 **GitHub**: [https://github.com/ohadgu/api-agent](https://github.com/ohadgu/api-agent-1)

```bash
# Clone the repository
git clone https://github.com/ohadgu/api-agent.git
cd api-agent
```

## Project Structure

```
AgentAPI/
├── app/                        # Main application package (server-side)
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── celery_app.py           # Celery configuration and setup
│   ├── api/                    # API endpoints and routing
│   │   ├── __init__.py
│   │   ├── api_endpoints.py    # Task API endpoints
│   │   ├── health.py           # Health check endpoints
│   │   ├── server_routes.py    # HTTP server management routes
│   ├── infra/                  # Infrastructure components
│   │   ├── __init__.py
│   │   ├── db.py               # Database configuration
│   │   ├── models.py           # SQLAlchemy models
│   │   └── dynamic_http_server.py  # HTTP server implementation
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── dns_query_request.py
│   │   ├── http_request.py
│   │   ├── http_server_request.py
│   │   ├── port_scan_request.py
│   │   ├── process_tree_request.py
│   │   └── registry_request.py
│   ├── tasks/                  # Celery task implementations
│   │   ├── __init__.py
│   │   ├── dns_query.py        # DNS query tasks
│   │   ├── http_request.py     # HTTP request tasks
│   │   ├── port_scan.py        # Port scanning tasks
│   │   ├── process_tree.py     # Process tree tasks
│   │   └── registry_action.py  # Registry manipulation tasks
│   └── tests/                  # Unit tests
│       ├── __init__.py
│       ├── test_dns_query.py
│       ├── test_http_request.py
│       └── test_port_scan.py
├── console_client.py           # Interactive client application
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Container build configuration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # Project documentation
```

## Architecture Notes

- **FastAPI**: Main API framework with automatic OpenAPI documentation
- **Celery**: Distributed task queue for async operations
- **Redis**: Message broker and result backend
- **PostgreSQL**: Database for task persistence and logging
- **Pydantic**: Data validation and serialization for API schemas
- **Docker**: Containerized deployment with scaling support

## Quickstart (docker-compose)

```bash
# Start the application with single worker
docker-compose up -d --build

# Start with multiple workers (3 workers for better performance)
docker-compose up -d --build --scale worker=3

# API docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

## API Documentation

Interactive API documentation is available via Swagger UI:

**🔗 [Swagger UI - Interactive API Docs](http://localhost:8000/docs)**

The Swagger interface provides:
- Complete API endpoint documentation
- Interactive request/response testing
- Schema definitions for all request/response models
- Real-time API exploration and testing

## Scaling Workers

The application supports horizontal scaling of worker processes:

```bash
# Scale to 5 workers for high-throughput scenarios
docker-compose up -d --scale worker=5

# Scale back down to 2 workers
docker-compose up -d --scale worker=2
```

Each worker can process tasks independently, providing better performance for concurrent operations like DNS queries, HTTP requests, and port scans.

## Console Client

A user-friendly console client is available for interactive testing:

```bash
# Run the interactive console client
python console_client.py

# The client provides:
# - Menu-driven interface
# - Real-time task polling with progress bars
# - Formatted result display
# - Error handling and validation
```

## Available Endpoints

### Health Check
```bash
# Check API health
curl http://localhost:8000/health
```

### Task Results
```bash
# Poll for task result using task ID
curl http://localhost:8000/tasks/result/{task_id}
```

### DNS Query
```bash
# Query DNS for a domain
curl -X POST -H "Content-Type: application/json" \
  -d '{"domain":"google.com"}' \
  http://localhost:8000/tasks/dns

# Example response:
# {"task_id":"abc123","status":"queued","name":"net.dns_query","domain":"google.com"}
```

### HTTP Request
```bash
# Make an HTTP GET request
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "method":"GET",
    "domain":"httpbin.org",
    "port":80,
    "path":"/get",
    "timeout_s":2.0
  }' \
  http://localhost:8000/tasks/http/request

# Make an HTTP POST request with body and query params
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "method":"POST",
    "domain":"httpbin.org",
    "port":80,
    "path":"/post",
    "timeout_s":5.0,
    "body":{"test":"data","message":"hello"},
    "params":{"key":"value"}
  }' \
  http://localhost:8000/tasks/http/request

# HTTPS request (use port 443)
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "method":"GET",
    "domain":"httpbin.org",
    "port":443,
    "path":"/get"
  }' \
  http://localhost:8000/tasks/http/request
```

### Port Scan
```bash
# Scan ports on a target domain
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "domain":"google.com",
    "from_port":20,
    "to_port":150,
    "timeout_s":0.15
  }' \
  http://localhost:8000/tasks/ports/scan
```

### Process Tree (Synchronous)
```bash
# Get process tree for a specific PID
curl -X POST -H "Content-Type: application/json" \
  -d '{"pid":1}' \
  http://localhost:8000/tasks/process/tree

# Returns immediately with process tree data
```

### Registry Actions (Windows Only)
```bash
# Get registry value
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "action":"GET",
    "key":"Software\\Microsoft\\Windows\\CurrentVersion",
    "value_name":"ProductName"
  }' \
  http://localhost:8000/tasks/registry/action

# Set registry value
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "action":"SET",
    "key":"Software\\TestApp",
    "value_name":"TestValue",
    "value_data":"Hello World"
  }' \
  http://localhost:8000/tasks/registry/action

# Delete registry value
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "action":"DELETE",
    "key":"Software\\TestApp",
    "value_name":"TestValue"
  }' \
  http://localhost:8000/tasks/registry/action

# Note: Registry actions execute synchronously (no task_id returned)
# Note: Only works when running API on Windows (returns error in Docker/Linux)
```

### HTTP Server
```bash
# Create a temporary HTTP server with tracking
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "page_uri":"/test",
    "response_data":"<h1>Hello from HTTP server!</h1><p>Your visit has been tracked!</p>",
    "timeout_seconds":600
  }' \
  http://localhost:8000/tasks/http/server

# Access the created server
curl http://localhost:8000/server/a1b2c3d4/test
```

### HTTP Server Logs
```bash
# View logs for all active HTTP servers
curl http://localhost:8000/server/logs/all

# View logs for a specific HTTP server
curl http://localhost:8000/server/{server_id}/logs
```
