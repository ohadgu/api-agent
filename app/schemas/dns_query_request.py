from pydantic import BaseModel, Field, field_validator


class DNSQueryRequest(BaseModel):
    """Schema for DNS query requests."""

    domain: str = Field(..., min_length=1, max_length=255, example="google.com")

    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        """Basic domain validation."""
        v = v.strip()
        if not v:
            raise ValueError("Domain cannot be empty")

        if any(char in v for char in [' ', '\t', '\n']):
            raise ValueError("Domain cannot contain whitespace")

        if v.startswith('.') or v.endswith('.'):
            raise ValueError("Domain cannot start or end with a dot")

        return v.lower()
