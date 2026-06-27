#!/usr/bin/env python3
"""
Procura por padrão específico: dono_teste_fc_20260617043914_38
e variações similares
"""

import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

TIMESTAMP = datetime.now().isoformat()
SEARCH_PATTERN = "dono_teste_"
SPECIFIC_ID = "dono_teste_fc_20260617043914_38"

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

def search_recursive(db, collection_ref, path_prefix="", depth=0, results=None):
    """Busca recursiva por padrao."""
    if results is None:
        results = {
            "exact_match": None,
            "similar_matches": [],
            "total_docs_scanned": 0
        }

    if depth > 4:  # Limitar profundidade
        return results

    try:
        for doc in collection_ref.stream():
            results["total_docs_scanned"] += 1
            doc_id = doc.id
            full_path = path_prefix + "/" + doc_id if path_prefix else doc_id

            # Buscar correspondencia exata
            if doc_id == SPECIFIC_ID:
                results["exact_match"] = {
                    "path": full_path,
                    "doc_id": doc_id,
                    "found": True,
                    "data": doc.to_dict()
                }
                print(f"\n*** ENCONTRADO (EXATO): {full_path}")

            # Buscar correspondencias similares (comeca com dono_teste_)
            elif doc_id.startswith(SEARCH_PATTERN):
                results["similar_matches"].append({
                    "path": full_path,
                    "doc_id": doc_id
                })
                print(f"SIMILAR: {full_path}")

            # Procurar em subcoleções
            try:
                for subcol in doc.reference.collections():
                    subcol_ref = db.collection_group(subcol.id) if depth == 0 else subcol
                    if depth > 0:  # Evitar infinita recursao
                        for subdoc in subcol.stream():
                            results["total_docs_scanned"] += 1
                            subdoc_id = subdoc.id
                            sub_path = full_path + "/" + subcol.id + "/" + subdoc_id

                            if subdoc_id == SPECIFIC_ID:
                                results["exact_match"] = {
                                    "path": sub_path,
                                    "doc_id": subdoc_id,
                                    "found": True,
                                    "data": subdoc.to_dict()
                                }
                                print(f"\n*** ENCONTRADO (EXATO): {sub_path}")

                            elif subdoc_id.startswith(SEARCH_PATTERN):
                                results["similar_matches"].append({
                                    "path": sub_path,
                                    "doc_id": subdoc_id
                                })
                                print(f"SIMILAR: {sub_path}")
            except:
                pass

    except Exception as e:
        print(f"Erro ao buscar: {e}")

    return results

def main():
    print("=" * 90)
    print("PROCURANDO: " + SPECIFIC_ID)
    print("=" * 90)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()

    print("Buscando em todas as colecoes...\n")

    results = {
        "exact_match": None,
        "similar_matches": [],
        "total_docs_scanned": 0,
        "search_target": SPECIFIC_ID
    }

    # Buscar em cada colecao
    for collection in db.collections():
        col_name = collection.id
        print(f"[{col_name}]")

        col_results = search_recursive(db, collection, col_name, 0)
        results["total_docs_scanned"] += col_results["total_docs_scanned"]

        if col_results["exact_match"]:
            results["exact_match"] = col_results["exact_match"]

        results["similar_matches"].extend(col_results["similar_matches"])

    print("\n" + "=" * 90)
    print("RESULTADO")
    print("=" * 90)

    if results["exact_match"]:
        print(f"\n*** ENCONTRADO (EXATO): {results['exact_match']['path']}")
        print(f"Dados: {json.dumps(results['exact_match']['data'], indent=2)}")
    else:
        print(f"\n! NAO ENCONTRADO: {SPECIFIC_ID}")

    print(f"\nPadrao similar '{SEARCH_PATTERN}*' encontrados: {len(results['similar_matches'])}")
    if results["similar_matches"]:
        print("\nLista de similares:")
        for match in results["similar_matches"]:
            print(f"  - {match['path']}")

    print(f"\nTotal documentos verificados: {results['total_docs_scanned']}")
    print("=" * 90)

    # Salvar relatorio
    report_path = "docs/auditorias/SEARCH_SPECIFIC_" + SPECIFIC_ID.replace(":", "-") + "_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nRelatorio: {report_path}")

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print("ERRO: " + str(e))
        import traceback
        traceback.print_exc()
        exit(1)
