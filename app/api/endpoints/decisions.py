# Ruta: app/api/endpoints/decisions.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID as UUIDType
from app.schemas import decision_history_schema
from app.services import decision_history_service
from app.db.session import get_db
from app.api import deps
from app.db import models
from app.services.google_calendar_service import delete_google_event

router = APIRouter()

@router.post("/", response_model=decision_history_schema.DecisionHistoryResponse)
def log_decision(
    decision: decision_history_schema.DecisionHistoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Registra la decisión del usuario respecto a una sugerencia de la IA.
    - Si rechaza (is_accepted=False): libera el bloque y reprograma la tarea.
    - Si acepta (is_accepted=True): marca la tarea como completada.
    """
    task_id_str = decision.conflict_context.get("task_id")
    task = None

    if task_id_str:
        task = db.query(models.Task).filter(
            models.Task.id == task_id_str,
            models.Task.user_id == current_user.id
        ).first()

    if task:
        # 1. Enriquecemos conflict_context con datos reales de la tarea
        # para que build_user_penalty_profile() siempre tenga "category"
        decision.conflict_context = {
            **decision.conflict_context,
            "category": task.category,
            "energy_level": task.energy_level,
            "difficulty_level": task.difficulty_level,
            "priority": task.priority,
        }

        # 2. Copiamos el confidence_score desde el TimeBlock al DecisionHistory
        # para registrar qué tan segura estaba la IA al hacer esta sugerencia
        try:
            task_uuid = UUIDType(task_id_str)
            existing_block = db.query(models.TimeBlock).filter(
                models.TimeBlock.task_id == task_uuid,
                models.TimeBlock.user_id == current_user.id
            ).first()

            if existing_block and existing_block.ai_confidence is not None:
                decision.confidence_score = existing_block.ai_confidence
        except (ValueError, AttributeError):
            # Si el UUID es inválido, simplemente no copiamos la confianza
            pass

    # 3. Guardamos el registro enriquecido en el historial
    record = decision_history_service.create_decision_record(db, decision, current_user.id)

    # 4. Orquestamos el estado de la tarea según la decisión
    if task:
        if decision.is_accepted is False:
            # REPROGRAMAR: liberamos el bloque y ponemos la tarea como pendiente
            task.status = "Pendiente"

            blocks_to_delete = db.query(models.TimeBlock).filter(
                models.TimeBlock.task_id == task_id_str
            ).all()

            for block in blocks_to_delete:
                if block.google_event_id:
                    try:
                        delete_google_event(block.google_event_id)
                    except Exception as e:
                        print(f"⚠️ No se pudo eliminar evento de Google: {e}")
                db.delete(block)
        else:
            # COMPLETADA: sellamos la tarea como finalizada
            task.status = "Completada"

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