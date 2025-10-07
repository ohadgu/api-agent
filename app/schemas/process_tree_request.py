from pydantic import BaseModel, Field


class ProcessTreeRequest(BaseModel):
    """Input for /api/tasks/process/tree"""
    pid: int = Field(..., gt=0, lt=2147483647, description="Root process ID to get tree from", example=1)
