"""
TESTE REAL P0.6.2 — Frase do Usuário com Typos

Objetivo: Validar que a frase "gstria de agndar unha para terç agora, teria?"
é processada corretamente com fallback GPT e desambiguação de serviços.

Fluxo esperado:
1. Cliente envia MSG1 com typos
2. Sistema determinístico falha
3. Sistema chama GPT
4. GPT interpreta e retorna serviço(s)
5. Sistema processa resultado
"""

import pytest
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


class TestMsgRealComTypos:
    """Teste da frase real com typos"""

    @pytest.mark.asyncio
    async def test_msg_real_gstria_agndar_unha(self):
        """
        TESTE REAL: "gstria de agndar unha para terç agora, teria?"

        Esperado:
        - Sistema não quebra
        - GPT é chamado (determinístico insuficiente)
        - Resultado é agendamento_direto (não consulta)
        - Serviço é resolvido (manicure, pedicure, ou indefinida se ambíguo)
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        # TESTE REAL
        resposta = await roteador_principal(
            user_id=actor_id,
            mensagem="gstria de agndar unha para terç agora, teria?",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        ctx = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print(f"\n[RESULTADO]")
        print(f"  intencao: {ctx.get('intencao_conversacional')}")
        print(f"  servico: {ctx.get('servico')}")
        print(f"  resposta: {resposta}")
        print(f"  estado_fluxo: {ctx.get('estado_fluxo')}")

        # Validações
        assert ctx.get("intencao_conversacional") is not None, "Intenção não foi detectada"
        assert ctx.get("intencao_conversacional") != "indefinida", \
            f"Esperava interpretação, got indefinida"

        # Se conseguiu identificar serviço
        if ctx.get("servico"):
            assert ctx.get("servico") in ["manicure", "pedicure"], \
                f"Serviço inesperado: {ctx.get('servico')}"

        print(f"✅ TESTE PASSOU", flush=True)

    @pytest.mark.asyncio
    async def test_msg_clara_para_comparacao(self):
        """
        Teste com mensagem CLARA (sem typos) para comparação

        "Quero agendar manicure para terça"
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080b"  # Actor diferente para não misturar

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        resposta = await roteador_principal(
            user_id=actor_id,
            mensagem="Quero agendar manicure para terça",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        ctx = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print(f"\n[COMPARAÇÃO - MENSAGEM CLARA]")
        print(f"  intencao: {ctx.get('intencao_conversacional')}")
        print(f"  servico: {ctx.get('servico')}")

        assert ctx.get("intencao_conversacional") == "agendamento_direto"
        assert ctx.get("servico") == "manicure"

        print(f"✅ TESTE PASSOU", flush=True)
