from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.db import models
from app.schemas import user_schema
from uuid import UUID

# Configuramos el encriptador de contraseñas usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(db: Session, user: user_schema.UserCreate):
    #Encriptamos la contraseña antes de tocar la base de datos
    hashed_password = pwd_context.hash(user.password)
    
    db_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

# Lógica para actualizar contraseña verificando la anterior
def update_password(db: Session, user_id: UUID, password_data: user_schema.UserPasswordUpdate):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not pwd_context.verify(password_data.current_password, user.password_hash):
        return False
        
    user.password_hash = pwd_context.hash(password_data.new_password)
    db.commit()
    return True