"""
Evaluación del modelo de aprendizaje adaptativo (Sección 4.2).

Parte A - Prueba controlada: se registran rechazos sucesivos y se verifica
          que la hora que propone el motor cambia.
Parte B - Simulación: un usuario simulado, con preferencias fijas, usa el
          sistema durante varios días, con aprendizaje y sin él (control).

Uso (desde la raíz del backend, con el entorno virtual activado):
    python simulacion_aprendizaje.py

No necesita base de datos, servidor ni Google Calendar: ejecuta el motor real.
Los resultados son deterministas (semillas fijas): al repetir la ejecución
se obtienen los mismos números.
"""
import csv
import random
import statistics
import uuid
from datetime import date, datetime, time as dtime, timedelta
from types import SimpleNamespace

from app.ai_engine.csp_solver import CSPSolver
from app.ai_engine.learning import build_user_penalty_profile, get_franja

AJUSTES = SimpleNamespace(work_start_time=dtime(8, 0), work_end_time=dtime(20, 0))
FECHA_BASE = date.today() + timedelta(days=10)

DIAS = 14                   
TAREAS_POR_DIA = 10       
SEMILLAS = 20             
DURACIONES = [30, 45, 60, 90]
CATEGORIAS = ["Trabajo", "Estudio", "Salud", "Hogar", "Ocio"]
ENERGIAS = ["Bajo", "Medio", "Alto"]

DESAGRADO = {("Hogar", "Mañana"), ("Estudio", "Tarde"), ("Trabajo", "Tarde")}
PROB_RECHAZO = 1.0       


def nueva_tarea(categoria, duracion=60, energia="Medio", rng=None, prioridad=3, fecha=None):
    ident = uuid.UUID(int=rng.getrandbits(128)) if rng else uuid.uuid4()
    fecha = fecha or FECHA_BASE
    return SimpleNamespace(
        id=ident, title=f"Tarea {categoria}", duration_minutes=duracion, priority=prioridad,
        category=categoria, energy_level=energia, difficulty_level="Media", is_flexible=True,
        deadline=datetime.combine(fecha, dtime(12, 0)), fixed_start_time=None,
        preferred_time_of_day="Cualquier")


def registro_rechazo(tarea, inicio, con_categoria=True):
    """Registro equivalente al que guarda el servidor cuando el usuario rechaza un bloque."""
    contexto = {"task_id": str(tarea.id), "scheduled_time": inicio.isoformat()}
    if con_categoria:
        contexto["category"] = tarea.category
    return SimpleNamespace(is_accepted=False, conflict_context=contexto)


def proponer(tarea, historial, fecha=None):
    fecha = fecha or FECHA_BASE
    agenda = CSPSolver([tarea], AJUSTES, fecha, historial, []).solve()
    return agenda[tarea.id][0]


def perfil_texto(historial):
    perfil = build_user_penalty_profile(historial)
    if not perfil:
        return "vacío"
    return ", ".join(f"{c}-{f}: {p}" for (c, f), p in sorted(perfil.items()))


def parte_a():
    print("=" * 72)
    print("PARTE A - PRUEBA CONTROLADA")
    print("=" * 72)
    rng = random.Random(1)
    filas = []

    historial = []
    t1 = nueva_tarea("Estudio", rng=rng)
    h1 = proponer(t1, historial)
    filas.append(("Sin historial", perfil_texto(historial), h1))

    historial.append(registro_rechazo(t1, h1))
    t2 = nueva_tarea("Estudio", rng=rng)                  # otra tarea de la misma categoría
    h2 = proponer(t2, historial)
    filas.append((f"Tras rechazar Estudio a las {h1:%H:%M} (otra tarea de Estudio)", perfil_texto(historial), h2))

    historial.append(registro_rechazo(t2, h2))
    t3 = nueva_tarea("Estudio", rng=rng)
    h3 = proponer(t3, historial)
    filas.append((f"Tras rechazar Estudio también a las {h2:%H:%M}", perfil_texto(historial), h3))

    t4 = nueva_tarea("Estudio", rng=rng)
    h4_antes = proponer(t4, [])
    h4 = proponer(t4, [registro_rechazo(t4, h4_antes, con_categoria=False)])
    filas.append((f"Misma tarea tras rechazarla a las {h4_antes:%H:%M} (solo exclusión de hora)", "vacío", h4))

    print(f"{'Situación':<68} {'Perfil aprendido':<34} {'Hora propuesta':>14}")
    for situacion, perfil, hora in filas:
        print(f"{situacion:<68} {perfil:<34} {hora:%H:%M}".rstrip())
    print("\nFilas para LaTeX (Situación & Perfil & Hora):")
    for situacion, perfil, hora in filas:
        print(f"  {situacion} & {perfil} & {hora:%H:%M} \\\\")
    return filas


def simular(semilla, con_aprendizaje):
    historial = []
    combinaciones_rechazadas = set()
    por_dia = []
    for dia in range(DIAS):
        fecha = FECHA_BASE + timedelta(days=dia)
        rng = random.Random(semilla * 1000 + dia)
        tareas = [nueva_tarea(rng.choice(CATEGORIAS), rng.choice(DURACIONES), rng.choice(ENERGIAS),
                              rng, rng.randint(1, 5), fecha) for _ in range(TAREAS_POR_DIA)]
        por_id = {t.id: t for t in tareas}
        agenda = CSPSolver(tareas, AJUSTES, fecha, historial if con_aprendizaje else [], []).solve()

        rechazados = repetidos = 0
        for tid, (inicio, _fin) in agenda.items():
            tarea = por_id[tid]
            combinacion = (tarea.category, get_franja(inicio.hour))
            if combinacion in DESAGRADO and rng.random() < PROB_RECHAZO:
                rechazados += 1
                if combinacion in combinaciones_rechazadas:
                    repetidos += 1
                combinaciones_rechazadas.add(combinacion)
                if con_aprendizaje:
                    historial.append(registro_rechazo(tarea, inicio))
        por_dia.append((len(agenda), rechazados, repetidos))
    return por_dia


def parte_b():
    print("\n" + "=" * 72)
    print("PARTE B - SIMULACIÓN CON USUARIO SIMULADO")
    print("=" * 72)
    print(f"{DIAS} días, {TAREAS_POR_DIA} tareas nuevas por día, {SEMILLAS} simulaciones independientes.")
    print("Preferencias ocultas (rechaza): " + ", ".join(f"{c}-{f}" for c, f in sorted(DESAGRADO)))

    resultados = {}
    for modo in ("con", "sin"):
        resultados[modo] = [simular(s, modo == "con") for s in range(1, SEMILLAS + 1)]

    def tasa_aceptacion(modo, dia):
        valores = []
        for sim in resultados[modo]:
            agendados, rechazados, _ = sim[dia]
            valores.append(100 * (agendados - rechazados) / agendados if agendados else 100)
        return statistics.mean(valores)

    print(f"\n{'Día':>4} {'Aceptación CON aprendizaje (%)':>32} {'Aceptación SIN aprendizaje (%)':>32}")
    filas_dia = []
    for d in range(DIAS):
        con, sin = tasa_aceptacion("con", d), tasa_aceptacion("sin", d)
        filas_dia.append((d + 1, con, sin))
        print(f"{d + 1:>4} {con:>32.1f} {sin:>32.1f}")

    print("\nResumen (promedio de las simulaciones):")
    for etiqueta, modo in (("CON aprendizaje", "con"), ("SIN aprendizaje", "sin")):
        rech = [sum(r for _, r, _ in sim) for sim in resultados[modo]]
        rep = [sum(x for _, _, x in sim) for sim in resultados[modo]]
        total_rech, total_rep = statistics.mean(rech), statistics.mean(rep)
        pct_rep = 100 * total_rep / total_rech if total_rech else 0
        ini = statistics.mean(tasa_aceptacion(modo, d) for d in range(0, 3))
        fin = statistics.mean(tasa_aceptacion(modo, d) for d in range(DIAS - 3, DIAS))
        print(f"  {etiqueta:<16} aceptación días 1-3: {ini:5.1f} %  |  días {DIAS - 2}-{DIAS}: {fin:5.1f} %  |  "
              f"rechazos totales: {total_rech:5.1f}  |  rechazos repetidos: {pct_rep:4.1f} %")

    with open("simulacion_aprendizaje_resultados.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dia", "aceptacion_con_aprendizaje", "aceptacion_sin_aprendizaje"])
        for d, con, sin in filas_dia:
            w.writerow([d, f"{con:.2f}", f"{sin:.2f}"])
    print("\nTabla por día guardada en: simulacion_aprendizaje_resultados.csv")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        dias = [d for d, _, _ in filas_dia]
        plt.figure(figsize=(7, 3.8))
        plt.plot(dias, [c for _, c, _ in filas_dia], marker="o", label="Con aprendizaje")
        plt.plot(dias, [s for _, _, s in filas_dia], marker="s", linestyle="--", label="Sin aprendizaje")
        plt.xlabel("Día de uso")
        plt.ylabel("Tasa de aceptación (%)")
        plt.ylim(0, 105)
        plt.xticks(dias)
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig("simulacion_aprendizaje.png", dpi=200)
        print("Gráfica guardada en: simulacion_aprendizaje.png")
    except ImportError:
        print("(Para generar la gráfica instala matplotlib: pip install matplotlib)")


if __name__ == "__main__":
    parte_a()
    parte_b()