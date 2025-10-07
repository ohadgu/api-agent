import pytest
import socket
from unittest.mock import patch, Mock
from app.tasks.dns_query import _resolve, dns_query, enqueue_dns_query


class TestResolveFunction:
    """Tests for the _resolve helper function."""

    def test_resolve_valid_domain(self):
        """Test resolving a valid domain returns IP addresses."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            # Mock getaddrinfo to return IPv4 and IPv6 addresses
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.1', 80)),
                (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('2001:db8::1', 80, 0, 0)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.2', 80))
            ]

            result = _resolve('example.com')

            assert isinstance(result, list)
            assert len(result) == 3
            assert '192.0.2.1' in result
            assert '192.0.2.2' in result
            assert '2001:db8::1' in result

    def test_resolve_domain_normalization(self):
        """Test domain name normalization (strip whitespace and trailing dot)."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.1', 80))
            ]

            # Test with trailing dot and whitespace
            result = _resolve('  example.com.  ')

            mock_getaddrinfo.assert_called_once_with('example.com', None)
            assert '192.0.2.1' in result

    def test_resolve_duplicate_ips(self):
        """Test that duplicate IP addresses are removed."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            # Mock with duplicate IPs
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.1', 80)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.1', 80)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.2', 80))
            ]

            result = _resolve('example.com')

            assert len(result) == 2
            assert '192.0.2.1' in result
            assert '192.0.2.2' in result

    def test_resolve_gaierror(self):
        """Test handling of DNS resolution failures (gaierror)."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror("Name resolution failed")

            with pytest.raises(ValueError, match="Failed to resolve domain 'nonexistent.com'"):
                _resolve('nonexistent.com')

    def test_resolve_socket_error(self):
        """Test handling of socket errors."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.error("Network error")

            with pytest.raises(ValueError, match="Network error while resolving 'example.com'"):
                _resolve('example.com')

    def test_resolve_unexpected_error(self):
        """Test handling of unexpected errors."""
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = Exception("Unexpected error")

            with pytest.raises(ValueError, match="Unexpected error resolving 'example.com'"):
                _resolve('example.com')


class TestDnsQueryTask:
    """Tests for the dns_query Celery task."""

    def test_dns_query_success(self):
        """Test successful DNS query."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['192.0.2.1', '192.0.2.2', '2001:db8::1']

            result = dns_query('example.com')

            assert result['domain'] == 'example.com'
            assert result['ips'] == ['192.0.2.1', '192.0.2.2', '2001:db8::1']
            assert result['primary'] == '192.0.2.1'
            assert result['ip_count'] == 3

    def test_dns_query_single_ip(self):
        """Test DNS query with single IP result."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['192.0.2.1']

            result = dns_query('example.com')

            assert result['domain'] == 'example.com'
            assert result['ips'] == ['192.0.2.1']
            assert result['primary'] == '192.0.2.1'
            assert result['ip_count'] == 1

    def test_dns_query_no_ips(self):
        """Test DNS query with no IP results."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = []

            result = dns_query('example.com')

            assert result['domain'] == 'example.com'
            assert result['ips'] == []
            assert result['primary'] is None
            assert result['ip_count'] == 0

    def test_dns_query_sorts_ips(self):
        """Test that IP addresses are sorted in the result."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['192.0.2.3', '192.0.2.1', '192.0.2.2']

            result = dns_query('example.com')

            assert result['ips'] == ['192.0.2.1', '192.0.2.2', '192.0.2.3']
            assert result['primary'] == '192.0.2.3'  # First in original order (before sorting)

    def test_dns_query_strips_domain(self):
        """Test that domain is stripped of whitespace."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['192.0.2.1']

            result = dns_query('  example.com  ')

            assert result['domain'] == 'example.com'
            mock_resolve.assert_called_once_with('example.com')

    def test_dns_query_empty_domain(self):
        """Test DNS query with empty domain raises ValueError."""
        with pytest.raises(ValueError, match="Domain cannot be empty"):
            dns_query('')

    def test_dns_query_whitespace_domain(self):
        """Test DNS query with whitespace-only domain raises ValueError."""
        with pytest.raises(ValueError, match="Domain cannot be empty"):
            dns_query('   ')

    def test_dns_query_none_domain(self):
        """Test DNS query with None domain raises ValueError."""
        with pytest.raises(ValueError, match="Domain cannot be empty"):
            dns_query(None)

    def test_dns_query_resolution_failure(self):
        """Test DNS query when resolution fails."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.side_effect = ValueError("Failed to resolve domain 'nonexistent.com'")

            with pytest.raises(ValueError, match="Failed to resolve domain 'nonexistent.com'"):
                dns_query('nonexistent.com')

    def test_dns_query_unexpected_error(self):
        """Test DNS query with unexpected error."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(ValueError, match="DNS query failed for 'example.com'"):
                dns_query('example.com')


class TestEnqueueDnsQuery:
    """Tests for the enqueue_dns_query function."""

    @patch('app.tasks.dns_query.dns_query')
    def test_enqueue_dns_query_success(self, mock_task):
        """Test successful enqueueing of DNS query."""
        # Mock the Celery task
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result
        mock_task.name = 'net.dns_query'

        # Mock database session
        mock_db = Mock()

        result = enqueue_dns_query('example.com', mock_db)

        # Verify task was called with correct arguments
        mock_task.apply_async.assert_called_once_with(args=['example.com'])

        # Verify database record was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify return value
        assert result['task_id'] == 'test-task-id'
        assert result['status'] == 'queued'
        assert result['name'] == 'net.dns_query'
        assert result['domain'] == 'example.com'

    @patch('app.tasks.dns_query.dns_query')
    def test_enqueue_dns_query_creates_task_run(self, mock_task):
        """Test that a TaskRun record is created with correct data."""
        # Mock the Celery task
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_task.apply_async.return_value = mock_result
        mock_task.name = 'net.dns_query'

        # Mock database session and TaskRun
        mock_db = Mock()

        with patch('app.infra.models.TaskRun') as mock_task_run_class:
            mock_task_run = Mock()
            mock_task_run_class.return_value = mock_task_run

            enqueue_dns_query('example.com', mock_db)

            # Verify TaskRun was created with correct arguments
            mock_task_run_class.assert_called_once_with(
                id='test-task-id',
                name='net.dns_query',
                status='PENDING',
                args_json=['example.com']
            )

            # Verify TaskRun was added to database
            mock_db.add.assert_called_once_with(mock_task_run)


class TestDnsQueryIntegration:
    """Integration tests using real socket operations."""

    def test_resolve_localhost(self):
        """Test resolving localhost (should work on any system)."""
        result = _resolve('localhost')

        assert isinstance(result, list)
        assert len(result) > 0
        # localhost should resolve to loopback addresses
        assert any(ip in ['127.0.0.1', '::1'] for ip in result)

    def test_dns_query_localhost(self):
        """Test full DNS query for localhost."""
        result = dns_query('localhost')

        assert result['domain'] == 'localhost'
        assert isinstance(result['ips'], list)
        assert len(result['ips']) > 0
        assert result['primary'] is not None
        assert result['ip_count'] > 0

        # Should contain loopback addresses
        assert any(ip in ['127.0.0.1', '::1'] for ip in result['ips'])


# Pytest fixtures for common test data
@pytest.fixture
def sample_domain():
    """Sample domain for testing."""
    return 'example.com'


@pytest.fixture
def sample_ips():
    """Sample IP addresses for testing."""
    return ['192.0.2.1', '192.0.2.2', '2001:db8::1']


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    return Mock()
