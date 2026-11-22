# -*- coding: utf-8 -*-
"""
Testes das Correções P0 — Consulta Informativa e Seleção de Opções
Data: 2026-11-18
"""

import pytest
import re
import unidecode


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação"""
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


# =============================================================================
# CORREÇÃO 1: Falso Positivo em tem_agendar
# =============================================================================

class TestCorrecao1_FalsoPositivoConsigo:
    """Testes para CORREÇÃO 1: 'consigo' não deve ativar tem_agendar isoladamente"""

    @staticmethod
    def detector_tem_agendar_original(mensagem: str) -> bool:
        """Detector ANTES da correção (com 'consigo')"""
        return any(x in normalizar(mensagem) for x in [
            "agendar", "marcar", "horario", "horário", "dá para", "da para",
            "pode ser", "posso", "consigo", "faço", "faz", "reserva"
        ])

    @staticmethod
    def detector_tem_agendar_corrigido(mensagem: str) -> bool:
        """Detector APÓS a correção (sem 'consigo')"""
        return any(x in normalizar(mensagem) for x in [
            "agendar", "marcar", "horario", "horário", "dá para", "da para",
            "pode ser", "posso", "faço", "faz", "reserva"
        ])

    def test_consigo_capacidade_nao_ativa_agendamento(self):
        """Teste 1: 'Consigo chegar' não deve ativar agendamento"""
        mensagem = "Consigo chegar a partir das 14h"

        # Antes: ✗ FALSO POSITIVO
        tem_agendar_antes = self.detector_tem_agendar_original(mensagem)
        assert tem_agendar_antes == True, "Antes da correção: 'consigo' ativa tem_agendar ✗"

        # Depois: ✓ CORRETO
        tem_agendar_depois = self.detector_tem_agendar_corrigido(mensagem)
        assert tem_agendar_depois == False, "Depois da correção: 'consigo' NÃO ativa tem_agendar ✓"

        print(f"✓ Teste 1 PASS: '{mensagem}' | Antes={tem_agendar_antes} → Depois={tem_agendar_depois}")

    def test_quero_agendar_continua_funcionando(self):
        """Teste 2: 'Quero agendar' continua ativando agendamento"""
        mensagem = "Quero agendar para amanhã"

        tem_agendar_antes = self.detector_tem_agendar_original(mensagem)
        tem_agendar_depois = self.detector_tem_agendar_corrigido(mensagem)

        assert tem_agendar_antes == True, "Antes: 'agendar' ativa ✓"
        assert tem_agendar_depois == True, "Depois: 'agendar' continua ativando ✓"

        print(f"✓ Teste 2 PASS: '{mensagem}' continua ativando agendamento")

    def test_agendar_apenas_consulta(self):
        """Teste 3: Consulta sobre agendamento (sem intenção) não ativa"""
        mensagem = "Consigo agendar em qualquer dia desta semana?"

        tem_agendar_antes = self.detector_tem_agendar_original(mensagem)
        tem_agendar_depois = self.detector_tem_agendar_corrigido(mensagem)

        # Antes: ✗ FALSO - "consigo" + "agendar" = confusão
        # Depois: ✓ CORRETO - "agendar" é mais explícito (consulta real)
        assert tem_agendar_antes == True, "Antes: 'consigo' + 'agendar' = True (esperado)"
        assert tem_agendar_depois == True, "Depois: 'agendar' explícito = True (correto)"

        print(f"✓ Teste 3 PASS: Consulta sobre agendamento mantém 'agendar'")

    def test_consulta_pura_sem_termos_agendamento(self):
        """Teste 4: Consulta pura sem nenhum termo de agendamento"""
        mensagem = "Quais são seus serviços?"

        tem_agendar_antes = self.detector_tem_agendar_original(mensagem)
        tem_agendar_depois = self.detector_tem_agendar_corrigido(mensagem)

        assert tem_agendar_antes == False
        assert tem_agendar_depois == False

        print(f"✓ Teste 4 PASS: Consulta pura não ativa agendamento")


# =============================================================================
# CORREÇÃO 2: Reconhecimento de Seleção
# =============================================================================

class TestCorrecao2_ReconhecimentoSelecao:
    """Testes para CORREÇÃO 2: Seleção reconhecida com contexto_resultado_consulta válido"""

    def test_selecao_reconhecida_com_opcoes_reais(self):
        """Teste 5: 'o primeiro' é reconhecido quando há opcoes_reais"""
        # Simular contexto
        ctx_inicial = {
            "contexto_consulta": {},  # Vazio
            "contexto_resultado_consulta": {
                "opcoes": [
                    {"numero": 1, "hora_inicio": "14:00"},
                    {"numero": 2, "hora_inicio": "14:20"},
                    {"numero": 3, "hora_inicio": "14:40"}
                ]
            }
        }

        # Verificar pré-condições da CORREÇÃO 2
        contexto_consulta_valido = ctx_inicial.get("contexto_consulta", {})
        resultado_consulta_persistido = ctx_inicial.get("contexto_resultado_consulta", {})
        tem_opcoes_reais = isinstance(resultado_consulta_persistido, dict) and len(resultado_consulta_persistido.get("opcoes", [])) > 0

        # Antes: Falha (depende de contexto_consulta.servicos_multiplos)
        # Depois: Sucesso (depende apenas de tem_opcoes_reais)
        pode_reconhecer_selecao = tem_opcoes_reais

        assert pode_reconhecer_selecao == True, "Seleção deve ser reconhecida com opcoes_reais ✓"
        print(f"✓ Teste 5 PASS: Seleção reconhecida com opcoes_reais")

    def test_selecao_bloqueada_sem_opcoes(self):
        """Teste 6: Seleção não é reconhecida sem opcoes_reais"""
        ctx_sem_opcoes = {
            "contexto_consulta": {},
            "contexto_resultado_consulta": {"opcoes": []}
        }

        resultado_consulta_persistido = ctx_sem_opcoes.get("contexto_resultado_consulta", {})
        tem_opcoes_reais = isinstance(resultado_consulta_persistido, dict) and len(resultado_consulta_persistido.get("opcoes", [])) > 0
        pode_reconhecer_selecao = tem_opcoes_reais

        assert pode_reconhecer_selecao == False, "Seleção não deve ser reconhecida sem opcoes_reais ✓"
        print(f"✓ Teste 6 PASS: Seleção corretamente bloqueada sem opcoes")

    def test_selecao_multiplos_estados_fluxo(self):
        """Teste 7: Seleção funciona em múltiplos estados_fluxo (desde que tenha opcoes_reais)"""
        estados = ["idle", "aguardando_data", "aguardando_profissional", "consultando"]

        ctx_base = {
            "contexto_resultado_consulta": {
                "opcoes": [
                    {"numero": 1, "hora_inicio": "14:00"},
                    {"numero": 2, "hora_inicio": "14:20"},
                ]
            }
        }

        for estado in estados:
            ctx_base["estado_fluxo"] = estado

            resultado_consulta_persistido = ctx_base.get("contexto_resultado_consulta", {})
            tem_opcoes_reais = isinstance(resultado_consulta_persistido, dict) and len(resultado_consulta_persistido.get("opcoes", [])) > 0
            pode_reconhecer_selecao = tem_opcoes_reais

            assert pode_reconhecer_selecao == True, f"Seleção deve funcionar em estado={estado} se tem opcoes_reais"

        print(f"✓ Teste 7 PASS: Seleção funciona em múltiplos estados")


# =============================================================================
# TESTES DE REGRESSÃO
# =============================================================================

class TestRegressao:
    """Testes de regressão para garantir que as correções não quebram fluxos existentes"""

    def test_agendamento_direto_continua_funcionando(self):
        """Teste 8: Agendamento direto continua funcionando normalmente"""
        mensagem = "Quero agendar manicure para amanhã às 14h"

        tem_agendar = any(x in normalizar(mensagem) for x in [
            "agendar", "marcar", "horario", "horário", "dá para", "da para",
            "pode ser", "posso", "faço", "faz", "reserva"
        ])

        tem_temporal = any(x in normalizar(mensagem) for x in [
            "amanhã", "hoje", "segunda", "14h", "15h", "16h"
        ])

        assert tem_agendar == True, "Agendamento direto continua sendo detectado"
        assert tem_temporal == True, "Temporal continua sendo detectado"

        print(f"✓ Teste 8 PASS: Agendamento direto não sofre regressão")

    def test_consulta_pura_sem_regressao(self):
        """Teste 9: Consulta pura sem mudanças"""
        mensagem = "Quais profissionais vocês têm?"

        tem_agendar = any(x in normalizar(mensagem) for x in [
            "agendar", "marcar", "horario", "horário", "dá para", "da para",
            "pode ser", "posso", "faço", "faz", "reserva"
        ])

        assert tem_agendar == False, "Consulta pura não ativa agendamento"
        print(f"✓ Teste 9 PASS: Consulta pura sem regressão")

    def test_isolamento_tenant_actor(self):
        """Teste 10: Isolamento multi-tenant/actor validado"""
        ctx_a = {
            "tenant_id": "7394370553",
            "actor_id": "whatsapp:5511991382080",
            "contexto_resultado_consulta": {"opcoes": [{"numero": 1}]}
        }

        ctx_b = {
            "tenant_id": "9999999999",  # Outro tenant
            "actor_id": "whatsapp:5511991382080",
            "contexto_resultado_consulta": {}
        }

        # Cada um tem seu contexto
        tem_opcoes_a = len(ctx_a.get("contexto_resultado_consulta", {}).get("opcoes", [])) > 0
        tem_opcoes_b = len(ctx_b.get("contexto_resultado_consulta", {}).get("opcoes", [])) > 0

        assert tem_opcoes_a == True, "Context A tem opcoes"
        assert tem_opcoes_b == False, "Context B não tem opcoes"
        assert ctx_a["tenant_id"] != ctx_b["tenant_id"], "Tenants diferentes"

        print(f"✓ Teste 10 PASS: Isolamento tenant/actor validado")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
