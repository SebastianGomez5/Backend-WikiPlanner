from datetime import datetime
from app.ai_engine.learning import get_category_penalty

def calculate_slot_penalty(task, slot_start: datetime, user_profile=None):
    # ... (sin cambios, queda igual que ya lo tienes)
    penalty = 0
    hora_del_dia = slot_start.hour

    if task.energy_level == "Alto" or task.difficulty_level == "Alta":
        if hora_del_dia >= 18:
            penalty += 50
        elif hora_del_dia >= 15:
            penalty += 20

    if task.category in ["Ocio", "Salud"]:
        if hora_del_dia < 12:
            penalty += 15

    penalty += get_category_penalty(task, slot_start, user_profile)

    if not task.is_flexible:
        penalty = 0

    return penalty

def calculate_confidence(penalty: float) -> float:
    """
    Convierte la penalización de un slot en un puntaje de confianza.

    A menor penalización (slot ideal), mayor confianza.
    A mayor penalización (slot forzado/incómodo), menor confianza.

    El resultado se limita entre 0.1 y 1.0 para evitar extremos absolutos:
    - 0.1 representa que la IA sabe que es una mala asignación, pero no
      hubo otra opción (nunca decimos "0% seguro" porque igual se agendó).
    - 1.0 representa la asignación ideal (penalización = 0).
    """
    confidence = 1.0 - (penalty / 100)
    return round(max(0.1, min(1.0, confidence)), 2)