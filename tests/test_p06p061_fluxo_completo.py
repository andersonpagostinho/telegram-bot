"""
TESTE COMPLETO P0.6 + P0.6.1 — Fluxo sequencial com mudança de serviço
"""

import pytest
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


class TestP06P061FluxoCompleto:
    """Teste sequencial com P0.6 + P0.6.1"""

    @pytest.mark.asyncio
    async def test_mudanca_servico_completa(self):
        """
        Teste completo: MSG1 corte → MSG2 manicure (sem typos para isolate P0.6.1)

        MSG2: "Quero manicure para terça, teria?"

        Com P0.6.1, deve ser classificado como agendamento_direto
        Com P0.6, extrair_slots_e_mesclar busca novo serviço
        Resultado: servico muda para "manicure" (ou None se não encontrado, mas não "corte")
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        # MSG 1: Corte
        await roteador_principal(
            user_id=actor_id,
            mensagem="Quero corte para terça",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        ctx1 = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
        assert ctx1.get("servico") == "corte feminino"
        assert ctx1.get("intencao_conversacional") == "agendamento_direto"
        print(f"✅ MSG1: servico={ctx1.get('servico')} | intencao={ctx1.get('intencao_conversacional')}", flush=True)

        # MSG 2: Muda para manicure (SEM TYPOS para testar P0.6.1)
        await roteador_principal(
            user_id=actor_id,
            mensagem="Quero manicure para terça, teria?",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        ctx2 = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print(f"✅ MSG2: servico={ctx2.get('servico')} | intencao={ctx2.get('intencao_conversacional')}", flush=True)

        # Validações P0.6.1
        assert ctx2.get("intencao_conversacional") == "agendamento_direto", \
            f"P0.6.1 FALHOU: Intenção reclassificada para {ctx2.get('intencao_conversacional')}"

        # Validações P0.6
        assert ctx2.get("servico") != "corte feminino", \
            f"P0.6 FALHOU: Serviço anterior não foi alterado!"

        assert ctx2.get("servico") in ["manicure", None], \
            f"P0.6: Esperava manicure ou None, got {ctx2.get('servico')}"

        print(f"✅ FLUXO COMPLETO: P0.6 + P0.6.1 funcionando!", flush=True)
