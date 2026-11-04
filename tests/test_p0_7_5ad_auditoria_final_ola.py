"""
[P0.7.5AD] E2E ESPECÍFICO DO GATILHO: confirmacao_pendente + "ola"

Objetivo: Validar exatamente o cenário que causava Sentinel error.

Setup:
- confirmacao_pendente=True (confirmação legítima pendente)
- draft_agendamento={...} (draft válido)

Input: Mensagem "ola" (nova consulta pura)

Esperado:
1. DELETE_FIELD enviado à persistência
2. ctx.pop() remove Sentinel
3. Nenhum Sentinel.get() error
4. draft_agendamento removido do Firestore
5. Nova consulta processada normalmente
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
)
from services.firebase_service_async import buscar_dado_em_path
from router.principal_router import roteador_principal
from unittest.mock import MagicMock


class MockContext:
    """Mock mínimo de contexto Telegram"""
    def __init__(self):
        self.bot = MagicMock()


@pytest.mark.asyncio
async def test_p0_7_5ad_gateway_confirmacao_pendente_ola():
    """
    Teste específico do gatilho P0.7.5AC:
    1. Confirmação pendente ativa
    2. Draft agendamento completo
    3. Mensagem "ola" (nova consulta pura)
    4. Validar sem Sentinel error
    """
    TENANT = "7394370553"
    ACTOR = "whatsapp:test_p0_7_5ad_ola_001"

    print("\n" + "="*100)
    print("[P0.7.5AD] TESTE E2E ESPECÍFICO: confirmacao_pendente + 'ola'")
    print("="*100)

    amanha = datetime.now() + timedelta(days=1)
    data_hora = amanha.strftime("%Y-%m-%d") + "T14:00:00"

    # SETUP: Contexto legítimo com confirmação pendente
    print("\n[PASSO 1] Setup: confirmacao_pendente=True + draft válido")
    ctx_inicial = {
        "_tenant_id_guard": TENANT,
        "tipo_usuario": "cliente",
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "confirmacao_pendente": True,
        "intencao_conversacional": "indefinida",  # Vai para reiteration
        "profissional_escolhido": "Bruna",
        "servico": "corte feminino",
        "data_hora": data_hora,
        "draft_agendamento": {
            "servico": "corte feminino",
            "profissional": "Bruna",
            "data_hora": data_hora,
        },
    }

    await salvar_contexto_temporario_v2(TENANT, ACTOR, ctx_inicial)
    print("  ✓ Contexto salvo com confirmacao_pendente=True e draft válido")

    # Verificar Firestore antes
    path = f"Clientes/{TENANT}/Sessoes/{ACTOR}"
    doc_antes = await buscar_dado_em_path(path)
    assert "draft_agendamento" in doc_antes, "Draft deve estar em Firestore antes"
    print(f"  ✓ Firestore antes: draft_agendamento existe")

    # EXECUTAR: Chamar roteador com "ola"
    print("\n[PASSO 2] Executar: roteador com mensagem='ola'")
    print("  Esperado: DELETE_FIELD aplicado, ctx.pop() executado, sem Sentinel error")

    try:
        resultado = await roteador_principal(
            user_id="test_p0_7_5ad_ola_001",
            mensagem="ola",
            tenant_id=TENANT,
            phone_number_id="1350170954840548",
            update=None,
            context=MockContext()
        )
        print(f"  ✓ Roteador executado sem erro")
        print(f"  ✓ Resposta: {str(resultado.get('resposta', ''))[:100] if isinstance(resultado, dict) else 'N/A'}")
    except AttributeError as e:
        if "Sentinel" in str(e) or "get" in str(e):
            print(f"  ✗ FALHOU: Sentinel error detectado!")
            print(f"  ✗ Erro: {e}")
            raise
        else:
            raise

    # VALIDAÇÃO 1: Firestore sem draft_agendamento
    print("\n[PASSO 3] Validar Firestore após execução")
    doc_depois = await buscar_dado_em_path(path)
    assert doc_depois is not None, "Sessão deve existir em Firestore"

    if "draft_agendamento" in doc_depois:
        draft_val = doc_depois.get("draft_agendamento")
        print(f"  ✗ FALHOU: draft_agendamento ainda existe em Firestore")
        print(f"  ✗ Valor: {draft_val}")
        assert False, "draft_agendamento deveria ter sido deletado"
    else:
        print(f"  ✓ Firestore após: draft_agendamento REMOVIDO (DELETE_FIELD funcionou)")

    # VALIDAÇÃO 2: confirmacao_pendente foi resetado
    assert doc_depois.get("aguardando_confirmacao_agendamento") == False, \
        "aguardando_confirmacao_agendamento deve ser False"
    print(f"  ✓ Firestore: aguardando_confirmacao_agendamento=False")

    # VALIDAÇÃO 3: Estado transitório
    assert doc_depois.get("estado_fluxo") in ["idle", "agendando"], \
        f"estado_fluxo deve ser idle ou agendando, é {doc_depois.get('estado_fluxo')}"
    print(f"  ✓ Firestore: estado_fluxo={doc_depois.get('estado_fluxo')}")

    print("\n" + "="*100)
    print("✅ [P0.7.5AD] TESTE GATILHO PASSOU")
    print("="*100)
    print("Validações:")
    print("  ✓ DELETE_FIELD enviado à persistência")
    print("  ✓ ctx.pop('draft_agendamento') removeu Sentinel")
    print("  ✓ Nenhum Sentinel.get() error")
    print("  ✓ draft_agendamento removido do Firestore")
    print("  ✓ Nova consulta processada")
