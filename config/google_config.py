import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 🔹 Obtém a credencial do JSON da variável de ambiente
google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not google_credentials_json:
    raise ValueError("❌ Credenciais do Google não encontradas na variável de ambiente!")

# 🔹 Converte a string JSON para um dicionário
creds_info = json.loads(google_credentials_json)

# 🔹 Carrega as credenciais a partir do dicionário
creds = service_account.Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/calendar"])

def get_calendar_service():
    return build("calendar", "v3", credentials=creds)
