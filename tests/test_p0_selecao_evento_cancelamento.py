#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 — Teste: Seleção de Evento em Cancelamento WhatsApp

Objetivo: Validar que o sistema reconhece números como seleção de evento
quando há múltiplos eventos pendentes de cancelamento.

Cenários:
- T1-T6: Classificador reconhece seleção numérica
- T7-T9: Classificador preserva confirmacao/negacao/ambiguo
- T10: Integração com router principal
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.classificador_conversa import classificar_confirmacao_cancelamento


class TestSeleçãoEventoCancelamento:
    """Regressão: seleção de evento por número"""

    def test_t1_numero_1_com_multiplos(self):
        """T1: Entrada '1' com 3 eventos → selecao_numero"""
        ctx = {
            "cancelamento_pendente": {
                "resumo_eventos": [
                    {"evento_id": "evt1", "descricao": "Corte", "data": "2026-10-12", "hora_inicio": "08:00"},
                    {"evento_id": "evt2", "descricao": "Escova", "data": "2026-10-13", "hora_inicio": "09:00"},
                    {"evento_id": "evt3", "descricao": "Coloracao", "data": "2026-10-14", "hora_inicio": "10:00"},
                ]
            }
        }
        resultado = classificar_confirmacao_cancelamento("1", ctx)
        assert resultado == "selecao_numero", f"Esperado 'selecao_numero', obteve '{resultado}'"
        print("[T1 OK] '1' → selecao_numero")

    def test_t2_numero_2_com_multiplos(self):
        """T2: Entrada '2' com 3 eventos → selecao_numero"""
        ctx = {
            "cancelamento_pendente": {
                "resumo_eventos": [
                    {"evento_id": "evt1", "descricao": "Corte", "data": "2026-10-12", "hora_inicio": "08:00"},
                    {"evento_id": "evt2", "descricao": "Escova", "data": "2026-10-13", "hora_inicio": "09:00"},
                    {"evento_id": "evt3", "descricao": "Coloracao", "data": "2026-10-14", "hora_inicio": "10:00"},
                ]
            }
        }
        resultado = classificar_confirmacao_cancelamento("2", ctx)
        assert resultado == "selecao_numero", f"Esperado 'selecao_numero', obteve '{resultado}'"
        print("[T2 OK] '2' → selecao_numero")

    def test_t3_numero_3_com_multiplos(self):
        """T3: Entrada '3' com 3 eventos → selecao_numero"""
        ctx = {
            "cancelamento_pendente": {
                "resumo_eventos": [
                    {"evento_id": "evt1", "descricao": "Corte", "data": "2026-10-12", "hora_inicio": "08:00"},
                    {"evento_id": "evt2", "descricao": "Escova", "data": "2026-10-13", "hora_inicio": "09:00"},
                    {"evento_id": "evt3", "descricao": "Coloracao", "data": "2026-10-14", "hora_inicio": "10:00"},
                ]
            }
        }
        resultado = classificar_confirmacao_cancelamento("3", ctx)
        assert resultado == "selecao_numero", f"Esperado 'selecao_numero', obteve '{resultado}'"
        print("[T3 OK] '3' → selecao_numero")

    def test_t4_numero_com_descricao(self):
        """T4: Entrada '1) Corte com Bruna — 2026-10-12 às 08:20' → selecao_numero"""
        ctx = {
            "cancelamento_pendente": {
                "resumo_eventos": [
                    {"evento_id": "evt1", "descricao": "Corte com Bruna", "data": "2026-10-12", "hora_inicio": "08:20"},
                    {"evento_id": "evt2", "descricao": "Escova com Ana", "data": "2026-10-13", "hora_inicio": "09:00"},
                ]
            }
        }
        resultado = classificar_confirmacao_cancelamento("1) corte com bruna — 2026-10-12 às 08:20", ctx)
        assert resultado == "selecao_numero", f"Esperado 'selecao_numero', obteve '{resultado}'"
        print("[T4 OK] '1) Corte...' → selecao_numero")

    def test_t5_numero_zero_invalido(self):
        """T5: Entrada '0' → não seleciona (inválido)"""
        ctx = {
            "cancelamento_pendente": {
                "resumo_eventos": [
                    {"evento_id": "evt1", "descricao": "Corte", "data": "2026-10-12", "hora_inicio": "08:00"},
                    {"evento_id": "evt2", "descricao": "Escova", "data": "2026-10-13", "hora_inicio": "09:00"},
                ]
            }
        }
        resultado = classificar_confirmacao_cancelamento("0", ctx)
        assert resultado != "selecao_numero", f"'0' não deveria ser selecao_numero, obteve '{resultado}'"
        print("[T5 OK] '0' → não seleciona (ambiguo ou outro)")

    def test_t6_numero_fora_alcance(self):
        """T6: Entrada '99' → não seleciona (fora do alcance)"""
        ctx = {
            "cancelamento_pendente": {
                "resumo_eventos": [
                    {"evento_id": "evt1", "descricao": "Corte", "data": "2026-10-12", "hora_inicio": "08:00"},
                    {"evento_id": "evt2", "descricao": "Escova", "data": "2026-10-13", "hora_inicio": "09:00"},
                ]
            }
        }
        resultado = classificar_confirmacao_cancelamento("99", ctx)
        assert resultado != "selecao_numero", f"'99' não deveria ser selecao_numero, obteve '{resultado}'"
        print("[T6 OK] '99' → não seleciona (ambiguo ou outro)")

    def test_t7_sem_resumo_eventos_numero_1(self):
        """T7: Entrada '1' SEM resumo_eventos → preserva comportamento anterior"""
        ctx = {
            "cancelamento_pendente": {
                "evento_id": "evt1",
                "resumo_evento": {"evento_id": "evt1", "descricao": "Corte"}
            }
        }
        resultado = classificar_confirmacao_cancelamento("1", ctx)
        # '1' sem resumo_eventos não deve ser selecao_numero
        # Deve cair no fallback ambiguo
        assert resultado != "selecao_numero", f"Sem resumo_eventos, '1' não deveria ser selecao_numero"
        print("[T7 OK] Sem resumo_eventos: '1' preserva comportamento anterior")

    def test_t8_confirmacao_sim_preservada(self):
        """T8: Entrada 'sim' → ainda é confirmacao"""
        ctx = {
            "cancelamento_pendente": {
                "evento_id": "evt1",
                "resumo_evento": {"evento_id": "evt1"}
            }
        }
        resultado = classificar_confirmacao_cancelamento("sim", ctx)
        assert resultado == "confirmacao", f"'sim' deveria ser confirmacao, obteve '{resultado}'"
        print("[T8 OK] 'sim' → confirmacao preservada")

    def test_t9_negacao_nao_preservada(self):
        """T9: Entrada 'não' → ainda é negacao"""
        ctx = {
            "cancelamento_pendente": {
                "evento_id": "evt1",
                "resumo_evento": {"evento_id": "evt1"}
            }
        }
        resultado = classificar_confirmacao_cancelamento("não", ctx)
        assert resultado == "negacao", f"'não' deveria ser negacao, obteve '{resultado}'"
        print("[T9 OK] 'não' → negacao preservada")

    def test_t10_ambiguo_nao_consigo_preservado(self):
        """T10: Entrada 'não consigo ir' → ainda é ambiguo"""
        ctx = {
            "cancelamento_pendente": {
                "evento_id": "evt1",
                "resumo_evento": {"evento_id": "evt1"}
            }
        }
        resultado = classificar_confirmacao_cancelamento("não consigo ir", ctx)
        assert resultado == "ambiguo", f"'não consigo ir' deveria ser ambiguo, obteve '{resultado}'"
        print("[T10 OK] 'não consigo ir' → ambiguo preservado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
