from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import task_schema
from app.services import task_service
from app.db.session import get_db

from app.api import deps
from app.db import models
router = APIRouter()

@router.post("/", response_model=task_schema.TaskResponse)
def create_task(
    task: task_schema.TaskCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    
    return task_service.create_task(db=db, task=task, user_id=current_user.id)