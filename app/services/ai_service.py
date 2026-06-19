# Ruta: app/services/ai_service.py

from sqlalchemy.orm import Session
from datetime import date, datetime, time
from uuid import UUID
from app.db import models
from app.ai_engine.csp_solver import CSPSolver
from app.schemas.time_block_schema import TimeBlockCreate
from app.services import time_block_service, user_settings_service
from app.services.google_calendar_service import create_google_event, delete_google_event 

def generate_daily_schedule(db: Session, user_id: UUID, target_date: date):
    settings = user_settings_service.get_user_settings(db, user_id)
    if not settings:
        raise ValueError("El usuario no tiene preferencias configuradas. Por favor, configúralas primero.")

    start_of_day = datetime.combine(target_date, time.min)
    end_of_day = datetime.combine(target_date, time.max)
    
    # 1. Buscar los bloques viejos del día
    old_blocks = db.query(models.TimeBlock).filter(
        models.TimeBlock.user_id == user_id,
        models.TimeBlock.start_time >= start_of_day,
        models.TimeBlock.start_time <= end_of_day
    ).all()
    
    # 2. Limpieza profunda: Borrar de Google y luego de la base local
    for block in old_blocks:
        task = db.query(models.Task).filter(models.Task.id == block.task_id).first()
        if task and task.status == "Agendada":
            task.status = "Pendiente"
            
        if block.google_event_id:
            try:
                delete_google_event(block.google_event_id)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar evento de Google: {e}")
            
        db.delete(block)
    
    db.commit()

    # 3. Traer tareas pendientes y ejecutar la IA
    tasks = db.query(models.Task).filter(
        models.Task.user_id == user_id,
        models.Task.status == "Pendiente"
    ).all()

    if not tasks:
        return {
            "mensaje": "No hay tareas pendientes para agendar en este momento.",
            "tareas_agendadas": 0,
            "tareas_no_agendadas": []
        }

    # Extraemos la memoria de rechazos para el aprendizaje
    rejected_decisions = db.query(models.DecisionHistory).filter(
        models.DecisionHistory.user_id == user_id,
        models.DecisionHistory.is_accepted == False
    ).all()

    # Inyectamos la memoria al motor CSP
    solver = CSPSolver(
        tasks=tasks, 
        user_settings=settings, 
        target_date=target_date, 
        rejected_decisions=rejected_decisions
    )
    
    best_schedule = solver.solve()

    if not best_schedule or len(best_schedule) == 0:
        return {
            "mensaje": "No se pudo agendar ninguna tarea. Revisa que tus preferencias (Ej: Mañana/Tarde) coincidan con el horario de tu jornada laboral en tu perfil.",
            "tareas_agendadas": 0,
            "tareas_no_agendadas": solver.unscheduled_tasks
        }

    created_blocks = []
    for task_id, (start_time, end_time) in best_schedule.items():
        db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
        
        # Google Calendar no bloqueante: si falla, el bloque se crea igual
        g_event_id = None
        try:
            g_event_id = create_google_event(db_task.title, start_time, end_time)
        except Exception as e:
            print(f"⚠️ No se pudo sincronizar con Google Calendar: {e}")

        block_data = TimeBlockCreate(
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            google_event_id=g_event_id,
            is_locked=False,
            ai_confidence=solver.confidence_scores.get(task_id)  # NUEVO
        )
        
        db_block = time_block_service.create_time_block(db, block=block_data, user_id=user_id)
        created_blocks.append(db_block)

        if db_task:
            db_task.status = "Agendada"
    
    db.commit()

    mensaje = "Agenda generada exitosamente."
    if solver.unscheduled_tasks:
        nombres = ", ".join(t["title"] for t in solver.unscheduled_tasks)
        mensaje += f" Sin embargo, {len(solver.unscheduled_tasks)} tarea(s) no pudieron agendarse: {nombres}."

    return {
        "mensaje": mensaje,
        "tareas_agendadas": len(best_schedule),
        "tareas_no_agendadas": solver.unscheduled_tasks
    }