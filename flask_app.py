from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import logging
import asyncio
from services.firestore_client import get_db
from handlers.whatsapp_bridge_handler import processar_mensagem_whatsapp

app = Flask(__name__)

# 🔥 Inicializar Firebase se ainda não estiver rodando
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials:
    raise ValueError("❌ Credenciais do Firebase não encontradas!")

cred_info = json.loads(firebase_credentials)

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)

# [INFRA-03] Usar singleton de firestore_client em vez de criar cliente independente
db = get_db()

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# ENDPOINT: POST /whatsapp/incoming
# ============================================================================

@app.route("/whatsapp/incoming", methods=["POST"])
def whatsapp_incoming():
    """
    Ponte WhatsApp Adapter → NeoEve Core

    POST /whatsapp/incoming
    Content-Type: application/json

    Payload:
    {
      "canal": "whatsapp",
      "tenant_id": "7394370553",
      "neoeve_number": "5519994443694",
      "actor_id": "5519999999999",
      "texto": "oi"
    }

    Response:
    {
      "canal": "whatsapp",
      "actor_id": "5519999999999",
      "tenant_id": "7394370553",
      "resposta": "<resposta>"
    }
    """
    try:
        payload = request.get_json()

        logger.info(f"[WHATSAPP_BRIDGE] POST recebido: {payload}")

        # Processar mensagem (executar em event loop)
        resultado = asyncio.run(processar_mensagem_whatsapp(payload))

        logger.info(f"[WHATSAPP_BRIDGE] Resposta: {resultado}")

        return jsonify(resultado), 200

    except Exception as e:
        logger.exception(f"[WHATSAPP_BRIDGE] Erro ao processar request: {e}")
        return (
            jsonify({
                "erro": str(e),
                "resposta": "Desculpa, erro ao processar sua mensagem.",
            }),
            500,
        )


@app.route("/test_firebase")
def test_firebase():
    try:
        # Criar um documento de teste no Firestore
        doc_ref = db.collection("testes").document("primeiro_teste")
        doc_ref.set({"mensagem": "Conexão bem-sucedida no Render!"})

        # Buscar o documento salvo
        doc = doc_ref.get()
        if doc.exists:
            return jsonify({"status": "✅ Firebase conectado!", "data": doc.to_dict()}), 200
        else:
            return jsonify({"status": "❌ Erro ao salvar no Firebase"}), 500

    except Exception as e:
        return jsonify({"status": "❌ Erro ao conectar ao Firebase", "erro": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
