from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import task_schema
from app.services import task_service
from app.db.session import get_db
from typing import List
from uuid import UUID

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

@router.get("/pending", response_model=List[task_schema.TaskResponse])
def get_pending_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    return task_service.get_pending_tasks(db=db, user_id=current_user.id)

@router.put("/{task_id}", response_model=task_schema.TaskResponse)
def update_task(
    task_id: UUID,
    task: task_schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    db_task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()

    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    for key, value in task.model_dump().items():
        setattr(db_task, key, value)

    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    db_task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    ).first()

    if not db_task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    db.delete(db_task)
    db.commit()