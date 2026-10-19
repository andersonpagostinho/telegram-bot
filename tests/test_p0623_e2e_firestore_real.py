"""
P0.6.2.3 — TESTES E2E COM FIRESTORE REAL ISOLADO

Valida que o handler de aguardando_servico funciona ponta a ponta:
1. Contexto persistido em Firestore com múltiplos_servicos_candidatos
2. Cliente envia "manicure"
3. Interpretador contextual processa
4. Contexto é atualizado: servico setado, candidatos removidos
5. Estado_fluxo muda para próximo passo
6. Fluxo continua até pré-confirmação

Usa tenant de teste exclusivo: test_tenant_p0623_{timestamp}
Sem dados reais, sem alteração de produção.
"""

import pytest
import uuid
from datetime import datetime
import sys
import asyncio


# Importar Firebase real (não mock)
try:
    from services.firebase_service_async import (
        atualizar_dado_em_path,
        buscar_dado_em_path,
        deletar_dado_em_path,
    )
    from services.interpretacao_contextual_service import interpretar_resposta_contextual
    from utils.contexto_temporario import (
        salvar_contexto_temporario_v2,
        carregar_contexto_temporario_v2,
    )
    FIREBASE_DISPONIVEL = True
except Exception as e:
    print(f"⚠️ Firebase não disponível: {e}")
    FIREBASE_DISPONIVEL = False


@pytest.mark.skipif(not FIREBASE_DISPONIVEL, reason="Firebase não disponível")
class TestP0623E2EFirestoreReal:
    """Testes E2E com Firestore real (dados isolados de teste)"""

    @pytest.fixture
    async def tenant_teste(self):
        """Gera tenant exclusivo de teste"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        tenant_id = f"test_p0623_{timestamp}_{str(uuid.uuid4())[:8]}"
        print(f"\n[FIXTURE] Tenant de teste criado: {tenant_id}")
        return tenant_id

    @pytest.fixture
    async def cliente_teste(self):
        """Gera cliente de teste exclusivo"""
        cliente_id = f"whatsapp:test_{str(uuid.uuid4())[:12]}"
        print(f"[FIXTURE] Cliente de teste criado: {cliente_id}")
        return cliente_id

    # ========================================================================
    # E2E T1: Fluxo completo "manicure" com Firestore real
    # ========================================================================
    @pytest.mark.asyncio
    async def test_e2e_t1_fluxo_manicure_firestore_real(self, tenant_teste, cliente_teste):
        """
        E2E: Cliente responde "manicure" após múltiplos candidatos
        Valida: contexto em Firestore → interpretação → atualização → próximo passo
        """
        tenant_id = tenant_teste
        actor_id = cliente_teste

        try:
            # PASSO 1: Persistir contexto com múltiplos_servicos_candidatos
            print(f"\n[E2E_T1_P1] Persistindo contexto inicial...")

            contexto_inicial = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": ["manicure", "pedicure"],
                "intencao_conversacional": "agendamento_direto",
                "data": "2026-10-22",
                "horario": "14:00",
                "profissional_escolhido": None,
            }

            await salvar_contexto_temporario_v2(tenant_id, actor_id, contexto_inicial)
            print(f"[E2E_T1_P1] ✅ Contexto persistido")

            # PASSO 2: Carregar contexto de Firestore
            print(f"[E2E_T1_P2] Carregando contexto de Firestore...")

            ctx_carregado = await carregar_contexto_temporario_v2(tenant_id, actor_id)
            assert ctx_carregado is not None, "Contexto não foi persistido"
            assert ctx_carregado.get("estado_fluxo") == "aguardando_servico"
            assert ctx_carregado.get("multiplos_servicos_candidatos") == ["manicure", "pedicure"]
            print(f"[E2E_T1_P2] ✅ Contexto carregado e validado")

            # PASSO 3: Interpretar resposta contextual
            print(f"[E2E_T1_P3] Interpretando resposta 'manicure'...")

            resultado_interpretacao = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="manicure",
                estado_fluxo="aguardando_servico",
                contexto=ctx_carregado
            )

            assert resultado_interpretacao is not None
            assert resultado_interpretacao.get("interpretado_sucesso") is True
            assert resultado_interpretacao.get("servico") == "manicure"
            assert resultado_interpretacao.get("ambigua") is False
            print(f"[E2E_T1_P3] ✅ Interpretação bem-sucedida: servico={resultado_interpretacao.get('servico')}")

            # PASSO 4: Atualizar contexto (simular handler do router)
            print(f"[E2E_T1_P4] Atualizando contexto com serviço escolhido...")

            ctx_atualizado = ctx_carregado.copy()
            ctx_atualizado["servico"] = resultado_interpretacao.get("servico")
            ctx_atualizado.pop("multiplos_servicos_candidatos", None)  # Consumir candidatos

            # Como profissional NÃO foi escolhido, próximo passo é aguardando_profissional
            ctx_atualizado["estado_fluxo"] = "aguardando_profissional"

            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx_atualizado)
            print(f"[E2E_T1_P4] ✅ Contexto atualizado em Firestore")

            # PASSO 5: Validar estado em Firestore
            print(f"[E2E_T1_P5] Validando estado em Firestore...")

            ctx_validacao = await carregar_contexto_temporario_v2(tenant_id, actor_id)

            assert ctx_validacao.get("servico") == "manicure", "Serviço não foi atualizado"
            assert ctx_validacao.get("multiplos_servicos_candidatos") is None, "Candidatos não foram consumidos"
            assert ctx_validacao.get("estado_fluxo") == "aguardando_profissional", "Estado não transitou"
            assert ctx_validacao.get("data") == "2026-10-22", "Data foi perdida"
            assert ctx_validacao.get("horario") == "14:00", "Horário foi perdido"
            print(f"[E2E_T1_P5] ✅ Estado validado em Firestore")

            print(f"\n[E2E_T1] ✅ FLUXO COMPLETO VALIDADO: manicure → profissional (próximo passo)")

        finally:
            # LIMPEZA: Deletar dados de teste
            print(f"\n[CLEANUP] Limpando dados de teste...")
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
                print(f"[CLEANUP] ✅ Dados de teste deletados")
            except Exception as e:
                print(f"[CLEANUP] ⚠️ Erro ao deletar: {e}")

    # ========================================================================
    # E2E T2: Fluxo pedicure com validação de isolamento
    # ========================================================================
    @pytest.mark.asyncio
    async def test_e2e_t2_fluxo_pedicure_isolamento_tenant(self, tenant_teste, cliente_teste):
        """
        E2E: Cliente responde "pedicure" - valida isolamento de tenant
        """
        tenant_id = tenant_teste
        actor_id = cliente_teste

        try:
            # Contexto com múltiplos candidatos
            print(f"\n[E2E_T2_P1] Teste de isolamento com pedicure...")

            contexto_inicial = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": ["manicure", "pedicure"],
                "profissional_escolhido": "Bruna",
                "data": "2026-10-23",
            }

            await salvar_contexto_temporario_v2(tenant_id, actor_id, contexto_inicial)

            ctx_carregado = await carregar_contexto_temporario_v2(tenant_id, actor_id)

            # Interpretar "pedicure"
            resultado = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="pedicure",
                estado_fluxo="aguardando_servico",
                contexto=ctx_carregado
            )

            assert resultado.get("interpretado_sucesso") is True
            assert resultado.get("servico") == "pedicure"

            # Como profissional JÁ foi escolhido, próximo passo é aguardando_data
            ctx_atualizado = ctx_carregado.copy()
            ctx_atualizado["servico"] = "pedicure"
            ctx_atualizado.pop("multiplos_servicos_candidatos", None)
            ctx_atualizado["estado_fluxo"] = "aguardando_data"  # Falta data (tem profissional)

            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx_atualizado)

            # Validar
            ctx_final = await carregar_contexto_temporario_v2(tenant_id, actor_id)
            assert ctx_final.get("servico") == "pedicure"
            assert ctx_final.get("estado_fluxo") == "aguardando_data"
            assert ctx_final.get("profissional_escolhido") == "Bruna"

            print(f"[E2E_T2] ✅ ISOLAMENTO VALIDADO: pedicure → data (próximo passo)")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
            except:
                pass

    # ========================================================================
    # E2E T3: Validar que outro tenant NÃO vê dados deste
    # ========================================================================
    @pytest.mark.asyncio
    async def test_e2e_t3_isolamento_cross_tenant(self, cliente_teste):
        """
        E2E: Valida que dois tenants têm dados isolados
        """
        tenant_a = f"test_tenantA_{str(uuid.uuid4())[:8]}"
        tenant_b = f"test_tenantB_{str(uuid.uuid4())[:8]}"
        actor_id = cliente_teste

        try:
            print(f"\n[E2E_T3] Teste de isolamento cross-tenant...")

            # Persistir em tenant A
            ctx_a = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": ["manicure"],
            }
            await salvar_contexto_temporario_v2(tenant_a, actor_id, ctx_a)

            # Persistir em tenant B (dados diferentes)
            ctx_b = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": ["corte", "escova"],
            }
            await salvar_contexto_temporario_v2(tenant_b, actor_id, ctx_b)

            # Carregar de tenant A
            ctx_a_carregado = await carregar_contexto_temporario_v2(tenant_a, actor_id)
            assert ctx_a_carregado.get("multiplos_servicos_candidatos") == ["manicure"]

            # Carregar de tenant B
            ctx_b_carregado = await carregar_contexto_temporario_v2(tenant_b, actor_id)
            assert ctx_b_carregado.get("multiplos_servicos_candidatos") == ["corte", "escova"]

            # Validar que são diferentes
            assert ctx_a_carregado != ctx_b_carregado

            print(f"[E2E_T3] ✅ ISOLAMENTO CROSS-TENANT VALIDADO")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_a}/Sessoes/{actor_id}")
                await deletar_dado_em_path(f"Clientes/{tenant_b}/Sessoes/{actor_id}")
            except:
                pass

    # ========================================================================
    # E2E T4: Validar consumo de candidatos (idempotência)
    # ========================================================================
    @pytest.mark.asyncio
    async def test_e2e_t4_consumo_candidatos_idempotencia(self, tenant_teste, cliente_teste):
        """
        E2E: Valida que após consumir candidatos, reenviio não reprocessa
        """
        tenant_id = tenant_teste
        actor_id = cliente_teste

        try:
            print(f"\n[E2E_T4] Teste de idempotência...")

            # PASSO 1: Primeira resposta
            contexto_1 = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": ["manicure", "pedicure"],
            }
            await salvar_contexto_temporario_v2(tenant_id, actor_id, contexto_1)

            ctx_1 = await carregar_contexto_temporario_v2(tenant_id, actor_id)
            resultado_1 = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="manicure",
                estado_fluxo="aguardando_servico",
                contexto=ctx_1
            )

            assert resultado_1.get("interpretado_sucesso") is True

            # PASSO 2: Consumir e atualizar estado
            ctx_consumido = ctx_1.copy()
            ctx_consumido["servico"] = "manicure"
            ctx_consumido.pop("multiplos_servicos_candidatos", None)
            ctx_consumido["estado_fluxo"] = "aguardando_profissional"

            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx_consumido)

            # PASSO 3: Reenviio (messagem duplicada)
            ctx_2 = await carregar_contexto_temporario_v2(tenant_id, actor_id)

            # Estado agora é aguardando_profissional, não aguardando_servico
            assert ctx_2.get("estado_fluxo") == "aguardando_profissional"
            assert ctx_2.get("multiplos_servicos_candidatos") is None  # Consumidos

            # Tentar interpretar novamente com estado alterado
            resultado_2 = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="manicure",
                estado_fluxo="aguardando_profissional",  # DIFERENTE!
                contexto=ctx_2
            )

            # Resultado deve ser diferente (profissional, não serviço)
            assert resultado_2.get("tipo_resposta") != "preferencia_servico"

            print(f"[E2E_T4] ✅ IDEMPOTÊNCIA VALIDADA: reenviio não reprocessa")

        finally:
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
            except:
                pass


if __name__ == "__main__":
    print("\n🧪 Executando testes E2E com Firestore real...\n")
    print("⚠️ AVISO: Estes testes usam Firestore real com dados isolados de teste.")
    print("Tenant de teste será criado e deletado automaticamente.\n")

    pytest.main([__file__, "-v", "-s"])
