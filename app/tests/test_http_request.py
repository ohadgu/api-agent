import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from app.tasks.http_request import http_request, _build_url


class TestBuildUrl:
    """Test cases for the _build_url helper function."""

    def test_build_url_http_default_port(self):
        """Test HTTP URL with default port 80."""
        result = _build_url("example.com", 80, "/api/test")
        assert result == "http://example.com/api/test"

    def test_build_url_https_default_port(self):
        """Test HTTPS URL with default port 443."""
        result = _build_url("example.com", 443, "/api/test")
        assert result == "https://example.com/api/test"

    def test_build_url_https_explicit(self):
        """Test HTTPS URL when explicitly requested."""
        result = _build_url("example.com", 80, "/api/test", https=True)
        assert result == "https://example.com:80/api/test"

    def test_build_url_custom_port_http(self):
        """Test HTTP URL with custom port."""
        result = _build_url("example.com", 8080, "/api/test")
        assert result == "http://example.com:8080/api/test"

    def test_build_url_custom_port_https(self):
        """Test HTTPS URL with custom port."""
        result = _build_url("example.com", 8443, "/api/test", https=True)
        assert result == "https://example.com:8443/api/test"

    def test_build_url_root_path(self):
        """Test URL with root path."""
        result = _build_url("example.com", 80, "/")
        assert result == "http://example.com/"

    def test_build_url_empty_path(self):
        """Test URL with empty path."""
        result = _build_url("example.com", 80, "")
        assert result == "http://example.com"


class TestHttpRequest:
    """Test cases for the http_request Celery task."""

    @patch('app.tasks.http_request.requests')
    def test_get_request_success(self, mock_requests):
        """Test successful GET request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success response"
        mock_requests.get.return_value = mock_response

        # Execute task
        result = http_request("GET", "example.com", 80, "/api/test")

        # Verify result
        assert result == "Success response"

        # Verify request was made correctly
        mock_requests.get.assert_called_once_with(
            url="http://example.com/api/test",
            timeout=8.0,
            headers={},
            params=None
        )
        mock_response.raise_for_status.assert_called_once()

    @patch('app.tasks.http_request.requests')
    def test_post_request_with_json_body(self, mock_requests):
        """Test POST request with JSON body."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = "Created"
        mock_requests.post.return_value = mock_response

        body = {"name": "test", "value": 123}
        result = http_request("POST", "api.example.com", 443, "/users",
                            body=body, https=True)

        assert result == "Created"
        mock_requests.post.assert_called_once_with(
            url="https://api.example.com/users",
            timeout=8.0,
            headers={},
            params=None,
            json=body
        )

    @patch('app.tasks.http_request.requests')
    def test_post_request_with_string_body(self, mock_requests):
        """Test POST request with string body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_requests.post.return_value = mock_response

        body = "raw string data"
        result = http_request("POST", "example.com", 80, "/api", body=body)

        assert result == "OK"
        mock_requests.post.assert_called_once_with(
            url="http://example.com/api",
            timeout=8.0,
            headers={},
            params=None,
            data=body
        )

    @patch('app.tasks.http_request.requests')
    def test_put_request_with_body(self, mock_requests):
        """Test PUT request with body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Updated"
        mock_requests.put.return_value = mock_response

        body = {"id": 1, "name": "updated"}
        result = http_request("PUT", "example.com", 80, "/api/items/1", body=body)

        assert result == "Updated"
        mock_requests.put.assert_called_once_with(
            url="http://example.com/api/items/1",
            timeout=8.0,
            headers={},
            params=None,
            json=body
        )

    @patch('app.tasks.http_request.requests')
    def test_delete_request_no_body(self, mock_requests):
        """Test DELETE request without body."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_requests.delete.return_value = mock_response

        result = http_request("DELETE", "example.com", 80, "/api/items/1")

        assert result == ""
        mock_requests.delete.assert_called_once_with(
            url="http://example.com/api/items/1",
            timeout=8.0,
            headers={},
            params=None
        )

    @patch('app.tasks.http_request.requests')
    def test_request_with_headers(self, mock_requests):
        """Test request with custom headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests.get.return_value = mock_response

        headers = {"Authorization": "Bearer token123", "Content-Type": "application/json"}
        result = http_request("GET", "example.com", 80, "/api", headers=headers)

        assert result == "Success"
        mock_requests.get.assert_called_once_with(
            url="http://example.com/api",
            timeout=8.0,
            headers=headers,
            params=None
        )

    @patch('app.tasks.http_request.requests')
    def test_request_with_params(self, mock_requests):
        """Test request with URL parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests.get.return_value = mock_response

        params = {"page": "1", "limit": "10"}
        result = http_request("GET", "example.com", 80, "/api", params=params)

        assert result == "Success"
        mock_requests.get.assert_called_once_with(
            url="http://example.com/api",
            timeout=8.0,
            headers={},
            params=params
        )

    @patch('app.tasks.http_request.requests')
    def test_request_with_custom_timeout(self, mock_requests):
        """Test request with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests.get.return_value = mock_response

        result = http_request("GET", "example.com", 80, "/api", timeout_s=15.0)

        assert result == "Success"
        mock_requests.get.assert_called_once_with(
            url="http://example.com/api",
            timeout=15.0,
            headers={},
            params=None
        )

    @patch('app.tasks.http_request.requests')
    def test_timeout_exception(self, mock_requests):
        """Test timeout exception handling."""
        mock_requests.get.side_effect = Timeout("Request timed out")

        with pytest.raises(RequestException) as exc_info:
            http_request("GET", "example.com", 80, "/api")

        assert "Request timeout after 8.0s for http://example.com/api" in str(exc_info.value)

    @patch('app.tasks.http_request.requests')
    def test_connection_error(self, mock_requests):
        """Test connection error handling."""
        mock_requests.get.side_effect = ConnectionError("Connection refused")

        with pytest.raises(RequestException) as exc_info:
            http_request("GET", "example.com", 80, "/api")

        assert "Connection failed to http://example.com/api" in str(exc_info.value)

    @patch('app.tasks.http_request.requests')
    def test_http_error_4xx(self, mock_requests):
        """Test HTTP 4xx error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_requests.get.return_value = mock_response

        with pytest.raises(RequestException) as exc_info:
            http_request("GET", "example.com", 80, "/api/notfound")

        assert "HTTP error 404 from http://example.com/api/notfound" in str(exc_info.value)

    @patch('app.tasks.http_request.requests')
    def test_http_error_5xx(self, mock_requests):
        """Test HTTP 5xx error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
        mock_requests.get.return_value = mock_response

        with pytest.raises(RequestException) as exc_info:
            http_request("GET", "example.com", 80, "/api")

        assert "HTTP error 500 from http://example.com/api" in str(exc_info.value)

    @patch('app.tasks.http_request.requests')
    def test_generic_request_exception(self, mock_requests):
        """Test generic RequestException handling."""
        mock_requests.get.side_effect = RequestException("Generic request error")

        with pytest.raises(RequestException) as exc_info:
            http_request("GET", "example.com", 80, "/api")

        # Should re-raise the original RequestException
        assert "Generic request error" in str(exc_info.value)

    @patch('app.tasks.http_request.requests')
    def test_unexpected_exception(self, mock_requests):
        """Test unexpected exception handling."""
        mock_requests.get.side_effect = ValueError("Unexpected error")

        with pytest.raises(RequestException) as exc_info:
            http_request("GET", "example.com", 80, "/api")

        assert "Unexpected error requesting http://example.com/api" in str(exc_info.value)

    @patch('app.tasks.http_request.requests')
    def test_get_request_ignores_body(self, mock_requests):
        """Test that GET request ignores body parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests.get.return_value = mock_response

        # Pass body to GET request - should be ignored
        result = http_request("GET", "example.com", 80, "/api", body={"ignored": "data"})

        assert result == "Success"
        # Verify body was not included in the request
        call_kwargs = mock_requests.get.call_args[1]
        assert 'json' not in call_kwargs
        assert 'data' not in call_kwargs

    @patch('app.tasks.http_request.requests')
    def test_delete_request_ignores_body(self, mock_requests):
        """Test that DELETE request ignores body parameter."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_requests.delete.return_value = mock_response

        # Pass body to DELETE request - should be ignored
        result = http_request("DELETE", "example.com", 80, "/api/items/1", body={"ignored": "data"})

        assert result == ""
        # Verify body was not included in the request
        call_kwargs = mock_requests.delete.call_args[1]
        assert 'json' not in call_kwargs
        assert 'data' not in call_kwargs

    @patch('app.tasks.http_request.requests')
    def test_method_case_insensitive(self, mock_requests):
        """Test that HTTP method is case insensitive."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests.get.return_value = mock_response

        # Test lowercase method
        result = http_request("get", "example.com", 80, "/api")

        assert result == "Success"
        mock_requests.get.assert_called_once()

    @patch('app.tasks.http_request.requests')
    def test_empty_headers_converted_to_dict(self, mock_requests):
        """Test that None headers are converted to empty dict."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_requests.get.return_value = mock_response

        result = http_request("GET", "example.com", 80, "/api", headers=None)

        assert result == "Success"
        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs['headers'] == {}
