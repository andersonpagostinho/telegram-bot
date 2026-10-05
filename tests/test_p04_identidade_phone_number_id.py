#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0.4 — Teste: phone_number_id preservado em IdentidadeContexto
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.identidade_contexto import IdentidadeContexto, criar_identidade_whatsapp


def test_identidade_contexto_tem_phone_number_id():
    """Validar que IdentidadeContexto aceita phone_number_id"""

    print("\n[TEST] IdentidadeContexto com phone_number_id")

    identidade = IdentidadeContexto(
        user_id="5511991382080",
        tenant_id="7394370553",
        actor_id="whatsapp:5511991382080",
        canal="whatsapp",
        phone_number_id="1350170954840548"
    )

    assert identidade.phone_number_id == "1350170954840548", "phone_number_id nao preservado"
    print(f"  [OK] phone_number_id armazenado: {identidade.phone_number_id}")


def test_criar_identidade_whatsapp_preserva_phone_number_id():
    """Validar que criar_identidade_whatsapp() preserva phone_number_id"""

    print("\n[TEST] criar_identidade_whatsapp() preserva phone_number_id")

    wa_id = "5511991382080"
    phone_number_id = "1350170954840548"
    tenant_id = "7394370553"

    identidade = criar_identidade_whatsapp(wa_id, phone_number_id, tenant_id)

    assert identidade.user_id == wa_id, "user_id incorreto"
    assert identidade.tenant_id == tenant_id, "tenant_id incorreto"
    assert identidade.canal == "whatsapp", "canal incorreto"
    assert identidade.phone_number_id == phone_number_id, f"phone_number_id nao preservado. Recebido: {identidade.phone_number_id}"

    print(f"  [OK] user_id: {identidade.user_id}")
    print(f"  [OK] tenant_id: {identidade.tenant_id}")
    print(f"  [OK] actor_id: {identidade.actor_id}")
    print(f"  [OK] canal: {identidade.canal}")
    print(f"  [OK] phone_number_id: {identidade.phone_number_id}")


def test_identidade_default_phone_number_id_none():
    """Validar compatibilidade backward com phone_number_id=None"""

    print("\n[TEST] phone_number_id default=None para Telegram")

    identidade = IdentidadeContexto(
        user_id="123456789",
        tenant_id="tenant_123",
        actor_id="tg:123456789",
        canal="telegram"
    )

    assert identidade.phone_number_id is None, "phone_number_id deve ser None por default"
    print(f"  [OK] phone_number_id default: None (compativel Telegram)")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("[TESTES P0.4] IdentidadeContexto e phone_number_id")
    print("="*80)

    try:
        test_identidade_contexto_tem_phone_number_id()
        test_criar_identidade_whatsapp_preserva_phone_number_id()
        test_identidade_default_phone_number_id_none()

        print("\n" + "="*80)
        print("[RESULTADO] TODOS OS TESTES PASSARAM")
        print("="*80)
    except AssertionError as e:
        print(f"\n[ERRO] TESTE FALHOU: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
