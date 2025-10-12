from pydantic import BaseModel, Field, field_validator


class HTTPRequest(BaseModel):
    method: str = Field(default="GET")
    domain: str = Field(..., min_length=1, max_length=255, example="example.com")
    port: int = Field(default=80)
    path: str = Field(default="/")
    body: dict | None = Field(default=None)
    params: dict | None = Field(default=None)
    timeout_s: float = Field(default=2.0)


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


    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        method = v.upper().strip()
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise ValueError(f"Only GET/POST/PUT/DELETE methods are supported, got: {method}")
        return method

    class Config:
        json_schema_extra = {
            "example": {
                "method": "GET",
                "domain": "example.com",
                "port": 80,
                "path": "/",
                "body": {},
                "params": {},
                "timeout_s": 3.0
            }
        }



    




