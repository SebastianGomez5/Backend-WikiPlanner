from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class TaskSimpleInfo(BaseModel):
    title: str
    status: str
    
    model_config = ConfigDict(from_attributes=True)

class TimeBlockBase(BaseModel):
    start_time: datetime
    end_time: datetime
    google_event_id: Optional[str] = None
    is_locked: bool = False

class TimeBlockCreate(TimeBlockBase):
    task_id: UUID

class TimeBlockResponse(TimeBlockBase):
    id: UUID
    task_id: UUID
    user_id: UUID
    
    task: TaskSimpleInfo 

    model_config = ConfigDict(from_attributes=True)