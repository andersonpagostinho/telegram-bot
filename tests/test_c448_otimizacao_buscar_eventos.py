"""
C4.4.8 — Testes: Otimização buscar_eventos_por_intervalo

Validar que:
1. eventos_disponiveis=None mantém comportamento original (fallback Firestore)
2. eventos_disponiveis=[...] funciona sem chamar Firestore
3. Resultado é equivalente em ambos casos
4. Não há redundância de leitura quando lista é fornecida
"""

import pytest
import asyncio
from datetime import datetime, timedelta, date
import pytz
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recorrencia_service import _gerar_3_horarios_livres

FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC448OtimizacaoBuscarEventos:
    """Validar otimização de _gerar_3_horarios_livres com eventos pré-carregados"""

    @pytest.mark.asyncio
    async def test_T1_fallback_firestore(self):
        """T1: eventos_disponiveis=None usa buscar_eventos_por_intervalo (original)"""
        print("\n[T1] Fallback Firestore (eventos_disponiveis=None)")

        user_id = "test_user_fallback"
        data_alvo = datetime.now(FUSO_BR).date() + timedelta(days=10)

        # Mock de buscar_eventos_por_intervalo retornando eventos do dia
        mock_eventos_dia = [
            {
                "data": data_alvo.isoformat(),
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "cliente_id": "cli_1",
                "descricao": "corte",
                "profissional": "João",
                "status": "confirmado"
            }
        ]

        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', new_callable=AsyncMock) as mock_buscar:
            mock_buscar.return_value = mock_eventos_dia

            # Chamar SEM fornecer eventos_disponiveis (usa fallback)
            horarios = await _gerar_3_horarios_livres(
                user_id=user_id,
                data_sugerida=data_alvo,
                servico_chave="manicure",
                profissional=None,
                duracao_min=30,
                eventos_disponiveis=None  # ← Fallback Firestore
            )

            # Assert
            assert isinstance(horarios, list), "[FAIL T1] Retorno não é lista"
            assert len(horarios) >= 0, "[FAIL T1] Lista vazia ou negativa"
            mock_buscar.assert_called_once()  # Verifica que Firestore foi chamado

            print(f"  [OK T1] Fallback Firestore funcionando: {len(horarios)} horários encontrados")

    @pytest.mark.asyncio
    async def test_T2_lista_precarga_sem_firestore(self):
        """T2: eventos_disponiveis=[...] funciona sem Firestore"""
        print("\n[T2] Lista pré-carregada (sem Firestore)")

        user_id = "test_user_lista"
        data_alvo = datetime(2026, 10, 15).date()

        # Eventos disponíveis em memória
        eventos_disponiveis = [
            {
                "data": data_alvo.isoformat(),
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "cliente_id": "cli_1",
                "descricao": "corte",
                "profissional": "Prof1",
                "status": "confirmado"
            },
            {
                "data": data_alvo.isoformat(),
                "hora_inicio": "14:00",
                "hora_fim": "15:00",
                "cliente_id": "cli_2",
                "descricao": "escova",
                "profissional": "Prof2",
                "status": "confirmado"
            },
            {
                "data": (data_alvo - timedelta(days=1)).isoformat(),  # Dia anterior
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "cliente_id": "cli_3",
                "descricao": "manicure",
                "profissional": "Prof3",
                "status": "confirmado"
            }
        ]

        # Mock Firestore para falhar se chamado
        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', new_callable=AsyncMock) as mock_buscar:
            mock_buscar.side_effect = Exception("buscar_eventos_por_intervalo foi chamada! (redundância)")

            # Chamar COM eventos_disponiveis (não deve chamar Firestore)
            horarios = await _gerar_3_horarios_livres(
                user_id=user_id,
                data_sugerida=data_alvo,
                servico_chave="teste",
                profissional=None,
                duracao_min=30,
                eventos_disponiveis=eventos_disponiveis  # ← Lista pré-carregada
            )

            # Assert
            assert isinstance(horarios, list), "[FAIL T2] Retorno não é lista"
            mock_buscar.assert_not_called(), "[FAIL T2] Firestore foi chamado (redundância não eliminada)"

            print(f"  [OK T2] Lista pré-carregada sem redundância: {len(horarios)} horários encontrados")

    @pytest.mark.asyncio
    async def test_T3_equivalencia_resultado(self):
        """T3: Resultado com lista pré-carregada == resultado Firestore"""
        print("\n[T3] Equivalência de resultado")

        user_id = "test_user_equivalencia"
        data_alvo = datetime.now(FUSO_BR).date() + timedelta(days=15)

        # Cenário: 2 eventos ocupando alguns horários
        eventos_firestore = [
            {
                "data": data_alvo.isoformat(),
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "cliente_id": "cli_1",
                "descricao": "corte",
                "profissional": "Prof1",
                "status": "confirmado"
            },
            {
                "data": data_alvo.isoformat(),
                "hora_inicio": "14:00",
                "hora_fim": "15:00",
                "cliente_id": "cli_2",
                "descricao": "escova",
                "profissional": "Prof2",
                "status": "confirmado"
            }
        ]

        # Caminho 1: Via Firestore
        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', new_callable=AsyncMock) as mock_buscar:
            mock_buscar.return_value = eventos_firestore

            resultado_firestore = await _gerar_3_horarios_livres(
                user_id=user_id,
                data_sugerida=data_alvo,
                servico_chave="manicure",
                profissional=None,
                duracao_min=30,
                eventos_disponiveis=None  # ← Via Firestore
            )

        # Caminho 2: Via lista pré-carregada
        resultado_lista = await _gerar_3_horarios_livres(
            user_id=user_id,
            data_sugerida=data_alvo,
            servico_chave="manicure",
            profissional=None,
            duracao_min=30,
            eventos_disponiveis=eventos_firestore  # ← Via lista
        )

        # Assert
        assert isinstance(resultado_firestore, list), "[FAIL T3] Firestore não retorna lista"
        assert isinstance(resultado_lista, list), "[FAIL T3] Lista não retorna lista"
        assert resultado_firestore == resultado_lista, f"[FAIL T3] Resultados diferem: {resultado_firestore} vs {resultado_lista}"

        print(f"  [OK T3] Equivalência confirmada: ambos retornam {len(resultado_firestore)} horários")

    @pytest.mark.asyncio
    async def test_T4_sem_redundancia_firestore(self):
        """T4: Com eventos_disponiveis, Firestore não é chamado"""
        print("\n[T4] Ausência de redundância")

        user_id = "test_user_redundancia"
        data_alvo = datetime.now(FUSO_BR).date() + timedelta(days=20)
        eventos_disponiveis = []  # Vazio, mas fornecido

        mock_buscar = AsyncMock(side_effect=Exception("ERRO: buscar_eventos_por_intervalo foi chamada!"))

        with patch('services.recorrencia_service.buscar_eventos_por_intervalo', mock_buscar):
            try:
                horarios = await _gerar_3_horarios_livres(
                    user_id=user_id,
                    data_sugerida=data_alvo,
                    servico_chave="teste",
                    profissional=None,
                    duracao_min=30,
                    eventos_disponiveis=eventos_disponiveis  # ← Evita Firestore
                )

                # Assert
                assert isinstance(horarios, list), "[FAIL T4] Retorno não é lista"
                mock_buscar.assert_not_called(), "[FAIL T4] Firestore foi chamado"

                print(f"  [OK T4] Sem redundância confirmada: retornou {len(horarios)} horários sem chamar Firestore")

            except Exception as e:
                if "buscar_eventos_por_intervalo foi chamada" in str(e):
                    pytest.fail(f"[FAIL T4] Redundância detectada: {e}")
                raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
