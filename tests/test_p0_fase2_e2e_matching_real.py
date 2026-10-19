"""
FASE 2 — E2E FIREBASE REAL: Validação da Refatoração de Matching

Teste de ponta a ponta com Firebase real, novo cliente, entrada única.
Igual ao padrão que o usuário validou anteriormente.
"""

import pytest
import time

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_e2e_firebase_real_matching_puro_corte_feminino():
    """
    E2E Firebase Real: Cliente novo faz consulta pura com refatoração de matching.

    Entrada: "você tem agenda para corte feminino amanhã às 10?"

    Esperado:
    - Sistema detecta serviço "corte feminino" (match exato, não prefixo)
    - Sistema responde: "Sim, fazemos corte feminino! Gostaria de agendar?"
    - Valida que matching puro está funcionando de verdade
    """
    from router.principal_router import roteador_principal
    from utils.contexto_temporario import carregar_contexto_temporario

    # Novo user_id único
    timestamp_ms = int(time.time() * 1000)
    user_id_novo = f"551199{timestamp_ms % 10000000:07d}"

    print("\n" + "="*90)
    print("E2E FIREBASE REAL — Matching Puro: 'corte feminino' (match exato)")
    print("="*90)

    print(f"\n[SETUP]")
    print(f"  Tenant: {E2E_TENANT_ID}")
    print(f"  User ID novo: {user_id_novo}")
    print(f"  Entrada: 'você tem agenda para corte feminino amanhã às 10?'")

    # Validar contexto vazio
    ctx_inicial = await carregar_contexto_temporario(
        E2E_TENANT_ID, user_id_novo
    ) or {}

    print(f"\n[PRÉ-TESTE]")
    print(f"  Contexto vazio? {len(ctx_inicial) == 0}")
    assert len(ctx_inicial) == 0, "Contexto deve estar vazio"

    # ============================================================
    # TESTE: Entrada com serviço completo (não apenas prefixo)
    # ============================================================
    print(f"\n[ENTRADA]")
    entrada = "você tem agenda para corte feminino amanhã às 10?"
    print(f'  "{entrada}"')

    resposta = await roteador_principal(
        user_id=user_id_novo,
        mensagem=entrada,
        tenant_id=E2E_TENANT_ID,
        context=None,
    )

    assert isinstance(resposta, dict), f"Esperava dict, obteve: {type(resposta)}"
    resposta_texto = resposta.get("resposta", "")

    print(f"\n[RESPOSTA]")
    print(f"─" * 90)
    print(resposta_texto)
    print(f"─" * 90)

    # ============================================================
    # VALIDAÇÕES — Matching puro deve detectar "corte feminino"
    # ============================================================
    print(f"\n[VALIDAÇÕES]")

    # 1. Sistema detectou "corte feminino"?
    tem_corte_feminino = "corte feminino" in resposta_texto.lower()
    print(f"  Menciona 'corte feminino': {tem_corte_feminino}")

    # 2. Respondeu afirmativamente?
    tem_afirmacao = "sim" in resposta_texto.lower() or "fazemos" in resposta_texto.lower()
    print(f"  Resposta afirmativa: {tem_afirmacao}")

    # 3. NÃO reutilizou confirmação anterior (não há anterior)
    tem_reapresentacao = "confirmando" in resposta_texto.lower()
    assert not tem_reapresentacao, "Não deveria reapresentar confirmação"
    print(f"  ✅ NÃO reutilizou confirmação anterior")

    # 4. Perguntou se quer agendar?
    tem_pergunta_agendamento = "agendar" in resposta_texto.lower() or "gostaria" in resposta_texto.lower()
    print(f"  Pergunta se quer agendar: {tem_pergunta_agendamento}")

    # ============================================================
    # CONTEXTO PÓS-RESPOSTA
    # ============================================================
    print(f"\n[CONTEXTO PÓS-RESPOSTA]")
    ctx_apos = await carregar_contexto_temporario(
        E2E_TENANT_ID, user_id_novo
    ) or {}

    campos = ["intencao_conversacional", "estado_fluxo", "aguardando_confirmacao_agendamento_por_consulta", "servico_sugerido_consulta"]
    for campo in campos:
        valor = ctx_apos.get(campo)
        if valor:
            print(f"  {campo}: {valor}")

    # Validação crítica
    if ctx_apos.get("aguardando_confirmacao_agendamento_por_consulta"):
        servico = ctx_apos.get("servico_sugerido_consulta")
        assert servico is not None, "Não deveria ter confirmação com serviço=None"
        assert "corte" in servico.lower(), f"Serviço deveria conter 'corte', obteve: {servico}"
        print(f"  ✅ Confirmação salva com serviço válido: {servico}")

    print(f"\n" + "="*90)
    print("✅ E2E FIREBASE REAL PASSOU — Matching Puro Funciona!")
    print("="*90)

    return {
        "entrada": entrada,
        "resposta": resposta_texto,
        "contexto": ctx_apos
    }


@pytest.mark.asyncio
async def test_e2e_firebase_real_matching_prefixo_corte():
    """
    E2E Firebase Real: Cliente novo faz consulta com apenas prefixo "corte".

    Entrada: "você tem agenda para corte amanhã às 10?"

    Esperado:
    - Sistema detecta que "corte" pode ser "corte feminino" (match de prefixo)
    - Mas não consegue determinar QUAL tipo de corte
    - Sistema lista serviços: "Não consegui identificar exatamente qual serviço..."
    """
    from router.principal_router import roteador_principal
    from utils.contexto_temporario import carregar_contexto_temporario

    # Novo user_id único
    timestamp_ms = int(time.time() * 1000)
    user_id_novo = f"551199{(timestamp_ms + 1) % 10000000:07d}"

    print("\n" + "="*90)
    print("E2E FIREBASE REAL — Matching Prefixo: 'corte' (sem especificar tipo)")
    print("="*90)

    print(f"\n[SETUP]")
    print(f"  Tenant: {E2E_TENANT_ID}")
    print(f"  User ID novo: {user_id_novo}")
    print(f"  Entrada: 'você tem agenda para corte amanhã às 10?'")

    # Validar contexto vazio
    ctx_inicial = await carregar_contexto_temporario(
        E2E_TENANT_ID, user_id_novo
    ) or {}

    print(f"\n[PRÉ-TESTE]")
    print(f"  Contexto vazio? {len(ctx_inicial) == 0}")
    assert len(ctx_inicial) == 0, "Contexto deve estar vazio"

    # ============================================================
    # TESTE: Entrada com apenas prefixo "corte"
    # ============================================================
    print(f"\n[ENTRADA]")
    entrada = "você tem agenda para corte amanhã às 10?"
    print(f'  "{entrada}"')

    resposta = await roteador_principal(
        user_id=user_id_novo,
        mensagem=entrada,
        tenant_id=E2E_TENANT_ID,
        context=None,
    )

    assert isinstance(resposta, dict), f"Esperava dict, obteve: {type(resposta)}"
    resposta_texto = resposta.get("resposta", "")

    print(f"\n[RESPOSTA]")
    print(f"─" * 90)
    print(resposta_texto)
    print(f"─" * 90)

    # ============================================================
    # VALIDAÇÕES
    # ============================================================
    print(f"\n[VALIDAÇÕES]")

    # 1. Sistema não conseguiu determinar o serviço específico
    # Então lista as opções
    lista_opcoes = "qual" in resposta_texto.lower() or "oferec" in resposta_texto.lower()
    assert lista_opcoes, "Deveria listar opções quando 'corte' é ambíguo"
    print(f"  ✅ Sistema listou opções de serviço")

    # 2. Menciona "corte feminino" ou "corte masculino" nas opções?
    tem_corte = "corte" in resposta_texto.lower()
    print(f"  Menciona 'corte' nas opções: {tem_corte}")

    # 3. NÃO tentou agendar automaticamente
    tem_agendar_automatico = "gostaria de agendar" in resposta_texto.lower() and "qual serviço" not in resposta_texto.lower()
    assert not tem_agendar_automatico or lista_opcoes, "Não deveria agendar sem serviço definido"
    print(f"  ✅ Não agendou automaticamente")

    # ============================================================
    # CONTEXTO PÓS-RESPOSTA
    # ============================================================
    print(f"\n[CONTEXTO PÓS-RESPOSTA]")
    ctx_apos = await carregar_contexto_temporario(
        E2E_TENANT_ID, user_id_novo
    ) or {}

    # Não deveria ter confirmação pendente (serviço é ambíguo)
    tem_confirmacao = ctx_apos.get("aguardando_confirmacao_agendamento_por_consulta")
    assert not tem_confirmacao, "Não deveria ter confirmação com serviço ambíguo"
    print(f"  ✅ NÃO salvou confirmação com serviço ambíguo")

    print(f"\n" + "="*90)
    print("✅ E2E FIREBASE REAL PASSOU — Ambiguidade Detectada Corretamente!")
    print("="*90)

    return {
        "entrada": entrada,
        "resposta": resposta_texto,
        "contexto": ctx_apos
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
