"""
Pruebas de la integración con Google Calendar (indicador del OE4 del marco lógico):
    - sincronización exitosa en al menos el 95 % de las pruebas,
    - sin pérdida ni duplicidad de eventos,
    - latencia menor a 3 segundos.

Usa las funciones REALES del servicio (create_google_event, delete_google_event y
get_calendar_events) sobre la cuenta de Google vinculada a TU usuario, y verifica de
forma independiente, consultando directamente a Google, que el resultado sea el correcto.

Uso (desde la raíz del backend, con el entorno virtual activado):
    1) Edita CORREO: el correo con el que te registraste en la app y que ya tiene
       Google Calendar vinculado.
    2) python probar_google_calendar.py
    Si una ejecución se interrumpe y quedan eventos de prueba:
       python probar_google_calendar.py --limpiar

IMPORTANTE:
    - Crea y elimina eventos de prueba en tu Google Calendar real. Se crean en un día
      futuro (DIAS_ADELANTE) y su título empieza por "PRUEBA-WikiPlanner".
    - Requiere conexión a internet. No necesita uvicorn ni ngrok.
    - Aplica antes la corrección de zona horaria de get_calendar_events: una de las
      pruebas incluye un evento de las 19:30 para comprobarla.
"""
import argparse
import csv
from pathlib import Path
import statistics
import sys
import time
import uuid
from datetime import date, datetime, time as dtime, timedelta, timezone

# Asegurar que la raíz del backend esté en sys.path
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------
CORREO = "user@example.com"     # <- EDITA ESTE VALOR
REPETICIONES = 20                    # repeticiones de crear, eliminar y leer
REPETICIONES_REGENERAR = 5           # regeneraciones completas de una agenda
BLOQUES_POR_AGENDA = 5               # eventos por agenda en la prueba de regenerar
DIAS_ADELANTE = 30                   # los eventos de prueba se crean este número de días en el futuro
PREFIJO = "PRUEBA-WikiPlanner"
UMBRAL_LATENCIA = 3.0                # segundos (marco lógico)
UMBRAL_EXITO = 95.0                  # porcentaje (marco lógico)

ZONA = timezone(timedelta(hours=-5))  # Colombia: UTC-5 fijo


def a_iso(dt):
    """Fecha local de Colombia (sin zona) -> texto ISO con desfase, para hablar con Google."""
    return dt.replace(tzinfo=ZONA).isoformat()


class GoogleDirecto:
    """
    Acceso directo a la API de Google, independiente del código del sistema.
    Sirve para preparar eventos 'externos' (creados por otra persona) y para
    verificar el estado real del calendario.
    """

    def __init__(self, usuario, get_access_token, api_base):
        self.usuario = usuario
        self.get_access_token = get_access_token
        self.api_base = api_base

    def _cabecera(self):
        return {"Authorization": f"Bearer {self.get_access_token(self.usuario.google_refresh_token)}"}

    def listar(self, inicio, fin):
        import requests
        respuesta = requests.get(
            f"{self.api_base}/calendars/primary/events", headers=self._cabecera(), timeout=30,
            params={"timeMin": a_iso(inicio), "timeMax": a_iso(fin), "singleEvents": "true",
                    "orderBy": "startTime", "maxResults": 250})
        respuesta.raise_for_status()
        return respuesta.json().get("items", [])

    def crear_externo(self, titulo, inicio, fin):
        import requests
        cuerpo = {"summary": titulo, "description": "Evento de prueba creado por otra persona",
                  "start": {"dateTime": a_iso(inicio), "timeZone": "America/Bogota"},
                  "end": {"dateTime": a_iso(fin), "timeZone": "America/Bogota"}}
        respuesta = requests.post(f"{self.api_base}/calendars/primary/events",
                                  headers=self._cabecera(), json=cuerpo, timeout=30)
        respuesta.raise_for_status()
        return respuesta.json()["id"]

    def borrar(self, evento_id):
        import requests
        requests.delete(f"{self.api_base}/calendars/primary/events/{evento_id}",
                        headers=self._cabecera(), timeout=30)


class Registro:
    def __init__(self):
        self.filas = []   # (operacion, repeticion, exito, latencia, detalle)

    def agregar(self, operacion, repeticion, exito, latencia, detalle=""):
        self.filas.append((operacion, repeticion, bool(exito), latencia, detalle))


def titulo(corrida, etiqueta, n):
    return f"{PREFIJO}-{corrida}-{etiqueta}-{n}"


def contar_por_titulo(eventos, prefijo):
    conteo = {}
    for e in eventos:
        t = e.get("summary", "")
        if t.startswith(prefijo):
            conteo[t] = conteo.get(t, 0) + 1
    return conteo


def dia(fecha):
    return datetime.combine(fecha, dtime.min), datetime.combine(fecha, dtime.max)


# ----------------------------------------------------------------------
# Pruebas
# ----------------------------------------------------------------------
def prueba_crear(servicio, directo, usuario, fecha, corrida, registro):
    inicio_dia, fin_dia = dia(fecha)
    intentos = []
    for i in range(1, REPETICIONES + 1):
        t = titulo(corrida, "CREAR", i)
        inicio = datetime.combine(fecha, dtime(10, 0))
        t0 = time.perf_counter()
        evento_id = servicio.create_google_event(usuario, t, inicio, inicio + timedelta(minutes=30))
        intentos.append((i, t, evento_id, time.perf_counter() - t0))

    conteo = contar_por_titulo(directo.listar(inicio_dia, fin_dia), f"{PREFIJO}-{corrida}-CREAR")
    creados = {}
    for i, t, evento_id, latencia in intentos:
        copias = conteo.get(t, 0)
        ok = bool(evento_id) and copias == 1
        detalle = "" if ok else ("el servicio no devolvió identificador" if not evento_id
                                 else f"{copias} copias en Google")
        registro.agregar("crear", i, ok, latencia, detalle)
        if evento_id:
            creados[t] = evento_id
    return creados


def prueba_eliminar(servicio, directo, usuario, fecha, corrida, creados, registro):
    inicio_dia, fin_dia = dia(fecha)
    intentos = []
    for i, (t, evento_id) in enumerate(creados.items(), start=1):
        t0 = time.perf_counter()
        borrado = servicio.delete_google_event(usuario, evento_id)
        intentos.append((i, t, borrado, time.perf_counter() - t0))

    conteo = contar_por_titulo(directo.listar(inicio_dia, fin_dia), f"{PREFIJO}-{corrida}-CREAR")
    for i, t, borrado, latencia in intentos:
        quedan = conteo.get(t, 0)
        ok = bool(borrado) and quedan == 0
        detalle = "" if ok else ("el servicio indicó fallo" if not borrado else "el evento sigue en Google")
        registro.agregar("eliminar", i, ok, latencia, detalle)


def prueba_leer(servicio, directo, usuario, fecha, corrida, registro):
    inicio_dia, fin_dia = dia(fecha)
    externos = {
        "mañana": (titulo(corrida, "EXT-MANANA", 1), dtime(9, 0), dtime(10, 0)),
        "noche": (titulo(corrida, "EXT-NOCHE", 1), dtime(19, 30), dtime(20, 30)),
    }
    ids_externos, id_propio = [], None
    titulo_propio = titulo(corrida, "PROPIO", 1)
    try:
        for _, (t, a, b) in externos.items():
            ids_externos.append(directo.crear_externo(
                t, datetime.combine(fecha, a), datetime.combine(fecha, b)))
        id_propio = servicio.create_google_event(
            usuario, titulo_propio, datetime.combine(fecha, dtime(12, 0)), datetime.combine(fecha, dtime(12, 30)))

        for i in range(1, REPETICIONES + 1):
            t0 = time.perf_counter()
            eventos = servicio.get_calendar_events(usuario, inicio_dia, fin_dia)   # mismo patrón que ai_service
            latencia = time.perf_counter() - t0
            visibles = [e for e in eventos if e["title"].startswith(f"{PREFIJO}-{corrida}")]
            problemas = []
            for nombre, (t, a, b) in externos.items():
                coinciden = [e for e in visibles if e["title"] == t
                             and e["start"] == datetime.combine(fecha, a)
                             and e["end"] == datetime.combine(fecha, b)]
                if len(coinciden) != 1:
                    problemas.append(f"evento de la {nombre}: {len(coinciden)} coincidencias (se esperaba 1)")
            if any(e["title"] == titulo_propio for e in visibles):
                problemas.append("incluyó un evento creado por el propio sistema")
            registro.agregar("leer", i, not problemas, latencia, "; ".join(problemas))
    except Exception as error:   # no se pudo preparar la prueba
        registro.agregar("leer", 0, False, 0.0, f"no se pudo preparar la prueba: {str(error)[:120]}")
    finally:
        for evento_id in ids_externos:
            directo.borrar(evento_id)
        if id_propio:
            servicio.delete_google_event(usuario, id_propio)


def prueba_regenerar(servicio, directo, usuario, fecha, corrida, registro):
    inicio_dia, fin_dia = dia(fecha)

    def crear_agenda(etiqueta):
        ids = {}
        for j in range(BLOQUES_POR_AGENDA):
            t = titulo(corrida, etiqueta, j + 1)
            inicio = datetime.combine(fecha, dtime(14, 0)) + timedelta(minutes=30 * j)
            ids[t] = servicio.create_google_event(usuario, t, inicio, inicio + timedelta(minutes=30))
        return ids

    anterior = crear_agenda("REG0")
    for rep in range(1, REPETICIONES_REGENERAR + 1):
        t0 = time.perf_counter()
        borrados = [servicio.delete_google_event(usuario, eid) for eid in anterior.values() if eid]
        nueva = crear_agenda(f"REG{rep}")
        latencia = time.perf_counter() - t0

        conteo = contar_por_titulo(directo.listar(inicio_dia, fin_dia), f"{PREFIJO}-{corrida}-REG")
        problemas = []
        if not all(borrados):
            problemas.append("falló al eliminar algún evento anterior")
        if not all(nueva.values()):
            problemas.append("falló al crear algún evento nuevo")
        if set(conteo) != set(nueva):
            problemas.append("los eventos en Google no coinciden con la agenda nueva (pérdida o restos)")
        if any(v > 1 for v in conteo.values()):
            problemas.append("hay eventos duplicados")
        registro.agregar("regenerar", rep, not problemas, latencia, "; ".join(problemas))
        anterior = nueva

    for eid in anterior.values():
        if eid:
            servicio.delete_google_event(usuario, eid)


def limpiar_restos(directo, fecha):
    inicio, _ = dia(fecha)
    _, fin = dia(fecha + timedelta(days=1))
    restos = [e for e in directo.listar(inicio, fin) if e.get("summary", "").startswith(PREFIJO)]
    for evento in restos:
        directo.borrar(evento["id"])
    return len(restos)


def ejecutar_pruebas(servicio, directo, usuario, fecha):
    corrida = uuid.uuid4().hex[:6]
    registro = Registro()
    print(f"Corrida {corrida}: eventos de prueba en la fecha {fecha:%Y-%m-%d}.")
    try:
        print(" - Crear eventos...")
        creados = prueba_crear(servicio, directo, usuario, fecha, corrida, registro)
        print(" - Eliminar eventos...")
        prueba_eliminar(servicio, directo, usuario, fecha, corrida, creados, registro)
        print(" - Leer eventos externos...")
        prueba_leer(servicio, directo, usuario, fecha, corrida, registro)
        print(" - Regenerar agendas...")
        prueba_regenerar(servicio, directo, usuario, fecha, corrida, registro)
    finally:
        restos = limpiar_restos(directo, fecha)
        print(f"Limpieza final: {restos} evento(s) de prueba restante(s) eliminado(s) "
              f"({'todo se había borrado correctamente' if restos == 0 else 'revisa los fallos indicados'}).")
    return registro


# ----------------------------------------------------------------------
# Resultados
# ----------------------------------------------------------------------
NOMBRES = [
    ("crear", "Crear un evento"),
    ("eliminar", "Eliminar un evento"),
    ("leer", "Leer los eventos externos del día"),
    ("regenerar", "Regenerar la agenda de un día (borrar y crear)"),
]


def coma(valor, decimales):
    return f"{valor:.{decimales}f}".replace(".", ",")


def resumir(registro):
    resumen = {}
    for clave, nombre in NOMBRES:
        filas = [f for f in registro.filas if f[0] == clave]
        if not filas:
            resumen[clave] = None
            continue
        exitosas = sum(1 for f in filas if f[2])
        latencias = [f[3] for f in filas if f[3] > 0]
        resumen[clave] = {
            "nombre": nombre, "pruebas": len(filas), "exitosas": exitosas,
            "exito": 100 * exitosas / len(filas),
            "media": statistics.mean(latencias) if latencias else 0.0,
            "maxima": max(latencias) if latencias else 0.0,
            "fallos": [f for f in filas if not f[2]],
        }
    return resumen


def imprimir(resumen):
    print("\n" + "=" * 92)
    print("RESULTADOS DE LA INTEGRACIÓN CON GOOGLE CALENDAR")
    print("=" * 92)
    print(f"{'Operación':<50}{'Pruebas':>8}{'Exitosas':>9}{'Éxito %':>9}{'Media (s)':>10}{'Máx (s)':>9}")
    for clave, _ in NOMBRES:
        r = resumen[clave]
        if r is None:
            continue
        print(f"{r['nombre']:<50}{r['pruebas']:>8}{r['exitosas']:>9}{r['exito']:>9.1f}"
              f"{r['media']:>10.3f}{r['maxima']:>9.3f}")

    print("\nFilas para LaTeX (Operación & Pruebas & Exitosas & Latencia media (s)):")
    for clave, _ in NOMBRES:
        r = resumen[clave]
        if r:
            print(f"  {r['nombre']} & {r['pruebas']} & {r['exitosas']} & {coma(r['media'], 3)} \\\\")

    print(f"\nComparación con el marco lógico (éxito >= {UMBRAL_EXITO:.0f} % y latencia < {UMBRAL_LATENCIA:.0f} s):")
    for clave, _ in NOMBRES:
        r = resumen[clave]
        if r is None:
            continue
        cumple_exito = r["exito"] >= UMBRAL_EXITO
        cumple_lat = r["media"] < UMBRAL_LATENCIA
        print(f"  {r['nombre']:<50} éxito: {'CUMPLE' if cumple_exito else 'NO CUMPLE':<10} "
              f"latencia media: {'CUMPLE' if cumple_lat else 'NO CUMPLE'}")

    fallos = [(r["nombre"], f) for r in resumen.values() if r for f in r["fallos"]]
    if fallos:
        print("\nPrimeros fallos registrados:")
        for nombre, f in fallos[:8]:
            print(f"  [{nombre} #{f[1]}] {f[4]}")
        print("  Si falla el evento de las 19:30 al leer, revisa la corrección de zona horaria "
              "en google_calendar_service.py.")


def guardar_csv(registro, ruta=None):
    if ruta is None:
        resultados_dir = BASE_DIR / "resultados"
        resultados_dir.mkdir(parents=True, exist_ok=True)
        ruta = resultados_dir / "probar_google_calendar_resultados.csv"

    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        w = csv.writer(archivo)
        w.writerow(["operacion", "repeticion", "exito", "latencia_s", "detalle"])
        for operacion, rep, exito, latencia, detalle in registro.filas:
            w.writerow([operacion, rep, exito, f"{latencia:.4f}", detalle])
    print(f"\nRegistro de cada operación (sin datos personales) guardado en: {ruta}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limpiar", action="store_true", help="elimina eventos de prueba que hayan quedado")
    args = parser.parse_args()

    if CORREO == "tu_correo@ejemplo.com":
        sys.exit("Edita la variable CORREO al inicio del archivo antes de ejecutar.")

    from app.db.session import SessionLocal
    from app.db import models
    from app.services import google_calendar_service as servicio

    db = SessionLocal()
    try:
        usuario = db.query(models.User).filter(models.User.email == CORREO).first()
        if not usuario:
            sys.exit("No se encontró ese correo en la base de datos.")
        if not usuario.google_refresh_token:
            sys.exit("Ese usuario no tiene Google Calendar vinculado. Vincúlalo desde la app (Perfil).")

        directo = GoogleDirecto(usuario, servicio.get_access_token, servicio.CALENDAR_API_BASE)
        fecha = date.today() + timedelta(days=DIAS_ADELANTE)

        if args.limpiar:
            print(f"Eventos de prueba eliminados: {limpiar_restos(directo, fecha)}")
            return

        print(f"Python {sys.version.split()[0]} - {datetime.now():%Y-%m-%d %H:%M}")
        registro = ejecutar_pruebas(servicio, directo, usuario, fecha)
        resumen = resumir(registro)
        imprimir(resumen)
        guardar_csv(registro)
    finally:
        db.close()


if __name__ == "__main__":
    main()