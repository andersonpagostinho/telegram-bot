"""
Adicione isto ao seu main.py ou flask_app.py para ter um endpoint de debug em Render

Exemplo:
    from render_debug_endpoint import add_debug_routes
    add_debug_routes(app)  # app é sua instância Flask/FastAPI

Depois acesse: https://seu-app.onrender.com/debug/firebase
"""

import os
import base64
import json


def add_debug_routes(app):
    """Adiciona rotas de debug para diagnosticar credenciais em Render"""

    @app.route("/debug/firebase", methods=["GET"])
    def debug_firebase():
        """Diagnóstico de FIREBASE_CREDENTIALS_B64"""

        result = {
            "timestamp": str(os.popen("date").read()),
            "environment": {},
            "tests": {},
            "status": "OK"
        }

        # ========== VERIFICAR VARIÁVEIS ==========
        b64_var = os.getenv("FIREBASE_CREDENTIALS_B64")
        json_var = os.getenv("FIREBASE_CREDENTIALS")

        result["environment"]["FIREBASE_CREDENTIALS_B64"] = {
            "exists": b64_var is not None,
            "size": len(b64_var) if b64_var else 0
        }

        result["environment"]["FIREBASE_CREDENTIALS"] = {
            "exists": json_var is not None,
            "size": len(json_var) if json_var else 0
        }

        # ========== TESTE 1: Base64 EXISTE? ==========
        if not b64_var:
            result["tests"]["b64_exists"] = False
            result["status"] = "ERROR"
            result["error"] = "FIREBASE_CREDENTIALS_B64 não definida em Render"
            return result, 400

        result["tests"]["b64_exists"] = True
        result["tests"]["b64_size"] = len(b64_var)
        result["tests"]["b64_size_correct"] = len(b64_var) == 3224

        if len(b64_var) < 3224:
            result["status"] = "WARN"
            result["warning"] = f"Base64 truncada (recebeu {len(b64_var)}, esperado 3224)"

        # ========== TESTE 2: Decodificar ==========
        try:
            decoded = base64.b64decode(b64_var).decode('utf-8')
            result["tests"]["b64_decode"] = True
            result["tests"]["decoded_size"] = len(decoded)
        except Exception as e:
            result["tests"]["b64_decode"] = False
            result["tests"]["b64_decode_error"] = str(e)[:100]
            result["status"] = "ERROR"
            return result, 400

        # ========== TESTE 3: JSON válido? ==========
        try:
            json_obj = json.loads(decoded)
            result["tests"]["json_valid"] = True
        except json.JSONDecodeError as e:
            result["tests"]["json_valid"] = False
            result["tests"]["json_error"] = str(e)[:100]
            result["status"] = "ERROR"
            return result, 400

        # ========== TESTE 4: Campos obrigatórios ==========
        campos = ["type", "project_id", "private_key", "client_email"]
        campos_encontrados = [c for c in campos if c in json_obj]
        campos_faltando = [c for c in campos if c not in json_obj]

        result["tests"]["required_fields"] = {
            "found": campos_encontrados,
            "missing": campos_faltando,
            "complete": len(campos_faltando) == 0
        }

        if campos_faltando:
            result["status"] = "ERROR"
            result["error"] = f"Campos faltando: {campos_faltando}"
            return result, 400

        # ========== TESTE 5: Valores de campos ==========
        result["tests"]["fields"] = {
            "type": json_obj.get("type"),
            "project_id": json_obj.get("project_id"),
            "client_email": json_obj.get("client_email"),
            "private_key_len": len(json_obj.get("private_key", ""))
        }

        # ========== RESULTADO ==========
        result["summary"] = "✅ Credenciais OK, pronto para usar"
        return result, 200

    @app.route("/debug/firebase/full", methods=["GET"])
    def debug_firebase_full():
        """Output completo (pode ser longo)"""

        b64_var = os.getenv("FIREBASE_CREDENTIALS_B64")

        if not b64_var:
            return {
                "error": "FIREBASE_CREDENTIALS_B64 não definida",
                "size": 0
            }, 400

        try:
            decoded = base64.b64decode(b64_var).decode('utf-8')
            json_obj = json.loads(decoded)

            return {
                "b64_size": len(b64_var),
                "decoded_size": len(decoded),
                "json": json_obj,
                "status": "OK"
            }, 200
        except Exception as e:
            return {
                "error": str(e),
                "b64_size": len(b64_var)
            }, 400

    return app


# Se executado diretamente (teste local)
if __name__ == "__main__":
    from flask import Flask

    app = Flask(__name__)
    add_debug_routes(app)

    print("🚀 Servidor de debug iniciado")
    print("   Acesse: http://localhost:5000/debug/firebase")

    app.run(debug=True, port=5000)
