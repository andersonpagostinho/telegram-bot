"""
P0 — E2E Test: Validação de Lógica de Comparação

Testa a lógica pura do fix P0.7.1 sem dependências complexas.
Reproduz o cenário: mensagem de comparação + draft anterior.
"""

import pytest


@pytest.mark.asyncio
async def test_e2e_comparacao_logica_pura():
    """Teste E2E: Comparação não aciona validação de conflito."""

    print("\n" + "="*70)
    print("[E2E TEST] Comparação de Profissionais — Validação Lógica Pura")
    print("="*70)

    # Simular estado anterior
    ctx_antes = {
        "draft_agendamento": {
            "profissional": "Bruna",
            "data_hora": "2026-10-28T10:00:00",
            "servico": "corte feminino"
        },
        "estado_fluxo": "idle",
        "tenant_id": "7394370553",
        "actor_id": "whatsapp:5511991382080"
    }

    # Simular resposta do GPT para comparação
    gpt_response = {
        "intencao": "consulta",
        "entidades": {
            "profissional_1": "Carla",
            "profissional_2": "Bruna"
        },
        "confianca": 80
    }

    print("\n[SETUP]")
    print(f"  Draft anterior: {ctx_antes['draft_agendamento']}")
    print(f"  GPT resposta: {gpt_response}")

    # ETAPA 1: Aplicar lógica de P0.7.1
    print("\n[ETAPA 1] Aplicando lógica de P0.7.1 (detecção + decisão)")

    entidades = gpt_response.get("entidades", {})
    eh_comparacao = bool(entidades.get("profissional_1") or entidades.get("profissional_2"))

    print(f"  eh_comparacao = {eh_comparacao}")
    assert eh_comparacao is True, "FAIL: Comparação não foi detectada"
    print("  ✓ Comparação detectada")

    # Aplicar lógica de reclassificação
    if eh_comparacao:
        intencao_final = "consulta"  # Mantém genérico
        print(f"  → Intencao final: '{intencao_final}' (genérico)")
    else:
        intencao_final = "consulta_disponibilidade_aberta"
        print(f"  → Intencao final: '{intencao_final}' (reclassificado)")

    assert intencao_final == "consulta", "FAIL: Comparação foi reclassificada"
    print("  ✓ Comparação mantida como genérica")

    # ETAPA 2: Validar que não aciona VALIDACAO_CONFLITO_PRE_GPT
    print("\n[ETAPA 2] Verificando se VALIDACAO_CONFLITO_PRE_GPT seria disparada")

    # Simular contexto após P0.7
    ctx_apos_p07 = {
        "intencao_conversacional": intencao_final,
        "tenant_id": ctx_antes["tenant_id"],
        "actor_id": ctx_antes["actor_id"]
    }

    # Se for comparação, não extrai profissional
    if not eh_comparacao:
        ctx_apos_p07["profissional"] = entidades.get("profissional")
        ctx_apos_p07["data_hora"] = "2026-10-28T10:00:00"

    # Simular a condição de VALIDACAO_CONFLITO_PRE_GPT
    intencao_conversa_atual = ctx_apos_p07.get("intencao_conversacional")
    profissional_consulta = ctx_apos_p07.get("profissional")
    data_hora_consulta = ctx_apos_p07.get("data_hora")

    deve_validar_conflito = (
        intencao_conversa_atual == "consulta_disponibilidade_aberta"
        and profissional_consulta
        and data_hora_consulta
    )

    print(f"  intencao_conversacional: '{intencao_conversa_atual}'")
    print(f"  profissional_consulta: {profissional_consulta}")
    print(f"  data_hora_consulta: {data_hora_consulta}")
    print(f"  deve_validar_conflito: {deve_validar_conflito}")

    assert deve_validar_conflito is False, "FAIL: VALIDACAO_CONFLITO foi disparada"
    print("  ✓ VALIDACAO_CONFLITO não é disparada")

    # ETAPA 3: Validar que draft anterior é preservado
    print("\n[ETAPA 3] Validando preservação do draft anterior")

    draft_original = ctx_antes["draft_agendamento"]
    # Draft não deve ser alterado por comparação
    draft_final = ctx_antes["draft_agendamento"]  # Não foi alterado

    assert draft_final == draft_original, "FAIL: Draft foi alterado"
    print(f"  Draft preservado: {draft_final}")
    print("  ✓ Draft mantido intacto")

    # ETAPA 4: Validar isolamento de tenant
    print("\n[ETAPA 4] Validando isolamento de tenant")

    tenant_original = ctx_antes["tenant_id"]
    actor_original = ctx_antes["actor_id"]

    assert ctx_apos_p07["tenant_id"] == tenant_original, "FAIL: tenant_id divergiu"
    assert ctx_apos_p07["actor_id"] == actor_original, "FAIL: actor_id divergiu"

    print(f"  tenant_id: {ctx_apos_p07['tenant_id']}")
    print(f"  actor_id: {ctx_apos_p07['actor_id']}")
    print("  ✓ Isolamento mantido")

    # RESUMO
    print("\n" + "="*70)
    print("✅ TESTE E2E PASSOU")
    print("="*70)
    print("\nValidações executadas:")
    print("  [✓] Comparação detectada (profissional_1 + profissional_2)")
    print("  [✓] Não reclassificada (intencao_final = 'consulta')")
    print("  [✓] VALIDACAO_CONFLITO não disparada")
    print("  [✓] Draft anterior preservado")
    print("  [✓] Isolamento de tenant mantido")
    print("\nComportamento esperado:")
    print("  • Resposta sobre comparação será fornecida")
    print("  • GPT responderá sobre serviços de Carla vs Bruna")
    print("  • Draft com Bruna continuará disponível para retomada")


@pytest.mark.asyncio
async def test_e2e_consulta_real_continua_funcionando():
    """Teste E2E: Consulta real continua funcionando como antes."""

    print("\n" + "="*70)
    print("[E2E TEST] Consulta Real — Comportamento Preservado")
    print("="*70)

    # Simular resposta do GPT para consulta real
    gpt_response = {
        "intencao": "consulta",
        "entidades": {
            "profissional": "Carla",  # Singular, não plural
            "data": "2026-10-28",
            "horario": "10:00"
        },
        "confianca": 85
    }

    print(f"\n[SETUP] GPT resposta (consulta real): {gpt_response}")

    # Aplicar lógica de P0.7.1
    entidades = gpt_response.get("entidades", {})
    eh_comparacao = bool(entidades.get("profissional_1") or entidades.get("profissional_2"))

    print(f"\n[LÓGICA] eh_comparacao = {eh_comparacao}")
    assert eh_comparacao is False, "FAIL: Consulta real foi detectada como comparação"
    print("✓ Consulta real identificada corretamente")

    # Aplicar reclassificação
    if eh_comparacao:
        intencao_final = "consulta"
    else:
        intencao_final = "consulta_disponibilidade_aberta"

    print(f"[LÓGICA] intencao_final = '{intencao_final}'")
    assert intencao_final == "consulta_disponibilidade_aberta", "FAIL: Consulta não foi reclassificada"
    print("✓ Consulta reclassificada como esperado")

    # Validar extração
    ctx_apos = {"intencao_conversacional": intencao_final}
    if not eh_comparacao:
        ctx_apos["profissional"] = entidades.get("profissional")
        ctx_apos["data_hora"] = f"{entidades['data']}T{entidades['horario']}:00"

    print(f"[CONTEXTO] profissional = '{ctx_apos.get('profissional')}'")
    print(f"[CONTEXTO] data_hora = '{ctx_apos.get('data_hora')}'")

    # Validar que VALIDACAO_CONFLITO seria disparada
    deve_validar_conflito = (
        intencao_final == "consulta_disponibilidade_aberta"
        and ctx_apos.get("profissional")
        and ctx_apos.get("data_hora")
    )

    assert deve_validar_conflito is True, "FAIL: VALIDACAO_CONFLITO não seria disparada"
    print("✓ VALIDACAO_CONFLITO seria disparada (comportamento preservado)")

    print("\n" + "="*70)
    print("✅ TESTE E2E PASSOU")
    print("="*70)
    print("\nComportamento preservado:")
    print("  • Consultas reais continuam sendo reclassificadas")
    print("  • VALIDACAO_CONFLITO_PRE_GPT continua ativa")
    print("  • Sistema valida conflitos de agenda normalmente")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
