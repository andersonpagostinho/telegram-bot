#!/usr/bin/env python3
"""
Procura e lista documentos 'fantasma' (vazios/orfãos) no Firestore
que aparecem na visualização mas não têm conteúdo real
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
    print("PROCURANDO: Documentos Fantasma/Orfaos (vazios)")
    print("=" * 80)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()
    clientes_ref = db.collection("Clientes")

    phantom_docs = []
    total = 0
    empty = 0

    print("Analisando documentos de Clientes...\n")

    for doc in clientes_ref.stream():
        total += 1
        doc_id = doc.id
        doc_data = doc.to_dict()

        # Documento com dados vazios = fantasma
        if doc_data is None or len(doc_data) == 0:
            empty += 1
            phantom_docs.append({
                "path": "Clientes/" + doc_id,
                "doc_id": doc_id,
                "has_data": False
            })
            print(f"  [FANTASMA] {doc_id}")
        else:
            # Procurar subcoleções vazias ou com documentos fantasma
            try:
                subcols = list(doc.reference.collections())
                for subcol in subcols:
                    for subdoc in subcol.stream():
                        subdoc_id = subdoc.id
                        subdoc_data = subdoc.to_dict()

                        if subdoc_data is None or len(subdoc_data) == 0:
                            empty += 1
                            phantom_docs.append({
                                "path": "Clientes/" + doc_id + "/" + subcol.id + "/" + subdoc_id,
                                "doc_id": subdoc_id,
                                "subcol": subcol.id,
                                "parent": doc_id,
                                "has_data": False
                            })
                            print(f"  [FANTASMA] Clientes/{doc_id}/{subcol.id}/{subdoc_id}")
            except:
                pass

    print("\n" + "=" * 80)
    print("RESULTADO")
    print("=" * 80)
    print(f"Total documentos analisados: {total}")
    print(f"Documentos fantasma encontrados: {empty}")
    print("=" * 80)

    if phantom_docs:
        print("\nDocumentos fantasma:")
        for doc in phantom_docs:
            print(f"  - {doc['path']}")

    # Salvar relatorio
    report = {
        "timestamp": TIMESTAMP,
        "total_documents_scanned": total,
        "phantom_documents_found": empty,
        "phantom_docs": phantom_docs
    }

    report_path = "docs/auditorias/PHANTOM_DOCS_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nRelatorio: {report_path}")

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
