#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.whatsapp_endpoint_service import registrar_endpoint_whatsapp, resolver_tenant_por_endpoint
from services.firestore_client import get_db

def registrar_e_validar():
    print("\n" + "=" * 80)
    print("GATE C3.15.3 - REGISTRAR E VALIDAR ENDPOINT")
    print("=" * 80)
    print("Timestamp: " + datetime.now().isoformat())
    print()

    # Parametros fornecidos
    phone_number_id = "1350170954840548"
    tenant_id = "7394370553"
    display_phone_number = "+55 19 99444-3694"
    waba_id = "1630189518519404"

    print("[PARAMETROS]")
    print("  phone_number_id: " + phone_number_id)
    print("  tenant_id: " + tenant_id)
    print("  display_phone_number: " + display_phone_number)
    print("  waba_id: " + waba_id)
    print()

    # 1. Registrar endpoint
    print("[1] REGISTRAR ENDPOINT")
    print("-" * 80)

    resultado_registro = registrar_endpoint_whatsapp(
        phone_number_id=phone_number_id,
        tenant_id=tenant_id,
        display_phone_number=display_phone_number,
        waba_id=waba_id,
    )

    print("Resultado:")
    print(json.dumps(resultado_registro, indent=2, ensure_ascii=False))
    print()

    if not resultado_registro.get("ok"):
        print("[ERRO] Falha ao registrar endpoint")
        print()
        return False

    print("[OK] Endpoint registrado com sucesso")
    print()

    # 2. Validar com resolver_tenant_por_endpoint
    print("[2] VALIDAR RESOLVIMENTO DO TENANT")
    print("-" * 80)

    tenant_resolvido = resolver_tenant_por_endpoint(phone_number_id)

    print("Resultado: " + str(tenant_resolvido))
    print()

    if tenant_resolvido == tenant_id:
        print("[OK] Tenant resolvido corretamente (" + str(tenant_resolvido) + ")")
    elif tenant_resolvido == "7394370553":
        print("[OK] Retornou 7394370553 (conforme esperado)")
    else:
        print("[ERRO] Tenant resolvido incorretamente")
        print("  Esperado: " + str(tenant_id))
        print("  Obtido: " + str(tenant_resolvido))
        return False

    print()

    # 3. Verificar no Firestore
    print("[3] VERIFICAR DOCUMENTO NO FIRESTORE")
    print("-" * 80)

    db = get_db()
    doc_ref = db.collection("WhatsAppEndpoints").document(phone_number_id)
    doc_snapshot = doc_ref.get()

    if not doc_snapshot.exists:
        print("[ERRO] Documento NAO encontrado no Firestore")
        return False

    print("[OK] Documento encontrado")
    print()

    doc_data = doc_snapshot.to_dict()

    # Validar campos
    validacoes = {
        "tenant_id": (doc_data.get("tenant_id"), tenant_id),
        "status": (doc_data.get("status"), "ativo"),
        "validado": (doc_data.get("validado"), True),
        "phone_number_id": (doc_data.get("phone_number_id"), phone_number_id),
        "display_phone_number": (doc_data.get("display_phone_number"), display_phone_number),
        "waba_id": (doc_data.get("waba_id"), waba_id),
    }

    print("[VALIDACOES]")
    todos_ok = True
    for campo, (valor_obtido, valor_esperado) in validacoes.items():
        ok = valor_obtido == valor_esperado
        status = "[OK]" if ok else "[ERRO]"
        print("{} {}".format(status, campo))
        print("    Esperado: {}".format(repr(valor_esperado)))
        print("    Obtido: {}".format(repr(valor_obtido)))
        if not ok:
            todos_ok = False

    print()

    # 4. Resumo final
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print()

    if todos_ok and tenant_resolvido == tenant_id:
        print("[OK] TODAS AS VALIDACOES PASSARAM")
        print()
        print("Documento criado:")
        print(json.dumps(doc_data, indent=2, ensure_ascii=False))
        print()
        return True
    else:
        print("[ERRO] VALIDACOES FALHARAM")
        return False

if __name__ == "__main__":
    try:
        sucesso = registrar_e_validar()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print("\n[ERRO FATAL] " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
