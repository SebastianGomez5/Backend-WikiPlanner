from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.core import security

router = APIRouter()


# Swagger ponga un botón de "Authorize" automático en la documentación.
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Buscamos al usuario por su correo (Swagger usa el campo 'username' para el correo por defecto en este formulario)
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # 2. Si no existe o la contraseña está mal, lanzamos un error 401 (No autorizado)
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Si todo está bien, le fabricamos su token metiendo su ID adentro (convertido a string)
    access_token = security.create_access_token(data={"sub": str(user.id)})
    
    # 4. Devolvemos el token en el formato estándar de OAuth2
    return {"access_token": access_token, "token_type": "bearer"}