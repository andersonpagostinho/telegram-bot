"""
Teste simples: Novo ator com typos - deve usar GPT fallback
"""

import pytest
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


@pytest.mark.asyncio
async def test_novo_ator_typos_gpt_fallback():
    """Nova sessão sem histórico anterior - GPT fallback deve funcionar"""

    # Novo ator = garantido estado limpo
    new_actor = "whatsapp:9999999999999"
    tenant_id = "7394370553"

    # Setup novo ator
    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{new_actor}",
        dados={"estado_fluxo": "idle"}
    )

    print("\n[TESTE] Novo ator com typos → GPT fallback")

    # Mensagem com typos
    resultado = await roteador_principal(
        user_id=new_actor,
        mensagem="ola, gstria de agndar unha para terç agora",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    # Verificar
    sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{new_actor}")

    print(f"Intenção: {sessao.get('intencao_conversacional')}")
    print(f"Estado: {sessao.get('estado_fluxo')}")

    # Esperado: GPT fallback reconheceu como agendamento_direto
    assert sessao.get("intencao_conversacional") in ["agendamento_direto", "consulta"], \
        f"Esperado agendamento_direto ou consulta, obteve {sessao.get('intencao_conversacional')}"

    print("PASS: GPT fallback funcionou")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
