import pytest
from unittest.mock import MagicMock, patch
import socket
from pydantic import ValidationError
from app.schemas.dns_query_request import DNSQueryRequest
from app.tasks.dns_query import dns_query, _resolve, enqueue_dns_query


class TestDNSQueryRequest:
    """Test cases for DNSQueryRequest schema validation."""

    def test_valid_domain(self):
        """Test valid domain names."""
        valid_domains = [
            "google.com",
            "example.org",
            "sub.domain.com",
            "test-site.co.uk",
            "a.b.c.d.com"
        ]
        
        for domain in valid_domains:
            request = DNSQueryRequest(domain=domain)
            assert request.domain == domain.lower()

    def test_domain_converted_to_lowercase(self):
        """Test that domain is converted to lowercase."""
        request = DNSQueryRequest(domain="GoOgLe.CoM")
        assert request.domain == "google.com"

    def test_domain_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        request = DNSQueryRequest(domain="  google.com  ")
        assert request.domain == "google.com"

    def test_empty_domain_raises_error(self):
        """Test that empty domain raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DNSQueryRequest(domain="")
        
        # Pydantic's min_length validation catches this before our custom validator
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_domain_raises_error(self):
        """Test that whitespace-only domain raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DNSQueryRequest(domain="   ")
        
        assert "Domain cannot be empty" in str(exc_info.value)

    def test_domain_with_internal_whitespace_raises_error(self):
        """Test that domain with whitespace raises ValidationError."""
        invalid_domains = [
            "google .com",
            "google\t.com",
            "google\n.com",
            "goo gle.com"
        ]
        
        for domain in invalid_domains:
            with pytest.raises(ValidationError) as exc_info:
                DNSQueryRequest(domain=domain)
            assert "Domain cannot contain whitespace" in str(exc_info.value)

    def test_domain_starting_with_dot_raises_error(self):
        """Test that domain starting with dot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DNSQueryRequest(domain=".google.com")
        
        assert "Domain cannot start or end with a dot" in str(exc_info.value)

    def test_domain_ending_with_dot_raises_error(self):
        """Test that domain ending with dot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DNSQueryRequest(domain="google.com.")
        
        assert "Domain cannot start or end with a dot" in str(exc_info.value)

    def test_domain_too_long_raises_error(self):
        """Test that domain exceeding max length raises ValidationError."""
        long_domain = "a" * 256 + ".com"
        
        with pytest.raises(ValidationError) as exc_info:
            DNSQueryRequest(domain=long_domain)
        
        assert "String should have at most 255 characters" in str(exc_info.value)

    def test_missing_domain_raises_error(self):
        """Test that missing domain raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DNSQueryRequest()
        
        assert "Field required" in str(exc_info.value)


class TestResolveFunction:
    """Test cases for the _resolve helper function."""

    def test_resolve_returns_unique_ips(self):
        """Test that _resolve returns unique IP addresses."""
        with patch('app.tasks.dns_query.socket.getaddrinfo') as mock_getaddrinfo:
            # Mock socket.getaddrinfo to return both IPv4 and IPv6
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, None, None, None, ('142.250.185.46', 0)),
                (socket.AF_INET6, None, None, None, ('2607:f8b0:4004:c07::8a', 0)),
                (socket.AF_INET, None, None, None, ('142.250.185.46', 0)),  # Duplicate
            ]

            result = _resolve("google.com")
            
            assert isinstance(result, list)
            assert len(result) == 2  # Duplicates removed
            assert '142.250.185.46' in result
            assert '2607:f8b0:4004:c07::8a' in result

    def test_resolve_single_ip(self):
        """Test resolving domain with single IP."""
        with patch('app.tasks.dns_query.socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, None, None, None, ('93.184.216.34', 0))
            ]

            result = _resolve("example.com")
            
            assert result == ['93.184.216.34']

    def test_resolve_gaierror_raises_valueerror(self):
        """Test that DNS resolution failure raises ValueError."""
        with patch('app.tasks.dns_query.socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.gaierror(8, "nodename nor servname provided")

            with pytest.raises(ValueError) as exc_info:
                _resolve("nonexistent-domain-12345.com")
            
            assert "Failed to resolve domain" in str(exc_info.value)
            assert "nonexistent-domain-12345.com" in str(exc_info.value)

    def test_resolve_socket_error_raises_valueerror(self):
        """Test that socket error raises ValueError."""
        with patch('app.tasks.dns_query.socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = socket.error("Network unreachable")

            with pytest.raises(ValueError) as exc_info:
                _resolve("example.com")
            
            assert "Network error while resolving" in str(exc_info.value)

    def test_resolve_unexpected_error_raises_valueerror(self):
        """Test that unexpected errors are caught and wrapped."""
        with patch('app.tasks.dns_query.socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(ValueError) as exc_info:
                _resolve("example.com")
            
            assert "Unexpected error resolving" in str(exc_info.value)


class TestDNSQueryTask:
    """Test cases for the dns_query Celery task."""

    def test_dns_query_success(self):
        """Test successful DNS query."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['93.184.216.34', '2606:2800:220:1:248:1893:25c8:1946']

            result = dns_query("example.com")
            
            assert result["domain"] == "example.com"
            assert result["ips"] == ['93.184.216.34', '2606:2800:220:1:248:1893:25c8:1946']
            assert result["ip_count"] == 2
            
            mock_resolve.assert_called_once_with("example.com")

    def test_dns_query_single_ip(self):
        """Test DNS query returning single IP."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['142.250.185.46']

            result = dns_query("google.com")
            
            assert result["domain"] == "google.com"
            assert result["ips"] == ['142.250.185.46']
            assert result["ip_count"] == 1

    def test_dns_query_multiple_ips(self):
        """Test DNS query returning multiple IPs."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_ips = [f'192.0.2.{i}' for i in range(1, 6)]
            mock_resolve.return_value = mock_ips

            result = dns_query("multi-ip-domain.com")
            
            assert result["domain"] == "multi-ip-domain.com"
            assert result["ips"] == mock_ips
            assert result["ip_count"] == 5

    def test_dns_query_resolution_failure(self):
        """Test DNS query when resolution fails."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.side_effect = ValueError("Failed to resolve domain 'bad-domain.com': [Errno 8]")

            with pytest.raises(ValueError) as exc_info:
                dns_query("bad-domain.com")
            
            assert "Failed to resolve domain" in str(exc_info.value)

    def test_dns_query_unexpected_error(self):
        """Test DNS query with unexpected error."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(ValueError) as exc_info:
                dns_query("example.com")
            
            assert "DNS query failed" in str(exc_info.value)


class TestEnqueueDNSQuery:
    """Test cases for the enqueue_dns_query function."""

    def test_enqueue_dns_query_creates_task_and_db_record(self):
        """Test that enqueue_dns_query creates task and database record."""
        with patch('app.tasks.dns_query.dns_query.apply_async') as mock_apply_async:
            # Mock Celery task result
            mock_result = MagicMock()
            mock_result.id = "test-task-123"
            mock_apply_async.return_value = mock_result

            # Mock database session
            mock_db = MagicMock()

            result = enqueue_dns_query("example.com", mock_db)
            
            # Verify Celery task was queued
            mock_apply_async.assert_called_once_with(args=["example.com"])
            
            # Verify database operations
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            
            # Verify return value
            assert result["task_id"] == "test-task-123"
            assert result["status"] == "queued"
            assert result["name"] == "net.dns_query"
            assert result["domain"] == "example.com"

    def test_enqueue_dns_query_task_run_record(self):
        """Test that TaskRun record is created with correct data."""
        with patch('app.tasks.dns_query.dns_query.apply_async') as mock_apply_async:
            mock_result = MagicMock()
            mock_result.id = "task-456"
            mock_apply_async.return_value = mock_result

            mock_db = MagicMock()

            enqueue_dns_query("google.com", mock_db)
            
            # Get the TaskRun object that was added to the database
            call_args = mock_db.add.call_args
            task_run = call_args[0][0]
            
            assert task_run.id == "task-456"
            assert task_run.name == "net.dns_query"
            assert task_run.status == "PENDING"
            assert task_run.args_json == ["google.com"]

    def test_enqueue_multiple_domains(self):
        """Test enqueueing multiple DNS queries."""
        with patch('app.tasks.dns_query.dns_query.apply_async') as mock_apply_async:
            domains = ["example.com", "google.com", "github.com"]
            mock_db = MagicMock()

            for i, domain in enumerate(domains):
                mock_result = MagicMock()
                mock_result.id = f"task-{i}"
                mock_apply_async.return_value = mock_result

                result = enqueue_dns_query(domain, mock_db)
                
                assert result["domain"] == domain
                assert result["task_id"] == f"task-{i}"

            # Verify database operations called for each domain
            assert mock_db.add.call_count == len(domains)
            assert mock_db.commit.call_count == len(domains)


class TestDNSQueryIntegration:
    """Integration tests combining schema validation and task execution."""

    def test_full_flow_valid_domain(self):
        """Test full flow from schema validation to task execution."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['93.184.216.34']

            # 1. Validate schema
            request = DNSQueryRequest(domain="  EXAMPLE.COM  ")
            assert request.domain == "example.com"

            # 2. Execute task
            result = dns_query(request.domain)
            
            assert result["domain"] == "example.com"
            assert result["ips"] == ['93.184.216.34']
            assert result["ip_count"] == 1

    def test_invalid_domain_caught_by_schema(self):
        """Test that invalid domains are caught at schema level."""
        with pytest.raises(ValidationError):
            DNSQueryRequest(domain=".invalid.com")

    def test_domain_normalization_flow(self):
        """Test that domain normalization works through full flow."""
        with patch('app.tasks.dns_query._resolve') as mock_resolve:
            mock_resolve.return_value = ['192.0.2.1']

            # Domain with uppercase and whitespace
            request = DNSQueryRequest(domain="  GoOgLe.COM  ")
            result = dns_query(request.domain)
            
            # Verify normalization happened
            mock_resolve.assert_called_once_with("google.com")
            assert result["domain"] == "google.com"

