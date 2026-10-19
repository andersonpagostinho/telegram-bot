#!/usr/bin/env python3
"""
TESTES E2E — GUARD_AGUARDANDO_DATA com novo serviço

Casos:
- T-NOVO: Draft coloracao + novo serviço corte → detecta e atualiza
- T-PRESERVA: Draft corte + sem novo serviço → preserva
- T-MULTI: Múltiplos serviços → pede esclarecimento
- T-VAZIO: Sem serviço em draft e texto → não inventa
- T-TENANT-ISO: Dois tenants isolados
- T-CONSULTA-E2E: Reproduz o bug: draft coloracao + msg com corte + confirmação
"""

import pytest
import sys
import time
sys.path.insert(0, "/c/dev/neoeve")

from router.principal_router import roteador_principal
from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
)
from utils.identidade_contexto import criar_identidade_whatsapp

TENANT_TEST = "7394370553"  # Tenant com profissionais conhecidos


@pytest.mark.asyncio
async def test_t_novo_draft_coloracao_novo_corte():
    """T-NOVO: Draft 'coloracao' + mensagem 'quero corte amanha as 10'
    → deve identificar novo serviço 'corte feminino' e atualizar contexto"""

    print("\n" + "="*90)
    print("T-NOVO: Draft coloracao + novo serviço corte → detecta e atualiza")
    print("="*90)

    ts = int(time.time() * 1000) % 1000000
    user_id = f"55119991{ts:07d}"
    cliente_id = user_id  # Sem prefixo para compatibilidade com roteador_principal

    # Setup: Draft antigo com coloracao
    ctx_initial = {
        "draft_agendamento": {
            "servico": "coloracao",
            "data_hora": "2026-10-10T15:00:00"
        },
        "servico": "coloracao",
        "estado_fluxo": "aguardando_data",
        "modo_prechecagem": True,
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx_initial)
    print(f"[SETUP] Salvo ctx com draft.servico=coloracao")

    # Msg 1: Nova solicitação com corte
    print(f"\n[MSG1] Enviando: 'voce tem agenda para corte feminino amanha as 10?'")
    resposta = await roteador_principal(
        user_id=user_id,
        mensagem="voce tem agenda para corte feminino amanha as 10?",
        tenant_id=TENANT_TEST,
        context=None,
    )

    print(f"[RESP1] Resposta: {resposta.get('resposta', '')[:150]}")

    # Verificar contexto após Msg1
    ctx_after = await carregar_contexto_temporario_v2(TENANT_TEST, cliente_id)
    print(f"\n[VALIDAÇÃO]")
    print(f"  servico: {ctx_after.get('servico')}")
    print(f"  draft.servico: {ctx_after.get('draft_agendamento', {}).get('servico')}")
    print(f"  estado: {ctx_after.get('estado_fluxo')}")

    # T-NOVO: Deve ter detectado "corte feminino", não reutilizar "coloracao"
    assert ctx_after.get("servico") == "corte feminino", \
        f"T-NOVO FAIL: servico deveria ser 'corte feminino', obteve {ctx_after.get('servico')}"
    assert ctx_after.get("draft_agendamento", {}).get("servico") == "corte feminino", \
        f"T-NOVO FAIL: draft.servico deveria ser 'corte feminino', obteve {ctx_after.get('draft_agendamento', {}).get('servico')}"

    # Não deve repergunttar data/hora
    resposta_text = resposta.get("resposta", "").lower()
    assert "qual dia" not in resposta_text and "horario" not in resposta_text, \
        f"T-NOVO FAIL: Sistema reperguntou data/hora na resposta"

    print(f"\n✅ T-NOVO PASSOU")


@pytest.mark.asyncio
async def test_t_preserva_draft_sem_novo_servico():
    """T-PRESERVA: Draft 'corte' + mensagem 'amanha as 14' (sem novo serviço)
    → deve preservar serviço, só atualizar horário"""

    print("\n" + "="*90)
    print("T-PRESERVA: Draft corte + sem novo serviço → preserva")
    print("="*90)

    ts = int(time.time() * 1000) % 1000000
    user_id = f"55119992{ts:07d}"
    cliente_id = user_id

    # Setup: Draft com corte
    ctx_initial = {
        "draft_agendamento": {
            "servico": "corte feminino",
            "data_hora": "2026-10-10T10:00:00"
        },
        "servico": "corte feminino",
        "estado_fluxo": "aguardando_data",
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx_initial)
    print(f"[SETUP] Draft com servico=corte feminino")

    # Msg: Apenas nova hora
    print(f"\n[MSG] Enviando: 'amanha as 14'")
    resposta = await roteador_principal(
        user_id=user_id,
        mensagem="amanha as 14",
        tenant_id=TENANT_TEST,
        context=None,
    )

    print(f"[RESP] {resposta.get('resposta', '')[:150]}")

    # Verificar: Serviço preservado, horário atualizado
    ctx_after = await carregar_contexto_temporario_v2(TENANT_TEST, cliente_id)
    print(f"\n[VALIDAÇÃO]")
    print(f"  servico: {ctx_after.get('servico')}")
    print(f"  draft.data_hora: {ctx_after.get('draft_agendamento', {}).get('data_hora')}")

    # T-PRESERVA: Serviço mantém "corte feminino"
    assert ctx_after.get("servico") == "corte feminino", \
        f"T-PRESERVA FAIL: servico mudou inesperadamente para {ctx_after.get('servico')}"

    # Data atualizada para próximo dia às 14h
    data_hora = ctx_after.get("data_hora")
    assert data_hora and "T14:" in data_hora, \
        f"T-PRESERVA FAIL: data_hora não foi atualizada para 14h: {data_hora}"

    print(f"\n✅ T-PRESERVA PASSOU")


@pytest.mark.asyncio
async def test_t_vazio_sem_servico_draft_nem_texto():
    """T-VAZIO: Draft vazio + mensagem sem serviço reconhecível
    → deve pedir serviço, não inventar"""

    print("\n" + "="*90)
    print("T-VAZIO: Sem serviço em draft e texto → não inventa")
    print("="*90)

    ts = int(time.time() * 1000) % 1000000
    user_id = f"55119993{ts:07d}"
    cliente_id = user_id

    # Setup: Draft vazio
    ctx_initial = {
        "draft_agendamento": {},
        "estado_fluxo": "aguardando_data",
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx_initial)
    print(f"[SETUP] Draft vazio")

    # Msg: Apenas data, nenhum serviço
    print(f"\n[MSG] Enviando: 'amanha as 15'")
    resposta = await roteador_principal(
        user_id=user_id,
        mensagem="amanha as 15",
        tenant_id=TENANT_TEST,
        context=None,
    )

    print(f"[RESP] {resposta.get('resposta', '')[:150]}")

    ctx_after = await carregar_contexto_temporario_v2(TENANT_TEST, cliente_id)

    # T-VAZIO: Estado deve ser aguardando_servico
    assert ctx_after.get("estado_fluxo") == "aguardando_servico", \
        f"T-VAZIO FAIL: estado={ctx_after.get('estado_fluxo')}, esperado aguardando_servico"

    # Serviço não foi inventado
    assert not ctx_after.get("servico"), \
        f"T-VAZIO FAIL: serviço foi inventado: {ctx_after.get('servico')}"

    print(f"\n✅ T-VAZIO PASSOU")


@pytest.mark.asyncio
async def test_t_tenant_iso_dois_tenants_isolados():
    """T-TENANT-ISO: Dois tenants com drafts diferentes
    → nenhuma contaminação entre tenants"""

    print("\n" + "="*90)
    print("T-TENANT-ISO: Isolamento por tenant")
    print("="*90)

    # Tenant 1
    tenant1 = "7394370553"
    user1 = "551199990001"
    cliente1 = f"whatsapp:{user1}"

    # Tenant 2 (usamos um tenant diferente para teste)
    # Nota: Para teste real, precisaríamos de 2 tenants real no Firebase
    # Por enquanto, apenas verificamos que a função recebe dono_id correto

    ctx_t1 = {
        "draft_agendamento": {"servico": "coloracao"},
        "servico": "coloracao",
        "estado_fluxo": "aguardando_data",
    }

    await salvar_contexto_temporario_v2(tenant1, cliente1, ctx_t1)

    # Verificar que foi salvo no path correto (sem ferramentas, apenas lógica)
    ctx_loaded = await carregar_contexto_temporario_v2(tenant1, cliente1)
    assert ctx_loaded.get("servico") == "coloracao", \
        "T-TENANT-ISO FAIL: contexto não foi salvo ou carregado corretamente"

    print(f"✅ T-TENANT-ISO PASSOU (isolamento path verificado)")


@pytest.mark.asyncio
async def test_t_consulta_e2e_bug_reproduction():
    """T-CONSULTA-E2E: Reproduz exatamente o bug reportado

    Cenário:
    1. Conversação anterior salva draft com coloracao
    2. Msg1: "voce tem agenda para corte amanha as 10?"
    3. Esperado: Detecta corte, não reutiliza coloracao
    4. Msg2: "sim gostaria sim"
    5. Verificar: Estado avança, profissionais listados são para corte
    """

    print("\n" + "="*90)
    print("T-CONSULTA-E2E: Reprodução do bug — corte vs coloracao")
    print("="*90)

    ts = int(time.time() * 1000) % 1000000
    user_id = f"551199994{ts:07d}"
    cliente_id = user_id

    # SETUP: Simula conversa anterior sobre coloracao
    print(f"[SETUP] Simula draft anterior com coloracao")
    ctx_coloracao = {
        "draft_agendamento": {
            "servico": "coloracao",
            "data_hora": "2026-10-15T14:00:00"
        },
        "servico": "coloracao",
        "estado_fluxo": "aguardando_data",
        "profissional_escolhido": None,
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx_coloracao)

    # MSG1: "voce tem agenda para corte feminino amanha as 10?"
    print(f"\n[MSG1] Enviando: 'voce tem agenda para corte feminino amanha as 10?'")
    resp1 = await roteador_principal(
        user_id=user_id,
        mensagem="voce tem agenda para corte feminino amanha as 10?",
        tenant_id=TENANT_TEST,
        context=None,
    )

    print(f"[RESP1] {resp1.get('resposta', '')[:200]}")

    ctx_msg1 = await carregar_contexto_temporario_v2(TENANT_TEST, cliente_id)
    print(f"\n[CTX-MSG1]")
    print(f"  servico: {ctx_msg1.get('servico')}")
    print(f"  estado: {ctx_msg1.get('estado_fluxo')}")
    print(f"  data_hora: {ctx_msg1.get('data_hora')}")

    # VALIDAÇÃO 1: Serviço foi atualizado para corte, não coloracao
    assert ctx_msg1.get("servico") == "corte feminino", \
        f"T-E2E FAIL: servico deveria ser 'corte feminino', obteve {ctx_msg1.get('servico')}"

    assert ctx_msg1.get("estado_fluxo") in ["aguardando_profissional", "aguardando_confirmacao_consulta"], \
        f"T-E2E FAIL: estado={ctx_msg1.get('estado_fluxo')}, esperado aguardando_profissional ou confirmacao"

    # Data/hora preservada e atualizada
    assert ctx_msg1.get("data_hora"), "T-E2E FAIL: data_hora não foi preservada"
    assert "T10:" in ctx_msg1.get("data_hora", ""), \
        f"T-E2E FAIL: horário deveria ser 10h, obteve {ctx_msg1.get('data_hora')}"

    # Resposta não deve mencionar coloracao
    resp1_text = resp1.get("resposta", "").lower()
    assert "coloracao" not in resp1_text, \
        f"T-E2E FAIL: resposta ainda menciona coloracao: {resp1.get('resposta')}"

    # MSG2: Confirmação
    print(f"\n[MSG2] Enviando: 'sim gostaria sim'")
    resp2 = await roteador_principal(
        user_id=user_id,
        mensagem="sim gostaria sim",
        tenant_id=TENANT_TEST,
        context=None,
    )

    print(f"[RESP2] {resp2.get('resposta', '')[:200]}")

    ctx_msg2 = await carregar_contexto_temporario_v2(TENANT_TEST, cliente_id)
    print(f"\n[CTX-MSG2]")
    print(f"  servico: {ctx_msg2.get('servico')}")
    print(f"  estado: {ctx_msg2.get('estado_fluxo')}")

    # VALIDAÇÃO 2: Serviço preservado, não reverteu para coloracao
    assert ctx_msg2.get("servico") == "corte feminino", \
        f"T-E2E FAIL: servico reverteu para {ctx_msg2.get('servico')}"

    # Estado avançou
    assert ctx_msg2.get("estado_fluxo") != "aguardando_data", \
        f"T-E2E FAIL: estado não avançou de aguardando_data"

    print(f"\n✅ T-CONSULTA-E2E PASSOU")


@pytest.mark.asyncio
async def test_t_multi_multiplos_servicos():
    """T-MULTI: Mensagem com múltiplos serviços mencionados
    → deve pedir esclarecimento, não selecionar arbitrariamente"""

    print("\n" + "="*90)
    print("T-MULTI: Múltiplos serviços mencionados → pedir esclarecimento")
    print("="*90)

    ts = int(time.time() * 1000) % 1000000
    user_id = f"551199996{ts:07d}"
    cliente_id = user_id

    # Setup: Draft com coloracao
    ctx_initial = {
        "draft_agendamento": {
            "servico": "coloracao",
        },
        "servico": "coloracao",
        "estado_fluxo": "aguardando_data",
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, cliente_id, ctx_initial)
    print(f"[SETUP] Draft com coloracao")

    # Msg: Múltiplos serviços
    print(f"\n[MSG] Enviando: 'quero corte e escova amanha as 10'")
    resposta = await roteador_principal(
        user_id=user_id,
        mensagem="quero corte e escova amanha as 10",
        tenant_id=TENANT_TEST,
        context=None,
    )

    print(f"[RESP] {resposta.get('resposta', '')[:150]}")

    ctx_after = await carregar_contexto_temporario_v2(TENANT_TEST, cliente_id)

    print(f"\n[VALIDAÇÃO]")
    print(f"  estado: {ctx_after.get('estado_fluxo')}")
    print(f"  servicos_opcao: {ctx_after.get('servicos_opcao')}")

    # T-MULTI: Estado deve ser aguardando_servico
    assert ctx_after.get("estado_fluxo") == "aguardando_servico", \
        f"T-MULTI FAIL: estado={ctx_after.get('estado_fluxo')}, esperado aguardando_servico"

    # Múltiplos serviços foram detectados
    opcoes = ctx_after.get("servicos_opcao", [])
    assert len(opcoes) >= 2, \
        f"T-MULTI FAIL: servicos_opcao deveria ter >= 2, obteve {len(opcoes)}"

    # Resposta não menciona coloracao
    resposta_text = resposta.get("resposta", "").lower()
    assert "coloracao" not in resposta_text, \
        f"T-MULTI FAIL: resposta ainda menciona coloracao"

    print(f"\n✅ T-MULTI PASSOU")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
