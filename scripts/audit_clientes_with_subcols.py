#!/usr/bin/env python3
"""
Auditoria COMPLETA de Clientes + todas suas subcoleções
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

def count_tests_in_path(db, path):
    """Conta testes em um caminho especifico."""
    tests = []

    try:
        parts = path.split("/")
        ref = db
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):
                ref = ref.collection(parts[i]).document(parts[i+1])

        # Se chegou aqui, ref eh um documento
        # Pegar suas subcoleções
        for subcol in ref.collections():
            for doc in subcol.stream():
                doc_id = doc.id
                if any(x in doc_id.lower() for x in ["teste", "test", "debug", "tmp", "dono_teste", "bateria"]):
                    tests.append({
                        "path": path + "/" + subcol.id + "/" + doc_id,
                        "type": "subcollection_doc"
                    })
    except:
        pass

    return tests

def main():
    print("=" * 80)
    print("AUDITORIA: Clientes + Subcoleções")
    print("=" * 80)
    print("Timestamp: " + TIMESTAMP + "\n")

    db = init_firestore()
    clientes_ref = db.collection("Clientes")

    all_results = {
        "timestamp": TIMESTAMP,
        "total_clientes": 0,
        "total_subcols": 0,
        "total_docs_in_subcols": 0,
        "total_tests": 0,
        "clientes": {}
    }

    print("Analisando cada cliente...\n")

    for cliente_doc in clientes_ref.stream():
        cliente_id = cliente_doc.id
        all_results["total_clientes"] += 1

        print("[Cliente] " + cliente_id)

        cliente_info = {
            "id": cliente_id,
            "subcoleções": {}
        }

        # Listar subcoleções
        for subcol in cliente_doc.reference.collections():
            subcol_name = subcol.id
            all_results["total_subcols"] += 1

            subcol_info = {
                "name": subcol_name,
                "total_docs": 0,
                "test_docs": []
            }

            print("  [Subcol] " + subcol_name)

            # Contar documentos e testes
            for doc in subcol.stream():
                subcol_info["total_docs"] += 1
                all_results["total_docs_in_subcols"] += 1

                doc_id = doc.id
                full_path = cliente_id + "/" + subcol_name + "/" + doc_id

                # Detectar testes
                is_test = any(x in doc_id.lower() for x in ["teste", "test_", "debug_", "tmp_", "dono_teste_", "bateria_"])

                if is_test:
                    subcol_info["test_docs"].append(doc_id)
                    all_results["total_tests"] += 1
                    print("    [TESTE] " + doc_id)
                else:
                    print("    [OK]    " + doc_id)

            cliente_info["subcoleções"][subcol_name] = subcol_info

        all_results["clientes"][cliente_id] = cliente_info
        print()

    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print("Total de clientes: " + str(all_results["total_clientes"]))
    print("Total de subcoleções: " + str(all_results["total_subcols"]))
    print("Total de documentos em subcoleções: " + str(all_results["total_docs_in_subcols"]))
    print("TOTAL DE TESTES: " + str(all_results["total_tests"]))
    print("=" * 80)

    # Salvar
    report_path = "docs/auditorias/CLIENTES_WITH_SUBCOLS_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(all_results, f, indent=2)

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
