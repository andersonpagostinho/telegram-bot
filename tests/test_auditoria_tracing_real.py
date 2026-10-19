"""
AUDITORIA: Rastreamento real de chamadas ao GPT (sem mocks)

Usar print statements e logs para auditar fluxo real
"""

import pytest
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


class TestAuditoriaTracingReal:
    """Rastreamento real sem mocks"""

    @pytest.mark.asyncio
    async def test_tracing_mensagem_typo_real(self):
        """
        Rastrear fluxo real da mensagem com typos
        Verificar se GPT é acionado, quando e por que
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        print("\n" + "="*80)
        print("[AUDITORIA] Executando mensagem com typos SEM mock")
        print("Mensagem: 'ola, gstria de agndar unha para terç agora, tedia?'")
        print("="*80)

        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="ola, gstria de agndar unha para terç agora, tedia?",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print("\n" + "="*80)
        print("[AUDITORIA] Resultado Final")
        print("="*80)
        print(f"Intenção conversacional: {sessao.get('intencao_conversacional')}")
        print(f"Estado fluxo: {sessao.get('estado_fluxo')}")
        print(f"Resposta: {resultado.get('resposta', '')[:100] if isinstance(resultado, dict) else resultado[:100]}")
        print("="*80)

    @pytest.mark.asyncio
    async def test_tracing_mensagem_valida_real(self):
        """
        Rastrear fluxo de mensagem válida (sem typos)
        Verificar se GPT é acionado ou não
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        print("\n" + "="*80)
        print("[AUDITORIA] Executando mensagem válida SEM mock")
        print("Mensagem: 'Quero agendar corte feminino para terça-feira às 14h'")
        print("="*80)

        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="Quero agendar corte feminino para terça-feira às 14h",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print("\n" + "="*80)
        print("[AUDITORIA] Resultado Final")
        print("="*80)
        print(f"Intenção conversacional: {sessao.get('intencao_conversacional')}")
        print(f"Estado fluxo: {sessao.get('estado_fluxo')}")
        print(f"Resposta: {resultado.get('resposta', '')[:100] if isinstance(resultado, dict) else resultado[:100]}")
        print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
