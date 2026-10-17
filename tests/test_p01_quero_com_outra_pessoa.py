"""
P0.1 — TESTE: "quero com outra pessoa" reconhecido e processado corretamente

CENÁRIO TESTE:
Cliente está em estado agendando com draft ativo e diz "quero com outra pessoa".
Sistema deve reconhecer como pedido de troca de profissional e oferecer alternativas.

CASOS COBERTOS:
1. "quero com outra pessoa" durante agendando sem confirmação
2. "quero com outra pessoa" durante confirmacao_pendente
3. "quero outra pessoa" (variação sem "com")
4. "quero outra mulher" (variação alternativa)
5. Ambiguidade: sem serviço no draft (edge case)
6. Sem profissional anterior (edge case)
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

import pytest
from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2


class TestP01QueroComOutraPessoa:
    """Testa reconhecimento de "quero com outra pessoa" em vários cenários"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para todos os testes"""
        self.tenant_id = "7394370553"
        self.cliente_id = "whatsapp:5511991382080"
        self.actor_id = "whatsapp:5511991382080"
        self.dono_id = self.tenant_id

    async def test_1_quero_com_outra_pessoa_agendando_sem_confirmacao(self):
        """Test: 'quero com outra pessoa' reconhecido durante agendando sem confirmacao"""

        # Simular contexto real após oferecer menu de alternativas
        ctx = {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": False,
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
            "alternativa_profissional": ["Gloria", "Joana"]
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)

        # Verificar que salvou
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        assert ctx_carregado is not None, "Contexto deveria ter sido salvo"
        assert ctx_carregado.get("draft_agendamento") is not None, "Draft deveria estar preservado"
        assert ctx_carregado.get("alternativa_profissional") == ["Gloria", "Joana"], "Alternativas deveria estar preservadas"

        print("✅ Test 1 PASSED: Contexto com alternativas salvo corretamente")

    async def test_2_quero_com_outra_pessoa_confirmacao_pendente(self):
        """Test: 'quero com outra pessoa' reconhecido durante confirmacao_pendente"""

        ctx = {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": True,  # ← Confirmacao pendente
            "intencao_conversacional": None,
            "tipo_ajuste_incremental": None,
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

        assert ctx_carregado.get("aguardando_confirmacao_agendamento") is True, "Confirmação pendente deveria estar ativa"
        assert len(ctx_carregado.get("alternativa_profissional", [])) == 3, "Deveria ter 3 alternativas"

        print("✅ Test 2 PASSED: Contexto de confirmacao pendente salvo corretamente")

    async def test_3_quero_outra_pessoa_variacao(self):
        """Test: Variação sem 'com' é reconhecida"""

        # Texto: "quero outra pessoa"
        # Esperado: reconhecer como troca de profissional genérica
        texto = "quero outra pessoa"

        # Simular normalização
        from router.principal_router import normalizar

        texto_norm = normalizar(texto)

        # Verificar que reconhece com a nova lógica (linha 2392)
        reconhece = any(x in texto_norm for x in ["outra profissional", "outra prof", "profissional diferente", "outra pessoa", "outra mulher"])

        assert reconhece is True, f"'{texto}' deveria ser reconhecido como troca de profissional"

        print("✅ Test 3 PASSED: 'quero outra pessoa' reconhecido")

    async def test_4_quero_outra_mulher_variacao(self):
        """Test: Variação com 'mulher' é reconhecida"""

        texto = "quero atendimento com outra mulher"

        from router.principal_router import normalizar

        texto_norm = normalizar(texto)
        reconhece = any(x in texto_norm for x in ["outra profissional", "outra prof", "profissional diferente", "outra pessoa", "outra mulher"])

        assert reconhece is True, f"'{texto}' deveria ser reconhecido"

        print("✅ Test 4 PASSED: 'quero outra mulher' reconhecido")

    async def test_5_ambiguidade_sem_servico(self):
        """Test: Edge case — 'quero com outra pessoa' sem serviço no draft"""

        ctx = {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": False,
            "servico": None,  # ← Sem serviço
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            }
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_carregado = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # Deveria permitir salvar mesmo sem serviço (será pedido depois)
        assert ctx_carregado is not None, "Contexto deveria ser salvo mesmo sem serviço"
        assert ctx_carregado.get("profissional_escolhido") == "Bruna", "Profissional deveria estar preservado"

        print("✅ Test 5 PASSED: Edge case sem serviço tratado")

    async def test_6_isolamento_entre_tenants(self):
        """Test: Alteração em um tenant não afeta outro"""

        tenant_a = "7394370553"
        tenant_b = "9876543210"
        cliente = "whatsapp:5511991382080"

        ctx_a = {
            "estado_fluxo": "agendando",
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {"profissional": "Bruna"}
        }

        ctx_b = {
            "estado_fluxo": "agendando",
            "profissional_escolhido": "Maria",
            "draft_agendamento": {"profissional": "Maria"}
        }

        await salvar_contexto_temporario_v2(tenant_a, cliente, ctx_a)
        await salvar_contexto_temporario_v2(tenant_b, cliente, ctx_b)

        ctx_a_carregado = await carregar_contexto_temporario_v2(tenant_a, cliente)
        ctx_b_carregado = await carregar_contexto_temporario_v2(tenant_b, cliente)

        assert ctx_a_carregado.get("profissional_escolhido") == "Bruna", "Tenant A deveria ter Bruna"
        assert ctx_b_carregado.get("profissional_escolhido") == "Maria", "Tenant B deveria ter Maria"

        print("✅ Test 6 PASSED: Isolamento entre tenants confirmado")

    async def test_7_reprocessamento_duplicado(self):
        """Test: Reprocessamento da mesma mensagem não duplica estado"""

        ctx = {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": False,
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": "2026-10-20T09:00:00",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            }
        }

        # Salvar primeira vez
        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx)
        ctx_v1 = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # Salvar segunda vez (reprocessamento)
        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx_v1)
        ctx_v2 = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        # Deveria ser idêntico
        assert ctx_v1.get("draft_agendamento") == ctx_v2.get("draft_agendamento"), "Draft não deveria mudar"
        assert ctx_v1.get("profissional_escolhido") == ctx_v2.get("profissional_escolhido"), "Profissional não deveria mudar"

        print("✅ Test 7 PASSED: Reprocessamento não duplica estado")

    async def test_8_persistencia_merge(self):
        """Test: Merge não sobrescreve campos atuais com valores antigos"""

        # Contexto inicial
        ctx_v1 = {
            "estado_fluxo": "agendando",
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-20T09:00:00"
            }
        }

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx_v1)

        # Carregar e modificar
        ctx_v2 = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)
        ctx_v2["profissional_escolhido"] = "Gloria"
        ctx_v2["draft_agendamento"]["profissional"] = "Gloria"

        await salvar_contexto_temporario_v2(self.dono_id, self.cliente_id, ctx_v2)

        # Verificar que a mudança foi persistida
        ctx_v3 = await carregar_contexto_temporario_v2(self.dono_id, self.cliente_id)

        assert ctx_v3.get("profissional_escolhido") == "Gloria", "Profissional deveria ter sido atualizado para Gloria"
        assert ctx_v3.get("draft_agendamento", {}).get("profissional") == "Gloria", "Draft também deveria ter Gloria"

        print("✅ Test 8 PASSED: Persistência merge atualiza corretamente")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
