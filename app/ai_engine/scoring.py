from datetime import datetime
from app.ai_engine.learning import get_category_penalty

def calculate_slot_penalty(task, slot_start: datetime, user_profile=None):
    penalty = 0
    hora_del_dia = slot_start.hour

    # 1. Energía y dificultad
    if task.energy_level == "Alto" or task.difficulty_level == "Alta":
        if hora_del_dia >= 18:
            penalty += 50
        elif hora_del_dia >= 15:
            penalty += 20

    # 2. Categoría
    if task.category in ["Ocio", "Salud"]:
        if hora_del_dia < 12:
            penalty += 15

    # 3. Aprendizaje generalizado del usuario
    penalty += get_category_penalty(task, slot_start, user_profile)

    # 4. Tareas fijas: sin penalización (esto debe ir AL FINAL y separado)
    if not task.is_flexible:
        penalty = 0

    return penalty