"""
Testes: Onboarding Conversacional de Funcionamento (Novo Parser)
Data: 2026-11-16
Escopo: Parser dias/horários + salvamento expandido
"""

import pytest
from services.onboarding_dono_service import (
    _parsear_dias_semana,
    _parsear_horarios,
    construir_agenda_por_dias,
    _normalizar_hora,
    _validar_formato_hora
)


class TestParserDiasSemana:
    """Testes de parsing de dias da semana"""

    def test_seg_sex(self):
        """'segunda a sexta' → [0,1,2,3,4]"""
        result = _parsear_dias_semana("segunda a sexta")
        assert result == [0, 1, 2, 3, 4]

    def test_seg_sab(self):
        """'segunda a sábado' → [0,1,2,3,4,5]"""
        result = _parsear_dias_semana("segunda a sábado")
        assert result == [0, 1, 2, 3, 4, 5]

    def test_dias_especificos(self):
        """'segunda, quarta, sexta' → [0,2,4]"""
        result = _parsear_dias_semana("segunda, quarta, sexta")
        assert 0 in result and 2 in result and 4 in result

    def test_todos_dias(self):
        """'todos os dias' → [0,1,2,3,4,5,6]"""
        result = _parsear_dias_semana("todos os dias")
        assert len(result) == 7


class TestParserHorarios:
    """Testes de parsing de horários"""

    def test_9_as_18(self):
        """'9h às 18h' → {09:00-18:00}"""
        result = _parsear_horarios("das 9h às 18h")
        assert result["inicio"] == "09:00"
        assert result["fim"] == "18:00"

    def test_9_30_as_17_45(self):
        """'9:30 às 17:45' → {09:30-17:45}"""
        result = _parsear_horarios("das 9:30 até 17:45")
        assert result["inicio"] == "09:30"
        assert result["fim"] == "17:45"

    def test_8_as_12_e_13_as_18(self):
        """Com intervalo: 'das 8 às 12 e das 13 às 18' → pega primeiras"""
        result = _parsear_horarios("das 8 às 12 e das 13 às 18")
        # Padrão simples pega primeiro intervalo
        assert result.get("inicio") is not None


class TestConstruirAgenda:
    """Testes de construção de agenda para Firestore"""

    def test_seg_sex_9_18(self):
        """Segunda a sexta, 9-18, domingo fechado"""
        dias_config = {
            "dias": [0, 1, 2, 3, 4],
            "horarios": {
                "0": {"inicio": "09:00", "fim": "18:00"}
            }
        }
        agenda = construir_agenda_por_dias(dias_config)

        # Verificar que seg-sex estão abertos
        assert agenda["0"]["aberto"] is True
        assert agenda["0"]["inicio"] == "09:00"
        # Verificar que dom está fechado
        assert agenda["6"]["aberto"] is False

    def test_sab_horario_diferente(self):
        """Sábado com horário diferente"""
        dias_config = {
            "dias": [0, 1, 2, 3, 4, 5],
            "horarios": {
                "0": {"inicio": "09:00", "fim": "18:00"},
                "5": {"inicio": "09:00", "fim": "13:00"}
            }
        }
        agenda = construir_agenda_por_dias(dias_config)

        # Sexta: 18:00
        assert agenda["4"]["fim"] == "18:00"
        # Sábado: 13:00
        assert agenda["5"]["fim"] == "13:00"
        # Domingo: fechado
        assert agenda["6"]["aberto"] is False


class TestNormalizacao:
    """Testes de normalização e validação"""

    def test_normalizar_9_00(self):
        """'9:00' → '09:00'"""
        assert _normalizar_hora("9:00") == "09:00"

    def test_validar_9_00(self):
        """'9:00' é válido"""
        assert _validar_formato_hora("9:00") is True

    def test_validar_25_00_invalido(self):
        """'25:00' é inválido"""
        assert _validar_formato_hora("25:00") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
