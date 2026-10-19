"""
P0.6.2.3 — TESTES E2E SIMPLES COM FIRESTORE REAL

Validação ponta a ponta com dados reais em Firestore isolado.
"""

import pytest
import uuid
from datetime import datetime
from google.cloud import firestore


try:
    from services.firebase_service_async import buscar_dado_em_path, deletar_dado_em_path
    from services.interpretacao_contextual_service import interpretar_resposta_contextual
    from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2
    FIREBASE_OK = True
except Exception as e:
    print(f"Firebase import error: {e}")
    FIREBASE_OK = False


@pytest.mark.skipif(not FIREBASE_OK, reason="Firebase imports failed")
class TestP0623E2ESimples:
    """E2E com Firestore real"""

    @pytest.mark.asyncio
    async def test_e2e_manicure_ate_proxima_etapa(self):
        """
        E2E Completo:
        1. Persistir contexto com múltiplos_servicos_candidatos
        2. Carregar de Firestore
        3. Interpretar "manicure"
        4. Atualizar contexto (remover candidatos via DELETE_FIELD)
        5. Validar em Firestore
        """
        tenant_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
        actor_id = f"actor_{str(uuid.uuid4())[:8]}"

        try:
            print(f"\n[E2E] Teste ponta a ponta: {tenant_id}")

            # 1. Persistir contexto inicial
            print("[E2E] 1. Persistindo contexto com múltiplos candidatos...")
            contexto_1 = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": ["manicure", "pedicure"],
                "data": "2026-10-22",
            }
            await salvar_contexto_temporario_v2(tenant_id, actor_id, contexto_1)

            # 2. Carregar de Firestore
            print("[E2E] 2. Carregando de Firestore...")
            ctx_carregado = await carregar_contexto_temporario_v2(tenant_id, actor_id)
            assert ctx_carregado is not None
            assert ctx_carregado.get("estado_fluxo") == "aguardando_servico"
            assert "manicure" in ctx_carregado.get("multiplos_servicos_candidatos", [])
            print(f"[E2E] ✅ Contexto carregado: {len(ctx_carregado)} campos")

            # 3. Interpretar resposta
            print("[E2E] 3. Interpretando 'manicure'...")
            resultado = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="manicure",
                estado_fluxo="aguardando_servico",
                contexto=ctx_carregado
            )
            assert resultado.get("interpretado_sucesso") is True
            assert resultado.get("servico") == "manicure"
            print(f"[E2E] ✅ Interpretação: servico={resultado.get('servico')}")

            # 4. Atualizar contexto com DELETE_FIELD
            print("[E2E] 4. Atualizando contexto (DELETE_FIELD para candidatos)...")
            ctx_atualizado = {
                "servico": "manicure",
                "estado_fluxo": "aguardando_profissional",
                "multiplos_servicos_candidatos": firestore.DELETE_FIELD,
            }
            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx_atualizado)

            # 5. Validar em Firestore
            print("[E2E] 5. Validando em Firestore...")
            ctx_final = await carregar_contexto_temporario_v2(tenant_id, actor_id)

            assert ctx_final.get("servico") == "manicure", f"Serviço: {ctx_final.get('servico')}"
            assert ctx_final.get("estado_fluxo") == "aguardando_profissional", f"Estado: {ctx_final.get('estado_fluxo')}"
            assert "multiplos_servicos_candidatos" not in ctx_final or ctx_final.get("multiplos_servicos_candidatos") is None, \
                f"Candidatos não removidos: {ctx_final.get('multiplos_servicos_candidatos')}"
            assert ctx_final.get("data") == "2026-10-22", "Data perdida"

            print("[E2E] ✅ VALIDAÇÃO COMPLETA: manicure → profissional (próximo passo)")
            print(f"[E2E] Estado final: {ctx_final}")

        finally:
            print(f"[CLEANUP] Deletando dados de teste...")
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
                print("[CLEANUP] ✅ Limpeza concluída")
            except Exception as e:
                print(f"[CLEANUP] ⚠️ Erro: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
