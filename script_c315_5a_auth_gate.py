#!/usr/bin/env python3
"""
C3.15.5-A — PRÉ-GATE DE AUTENTICAÇÃO
=====================================

Objetivo: Validar que o ambiente consegue autenticar no Firebase/Firestore
usando credenciais já existentes no projeto.

Comportamento:
✅ Valida mecanismo de credencial existente
✅ Inicializa cliente Firebase/Firestore
✅ Executa operação READ-ONLY (sem acessar dados de clientes)
✅ Relata somente: AUTH/FIRESTORE status + PROJECT_ID

Restrições (OBRIGATÓRIAS):
❌ Não altera arquivo de produção
❌ Não executa escrita no Firestore
❌ Não imprime token, private_key, client_secret
"""

import os
import sys
import json
import base64
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("C3.15.5-A — PRÉ-GATE DE AUTENTICAÇÃO")
    print("="*70 + "\n")

    # ✅ PASSO 1: Identificar mecanismo de credencial
    print("[PASSO 1] 🔍 Identificar mecanismo de credencial existente...")

    cred_mechanism = None
    cred_source = None
    cred_obj = None
    project_id = None

    # Tentativa 1: FIREBASE_CREDENTIALS_B64 (Base64)
    print("  → Verificando: FIREBASE_CREDENTIALS_B64")
    firebase_creds_b64 = os.getenv("FIREBASE_CREDENTIALS_B64")
    if firebase_creds_b64:
        try:
            decoded = base64.b64decode(firebase_creds_b64).decode('utf-8')
            cred_obj = json.loads(decoded)
            cred_mechanism = "FIREBASE_CREDENTIALS_B64"
            cred_source = "environment variable (Base64-encoded)"
            project_id = cred_obj.get("project_id")
            print(f"    ✅ Encontrado: Base64-encoded JSON")
        except Exception as e:
            print(f"    ❌ Falha ao decodificar Base64: {str(e)[:80]}")

    # Tentativa 2: FIREBASE_CREDENTIALS (JSON string ou caminho)
    if not cred_mechanism:
        print("  → Verificando: FIREBASE_CREDENTIALS")
        firebase_creds_str = os.getenv("FIREBASE_CREDENTIALS")
        if firebase_creds_str:
            try:
                cred_obj = json.loads(firebase_creds_str)
                cred_mechanism = "FIREBASE_CREDENTIALS"
                cred_source = "environment variable (JSON string)"
                project_id = cred_obj.get("project_id")
                print(f"    ✅ Encontrado: JSON string")
            except:
                # Pode ser um caminho
                if os.path.exists(firebase_creds_str):
                    try:
                        with open(firebase_creds_str, 'r') as f:
                            cred_obj = json.load(f)
                        cred_mechanism = "FIREBASE_CREDENTIALS"
                        cred_source = f"file path: {firebase_creds_str}"
                        project_id = cred_obj.get("project_id")
                        print(f"    ✅ Encontrado: Caminho para arquivo JSON")
                    except Exception as e:
                        print(f"    ❌ Erro ao ler arquivo: {str(e)[:80]}")

    # Tentativa 3: Arquivo JSON local
    if not cred_mechanism:
        print("  → Verificando: Arquivos JSON locais no diretório")
        local_paths = [
            "firebase_credentials.json",
            "agendabot-450219-e39469ceff37.json",
            "firebaseConfig.json",
        ]

        for local_file in local_paths:
            if os.path.exists(local_file):
                try:
                    with open(local_file, 'r') as f:
                        cred_obj = json.load(f)
                    cred_mechanism = "LOCAL_JSON_FILE"
                    cred_source = f"file: {local_file}"
                    project_id = cred_obj.get("project_id")
                    print(f"    ✅ Encontrado: {local_file}")
                    break
                except Exception as e:
                    print(f"    ❌ Erro ao ler {local_file}: {str(e)[:80]}")

    # Status do PASSO 1
    if cred_mechanism:
        print(f"\n✅ CREDENCIAL ENCONTRADA")
        print(f"   Mecanismo: {cred_mechanism}")
        print(f"   Fonte: {cred_source}")
        print(f"   Project ID: {project_id}\n")
    else:
        print(f"\n❌ NENHUMA CREDENCIAL ENCONTRADA")
        print(f"   Variáveis de ambiente verificadas:")
        print(f"   - FIREBASE_CREDENTIALS_B64: {'definida' if os.getenv('FIREBASE_CREDENTIALS_B64') else 'não definida'}")
        print(f"   - FIREBASE_CREDENTIALS: {'definida' if os.getenv('FIREBASE_CREDENTIALS') else 'não definida'}")
        print(f"\n   Arquivos locais verificados:")
        for local_file in ["firebase_credentials.json", "agendabot-450219-e39469ceff37.json", "firebaseConfig.json"]:
            exists = "✓" if os.path.exists(local_file) else "✗"
            print(f"   [{exists}] {local_file}")

        print("\n❌ AUTH: FAIL")
        print("Causa: Nenhum mecanismo de credencial disponível")
        return False

    # ✅ PASSO 2: Validar credencial JSON
    print("[PASSO 2] 🔍 Validar estrutura da credencial...")

    required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
    missing = [f for f in required_fields if f not in cred_obj]

    if missing:
        print(f"   ❌ Campos obrigatórios faltando: {missing}")
        print(f"\n❌ AUTH: FAIL")
        print(f"Causa: Credencial JSON incompleta (faltam: {', '.join(missing)})")
        return False

    print(f"   ✅ Estrutura válida")
    print(f"   Type: {cred_obj.get('type')}")
    print(f"   Client email: {cred_obj.get('client_email', 'N/A')}\n")

    # ✅ PASSO 3: Inicializar Firebase
    print("[PASSO 3] 🔥 Inicializar Firebase Admin SDK...")

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Verificar se já está inicializado
        try:
            firebase_admin.get_app()
            print("   ⚠️  Firebase já estava inicializado (reutilizando)")
        except ValueError:
            # Não inicializado, fazer isso agora
            # Criar credencial usando o objeto JSON
            if cred_mechanism == "FIREBASE_CREDENTIALS_B64":
                # Salvar temporariamente em arquivo
                temp_creds_path = "/tmp/firebase_creds_temp.json"
                with open(temp_creds_path, 'w') as f:
                    json.dump(cred_obj, f)
                cred = credentials.Certificate(temp_creds_path)
            else:
                cred = credentials.Certificate(cred_obj)

            firebase_admin.initialize_app(cred)
            print("   ✅ Firebase Admin SDK inicializado")

        # Obter cliente Firestore
        db = firestore.client()
        print("   ✅ Cliente Firestore obtido\n")

    except ImportError as e:
        print(f"   ❌ Importação falhou: {str(e)[:100]}")
        print(f"\n❌ FIRESTORE CLIENT: FAIL")
        print(f"Causa: Bibliotecas Firebase não disponíveis")
        return False
    except Exception as e:
        print(f"   ❌ Erro ao inicializar: {str(e)[:100]}")
        print(f"\n❌ AUTH: FAIL")
        print(f"Causa: {str(e)[:200]}")
        return False

    # ✅ PASSO 4: Teste de conectividade READ-ONLY
    print("[PASSO 4] 📖 Teste de conectividade (READ-ONLY)...")

    try:
        # Fazer uma leitura sem acessar dados de clientes
        # Esta operação é READ-ONLY e não vai salvar nada

        # Tentar listar documentos de uma coleção (operação segura)
        test_collection_ref = db.collection("_connectivity_test")
        test_docs = test_collection_ref.limit(1).stream()

        # Consumir o iterador para validar a conexão
        count = 0
        for doc in test_docs:
            count += 1

        print(f"   ✅ Leitura bem-sucedida (conexão validada)")
        print(f"   ✅ Firestore acessível\n")

    except Exception as e:
        error_msg = str(e)[:150]
        print(f"   ❌ Erro na leitura: {error_msg}")
        print(f"\n❌ FIRESTORE CLIENT: FAIL")
        print(f"Causa: {error_msg}")
        return False

    # ✅ RESULTADO FINAL
    print("="*70)
    print("✅ C3.15.5-A AUTH GATE — RESULTADO\n")
    print(f"AUTH: PASS")
    print(f"FIRESTORE CLIENT: PASS")
    print(f"PROJECT_ID: {project_id}")
    print(f"WRITES EXECUTADAS: 0")
    print(f"\nMecanismo: {cred_mechanism}")
    print(f"Fonte: {cred_source}")
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
