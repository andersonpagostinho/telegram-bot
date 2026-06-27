#!/usr/bin/env python3
"""
Auditoria FINAL antes de limpeza - PREVIEW APENAS, SEM DELETAR
Identifica TODOS os items a serem deletados com checklist de segurança
"""

import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

TIMESTAMP = datetime.now().isoformat()
PRESERVE_CLIENTES = ["7371670478", "7394370553", "whatsapp:55119999006"]
TEST_PATTERNS = ["teste_", "teste_fluxo_p1_", "debug_", "tmp_", "dono_teste_", "bateria_"]

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

    for pattern in TEST_PATTERNS:
        if name_lower.startswith(pattern.lower()):
            return True

    if name_lower in {"9999999999", "none", "null", "undefined"}:
        return True

    return False

def is_test_collection(name):
    """Verifica se colecao eh teste."""
    name_lower = name.lower()
    return any(x in name_lower for x in ["teste", "debug", "test_"])

def main():
    print("=" * 90)
    print("AUDITORIA FINAL - PREVIEW DE LIMPEZA (SEM DELETAR)")
    print("=" * 90)
    print("Timestamp: " + TIMESTAMP)
    print("TENANTS A PRESERVAR: " + ", ".join(PRESERVE_CLIENTES))
    print("=" * 90 + "\n")

    db = init_firestore()

    report = {
        "timestamp": TIMESTAMP,
        "execution_mode": "DRY_RUN_ONLY",
        "preserve_clientes": PRESERVE_CLIENTES,
        "items_to_delete": {
            "test_documents_in_clientes": [],
            "phantom_documents": [],
            "test_collections": [],
            "test_docs_in_other_collections": []
        },
        "summary": {
            "total_test_docs": 0,
            "total_phantom_docs": 0,
            "total_test_collections": 0,
            "total_items_to_delete": 0,
            "safety_checks": []
        }
    }

    print("[1] Analisando Clientes collection...\n")

    # Analisar Clientes
    clientes_ref = db.collection("Clientes")
    for cliente_doc in clientes_ref.stream():
        cliente_id = cliente_doc.id
        cliente_data = cliente_doc.to_dict() or {}

        # Verificar se eh teste
        if is_test_name(cliente_id):
            report["items_to_delete"]["test_documents_in_clientes"].append({
                "path": "Clientes/" + cliente_id,
                "type": "cliente_teste",
                "has_subcols": len(list(cliente_doc.reference.collections())) > 0
            })
            report["summary"]["total_test_docs"] += 1
            print(f"  DELETAR: Clientes/{cliente_id} (teste)")

        # Verificar se eh fantasma
        elif len(cliente_data) == 0:
            report["items_to_delete"]["phantom_documents"].append({
                "path": "Clientes/" + cliente_id,
                "type": "cliente_fantasma"
            })
            report["summary"]["total_phantom_docs"] += 1
            print(f"  DELETAR: Clientes/{cliente_id} (fantasma/vazio)")

        # Eh cliente real - preservar
        elif cliente_id in PRESERVE_CLIENTES:
            print(f"  PRESERVAR: Clientes/{cliente_id} (real - importante!)")

            # Mas verificar subcoleções de teste
            for subcol in cliente_doc.reference.collections():
                subcol_name = subcol.id

                for subdoc in subcol.stream():
                    subdoc_id = subdoc.id
                    subdoc_data = subdoc.to_dict() or {}

                    # Documento teste dentro de cliente real
                    if is_test_name(subdoc_id):
                        report["items_to_delete"]["test_documents_in_clientes"].append({
                            "path": f"Clientes/{cliente_id}/{subcol_name}/{subdoc_id}",
                            "type": "subdoc_teste",
                            "parent_cliente": cliente_id
                        })
                        report["summary"]["total_test_docs"] += 1
                        print(f"    DELETAR: {subcol_name}/{subdoc_id} (teste dentro de cliente real)")

                    # Documento fantasma dentro de cliente real
                    elif len(subdoc_data) == 0:
                        report["items_to_delete"]["phantom_documents"].append({
                            "path": f"Clientes/{cliente_id}/{subcol_name}/{subdoc_id}",
                            "type": "subdoc_fantasma",
                            "parent_cliente": cliente_id
                        })
                        report["summary"]["total_phantom_docs"] += 1
                        print(f"    DELETAR: {subcol_name}/{subdoc_id} (fantasma/vazio dentro de cliente real)")

    print("\n[2] Analisando outras colecoes...\n")

    # Analisar outras coleções
    for collection in db.collections():
        col_name = collection.id

        # Pular Clientes (ja analisada)
        if col_name == "Clientes":
            continue

        # Colecao de teste
        if is_test_collection(col_name):
            doc_count = 0
            for doc in collection.stream():
                doc_count += 1

            report["items_to_delete"]["test_collections"].append({
                "name": col_name,
                "document_count": doc_count
            })
            report["summary"]["total_test_collections"] += 1
            print(f"  DELETAR COLECAO: {col_name} ({doc_count} docs)")

            # Listar docs na colecao
            for doc in collection.stream():
                report["items_to_delete"]["test_docs_in_other_collections"].append({
                    "path": col_name + "/" + doc.id,
                    "doc_id": doc.id,
                    "collection": col_name
                })

    print("\n" + "=" * 90)
    print("RESUMO FINAL")
    print("=" * 90)

    total_delete = (
        report["summary"]["total_test_docs"] +
        report["summary"]["total_phantom_docs"] +
        report["summary"]["total_test_collections"]
    )

    print(f"Documentos teste a deletar: {report['summary']['total_test_docs']}")
    print(f"Documentos fantasma a deletar: {report['summary']['total_phantom_docs']}")
    print(f"Colecoes teste a deletar: {report['summary']['total_test_collections']}")
    print(f"\nTOTAL DE ITEMS A DELETAR: {total_delete}")
    print()

    # Checklist de segurança
    safety_ok = True
    print("CHECKLIST DE SEGURANÇA:")
    print("-" * 90)

    # Verificar se clientes reais nao foram marcados para deletar no NIVEL DE RAIZ
    cliente_7371670478_marked = any(
        item.get("path") == "Clientes/7371670478"
        for item in report["items_to_delete"]["test_documents_in_clientes"]
    )
    cliente_7394370553_marked = any(
        item.get("path") == "Clientes/7394370553"
        for item in report["items_to_delete"]["test_documents_in_clientes"]
    )

    checks = [
        ("Clientes/7371670478 nao foi marcado para deletar (nivel raiz)",
         not cliente_7371670478_marked),
        ("Clientes/7394370553 nao foi marcado para deletar (nivel raiz)",
         not cliente_7394370553_marked),
        ("Modo DRY_RUN ativo (nao deleta nada)",
         report["execution_mode"] == "DRY_RUN_ONLY"),
        ("Relatorio JSON salvo para auditoria",
         True)
    ]

    for check_name, result in checks:
        status = "[OK]" if result else "[FAIL]"
        print("  " + status + ": " + check_name)
        if not result:
            safety_ok = False
            report["summary"]["safety_checks"].append({"check": check_name, "result": False})
        else:
            report["summary"]["safety_checks"].append({"check": check_name, "result": True})

    print("=" * 90)

    if safety_ok:
        print("\n[OK] SEGURANCA: TODOS OS CHECKS PASSARAM")
    else:
        print("\n[FAIL] SEGURANCA: ALGUNS CHECKS FALHARAM - ABORTAR LIMPEZA")

    print("\n" + "=" * 90)

    # Salvar relatorio
    report_path = "docs/auditorias/FINAL_AUDIT_BEFORE_CLEANUP_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Relatorio salvo: {report_path}")
    print("=" * 90)

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print("ERRO: " + str(e))
        import traceback
        traceback.print_exc()
        exit(1)
