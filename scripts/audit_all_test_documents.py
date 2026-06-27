#!/usr/bin/env python3
"""
Auditoria completa de TODOS os documentos de teste no Firestore.
Procura em todas as coleções, não apenas em Clientes.
Modo dry-run por padrão. Nenhuma deleção sem --confirm-delete.
"""

import json
import argparse
import os
from datetime import datetime
from typing import Dict, List, Set
import firebase_admin
from firebase_admin import credentials, firestore

TEST_PREFIXES = ["teste_", "teste_fluxo_p1_", "debug_", "tmp_", "dono_teste_", "bateria_"]
TEST_COLLECTION_NAMES = ["teste_collection", "teste_diagnostico", "testes", "test_", "debug_"]
TEST_DOCUMENT_IDS = ["9999999999", "None", "null", "undefined", "mock", "fake", "temp"]
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
        pass

    return firestore.client()

def is_test_collection(collection_name: str) -> bool:
    """Verificar se nome da coleção parece ser teste."""
    for prefix in TEST_COLLECTION_NAMES:
        if prefix in collection_name.lower():
            return True
    return False

def is_test_document(doc_id: str) -> bool:
    """Verificar se ID do documento parece ser teste."""
    doc_id_lower = str(doc_id).lower()

    # Verificar prefixos
    for prefix in TEST_PREFIXES:
        if doc_id_lower.startswith(prefix):
            return True

    # Verificar IDs específicos
    for test_id in TEST_DOCUMENT_IDS:
        if doc_id_lower == test_id.lower() or doc_id == test_id:
            return True

    return False

def audit_all_collections(db) -> Dict:
    """Auditar TODAS as coleções do Firestore."""
    print(f"[{TIMESTAMP}] Iniciando auditoria completa de todas as coleções...")

    audit_results = {
        "timestamp": TIMESTAMP,
        "total_test_documents": 0,
        "total_test_collections": 0,
        "collections_analyzed": 0,
        "collections_found": {},
        "execution_mode": "dry-run",
    }

    try:
        # Listar todas as coleções na raiz
        collections = db.collections()

        test_documents = {}
        test_collections = set()

        for collection in collections:
            collection_name = collection.id
            audit_results["collections_analyzed"] += 1

            print(f"  Analisando coleção: {collection_name}...", end=" ", flush=True)

            is_test_col = is_test_collection(collection_name)
            if is_test_col:
                test_collections.add(collection_name)
                audit_results["total_test_collections"] += 1
                print(f"[TESTE]", end=" ", flush=True)

            # Varrer documentos
            try:
                docs = collection.stream()
                doc_count = 0
                test_doc_count = 0

                for doc in docs:
                    doc_count += 1
                    doc_id = doc.id

                    if is_test_document(doc_id):
                        test_doc_count += 1
                        audit_results["total_test_documents"] += 1

                        key = f"{collection_name}/{doc_id}"
                        test_documents[key] = {
                            "collection": collection_name,
                            "doc_id": doc_id,
                            "created_at": doc.create_time.isoformat() if doc.create_time else "unknown",
                            "updated_at": doc.update_time.isoformat() if doc.update_time else "unknown",
                        }

                print(f"({doc_count} docs, {test_doc_count} testes)")

                if test_doc_count > 0:
                    if collection_name not in audit_results["collections_found"]:
                        audit_results["collections_found"][collection_name] = []

                    audit_results["collections_found"][collection_name].extend(
                        [test_documents[k] for k in list(test_documents.keys())[-test_doc_count:]]
                    )

            except Exception as e:
                print(f"[ERRO: {str(e)[:50]}]")
                continue

        # Adicionar resumo
        audit_results["test_collections_list"] = list(test_collections) if test_collections else []
        audit_results["sample_test_documents"] = {k: v for k, v in list(test_documents.items())[:50]}

        return audit_results

    except Exception as e:
        audit_results["error"] = str(e)
        return audit_results

def save_report(audit_data: Dict, filename: str = None):
    """Salvar relatório JSON."""
    if not filename:
        timestamp_safe = TIMESTAMP.replace(':', '-').replace('.', '_')
        filename = f"FIRESTORE_AUDIT_ALL_COLLECTIONS_{timestamp_safe}.json"

    os.makedirs(REPORT_DIR, exist_ok=True)
    filepath = os.path.join(REPORT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Relatório salvo: {filepath}")
    return filepath

def main():
    parser = argparse.ArgumentParser(
        description="Auditar TODOS os documentos de teste em Firestore"
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        default=False,
        help="OBRIGATÓRIO: Confirmar deleção real (não implementado ainda)"
    )

    args = parser.parse_args()

    print(f"NeoEve Firestore Complete Audit")
    print(f"Timestamp: {TIMESTAMP}")
    print(f"Modo: DRY-RUN")
    print("-" * 70)

    try:
        db = init_firestore()
        print("[OK] Conectado ao Firestore\n")

        # Executar auditoria
        audit_data = audit_all_collections(db)

        print("\n" + "=" * 70)
        print("RESUMO DA AUDITORIA:")
        print("=" * 70)
        print(f"Coleções analisadas: {audit_data['collections_analyzed']}")
        print(f"Coleções de TESTE encontradas: {audit_data['total_test_collections']}")
        print(f"Documentos de TESTE encontrados: {audit_data['total_test_documents']}")
        print()

        if audit_data["total_test_collections"] > 0:
            print("Coleções de teste:")
            for col in audit_data["test_collections_list"]:
                print(f"  - {col}")

        print()
        print("=" * 70)
        print(f"TOTAL A REMOVER: {audit_data['total_test_documents']} documentos")
        print("=" * 70)

        # Salvar relatório
        save_report(audit_data)

        # Exibir JSON resumido
        print("\nJSON Resumido:")
        print(json.dumps({
            "timestamp": audit_data["timestamp"],
            "collections_analyzed": audit_data["collections_analyzed"],
            "test_collections_found": audit_data["total_test_collections"],
            "total_test_documents": audit_data["total_test_documents"],
            "test_collections": audit_data["test_collections_list"],
        }, indent=2, ensure_ascii=False))

        return 0

    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
