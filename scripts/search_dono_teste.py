#!/usr/bin/env python3
"""
Procura por documentos com padrão 'dono_teste_' em Clientes
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
    print("PROCURANDO: dono_teste_* em Clientes")
    print("=" * 80)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()
    clientes_ref = db.collection("Clientes")

    found = []
    total = 0

    print("Lendo documentos de Clientes...\n")

    for doc in clientes_ref.stream():
        total += 1
        doc_id = doc.id
        print(f"  {doc_id}")

        if "dono_teste_" in doc_id.lower():
            found.append(doc_id)
            print(f"    ^^ ENCONTRADO!")

    print("\n" + "=" * 80)
    print("RESULTADO")
    print("=" * 80)
    print(f"Total documentos em Clientes: {total}")
    print(f"Documentos com 'dono_teste_': {len(found)}")

    if found:
        print("\nEncontrados:")
        for doc_id in found:
            print(f"  - {doc_id}")
    else:
        print("\nNenhum documento com 'dono_teste_' foi encontrado")

    # Salvar relatorio
    report = {
        "timestamp": TIMESTAMP,
        "pattern": "dono_teste_",
        "collection": "Clientes",
        "total_documents": total,
        "matching_documents": len(found),
        "document_ids": found
    }

    report_path = "docs/auditorias/SEARCH_dono_teste_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\nRelatorio: " + report_path)

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print("ERRO: " + str(e))
        import traceback
        traceback.print_exc()
        exit(1)
