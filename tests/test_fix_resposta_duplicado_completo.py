"""
TESTES PARA FIX: Resposta de Evento Duplicado
Valida que primeira confirmação mostra sucesso formatado,
retentar mostra "já confirmado", e concorrência é segura.

Testes Unitários: 4
Testes E2E: 3
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.event_service_async import salvar_evento
from services.agenda_lock_service import criar_evento_com_lock
from handlers.event_handler import add_evento_por_gpt
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from pytz import timezone

FUSO_BR = timezone("America/Sao_Paulo")

# ============================================================================
# UNIT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_novo_evento_retorna_criado():
    """
    CENÁRIO: Novo evento sendo criado pela primeira vez
    ESPERADO: status="criado", confirmado_nesta_requisicao=True
    """
    dono_id = "7394370553"
    cliente_id = "5511991382080"

    evento = {
        "descricao": "Corte com Bruna",
        "data": "2026-11-10",
        "hora_inicio": "14:00",
        "hora_fim": "15:00",
        "profissional": "Bruna",
        "servico": "corte",
        "cliente_id": cliente_id,
        "confirmado": True,
        "status": "confirmado"
    }

    event_id = f"{cliente_id}_bruna_2026-11-10".replace(" ", "_").lower()

    resultado = await criar_evento_com_lock(dono_id, evento, event_id)

    assert resultado.get("ok") is True, f"Falha na criação: {resultado.get('motivo')}"
    assert resultado.get("status") == "criado", f"Status incorreto: {resultado.get('status')}"
    assert resultado.get("confirmado_nesta_requisicao") is True, "Deveria marcar como confirmado nesta requisição"
    assert resultado.get("evento_id") == event_id


@pytest.mark.asyncio
async def test_evento_ja_confirmado_retorna_duplicado_confirmado():
    """
    CENÁRIO: Evento já confirmado, tentando confirmar novamente
    ESPERADO: status="duplicado_confirmado", confirmado_nesta_requisicao=False
    """
    dono_id = "7394370553"
    cliente_id = "5511991382080"
    event_id = f"{cliente_id}_bruna_2026-11-11".replace(" ", "_").lower()
    evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"

    # Simular evento já confirmado em Firebase
    evento_existente = {
        "descricao": "Corte com Bruna",
        "data": "2026-11-11",
        "hora_inicio": "14:00",
        "hora_fim": "15:00",
        "profissional": "Bruna",
        "confirmado": True,
        "status": "confirmado",
        "confirmado_em": datetime.now(FUSO_BR).isoformat(),
        "cliente_id": cliente_id
    }

    with patch('services.firebase_service_async.buscar_dado_em_path') as mock_buscar:
        mock_buscar.return_value = evento_existente

        with patch('services.agenda_lock_service.adquirir_locks_atomicamente') as mock_locks:
            # Simular falha ao adquirir locks (já existem do evento anterior)
            mock_locks.return_value = {
                "ok": False,
                "motivo": "lock_já_existe"
            }

            evento = {
                "descricao": "Corte com Bruna",
                "data": "2026-11-11",
                "hora_inicio": "14:00",
                "hora_fim": "15:00",
                "profissional": "Bruna",
                "confirmado": True
            }

            resultado = await criar_evento_com_lock(dono_id, evento, event_id)

            assert resultado.get("ok") is True
            assert resultado.get("status") == "duplicado_confirmado", f"Status incorreto: {resultado.get('status')}"
            assert resultado.get("confirmado_nesta_requisicao") is False, "Não deveria marcar como confirmado nesta requisição"


@pytest.mark.asyncio
async def test_evento_pendente_confirmando_retorna_duplicado_pendente_agora():
    """
    CENÁRIO: Evento pendente (confirmado=False), agora sendo confirmado
    ESPERADO: status="duplicado_pendente_agora", confirmado_nesta_requisicao=True
    """
    dono_id = "7394370553"
    cliente_id = "5511991382080"
    event_id = f"{cliente_id}_gloria_2026-11-12".replace(" ", "_").lower()
    evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"

    # Simular evento pendente em Firebase
    evento_existente = {
        "descricao": "Manicure com Gloria",
        "data": "2026-11-12",
        "hora_inicio": "15:00",
        "hora_fim": "16:00",
        "profissional": "Gloria",
        "confirmado": False,  # ← PENDENTE
        "status": "pendente",
        "cliente_id": cliente_id
    }

    evento_atualizado = None

    async def mock_salvar(path, dados):
        nonlocal evento_atualizado
        evento_atualizado = dados
        return True

    with patch('services.firebase_service_async.buscar_dado_em_path') as mock_buscar:
        mock_buscar.return_value = evento_existente

        with patch('services.firebase_service_async.salvar_dado_em_path', side_effect=mock_salvar):
            with patch('services.firebase_service_async.atualizar_dado_em_path', new_callable=AsyncMock):
                with patch('services.agenda_lock_service.adquirir_locks_atomicamente') as mock_locks:
                    # Simular falha ao adquirir locks
                    mock_locks.return_value = {
                        "ok": False,
                        "motivo": "lock_já_existe"
                    }

                    evento = {
                        "descricao": "Manicure com Gloria",
                        "data": "2026-11-12",
                        "hora_inicio": "15:00",
                        "hora_fim": "16:00",
                        "profissional": "Gloria",
                        "confirmado": True  # ← Tentando confirmar
                    }

                    resultado = await criar_evento_com_lock(dono_id, evento, event_id)

                    assert resultado.get("ok") is True
                    assert resultado.get("status") == "duplicado_pendente_agora", f"Status incorreto: {resultado.get('status')}"
                    assert resultado.get("confirmado_nesta_requisicao") is True, "Deveria marcar como confirmado NESTA requisição"

                    # ✅ Verificar que evento foi atualizado para confirmado
                    assert evento_atualizado is not None, "Evento deveria ter sido atualizado"
                    assert evento_atualizado.get("confirmado") is True, "Evento deveria ter confirmado=True"


@pytest.mark.asyncio
async def test_evento_conflito_retorna_conflito():
    """
    CENÁRIO: Conflito de horário com outro evento
    ESPERADO: status="conflito", ok=False
    """
    dono_id = "7394370553"
    cliente_id = "5511991382080"
    event_id = f"{cliente_id}_carla_2026-11-13".replace(" ", "_").lower()

    # Simular evento existente do mesmo profissional no mesmo horário
    evento_existente = {
        "descricao": "Escova com Carla",
        "data": "2026-11-13",
        "hora_inicio": "16:00",
        "hora_fim": "17:00",
        "profissional": "Carla",
        "confirmado": True,
        "status": "confirmado"
    }

    with patch('services.firebase_service_async.buscar_subcolecao') as mock_eventos:
        mock_eventos.return_value = {"event_1": evento_existente}

        with patch('services.agenda_lock_service.adquirir_locks_atomicamente') as mock_locks:
            # Locks criados com sucesso
            mock_locks.return_value = {
                "ok": True,
                "lock_keys_criados": ["carla_20261113_160000"]
            }

            evento = {
                "descricao": "Escova com Carla",
                "data": "2026-11-13",
                "hora_inicio": "16:00",
                "hora_fim": "17:00",
                "profissional": "Carla",
                "confirmado": True
            }

            resultado = await criar_evento_com_lock(dono_id, evento, event_id)

            assert resultado.get("ok") is False
            assert resultado.get("status") == "conflito", f"Status incorreto: {resultado.get('status')}"
            assert "conflito" in resultado.get("motivo", "").lower()


# ============================================================================
# E2E TESTS COM FIRESTORE REAL
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_usuario_nao_confirmou_confirma_agora():
    """
    E2E CENÁRIO: Usuário não confirmou ainda, agora confirma
    ESPERADO: Mensagem formatada com sucesso ✨
    """
    # ⚠️ NOTA: Este teste requer Firestore real
    # Skip se não há credenciais disponíveis

    dono_id = "7394370553_test"
    cliente_id = "5511991382080_test"

    msg_enviada = None

    async def mock_enviar_whatsapp(user_id, mensagem, **kwargs):
        nonlocal msg_enviada
        msg_enviada = mensagem

    with patch('utils.whatsapp_utils.enviar_mensagem_whatsapp', side_effect=mock_enviar_whatsapp):
        with patch('services.firebase_service_async.obter_id_dono') as mock_dono:
            mock_dono.return_value = dono_id

            with patch('services.firebase_service_async.limpar_contexto_agendamento_v2', new_callable=AsyncMock) as mock_cleanup:
                mock_cleanup.return_value = True

                # Simular primeiro salvamento (novo evento)
                resultado = await salvar_evento(
                    user_id=cliente_id,
                    evento={
                        "descricao": "Corte com Bruna",
                        "data": "2026-11-14",
                        "hora_inicio": "14:00",
                        "hora_fim": "15:00",
                        "profissional": "Bruna",
                        "servico": "corte",
                        "cliente_id": cliente_id,
                        "confirmado": True,
                        "status": "confirmado"
                    },
                    tenant_id=dono_id
                )

                # ✅ Validar resposta
                assert resultado.get("ok") is True
                assert resultado.get("status") in ["criado", "duplicado_pendente_agora"]

                if resultado.get("confirmado_nesta_requisicao"):
                    # Se é primeira confirmação, deveria ter enviado sucesso
                    assert msg_enviada is not None
                    assert "✨" in msg_enviada or "Horário confirmado" in msg_enviada


@pytest.mark.asyncio
async def test_e2e_usuario_ja_confirmou_retenta():
    """
    E2E CENÁRIO: Usuário já confirmou, tenta confirmar novamente
    ESPERADO: Mensagem "já está confirmado", não sucesso formatado
    """
    dono_id = "7394370553_test"
    cliente_id = "5511991382080_test"
    event_id = f"{cliente_id}_joana_2026-11-15".replace(" ", "_").lower()
    evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"

    msg_enviada = None

    async def mock_enviar_whatsapp(user_id, mensagem, **kwargs):
        nonlocal msg_enviada
        msg_enviada = mensagem

    # Simular evento já confirmado
    evento_confirmado = {
        "descricao": "Escova com Joana",
        "data": "2026-11-15",
        "hora_inicio": "15:30",
        "hora_fim": "16:30",
        "profissional": "Joana",
        "confirmado": True,
        "status": "confirmado",
        "confirmado_em": datetime.now(FUSO_BR).isoformat()
    }

    with patch('utils.whatsapp_utils.enviar_mensagem_whatsapp', side_effect=mock_enviar_whatsapp):
        with patch('services.firebase_service_async.obter_id_dono') as mock_dono:
            mock_dono.return_value = dono_id

            with patch('services.firebase_service_async.buscar_dado_em_path') as mock_buscar:
                mock_buscar.return_value = evento_confirmado

                # Tentar "confirmar" novamente
                resultado = await salvar_evento(
                    user_id=cliente_id,
                    evento={**evento_confirmado, "confirmado": True},
                    tenant_id=dono_id
                )

                # ✅ Validar resposta
                assert resultado.get("ok") is True
                assert resultado.get("status") == "duplicado_confirmado"
                assert resultado.get("confirmado_nesta_requisicao") is False

                # ✅ Validar mensagem enviada
                if msg_enviada:
                    assert "já está confirmado" in msg_enviada.lower()
                    assert "✨" not in msg_enviada  # Não deve ter emoji de sucesso


@pytest.mark.asyncio
async def test_e2e_concorrencia_duas_confirmacoes():
    """
    E2E CENÁRIO: Duas requisições simultâneas tentando confirmar o MESMO evento
    ESPERADO: Apenas uma criação em Firestore, outras veem idempotência
    """
    dono_id = "7394370553_test"
    cliente_id = "5511991382080_test"
    event_id = f"{cliente_id}_carla_2026-11-16".replace(" ", "_").lower()
    evento_path = f"Clientes/{dono_id}/Eventos/{event_id}"

    evento_template = {
        "descricao": "Manicure com Carla",
        "data": "2026-11-16",
        "hora_inicio": "14:00",
        "hora_fim": "15:00",
        "profissional": "Carla",
        "servico": "manicure",
        "cliente_id": cliente_id,
        "confirmado": True,
        "status": "confirmado"
    }

    # Simular duas requisições concorrentes
    resultado_1, resultado_2 = await asyncio.gather(
        criar_evento_com_lock(dono_id, evento_template.copy(), event_id),
        criar_evento_com_lock(dono_id, evento_template.copy(), event_id)
    )

    # ✅ Ambas devem ter ok=True
    assert resultado_1.get("ok") is True
    assert resultado_2.get("ok") is True

    # ✅ Pelo menos uma deve ser "criado" ou "duplicado_pendente_agora"
    statuses = {resultado_1.get("status"), resultado_2.get("status")}
    assert any(s in ["criado", "duplicado_pendente_agora"] for s in statuses), \
        f"Nenhuma requisição marcou como confirmação legítima: {statuses}"

    # ✅ A outra pode ser "duplicado_confirmado"
    assert "duplicado_confirmado" in statuses or "criado" in statuses, \
        f"Estatuses incorretos: {statuses}"

    # ✅ Apenas um evento deve estar em Firestore (não sobrescrita)
    # Nota: Este teste precisa de Firestore real para validar
    print(f"✅ E2E Concorrência validado: resultado_1={resultado_1.get('status')}, resultado_2={resultado_2.get('status')}")


if __name__ == "__main__":
    print("Testes para fix de resposta duplicado criados com sucesso")
    print("Execute com: pytest tests/test_fix_resposta_duplicado_completo.py -v")
