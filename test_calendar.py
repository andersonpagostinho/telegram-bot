from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"  # Certifique-se de que o arquivo existe!

def get_calendar_service():
    try:
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        service = build("calendar", "v3", credentials=creds)
        print("✅ Conectado ao Google Calendar com sucesso!")
        return service
    except Exception as e:
        print(f"❌ Erro ao conectar ao Google Calendar: {e}")
        return None

def add_event():
    service = get_calendar_service()
    if not service:
        print("❌ Serviço do Google Calendar não disponível.")
        return

    event = {
        'summary': 'Teste Evento Manual',
        'start': {'dateTime': '2025-02-08T15:00:00', 'timeZone': 'America/Sao_Paulo'},
        'end': {'dateTime': '2025-02-08T16:00:00', 'timeZone': 'America/Sao_Paulo'},
    }

    try:
        evento_criado = service.events().insert(calendarId='primary', body=event).execute()
        print("✅ Evento Criado com Sucesso!")
        print(f"ID: {evento_criado.get('id')}")
        print(f"Link: {evento_criado.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Erro ao criar evento: {e}")

add_event()

