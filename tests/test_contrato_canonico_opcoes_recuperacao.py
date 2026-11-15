"""
Test: Contrato Canônico — Preservação de contexto_resultado_consulta

Valida que quando informacao_service persiste opcoes para Firestore,
eles não são perdidos por sobrescrita com versão vazia do ctx.

Cenário:
1. informacao_service.py chama persistir_resultado_consulta() → escreve opcoes em Firestore
2. responder_consulta_informativa() retorna, ctx ainda tem contexto_resultado_consulta: {} (carregado no router start)
3. salvar_contexto_temporario_v2() merges ctx com Firestore
4. FIX: preserva opcoes de Firestore em vez de sobrescrever com vazio
"""

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from utils.contexto_temporario import salvar_contexto_temporario_v2
from services.firebase_service_async import buscar_dado_em_path, atualizar_dado_em_path


@pytest.fixture
def opcoes_mock():
    """Opções de horário que teriam sido persistidas por informacao_service"""
    return [
        {
            "opcao_id": "opt_1",
            "data_hora": "2026-11-15",
            "inicio": "14:00",
            "fim": "15:20",
            "profissional": "Bruna",
            "servicos": ["manicure", "pedicure"],
            "duracao_total": 80,
            "timestamp_criacao": datetime.now().isoformat(),
            "ttl_segundos": 300
        },
        {
            "opcao_id": "opt_2",
            "data_hora": "2026-11-15",
            "inicio": "15:30",
            "fim": "16:50",
            "profissional": "Bruna",
            "servicos": ["manicure", "pedicure"],
            "duracao_total": 80,
            "timestamp_criacao": datetime.now().isoformat(),
            "ttl_segundos": 300
        },
        {
            "opcao_id": "opt_3",
            "data_hora": "2026-11-15",
            "inicio": "17:00",
            "fim": "18:20",
            "profissional": "Bruna",
            "servicos": ["manicure", "pedicure"],
            "duracao_total": 80,
            "timestamp_criacao": datetime.now().isoformat(),
            "ttl_segundos": 300
        }
    ]


@pytest.mark.asyncio
async def test_preservacao_opcoes_apos_merge(opcoes_mock):
    """
    Teste A: Verifica que contexto_resultado_consulta com opcoes é preservado
    quando ctx tem versão vazia e merge acontece.
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # CENÁRIO 1: Firestore já tem resultado com opcoes (persistidas por informacao_service)
    firestore_state = {
        "contexto_resultado_consulta": {
            "opcoes": opcoes_mock,
            "profissional_id": "Bruna",
            "duracao_total_min": 80,
            "timestamp_resultado": datetime.now().isoformat(),
        },
        "contexto_consulta": {
            "servicos_multiplos": ["manicure", "pedicure"],
            "intervalo_inicio": 14,
            "intervalo_fim": 17,
        },
        "estado_fluxo": "aguardando_selecao",
        "timestamp": datetime.now().isoformat(),
    }

    # Mock Firestore read to return opcoes
    with patch('utils.contexto_temporario.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = firestore_state

        # CENÁRIO 2: ctx (carregado no router start) tem contexto_resultado_consulta vazio
        # (porque foi inicializado antes de responder_consulta_informativa rodar)
        ctx = {
            "contexto_resultado_consulta": {},  # VAZIO — seria sobrescrito sem o fix!
            "contexto_consulta": firestore_state["contexto_consulta"],
            "estado_fluxo": "aguardando_selecao",
        }

        with patch('utils.contexto_temporario.atualizar_dado_em_path', new_callable=AsyncMock) as mock_atualizar:
            mock_atualizar.return_value = True

            # Chamar merge
            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx)

            # Verificar que atualizar_dado_em_path foi chamado com opcoes preservadas
            mock_atualizar.assert_called_once()
            args = mock_atualizar.call_args

            # O argumento final (dados salvos) deve ter opcoes
            saved_data = args[0][1]
            assert "contexto_resultado_consulta" in saved_data
            assert "opcoes" in saved_data["contexto_resultado_consulta"]
            assert len(saved_data["contexto_resultado_consulta"]["opcoes"]) == 3

            # Verificar que IDs das opcoes estão preservadas
            saved_opcoes = saved_data["contexto_resultado_consulta"]["opcoes"]
            saved_ids = [opt["opcao_id"] for opt in saved_opcoes]
            assert saved_ids == ["opt_1", "opt_2", "opt_3"]

            print(f"✅ Teste A PASS: {len(saved_opcoes)} opcoes preservadas após merge")


@pytest.mark.asyncio
async def test_merge_quando_ctx_tem_opcoes_atualizadas(opcoes_mock):
    """
    Teste B: Quando ctx foi ATUALIZADO com opcoes novas (pelo responder_consulta_informativa),
    elas não devem ser sobrescritas.
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # CENÁRIO: ctx foi atualizado por responder_consulta_informativa
    opcoes_nova = [opt.copy() for opt in opcoes_mock[:2]]  # Apenas 2 opcoes

    firestore_state = {
        "contexto_resultado_consulta": {
            "opcoes": opcoes_mock,  # 3 opcoes antigas em Firestore
        },
    }

    ctx = {
        "contexto_resultado_consulta": {
            "opcoes": opcoes_nova,  # 2 opcoes novas no ctx
        },
    }

    with patch('utils.contexto_temporario.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = firestore_state

        with patch('utils.contexto_temporario.atualizar_dado_em_path', new_callable=AsyncMock) as mock_atualizar:
            mock_atualizar.return_value = True

            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx)

            saved_data = mock_atualizar.call_args[0][1]
            saved_opcoes = saved_data["contexto_resultado_consulta"]["opcoes"]

            # Deve manter as 2 opcoes novas, não as 3 antigas
            assert len(saved_opcoes) == 2
            print(f"✅ Teste B PASS: 2 opcoes novas mantidas (não sobrescritas por Firestore)")


@pytest.mark.asyncio
async def test_merge_quando_firestore_vazio():
    """
    Teste C: Quando Firestore não tem opcoes, ctx é preservado normalmente.
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    firestore_state = {
        "contexto_resultado_consulta": {},  # Vazio em Firestore
    }

    ctx = {
        "contexto_resultado_consulta": {
            "opcoes": [{"opcao_id": "opt_X"}]
        },
    }

    with patch('utils.contexto_temporario.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar:
        mock_buscar.return_value = firestore_state

        with patch('utils.contexto_temporario.atualizar_dado_em_path', new_callable=AsyncMock) as mock_atualizar:
            mock_atualizar.return_value = True

            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx)

            saved_data = mock_atualizar.call_args[0][1]
            saved_opcoes = saved_data["contexto_resultado_consulta"]["opcoes"]

            # Deve manter a opcao do ctx
            assert len(saved_opcoes) == 1
            assert saved_opcoes[0]["opcao_id"] == "opt_X"
            print(f"✅ Teste C PASS: Opcoes do ctx preservadas quando Firestore vazio")
