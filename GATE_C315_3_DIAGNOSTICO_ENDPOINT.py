#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Forcar UTF-8 no Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.firebase_config import firebase_admin, firestore

def diagnosticar_endpoint():
    print("\n" + "=" * 80)
    print("GATE C3.15.3-C - DIAGNOSTICO DO ENDPOINT")
    print("=" * 80)
    print("Timestamp: " + datetime.now().isoformat())
    print()

    db = firestore.client()

    # 1. Verificar documento
    print("[1] Verificar documento WhatsAppEndpoints/1350170954840548")
    print("-" * 80)

    doc_ref = db.collection("WhatsAppEndpoints").document("1350170954840548")
    doc_snapshot = doc_ref.get()

    if not doc_snapshot.exists:
        print("[RESULTADO] DOCUMENTO NAO EXISTE no Firestore")
        print("\nAbortando.\n")
        return False

    print("[RESULTADO] Documento EXISTE no Firestore")
    print()

    # 2. Coletar dados
    print("[2] Coletar dados do documento")
    print("-" * 80)

    doc_data = doc_snapshot.to_dict()

    campos = ["tenant_id", "status", "validado", "display_phone_number", "waba_id"]

    for campo in campos:
        valor = doc_data.get(campo, "[NAO ENCONTRADO]")
        print("{:.<30} {}".format(campo, repr(valor)))

    print()
    print("[DOCUMENTO COMPLETO]")
    print("-" * 80)
    print(json.dumps(doc_data, indent=2, ensure_ascii=False))
    print()

    # 3. Projeto Firebase
    print("[3] Projeto Firebase")
    print("-" * 80)

    app = firebase_admin.get_app()
    credentials = app.credentials.get_credential()

    if hasattr(credentials, 'project_id'):
        project_id = credentials.project_id
    else:
        try:
            firebase_json_str = os.getenv("FIREBASE_CREDENTIALS")
            if firebase_json_str:
                firebase_json = json.loads(firebase_json_str)
                project_id = firebase_json.get("project_id", "[DESCONHECIDO]")
            else:
                project_id = "[DESCONHECIDO]"
        except:
            project_id = "[DESCONHECIDO]"

    print("Projeto: " + str(project_id))
    print()

    # 4. Testar funcao resolve_tenant_por_endpoint
    print("[4] Testar resolve_tenant_por_endpoint('1350170954840548')")
    print("-" * 80)

    try:
        from services.whatsapp_service import resolve_tenant_por_endpoint

        tenant_id_resolvido = resolve_tenant_por_endpoint("1350170954840548")

        print("Resultado: " + str(tenant_id_resolvido))

        tenant_no_doc = doc_data.get("tenant_id")
        if tenant_id_resolvido == 7394370553:
            print("[OK] Retornou 7394370553 (conforme esperado)")
        elif tenant_id_resolvido == tenant_no_doc:
            print("[AVISO] Retornou {} (diferente de 7394370553, mas == ao doc)".format(tenant_id_resolvido))
        else:
            print("[ERRO] Retornou {} (NAO CORRESPONDE ao esperado 7394370553)".format(tenant_id_resolvido))

        print()

    except ImportError as e:
        print("[ERRO] Erro ao importar: " + str(e))
        print()
    except Exception as e:
        print("[ERRO] Erro ao executar: " + str(e))
        import traceback
        traceback.print_exc()
        print()

    # 5. Resumo
    print("=" * 80)
    print("RESUMO DIAGNOSTICO")
    print("=" * 80)
    print()
    print("Documento existe: SIM")
    print("Projeto Firebase: " + str(project_id))
    print("tenant_id: " + str(doc_data.get('tenant_id', '[NAO ENCONTRADO]')))
    print("status: " + str(doc_data.get('status', '[NAO ENCONTRADO]')))
    print("validado: " + str(doc_data.get('validado', '[NAO ENCONTRADO]')))
    print("display_phone_number: " + str(doc_data.get('display_phone_number', '[NAO ENCONTRADO]')))
    print("waba_id: " + str(doc_data.get('waba_id', '[NAO ENCONTRADO]')))
    print()
    print("=" * 80)
    print()

    return True

if __name__ == "__main__":
    try:
        sucesso = diagnosticar_endpoint()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print("\n[ERRO FATAL] " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
