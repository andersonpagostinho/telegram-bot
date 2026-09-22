from firebase_admin import firestore
from datetime import datetime, timedelta
import pytz

db = firestore.client()

# Tempo de expiração de sessão (em minutos)
SESSION_TTL_MINUTES = 30

def criar_ou_atualizar_sessao(user_id, dados: dict):
    now = datetime.now(pytz.UTC)
    dados['last_updated'] = now
    db.collection("sessions").document(user_id).set(dados, merge=True)

def pegar_sessao(user_id):
    doc = db.collection("sessions").document(user_id).get()
    if doc.exists:
        sessao = doc.to_dict()
        last_updated = sessao.get('last_updated')
        if last_updated and datetime.now(pytz.UTC) - last_updated > timedelta(minutes=SESSION_TTL_MINUTES):
            resetar_sessao(user_id)
            return None
        return sessao
    return None

def resetar_sessao(user_id):
    db.collection("sessions").document(user_id).delete()

def limpar_sessoes_expiradas():
    limite = datetime.now(pytz.UTC) - timedelta(minutes=SESSION_TTL_MINUTES)
    docs = db.collection("sessions").where("last_updated", "<", limite).stream()
    for doc in docs:
        doc.reference.delete()
