from datetime import datetime
from app.ai_engine.learning import get_category_penalty

def calculate_slot_penalty(task, slot_start: datetime, user_profile=None):
    penalty, _ = calculate_slot_penalty_with_reasons(task, slot_start, user_profile)
    return penalty

def calculate_slot_penalty_with_reasons(task, slot_start: datetime, user_profile=None):
    """
    Calcula la penalización de un slot y genera las razones explicativas (XAI).
    """
    penalty = 0
    reasons = []
    hora = slot_start.hour

    if not task.is_flexible:
        return 0, ["Es un evento fijo programado a la hora exacta solicitada."]

    # 1. Preferencia de horario (Momento ideal)
    pref = getattr(task, "preferred_time_of_day", "Cualquier")
    if pref == "Mañana" and 6 <= hora < 12:
        reasons.append("Coincide con tu horario preferido (Mañana).")
    elif pref == "Tarde" and 12 <= hora < 18:
        reasons.append("Coincide con tu horario preferido (Tarde).")
    elif pref == "Noche" and hora >= 18:
        reasons.append("Coincide con tu horario preferido (Noche).")
    elif pref and pref != "Cualquier":
        reasons.append(f"Se ubicó aquí para evitar colisiones con otras tareas de tu día.")

    # 2. Exigencia de Energía y Dificultad
    energy = getattr(task, "energy_level", None)
    difficulty = getattr(task, "difficulty_level", None)
    if energy == "Alto" or difficulty == "Alta":
        if hora >= 18:
            penalty += 50
            reasons.append("Se movió a la noche por falta de espacio temprano, aunque requiere alta energía.")
        elif hora >= 15:
            penalty += 20
            reasons.append("Se agendó en la tarde tras agotar franjas matutinas de mayor concentración.")
        else:
            reasons.append("Aprovecha tu pico de energía y concentración en la primera mitad del día.")
    elif energy == "Bajo":
        if hora >= 15:
            reasons.append("Actividad ligera ideal para momentos de menor energía.")

    # 3. Categoría (Ocio / Salud vs Productividad)
    if task.category in ["Ocio", "Salud"]:
        if hora < 12:
            penalty += 15
            reasons.append("Se colocó en la mañana para garantizar tiempo de descanso en tu jornada.")
        else:
            reasons.append(f"Horario ideal para {task.category.lower()}, facilitando la desconexión.")
    elif task.category in ["Trabajo", "Estudio"]:
        if hora < 14:
            reasons.append(f"Franja de alto rendimiento recomendada para {task.category.lower()}.")

    # 4. Hábitos aprendidos (DecisionHistory)
    prof_penalty = get_category_penalty(task, slot_start, user_profile)
    if prof_penalty > 0:
        penalty += prof_penalty
        reasons.append("Ajuste por hábitos pasados: se asignó aquí al ser la mejor alternativa viable.")
    elif user_profile:
        reasons.append("Respeta tus patrones y hábitos previos.")

    return penalty, reasons

def calculate_confidence(penalty: float) -> float:
    """
    Convierte la penalización de un slot en un puntaje de confianza.

    A menor penalización (slot ideal), mayor confianza.
    A mayor penalización (slot forzado/incómodo), menor confianza.
    """
    confidence = 1.0 - (penalty / 100)
    return round(max(0.1, min(1.0, confidence)), 2)

def generate_explanation(task, slot_start: datetime, penalty: float, reasons: list, confidence: float) -> str:
    """
    Combina las razones técnicas en una explicación en lenguaje natural para el usuario (Explainable AI - XAI).
    """
    pct = int(confidence * 100)

    if not task.is_flexible:
        hora_fmt = slot_start.strftime("%I:%M %p").lstrip("0")
        return f"Evento fijo agendado a tu hora exacta ({hora_fmt}). Confianza: 100%."

    if not reasons:
        reasons = ["Franja óptima disponible sin conflictos en tu jornada laboral."]

    # Tomar las 2 razones más directas
    narrativa = " ".join(reasons[:2])

    if penalty == 0:
        prefijo = f"Horario óptimo ({pct}% de confianza):"
    elif penalty <= 25:
        prefijo = f"Buen encaje ({pct}% de confianza):"
    else:
        prefijo = f"Mejor horario disponible ({pct}% de confianza):"

    return f"{prefijo} {narrativa}"