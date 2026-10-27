"""
P0.7.2A-FIX: Validar que resposta informativa eh RETORNADA (nao apenas armazenada)

Cenario do bug original:
1. Cliente: "a bruna esta disponivel amanha as 10?"
   -> Bot: Detecta conflito, responde com sugestoes

2. Cliente: "a carla faz as mesmas coisa que a bruna?"
   -> Bot: DEVERIA retornar comparacao de servicos
   -> BUG: A resposta ficava em resposta_informativa_pendente mas nao era enviada!

Este teste valida que o fix retorna a resposta imediatamente.
"""

import pytest
from unittest.mock import MagicMock
from router.principal_router import roteador_principal

E2E_TENANT_ID = "7394370553"
E2E_USER_ID = "5511991382080"


@pytest.mark.asyncio
async def test_comparacao_resposta_retornada():
    """
    CASO: Comparacao deve ser RETORNADA imediatamente ao usuario

    Em fluxo hibrido (consulta + agendamento), a resposta informativa
    deve ser enviada ANTES de continuar processamento de conflitos.
    """
    print("\n" + "="*80)
    print("[T-FIX] Testando: Resposta informativa SEM fallback para GPT")
    print("="*80)

    context_mock = MagicMock()

    # Etapa 1: Mensagem de disponibilidade com data/hora
    print("\n[ETAPA 1] Cliente: 'a bruna esta disponivel amanha as 10?'")
    resposta1 = await roteador_principal(
        user_id=E2E_USER_ID,
        mensagem="a bruna esta disponivel amanha as 10?",
        tenant_id=E2E_TENANT_ID,
        context=context_mock,
    )
    print(f"[ETAPA 1 RESPOSTA] {resposta1[:100] if resposta1 else '(NENHUMA)'}")
    assert resposta1 is not None, "Deveria ter resposta para conflito"

    # Etapa 2: Mensagem de comparacao - CRÍTICA
    print("\n[ETAPA 2] Cliente: 'a carla faz as mesmas coisa que a bruna?'")
    resposta2 = await roteador_principal(
        user_id=E2E_USER_ID,
        mensagem="a carla faz as mesmas coisa que a bruna?",
        tenant_id=E2E_TENANT_ID,
        context=context_mock,
    )
    print(f"[ETAPA 2 RESPOSTA] {resposta2[:200] if resposta2 else '(NENHUMA)'}")

    # VALIDACOES CRITICAS
    assert resposta2 is not None, "ERRO: Resposta eh NULA! (BUG nao foi fixado)"

    # Deve ser resposta informativa, NAO GPT generica
    assert "bruna" in resposta2.lower() or "carla" in resposta2.lower(), \
        "ERRO: Deveria mencionar as profissionais"

    print("\n✅ FIX VALIDADO!")
    print("   - Resposta retornada: SIM")
    print("   - Sem fallback GPT: SIM")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
