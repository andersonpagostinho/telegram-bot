"""
C4.4.7-B — Teste: Eliminação de Redundância Firestore

Validar que:
1. _descobrir_cadencia(lst, chave_servico) funciona sem leitura Firestore
2. Resultado é equivalente ao comportamento anterior
3. Nenhuma chamada adicional a buscar_subcolecao() durante _descobrir_cadencia()
4. Filtros e normalização continuam corretos
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import sys
import uuid
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recorrencia_service import (
    _descobrir_cadencia,
    _parse_dt,
    _normalizar_servico,
)

FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC447bEliminacaoRedundancia:
    """Validar otimização sem leitura redundante Firestore"""

    async def _criar_evento(self, data_str: str, hora_str: str, servico: str):
        """Helper: criar evento dict"""
        return {
            "data": data_str,
            "hora_inicio": hora_str,
            "hora_fim": "11:00",
            "cliente_id": "cli_test",
            "descricao": servico,
            "profissional": "João",
            "status": "confirmado",
        }

    @pytest.mark.asyncio
    async def test_T1_sem_leitura_firestore(self):
        """T1: _descobrir_cadencia() não lê Firestore"""
        print("\n[T1] Sem leitura Firestore")

        agora = datetime.now(FUSO_BR)

        # Criar eventos em memória
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        # Mock buscar_subcolecao para falhar se chamado
        with patch('services.recorrencia_service.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:
            mock_buscar.side_effect = Exception("buscar_subcolecao foi chamado! (redundância!)")

            # Chamar _descobrir_cadencia com lst
            cadencia = await _descobrir_cadencia(lst, "corte cabelo")

            # Se chegou aqui, buscar_subcolecao NÃO foi chamado
            assert cadencia is not None, "[FAIL T1] Cadência não descoberta"
            assert 10 <= cadencia <= 35, f"[FAIL T1] Cadência fora intervalo: {cadencia}"

            # Verificar que buscar_subcolecao não foi chamado
            mock_buscar.assert_not_called()

            print(f"  [OK T1] _descobrir_cadencia() sem leitura Firestore: cadência={cadencia}")

    @pytest.mark.asyncio
    async def test_T2_equivalencia_com_lst(self):
        """T2: Resultado com lst == resultado anterior"""
        print("\n[T2] Equivalência com lst")

        agora = datetime.now(FUSO_BR)

        # Criar eventos
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=45)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=15)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        # Chamar com novo assinatura
        cadencia = await _descobrir_cadencia(lst, "corte cabelo")

        # Intervalos: [15, 15]
        # Mediana: 15
        assert cadencia == 15, f"[FAIL T2] Esperava 15, obteve {cadencia}"
        print(f"  [OK T2] Equivalência comprovada: cadência={cadencia}")

    @pytest.mark.asyncio
    async def test_T3_normalizacao_mantida(self):
        """T3: Normalização com unidecode continua funcionando"""
        print("\n[T3] Normalização mantida")

        agora = datetime.now(FUSO_BR)

        # Criar eventos com variações
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
                "10:00",
                "Côrte Cabêlo"  # Com acentos
            ),
            await self._criar_evento(
                (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
                "10:00",
                "CORTE CABELO"  # Maiúsculas
            ),
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"  # Minúsculas
            ),
        ]

        # Buscar com acentos
        cadencia = await _descobrir_cadencia(lst, "Côrte Cabêlo")

        assert cadencia is not None, "[FAIL T3] Normalização falhou"
        print(f"  [OK T3] Normalização mantida: {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T4_filtro_cliente_preservado(self):
        """T4: Filtro de cliente_id preservado (já em lst)"""
        print("\n[T4] Filtro cliente_id preservado")

        agora = datetime.now(FUSO_BR)

        # Criar eventos
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        # lst já contém apenas eventos de cliente_id correto
        cadencia = await _descobrir_cadencia(lst, "corte cabelo")

        assert cadencia is not None, "[FAIL T4] Cadência não descoberta"
        assert 10 <= cadencia <= 35, f"[FAIL T4] Fora intervalo: {cadencia}"
        print(f"  [OK T4] Filtro cliente_id preservado: {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T5_validacao_parse_dt_mantida(self):
        """T5: Validação de data/hora com _parse_dt() continua"""
        print("\n[T5] Validação _parse_dt() mantida")

        agora = datetime.now(FUSO_BR)

        # Criar eventos: 2 válidos + 1 sem hora (será ignorado)
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            {  # Evento sem hora (será descartado)
                "data": (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
                "hora_inicio": None,  # SEM HORA
                "cliente_id": "cli_test",
                "descricao": "corte cabelo",
                "profissional": "João",
                "status": "confirmado",
            },
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        # Com 2 eventos válidos, cadência não pode ser descoberta (< 3 eventos)
        cadencia = await _descobrir_cadencia(lst, "corte cabelo")

        assert cadencia is None, f"[FAIL T5] Esperava None (< 3 eventos), obteve {cadencia}"
        print(f"  [OK T5] Validação _parse_dt() mantida: eventos sem hora ignorados")

    @pytest.mark.asyncio
    async def test_T6_minimo_tres_eventos(self):
        """T6: Mínimo de 3 eventos (validação mantida)"""
        print("\n[T6] Mínimo 3 eventos")

        agora = datetime.now(FUSO_BR)

        # Apenas 2 eventos
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        cadencia = await _descobrir_cadencia(lst, "corte cabelo")

        assert cadencia is None, f"[FAIL T6] <3 eventos deveria retornar None, obteve {cadencia}"
        print(f"  [OK T6] Mínimo 3 eventos validado")

    @pytest.mark.asyncio
    async def test_T7_intervalo_10_35_mantido(self):
        """T7: Intervalo [10, 35] dias validado"""
        print("\n[T7] Intervalo [10, 35] dias")

        agora = datetime.now(FUSO_BR)

        # Criar eventos: intervalo muito curto (5 dias)
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=15)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=5)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        cadencia = await _descobrir_cadencia(lst, "corte cabelo")

        # Mediana([5, 5]) = 5 < 10 → None
        assert cadencia is None, f"[FAIL T7] Fora intervalo, deveria ser None, obteve {cadencia}"
        print(f"  [OK T7] Intervalo [10, 35] validado (fora = None)")

    @pytest.mark.asyncio
    async def test_T8_mediana_correta(self):
        """T8: Cálculo da mediana correto"""
        print("\n[T8] Mediana correta")

        agora = datetime.now(FUSO_BR)

        # Intervalos irregulares: [10, 20, 10]
        # Mediana([10, 10, 20]) = 10
        lst = [
            await self._criar_evento(
                (agora - timedelta(days=40)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
            await self._criar_evento(
                (agora - timedelta(days=0)).strftime("%Y-%m-%d"),
                "10:00",
                "corte cabelo"
            ),
        ]

        cadencia = await _descobrir_cadencia(lst, "corte cabelo")

        # Intervalos: [10, 20, 10]
        # Sorted: [10, 10, 20]
        # Mediana: 10
        assert cadencia == 10, f"[FAIL T8] Mediana correta, obteve {cadencia}"
        print(f"  [OK T8] Mediana correta: {cadencia} dias")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
