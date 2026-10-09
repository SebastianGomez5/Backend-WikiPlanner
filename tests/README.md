# 🧪 Suite de Pruebas y Evaluación Empírica (WikiPlanner)

Esta carpeta contiene los scripts de pruebas, benchmarks y simulaciones desarrollados para la evaluación experimental del Trabajo de Grado (**Marco Lógico y Validación Científica**).

---

## 📂 Contenido del Módulo

```text
tests/
├── benchmark_csp.py            # Evaluación de rendimiento temporal del motor CSP (OE3)
├── simulacion_aprendizaje.py   # Simulación del modelo de aprendizaje adaptativo (Sección 4.2)
├── probar_google_calendar.py   # Pruebas de integración con la API de Google Calendar (OE4)
├── resultados/                 # Archivos CSV generados con los resultados empíricos
│   ├── benchmark_csp_resultados.csv
│   ├── simulacion_aprendizaje_resultados.csv
│   └── probar_google_calendar_resultados.csv
└── README.md                   # Esta documentación
```

---

## 🔬 Descripción de las Pruebas

### 1. Benchmark del Motor CSP (`benchmark_csp.py`)
- **Objetivo**: Evaluar el indicador del marco lógico (**OE3**): tiempo de cómputo promedio menor a 5 segundos para $n = 20$ tareas.
- **Entorno**: No requiere base de datos ni servicios externos. Genera escenarios sintéticos (*holgado* y *saturado*) con eventos externos y restricciones temporales.
- **Ejecución**:
  ```powershell
  python tests/benchmark_csp.py
  ```
- **Salida**: Genera estadísticas de media, desviación estándar, tiempos mínimos/máximos, filas formateadas para tablas LaTeX y guarda el detalle en `resultados/benchmark_csp_resultados.csv`.

---

### 2. Simulación del Modelo de Aprendizaje Adaptativo (`simulacion_aprendizaje.py`)
- **Objetivo**: Evaluar la convergencia del aprendizaje por refuerzo y penalizaciones (**Sección 4.2**).
  - **Parte A**: Prueba controlada ante rechazos sucesivos (verifica que la propuesta de horario cambie dinámicamente).
  - **Parte B**: Simulación a lo largo de 14 días comparando un agente con aprendizaje vs. un agente de control sin aprendizaje.
- **Ejecución**:
  ```powershell
  python tests/simulacion_aprendizaje.py
  ```
- **Salida**: Métricas de tasa de aceptación inicial (días 1–3) vs. final (días 12–14), porcentaje de rechazos repetidos, exportación de datos a `resultados/simulacion_aprendizaje_resultados.csv` y gráfica `simulacion_aprendizaje.png` (si `matplotlib` está disponible).

---

### 3. Pruebas de Integración con Google Calendar (`probar_google_calendar.py`)
- **Objetivo**: Evaluar el indicador del marco lógico (**OE4**):
  - Tasa de sincronización exitosa $\ge 95\%$.
  - Cero duplicidad o pérdida de eventos.
  - Latencia promedio menor a 3.0 segundos.
- **Requisitos**: Conexión a internet, cuenta de Google vinculada en la base de datos y configuración del parámetro `CORREO`.
- **Ejecución**:
  ```powershell
  python tests/probar_google_calendar.py
  # Para limpiar eventos de prueba creados en caso de interrupción:
  python tests/probar_google_calendar.py --limpiar
  ```
- **Salida**: Tabla de latencias y tasas de éxito por operación (crear, listar, eliminar, regenerar agenda) guardada en `resultados/probar_google_calendar_resultados.csv`.
