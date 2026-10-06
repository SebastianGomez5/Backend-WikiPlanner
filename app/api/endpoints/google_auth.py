# app/api/endpoints/google_auth.py
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import requests
import urllib.parse

from app.db.session import get_db
from app.api import deps
from app.db import models
from app.core.config import settings

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email"


@router.get("/authorize")
def google_authorize(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token inválido")
    except (JWTError, ValueError):
        return HTMLResponse("<h2>❌ Sesión inválida o expirada. Vuelve a iniciar sesión en la app.</h2>")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": user_id,
    }

    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_id = state

    token_response = requests.post(GOOGLE_TOKEN_URL, data={
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
    })

    token_data = token_response.json()

    if "refresh_token" not in token_data:
        return HTMLResponse("""
            <h2>⚠️ No se recibió un token de actualización</h2>
            <p>Por favor revoca el acceso en 
            <a href="https://myaccount.google.com/permissions" target="_blank">
            myaccount.google.com/permissions</a> e intenta de nuevo.</p>
        """)

    
    google_email = None
    access_token = token_data.get("access_token")
    if access_token:
        userinfo_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_response.status_code == 200:
            google_email = userinfo_response.json().get("email")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.google_refresh_token = token_data["refresh_token"]
        user.google_email = google_email
        db.commit()

    return HTMLResponse(f"""
        <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1>✅ Cuenta de Google conectada</h1>
                <p>{google_email or ''}</p>
                <p>Ya puedes cerrar esta ventana y volver a la aplicación.</p>
            </body>
        </html>
    """)


@router.get("/status")
def google_status(current_user: models.User = Depends(deps.get_current_user)):
    return {
        "conectado": bool(current_user.google_refresh_token),
        "email": current_user.google_email
    }


@router.delete("/disconnect")
def google_disconnect(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    current_user.google_refresh_token = None
    current_user.google_email = None
    db.commit()
    return {"mensaje": "Cuenta de Google desconectada exitosamente."}