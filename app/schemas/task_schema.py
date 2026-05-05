from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class TaskBase(BaseModel):
    title: str
    duration_minutes: int
    priority: int
    difficulty_level: Optional[str] = None
    category: Optional[str] = None
    energy_level: Optional[str] = None
    is_flexible: bool = True
    deadline: Optional[datetime] = None
    fixed_start_time: Optional[datetime] = None
    preferred_time_of_day: Optional[str] = "Cualquier"

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: UUID
    user_id: UUID
    status: str

    model_config = ConfigDict(from_attributes=True)