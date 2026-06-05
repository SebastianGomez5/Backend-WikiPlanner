# Ruta: app/api/endpoints/decisions.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.schemas import decision_history_schema
from app.services import decision_history_service
from app.db.session import get_db
from app.api import deps
from app.db import models

# Importamos la función para borrar en Google
from app.services.google_calendar_service import delete_google_event

router = APIRouter()

@router.post("/", response_model=decision_history_schema.DecisionHistoryResponse)
def log_decision(
    decision: decision_history_schema.DecisionHistoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Registra la decisión. Si reprograma, libera el espacio. 
    Si completa, la sella como finalizada para siempre.
    """
    # 1. Guardamos el historial para el Machine Learning
    record = decision_history_service.create_decision_record(db, decision, current_user.id)
    
    # 2. Orquestación: Qué hacer con la tarea según la decisión
    task_id_str = decision.conflict_context.get("task_id")
    
    if task_id_str:
        task = db.query(models.Task).filter(
            models.Task.id == task_id_str, 
            models.Task.user_id == current_user.id
        ).first()
        
        if task:
            if decision.is_accepted is False:
                # REPROGRAMAR: Liberamos el espacio
                task.status = "Pendiente"
                
                blocks_to_delete = db.query(models.TimeBlock).filter(
                    models.TimeBlock.task_id == task_id_str
                ).all()
                
                for block in blocks_to_delete:
                    if block.google_event_id:
                        delete_google_event(block.google_event_id)
                    db.delete(block)
            else:
                # COMPLETADA: La marcamos como finalizada para siempre
                task.status = "Completada"
                
            # Confirmamos todos los cambios en la base de datos
            db.commit()

    return record

@router.get("/", response_model=List[decision_history_schema.DecisionHistoryResponse])
def get_history(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Devuelve el historial de decisiones del usuario."""
    return decision_history_service.get_user_decisions(db, current_user.id, skip, limit)