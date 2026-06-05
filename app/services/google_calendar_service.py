import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Si modificas estos SCOPES, elimina el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Gestiona la autenticación y devuelve el objeto del servicio de Google Calendar."""
    creds = None
    # El archivo token.json guarda los tokens de acceso y refresco del usuario.
    # Se crea automáticamente cuando el flujo se completa por primera vez.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si no hay credenciales válidas disponibles, dejamos que el usuario inicie sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardamos las credenciales para la próxima vez
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def create_google_event(task_title, start_time, end_time):
    """Crea un evento real en el Google Calendar del usuario."""
    try:
        service = get_calendar_service()

        event = {
            'summary': task_title,
            'description': 'Generado por Agenda IA inteligente',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Bogota', # Ajusta a tu zona horaria de Colombia
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Bogota',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('id')

    except HttpError as error:
        print(f'Ocurrió un error con la API de Google: {error}')
        return None

def delete_google_event(event_id: str):
    """
    Elimina un evento específico de Google Calendar usando su ID.
    Esta función es vital para no duplicar eventos al regenerar la agenda.
    """
    if not event_id:
        return False
        
    try:
        service = get_calendar_service()
        
        # 'primary' indica que es el calendario principal del usuario
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"Evento {event_id} eliminado de Google Calendar exitosamente.")
        return True
    except Exception as e:
        print(f"Error al eliminar el evento de Google Calendar: {e}")
        return False