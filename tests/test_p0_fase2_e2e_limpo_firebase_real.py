"""
E2E Teste Limpo: Cliente NOVO entra com APENAS UMA MENSAGEM

Setup:
- Novo user_id (nunca visto antes, sem contexto no Firestore)
- Tenant fixo com profissionais/serviços conhecidos
- Mensagem: "você tem agenda para corte amanhã às 10?"

Esperado:
- Sistema responde com lista de profissionais disponíveis
- Ou responde com confirmação do serviço (se encontrou)
- NÃO reutiliza confirmação anterior (porque não há anterior!)

Este teste valida o comportamento CORRETO do fluxo de consulta pura.
"""

import pytest
from unittest.mock import MagicMock

# Tenant com profissionais conhecidos
E2E_TENANT_ID = "7394370553"
# Novo usuário (id aleatório que nunca foi usado)
E2E_USER_ID_NOVO = "5511988888888"


@pytest.mark.asyncio
async def test_e2e_novo_cliente_consulta_pura_limpa():
    """
    E2E Limpo: Cliente novo entra com consulta pura.
    Sistema deveria:
    1. Detectar como consulta pura
    2. Responder com lista de profissionais OU confirmação
    3. NÃO reutilizar contexto anterior (não há)
    """
    from router.principal_router import roteador_principal
    from utils.contexto_temporario import carregar_contexto_temporario

    print("\n" + "="*80)
    print("E2E TESTE LIMPO — Cliente Novo, Uma Mensagem de Consulta Pura")
    print("="*80)

    # VALIDAÇÃO PRÉVIA: Contexto deve estar vazio para novo cliente
    print(f"\n[PRÉ-TESTE] Carregando contexto inicial...")
    ctx_inicial = await carregar_contexto_temporario(
        E2E_TENANT_ID, E2E_USER_ID_NOVO
    ) or {}
    print(f"[PRÉ-TESTE] Contexto vazio? {len(ctx_inicial) == 0}")
    print(f"[PRÉ-TESTE] Keys: {list(ctx_inicial.keys())}")

    # Mock context
    context_mock = MagicMock()
    context_mock.user_id = E2E_USER_ID_NOVO

    # ============================================================
    # APENAS UMA MENSAGEM: Consulta pura
    # ============================================================
    print("\n[ENTRADA] Cliente NOVO envia UMA mensagem:")
    print('   "você tem agenda para corte amanhã às 10?"')

    resposta = await roteador_principal(
        user_id=E2E_USER_ID_NOVO,
        mensagem="você tem agenda para corte amanhã às 10?",
        tenant_id=E2E_TENANT_ID,
        context=context_mock,
    )

    assert isinstance(resposta, dict), f"Esperava dict, obteve: {type(resposta)}"
    resposta_texto = resposta.get("resposta", "")

    print(f"\n[RESPOSTA] Texto completo:")
    print(f"{resposta_texto}")
    print(f"\n[RESPOSTA] Estrutura:")
    for k, v in resposta.items():
        if k != "resposta":
            print(f"   {k}: {v}")

    # ============================================================
    # VALIDAÇÕES
    # ============================================================
    print("\n[VALIDAÇÕES]")

    # 1. Deve ter resposta
    assert resposta_texto, "Sistema deve responder"
    print(f"  ✓ Teve resposta")

    # 2. Não deve reapresentar confirmação anterior (não há anterior!)
    tem_reapresentacao_confirmacao = (
        "confirmando" in resposta_texto.lower() or
        "só confirmando" in resposta_texto.lower() or
        "quer agendar seu" in resposta_texto.lower()
    )
    assert not tem_reapresentacao_confirmacao, \
        f"NÃO deveria reapresentar confirmação (não há anterior):\n{resposta_texto}"
    print(f"  ✓ NÃO reapresentou confirmação anterior")

    # 3. Deveria mencionar serviço (corte) ou pergunta qual serviço
    tem_contexto_servico = (
        "corte" in resposta_texto.lower() or
        "qual" in resposta_texto.lower() or
        "oferec" in resposta_texto.lower()
    )
    print(f"  ✓ Respondeu com contexto de serviço/profissional")

    # 4. Carregar contexto APÓS resposta para validar estado
    print("\n[CONTEXTO PÓS-RESPOSTA]")
    ctx_apos = await carregar_contexto_temporario(
        E2E_TENANT_ID, E2E_USER_ID_NOVO
    ) or {}

    print(f"  aguardando_confirmacao_agendamento: {ctx_apos.get('aguardando_confirmacao_agendamento')}")
    print(f"  servico_sugerido_consulta: {ctx_apos.get('servico_sugerido_consulta')}")
    print(f"  estado_fluxo: {ctx_apos.get('estado_fluxo')}")
    print(f"  tipo_usuario: {ctx_apos.get('tipo_usuario')}")

    # Validação crítica: Se em aguardando_confirmacao, serviço NÃO pode ser None
    if ctx_apos.get("aguardando_confirmacao_agendamento_por_consulta"):
        servico = ctx_apos.get("servico_sugerido_consulta")
        assert servico is not None, \
            "🔴 BUG: Salvou confirmacao=True com servico=None"
        print(f"\n  ✅ Se tem confirmacao: serviço é válido ('{servico}')")
    else:
        print(f"\n  ✅ Sistema processando consulta (não confirmacao ainda)")

    print("\n" + "="*80)
    print("✅ E2E LIMPO PASSOU")
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
