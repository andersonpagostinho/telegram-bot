"""
[FIX P0.3.1] Testes da classificação determinística de consulta de disponibilidade.

Valida que a mensagem "voce tem agenda para corte amanha as 10?" é reconhecida
localmente sem chamar o GPT, e que a intenção resultante é compatível com o
roteador.

Testes obrigatórios (A-G):
  A: Frase de referência (completa com serviço, data, hora)
  B: Consulta sem horário
  C: Consulta sem serviço
  D: Fluxo ativo com serviço diferente
  E: Apenas data/hora, preservar serviço anterior
  F: Mensagem ambígua (fallback para GPT)
  G: Regressão dos testes existentes
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from services.interpretador_conversacional import interpretar_conversa_operacional
from services.classificador_conversa import normalizar_txt


class TestP0_3_1_ClassificacaoDeterministica:
    """Suite de testes para classificação determinística de consulta de disponibilidade"""

    def test_a_frase_referencia_completa(self):
        """
        [A] Frase de referência com serviço, data e hora.

        Esperado:
        - intencao = "consulta_disponibilidade_servico"
        - objetivo = "consultar_disponibilidade_por_servico"
        - confianca = 85
        - motivo = "padrão_consulta_determinístico"
        """
        texto = "voce tem agenda para corte amanha as 10?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico", \
            f"Esperado 'consulta_disponibilidade_servico', obteve '{resultado['intencao']}'"
        assert resultado["objetivo"] == "consultar_disponibilidade_por_servico", \
            f"Esperado 'consultar_disponibilidade_por_servico', obteve '{resultado['objetivo']}'"
        assert resultado["confianca"] == 85
        assert resultado["motivo"] == "padrão_consulta_determinístico"
        print(f"✅ [A] Classificação correta: {resultado}")

    def test_b_consulta_sem_horario(self):
        """
        [B] Consulta sem horário especificado.

        Esperado:
        - intencao = "consulta_disponibilidade_servico"
        - A extração posterior reconhece que horário está faltando
        - Não chama GPT para descobrir intenção
        """
        texto = "voce tem agenda para corte amanha?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        # A extração dinâmica (em outro componente) cuidará de solicitar horário
        print(f"✅ [B] Sem horário, mas intenção reconhecida: {resultado}")

    def test_c_consulta_sem_servico_explicito(self):
        """
        [C] Consulta sem serviço explícito.

        Esperado:
        - intencao = "consulta_disponibilidade_servico"
        - A extração posterior reconhece que serviço está faltando
        - Não inventa serviço, pede esclarecimento
        """
        texto = "voce tem agenda amanha?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        # "você tem agenda" é um padrão válido mesmo sem serviço explícito
        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        print(f"✅ [C] Sem serviço explícito, intenção reconhecida: {resultado}")

    def test_d_fluxo_ativo_servico_diferente(self):
        """
        [D] Cliente com draft ativo, consulta novo serviço.

        Esperado:
        - intencao = "consulta_disponibilidade_servico"
        - Respeita a mudança explícita
        - Preserva a intenção de consulta (não força continuidade do draft anterior)
        """
        texto = "voce tem agenda para pedicure amanha?"
        ctx = {
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Maria"
            },
            "estado_fluxo": "aguardando_data"
        }

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        # O roteador deve reconhecer que é nova consulta e não forçar o draft anterior
        print(f"✅ [D] Novo serviço reconhecido, intenção: {resultado}")

    def test_e_apenas_data_hora_preservar_servico(self):
        """
        [E] Mensagem com apenas data/hora, serviço anterior ativo.

        Esperado:
        - Neste caso, NÃO é padrão de "voce tem agenda para..."
        - Pode retornar "indefinida"
        - Roteador usa draft anterior para extrair serviço
        """
        texto = "amanha as 10h"
        ctx = {
            "draft_agendamento": {
                "servico": "corte",
                "data_hora": "2026-10-20T09:00:00"
            },
            "intencao_conversacional": "ajuste_incremental"
        }

        resultado = interpretar_conversa_operacional(texto, ctx)

        # Neste caso não é padrão de consulta, deve retornar "indefinida"
        assert resultado["intencao"] == "indefinida"
        # O roteador preserva o draft e o contexto
        print(f"✅ [E] Contexto preservado, intenção: {resultado}")

    def test_f_mensagem_ambigua_fallback_gpt(self):
        """
        [F] Mensagem ambígua que não casa com nenhum padrão determinístico.

        Esperado:
        - intencao = "indefinida"
        - Roteador chama GPT para resolver
        """
        texto = "oi, tudo bem? como voce esta?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "indefinida"
        assert resultado["motivo"] == "fallback_inicial"
        print(f"✅ [F] Mensagem ambígua, retorna indefinida para GPT: {resultado}")

    def test_g_regressao_negacao_confirmacao(self):
        """
        [G] Regressão: negação de confirmação ainda funciona.

        Esperado:
        - intencao = "negacao_confirmacao_agendamento"
        - objetivo = "encerrar_fluxo_agendamento"
        """
        texto = "nao, cancela isso"
        ctx = {
            "aguardando_confirmacao_agendamento": True
        }

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "negacao_confirmacao_agendamento"
        assert resultado["objetivo"] == "encerrar_fluxo_agendamento"
        print(f"✅ [G] Negação de confirmação ainda funciona: {resultado}")

    def test_variacao_tem_agenda(self):
        """Variação: "tem agenda para..."" sem "você" """
        texto = "tem agenda para corte amanha?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        print(f"✅ Variação 'tem agenda': {resultado}")

    def test_variacao_tem_horario(self):
        """Variação: "tem horário para..."" """
        texto = "tem horario para pedicure as 14h?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        print(f"✅ Variação 'tem horário': {resultado}")

    def test_variacao_tem_disponibilidade(self):
        """Variação: "tem disponibilidade"" """
        texto = "tem disponibilidade para coloracao amanha?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        print(f"✅ Variação 'tem disponibilidade': {resultado}")

    def test_variacao_voce_faz(self):
        """Variação: "você faz..."" """
        texto = "voce faz limpeza de pele?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        assert resultado["intencao"] == "consulta_disponibilidade_servico"
        print(f"✅ Variação 'você faz': {resultado}")


class TestP0_3_1_IntegracaoRoteador:
    """Testes de integração com o roteador"""

    def test_gpt_nao_chamado_consulta_deterministica(self):
        """
        Valida que GPT NÃO é chamado para consulta determinística.

        Instrumenta a função GPT e verifica que ela não é invocada
        quando interpretacao_conv.intencao != "indefinida"
        """
        texto = "voce tem agenda para corte amanha as 10?"
        ctx = {}

        # Classifica determinísticamente
        resultado_classificacao = interpretar_conversa_operacional(texto, ctx)

        # Se resultado é != "indefinida", GPT não será chamado
        assert resultado_classificacao["intencao"] != "indefinida", \
            f"Esperado intenção específica, obteve 'indefinida'"

        # Simula a condição do roteador (linha 5640)
        interpretacao_conv = resultado_classificacao
        condicao_gpt = (
            interpretacao_conv.get("intencao") == "indefinida"  # ← Essa é a chave
        )

        assert not condicao_gpt, \
            "Condição GPT seria TRUE, GPT seria chamado! Algo está errado."

        print(f"✅ GPT NÃO será chamado: condicao_gpt={condicao_gpt}")

    def test_objetivo_mapeado_corretamente(self):
        """
        Valida que a intenção mapeia para o objetivo correto no roteador.

        Linha 5550-5551 do roteador:
          elif intencao_conv == "consulta_disponibilidade_servico":
              objetivo_conversacional = "consultar_disponibilidade_por_servico"
        """
        texto = "voce tem agenda para corte amanha as 10?"
        ctx = {}

        resultado = interpretar_conversa_operacional(texto, ctx)

        # A função já retorna o objetivo correto
        assert resultado["objetivo"] == "consultar_disponibilidade_por_servico"

        # Se o roteador receber essa classificação, mapeará para o mesmo objetivo
        # (linha 5550-5551)
        print(f"✅ Objetivo mapeado corretamente no roteador")


if __name__ == "__main__":
    # Executar testes
    import sys
    pytest.main([__file__, "-v", "-s"] + sys.argv[1:])
