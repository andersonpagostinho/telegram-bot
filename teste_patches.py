#!/usr/bin/env python3
"""
Teste simulado dos 2 patches mínimos para consultas puras vs agendamentos.

Testes:
1. "vocês fazem escova?" (CONSULTA PURA)
2. "quero uma escova" (AGENDAMENTO)
3. "quero agendar uma escova amanhã às 10" (AGENDAMENTO COM DATA/HORA)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')


def simular_teste(numero: int, mensagem: str, tipo: str):
    """Simula o fluxo para um teste específico."""

    print(f"\n{'='*80}")
    print(f"TESTE {numero}: {tipo}")
    print(f"{'='*80}")
    print(f"Mensagem: '{mensagem}'")
    print(f"{'='*80}\n")

    # Simular contexto inicial limpo
    ctx = {
        "user_id": "teste_user_123",
        "objetivo_conversacional": None,
        "intencao_conversacional": None,
        "servico": None,
        "estado_fluxo": "inicial"
    }

    draft_agendamento = {}

    # --- PASSO 1: GPT classifica intenção ---
    print("[1] GPT CLASSIFICA A INTENÇÃO\n")

    if numero == 1:
        # "vocês fazem escova?" → consulta pura
        ctx["objetivo_conversacional"] = "consultar_disponibilidade_por_servico"
        ctx["intencao_conversacional"] = "consulta_disponibilidade_servico"
        print(f"    objetivo_conversacional = 'consultar_disponibilidade_por_servico'")
        print(f"    intencao_conversacional = 'consulta_disponibilidade_servico'")
        print(f"    ✅ IDENTIFICADA COMO: CONSULTA PURA\n")

    elif numero == 2:
        # "quero uma escova" → agendamento (sem data/hora)
        ctx["objetivo_conversacional"] = "agendar_servico"
        ctx["intencao_conversacional"] = "desejo_agendar"
        print(f"    objetivo_conversacional = 'agendar_servico'")
        print(f"    intencao_conversacional = 'desejo_agendar'")
        print(f"    ✅ IDENTIFICADA COMO: AGENDAMENTO\n")

    else:
        # "quero agendar uma escova amanhã às 10" → agendamento com data/hora
        ctx["objetivo_conversacional"] = "agendar_servico"
        ctx["intencao_conversacional"] = "desejo_agendar"
        ctx["data_hora"] = "amanhã 10:00"
        print(f"    objetivo_conversacional = 'agendar_servico'")
        print(f"    intencao_conversacional = 'desejo_agendar'")
        print(f"    data_hora = 'amanhã 10:00'")
        print(f"    ✅ IDENTIFICADA COMO: AGENDAMENTO COM DATA/HORA\n")

    # --- PASSO 2: extrair_slots_e_mesclar ---
    print("[2] EXTRAIR_SLOTS_E_MESCLAR\n")

    # Simular detecção de serviço
    servico_detectado = "escova"

    if servico_detectado:
        eh_consulta_pura_servico = (
            ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
            or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
        )

        if eh_consulta_pura_servico:
            print(f"    🛡️ [CONSULTA PURA] serviço detectado='{servico_detectado}', "
                  f"mas não entra em ctx['servico'] nem draft_agendamento")
            print(f"    ctx['servico'] → None (bloqueado)")
            print(f"    draft['servico'] → None (bloqueado)\n")
        else:
            ctx["servico"] = servico_detectado
            draft_agendamento["servico"] = servico_detectado
            print(f"    ✅ Serviço '{servico_detectado}' adicionado ao contexto")
            print(f"    ctx['servico'] = '{servico_detectado}'")
            print(f"    draft['servico'] = '{servico_detectado}'\n")

    # --- PASSO 3: resolver_proximo_passo_real ---
    print("[3] RESOLVER_PROXIMO_PASSO_REAL\n")

    proximo_passo_real = None

    # PATCH 2: Early return para consultas puras
    objetivo = ctx.get("objetivo_conversacional")
    intencao = ctx.get("intencao_conversacional")

    if (
        objetivo == "consultar_disponibilidade_por_servico"
        or intencao == "consulta_disponibilidade_servico"
    ):
        print(f"    🛡️ [CONSULTA PURA] resolver_proximo_passo_real bloqueado — "
              f"não perguntar data/hora")
        proximo_passo_real = None
        print(f"    proximo_passo_real = None (bloqueado)\n")
    else:
        # Simulação de lógica normal
        tem_data_valor = bool(ctx.get("data_hora"))

        if not ctx.get("servico"):
            proximo_passo_real = "perguntar_servico"
        elif not tem_data_valor:
            proximo_passo_real = "perguntar_data_hora"
        else:
            proximo_passo_real = "validar_profissional"

        print(f"    Lógica normal executada:")
        print(f"    tem_data_valor = {tem_data_valor}")
        print(f"    ctx['servico'] = {ctx.get('servico')}")
        print(f"    → proximo_passo_real = '{proximo_passo_real}'\n")

    # --- PASSO 4: p1_preservar_resposta_gpt ---
    print("[4] PRESERVAR_RESPOSTA_GPT\n")

    p1_preservar_resposta_gpt = (
        ctx.get("objetivo_conversacional") != "agendar_servico"
        and not proximo_passo_real
    )

    print(f"    p1_preservar_resposta_gpt = {p1_preservar_resposta_gpt}")
    print(f"    (objetivo != 'agendar_servico'={ctx.get('objetivo_conversacional') != 'agendar_servico'} "
          f"AND not proximo_passo_real={not proximo_passo_real})")

    if p1_preservar_resposta_gpt:
        print(f"    ✅ GPT RESPONDE LIVREMENTE (sem entrar em fluxo operacional)\n")
    else:
        print(f"    ❌ Entra em fluxo operacional (agendamento)\n")

    # --- RESUMO FINAL ---
    print("="*80)
    print("RESULTADO FINAL")
    print("="*80)

    print(f"\nDraft agendamento criado? {bool(draft_agendamento)}")
    print(f"  → draft = {draft_agendamento if draft_agendamento else '{}' }")

    print(f"\nctx['servico'] preenchido? {bool(ctx.get('servico'))}")
    print(f"  → {ctx.get('servico') or '(vazio)'}")

    print(f"\nproximo_passo_real = {proximo_passo_real}")

    print(f"\nGPT pode responder livremente? {p1_preservar_resposta_gpt}")

    # Resultado esperado
    print(f"\n{'─'*80}")
    if numero == 1:
        print("ESPERADO:")
        print("  ✅ Responde informativamente")
        print("  ✅ Não cria draft_agendamento")
        print("  ✅ Não define ctx['servico']")
        print("  ✅ Não define proximo_passo_real = perguntar_data_hora")
    elif numero == 2:
        print("ESPERADO:")
        print("  ✅ Entra em agendamento")
        print("  ✅ Define servico = escova")
        print("  ✅ Pergunta data/hora")
    else:
        print("ESPERADO:")
        print("  ✅ Entra no fluxo operacional")
        print("  ✅ Segue para profissional ou precheck")
        print("  ✅ Não cai como consulta pura")


if __name__ == "__main__":
    print("\n" + "█"*80)
    print("TESTE DOS 2 PATCHES MÍNIMOS")
    print("█"*80)

    # Teste 1: Consulta pura
    simular_teste(
        1,
        "vocês fazem escova?",
        "CONSULTA PURA"
    )

    # Teste 2: Agendamento simples
    simular_teste(
        2,
        "quero uma escova",
        "AGENDAMENTO SIMPLES"
    )

    # Teste 3: Agendamento com data/hora
    simular_teste(
        3,
        "quero agendar uma escova amanhã às 10",
        "AGENDAMENTO COM DATA/HORA"
    )

    print("\n" + "█"*80)
    print("FIM DOS TESTES")
    print("█"*80 + "\n")
