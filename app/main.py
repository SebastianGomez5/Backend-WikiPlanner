from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db import models
from app.api.endpoints import tasks
from app.api.endpoints import users
from app.api.endpoints import auth
from app.api.endpoints import user_settings
from app.api.endpoints import time_blocks
from app.api.endpoints import ai
from app.api.endpoints import decisions
from app.api.endpoints import kpi

models.Base.metadata.create_all(bind=engine) # Crea las tablas en la base de datos

app = FastAPI(
    title="WikiPlanner",
    description="Backend para el sistema de agendamiento dinámico con IA",
    version="1.0.0"
)

# 2. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En desarrollo permitimos todo
    allow_credentials=True,
    allow_methods=["*"],  # Permite leer, crear, actualizar y borrar datos.
    allow_headers=["*"],  # Permite cualquier tipo de encabezado de seguridad.
)

app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tareas"])
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])
app.include_router(user_settings.router, prefix="/api/settings", tags=["Preferencias"])
app.include_router(time_blocks.router, prefix="/api/time-blocks", tags=["Bloques de Tiempo"])
app.include_router(ai.router, prefix="/api/ai", tags=["Inteligencia Artificial"])
app.include_router(decisions.router, prefix="/api/decisions", tags=["Historial de Decisiones"])
app.include_router(kpi.router, prefix="/api/kpi", tags=["KPIs"])

# 3. Ruta de prueba o "Health Check"
@app.get("/")
def read_root():
    return {
        "estado": "Activo",
        "mensaje": "El servidor de la Agenda Inteligente está funcionando correctamente."
    }

# Nota: Más adelante, aquí importaremos y conectaremos las rutas de las tareas y usuarios.