
def get_franja(hora: int) -> str:
    """
    Clasifica una hora del día en una franja horaria.
    Esto unifica el criterio entre el perfil de aprendizaje y el scoring.
    """
    if 6 <= hora < 12:
        return "Mañana"
    elif 12 <= hora < 18:
        return "Tarde"
    else:
        return "Noche"


def build_user_penalty_profile(rejected_decisions):
    """
    Analiza el historial de decisiones rechazadas y construye un perfil
    de penalización generalizado por (categoria, franja_horaria).

    En lugar de recordar solo "el usuario rechazó la tarea X a las 6am",
    aprende patrones como "el usuario tiende a rechazar tareas de categoría
    'Salud' en la Mañana", aplicable a CUALQUIER tarea de esa categoría,
    no solo a la tarea original.

    Returns:
        dict: { (categoria, franja): penalizacion_acumulada }
    """
    profile = {}

    for decision in rejected_decisions:
        ctx = decision.conflict_context or {}
        categoria = ctx.get("category")
        hora_str = ctx.get("scheduled_time")

        if not categoria or not hora_str or 'T' not in hora_str:
            continue

        try:
            hora = int(hora_str.split('T')[1].split(':')[0])
        except (ValueError, IndexError):
            continue

        franja = get_franja(hora)
        key = (categoria, franja)

        # Cada rechazo acumula +25 puntos de penalización para ese
        # par (categoria, franja). Esto permite que patrones repetidos
        # pesen más que rechazos aislados.
        profile[key] = profile.get(key, 0) + 25

    return profile


def get_category_penalty(task, slot_start, user_profile):
    """
    Consulta el perfil del usuario para saber si la categoría de esta
    tarea, en esta franja horaria, tiene penalización aprendida.
    """
    if not user_profile or not task.category:
        return 0

    franja = get_franja(slot_start.hour)
    key = (task.category, franja)

    return user_profile.get(key, 0)