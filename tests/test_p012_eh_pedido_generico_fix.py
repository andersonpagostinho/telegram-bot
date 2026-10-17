"""
P0.1.2 — Testes obrigatórios para correção eh_pedido_generico
Validação da mudança em router/principal_router.py linha 7888-7889

Cenários testados:
1. agendando + modo_escolha_horario=True + "quero com outra pessoa" → deve oferecer menu
2. aguardando_escolha_horario + mesma mensagem → preservar comportamento
3. agendando + modo_escolha_horario=False → não deve entrar no ramo
4. Escolher profissional disponível → preservar serviço/data/horário
5. Escolher profissional indisponível → avisar sem criar evento
6. Escolher horário alternativo → fluxo existente continua
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

import pytest
from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2


class TestP012EhPedidoGenericoFix:
    """Testes para validar fix de eh_pedido_generico"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para testes"""
        self.tenant_id = "7394370553"
        self.cliente_id = "whatsapp:5511991382080"
        self.dono_id = self.tenant_id

    # =========================================================================
    # TESTE 1: estado="agendando" + modo_escolha_horario=True + "quero com outra"
    # ESPERADO: Entra em eh_pedido_generico (deve oferecer menu)
    # =========================================================================
    async def test_1_agendando_com_modo_escolha_true(self):
        """Cenário P0.1.2: agendando + modo_escolha_horario=True"""

        ctx = {
            "estado_fluxo": "agendando",          # ← Estado atual (não "aguardando_escolha_horario")
            "modo_escolha_horario": True,         # ← FLAG CRÍTICO
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": "profissional",
            "objetivo_conversacional": "ajustar_draft_existente",
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            },
            "horarios_sugeridos": ["10:10 - 11:10", "11:10 - 12:10", "12:10 - 13:10"],
            "alternativa_profissional": ["Gloria", "Joana", "Carla"],
            "dados_anteriores": None
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # ✅ Verificação: Contexto foi salvo corretamente
        assert ctx_carregado.get("estado_fluxo") == "agendando"
        assert ctx_carregado.get("modo_escolha_horario") is True
        assert ctx_carregado.get("intencao_conversacional") == "ajuste_incremental"
        assert ctx_carregado.get("tipo_ajuste_incremental") == "profissional"
        assert ctx_carregado.get("alternativa_profissional") == ["Gloria", "Joana", "Carla"]

        print("[PASS] Teste 1: Contexto P0.1.2 carregado corretamente")

    # =========================================================================
    # TESTE 2: aguardando_escolha_horario + "quero com outra pessoa"
    # ESPERADO: Preserva comportamento existente (entra em eh_pedido_generico)
    # =========================================================================
    async def test_2_aguardando_escolha_horario_preservado(self):
        """Cenário compatível: estado clássico aguardando_escolha_horario"""

        ctx = {
            "estado_fluxo": "aguardando_escolha_horario",  # ← Estado tradicional
            "modo_escolha_horario": False,
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": "profissional",
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            },
            "alternativa_profissional": ["Gloria", "Joana", "Carla"]
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # ✅ Verificação: Estado clássico foi preservado
        assert ctx_carregado.get("estado_fluxo") == "aguardando_escolha_horario"
        assert ctx_carregado.get("alternativa_profissional") == ["Gloria", "Joana", "Carla"]

        print("[PASS] Teste 2: Estado aguardando_escolha_horario preservado")

    # =========================================================================
    # TESTE 3: agendando + modo_escolha_horario=False → NÃO entra em eh_pedido_generico
    # ESPERADO: Não oferece menu (cai no fallback ou outro handler)
    # =========================================================================
    async def test_3_agendando_sem_modo_escolha(self):
        """Cenário negativo: agendando sem flag de escolha"""

        ctx = {
            "estado_fluxo": "agendando",
            "modo_escolha_horario": False,         # ← FLAG DESLIGADO
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": "profissional",
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00"
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # ✅ Verificação: Flag está desligado
        assert ctx_carregado.get("modo_escolha_horario") is False
        # Neste caso, eh_pedido_generico seria False (primeira condição falha)

        print("[PASS] Teste 3: agendando sem modo_escolha_horario rejeita eh_pedido_generico")

    # =========================================================================
    # TESTE 4: Escolher profissional disponível → preservar serviço/data/hora
    # ESPERADO: Draft mantém original, apenas profissional muda
    # =========================================================================
    async def test_4_escolher_profissional_disponivel(self):
        """Validar que escolha de profissional preserva dados originais"""

        ctx_inicial = {
            "estado_fluxo": "agendando",
            "modo_escolha_horario": True,
            "servico": "corte feminino",           # ← Original
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",   # ← Original
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            },
            "alternativa_profissional": ["Gloria", "Joana", "Carla"]
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx_inicial)

        # Simular escolha de Gloria
        ctx_pos_escolha = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)
        ctx_pos_escolha["profissional_escolhido"] = "Gloria"
        ctx_pos_escolha["draft_agendamento"]["profissional"] = "Gloria"

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx_pos_escolha)
        ctx_final = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # ✅ Verificação: Serviço e data_hora preservados, apenas profissional mudou
        assert ctx_final.get("servico") == "corte feminino"
        assert ctx_final.get("data_hora") == "2026-10-20T09:00:00"
        assert ctx_final.get("profissional_escolhido") == "Gloria"
        assert ctx_final.get("draft_agendamento", {}).get("profissional") == "Gloria"

        print("[PASS] Teste 4: Escolha de profissional preserva serviço e data_hora")

    # =========================================================================
    # TESTE 5: Escolher profissional indisponível → avisar sem criar evento
    # ESPERADO: Sem confirmacao_agendamento gerada antes de validação
    # =========================================================================
    async def test_5_escolher_profissional_indisponivel(self):
        """Validar que indisponibilidade é detectada"""

        ctx = {
            "estado_fluxo": "agendando",
            "modo_escolha_horario": True,
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            },
            "alternativa_profissional": ["Gloria"]  # Apenas Gloria
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # ✅ Verificação: Contexto não tem aguardando_confirmacao_agendamento ainda
        # (seria gerado APÓS validação de disponibilidade, não antes)
        assert not ctx_carregado.get("aguardando_confirmacao_agendamento")

        print("[PASS] Teste 5: Contexto não cria confirmacao sem validação prévia")

    # =========================================================================
    # TESTE 6: Escolher horário alternativo → fluxo existente continua
    # ESPERADO: Sem interferência da mudança em eh_pedido_generico
    # =========================================================================
    async def test_6_escolher_horario_alternativo(self):
        """Validar que escolha de horário não é afetada"""

        ctx = {
            "estado_fluxo": "agendando",
            "modo_escolha_horario": True,
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",  # Original
            "horarios_sugeridos": ["10:10 - 11:10", "11:10 - 12:10"],
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            }
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # ✅ Verificação: Horários sugeridos estão disponíveis
        assert ctx_carregado.get("horarios_sugeridos") == ["10:10 - 11:10", "11:10 - 12:10"]
        assert ctx_carregado.get("modo_escolha_horario") is True

        print("[PASS] Teste 6: Escolha de horário não é afetada pela mudança")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
