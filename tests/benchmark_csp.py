"""
Medición del tiempo de ejecución del motor de inferencia CSP.

Indicador del marco lógico (OE3): tiempo promedio < 5 s para n = 20 tareas.

Uso (desde la raíz del backend, con el entorno virtual activado):
    python benchmark_csp.py

No necesita base de datos, servidor, ngrok ni Google Calendar: ejecuta el
CSPSolver real con tareas sintéticas y mide solo el tiempo del motor.
"""
import csv
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import uuid
from datetime import date, datetime, time as dtime, timedelta
from types import SimpleNamespace

# Asegurar que la raíz del backend esté en sys.path
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.ai_engine.csp_solver import CSPSolver


TAMANOS = [5, 10, 20, 30]         
REPETICIONES = 30                  
SEMILLA_BASE = 2026                
JORNADA = (dtime(8, 0), dtime(20, 0))
FECHA_OBJETIVO = date.today() + timedelta(days=3)  
EVENTOS_EXTERNOS = [(dtime(10, 0), dtime(11, 0)), (dtime(15, 0), dtime(16, 0))]
N_RECHAZOS_HISTORIAL = 6           

ESCENARIOS = {
    "holgado": {
        "descripcion": "Carga holgada: tareas de 15 a 45 minutos (casi todas caben en el día)",
        "duraciones": [15, 15, 30, 30, 45],
    },
    "saturado": {
        "descripcion": "Carga saturada: tareas de 60 a 120 minutos (el día no alcanza para todas)",
        "duraciones": [60, 90, 120],
    },
}

CATEGORIAS = ["Trabajo", "Estudio", "Salud", "Hogar", "Ocio"]
ENERGIAS = ["Bajo", "Medio", "Alto"]
MOMENTOS = ["Cualquier", "Mañana", "Tarde", "Noche"]
PESOS_MOMENTOS = [6, 2, 2, 1]
HORAS_EVENTOS_FIJOS = [9, 11, 13, 14, 17]


def nuevo_id(rng):
    return uuid.UUID(int=rng.getrandbits(128))


def crear_tareas(rng, n, duraciones, fecha):
    """Genera n tareas con la misma forma que las que crea la aplicación móvil."""
    n_fijas = max(1, n // 10)
    tareas = []
    for hora in rng.sample(HORAS_EVENTOS_FIJOS, n_fijas):
        tareas.append(SimpleNamespace(
            id=nuevo_id(rng), title=f"Evento fijo {hora}h", duration_minutes=45,
            priority=3, category=rng.choice(CATEGORIAS), energy_level="Medio",
            difficulty_level="Media", is_flexible=False, deadline=None,
            fixed_start_time=datetime.combine(fecha, dtime(hora, 0)),
            preferred_time_of_day="Cualquier"))
    for i in range(n - n_fijas):
        tareas.append(SimpleNamespace(
            id=nuevo_id(rng), title=f"Tarea {i}", duration_minutes=rng.choice(duraciones),
            priority=rng.randint(1, 5), category=rng.choice(CATEGORIAS),
            energy_level=rng.choice(ENERGIAS), difficulty_level="Media",
            is_flexible=True, deadline=datetime.combine(fecha, dtime(12, 0)),
            fixed_start_time=None,
            preferred_time_of_day=rng.choices(MOMENTOS, weights=PESOS_MOMENTOS)[0]))
    return tareas


def crear_historial(rng, fecha):
    """Rechazos simulados (mayormente en la mañana) para ejercitar el perfil aprendido."""
    historial = []
    for _ in range(N_RECHAZOS_HISTORIAL):
        hora = rng.randint(7, 11)
        historial.append(SimpleNamespace(
            is_accepted=False,
            conflict_context={
                "task_id": str(nuevo_id(rng)),
                "category": rng.choice(["Salud", "Ocio", "Estudio"]),
                "scheduled_time": f"{fecha.isoformat()}T{hora:02d}:00:00",
            }))
    return historial


def agenda_valida(agenda, tareas, eventos, jornada_inicio, jornada_fin):
    """Verifica de forma independiente que la agenda cumpla las restricciones duras."""
    por_id = {t.id: t for t in tareas}
    bloques = sorted(agenda.values(), key=lambda b: b[0])
    for (_, fin_a), (ini_b, _) in zip(bloques, bloques[1:]):
        if fin_a > ini_b:
            return False                                  
    for ini, fin in bloques:
        for ev in eventos:
            if ini < ev["end"] and fin > ev["start"]:
                return False                               
    for tid, (ini, fin) in agenda.items():
        if por_id[tid].is_flexible and (ini < jornada_inicio or fin > jornada_fin):
            return False                                  
    return True


def coma(valor, decimales):
    return f"{valor:.{decimales}f}".replace(".", ",")


def medir(n, escenario, ajustes, eventos, jornada_inicio, jornada_fin, registro_csv, nombre_escenario):
    tiempos, agendadas, invalidas = [], [], 0
    for rep in range(REPETICIONES):
        rng = random.Random(SEMILLA_BASE + n * 1000 + rep)
        tareas = crear_tareas(rng, n, escenario["duraciones"], FECHA_OBJETIVO)
        historial = crear_historial(rng, FECHA_OBJETIVO)

        inicio = time.perf_counter()
        solver = CSPSolver(tareas, ajustes, FECHA_OBJETIVO, historial, eventos)
        agenda = solver.solve()
        segundos = time.perf_counter() - inicio

        valida = agenda_valida(agenda, tareas, eventos, jornada_inicio, jornada_fin)
        invalidas += 0 if valida else 1
        tiempos.append(segundos)
        agendadas.append(len(agenda))
        registro_csv.writerow([nombre_escenario, n, rep + 1, f"{segundos:.6f}", len(agenda), valida])
    return tiempos, agendadas, invalidas


def main():
    ajustes = SimpleNamespace(work_start_time=JORNADA[0], work_end_time=JORNADA[1])
    jornada_inicio = datetime.combine(FECHA_OBJETIVO, JORNADA[0])
    jornada_fin = datetime.combine(FECHA_OBJETIVO, JORNADA[1])
    eventos = [{"start": datetime.combine(FECHA_OBJETIVO, a), "end": datetime.combine(FECHA_OBJETIVO, b)}
               for a, b in EVENTOS_EXTERNOS]

    print("=" * 70)
    print("EQUIPO Y ENTORNO (para el apartado de protocolo del documento)")
    print("=" * 70)
    print(f"Sistema operativo : {platform.platform()}")
    print(f"Procesador        : {platform.processor() or 'no disponible'}")
    print(f"Núcleos lógicos   : {os.cpu_count()}")
    print(f"Python            : {sys.version.split()[0]}")
    print(f"Repeticiones      : {REPETICIONES} conjuntos de tareas por tamaño (semilla fija {SEMILLA_BASE})")
    print(f"Jornada           : {JORNADA[0].strftime('%H:%M')} a {JORNADA[1].strftime('%H:%M')}")
    print(f"Eventos externos  : {len(EVENTOS_EXTERNOS)} por día; historial simulado: {N_RECHAZOS_HISTORIAL} rechazos")

    rng = random.Random(0)
    CSPSolver(crear_tareas(rng, 10, [30], FECHA_OBJETIVO), ajustes, FECHA_OBJETIVO, [], eventos).solve()

    resultados_dir = BASE_DIR / "resultados"
    resultados_dir.mkdir(parents=True, exist_ok=True)
    ruta_csv = resultados_dir / "benchmark_csp_resultados.csv"

    archivo = open(ruta_csv, "w", newline="", encoding="utf-8")
    registro = csv.writer(archivo)
    registro.writerow(["escenario", "n_tareas", "repeticion", "segundos", "tareas_agendadas", "agenda_valida"])

    resumen = {}
    for nombre, escenario in ESCENARIOS.items():
        print("\n" + "=" * 70)
        print(f"ESCENARIO: {nombre} -> {escenario['descripcion']}")
        print("=" * 70)
        print(f"{'n':>4} {'media (s)':>11} {'desv (s)':>10} {'mín (s)':>10} {'máx (s)':>10} {'agendadas':>10} {'inválidas':>10}")
        filas_latex = []
        for n in TAMANOS:
            tiempos, agendadas, invalidas = medir(
                n, escenario, ajustes, eventos, jornada_inicio, jornada_fin, registro, nombre)
            media, desv = statistics.mean(tiempos), statistics.stdev(tiempos)
            prom_agendadas = statistics.mean(agendadas)
            resumen[(nombre, n)] = media
            print(f"{n:>4} {media:>11.4f} {desv:>10.4f} {min(tiempos):>10.4f} {max(tiempos):>10.4f} "
                  f"{prom_agendadas:>10.1f} {invalidas:>10}")
            filas_latex.append(f"{n} & {coma(media, 4)} & {coma(desv, 4)} & {coma(prom_agendadas, 1)} \\\\")
        print("\nFilas para la tabla de LaTeX (columnas: n, media, desviación, agendadas):")
        for fila in filas_latex:
            print("  " + fila)

    archivo.close()

    print("\n" + "=" * 70)
    media_20 = resumen[("holgado", 20)]
    veredicto = "CUMPLE" if media_20 < 5 else "NO CUMPLE"
    print(f"Indicador del marco lógico (n = 20, escenario holgado): media = {media_20:.4f} s -> {veredicto} (< 5 s)")
    print(f"Registro de cada ejecución guardado en: {ruta_csv}")


if __name__ == "__main__":
    main()