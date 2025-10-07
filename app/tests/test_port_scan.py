import pytest
from unittest.mock import Mock, patch, call
import socket
from app.tasks.port_scan import port_scan, _is_port_open


class TestIsPortOpen:
    """Test cases for the _is_port_open helper function."""

    @patch('app.tasks.port_scan.socket.socket')
    def test_port_open_success(self, mock_socket_class):
        """Test when port is open (connect_ex returns 0)."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 0  # Success

        result = _is_port_open("example.com", 80, 1.0)

        assert result is True
        mock_socket.settimeout.assert_called_once_with(1.0)
        mock_socket.connect_ex.assert_called_once_with(("example.com", 80))

    @patch('app.tasks.port_scan.socket.socket')
    def test_port_closed(self, mock_socket_class):
        """Test when port is closed (connect_ex returns non-zero)."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 1  # Connection refused

        result = _is_port_open("example.com", 80, 1.0)

        assert result is False
        mock_socket.settimeout.assert_called_once_with(1.0)
        mock_socket.connect_ex.assert_called_once_with(("example.com", 80))

    @patch('app.tasks.port_scan.socket.socket')
    def test_port_connection_exception(self, mock_socket_class):
        """Test when socket connection raises an exception."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.side_effect = socket.timeout("Connection timeout")

        result = _is_port_open("example.com", 80, 1.0)

        assert result is False
        mock_socket.settimeout.assert_called_once_with(1.0)
        mock_socket.connect_ex.assert_called_once_with(("example.com", 80))

    @patch('app.tasks.port_scan.socket.socket')
    def test_port_socket_creation_exception(self, mock_socket_class):
        """Test when socket creation raises an exception."""
        mock_socket_class.side_effect = OSError("Socket creation failed")

        result = _is_port_open("example.com", 80, 1.0)

        assert result is False

    @patch('app.tasks.port_scan.socket.socket')
    def test_port_different_timeout_values(self, mock_socket_class):
        """Test that timeout is properly set for different values."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 0

        # Test with different timeout values
        _is_port_open("example.com", 80, 0.1)
        mock_socket.settimeout.assert_called_with(0.1)

        _is_port_open("example.com", 80, 5.0)
        mock_socket.settimeout.assert_called_with(5.0)

    @patch('app.tasks.port_scan.socket.socket')
    def test_port_different_hosts_and_ports(self, mock_socket_class):
        """Test with different host and port combinations."""
        mock_socket = Mock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 0

        # Test different hosts and ports
        _is_port_open("google.com", 443, 1.0)
        mock_socket.connect_ex.assert_called_with(("google.com", 443))

        _is_port_open("localhost", 8080, 1.0)
        mock_socket.connect_ex.assert_called_with(("localhost", 8080))


class TestPortScan:
    """Test cases for the port_scan Celery task."""

    @patch('app.tasks.port_scan._is_port_open')
    def test_single_port_open(self, mock_is_port_open):
        """Test scanning single port that is open."""
        mock_is_port_open.return_value = True

        result = port_scan("example.com", 80, 80)

        assert result == [80]
        mock_is_port_open.assert_called_once_with("example.com", 80, 0.15)

    @patch('app.tasks.port_scan._is_port_open')
    def test_single_port_closed(self, mock_is_port_open):
        """Test scanning single port that is closed."""
        mock_is_port_open.return_value = False

        result = port_scan("example.com", 80, 80)

        assert result == []
        mock_is_port_open.assert_called_once_with("example.com", 80, 0.15)

    @patch('app.tasks.port_scan._is_port_open')
    def test_multiple_ports_all_open(self, mock_is_port_open):
        """Test scanning multiple ports that are all open."""
        mock_is_port_open.return_value = True

        result = port_scan("example.com", 80, 82)

        assert result == [80, 81, 82]
        expected_calls = [
            call("example.com", 80, 0.15),
            call("example.com", 81, 0.15),
            call("example.com", 82, 0.15)
        ]
        mock_is_port_open.assert_has_calls(expected_calls)
        assert mock_is_port_open.call_count == 3

    @patch('app.tasks.port_scan._is_port_open')
    def test_multiple_ports_some_open(self, mock_is_port_open):
        """Test scanning multiple ports where some are open."""
        # Port 80 and 443 open, 8080 closed
        def mock_port_check(host, port, timeout):
            return port in [80, 443]

        mock_is_port_open.side_effect = mock_port_check

        result = port_scan("example.com", 80, 443, timeout_s=1.0)

        # Should only return open ports, but we need to check the range
        # Since 80 to 443 is a large range, let's test a smaller range
        mock_is_port_open.reset_mock()
        mock_is_port_open.side_effect = lambda h, p, t: p in [80, 82]

        result = port_scan("example.com", 80, 82, timeout_s=1.0)

        assert result == [80, 82]
        expected_calls = [
            call("example.com", 80, 1.0),
            call("example.com", 81, 1.0),
            call("example.com", 82, 1.0)
        ]
        mock_is_port_open.assert_has_calls(expected_calls)

    @patch('app.tasks.port_scan._is_port_open')
    def test_multiple_ports_none_open(self, mock_is_port_open):
        """Test scanning multiple ports where none are open."""
        mock_is_port_open.return_value = False

        result = port_scan("example.com", 80, 82)

        assert result == []
        assert mock_is_port_open.call_count == 3

    @patch('app.tasks.port_scan._is_port_open')
    def test_custom_timeout(self, mock_is_port_open):
        """Test that custom timeout is passed to _is_port_open."""
        mock_is_port_open.return_value = True

        result = port_scan("example.com", 80, 80, timeout_s=2.5)

        assert result == [80]
        mock_is_port_open.assert_called_once_with("example.com", 80, 2.5)

    @patch('app.tasks.port_scan._is_port_open')
    def test_string_port_conversion(self, mock_is_port_open):
        """Test that string port numbers are converted to integers."""
        mock_is_port_open.return_value = True

        # Pass ports as strings (this might happen from API)
        result = port_scan("example.com", "80", "82")

        assert result == [80, 81, 82]
        expected_calls = [
            call("example.com", 80, 0.15),
            call("example.com", 81, 0.15),
            call("example.com", 82, 0.15)
        ]
        mock_is_port_open.assert_has_calls(expected_calls)

    @patch('app.tasks.port_scan._is_port_open')
    def test_large_port_range(self, mock_is_port_open):
        """Test scanning a larger port range."""
        # Only ports 22, 80, and 443 are open
        def mock_port_check(host, port, timeout):
            return port in [22, 80, 443]

        mock_is_port_open.side_effect = mock_port_check

        result = port_scan("example.com", 20, 445)

        assert result == [22, 80, 443]
        # Should have called _is_port_open for each port in range
        assert mock_is_port_open.call_count == 426  # 445 - 20 + 1

    @patch('app.tasks.port_scan._is_port_open')
    def test_common_ports_scenario(self, mock_is_port_open):
        """Test scanning common ports scenario."""
        # Simulate web server (80, 443 open) and SSH (22 open)
        def mock_port_check(host, port, timeout):
            return port in [22, 80, 443]

        mock_is_port_open.side_effect = mock_port_check

        result = port_scan("webserver.com", 20, 90)

        assert result == [22, 80]  # 443 is outside the range
        assert 22 in result
        assert 80 in result
        assert 443 not in result  # Outside scan range

    @patch('app.tasks.port_scan._is_port_open')
    def test_reverse_port_order(self, mock_is_port_open):
        """Test when from_port equals to_port (single port)."""
        mock_is_port_open.return_value = True

        result = port_scan("example.com", 80, 80)

        assert result == [80]
        mock_is_port_open.assert_called_once_with("example.com", 80, 0.15)

    @patch('app.tasks.port_scan._is_port_open')
    def test_different_hosts(self, mock_is_port_open):
        """Test scanning different host types."""
        mock_is_port_open.return_value = True

        # Test with domain name
        result1 = port_scan("google.com", 80, 80)
        assert result1 == [80]

        # Test with IP address
        result2 = port_scan("8.8.8.8", 53, 53)
        assert result2 == [53]

        # Test with localhost
        result3 = port_scan("localhost", 8080, 8080)
        assert result3 == [8080]

        expected_calls = [
            call("google.com", 80, 0.15),
            call("8.8.8.8", 53, 0.15),
            call("localhost", 8080, 0.15)
        ]
        mock_is_port_open.assert_has_calls(expected_calls)

    @patch('app.tasks.port_scan._is_port_open')
    def test_edge_case_high_ports(self, mock_is_port_open):
        """Test scanning high port numbers."""
        mock_is_port_open.return_value = False

        result = port_scan("example.com", 65530, 65535)

        assert result == []
        assert mock_is_port_open.call_count == 6  # 65535 - 65530 + 1

        # Verify it called with high port numbers
        calls = mock_is_port_open.call_args_list
        assert any(call_args[0][1] == 65535 for call_args in calls)

    @patch('app.tasks.port_scan._is_port_open')
    def test_results_are_sorted(self, mock_is_port_open):
        """Test that results are returned in sorted order."""
        # Make ports open in non-sequential order
        def mock_port_check(host, port, timeout):
            return port in [82, 80, 81, 85, 83]

        mock_is_port_open.side_effect = mock_port_check

        result = port_scan("example.com", 80, 85)

        # Results should be sorted even though ports were found in different order
        assert result == [80, 81, 82, 83, 85]
        assert result == sorted(result)  # Verify they're actually sorted
