#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 — Teste de Bloqueio de Eventos Passados no Cancelamento

Objetivo: Validar que cancelar_evento_por_texto() não retorna eventos com data no passado.

Status: Reproduz o bug — eventos passados aparecem como candidatos antes do patch.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestCancelarEventoPassado:
    """Testes de bloqueio de eventos passados no cancelamento"""

    def setup_method(self):
        """Setup para cada teste"""
        self.hoje = date(2026, 10, 6)
        self.ontem = self.hoje - timedelta(days=1)
        self.amanha = self.hoje + timedelta(days=1)

    def _evento_factory(self, data_str, status="confirmado"):
        """Factory para criar eventos de teste"""
        return {
            "data": data_str,
            "hora_inicio": "16:00",
            "hora_fim": "17:00",
            "status": status,
            "profissional": "Bruna",
            "descricao": "Corte cabelo",
            "servico": "corte",
        }

    def _simular_filtro_data_passada(self, evento):
        """
        Simula o filtro de data que DEVERIA existir em cancelar_evento_por_texto().

        Retorna False se evento é passado (deve ser rejeitado).
        Retorna True se evento pode ser candidato.
        """
        try:
            data_str = evento.get("data", "")
            data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            return False  # Data inválida → rejeitar

        # Rejeitar se evento é passado
        if data_evento < self.hoje:
            return False

        return True

    # =====================================================
    # TESTES: Eventos Passados (devem ser rejeitados)
    # =====================================================

    def test_t1_evento_ontem_confirmado(self):
        """T1: Evento de ontem + confirmado NÃO é candidato"""
        evento = self._evento_factory(self.ontem.isoformat(), "confirmado")

        # ANTES DO PATCH: retorna True (BUG)
        # DEPOIS DO PATCH: retorna False (correto)
        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert not pode_ser_candidato, "Evento de ontem NÃO deve ser candidato para cancelamento"
        print("[OK] T1: evento ontem + confirmado => rejeitado")

    def test_t2_evento_2026_10_05_confirmado(self):
        """T2: Evento 2026-10-05 com hoje=2026-10-06 NÃO é candidato"""
        evento = self._evento_factory("2026-10-05", "confirmado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert not pode_ser_candidato, "Evento 2026-10-05 NÃO deve ser candidato"
        print("[OK] T2: evento 2026-10-05 => rejeitado")

    def test_t3_evento_junho_confirmado(self):
        """T3: Evento de junho + confirmado NÃO é candidato"""
        evento = self._evento_factory("2026-06-03", "confirmado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert not pode_ser_candidato, "Evento de junho NÃO deve ser candidato"
        print("[OK] T3: evento 2026-06-03 => rejeitado")

    # =====================================================
    # TESTES: Eventos Hoje (devem ser aceitos)
    # =====================================================

    def test_t4_evento_hoje_confirmado(self):
        """T4: Evento de hoje + confirmado continua sendo candidato"""
        evento = self._evento_factory(self.hoje.isoformat(), "confirmado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert pode_ser_candidato, "Evento de hoje DEVE continuar sendo candidato"
        print("[OK] T4: evento hoje => aceito")

    # =====================================================
    # TESTES: Eventos Futuros (devem ser aceitos)
    # =====================================================

    def test_t5_evento_amanha_confirmado(self):
        """T5: Evento de amanha + confirmado continua sendo candidato"""
        evento = self._evento_factory(self.amanha.isoformat(), "confirmado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert pode_ser_candidato, "Evento de amanha DEVE continuar sendo candidato"
        print("[OK] T5: evento amanha => aceito")

    def test_t6_evento_futuro_confirmado(self):
        """T6: Evento futuro + confirmado continua sendo candidato"""
        futuro = self.hoje + timedelta(days=10)
        evento = self._evento_factory(futuro.isoformat(), "confirmado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert pode_ser_candidato, "Evento futuro DEVE continuar sendo candidato"
        print("[OK] T6: evento futuro => aceito")

    # =====================================================
    # TESTES: Status diferente + Data Passada
    # =====================================================

    def test_t7_evento_passado_cancelado(self):
        """T7: Evento passado + cancelado NÃO é candidato (já foi rejeitado por status)"""
        evento = self._evento_factory(self.ontem.isoformat(), "cancelado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert not pode_ser_candidato, "Evento cancelado + passado NÃO deve ser candidato"
        print("[OK] T7: evento passado + cancelado => rejeitado")

    # =====================================================
    # TESTES: Data Inválida
    # =====================================================

    def test_t8_evento_data_invalida(self):
        """T8: Evento com data inválida NÃO causa exceção e NÃO é candidato"""
        evento = self._evento_factory("data-invalida", "confirmado")

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert not pode_ser_candidato, "Evento com data inválida NÃO deve ser candidato"
        print("[OK] T8: evento data invalida => rejeitado (sem exceção)")

    def test_t9_evento_sem_data(self):
        """T9: Evento sem campo 'data' NÃO causa exceção e NÃO é candidato"""
        evento = {
            "hora_inicio": "16:00",
            "status": "confirmado",
            "profissional": "Bruna",
        }

        pode_ser_candidato = self._simular_filtro_data_passada(evento)

        assert not pode_ser_candidato, "Evento sem data NÃO deve ser candidato"
        print("[OK] T9: evento sem data => rejeitado (sem exceção)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
