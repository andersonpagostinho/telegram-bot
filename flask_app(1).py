from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

app = Flask(__name__)

# 🔥 Inicializar Firebase se ainda não estiver rodando
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if not firebase_credentials:
    raise ValueError("❌ Credenciais do Firebase não encontradas!")

cred_info = json.loads(firebase_credentials)

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

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
