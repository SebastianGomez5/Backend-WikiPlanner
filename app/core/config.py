import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "API Agenda Inteligente"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "UnaClaveSuperSecretaParaMiProyectoDeGrado2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI")
settings = Settings()