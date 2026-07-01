from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import logging
import asyncio
from pathlib import Path
from services.firestore_client import get_db
from handlers.whatsapp_bridge_handler import processar_mensagem_whatsapp

app = Flask(__name__)

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# FIREBASE INITIALIZATION
# ============================================================================

def carregar_firebase_credentials():
    """
    Carrega credenciais Firebase de forma flexível:
    1. Se FIREBASE_CREDENTIALS começa com "{" → usar json.loads()
    2. Caso contrário → tratar como caminho de arquivo
    3. Se arquivo não existir, logar erro claro

    Retorna: dict com credenciais ou raises ValueError
    """
    firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

    if not firebase_credentials:
        raise ValueError(
            "❌ Variável FIREBASE_CREDENTIALS não definida!\n"
            "   Defina como:\n"
            "   - JSON completo: export FIREBASE_CREDENTIALS='{...}'\n"
            "   - Caminho arquivo: export FIREBASE_CREDENTIALS=firebase_credentials.json"
        )

    # Estratégia 1: Se começa com "{", é JSON completo
    if firebase_credentials.strip().startswith("{"):
        logger.info("[FIREBASE] Carregando credenciais de variável JSON")
        try:
            cred_info = json.loads(firebase_credentials)
            logger.info("[FIREBASE] ✅ Credenciais JSON carregadas com sucesso")
            return cred_info
        except json.JSONDecodeError as e:
            raise ValueError(
                f"❌ JSON inválido em FIREBASE_CREDENTIALS: {str(e)[:100]}"
            )

    # Estratégia 2: Tratar como caminho de arquivo
    logger.info(f"[FIREBASE] Tratando como caminho de arquivo: {firebase_credentials}")

    # Tentar como caminho absoluto
    if os.path.isabs(firebase_credentials):
        if os.path.exists(firebase_credentials):
            logger.info(f"[FIREBASE] Arquivo encontrado (absoluto): {firebase_credentials}")
            with open(firebase_credentials, "r") as f:
                cred_info = json.load(f)
            logger.info("[FIREBASE] ✅ Credenciais do arquivo carregadas com sucesso")
            return cred_info
        else:
            raise ValueError(
                f"❌ Arquivo Firebase não encontrado: {firebase_credentials}\n"
                f"   Caminho absoluto: {firebase_credentials}"
            )

    # Tentar como caminho relativo ao diretório do projeto
    rel_path = Path(firebase_credentials)
    if rel_path.exists():
        logger.info(f"[FIREBASE] Arquivo encontrado (relativo): {firebase_credentials}")
        with open(firebase_credentials, "r") as f:
            cred_info = json.load(f)
        logger.info("[FIREBASE] ✅ Credenciais do arquivo carregadas com sucesso")
        return cred_info

    # Tentar no diretório do projeto (raiz)
    project_root = Path(__file__).parent
    abs_path = project_root / firebase_credentials
    if abs_path.exists():
        logger.info(f"[FIREBASE] Arquivo encontrado (relativo ao projeto): {abs_path}")
        with open(abs_path, "r") as f:
            cred_info = json.load(f)
        logger.info("[FIREBASE] ✅ Credenciais do arquivo carregadas com sucesso")
        return cred_info

    # Nenhuma estratégia funcionou
    raise ValueError(
        f"❌ Arquivo Firebase não encontrado: {firebase_credentials}\n"
        f"   Tentadas localizações:\n"
        f"   - Caminho absoluto: {firebase_credentials}\n"
        f"   - Relativo ao cwd: {rel_path.resolve()}\n"
        f"   - Relativo ao projeto: {abs_path}"
    )


try:
    cred_info = carregar_firebase_credentials()
except ValueError as e:
    logger.error(str(e))
    raise

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)

# [INFRA-03] Usar singleton de firestore_client em vez de criar cliente independente
db = get_db()

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
