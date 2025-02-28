import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Caminho do JSON no Render
google_json_path = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not google_json_path or not os.path.exists(google_json_path):
    raise ValueError("❌ Arquivo de credenciais do Google não encontrado!")

with open(google_json_path, "r") as f:
    creds_info = json.load(f)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)

def get_calendar_service():
    return build("calendar", "v3", credentials=creds)
