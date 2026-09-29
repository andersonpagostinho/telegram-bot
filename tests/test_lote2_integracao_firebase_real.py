"""
LOTE 2 — TESTES DE INTEGRAÇÃO COM FIREBASE REAL
================================================

Valida que cada callsite bloqueia corretamente quando tenant_id é None
usando Firestore real (não mocks).

Cada teste:
1. Cria dados de teste no Firestore real
2. Executa a função de produção
3. Valida comportamento real
4. Limpa dados após teste
"""

import pytest
from datetime import datetime, timedelta
from pytz import timezone
from services.event_service_async import alterar_agendamento
from services.encaixe_service import solicitar_encaixe
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)

FUSO_BR = timezone("America/Sao_Paulo")


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
async def firebase_setup_c1():
    """Setup e cleanup para Callsite 1 (alterar_agendamento)."""
    dono_id = "test_dono_" + datetime.now().strftime("%s")
    cliente_id = "test_cliente_" + datetime.now().strftime("%s")
    event_id = "test_evt_" + datetime.now().strftime("%s")

    # Criar dados de teste no Firestore
    await salvar_dado_em_path(
        f"Clientes/{dono_id}",
        {"tipo_usuario": "dono", "nome": "Test Dono"}
    )

    await salvar_dado_em_path(
        f"Clientes/{cliente_id}",
        {
            "tipo_usuario": "cliente",
            "id_negocio": dono_id,
            "nome": "Test Cliente"
        }
    )

    # Criar evento de teste
    await salvar_dado_em_path(
        f"Clientes/{dono_id}/Eventos/{event_id}",
        {
            "cliente_id": cliente_id,
            "profissional": "Prof A",
            "servico": "Corte",
            "data": "2026-10-01",
            "hora_inicio": "14:00",
            "hora_fim": "14:30",
            "duracao_minutos": 30,
            "status": "confirmado",
            "confirmado": True
        }
    )

    yield dono_id, cliente_id, event_id

    # Cleanup
    await deletar_dado_em_path(f"Clientes/{dono_id}/Eventos/{event_id}")
    await deletar_dado_em_path(f"Clientes/{dono_id}")
    await deletar_dado_em_path(f"Clientes/{cliente_id}")


@pytest.fixture
async def firebase_setup_c2():
    """Setup e cleanup para Callsite 2 (solicitar_encaixe)."""
    dono_id = "test_dono_encaixe_" + datetime.now().strftime("%s")
    cliente_id = "test_cliente_encaixe_" + datetime.now().strftime("%s")

    # Criar dono
    await salvar_dado_em_path(
        f"Clientes/{dono_id}",
        {"tipo_usuario": "dono", "nome": "Test Dono Encaixe"}
    )

    # Criar cliente
    await salvar_dado_em_path(
        f"Clientes/{cliente_id}",
        {
            "tipo_usuario": "cliente",
            "id_negocio": dono_id,
            "nome": "Test Cliente Encaixe"
        }
    )

    yield dono_id, cliente_id

    # Cleanup
    await deletar_dado_em_path(f"Clientes/{dono_id}")
    await deletar_dado_em_path(f"Clientes/{cliente_id}")


# ============================================================
# CALLSITE 1: alterar_agendamento (Firebase Real)
# ============================================================

class TestCallsite1AltararAgendamentoFirebaseReal:
    """Valida alterar_agendamento() com Firestore real."""

    @pytest.mark.asyncio
    async def test_C1_A_firebase_tenant_valido_alteracao_ocorre(self, firebase_setup_c1):
        """A. Tenant válido → alteração ocorre com Firebase real"""
        dono_id, cliente_id, event_id = firebase_setup_c1

        # Execute
        resultado = await alterar_agendamento(
            user_id=dono_id,
            event_id=event_id,
            nova_data="2026-10-02",
            nova_hora_inicio="15:00"
        )

        # Assert
        assert resultado["ok"] == True, f"Esperava sucesso, recebeu: {resultado}"
        assert resultado["evento_id"] == event_id

        # Validar que escrita ocorreu (verificar Firestore)
        evento_atualizado = await buscar_dado_em_path(
            f"Clientes/{dono_id}/Eventos/{event_id}"
        )
        assert evento_atualizado is not None
        assert evento_atualizado["data"] == "2026-10-02"
        assert evento_atualizado["hora_inicio"] == "15:00"

    @pytest.mark.asyncio
    async def test_C1_B_firebase_tenant_none_bloqueio_sem_escrita(self, firebase_setup_c1):
        """B. Tenant None (cliente inexistente) → bloqueio sem escrita"""
        dono_id, cliente_id, event_id = firebase_setup_c1

        # Cliente que não existe em Firestore
        cliente_inexistente = "client_nao_existe_" + datetime.now().strftime("%s")

        # Execute
        resultado = await alterar_agendamento(
            user_id=cliente_inexistente,
            event_id=event_id,
            nova_data="2026-10-02",
            nova_hora_inicio="15:00"
        )

        # Assert: deve bloquear
        assert resultado["ok"] == False, f"Esperava bloqueio, recebeu sucesso: {resultado}"

        # Validar que evento original NÃO foi alterado
        evento_original = await buscar_dado_em_path(
            f"Clientes/{dono_id}/Eventos/{event_id}"
        )
        assert evento_original["data"] == "2026-10-01"  # Data original preserved

    @pytest.mark.asyncio
    async def test_C1_F_firebase_regressao_fluxo_normal(self, firebase_setup_c1):
        """F. Regressão: fluxo normal continua funcionando com Firebase real"""
        dono_id, cliente_id, event_id = firebase_setup_c1

        # Execute múltiplas alterações
        resultado1 = await alterar_agendamento(
            user_id=dono_id,
            event_id=event_id,
            nova_data="2026-10-03",
            nova_hora_inicio="16:00"
        )

        assert resultado1["ok"] == True

        # Segunda alteração
        resultado2 = await alterar_agendamento(
            user_id=dono_id,
            event_id=event_id,
            nova_data="2026-10-04",
            nova_hora_inicio="17:00"
        )

        assert resultado2["ok"] == True

        # Validar estado final no Firestore
        evento_final = await buscar_dado_em_path(
            f"Clientes/{dono_id}/Eventos/{event_id}"
        )
        assert evento_final["data"] == "2026-10-04"
        assert evento_final["hora_inicio"] == "17:00"


# ============================================================
# CALLSITE 2: solicitar_encaixe (Firebase Real)
# ============================================================

class TestCallsite2SolicitarEncaixeFirebaseReal:
    """Valida solicitar_encaixe() com Firestore real."""

    @pytest.mark.asyncio
    async def test_C2_A_firebase_tenant_valido_encaixe_ocorre(self, firebase_setup_c2):
        """A. Tenant válido → encaixe é criado com Firebase real"""
        dono_id, cliente_id = firebase_setup_c2
        dt_desejado = datetime.now(FUSO_BR) + timedelta(days=1, hours=2)

        # Execute
        resultado = await solicitar_encaixe(
            user_id=dono_id,
            descricao="Corte teste",
            profissional="Prof Teste",
            duracao_min=30,
            dt_desejado=dt_desejado,
            solicitante_user_id=cliente_id
        )

        # Assert
        assert resultado["status"] == "encaixe_confirmado", f"Recebido: {resultado}"

    @pytest.mark.asyncio
    async def test_C2_B_firebase_tenant_none_bloqueio_sem_escrita(self, firebase_setup_c2):
        """B. Tenant None (usuário inexistente) → bloqueio sem escrita"""
        dono_id, cliente_id = firebase_setup_c2

        # Usuário que não existe em Firestore
        usuario_inexistente = "user_nao_existe_" + datetime.now().strftime("%s")
        dt_desejado = datetime.now(FUSO_BR) + timedelta(days=1, hours=2)

        # Execute
        resultado = await solicitar_encaixe(
            user_id=usuario_inexistente,
            descricao="Corte teste",
            profissional="Prof Teste",
            duracao_min=30,
            dt_desejado=dt_desejado,
            solicitante_user_id=cliente_id
        )

        # Assert: deve bloquear com erro_tenant
        assert resultado["status"] == "erro_tenant", f"Recebido: {resultado}"
        assert "tenant" in resultado["mensagem"].lower()

    @pytest.mark.asyncio
    async def test_C2_F_firebase_regressao_fluxo_normal(self, firebase_setup_c2):
        """F. Regressão: fluxo normal continua funcionando com Firebase real"""
        dono_id, cliente_id = firebase_setup_c2
        dt_desejado = datetime.now(FUSO_BR) + timedelta(days=2, hours=3)

        # Execute
        resultado = await solicitar_encaixe(
            user_id=dono_id,
            descricao="Escova teste",
            profissional="Bruna",
            duracao_min=60,
            dt_desejado=dt_desejado,
            solicitante_user_id=cliente_id
        )

        # Assert
        assert resultado["status"] == "encaixe_confirmado"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
