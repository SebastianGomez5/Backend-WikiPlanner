from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.db.session import get_db
from app.api import deps
from app.db import models

router = APIRouter()

@router.get("/dashboard")
def get_kpi_dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    user_id = current_user.id

    # ── KPI 1: Tasa de cobertura ─────────────────────────────────────────
    total_tasks = db.query(models.Task).filter(
        models.Task.user_id == user_id
    ).count()

    scheduled_tasks = db.query(models.Task).filter(
        models.Task.user_id == user_id,
        models.Task.status.in_(["Agendada", "Completada"])
    ).count()

    coverage_rate = round((scheduled_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

    # ── KPI 2: Tasa de completado ────────────────────────────────────────
    completed_tasks = db.query(models.Task).filter(
        models.Task.user_id == user_id,
        models.Task.status == "Completada"
    ).count()

    completion_rate = round((completed_tasks / scheduled_tasks * 100), 1) if scheduled_tasks > 0 else 0

    # ── KPI 3: Tasa de aceptación general ───────────────────────────────
    all_decisions = db.query(models.DecisionHistory).filter(
        models.DecisionHistory.user_id == user_id,
        models.DecisionHistory.is_accepted.isnot(None)
    ).all()

    total_decisions = len(all_decisions)
    accepted = sum(1 for d in all_decisions if d.is_accepted is True)
    acceptance_rate = round((accepted / total_decisions * 100), 1) if total_decisions > 0 else 0

    # ── KPI 4: Tendencia semanal de aceptación (últimas 4 semanas) ───────
    weekly_trend = []
    today = datetime.utcnow()

    for i in range(3, -1, -1):  # semanas 3, 2, 1, 0 (esta semana)
        week_start = today - timedelta(weeks=i+1)
        week_end   = today - timedelta(weeks=i)

        week_decisions = db.query(models.DecisionHistory).filter(
            models.DecisionHistory.user_id == user_id,
            models.DecisionHistory.is_accepted.isnot(None),
            models.DecisionHistory.created_at >= week_start,
            models.DecisionHistory.created_at < week_end
        ).all()

        week_total    = len(week_decisions)
        week_accepted = sum(1 for d in week_decisions if d.is_accepted is True)
        week_rate     = round((week_accepted / week_total * 100), 1) if week_total > 0 else 0

        weekly_trend.append({
            "semana": f"S{4 - i}",
            "tasa_aceptacion": week_rate,
            "total_decisiones": week_total
        })

    # ── KPI 5: Confianza promedio de la IA ───────────────────────────────
    blocks_with_confidence = db.query(models.TimeBlock).filter(
        models.TimeBlock.user_id == user_id,
        models.TimeBlock.ai_confidence.isnot(None)
    ).all()

    avg_confidence = 0
    if blocks_with_confidence:
        avg_confidence = round(
            sum(b.ai_confidence for b in blocks_with_confidence) / len(blocks_with_confidence), 2
        )

    # ── KPI 6: Tasa de rechazo repetido ──────────────────────────────────
    # Mide si la IA sigue cometiendo el mismo error (sugerir horas ya rechazadas)
    rejected = [d for d in all_decisions if d.is_accepted is False]
    repeated_rejections = 0

    seen_patterns = {}  # {(task_id, hora): count}
    for d in rejected:
        ctx = d.conflict_context or {}
        task_id = ctx.get("task_id")
        hora_str = ctx.get("scheduled_time", "")
        if task_id and 'T' in hora_str:
            try:
                hora = hora_str.split('T')[1].split(':')[0]
                key = (task_id, hora)
                seen_patterns[key] = seen_patterns.get(key, 0) + 1
            except:
                pass

    repeated_rejections = sum(1 for v in seen_patterns.values() if v > 1)
    repeat_rejection_rate = round((repeated_rejections / len(rejected) * 100), 1) if rejected else 0

    return {
        "resumen": {
            "total_tareas": total_tasks,
            "tareas_completadas": completed_tasks,
            "total_decisiones": total_decisions,
            "confianza_promedio_ia": avg_confidence
        },
        "kpis": {
            "cobertura": coverage_rate,           # % tareas agendadas
            "completado": completion_rate,         # % tareas completadas
            "aceptacion": acceptance_rate,         # % sugerencias aceptadas
            "rechazo_repetido": repeat_rejection_rate  # % errores repetidos de la IA
        },
        "tendencia_semanal": weekly_trend
    }