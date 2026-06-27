#!/usr/bin/env python3
"""
Auditoria de documentos FANTASMA dentro de Clientes/ apenas
Verifica CADA documento e testa ref.get().exists
"""

import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

TIMESTAMP = datetime.now().isoformat()
PRESERVE_CLIENTES = ["7371670478", "7394370553", "whatsapp:55119999006"]

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
    print("=" * 90)
    print("AUDITORIA: Documentos FANTASMA em Clientes/ apenas")
    print("=" * 90)
    print("Timestamp: " + TIMESTAMP)
    print("Tenants REAIS a preservar: " + ", ".join(PRESERVE_CLIENTES))
    print("=" * 90 + "\n")

    db = init_firestore()
    clientes_ref = db.collection("Clientes")

    report = {
        "timestamp": TIMESTAMP,
        "scope": "Clientes/ only",
        "execution_mode": "DRY_RUN_AUDIT_ONLY",
        "preserve_tenants": PRESERVE_CLIENTES,
        "phantom_docs_root": [],
        "phantom_docs_in_subcols": [],
        "real_docs_with_phantom_subdocs": [],
        "summary": {
            "total_root_docs_scanned": 0,
            "total_phantom_docs_root": 0,
            "total_phantom_docs_in_subcols": 0,
            "total_subdocs_scanned": 0
        }
    }

    print("[FASE 1] Varrendo documentos raiz de Clientes/\n")

    # Varrer documentos raiz de Clientes
    for doc_snapshot in clientes_ref.stream():
        doc_id = doc_snapshot.id
        report["summary"]["total_root_docs_scanned"] += 1

        # Verificar se eh documento real
        ref = clientes_ref.document(doc_id)
        exists = ref.get().exists

        if doc_id in PRESERVE_CLIENTES:
            print(f"[REAL] {doc_id}")

            # Mas verificar subcoleções de teste
            print(f"  Verificando subcoleções de {doc_id}...\n")
            for subcol in ref.collections():
                subcol_name = subcol.id

                for subdoc_snapshot in subcol.stream():
                    subdoc_id = subdoc_snapshot.id
                    report["summary"]["total_subdocs_scanned"] += 1

                    # Verificar se subdocumento eh fantasma
                    subdoc_ref = ref.collection(subcol_name).document(subdoc_id)
                    subdoc_exists = subdoc_ref.get().exists

                    if not subdoc_exists:
                        # Fantasma dentro de cliente real
                        report["phantom_docs_in_subcols"].append({
                            "path": f"Clientes/{doc_id}/{subcol_name}/{subdoc_id}",
                            "doc_id": subdoc_id,
                            "parent_tenant": doc_id,
                            "subcol": subcol_name,
                            "exists": False
                        })
                        report["summary"]["total_phantom_docs_in_subcols"] += 1
                        print(f"    [FANTASMA] {subcol_name}/{subdoc_id}")

        else:
            # Documento raiz que nao eh conhecido
            if not exists:
                # Fantasma no nivel raiz
                report["phantom_docs_root"].append({
                    "path": f"Clientes/{doc_id}",
                    "doc_id": doc_id,
                    "type": "root_tenant",
                    "exists": False
                })
                report["summary"]["total_phantom_docs_root"] += 1
                print(f"[FANTASMA] {doc_id} (nao existe)")
            else:
                print(f"[OUTRO] {doc_id} (real, nao reconhecido como teste)")

    print("\n" + "=" * 90)
    print("RESUMO FINAL - CLIENTES/ APENAS")
    print("=" * 90)

    print(f"\nDocumentos raiz verificados: {report['summary']['total_root_docs_scanned']}")
    print(f"Documentos raiz FANTASMA: {report['summary']['total_phantom_docs_root']}")
    print(f"\nSubdocumentos verificados: {report['summary']['total_subdocs_scanned']}")
    print(f"Subdocumentos FANTASMA (em clientes reais): {report['summary']['total_phantom_docs_in_subcols']}")

    total_phantom = (
        report['summary']['total_phantom_docs_root'] +
        report['summary']['total_phantom_docs_in_subcols']
    )

    print(f"\n*** TOTAL DE DOCUMENTOS FANTASMA EM CLIENTES/: {total_phantom} ***")

    print("\n" + "=" * 90)
    print("LISTA DE FANTASMAS")
    print("=" * 90)

    if report["phantom_docs_root"]:
        print("\nFantasmas no nivel raiz de Clientes/:")
        for phantom in report["phantom_docs_root"]:
            print(f"  - {phantom['path']}")

    if report["phantom_docs_in_subcols"]:
        print("\nFantasmas dentro de clientes reais (subcoleções):")
        for phantom in report["phantom_docs_in_subcols"]:
            print(f"  - {phantom['path']}")

    print("\n" + "=" * 90)

    # Salvar relatorio
    report_path = "docs/auditorias/PHANTOM_CLIENTES_ONLY_" + TIMESTAMP.replace(":", "-").split(".")[0] + ".json"
    os.makedirs("docs/auditorias", exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nRelatorio JSON salvo: {report_path}")
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
