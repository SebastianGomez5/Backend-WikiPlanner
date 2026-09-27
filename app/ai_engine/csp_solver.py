import time
from datetime import datetime, timedelta
from app.ai_engine.scoring import calculate_slot_penalty, calculate_confidence
from app.ai_engine.learning import build_user_penalty_profile

class CSPSolver:
    def __init__(self, tasks, user_settings, target_date, rejected_decisions=None, external_events=None):
        self.tasks = tasks
        self.settings = user_settings
        self.target_date = target_date
        
        work_start = self.settings.work_start_time
        work_end = self.settings.work_end_time
        
        self.day_start = datetime.combine(self.target_date, work_start)
        self.day_end = datetime.combine(self.target_date, work_end)
        
        self.best_schedule = {}

        self.rejected_decisions = rejected_decisions or []

        self.user_profile = build_user_penalty_profile(self.rejected_decisions)

        self.unscheduled_tasks = []
        self.confidence_scores = {}
        self.external_events = external_events or []

    def solve(self):
        self.tasks.sort(key=lambda t: (t.is_flexible, -t.priority, -t.duration_minutes))
        schedule = {}

        self._backtrack(0, schedule)

        self.unscheduled_tasks = []
        for task in self.tasks:
            if task.id not in schedule:
                reason, suggestion = self._diagnose_unscheduled(task)
                self.unscheduled_tasks.append({
                    "task_id": str(task.id),
                    "title": task.title,
                    "reason": reason,
                    "suggestion": suggestion
                })

        self.confidence_scores = {}
        tasks_by_id = {t.id: t for t in self.tasks}
        for task_id, (slot_start, _slot_end) in schedule.items():
            task = tasks_by_id[task_id]
            penalty = calculate_slot_penalty(task, slot_start, self.user_profile)
            self.confidence_scores[task_id] = calculate_confidence(penalty)

        return schedule
        
    def _diagnose_unscheduled(self, task):
        """
        Determina POR QUÉ una tarea no pudo agendarse y qué SUGERENCIA
        práctica puede seguir el usuario para resolverlo.
        """
        now = datetime.now()
        is_today = (self.target_date == now.date())

        if not task.is_flexible and task.fixed_start_time:
            start = task.fixed_start_time.replace(tzinfo=None)
            if is_today and start < now:
                return (
                    "La hora fija asignada a este evento ya pasó el día de hoy.",
                    "Edita la tarea y ajusta la hora de inicio a una hora futura."
                )

        possible_slots = self._get_possible_slots(task)

        if not possible_slots:
            if is_today:
                now_hour = now.hour
                if now >= self.day_end:
                    return (
                        "Tu jornada laboral configurada para hoy ya ha finalizado.",
                        "Ve a tu Perfil para ampliar tu horario laboral o mueve la fecha límite de la tarea para mañana."
                    )
                if task.preferred_time_of_day == "Mañana" and now_hour >= 12:
                    return (
                        "El lapso de la 'Mañana' ya terminó para el día de hoy.",
                        "Edita el Momento Ideal a 'Tarde', 'Noche' o 'Cualquier' para aprovechar el resto del día."
                    )
                if task.preferred_time_of_day == "Tarde" and now_hour >= 18:
                    return (
                        "El lapso de la 'Tarde' ya terminó para el día de hoy.",
                        "Cambia el Momento Ideal a 'Noche' o 'Cualquier', o amplía la fecha límite para mañana."
                    )

            if task.deadline:
                return (
                    f"El plazo límite fijado no deja suficiente espacio continuo para sus {task.duration_minutes} min.",
                    "Edita la tarea para ampliar su fecha límite (ej. para mañana) o reduce su duración a menos minutos."
                )
            if task.preferred_time_of_day and task.preferred_time_of_day != "Cualquier":
                return (
                    f"Tu preferencia '{task.preferred_time_of_day}' no cuenta con {task.duration_minutes} min libres continuos en tu jornada.",
                    "Cambia el Momento Ideal a 'Cualquier' para que la IA aproveche cualquier hueco libre del día."
                )
            return (
                f"No quedan franjas horarias disponibles de {task.duration_minutes} min dentro de tu jornada laboral.",
                "Reduce la duración de la tarea (ej. a 15 o 30 min) o amplía tu horario en tu Perfil."
            )

        return (
            "Tu día ya está saturado con otras tareas de mayor prioridad o eventos externos.",
            "Aumenta la prioridad de esta tarea si es urgente, o amplía su fecha límite para que se agende mañana."
        )
    def _backtrack(self, task_index, current_schedule):
        if task_index == len(self.tasks):
            return True 

        task = self.tasks[task_index]
        possible_slots = self._get_possible_slots(task)

        for slot_start, slot_end in possible_slots:
            if self._is_valid(slot_start, slot_end, current_schedule):
                current_schedule[task.id] = (slot_start, slot_end)
                
                if self._backtrack(task_index + 1, current_schedule):
                    return True
                    
                del current_schedule[task.id] 

        return self._backtrack(task_index + 1, current_schedule)

    def _is_valid(self, start, end, current_schedule):
        for assigned_start, assigned_end in current_schedule.values():
            if start < assigned_end and end > assigned_start:
                return False

        # NUEVO — Respetamos los eventos externos de Google Calendar
        for ext_event in self.external_events:
            if start < ext_event["end"] and end > ext_event["start"]:
                return False

        return True

    def _get_possible_slots(self, task):
        now = datetime.now()
        is_today = (self.target_date == now.date())

        # Si la fecha objetivo ya pasó en días anteriores, no hay slots
        if self.target_date < now.date():
            return []

        # 1. CASO EVENTO FIJO
        if not task.is_flexible and task.fixed_start_time:
            start = task.fixed_start_time.replace(tzinfo=None)
            end = start + timedelta(minutes=task.duration_minutes)
            # Si el evento fijo ya pasó el día de hoy, no se puede agendar
            if is_today and start < now:
                return []
            return [(start, end)]

        # 2. CASO TAREA FLEXIBLE
        slots_with_scores = []
        
        # Si es hoy, la hora de inicio nunca puede ser una hora del pasado
        if is_today:
            # Redondear al siguiente cuarto de hora para dar margen de inicio
            minute_rounded = ((now.minute // 15) + 1) * 15
            now_slot = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minute_rounded)
            current_time = max(self.day_start, now_slot)
        else:
            current_time = self.day_start

        duration = timedelta(minutes=task.duration_minutes)

        rejected_hours = []
        for d in self.rejected_decisions:
            if str(d.conflict_context.get("task_id")) == str(task.id):
                st_str = d.conflict_context.get("scheduled_time")
                if st_str and 'T' in st_str:
                    try:
                        hour_str = st_str.split('T')[1].split(':')[0]
                        rejected_hours.append(int(hour_str))
                    except:
                        pass

        deadline_clean = None
        if task.deadline:
            deadline_clean = task.deadline.replace(tzinfo=None)
            if deadline_clean.date() == self.target_date:
                deadline_clean = max(deadline_clean, self.day_end)

        while current_time + duration <= self.day_end:
            hora = current_time.hour
            
            if hora in rejected_hours:
                current_time += timedelta(minutes=15)
                continue

            # Filtros de Preferencia del usuario
            if task.preferred_time_of_day == "Mañana" and (hora < 6 or hora >= 12):
                current_time += timedelta(minutes=15)
                continue
            if task.preferred_time_of_day == "Tarde" and (hora < 12 or hora >= 18):
                current_time += timedelta(minutes=15)
                continue
            if task.preferred_time_of_day == "Noche" and hora < 18:
                current_time += timedelta(minutes=15)
                continue

            if deadline_clean and (current_time + duration) > deadline_clean:
                break 
                
            penalty = calculate_slot_penalty(task, current_time, self.user_profile)
            slots_with_scores.append({
                "start": current_time,
                "end": current_time + duration,
                "penalty": penalty
            })
            current_time += timedelta(minutes=15)

        slots_with_scores.sort(key=lambda x: x["penalty"])
        return [(slot["start"], slot["end"]) for slot in slots_with_scores]