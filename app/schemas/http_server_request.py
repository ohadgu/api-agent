from pydantic import BaseModel, Field
from typing import Optional


class HTTPServerRequest(BaseModel):
    """Schema for creating a dynamic HTTP server."""

    page_uri: str = Field(...,min_length=1,
                          description="URI path to serve (e.g., '/test', '/index.html')")
    response_data: str = Field(...,
                               description="Data/content to return when the page is accessed")
    timeout_seconds: Optional[int] = Field(default=300, ge=10, le=3600,
                                           description="How long to keep the server running (10-3600 seconds, default: 300)")

    class Config:
        json_schema_extra = {
            "example": {
                "page_uri": "/test",
                "response_data": "<h1>Hello from HTTP server!</h1><p>Your visit has been tracked!</p>",
                "timeout_seconds": 300
            }
        }
