#!/usr/bin/env python3
"""
Auditoria PROFUNDA: Todos documentos de teste, incluindo subcoleções.
"""

import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

TEST_PREFIXES = ["teste_", "teste_fluxo_p1_", "debug_", "tmp_", "dono_teste_", "bateria_"]
TEST_KEYWORDS = ["teste", "debug", "test_"]

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

def is_test_name(name):
    """Verifica se nome eh teste."""
    name_lower = str(name).lower()

    # IDs especificos
    if name_lower in {"9999999999", "none", "null", "undefined"}:
        return True

    # Prefixos
    for prefix in TEST_PREFIXES:
        if name_lower.startswith(prefix.lower()):
            return True

    # Palavras-chave
    for keyword in TEST_KEYWORDS:
        if keyword in name_lower:
            return True

    return False

def audit_recursive(db, path="", depth=0, results=None):
    """Audit recursivo de colecoes e subcoleções."""
    if results is None:
        results = {
            "total_test_docs": 0,
            "total_test_cols": 0,
            "total_docs": 0,
            "paths_by_type": {"test_docs": [], "test_cols": []}
        }

    if depth > 3:  # Limitar profundidade
        return results

    try:
        if path == "":
            # Nivel raiz - listar colecoes
            collections = db.collections()
        else:
            # Nivel aninhado - documentos e suas subcoleções
            parts = path.split("/")
            doc_ref = db
            for i in range(0, len(parts), 2):
                doc_ref = doc_ref.collection(parts[i]).document(parts[i+1])
            collections = list(doc_ref.collections())

        for collection in collections:
            col_name = collection.id
            col_path = path + "/" + col_name if path else col_name

            is_test_col = is_test_name(col_name)

            if is_test_col:
                results["total_test_cols"] += 1
                print("  " * depth + "[TEST COL] " + col_path)
                results["paths_by_type"]["test_cols"].append(col_path)

            # Contar documentos
            for doc in collection.stream():
                results["total_docs"] += 1
                doc_id = doc.id
                doc_path = col_path + "/" + doc_id

                is_test_doc = is_test_name(doc_id)

                if is_test_doc:
                    results["total_test_docs"] += 1
                    print("  " * depth + "  [TEST DOC] " + doc_path)
                    results["paths_by_type"]["test_docs"].append(doc_path)

                # Recursao para subcoleções
                try:
                    subcols = list(doc.reference.collections())
                    if subcols:
                        audit_recursive(db, doc_path, depth + 1, results)
                except:
                    pass

    except Exception as e:
        print("Erro em " + str(path) + ": " + str(e))

    return results

def main():
    print("=" * 70)
    print("AUDITORIA PROFUNDA - TODOS NIVEIS")
    print("=" * 70)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()
    results = audit_recursive(db)

    print("\n" + "=" * 70)
    print("RESULTADO FINAL")
    print("=" * 70)
    print("Total documentos: " + str(results["total_docs"]))
    print("Total colecoes: VARIAVEL")
    print()
    print("TESTES ENCONTRADOS:")
    print("  Colecoes de teste: " + str(results["total_test_cols"]))
    print("  Documentos de teste: " + str(results["total_test_docs"]))
    print("=" * 70)

    # Salvar
    report_path = "docs/auditorias/DEEP_AUDIT_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
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
