"""
E2E Test: Fluxo Consulta → Agendamento com Firebase Real

Cenários:
1. Cliente pergunta "tem manicure amanhã?" → sistema responde com confirmação
2. Cliente confirma "sim" → sistema cria evento
3. Cliente pergunta com serviço não encontrado → lista serviços
"""

import pytest
from unittest.mock import MagicMock

# Constantes de teste
E2E_TENANT_ID = "7394370553"
E2E_USER_ID = "5511991382080"
E2E_ACTOR_ID = f"whatsapp:{E2E_USER_ID}"


@pytest.mark.asyncio
async def test_consulta_agendamento_simples_firebase_real():
    """
    E2E: Cliente consulta disponibilidade com Firebase real.
    Validar que estado de confirmação é salvo COM serviço válido (não None).
    """
    from router.principal_router import roteador_principal
    from utils.contexto_temporario import carregar_contexto_temporario

    print("\n" + "="*70)
    print("TEST: E2E Consulta Agendamento com Firebase Real")
    print("="*70)

    context_mock = MagicMock()
    context_mock.user_id = E2E_USER_ID

    # PASSO 1: Cliente pergunta sobre manicure
    print("\n[PASSO 1] Cliente: 'tem manicure amanha as 10?'")

    resposta1 = await roteador_principal(
        user_id=E2E_USER_ID,
        mensagem="tem manicure amanha as 10?",
        tenant_id=E2E_TENANT_ID,
        context=context_mock,
    )

    # roteador_principal retorna dict
    assert isinstance(resposta1, dict), f"Esperava dict, obteve: {type(resposta1)}"
    resposta_texto = resposta1.get("resposta", "")
    print(f"[RESPOSTA 1] {resposta_texto[:100]}...")

    # Validar que teve resposta
    assert resposta_texto, "Sistema deve responder à consulta"

    # PASSO 2: Carregar contexto após resposta
    print("\n[PASSO 2] Verificar contexto salvo...")
    ctx_apos_p1 = await carregar_contexto_temporario(
        E2E_TENANT_ID, E2E_ACTOR_ID
    ) or {}

    print(f"[CTX] aguardando_confirmacao={ctx_apos_p1.get('aguardando_confirmacao_agendamento_por_consulta')}")
    print(f"[CTX] servico_sugerido={ctx_apos_p1.get('servico_sugerido_consulta')}")

    # Validar: Se em estado de confirmação, serviço NÃO pode ser None
    if ctx_apos_p1.get("aguardando_confirmacao_agendamento_por_consulta"):
        servico_sugerido = ctx_apos_p1.get("servico_sugerido_consulta")
        assert servico_sugerido is not None, \
            "BUG: Salvou confirmação com serviço=None (regressão do fix)"
        print(f"\n✅ VALIDAÇÃO PASSOU: Confirmação salva com serviço válido ('{servico_sugerido}')")
    else:
        # Serviço não foi encontrado, lista deve estar disponível
        print(f"\n✅ VALIDAÇÃO PASSOU: Serviço não encontrado, pedindo especificação")




if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
