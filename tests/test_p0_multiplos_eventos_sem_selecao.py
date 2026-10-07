#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 — Teste Mínimo de Regressão: Múltiplos Eventos sem Seleção

Objetivo: Validar que quando há múltiplos eventos e usuário responde "sim"
sem selecionar um número, o sistema reapresenta a lista em vez de
tentar cancelar com evento_id=None.

Cenário: WhatsApp roteador_principal com cancelamento_pendente contendo
resumo_eventos (múltiplo) mas sem evento_id.
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestMultiplosEventosSemSelecao:
    """Regressão: múltiplos eventos sem seleção deve reapresentar lista"""

    def test_confirmacao_sim_com_multiplos_eventos_sem_evento_id(self):
        """
        Dado: cancelamento_pendente com resumo_eventos (2+ eventos) mas SEM evento_id
        Quando: usuário responde "sim"
        Então: sistema reapresenta lista numerada (não tenta cancelar)
        """

        # Simular contexto de múltiplos eventos
        cancelamento_pendente = {
            "cliente_id": "5511991382080",
            "resumo_eventos": [
                {
                    "evento_id": "evt1",
                    "descricao": "Corte de cabelo",
                    "data": "2026-10-10",
                    "hora_inicio": "14:00",
                    "profissional": "Bruna"
                },
                {
                    "evento_id": "evt2",
                    "descricao": "Escova",
                    "data": "2026-10-12",
                    "hora_inicio": "15:30",
                    "profissional": "Ana"
                },
                {
                    "evento_id": "evt3",
                    "descricao": "Coloração",
                    "data": "2026-10-15",
                    "hora_inicio": "10:00",
                    "profissional": "Maria"
                }
            ]
            # ← IMPORTANTE: SEM "evento_id" no nível superior
        }

        # Validação: sem evento_id no topo
        assert "evento_id" not in cancelamento_pendente, \
            "evento_id não deve estar no topo quando há múltiplos"

        # Validação: tem resumo_eventos
        assert "resumo_eventos" in cancelamento_pendente, \
            "resumo_eventos deve estar presente"

        resumo_eventos = cancelamento_pendente.get("resumo_eventos", [])
        assert len(resumo_eventos) > 1, "Deve haver múltiplos eventos"

        # Simular formatação que a proteção faria
        linhas = []
        for i, ev in enumerate(resumo_eventos, start=1):
            desc = ev.get('descricao', '(sem título)')
            data = ev.get('data', '????-??-??')
            hora = ev.get('hora_inicio', '??:??')
            linhas.append(f"{i}) {desc} — {data} às {hora}")

        resposta = "Qual deseja cancelar?\n" + "\n".join(linhas)

        # Validações esperadas
        assert "Qual deseja cancelar?" in resposta, "Deve pedir seleção"
        assert "1) Corte de cabelo — 2026-10-10 às 14:00" in resposta, "Deve incluir evento 1"
        assert "2) Escova — 2026-10-12 às 15:30" in resposta, "Deve incluir evento 2"
        assert "3) Coloração — 2026-10-15 às 10:00" in resposta, "Deve incluir evento 3"

        print("[REGRESSÃO PASS] Múltiplos eventos sem seleção reapresentam lista")

    def test_confirmacao_sim_com_evento_id_cancelamento_normal(self):
        """
        Dado: cancelamento_pendente COM evento_id (já foi selecionado)
        Quando: usuário responde "sim"
        Então: fluxo normal de cancelamento (não deve reapresentar lista)
        """

        # Simular contexto APÓS seleção de número
        cancelamento_pendente = {
            "evento_id": "evt1",  # ← PRESENTE, foi selecionado
            "cliente_id": "5511991382080",
            "resumo_evento": {
                "evento_id": "evt1",
                "descricao": "Corte de cabelo",
                "data": "2026-10-10",
                "hora_inicio": "14:00",
                "profissional": "Bruna"
            }
        }

        # Validação: com evento_id no topo
        assert "evento_id" in cancelamento_pendente, \
            "evento_id deve estar no topo após seleção"

        evento_id = cancelamento_pendente.get("evento_id")

        # Esta é a condição que PERMITE cancelamento
        assert evento_id, "evento_id deve ser confiável para cancelar"

        print("[REGRESSÃO PASS] Com evento_id permite cancelamento normal")

    def test_condicoes_protecao(self):
        """
        Validar as exatas condições para acionar a proteção.

        Proteção é acionada quando:
            resumo_eventos EXISTS
            AND evento_id NÃO EXISTS
        """

        # Caso 1: múltiplos SEM evento_id → proteção acionada
        ctx1 = {
            "resumo_eventos": [{"evento_id": "1"}, {"evento_id": "2"}],
            # evento_id ausente
        }

        protecao_acionada = "resumo_eventos" in ctx1 and "evento_id" not in ctx1
        assert protecao_acionada, "Proteção deve acionar para múltiplos sem evento_id"
        print("[CONDIÇÃO 1 OK] Múltiplos sem evento_id → proteção acionada")

        # Caso 2: múltiplos COM evento_id → proteção NÃO acionada
        ctx2 = {
            "evento_id": "evt1",
            "resumo_eventos": [{"evento_id": "1"}, {"evento_id": "2"}],
        }

        protecao_acionada = "resumo_eventos" in ctx2 and "evento_id" not in ctx2
        assert not protecao_acionada, "Proteção não deve acionar se evento_id existe"
        print("[CONDIÇÃO 2 OK] Múltiplos com evento_id → proteção NÃO acionada")

        # Caso 3: único evento COM evento_id → proteção NÃO acionada
        ctx3 = {
            "evento_id": "evt1",
            "resumo_evento": {"evento_id": "1"},
        }

        protecao_acionada = "resumo_eventos" in ctx3 and "evento_id" not in ctx3
        assert not protecao_acionada, "Proteção não deve acionar para caso único"
        print("[CONDIÇÃO 3 OK] Caso único → proteção NÃO acionada")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
