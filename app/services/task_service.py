from sqlalchemy.orm import Session
from app.db import models
from app.schemas import task_schema
from uuid import UUID

def create_task(db: Session, task: task_schema.TaskCreate, user_id: UUID):
    
    db_task = models.Task(**task.model_dump(), user_id=user_id)
    
    db.add(db_task)
    db.commit()
    
    db.refresh(db_task)
    
    return db_task