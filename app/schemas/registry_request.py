from pydantic import BaseModel, Field, field_validator

class RegistryRequest(BaseModel):
    action: str = Field(..., description="Action to perform: GET, SET, DELETE")
    key: str = Field(..., min_length=1, description="Registry key path (must not be empty)")
    value_name: str = Field(..., min_length=1, description="Registry value name (must not be empty)")
    value_data: str | None = Field(None, description="Registry value data (required for SET)")


    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        action = v.upper().strip()
        if action not in {"GET", "SET", "DELETE"}:
            raise ValueError(f"Only GET/SET/DELETE actions are supported, got: {action}")
        return action

    class Config:
        json_schema_extra = {
            "example": {
                "action": "GET",
                "key": "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders",
                "value_name": "Fonts"
            }
        }


# from pydantic import BaseModel, Field
# from typing import Optional, Literal


# class RegistryRequest(BaseModel):
#     """Schema for Windows Registry operations."""

#     action: Literal["GET", "SET", "DELETE"] = Field(..., description="Registry action: GET to read, SET to write, DELETE to remove")
#     key: str = Field( ..., min_length=1, description="Registry key path (e.g., 'HKEY_LOCAL_MACHINE\\SOFTWARE\\Example')")
#     value_name: Optional[str] = Field(default=None, description="Registry value name (required for GET/SET/DELETE operations)")
#     value_data: Optional[str] = Field(default=None, description="Registry value data (required for GET/SET/DELETE operations)")

#     class Config:
#         json_schema_extra = {
#             "example": {
#                 "action": "GET",
#                 "key": "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion",
#                 "value_name": "ProductName"
#             }
#         }
