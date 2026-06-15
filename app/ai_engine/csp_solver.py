import time
from datetime import datetime, timedelta
from app.ai_engine.scoring import calculate_slot_penalty
from app.ai_engine.learning import build_user_penalty_profile

class CSPSolver:
    def __init__(self, tasks, user_settings, target_date, rejected_decisions=None):
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

    def solve(self):
        # Ordenamos: Fijos primero, luego más prioritarios, luego más largos
        self.tasks.sort(key=lambda t: (t.is_flexible, -t.priority, -t.duration_minutes))
        schedule = {}
        
        self._backtrack(0, schedule)
        return schedule

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

        # Si la tarea no cupo en ningún lado, la saltamos y seguimos con la siguiente
        return self._backtrack(task_index + 1, current_schedule)

    def _is_valid(self, start, end, current_schedule):
        for assigned_start, assigned_end in current_schedule.values():
            if start < assigned_end and end > assigned_start:
                return False
        return True

    def _get_possible_slots(self, task):
        # 1. CASO EVENTO FIJO
        if not task.is_flexible and task.fixed_start_time:
            start = task.fixed_start_time.replace(tzinfo=None)
            end = start + timedelta(minutes=task.duration_minutes)
            return [(start, end)]

        # 2. CASO TAREA FLEXIBLE
        slots_with_scores = []
        current_time = self.day_start
        duration = timedelta(minutes=task.duration_minutes)

        # Extraemos a qué horas EXACTAS rechazó el usuario esta tarea en el pasado
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

        # Flexibilización inteligente del deadline si es para "hoy"
        deadline_clean = None
        if task.deadline:
            deadline_clean = task.deadline.replace(tzinfo=None)
            if deadline_clean.date() == self.target_date:
                deadline_clean = max(deadline_clean, self.day_end)

        while current_time + duration <= self.day_end:
            hora = current_time.hour
            
            # EL APRENDIZAJE: Si el usuario rechazó esta hora, la IA la descarta de inmediato
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

            # Verificamos si este hueco rompe el deadline flexibilizado
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