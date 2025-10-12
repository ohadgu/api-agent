import pytest
from unittest.mock import MagicMock, patch
import socket
from pydantic import ValidationError

from app.schemas.port_scan_request import PortScanRequest
from app.tasks.port_scan import port_scan, _is_port_open, enqueue_port_scan_task


class TestPortScanRequest:
    """Test cases for PortScanRequest schema validation."""

    def test_valid_port_scan_request(self):
        """Test valid port scan request."""
        request = PortScanRequest(
            domain="example.com",
            from_port=80,
            to_port=443
        )
        assert request.domain == "example.com"
        assert request.from_port == 80
        assert request.to_port == 443
        assert request.timeout_s == 0.15  # Default value

    def test_domain_normalized_to_lowercase(self):
        """Test that domain is normalized to lowercase."""
        request = PortScanRequest(
            domain="GOOGLE.COM",
            from_port=80,
            to_port=80
        )
        assert request.domain == "google.com"

    def test_domain_whitespace_stripped(self):
        """Test that domain whitespace is stripped."""
        request = PortScanRequest(
            domain="  example.com  ",
            from_port=22,
            to_port=22
        )
        assert request.domain == "example.com"

    def test_custom_timeout(self):
        """Test custom timeout value."""
        request = PortScanRequest(
            domain="example.com",
            from_port=80,
            to_port=80,
            timeout_s=2.5
        )
        assert request.timeout_s == 2.5

    def test_empty_domain_raises_error(self):
        """Test that empty domain raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="", from_port=80, to_port=80)
        assert "Domain cannot be empty" in str(exc_info.value)

    def test_domain_with_whitespace_raises_error(self):
        """Test that domain with internal whitespace raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="exam ple.com", from_port=80, to_port=80)
        assert "Domain cannot contain whitespace" in str(exc_info.value)

    def test_domain_starting_with_dot_raises_error(self):
        """Test that domain starting with dot raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain=".example.com", from_port=80, to_port=80)
        assert "Domain cannot start or end with a dot" in str(exc_info.value)

    def test_domain_ending_with_dot_raises_error(self):
        """Test that domain ending with dot raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="example.com.", from_port=80, to_port=80)
        assert "Domain cannot start or end with a dot" in str(exc_info.value)

    def test_port_below_range_raises_error(self):
        """Test that port below 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="example.com", from_port=0, to_port=80)
        assert "Port must be between 1 and 65535" in str(exc_info.value)

    def test_port_above_range_raises_error(self):
        """Test that port above 65535 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="example.com", from_port=80, to_port=65536)
        assert "Port must be between 1 and 65535" in str(exc_info.value)

    def test_to_port_less_than_from_port_raises_error(self):
        """Test that to_port < from_port raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="example.com", from_port=443, to_port=80)
        assert "to_port must be >= from_port" in str(exc_info.value)

    def test_from_port_equals_to_port_is_valid(self):
        """Test that scanning single port is valid."""
        request = PortScanRequest(
            domain="example.com",
            from_port=80,
            to_port=80
        )
        assert request.from_port == request.to_port == 80

    def test_timeout_zero_raises_error(self):
        """Test that timeout <= 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(
                domain="example.com",
                from_port=80,
                to_port=80,
                timeout_s=0
            )
        assert "greater than 0" in str(exc_info.value)

    def test_timeout_negative_raises_error(self):
        """Test that negative timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(
                domain="example.com",
                from_port=80,
                to_port=80,
                timeout_s=-1.0
            )
        assert "greater than 0" in str(exc_info.value)

    def test_timeout_above_max_raises_error(self):
        """Test that timeout > 5.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(
                domain="example.com",
                from_port=80,
                to_port=80,
                timeout_s=6.0
            )
        assert "less than or equal to 5" in str(exc_info.value)

    def test_missing_required_fields_raises_error(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PortScanRequest(domain="example.com")
        assert "Field required" in str(exc_info.value)


class TestIsPortOpenFunction:
    """Test cases for the _is_port_open helper function."""

    def test_port_is_open(self):
        """Test when port is open (connect_ex returns 0)."""
        with patch('app.tasks.port_scan.socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0  # Success
            mock_socket.__enter__ = MagicMock(return_value=mock_socket)
            mock_socket.__exit__ = MagicMock(return_value=False)
            mock_socket_class.return_value = mock_socket

            result = _is_port_open("example.com", 80, 0.5)

            assert result is True
            mock_socket.settimeout.assert_called_once_with(0.5)
            mock_socket.connect_ex.assert_called_once_with(("example.com", 80))

    def test_port_is_closed(self):
        """Test when port is closed (connect_ex returns non-zero)."""
        with patch('app.tasks.port_scan.socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 111  # Connection refused
            mock_socket.__enter__ = MagicMock(return_value=mock_socket)
            mock_socket.__exit__ = MagicMock(return_value=False)
            mock_socket_class.return_value = mock_socket

            result = _is_port_open("example.com", 8080, 0.5)

            assert result is False

    def test_connection_timeout(self):
        """Test when connection times out."""
        with patch('app.tasks.port_scan.socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.side_effect = socket.timeout("Connection timed out")
            mock_socket.__enter__ = MagicMock(return_value=mock_socket)
            mock_socket.__exit__ = MagicMock(return_value=False)
            mock_socket_class.return_value = mock_socket

            result = _is_port_open("example.com", 443, 0.1)

            assert result is False

    def test_connection_error(self):
        """Test when connection error occurs."""
        with patch('app.tasks.port_scan.socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.side_effect = socket.error("Network unreachable")
            mock_socket.__enter__ = MagicMock(return_value=mock_socket)
            mock_socket.__exit__ = MagicMock(return_value=False)
            mock_socket_class.return_value = mock_socket

            result = _is_port_open("example.com", 22, 0.5)

            assert result is False

    def test_unexpected_exception(self):
        """Test when unexpected exception occurs."""
        with patch('app.tasks.port_scan.socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.side_effect = RuntimeError("Unexpected error")
            mock_socket.__enter__ = MagicMock(return_value=mock_socket)
            mock_socket.__exit__ = MagicMock(return_value=False)
            mock_socket_class.return_value = mock_socket

            result = _is_port_open("example.com", 80, 0.5)

            assert result is False


class TestPortScanTask:
    """Test cases for the port_scan Celery task."""

    def test_port_scan_no_open_ports(self):
        """Test port scan when no ports are open."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = False

            result = port_scan("example.com", 80, 85, 0.5)

            assert result == []
            assert mock_is_port_open.call_count == 6  # 80-85 inclusive

    def test_port_scan_all_ports_open(self):
        """Test port scan when all ports are open."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = True

            result = port_scan("example.com", 20, 23, 0.5)

            assert result == [20, 21, 22, 23]
            assert mock_is_port_open.call_count == 4

    def test_port_scan_some_ports_open(self):
        """Test port scan with mixed open/closed ports."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            # Simulate ports 22, 80, 443 being open
            def side_effect(domain, port, timeout):
                return port in [22, 80, 443]
            
            mock_is_port_open.side_effect = side_effect

            result = port_scan("example.com", 20, 445, 0.3)

            assert result == [22, 80, 443]

    def test_port_scan_single_port_open(self):
        """Test scanning single port that is open."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = True

            result = port_scan("example.com", 80, 80, 0.5)

            assert result == [80]
            mock_is_port_open.assert_called_once_with("example.com", 80, 0.5)

    def test_port_scan_single_port_closed(self):
        """Test scanning single port that is closed."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = False

            result = port_scan("example.com", 8080, 8080, 0.5)

            assert result == []
            mock_is_port_open.assert_called_once()

    def test_port_scan_returns_list(self):
        """Test that port_scan always returns a list."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = False

            result = port_scan("example.com", 1, 3, 0.1)

            assert isinstance(result, list)

    def test_port_scan_calls_with_correct_params(self):
        """Test that _is_port_open is called with correct parameters."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = False

            port_scan("test.com", 100, 102, 1.5)

            calls = mock_is_port_open.call_args_list
            assert len(calls) == 3
            assert calls[0][0] == ("test.com", 100, 1.5)
            assert calls[1][0] == ("test.com", 101, 1.5)
            assert calls[2][0] == ("test.com", 102, 1.5)

    def test_port_scan_large_range(self):
        """Test port scan with larger port range."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            # Simulate common ports being open
            def side_effect(domain, port, timeout):
                return port in [80, 443, 8080]
            
            mock_is_port_open.side_effect = side_effect

            result = port_scan("example.com", 1, 9000, 0.1)

            assert result == [80, 443, 8080]
            assert mock_is_port_open.call_count == 9000


class TestEnqueuePortScanTask:
    """Test cases for the enqueue_port_scan_task function."""

    def test_enqueue_creates_task_and_db_record(self):
        """Test that enqueue creates Celery task and database record."""
        with patch('app.tasks.port_scan.port_scan.apply_async') as mock_apply_async:
            mock_result = MagicMock()
            mock_result.id = "test-scan-123"
            mock_apply_async.return_value = mock_result

            mock_db = MagicMock()
            
            payload = PortScanRequest(
                domain="example.com",
                from_port=80,
                to_port=443
            )

            result = enqueue_port_scan_task(payload, mock_db)

            # Verify Celery task was queued
            mock_apply_async.assert_called_once()
            call_kwargs = mock_apply_async.call_args[1]['kwargs']
            assert call_kwargs['domain'] == "example.com"
            assert call_kwargs['from_port'] == 80
            assert call_kwargs['to_port'] == 443
            
            # Verify database operations
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            
            # Verify return value
            assert result["task_id"] == "test-scan-123"
            assert result["status"] == "queued"
            assert result["name"] == "net.port_scan"

    def test_enqueue_task_run_record_correctness(self):
        """Test that TaskRun record contains correct data."""
        with patch('app.tasks.port_scan.port_scan.apply_async') as mock_apply_async:
            mock_result = MagicMock()
            mock_result.id = "scan-456"
            mock_apply_async.return_value = mock_result

            mock_db = MagicMock()
            
            payload = PortScanRequest(
                domain="google.com",
                from_port=1,
                to_port=1024,
                timeout_s=0.2
            )

            enqueue_port_scan_task(payload, mock_db)

            # Get the TaskRun object that was added
            call_args = mock_db.add.call_args
            task_run = call_args[0][0]
            
            assert task_run.id == "scan-456"
            assert task_run.name == "net.port_scan"
            assert task_run.status == "PENDING"
            assert task_run.kwargs_json['domain'] == "google.com"
            assert task_run.kwargs_json['from_port'] == 1
            assert task_run.kwargs_json['to_port'] == 1024
            assert task_run.kwargs_json['timeout_s'] == 0.2

    def test_enqueue_multiple_scans(self):
        """Test enqueueing multiple port scan tasks."""
        with patch('app.tasks.port_scan.port_scan.apply_async') as mock_apply_async:
            scans = [
                ("example.com", 80, 80),
                ("google.com", 443, 443),
                ("github.com", 22, 22)
            ]
            
            mock_db = MagicMock()

            for i, (domain, from_port, to_port) in enumerate(scans):
                mock_result = MagicMock()
                mock_result.id = f"scan-{i}"
                mock_apply_async.return_value = mock_result

                payload = PortScanRequest(
                    domain=domain,
                    from_port=from_port,
                    to_port=to_port
                )
                
                result = enqueue_port_scan_task(payload, mock_db)
                
                assert result["task_id"] == f"scan-{i}"

            assert mock_db.add.call_count == len(scans)
            assert mock_db.commit.call_count == len(scans)


class TestPortScanIntegration:
    """Integration tests combining schema validation and task execution."""

    def test_full_flow_valid_scan(self):
        """Test full flow from schema validation to task execution."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.side_effect = lambda d, p, t: p in [80, 443]

            # 1. Validate schema
            request = PortScanRequest(
                domain="  EXAMPLE.COM  ",
                from_port=70,
                to_port=450
            )
            assert request.domain == "example.com"  # Normalized

            # 2. Execute task
            result = port_scan(
                request.domain,
                request.from_port,
                request.to_port,
                request.timeout_s
            )
            
            assert result == [80, 443]

    def test_invalid_port_range_caught_by_schema(self):
        """Test that invalid port range is caught at schema level."""
        with pytest.raises(ValidationError):
            PortScanRequest(
                domain="example.com",
                from_port=443,
                to_port=80  # Invalid: to_port < from_port
            )

    def test_domain_normalization_flow(self):
        """Test that domain normalization works through full flow."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = True

            # Domain with uppercase and whitespace
            request = PortScanRequest(
                domain="  GoOgLe.COM  ",
                from_port=80,
                to_port=80
            )
            
            result = port_scan(request.domain, request.from_port, request.to_port, 0.5)
            
            # Verify normalization happened
            assert mock_is_port_open.call_args[0][0] == "google.com"
            assert result == [80]

    def test_default_timeout_applied(self):
        """Test that default timeout is applied when not specified."""
        with patch('app.tasks.port_scan._is_port_open') as mock_is_port_open:
            mock_is_port_open.return_value = False

            request = PortScanRequest(
                domain="example.com",
                from_port=80,
                to_port=80
                # timeout_s not specified, should use default 0.15
            )
            
            assert request.timeout_s == 0.15

            port_scan(request.domain, request.from_port, request.to_port, request.timeout_s)
            
            # Verify default timeout was passed
            assert mock_is_port_open.call_args[0][2] == 0.15

