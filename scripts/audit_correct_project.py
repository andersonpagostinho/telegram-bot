#!/usr/bin/env python3
"""
Auditoria completa: TODOS os documentos de teste no Firestore.
Usando projeto-agente-inteligente
"""

import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

TEST_PREFIXES = ["teste_", "teste_fluxo_p1_", "debug_", "tmp_", "dono_teste_", "bateria_"]
TEST_COLLECTION_KEYWORDS = ["teste", "debug", "test_"]
TEST_IDS = {"9999999999", "None", "null", "undefined"}

TIMESTAMP = datetime.now().isoformat()

def init_firestore():
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        raise Exception(f"Credenciais nao encontradas: {cred_path}")

    try:
        cred = credentials.Certificate(cred_path)
        # Especificar projeto explicitamente
        firebase_admin.initialize_app(cred, {"projectId": "projeto-agente-inteligente"})
    except ValueError:
        # App ja inicializado
        pass

    return firestore.client()

def is_test_doc(doc_id):
    """Verificar se documento eh teste."""
    doc_str = str(doc_id).lower()

    if doc_str in {"9999999999", "none", "null", "undefined"}:
        return True

    for prefix in TEST_PREFIXES:
        if doc_str.startswith(prefix.lower()):
            return True

    return False

def is_test_collection(col_name):
    """Verificar se colecao eh teste."""
    col_lower = col_name.lower()
    for keyword in TEST_COLLECTION_KEYWORDS:
        if keyword in col_lower:
            return True
    return False

def main():
    print("=" * 70)
    print("AUDITORIA COMPLETA DE TESTES NO FIREBASE")
    print("Projeto: projeto-agente-inteligente")
    print("=" * 70)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()

    results = {
        "timestamp": TIMESTAMP,
        "projeto": "projeto-agente-inteligente",
        "total_collections": 0,
        "test_collections": 0,
        "total_test_docs": 0,
        "collections": {}
    }

    print("Varrendo colecoes...\n")

    for collection in db.collections():
        col_name = collection.id
        results["total_collections"] += 1

        is_test_col = is_test_collection(col_name)

        test_docs_in_col = []
        total_docs_in_col = 0

        for doc in collection.stream():
            total_docs_in_col += 1
            if is_test_doc(doc.id):
                test_docs_in_col.append(doc.id)
                results["total_test_docs"] += 1

        if is_test_col:
            results["test_collections"] += 1
            status = "[COLECAO TESTE]"
        else:
            status = "            "

        print("[{}] {} | {} docs | {} testes".format(status, col_name.ljust(40), str(total_docs_in_col).rjust(4), str(len(test_docs_in_col)).rjust(4)))

        if len(test_docs_in_col) > 0 or is_test_col:
            results["collections"][col_name] = {
                "is_test_collection": is_test_col,
                "total_docs": total_docs_in_col,
                "test_doc_ids": test_docs_in_col
            }

    print("\n" + "=" * 70)
    print("RESULTADO FINAL")
    print("=" * 70)
    print("Colecoes totais: {}".format(results["total_collections"]))
    print("Colecoes de TESTE: {}".format(results["test_collections"]))
    print("Documentos de TESTE: {}".format(results["total_test_docs"]))
    print("=" * 70)

    # Salvar relatório
    report_path = "docs/auditorias/FULL_AUDIT_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\nRelatorio salvo: " + report_path + "\n")

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print("ERRO: " + str(e))
        import traceback
        traceback.print_exc()
        exit(1)
