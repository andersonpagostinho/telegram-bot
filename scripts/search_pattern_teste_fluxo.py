#!/usr/bin/env python3
"""
Procura especificamente por padrão: teste_fluxo_p1_*
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

def search_pattern(db, pattern, path="", depth=0, results=None):
    """Busca recursiva por padrao especifico."""
    if results is None:
        results = {"found": [], "total_checked": 0}

    if depth > 3:
        return results

    try:
        if path == "":
            collections = db.collections()
        else:
            parts = path.split("/")
            doc_ref = db
            for i in range(0, len(parts), 2):
                doc_ref = doc_ref.collection(parts[i]).document(parts[i+1])
            collections = list(doc_ref.collections())

        for collection in collections:
            col_name = collection.id

            for doc in collection.stream():
                results["total_checked"] += 1
                doc_id = doc.id
                doc_path = (path + "/" if path else "") + col_name + "/" + doc_id

                if pattern.lower() in doc_id.lower():
                    results["found"].append({
                        "path": doc_path,
                        "doc_id": doc_id,
                        "collection": col_name
                    })
                    print("ENCONTRADO: " + doc_path)

                try:
                    subcols = list(doc.reference.collections())
                    if subcols:
                        search_pattern(db, pattern, doc_path, depth + 1, results)
                except:
                    pass

    except Exception as e:
        print("Erro: " + str(e))

    return results

def main():
    pattern = "teste_fluxo_p1_"

    print("=" * 70)
    print("BUSCA: " + pattern + "*")
    print("=" * 70)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()
    results = search_pattern(db, pattern)

    print("\n" + "=" * 70)
    print("RESULTADO")
    print("=" * 70)
    print("Total documentos verificados: " + str(results["total_checked"]))
    print("Documentos ENCONTRADOS com '" + pattern + "': " + str(len(results["found"])))
    print("=" * 70)

    if results["found"]:
        print("\nLista:")
        for item in results["found"]:
            print("  - " + item["path"])

    # Salvar
    report_path = "docs/auditorias/SEARCH_" + pattern.replace("*", "") + "_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

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
