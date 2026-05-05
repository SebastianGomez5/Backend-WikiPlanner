import time
from datetime import datetime, timedelta
from app.ai_engine.scoring import calculate_slot_penalty

class CSPSolver:
    def __init__(self, tasks, user_settings, target_date):
        self.tasks = tasks
        self.settings = user_settings
        self.target_date = target_date
        
        work_start = self.settings.work_start_time
        work_end = self.settings.work_end_time
        
        self.day_start = datetime.combine(self.target_date, work_start)
        self.day_end = datetime.combine(self.target_date, work_end)
        
        self.best_schedule = {}

    def solve(self):
        self.tasks.sort(key=lambda t: (t.is_flexible, -t.priority, -t.duration_minutes))
        schedule = {}
        if self._backtrack(0, schedule):
            return schedule
        return None

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

        return False

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

        while current_time + duration <= self.day_end:
            # FILTRO NUEVO: Respetar el lapso preferido del usuario
            hora = current_time.hour
            
            if task.preferred_time_of_day == "Mañana" and (hora < 6 or hora >= 12):
                current_time += timedelta(minutes=15)
                continue
            if task.preferred_time_of_day == "Tarde" and (hora < 12 or hora >= 18):
                current_time += timedelta(minutes=15)
                continue
            if task.preferred_time_of_day == "Noche" and hora < 18:
                current_time += timedelta(minutes=15)
                continue

            if task.deadline and (current_time + duration) > task.deadline.replace(tzinfo=None):
                break 
                
            penalty = calculate_slot_penalty(task, current_time)
            slots_with_scores.append({
                "start": current_time,
                "end": current_time + duration,
                "penalty": penalty
            })
            current_time += timedelta(minutes=15)
            
        slots_with_scores.sort(key=lambda x: x["penalty"])
        return [(slot["start"], slot["end"]) for slot in slots_with_scores]