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


    rejected = [d for d in all_decisions if d.is_accepted is False]
    repeated_rejections = 0

    seen_patterns = {}  
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


@router.get("/balance")
def get_balance_stats(
    period: str = "day",  # "day", "week", "month"
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    Retorna el balance Ocio/Productividad según el período solicitado:
    - day: día de hoy (desde las 00:00 hasta las 23:59 de hoy)
    - week: semana actual (desde el lunes 00:00 hasta el domingo 23:59)
    - month: mes actual (desde el día 1 00:00 hasta fin de mes 23:59)
    """
    user_id = current_user.id
    now = datetime.now()

    if period == "day":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        label_periodo = "Hoy"
        label_prep = "hoy"
    elif period == "month":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = next_month - timedelta(microseconds=1)
        label_periodo = "Este mes"
        label_prep = "este mes"
    else:  # "week"
        period = "week"
        week_start = now - timedelta(days=now.weekday())
        period_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        label_periodo = "Esta semana"
        label_prep = "esta semana"

    
    blocks = (
        db.query(models.TimeBlock, models.Task)
        .join(models.Task, models.TimeBlock.task_id == models.Task.id)
        .filter(
            models.TimeBlock.user_id == user_id,
            models.TimeBlock.start_time >= period_start,
            models.TimeBlock.start_time <= period_end,
        )
        .all()
    )

    
    CATEGORIAS = ["Trabajo", "Estudio", "Salud", "Hogar", "Ocio"]
    minutos_por_categoria = {cat: 0 for cat in CATEGORIAS}

    for block, task in blocks:
        cat = task.category if task.category in CATEGORIAS else "Trabajo"
        duracion = int((block.end_time - block.start_time).total_seconds() / 60)
        minutos_por_categoria[cat] += duracion

    total_minutos = sum(minutos_por_categoria.values())

    
    porcentajes = {}
    for cat, mins in minutos_por_categoria.items():
        porcentajes[cat] = round((mins / total_minutos * 100), 1) if total_minutos > 0 else 0

    
    PRODUCTIVIDAD = ["Trabajo", "Estudio"]
    BIENESTAR     = ["Salud", "Hogar"]
    OCIO_CATS     = ["Ocio"]
    PRODUCTIVIDAD = ["Trabajo", "Estudio"]
    BIENESTAR     = ["Salud", "Hogar"]
    OCIO_CATS     = ["Ocio"]

    pct_productividad = sum(porcentajes[c] for c in PRODUCTIVIDAD)
    pct_bienestar     = sum(porcentajes[c] for c in BIENESTAR)
    pct_ocio          = sum(porcentajes[c] for c in OCIO_CATS)

    if total_minutos == 0:
        mensaje = f"Aún no tienes actividades agendadas para {label_prep}. ¡Genera tu agenda y comienza!"
        estado = "sin_datos"
    elif pct_productividad >= 85:
        mensaje = (
            f"{label_periodo} dedicaste {pct_productividad:.0f}% a Trabajo/Estudio y solo "
            f"{pct_ocio:.0f}% a Ocio. Considera agendar más tiempo de descanso para evitar el agotamiento."
        )
        estado = "desequilibrio_productividad"
    elif pct_ocio >= 50:
        mensaje = (
            f"{label_periodo} dedicaste {pct_ocio:.0f}% a Ocio. "
            f"¿Hay tareas pendientes importantes que puedas priorizar?"
        )
        estado = "desequilibrio_ocio"
    elif 60 <= pct_productividad <= 80 and pct_ocio >= 10:
        mensaje = (
            f"¡Buen balance {label_prep}! {pct_productividad:.0f}% productivo y "
            f"{pct_ocio:.0f}% de descanso. Sigue así."
        )
        estado = "equilibrado"
    else:
        mensaje = (
            f"{label_periodo}: {pct_productividad:.0f}% en Trabajo/Estudio, "
            f"{pct_bienestar:.0f}% en Salud/Hogar y {pct_ocio:.0f}% en Ocio."
        )
        estado = "neutral"

    return {
        "periodo": period,
        "label_periodo": label_periodo,
        "label_prep": label_prep,
        "fecha_inicio": period_start.strftime("%Y-%m-%d"),
        "fecha_fin": period_end.strftime("%Y-%m-%d"),
        "total_minutos_agendados": total_minutos,
        "total_horas_agendadas": round(total_minutos / 60, 1),
        "por_categoria": [
            {
                "categoria": cat,
                "minutos": minutos_por_categoria[cat],
                "horas": round(minutos_por_categoria[cat] / 60, 1),
                "porcentaje": porcentajes[cat],
            }
            for cat in CATEGORIAS
        ],
        "resumen_grupos": {
            "productividad": round(pct_productividad, 1),
            "bienestar": round(pct_bienestar, 1),
            "ocio": round(pct_ocio, 1),
        },
        "mensaje": mensaje,
        "estado": estado,   # sin_datos | equilibrado | desequilibrio_productividad | desequilibrio_ocio | neutral
    }
