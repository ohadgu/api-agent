from typing import Optional
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, TIMESTAMP, Integer, JSON, func

class Base(DeclarativeBase):
    pass

class TaskRun(Base):
    __tablename__ = "task_runs"
    id:          Mapped[str] = mapped_column(String(64), primary_key=True)
    name:        Mapped[str] = mapped_column(String(128), index=True)
    status:      Mapped[str] = mapped_column(String(32), index=True)
    created_at:  Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at:  Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    args_json:   Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    kwargs_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error:       Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    queue:       Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


