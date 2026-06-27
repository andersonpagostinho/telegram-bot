#!/usr/bin/env python3
"""
Auditoria e limpeza segura de tenants de teste em Firestore.
Executa em dry-run por padrão. Requer --confirm-delete para deletar.
"""

import json
import argparse
import os
from datetime import datetime
from typing import Dict, List, Tuple
import firebase_admin
from firebase_admin import credentials, firestore

# Configuração
TEST_PREFIXES = ["teste_fluxo_p1_", "teste_", "debug_", "tmp_"]
COLLECTION_CLIENTES = "Clientes"
TIMESTAMP = datetime.now().isoformat()
REPORT_DIR = "docs/auditorias"

def init_firestore():
    """Inicializar conexão com Firestore."""
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS não configurada")

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {cred_path}")

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    except ValueError:
        # App já inicializado
        pass

    return firestore.client()

def audit_test_tenants(db) -> Dict:
    """Auditar tenants de teste em Firestore."""
    print(f"[{TIMESTAMP}] Iniciando auditoria de tenants de teste...")

    audit_results = {
        "timestamp": TIMESTAMP,
        "prefixes_checked": TEST_PREFIXES,
        "total_test_tenants": 0,
        "details_by_prefix": {},
        "execution_mode": "dry-run",
        "firestore_path": f"{COLLECTION_CLIENTES}/"
    }

    try:
        clientes_ref = db.collection(COLLECTION_CLIENTES)
        docs = clientes_ref.stream()

        test_tenants = {}
        for doc in docs:
            doc_id = doc.id
            doc_data = doc.to_dict() or {}

            # Verificar se ID tem prefixo de teste
            for prefix in TEST_PREFIXES:
                if doc_id.startswith(prefix):
                    if prefix not in test_tenants:
                        test_tenants[prefix] = []

                    # Contar subcoleções de forma segura
                    try:
                        subcollections = list(doc.reference.collections())
                        subcol_count = len(subcollections)
                    except:
                        subcol_count = 0

                    test_tenants[prefix].append({
                        "id": doc_id,
                        "created_at": doc.create_time.isoformat() if doc.create_time else "unknown",
                        "updated_at": doc.update_time.isoformat() if doc.update_time else "unknown",
                        "subcollections_count": subcol_count,
                        "data_keys": list(doc_data.keys()),
                        "size_estimate": len(json.dumps(doc_data))
                    })
                    break

        # Consolidar resultados
        audit_results["total_test_tenants"] = sum(len(v) for v in test_tenants.values())

        for prefix in TEST_PREFIXES:
            if prefix in test_tenants:
                audit_results["details_by_prefix"][prefix] = {
                    "count": len(test_tenants[prefix]),
                    "samples": test_tenants[prefix][:3],  # Primeiras 3 amostras
                    "total_samples": len(test_tenants[prefix])
                }

        return audit_results

    except Exception as e:
        audit_results["error"] = str(e)
        return audit_results

def delete_test_tenants(db, dry_run: bool = True) -> Dict:
    """Deletar tenants de teste (com confirmação obrigatória)."""
    if dry_run:
        print("[DRY-RUN] Operacao de delecao esta desabilitada. Use --confirm-delete para executar.")
        return {"status": "dry-run", "deleted": 0}

    print("[ACAO DESTRUTIVA] Iniciando delecao de tenants de teste...")

    deleted_count = 0
    clientes_ref = db.collection(COLLECTION_CLIENTES)
    docs = clientes_ref.stream()

    for doc in docs:
        doc_id = doc.id
        for prefix in TEST_PREFIXES:
            if doc_id.startswith(prefix):
                print(f"[DELETANDO] {COLLECTION_CLIENTES}/{doc_id}")
                doc.reference.delete()
                deleted_count += 1
                break

    return {
        "status": "completed",
        "deleted": deleted_count,
        "timestamp": datetime.now().isoformat()
    }

def save_report(audit_data: Dict, filename: str = None):
    """Salvar relatório JSON."""
    if not filename:
        filename = f"FIRESTORE_CLEANUP_01_AUDIT_{TIMESTAMP.replace(':', '-')}.json"

    os.makedirs(REPORT_DIR, exist_ok=True)
    filepath = os.path.join(REPORT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Relatorio salvo: {filepath}")
    return filepath

def main():
    parser = argparse.ArgumentParser(
        description="Auditar e limpar tenants de teste em Firestore"
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        default=False,
        help="OBRIGATÓRIO: Confirmar deleção real de tenants"
    )

    args = parser.parse_args()

    # Se --confirm-delete foi passado, executa em modo deleção
    is_deletion_mode = args.confirm_delete

    print(f"NeoEve Firestore Cleanup Audit")
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Modo: {'DELEÇÃO REAL' if is_deletion_mode else 'DRY-RUN'}")
    print("-" * 60)

    try:
        db = init_firestore()
        print("[OK] Conectado ao Firestore")

        # Executar auditoria
        audit_data = audit_test_tenants(db)
        print(f"[OK] Auditoria concluida")
        print(f"    Total de tenants de teste encontrados: {audit_data['total_test_tenants']}")

        for prefix, details in audit_data["details_by_prefix"].items():
            print(f"    - {prefix}: {details['count']} documentos")

        # Executar deleção (se confirmado)
        if is_deletion_mode:
            delete_result = delete_test_tenants(db, dry_run=False)
            audit_data["deletion_result"] = delete_result
            print(f"[OK] Delecao concluida: {delete_result['deleted']} documentos deletados")
        else:
            audit_data["deletion_result"] = {
                "status": "skipped",
                "reason": "Use --confirm-delete para executar delecao real"
            }

        # Salvar relatório
        save_report(audit_data)

        # Exibir resumo
        print("-" * 60)
        print("RESUMO:")
        print(json.dumps({
            "timestamp": audit_data["timestamp"],
            "total_test_tenants": audit_data["total_test_tenants"],
            "prefixes": audit_data["details_by_prefix"],
            "deletion_status": audit_data.get("deletion_result", {}).get("status", "unknown")
        }, indent=2, ensure_ascii=False))

        return 0

    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
