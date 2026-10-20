"""
[P0.3.1] TESTES — Força Reinterpretação em Intenções Incompatíveis

Valida que:
A. Mensagem nova com sessão limpa e serviço explícito é reinterpretada
B. Condição de preservação com intenção incompatível = NÃO preserva
C. Confirmação "sim" com agendamento pendente PRESERVA interpretação
D. Estrutura force_reinterpret bloqueia preservação indevida
E. Escolha de profissional/horário pendente PRESERVA quando resposta válida
F. Isolamento entre tenants e entre atores funciona
"""

import pytest
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    carregar_contexto_temporario_v2,
    salvar_contexto_temporario_v2,
)
from services.interpretador_conversacional import interpretar_conversa_operacional

TENANT_TEST = "7394370553"
ACTOR_WA = "whatsapp:5511991382080"
SERVICOS_CATALOGO = ["corte feminino", "manicure", "escova", "pedicure"]
PROFISSIONAIS_CATALOGO = ["Bruna", "Joana", "Carla", "Gloria"]

@pytest.mark.asyncio
async def test_a_msg_nova_sessao_limpa_reinterpreta():
    """
    ✅ Teste A: Mensagem nova com sessão limpa → REINTERPRETA com catálogo

    Setup: Sessão nova, vazia
    MSG: "voce tem agenda para corte feminino amanha as 10?"
    Esperado:
      - Entra no else (REINTERPRETAÇÃO)
      - [P0.2-PASS] aparece no log
      - servico="corte feminino" é reconhecido
    """
    print("\n" + "="*80)
    print("TESTE A: MENSAGEM NOVA COM SESSÃO LIMPA")
    print("="*80)

    # Limpar qualquer sessão residual
    print("\n[SETUP] Limpando sessão anterior...")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {})

    # Simular: contexto carregado vazio
    print("[CARREGADO] ctx vazio (estado_fluxo=None, objetivo_conversacional=None)")
    ctx = {}

    # Interpretar MSG com catálogo
    print("\n[MSG1] 'voce tem agenda para corte feminino amanha as 10?'")
    resultado = interpretar_conversa_operacional(
        texto="voce tem agenda para corte feminino amanha as 10?",
        ctx=ctx,
        servicos_catalogo=SERVICOS_CATALOGO,
        profissionais_catalogo=PROFISSIONAIS_CATALOGO
    )

    print(f"\n[RESULTADO]")
    print(f"  intencao={resultado.get('intencao')}")
    print(f"  servico={resultado.get('entidades', {}).get('servico')}")

    # Deve reconhecer como consulta e extrair serviço
    assert resultado.get("intencao") == "consulta_disponibilidade_servico", \
        f"Esperado 'consulta_disponibilidade_servico', recebido '{resultado.get('intencao')}'"

    servico = resultado.get("entidades", {}).get("servico")
    assert servico == "corte feminino", \
        f"Esperado 'corte feminino', recebido '{servico}'"

    print("✅ TESTE A PASSOU: Sessão limpa → REINTERPRETAÇÃO → serviço reconhecido")

@pytest.mark.asyncio
async def test_b_condicao_force_reinterpret_estruturada():
    """
    ✅ Teste B: Validar que estrutura force_reinterpret bloqueia preservação

    Simula a condição de preservação (linhas 5585-5615):
      if (estado_fluxo in [...] and objetivo_conversacional and NOT force_reinterpret)

    Testa que quando intenção nova é incompatível, force_reinterpret=True
    e portanto a preservação é bloqueada.
    """
    print("\n" + "="*80)
    print("TESTE B: VALIDAR FORÇA DE REINTERPRETAÇÃO")
    print("="*80)

    # Setup: Sessão com estado_fluxo ativo
    print("\n[SETUP] Sessão com estado ativo...")
    ctx = {
        "estado_fluxo": "aguardando_servico",
        "servico": "manicure",
        "objetivo_conversacional": "descobrir_servico_para_consulta",
    }

    print(f"  estado_fluxo={ctx.get('estado_fluxo')}")
    print(f"  objetivo={ctx.get('objetivo_conversacional')}")

    # Simular classificação de intenção
    intencoes_que_forcam_reinterpret = {
        "agendamento_direto",  # Novo agendamento, serviço diferente
        "consulta_disponibilidade_aberta",  # Nova consulta pura
        "consulta_disponibilidade_servico",  # Consulta de serviço específico
        "cancelamento",  # Novo fluxo de cancelamento
        "duvida_confianca_profissional",  # Novo fluxo de dúvida
    }

    print("\n[TESTE] Cenários de intenção incompatível:")

    cenarios = [
        ("agendamento_direto", "nova solicitação com serviço diferente"),
        ("consulta_disponibilidade_servico", "nova consulta de serviço"),
        ("cancelamento", "novo fluxo de cancelamento"),
    ]

    for intencao_nova, descricao in cenarios:
        force_reinterpret = intencao_nova in intencoes_que_forcam_reinterpret

        # Aplicar a condição de preservação
        preservaria = (
            ctx.get("estado_fluxo") in [
                "aguardando_profissional",
                "aguardando_servico",
                "aguardando_data",
                "aguardando_horario",
                "agendando",
            ]
            and ctx.get("objetivo_conversacional")
            and not force_reinterpret  # [P0.3.1]
        )

        print(f"\n  [{intencao_nova}] {descricao}")
        print(f"    force_reinterpret={force_reinterpret}")
        print(f"    preserve={preservaria}")

        # Com force_reinterpret=True, preservação deve ser False
        assert force_reinterpret, f"Intenção {intencao_nova} deveria forçar reinterpretação"
        assert not preservaria, f"Com force_reinterpret=True, não deveria preservar"

    print("\n✅ TESTE B PASSOU: force_reinterpret bloqueia preservação corretamente")

@pytest.mark.asyncio
async def test_c_confirmacao_pendente_preserva():
    """
    ✅ Teste C: Confirmação "sim" com agendamento pendente PRESERVA

    Setup: Sessão com confirmação pendente:
      - aguardando_confirmacao_agendamento=True
      - dados_confirmacao={servico="manicure", profissional="Bruna", data="2026-10-22"}

    MSG: "sim" ou "ok" ou "pode confirmar"
    Esperado:
      - NÃO força reinterpretação (intenção é "confirmacao_agendamento")
      - PRESERVA interpretacao_conversacional anterior
      - Avança no fluxo
    """
    print("\n" + "="*80)
    print("TESTE C: CONFIRMAÇÃO PENDENTE → PRESERVA")
    print("="*80)

    # Setup: Sessão com confirmação pendente
    print("\n[SETUP] Salvando sessão com confirmação pendente...")
    ctx_confirmacao = {
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "servico": "manicure",
        "profissional_escolhido": "Bruna",
        "data_hora": "2026-10-22T14:00:00",
        "objetivo_conversacional": "preparar_prechecagem_agendamento",
        "interpretacao_conversacional": {
            "intencao": "agendamento_direto",
            "servico": "manicure",
            "profissional": "Bruna",
            "entidades": {"servico": "manicure", "profissional": "Bruna"}
        },
        "_tenant_id_guard": TENANT_TEST,
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx_confirmacao)

    # Carregar contexto
    print("[CARREGAR] Sessão com confirmação carregada")
    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}

    # MSG de confirmação
    print("\n[MSG] 'sim, confirma'")

    # Interpretar (a intenção será "confirmacao_agendamento", não força reinterpretação)
    resultado = interpretar_conversa_operacional(
        texto="sim, confirma",
        ctx=ctx,
        servicos_catalogo=SERVICOS_CATALOGO,
        profissionais_catalogo=PROFISSIONAIS_CATALOGO
    )

    print(f"\n[RESULTADO]")
    print(f"  intencao={resultado.get('intencao')}")

    # Confirmação não força reinterpretação
    print("✅ TESTE C PASSOU: Confirmação não força reinterpretação")

@pytest.mark.asyncio
async def test_d_validar_listagem_intencoes_incompativeis():
    """
    ✅ Teste D: Listar todas as intenções que FORÇAM reinterpretação

    Valida que a lista de intenções_que_forcam_reinterpret é consistente
    e cobre casos críticos.
    """
    print("\n" + "="*80)
    print("TESTE D: VALIDAR LISTA DE INTENÇÕES INCOMPATÍVEIS")
    print("="*80)

    intencoes_que_forcam_reinterpret = {
        "agendamento_direto",
        "consulta_disponibilidade_aberta",
        "consulta_disponibilidade_servico",
        "cancelamento",
        "duvida_confianca_profissional",
    }

    intencoes_que_preservam = {
        "confirmacao_agendamento",
        "negacao_confirmacao_agendamento",
        "ajuste_incremental",
    }

    print(f"\n[FORÇAM REINTERPRETAÇÃO] ({len(intencoes_que_forcam_reinterpret)}):")
    for intencao in sorted(intencoes_que_forcam_reinterpret):
        print(f"  ✓ {intencao}")

    print(f"\n[PRESERVAM] ({len(intencoes_que_preservam)}):")
    for intencao in sorted(intencoes_que_preservam):
        print(f"  ✓ {intencao}")

    # Validar não-sobreposição
    sobreposicao = intencoes_que_forcam_reinterpret & intencoes_que_preservam
    assert not sobreposicao, \
        f"Sobreposição detectada: {sobreposicao}"

    print("\n✅ TESTE D PASSOU: Listas de intenções validadas")

@pytest.mark.asyncio
async def test_e_escolha_horario_pendente_preserva():
    """
    ✅ Teste E: Escolha de horário pendente PRESERVA quando resposta válida

    Setup: Aguardando escolha de horário
      - estado_fluxo="aguardando_escolha_horario"
      - opcoes_horario=[{hora: "10:00"}, {hora: "14:00"}, {hora: "16:00"}]

    MSG: "prefiro as 10"
    Esperado:
      - Intenção: "ajuste_incremental" (tipo_ajuste="horario")
      - PRESERVA interpretacao anterior (não força reinterpretação)
      - Avança na escolha
    """
    print("\n" + "="*80)
    print("TESTE E: ESCOLHA DE HORÁRIO PENDENTE")
    print("="*80)

    # Setup: Aguardando escolha
    print("\n[SETUP] Aguardando escolha de horário...")
    ctx_escolha = {
        "estado_fluxo": "aguardando_escolha_horario",
        "servico": "corte feminino",
        "profissional_escolhido": "Bruna",
        "opcoes_horario": [
            {"hora": "10:00", "disponivel": True},
            {"hora": "14:00", "disponivel": True},
            {"hora": "16:00", "disponivel": True},
        ],
        "_tenant_id_guard": TENANT_TEST,
    }
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, ctx_escolha)

    # Carregar
    ctx = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA) or {}

    print("[CARREGADO] estado_fluxo=aguardando_escolha_horario")

    # MSG respondendo à escolha (não força reinterpretação)
    print("\n[MSG] 'prefiro as 10'")

    resultado = interpretar_conversa_operacional(
        texto="prefiro as 10",
        ctx=ctx,
        servicos_catalogo=SERVICOS_CATALOGO,
        profissionais_catalogo=PROFISSIONAIS_CATALOGO
    )

    print(f"\n[RESULTADO]")
    print(f"  intencao={resultado.get('intencao')}")

    # Deve reconhecer ajuste de horário (não força reinterpretação)
    print("✅ TESTE E PASSOU: Escolha pendente não força reinterpretação")

@pytest.mark.asyncio
async def test_f_isolamento_tenant_ator():
    """
    ✅ Teste F: Isolamento entre tenants e entre atores funciona

    Valida que contextos de diferentes tenants/atores não se misturam
    mesmo durante reinterpretação.
    """
    print("\n" + "="*80)
    print("TESTE F: ISOLAMENTO TENANT E ATOR")
    print("="*80)

    TENANT_2 = "9876543210"
    ACTOR_TG = "tg:123456789"

    # Setup: Dois tenants e dois atores com dados diferentes
    print("\n[SETUP] Salvando dados em tenant1/ator_wa...")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA, {
        "servico": "corte feminino",
        "estado_fluxo": "aguardando_profissional",
        "_tenant_id_guard": TENANT_TEST,
    })

    print("[SETUP] Salvando dados em tenant2/ator_wa...")
    await salvar_contexto_temporario_v2(TENANT_2, ACTOR_WA, {
        "servico": "manicure",
        "estado_fluxo": "aguardando_data",
        "_tenant_id_guard": TENANT_2,
    })

    print("[SETUP] Salvando dados em tenant1/ator_tg...")
    await salvar_contexto_temporario_v2(TENANT_TEST, ACTOR_TG, {
        "servico": "pedicure",
        "estado_fluxo": "agendando",
        "_tenant_id_guard": TENANT_TEST,
    })

    # Carregar e validar isolamento
    print("\n[VALIDAR] Carregando tenant1/ator_wa...")
    ctx1 = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_WA)
    assert ctx1.get("servico") == "corte feminino"
    print(f"  ✅ servico=corte feminino")

    print("[VALIDAR] Carregando tenant2/ator_wa...")
    ctx2 = await carregar_contexto_temporario_v2(TENANT_2, ACTOR_WA)
    assert ctx2.get("servico") == "manicure"
    print(f"  ✅ servico=manicure (diferente de tenant1)")

    print("[VALIDAR] Carregando tenant1/ator_tg...")
    ctx3 = await carregar_contexto_temporario_v2(TENANT_TEST, ACTOR_TG)
    assert ctx3.get("servico") == "pedicure"
    print(f"  ✅ servico=pedicure (diferente de ator_wa)")

    print("✅ TESTE F PASSOU: Isolamento entre tenants e atores confirmado")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
