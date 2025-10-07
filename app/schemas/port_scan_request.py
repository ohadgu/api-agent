from pydantic import BaseModel, field_validator, model_validator, Field, ConfigDict


class PortScanRequest(BaseModel):
    """Input for /api/tasks/ports/scan"""
    host: str = Field(..., description="Target domain name or IP address", example="google.com")
    from_port: int = Field(..., description="Starting port number", example=20)
    to_port: int = Field(..., description="Ending port number", example=150)
    timeout_s: float = Field(default=0.15, gt=0, le=5.0, description="Per-port connect timeout in seconds")

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
