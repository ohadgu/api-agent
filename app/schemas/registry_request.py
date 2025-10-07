from pydantic import BaseModel, Field
from typing import Optional, Literal


class RegistryRequest(BaseModel):
    """Schema for Windows Registry operations."""

    action: Literal["GET", "SET", "DELETE"] = Field(..., description="Registry action: GET to read, SET to write, DELETE to remove")
    key: str = Field( ..., min_length=1, description="Registry key path (e.g., 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Example')")
    value_name: Optional[str] = Field(default=None, description="Registry value name (required for GET/SET/DELETE operations)")
    value_data: Optional[str] = Field(default=None, description="Registry value data (required for GET/SET/DELETE operations)")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "GET",
                "key": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion",
                "value_name": "ProductName"
            }
        }
