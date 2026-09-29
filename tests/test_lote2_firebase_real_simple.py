"""
LOTE 2 — TESTES FIREBASE REAL (SIMPLES)
========================================

Validação direta com Firestore real, sem complexidade de fixtures async.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from pytz import timezone
import time
from services.event_service_async import alterar_agendamento
from services.encaixe_service import solicitar_encaixe
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)

FUSO_BR = timezone("America/Sao_Paulo")


async def setup_c1():
    """Criar dados de teste para Callsite 1."""
    ts = int(time.time())
    dono_id = f"test_dono_{ts}"
    cliente_id = f"test_cliente_{ts}"
    event_id = f"test_evt_{ts}"

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

    return dono_id, cliente_id, event_id


async def cleanup_c1(dono_id, cliente_id, event_id):
    """Limpar dados de teste Callsite 1."""
    await deletar_dado_em_path(f"Clientes/{dono_id}/Eventos/{event_id}")
    await deletar_dado_em_path(f"Clientes/{dono_id}")
    await deletar_dado_em_path(f"Clientes/{cliente_id}")


async def setup_c2():
    """Criar dados de teste para Callsite 2."""
    ts = int(time.time())
    dono_id = f"test_dono_encaixe_{ts}"
    cliente_id = f"test_cliente_encaixe_{ts}"

    await salvar_dado_em_path(
        f"Clientes/{dono_id}",
        {"tipo_usuario": "dono", "nome": "Test Dono Encaixe"}
    )

    await salvar_dado_em_path(
        f"Clientes/{cliente_id}",
        {
            "tipo_usuario": "cliente",
            "id_negocio": dono_id,
            "nome": "Test Cliente Encaixe"
        }
    )

    return dono_id, cliente_id


async def cleanup_c2(dono_id, cliente_id):
    """Limpar dados de teste Callsite 2."""
    await deletar_dado_em_path(f"Clientes/{dono_id}")
    await deletar_dado_em_path(f"Clientes/{cliente_id}")


# ============================================================
# CALLSITE 1: alterar_agendamento (Firebase Real)
# ============================================================

class TestCallsite1AltararAgendamentoFirebaseReal:
    """Valida alterar_agendamento() com Firestore real."""

    @pytest.mark.asyncio
    async def test_C1_A_firebase_tenant_valido_alteracao_ocorre(self):
        """A. Tenant válido → alteração ocorre com Firebase real"""
        dono_id, cliente_id, event_id = await setup_c1()

        try:
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
            print("[PASS] Teste C1_A: Alteração com tenant válido funcionou")

        finally:
            await cleanup_c1(dono_id, cliente_id, event_id)

    @pytest.mark.asyncio
    async def test_C1_B_firebase_tenant_none_bloqueio_sem_escrita(self):
        """B. Tenant None (cliente inexistente) → bloqueio sem escrita"""
        dono_id, cliente_id, event_id = await setup_c1()

        try:
            # Cliente que não existe em Firestore
            cliente_inexistente = f"client_nao_existe_{int(time.time())}"

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
            print("[PASS] Teste C1_B: Bloqueio com tenant None funcionou")

        finally:
            await cleanup_c1(dono_id, cliente_id, event_id)

    @pytest.mark.asyncio
    async def test_C1_F_firebase_regressao_fluxo_normal(self):
        """F. Regressão: fluxo normal continua funcionando com Firebase real"""
        dono_id, cliente_id, event_id = await setup_c1()

        try:
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
            print("[PASS] Teste C1_F: Regressão do fluxo normal funcionou")

        finally:
            await cleanup_c1(dono_id, cliente_id, event_id)


# ============================================================
# CALLSITE 2: solicitar_encaixe (Firebase Real)
# ============================================================

class TestCallsite2SolicitarEncaixeFirebaseReal:
    """Valida solicitar_encaixe() com Firestore real."""

    @pytest.mark.asyncio
    async def test_C2_A_firebase_tenant_valido_encaixe_ocorre(self):
        """A. Tenant válido → encaixe é criado com Firebase real"""
        dono_id, cliente_id = await setup_c2()

        try:
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
            print("[PASS] Teste C2_A: Encaixe com tenant válido funcionou")

        finally:
            await cleanup_c2(dono_id, cliente_id)

    @pytest.mark.asyncio
    async def test_C2_B_firebase_tenant_none_bloqueio_sem_escrita(self):
        """B. Tenant None (usuário inexistente) → bloqueio sem escrita"""
        dono_id, cliente_id = await setup_c2()

        try:
            # Usuário que não existe em Firestore
            usuario_inexistente = f"user_nao_existe_{int(time.time())}"
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
            print("[PASS] Teste C2_B: Bloqueio com tenant None funcionou")

        finally:
            await cleanup_c2(dono_id, cliente_id)

    @pytest.mark.asyncio
    async def test_C2_F_firebase_regressao_fluxo_normal(self):
        """F. Regressão: fluxo normal continua funcionando com Firebase real"""
        dono_id, cliente_id = await setup_c2()

        try:
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
            print("[PASS] Teste C2_F: Regressão do fluxo normal funcionou")

        finally:
            await cleanup_c2(dono_id, cliente_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
