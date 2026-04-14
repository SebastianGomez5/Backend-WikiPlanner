from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db import models

models.Base.metadata.create_all(bind=engine) # Crea las tablas en la base de datos

app = FastAPI(
    title="GIA",
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

# 3. Ruta de prueba o "Health Check"
@app.get("/")
def read_root():
    return {
        "estado": "Activo",
        "mensaje": "El servidor de la Agenda Inteligente está funcionando correctamente."
    }

# Nota: Más adelante, aquí importaremos y conectaremos las rutas de las tareas y usuarios.