# ⚙️ WikiPlanner - Backend (FastAPI & Motor de IA)

> **Sistema Inteligente Adaptativo para la Gestión y Optimización del Tiempo**  
> *Trabajo de Grado - Universidad del Valle (Escuela de Ingeniería de Sistemas y Computación)*

---

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Google Calendar API](https://img.shields.io/badge/Google_Calendar_API-v3-4285F4?logo=googlecalendar&logoColor=white)](https://developers.google.com/calendar)
[![License](https://img.shields.io/badge/License-Academic-blue.svg)]()

---

## 📌 Descripción del Proyecto

**WikiPlanner API** es el servidor de procesamiento y motor de Inteligencia Artificial (Backend) encargado de la optimización y asignación dinámica de horarios para actividades personales.

A diferencia de los calendarios tradicionales que delegan toda la carga cognitiva en el usuario, este sistema modela la planificación como un **Problema de Satisfacción de Restricciones (Constraint Satisfaction Problem - CSP)** resuelto mediante algoritmos de *backtracking* guiados por funciones de costo (*scoring*), balance de energía, prioridades y un **modelo de aprendizaje adaptativo basado en retroalimentación (*feedback loop*)**. Además, incorpora principios de **Inteligencia Artificial Explicable (Explainable AI - XAI)** para traducir las decisiones del algoritmo a explicaciones comprensibles para el usuario, persistencia relacional con PostgreSQL, analíticas de balance de vida y sincronización bidireccional con **Google Calendar**.

---

## ✨ Características Principales

- 🧠 **Motor de Inferencia CSP & Optimización (`app/ai_engine`)**:
  - **Resolución de Restricciones (CSP)**: Asignación determinista y libre de solapamientos respetando jornada laboral, duración, plazos límite (*deadlines*), eventos fijos y eventos externos.
  - **Función de Penalización Multicriterio (`scoring.py`)**: Puntuación de cada franja según afinidad horaria (Mañana, Tarde, Noche), nivel de energía y dificultad de la tarea, categoría (Trabajo/Estudio vs. Ocio/Salud) y penalizaciones aprendidas.
  - **Aprendizaje Adaptativo Continuo (`learning.py`)**: Construcción del perfil dinámico del usuario a partir del historial de rechazos o reprogramaciones (`DecisionHistory`), adaptando sugerencias futuras sin necesidad de reentrenamientos pesados.
  - **Inteligencia Artificial Explicable (XAI)**: Generación de justificaciones en lenguaje natural (`ai_explanation`) y porcentaje de confianza (`ai_confidence`) para cada tarea programada, respondiendo de forma transparente: *"¿Por qué la IA eligió esta hora?"*.
  - **Diagnóstico y Sugerencias de Tareas No Agendadas**: Diagnóstico automático del motivo exacto cuando una tarea no cabe en la agenda y formulación de sugerencias prácticas para el usuario.
- 📆 **Sincronización Bidireccional con Google Calendar (`app/services/google_calendar_service.py`)**:
  - Lectura de eventos externos (reuniones, compromisos de terceros) para considerarlos como restricciones duras en el motor CSP.
  - Normalización estricta de zona horaria para Colombia (`UTC-5`) para evitar desfases horarios.
  - Creación y actualización de eventos con marcado no intrusivo (`Generado por Agenda IA`) para prevenir duplicidades o bucles de sincronización.
- 📊 **Métricas de Productividad & Balance de Vida (`app/api/endpoints/kpi.py`)**:
  - Cálculo de la **Tasa de Adherencia** al plan y **Tasa de Aceptación** de sugerencias.
  - Análisis del **Balance Ocio / Productividad** con soporte de agregación temporal por **Día**, **Semana** y **Mes**.
- 🔑 **Seguridad y Control de Acceso**:
  - Autenticación mediante JSON Web Tokens (JWT) con hashing seguro (`passlib` + `bcrypt`).
  - Almacenamiento cifrado de tokens OAuth2 (`google_refresh_token`).
- 🗄️ **Modelado Relacional ORM**:
  - Modelos estructurados con SQLAlchemy (`User`, `UserSettings`, `Task`, `TimeBlock`, `DecisionHistory`).

---

## 🛠️ Tecnologías y Librerías

| Categoría | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Framework Web** | FastAPI | Framework asíncrono de alto rendimiento para APIs RESTful |
| **Servidor ASGI** | Uvicorn | Servidor ASGI rápido y ligero |
| **ORM / Base de Datos** | SQLAlchemy & PostgreSQL | Mapeo objeto-relacional y persistencia estructurada |
| **Seguridad** | PyJWT, Passlib (Bcrypt) | Autenticación JWT y hashing de credenciales |
| **Integración Google** | Google API Client, Requests | Sincronización OAuth2 con Google Calendar v3 |
| **Validación de Datos** | Pydantic v2 | Validación y serialización estricta de esquemas |

---

## 🗺️ Endpoints de la API REST

| Módulo | Prefijo | Descripción de Funcionalidad |
| :--- | :--- | :--- |
| **Autenticación** | `/api/auth` | Registro de usuarios, inicio de sesión y emisión de tokens JWT. |
| **Usuarios** | `/api/users` | Perfil de usuario, información personal y cambio de nombre. |
| **Preferencias** | `/api/settings` | Horarios de jornada laboral (inicio/fin) y modo activo. |
| **Tareas** | `/api/tasks` | CRUD de tareas (pendientes, completadas, fijas, flexibles, prioridades). |
| **Bloques de Tiempo** | `/api/time-blocks` | Consulta de la agenda agendada, eventos externos y confirmación de bloques. |
| **Inteligencia Artificial** | `/api/ai` | Ejecución del motor CSP para generación y regeneración de la agenda diaria. |
| **Decisiones (Feedback)** | `/api/decisions` | Registro de tareas completadas a tiempo o reprogramadas para aprendizaje. |
| **Métricas & KPIs** | `/api/kpi` | Dashboard general, adherencia, confianza y balance ocio/productividad. |
| **Google Calendar** | `/api/google` | Flujo de autorización OAuth2, vinculación y estado del servicio. |

---

## 📂 Estructura del Código Fuente

```text
Backend-WikiPlanner/
├── app/
│   ├── ai_engine/               # Motor de Inteligencia Artificial (CSP & Scoring)
│   │   ├── csp_solver.py        # Algoritmo CSP Backtracking, diagnóstico y XAI
│   │   ├── learning.py          # Modelo de aprendizaje adaptativo por rechazos
│   │   └── scoring.py           # Funciones de costo, penalización y explicaciones
│   ├── api/
│   │   └── endpoints/           # Controladores de rutas REST
│   │       ├── ai.py            # Generación inteligente de agenda diaria
│   │       ├── auth.py          # Registro y login
│   │       ├── decisions.py     # Registro de retroalimentación del usuario
│   │       ├── google_auth.py   # Flujo OAuth2 de Google
│   │       ├── kpi.py           # Analíticas de adherencia y balance temporal
│   │       ├── tasks.py         # CRUD de tareas y filtros
│   │       ├── time_blocks.py   # Agenda y bloques de tiempo
│   │       ├── user_settings.py # Preferencias de jornada laboral
│   │       └── users.py         # Perfil de usuario
│   ├── core/                    # Configuración central y seguridad
│   │   ├── config.py            # Variables de entorno y ajustes
│   │   └── security.py          # Criptografía y tokens JWT
│   ├── db/                      # Capa de datos y persistencia
│   │   ├── models.py            # Modelos SQLAlchemy (Task, TimeBlock, User, etc.)
│   │   └── session.py           # Conexión y sesión de base de datos
│   ├── schemas/                 # Validación de datos con Pydantic
│   │   ├── decision_schema.py
│   │   ├── task_schema.py
│   │   ├── time_block_schema.py
│   │   ├── user_schema.py
│   │   └── user_settings_schema.py
│   ├── services/                # Capa de servicios y lógica de negocio
│   │   ├── ai_service.py
│   │   ├── google_calendar_service.py # Sincronización con zona horaria UTC-5
│   │   ├── task_service.py
│   │   ├── time_block_service.py
│   │   └── user_settings_service.py
│   └── main.py                  # Instancia principal de la aplicación FastAPI
├── tests/                       # Suite de evaluación empírica y experimentos (TG)
│   ├── benchmark_csp.py         # Medición de tiempo de ejecución del motor (OE3)
│   ├── simulacion_aprendizaje.py# Simulación del modelo adaptativo a 14 días (Sección 4.2)
│   ├── probar_google_calendar.py# Pruebas de integración y latencia de Google Calendar (OE4)
│   ├── resultados/              # Archivos CSV y gráficas generadas de las pruebas
│   │   ├── benchmark_csp_resultados.csv
│   │   ├── simulacion_aprendizaje_resultados.csv
│   │   └── probar_google_calendar_resultados.csv
│   └── README.md                # Guía de ejecución de la suite de pruebas
├── .env                         # Variables de entorno (credenciales y base de datos)
├── credentials.json             # Credenciales cliente OAuth2 de Google Cloud
├── requirements.txt             # Dependencias del proyecto Python
└── README.md                    # Documentación técnica del backend
```

---

## 🧪 Suite de Pruebas y Evaluación Empírica

Para la validación del Trabajo de Grado frente al Marco Lógico, el backend cuenta con scripts de evaluación experimental automatizados dentro de la carpeta `tests/`:

1. **Benchmark de Rendimiento CSP (`tests/benchmark_csp.py`)**:
   - Evalúa el indicador del **OE3** (tiempo de ejecución $< 5$ segundos para $n = 20$ tareas).
   - Ejecución:
     ```powershell
     python tests/benchmark_csp.py
     ```

2. **Simulación de Aprendizaje Adaptativo (`tests/simulacion_aprendizaje.py`)**:
   - Evalúa la adaptación ante rechazos y simula el uso durante 14 días (con vs. sin aprendizaje).
   - Ejecución:
     ```powershell
     python tests/simulacion_aprendizaje.py
     ```

3. **Pruebas de Integración con Google Calendar (`tests/probar_google_calendar.py`)**:
   - Evalúa el indicador del **OE4** ($\ge 95\%$ de éxito, sin duplicidad, latencia $< 3$ s).
   - Ejecución:
     ```powershell
     python tests/probar_google_calendar.py
     ```

Los resultados detallados se exportan automáticamente en formato CSV a la subcarpeta `tests/resultados/`.

---

## 🚀 Instalación y Puesta en Marcha

### Requisitos Técnicos
- **Python**: `v3.10` o superior
- **PostgreSQL**: Servidor de base de datos relacional activo
- **Virtualenv**: Entorno virtual de Python

### Pasos de Instalación

1. **Clonar el repositorio e ingresar a la carpeta**:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd TG/Backend-WikiPlanner
   ```

2. **Crear y activar el entorno virtual**:
   - En Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - En Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el archivo `.env`**:
   Crea o edita el archivo `.env` en la raíz del backend:
   ```env
   PROJECT_NAME="WikiPlanner API"
   DATABASE_URL="postgresql://postgres:tu_password@localhost:5432/wikiplanner_db"
   SECRET_KEY="TuClaveSuperSecretaDePrueba"
   GOOGLE_CLIENT_ID="tu_google_client_id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="tu_google_client_secret"
   GOOGLE_REDIRECT_URI="http://localhost:8000/api/google/callback"
   ```

5. **Iniciar el servidor backend**:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Documentación Interactiva (Swagger / OpenAPI)**:
   Accede a la documentación automática y prueba los endpoints en:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🎓 Información Académica del Proyecto

- **Título del Trabajo de Grado**: *Implementación de un sistema inteligente adaptativo para la gestión y optimización del tiempo.*
- **Autor**: Juan Sebastián Gómez Agudelo (*Código: 2259474*)
- **Director**: MSc. Joshua David Triana Madrid, Ing.
- **Institución**: Universidad del Valle - Sede Tuluá
- **Facultad**: Facultad de Ingeniería
- **Escuela**: Escuela de Ingeniería de Sistemas y Computación
- **Año**: 2025 - 2026

---

## 📄 Licencia

Este proyecto ha sido desarrollado con fines exclusivamente académicos e investigativos en el marco del programa de Ingeniería de Sistemas y Computación de la **Universidad del Valle**.
