#!/usr/bin/env python3
"""
Console client for API Agent.
Allows users to interact with various API endpoints and poll for results.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

# API Configuration
API_BASE_URL = "http://localhost:8000/tasks"
POLL_INTERVAL = 1  # seconds
POLL_TIMEOUT = 45  # seconds


class APIClient:
    """Client for interacting with API endpoints."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to API endpoint."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Get task result by task ID."""
        return self.make_request("GET", f"result/{task_id}")

    def poll_task_result(self, task_id: str) -> Dict[str, Any]:
        """Poll for task result with timeout and interval."""
        print(f"\n🔄 Polling for task result (Task ID: {task_id})")
        print(f"⏱️  Checking every {POLL_INTERVAL}s for up to {POLL_TIMEOUT}s...")
        print("=" * 80)

        start_time = time.time()
        poll_count = 0
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

        while time.time() - start_time < POLL_TIMEOUT:
            poll_count += 1
            result = self.get_task_result(task_id)

            status = result.get("status", "UNKNOWN")
            elapsed = int(time.time() - start_time)
            spinner = spinner_chars[poll_count % len(spinner_chars)]

            # Create progress bar
            progress = min(elapsed / POLL_TIMEOUT, 1.0)
            bar_length = 30
            filled_length = int(bar_length * progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            # Status-specific emojis and messages
            if status == "PENDING":
                status_emoji = "⏳"
                status_msg = "Task is waiting in queue"
            elif status == "STARTED":
                status_emoji = "🚀"
                status_msg = "Task is running"
            elif status == "SUCCESS":
                status_emoji = "✅"
                status_msg = "Task completed successfully!"
            elif status == "FAILURE":
                status_emoji = "❌"
                status_msg = "Task failed"
            elif status == "ERROR":
                status_emoji = "🚨"
                status_msg = "Task encountered an error"
            else:
                status_emoji = "❓"
                status_msg = f"Unknown status: {status}"

            # Clear line and print status with progress bar
            print(f"\r{spinner} [{elapsed:2d}s] {status_emoji} {status_msg} │{bar}│ {progress*100:5.1f}%", end="", flush=True)

            if status in ["SUCCESS", "FAILURE", "ERROR"]:
                print()  # New line after completion
                print("=" * 80)
                if status == "SUCCESS":
                    print("🎉 Great! Your task completed successfully!")
                elif status == "FAILURE":
                    print("😞 Oh no! Your task didn't complete successfully.")
                elif status == "ERROR":
                    print("⚠️  Your task encountered an error.")
                return result

            time.sleep(POLL_INTERVAL)

        print()  # New line after timeout
        print("=" * 80)
        print("⏰ Hmm, this is taking longer than expected...")
        print(f"💡 You can check the result later using Task ID: {task_id}")
        return {"status": "TIMEOUT", "error": "Polling timeout exceeded"}


def display_menu():
    """Display available API endpoints menu."""
    print("\n" + "=" * 60)
    print("🚀 API Agent Console Client")
    print("=" * 60)
    print("Available API endpoints:")
    print()
    print("1. 🌐 DNS Query          - Resolve domain name")
    print("2. 📡 HTTP Request       - Make HTTP GET/POST/PUT/DELETE request")
    print("3. 🔍 Port Scan          - Scan TCP ports on target host")
    print("4. 🌳 Process Tree       - Get process tree (synchronous)")
    print("5. 🔧 Registry Action    - Registry GET/SET/DELETE operations")
    print("6. 🖥️  HTTP Server      - Create HTTP server with tracking")
    print("7. 📊 HTTP Logs All     - View all HTTP server logs")
    print("8. 📋 HTTP Logs Server  - View specific HTTP server logs")
    print("9. 🔍 Check Task Result  - Get result by task ID")
    print("0. ❌ Exit")
    print()


def get_dns_input() -> str:
    """Get DNS query input from user."""
    domain = input("Enter domain to resolve (e.g., google.com): ").strip()
    if not domain:
        raise ValueError("Domain cannot be empty")
    return domain


def get_http_input() -> Dict[str, Any]:
    """Get HTTP request input from user."""
    print("\nHTTP Request Configuration:")

    method = input("HTTP Method [GET]: ").strip().upper() or "GET"
    domain = input("Domain (e.g., example.com): ").strip()
    if not domain:
        raise ValueError("Domain cannot be empty")

    port = int(input("Port [80]: ").strip() or "80")
    path = input("Path [/]: ").strip() or "/"
    https = input("Use HTTPS? [y/N]: ").strip().lower().startswith('y')
    timeout = float(input("Timeout in seconds [8.0]: ").strip() or "8.0")

    # Optional fields
    headers = {}
    if input("Add custom headers? [y/N]: ").strip().lower().startswith('y'):
        print("Enter headers (format: key=value, press Enter with empty key to finish):")
        while True:
            key = input("Header key: ").strip()
            if not key:
                break
            value = input(f"Header value for '{key}': ").strip()
            headers[key] = value

    body = None
    if method in ["POST", "PUT"]:
        if input("Add request body? [y/N]: ").strip().lower().startswith('y'):
            body_text = input("Enter JSON body: ").strip()
            if body_text:
                try:
                    body = json.loads(body_text)
                except json.JSONDecodeError:
                    body = body_text  # Treat as string if not valid JSON

    return {
        "method": method,
        "domain": domain,
        "port": port,
        "path": path,
        "https": https,
        "timeout_s": timeout,
        "headers": headers if headers else None,
        "body": body,
        "params": None
    }


def get_port_scan_input() -> Dict[str, Any]:
    """Get port scan input from user."""
    print("\nPort Scan Configuration:")

    host = input("Target host (e.g., example.com): ").strip()
    if not host:
        raise ValueError("Host cannot be empty")

    from_port = int(input("From port [80]: ").strip() or "80")
    to_port = int(input("To port [443]: ").strip() or "443")
    timeout = float(input("Per-port timeout [0.3]: ").strip() or "0.3")

    if from_port > to_port:
        raise ValueError("From port must be <= to port")

    return {
        "host": host,
        "from_port": from_port,
        "to_port": to_port,
        "timeout_s": timeout
    }


def get_process_tree_input() -> Dict[str, Any]:
    """Get process tree input from user."""
    print("\nProcess Tree Configuration:")

    pid = int(input("Process ID (e.g., 1): ").strip() or "1")
    if pid <= 0:
        raise ValueError("PID must be positive")

    return {"pid": pid}


def get_task_id_input() -> str:
    """Get task ID input from user."""
    task_id = input("Enter task ID: ").strip()
    if not task_id:
        raise ValueError("Task ID cannot be empty")
    return task_id


def get_http_server_input() -> Dict[str, Any]:
    """Get HTTP server input from user."""
    print("\nHTTP Server Configuration:")

    page_uri = input("Page URI (e.g., /test, /admin): ").strip()
    if not page_uri:
        raise ValueError("Page URI cannot be empty")
    if not page_uri.startswith('/'):
        page_uri = '/' + page_uri

    print("\nResponse content options:")
    print("1. Simple text message")
    print("2. HTML content")
    print("3. JSON data")

    content_type = input("Choose content type [1]: ").strip() or "1"

    if content_type == "1":
        response_data = input("Enter text message: ").strip() or "Hello from HTTP server!"
    elif content_type == "2":
        response_data = input("Enter HTML content: ").strip()
        if not response_data:
            response_data = "<h1>Welcome!</h1><p>This is a test HTTP server.</p>"
    elif content_type == "3":
        json_input = input("Enter JSON data: ").strip()
        if json_input:
            try:
                # Validate JSON
                json.loads(json_input)
                response_data = json_input
            except json.JSONDecodeError:
                print("❌ Invalid JSON, using default")
                response_data = '{"message": "Hello from HTTP server!", "status": "active"}'
        else:
            response_data = '{"message": "Hello from HTTP server!", "status": "active"}'
    else:
        response_data = "Hello from HTTP server!"

    timeout_seconds = int(input("Timeout in seconds [300]: ").strip() or "300")

    return {
        "page_uri": page_uri,
        "response_data": response_data,
        "timeout_seconds": timeout_seconds
    }


def get_http_server_id_input() -> str:
    """Get HTTP server ID input from user."""
    server_id = input("Enter HTTP server ID: ").strip()
    if not server_id:
        raise ValueError("Server ID cannot be empty")
    return server_id


def format_result(result: Dict[str, Any]) -> str:
    """Format API result for display."""
    status = result.get("status", "UNKNOWN")

    if status == "SUCCESS":
        return f"✅ SUCCESS\n{json.dumps(result.get('result', {}), indent=2)}"
    elif status == "FAILURE":
        return f"❌ FAILURE\nError: {result.get('error', 'Unknown error')}"
    elif status == "ERROR":
        return f"🚨 ERROR\nError: {result.get('error', 'Unknown error')}"
    elif status in ["PENDING", "STARTED"]:
        return f"⏳ {status}\nTask is still running..."
    elif status == "TIMEOUT":
        return f"⏰ TIMEOUT\nPolling timed out after {POLL_TIMEOUT} seconds"
    else:
        return f"❓ {status}\n{json.dumps(result, indent=2)}"


def format_http_logs(logs_data: Dict[str, Any]) -> str:
    """Format HTTP server logs for display."""
    if "error" in logs_data:
        return f"❌ Error: {logs_data['error']}"

    if "summary" in logs_data:
        # All servers logs format
        summary = logs_data["summary"]
        servers = logs_data.get("servers", {})

        result = f"📊 SUMMARY:\n"
        result += f"  Active servers: {summary['active_servers']}\n"
        result += f"  Total requests: {summary['total_requests']}\n"
        result += f"  Unique clients: {summary['unique_clients']}\n"

        if servers:
            result += f"\n🖥️  ACTIVE SERVERS:\n"
            for server_id, server_info in servers.items():
                result += f"\n  Server ID: {server_id}\n"
                result += f"  Page URI: {server_info['page_uri']}\n"
                result += f"  Access URL: {server_info['access_url']}\n"
                result += f"  Request count: {server_info['request_count']}\n"
                result += f"  Unique clients: {server_info['unique_clients']}\n"

                if server_info.get('latest_request'):
                    latest = server_info['latest_request']
                    result += f"  Latest: {latest['timestamp']} - {latest['method']} {latest['path']} from {latest['client_ip']}\n"
        else:
            result += f"\n  No active servers found.\n"

        return result

    elif "server_id" in logs_data:
        # Specific server logs format
        server_info = logs_data.get("server_info", {})
        tracking_logs = logs_data.get("tracking_logs", [])

        result = f"📋 LOGS FOR SERVER: {logs_data['server_id']}\n"
        result += f"Page URI: {server_info.get('page_uri', 'N/A')}\n"
        result += f"Created: {server_info.get('created_at', 'N/A')}\n"
        result += f"Expires: {server_info.get('expires_at', 'N/A')}\n"
        result += f"Time remaining: {server_info.get('time_remaining', 'N/A')} seconds\n"
        result += f"Total requests: {logs_data.get('total_requests', 0)}\n"
        result += f"Unique clients: {logs_data.get('unique_clients', 0)}\n"

        if tracking_logs:
            result += f"\n🔍 REQUEST LOGS:\n"
            for log in tracking_logs:
                result += f"  {log['timestamp']} - {log['method']} {log['path']}\n"
                result += f"    Client: {log['client_ip']}\n"
                result += f"    User-Agent: {log.get('user_agent', 'N/A')}\n"
                if log.get('query_params'):
                    result += f"    Query params: {log['query_params']}\n"
                result += "\n"
        else:
            result += f"\n  No requests logged yet.\n"

        return result

    else:
        return json.dumps(logs_data, indent=2)


def main():
    """Main application loop."""
    client = APIClient()

    print("🔗 Connecting to SafeBreach API at", API_BASE_URL)

    while True:
        try:
            display_menu()
            choice = input("Select an option (0-9): ").strip()

            if choice == "0":
                print("\n👋 Goodbye!")
                sys.exit(0)

            elif choice == "1":  # DNS Query
                domain = get_dns_input()
                print(f"\n🌐 Querying DNS for: {domain}")

                result = client.make_request("POST", "dns", {"domain": domain})

                if "task_id" in result:
                    task_id = result["task_id"]
                    print(f"✅ Task queued successfully! Task ID: {task_id}")
                    final_result = client.poll_task_result(task_id)
                    print("\n📋 Final Result:")
                    print(format_result(final_result))
                else:
                    print(f"\n❌ Failed to queue task: {result}")

            elif choice == "2":  # HTTP Request
                http_data = get_http_input()
                print(f"\n📡 Making HTTP {http_data['method']} request to {http_data['domain']}")

                result = client.make_request("POST", "http/request", http_data)

                if "task_id" in result:
                    task_id = result["task_id"]
                    print(f"✅ Task queued successfully! Task ID: {task_id}")
                    final_result = client.poll_task_result(task_id)
                    print("\n📋 Final Result:")
                    print(format_result(final_result))
                else:
                    print(f"\n❌ Failed to queue task: {result}")

            elif choice == "3":  # Port Scan
                scan_data = get_port_scan_input()
                print(f"\n🔍 Scanning ports {scan_data['from_port']}-{scan_data['to_port']} on {scan_data['host']}")

                result = client.make_request("POST", "ports/scan", scan_data)

                if "task_id" in result:
                    task_id = result["task_id"]
                    print(f"✅ Task queued successfully! Task ID: {task_id}")
                    final_result = client.poll_task_result(task_id)
                    print("\n📋 Final Result:")
                    print(format_result(final_result))
                else:
                    print(f"\n❌ Failed to queue task: {result}")

            elif choice == "4":  # Process Tree Sync
                tree_data = get_process_tree_input()
                print(f"\n🌳 Getting process tree for PID: {tree_data['pid']} (sync)")

                result = client.make_request("POST", "process/tree", tree_data)
                print("\n📋 Result:")
                print(format_result(result))

            elif choice == "5":  # Registry Action
                print("\n🔧 Registry Action Configuration:")

                action = input("Action (GET/SET/DELETE): ").strip().upper()
                if action not in ["GET", "SET", "DELETE"]:
                    raise ValueError("Invalid action. Choose GET, SET, or DELETE.")

                key = input("Registry key (e.g., HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion): ").strip()
                if not key:
                    raise ValueError("Registry key cannot be empty")

                value_name = input("Value name (e.g., ProductName): ").strip()
                if not value_name:
                    raise ValueError("Value name cannot be empty")

                value_data = None
                if action == "SET":
                    value_data = input("Value data to set: ").strip()
                    if not value_data:
                        raise ValueError("Value data cannot be empty for SET operation")

                registry_data = {
                    "action": action,
                    "key": key,
                    "value_name": value_name,
                    "value_data": value_data
                }

                result = client.make_request("POST", "registry/action", registry_data)

                if "task_id" in result:
                    task_id = result["task_id"]
                    print(f"✅ Task queued successfully! Task ID: {task_id}")
                    final_result = client.poll_task_result(task_id)
                    print("\n📋 Final Result:")
                    print(format_result(final_result))
                else:
                    print(f"\n❌ Failed to queue task: {result}")

            elif choice == "6":  # HTTP Server
                http_data = get_http_server_input()
                print(f"\n🖥️  Creating HTTP server with URI {http_data['page_uri']}")

                result = client.make_request("POST", "http/server", http_data)

                if "server_info" in result:
                    server_info = result["server_info"]
                    server_id = server_info["server_id"]
                    access_url = server_info["access_url"]
                    print(f"✅ HTTP server created successfully!")
                    print(f"🆔 Server ID: {server_id}")
                    print(f"🌐 Access URL: {access_url}")
                    print(f"⏰ Expires in: {server_info['time_remaining']} seconds")
                else:
                    print(f"\n❌ Failed to create server: {result}")

            elif choice == "7":  # HTTP Logs All
                print("\n📊 Retrieving all HTTP server logs...")

                # Use direct URL since HTTP logs are not under /tasks
                http_url = "http://localhost:8000/server/logs/all"
                try:
                    response = client.session.get(http_url)
                    response.raise_for_status()
                    result = response.json()

                    print("\n📋 HTTP Server Logs:")
                    print(format_http_logs(result))
                except requests.exceptions.RequestException as e:
                    print(f"❌ Failed to retrieve logs: {e}")

            elif choice == "8":  # HTTP Logs Server
                server_id = get_http_server_id_input()
                print(f"\n📋 Retrieving logs for server: {server_id}")

                # Use direct URL since HTTP logs are not under /tasks
                http_url = f"http://localhost:8000/server/{server_id}/logs"
                try:
                    response = client.session.get(http_url)
                    response.raise_for_status()
                    result = response.json()

                    print("\n📋 Server Logs:")
                    print(format_http_logs(result))
                except requests.exceptions.RequestException as e:
                    print(f"❌ Failed to retrieve logs: {e}")

            elif choice == "9":  # Check Task Result
                task_id = get_task_id_input()
                print(f"\n🔍 Checking result for task: {task_id}")

                result = client.get_task_result(task_id)
                print("\n📋 Result:")
                print(format_result(result))

            else:
                print("❌ Invalid choice. Please select 0-9.")

            input("\n📌 Press Enter to continue...")

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user. Goodbye!")
            sys.exit(0)
        except ValueError as e:
            print(f"\n❌ Input error: {e}")
            input("📌 Press Enter to continue...")
        except Exception as e:
            print(f"\n🚨 Unexpected error: {e}")
            input("📌 Press Enter to continue...")


if __name__ == "__main__":
    main()
