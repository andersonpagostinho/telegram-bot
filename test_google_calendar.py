import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Pega as credenciais do ambiente
credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not credentials_json:
    print("❌ ERRO: GOOGLE_CREDENTIALS_JSON não foi encontrada!")
    exit()

# Converte a string JSON para um dicionário
try:
    creds_info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/calendar"])
    service = build("calendar", "v3", credentials=creds)

    # Lista os primeiros 5 eventos do calendário para teste
    calendar_id = "andersonpagostinho@gmail.com"  # Substitua pelo ID correto
    events_result = service.events().list(calendarId=calendar_id, maxResults=5, singleEvents=True, orderBy="startTime").execute()
    events = events_result.get("items", [])

    print("✅ Conexão com o Google Calendar bem-sucedida!")
    print(f"📅 Eventos encontrados: {len(events)}")
    for event in events:
        print(f"- {event['summary']} em {event['start'].get('dateTime', event['start'].get('date'))}")

except Exception as e:
    print(f"❌ Erro ao conectar ao Google Calendar: {e}")