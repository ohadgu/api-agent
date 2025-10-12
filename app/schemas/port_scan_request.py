from pydantic import BaseModel, field_validator, model_validator, Field, ConfigDict


class PortScanRequest(BaseModel):
    """Input for /api/tasks/ports/scan"""
    domain: str = Field(..., example="google.com")
    from_port: int = Field(..., example=20)
    to_port: int = Field(..., example=150)
    timeout_s: float = Field(default=0.15, gt=0, le=5.0)


    @field_validator("from_port", "to_port")
    @classmethod
    def _valid_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


    @model_validator(mode="after")
    def _order_ok(self):
        if self.to_port < self.from_port:
            raise ValueError("to_port must be >= from_port")
        return self


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
