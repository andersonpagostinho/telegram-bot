#!/usr/bin/env python3
"""
Auditoria COMPLETA da collection Clientes - todos os documentos
"""

import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

TIMESTAMP = datetime.now().isoformat()

def init_firestore():
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        raise Exception("Credenciais nao encontradas")

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"projectId": "projeto-agente-inteligente"})
    except ValueError:
        pass

    return firestore.client()

def main():
    print("=" * 80)
    print("AUDITORIA COMPLETA: Collection 'Clientes'")
    print("=" * 80)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()
    clientes_ref = db.collection("Clientes")

    all_docs = []
    test_docs = []

    print("Lendo todos os documentos de Clientes...\n")

    for doc in clientes_ref.stream():
        doc_id = doc.id
        doc_data = doc.to_dict() or {}

        all_docs.append({
            "id": doc_id,
            "created": doc.create_time.isoformat() if doc.create_time else None,
            "updated": doc.update_time.isoformat() if doc.update_time else None,
            "fields": list(doc_data.keys())
        })

        # Verificar se parece ser teste
        is_test = any([
            "teste" in doc_id.lower(),
            "debug" in doc_id.lower(),
            "tmp" in doc_id.lower(),
            "dono_teste" in doc_id.lower(),
            "bateria" in doc_id.lower(),
            doc_id in {"9999999999", "None", "null", "undefined"},
            len(doc_id) > 20 and doc_id[0].isalpha() and "_" in doc_id,  # UUIDs/test-like
        ])

        if is_test:
            test_docs.append(doc_id)
            print("  [TESTE] " + doc_id)
        else:
            print("  [OK]    " + doc_id)

    print("\n" + "=" * 80)
    print("RESUMO: Collection 'Clientes'")
    print("=" * 80)
    print("Total de documentos: " + str(len(all_docs)))
    print("Documentos de TESTE identificados: " + str(len(test_docs)))
    print()

    if test_docs:
        print("Testes encontrados:")
        for test_id in test_docs:
            print("  - " + test_id)

    # Salvar relatorio detalhado
    report = {
        "timestamp": TIMESTAMP,
        "collection": "Clientes",
        "total_documents": len(all_docs),
        "test_documents": len(test_docs),
        "all_document_ids": [d["id"] for d in all_docs],
        "test_document_ids": test_docs,
        "detailed": all_docs
    }

    report_path = "docs/auditorias/CLIENTES_FULL_AUDIT_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\nRelatorio completo: " + report_path)

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print("ERRO: " + str(e))
        import traceback
        traceback.print_exc()
        exit(1)
