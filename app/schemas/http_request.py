from typing import Optional, Dict, Any
import re
from pydantic import BaseModel, field_validator, Field, ConfigDict

# Security constants
MAX_TIMEOUT = 30.0


class HTTPRequest(BaseModel):
    """HTTP Request schema with essential validation."""

    method: str = Field(..., description="HTTP method", example="GET")
    domain: str = Field(..., description="Target domain name or IP address", example="example.com")
    port: int = Field(..., ge=1, le=65535, description="Port number (1-65535)", example=80)
    path: str = Field(default="/", description="URL path", example="/")
    body: Optional[Dict[str, Any] | str] = Field(default=None, description="Request body")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers")
    https: bool = Field(default=False, description="Force HTTPS", example=False)
    timeout_s: float = Field(default=8.0, gt=0, le=MAX_TIMEOUT, description="Request timeout in seconds")
    params: Optional[Dict[str, str]] = Field(default=None, description="URL parameters")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        method = v.upper().strip()
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise ValueError(f"Only GET/POST/PUT/DELETE methods are supported, got: {method}")
        return method

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        domain = v.strip().lower()
        if not domain:
            raise ValueError("Domain cannot be empty")

        # Regex validation for domain format
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$', domain):
            raise ValueError(f"Invalid domain format: {domain}")

        return domain

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v or v.strip() == "":
            return "/"
        path = v.strip()
        if not path.startswith("/"):
            path = "/" + path
        return path

    def build_url(self) -> str:
        """Build URL from validated components."""
        scheme = "https" if self.https or self.port == 443 else "http"
        base = f"{scheme}://{self.domain}"

        # Include port only if non-standard for the scheme
        if (scheme == "http" and self.port != 80) or (scheme == "https" and self.port != 443):
            base = f"{base}:{self.port}"

        return base + self.path

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "method": "GET",
                "domain": "example.com",
                "port": 80,
                "path": "/",
                "body": {},
                "headers": {},
                "https": False,
                "timeout_s": 8.0,
                "params": {}
            }
        }
    )
