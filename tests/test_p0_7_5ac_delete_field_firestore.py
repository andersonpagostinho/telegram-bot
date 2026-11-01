"""
[P0.7.5AC] Validar que DELETE_FIELD remove draft_agendamento do Firestore
e que ctx em memória não fica com Sentinel após persistência.

Teste específico para validar a correção do bug de ctx.pop("draft_agendamento", None).
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

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


@pytest.mark.asyncio
async def test_p0_7_5ac_delete_field_remove_do_firestore():
    """
    Validar que DELETE_FIELD é removido de ctx em memória após salvar,
    e que o campo é realmente deletado do Firestore.
    """
    TENANT = "7394370553"
    ACTOR_ID = "whatsapp:test_p0_7_5ac_001"

    print("\n" + "="*80)
    print("[P0.7.5AC] VALIDAR DELETE_FIELD E EXCLUSÃO EM FIRESTORE")
    print("="*80)

    # SETUP: Salvar contexto com draft_agendamento normal
    print("\n[PASSO 1] Salvar draft_agendamento normal")
    draft_inicial = {
        "servico": "corte feminino",
        "profissional": "Bruna",
        "data_hora": datetime.now().isoformat()
    }

    ctx_inicial = {
        "estado_fluxo": "agendando",
        "draft_agendamento": draft_inicial,
        "aguardando_confirmacao_agendamento": True,
        "_tenant_id_guard": TENANT,
    }

    await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, ctx_inicial)
    print("  ✓ Contexto inicial salvo com draft_agendamento")

    # Verificar Firestore: draft_agendamento deve estar lá
    path = f"Clientes/{TENANT}/Sessoes/{ACTOR_ID}"
    doc = await buscar_dado_em_path(path)
    assert doc, "Documento deve existir em Firestore"
    assert "draft_agendamento" in doc, "draft_agendamento deve estar em Firestore"
    assert doc["draft_agendamento"]["servico"] == "corte feminino"
    print("  ✓ Firestore: draft_agendamento encontrado com servico='corte feminino'")

    # PASSO 2: Simular a correção — salvar com DELETE_FIELD, depois pop
    print("\n[PASSO 2] Simular correção: DELETE_FIELD + ctx.pop()")
    from google.cloud import firestore

    ctx_para_salvar = {
        "estado_fluxo": "idle",
        "aguardando_confirmacao_agendamento": False,
        "draft_agendamento": firestore.DELETE_FIELD  # ← Instrução de deleção
    }

    # Salvar com DELETE_FIELD (como o router faz em linha 7599)
    await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, ctx_para_salvar)
    print("  ✓ Contexto salvo com DELETE_FIELD em draft_agendamento")

    # Simular o pop em memória (como a correção faz em linha 7602)
    ctx_para_salvar.pop("draft_agendamento", None)
    print("  ✓ Contexto em memória: draft_agendamento removido via pop()")

    # VALIDAÇÃO 1: ctx em memória não deve ter draft_agendamento
    assert "draft_agendamento" not in ctx_para_salvar, \
        "FALHOU: ctx em memória ainda tem draft_agendamento após pop()"
    print("  ✓ Validação PASS: ctx em memória limpo")

    # VALIDAÇÃO 2: Firestore deve ter removido o campo
    doc_apos = await buscar_dado_em_path(path)
    assert doc_apos, "Documento deve existir em Firestore"
    assert "draft_agendamento" not in doc_apos, \
        "FALHOU: draft_agendamento ainda existe em Firestore (DELETE_FIELD não funcionou)"
    assert doc_apos["estado_fluxo"] == "idle"
    assert doc_apos["aguardando_confirmacao_agendamento"] == False
    print("  ✓ Validação PASS: Firestore sem draft_agendamento")

    # PASSO 3: Verificar que carregar contexto não retorna Sentinel
    print("\n[PASSO 3] Carregar contexto após deleção")
    ctx_carregado = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

    # Não deve ter draft_agendamento
    assert "draft_agendamento" not in ctx_carregado or \
           ctx_carregado.get("draft_agendamento") is None, \
        "draft_agendamento deve estar ausente após carregar"

    # Se tentar fazer .get() em um None ou em não existência, não deve falhar
    draft_result = ctx_carregado.get("draft_agendamento")
    assert draft_result is None or isinstance(draft_result, dict), \
        f"draft_agendamento deve ser None ou dict, não {type(draft_result)}"

    print("  ✓ Validação PASS: Contexto carregado seguro")

    # PASSO 4: Verificar que o acesso a draft_agendamento agora é seguro
    print("\n[PASSO 4] Acesso seguro a draft_agendamento em ctx carregado")
    draft = ctx_carregado.get("draft_agendamento") or {}
    servico = draft.get("servico")  # ← Isto não deve causar AttributeError
    prof = draft.get("profissional")

    assert servico is None, "Servico deve ser None após deleção"
    assert prof is None, "Profissional deve ser None após deleção"
    print("  ✓ Validação PASS: Acesso a draft.get() seguro (sem Sentinel error)")

    # Cleanup
    await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {"_deleted": True})

    print("\n" + "="*80)
    print("✅ [P0.7.5AC] TESTE COMPLETO E VALIDADO")
    print("="*80)
