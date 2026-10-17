#!/usr/bin/env python3
"""
Testes para verificação de extração dinâmica de serviços.
8 cenários cobrindo:
1. Catálogo presente, serviço reconhecido
2. Catálogo ausente
3. Serviço de outro tenant
4. Mensagem sem serviço explícito com rascunho ativo
5. Novo serviço diferente do rascunho
6. Ajuste incremental sem palavras fixas
7. Intenções independentes de serviços
8. Regressão: isolamento multi-tenant
"""

import pytest
from services.classificador_conversa import (
    extrair_features_conversa,
    classificar_intencao_conversacional,
    detectar_tipo_ajuste_incremental,
    extrair_servico_do_catalogo,
)


class TestExtrairServicoDoCatalogo:
    """Testes da função extrair_servico_do_catalogo()"""

    def test_servico_reconhecido(self):
        """Teste 1: Catálogo presente, serviço reconhecido"""
        catalogo = ["corte", "escova", "coloracao"]
        texto = "quero marcar corte hoje"
        resultado = extrair_servico_do_catalogo(texto, catalogo)
        assert resultado == "corte", f"Esperado 'corte', obtido {resultado}"

    def test_catalogo_ausente(self):
        """Teste 2: Catálogo ausente"""
        texto = "quero marcar corte hoje"
        resultado = extrair_servico_do_catalogo(texto, catalogo_servicos=None)
        assert resultado is None, f"Esperado None, obtido {resultado}"

    def test_servico_nao_no_catalogo(self):
        """Teste 5: Serviço não no catálogo"""
        catalogo = ["corte", "escova"]
        texto = "quero marcar design de sobrancelha"
        resultado = extrair_servico_do_catalogo(texto, catalogo)
        assert resultado is None, f"Esperado None, obtido {resultado}"

    def test_multiplos_servicos_retorna_primeiro(self):
        """Comportamento: múltiplos serviços retorna o primeiro encontrado"""
        catalogo = ["corte", "escova", "coloracao"]
        texto = "quero escova depois corte"
        resultado = extrair_servico_do_catalogo(texto, catalogo)
        # A ordem é pela ordem do catálogo, não pela ordem de menção
        assert resultado in ["escova", "corte"], f"Resultado inesperado: {resultado}"


class TestExtrairFeatures:
    """Testes de extrair_features_conversa()"""

    def test_com_catalogo_presente(self):
        """Teste 1: Com catálogo, serviço é reconhecido"""
        catalogo = ["corte", "escova"]
        features = extrair_features_conversa("quero marcar corte", catalogo_servicos=catalogo)
        assert features["servico_mencionado"] == "corte"
        assert features["tem_contexto_servico"] is True

    def test_sem_catalogo(self):
        """Teste 2: Sem catálogo, servico_mencionado é None"""
        features = extrair_features_conversa("quero marcar corte", catalogo_servicos=None)
        assert features["servico_mencionado"] is None
        assert features["tem_contexto_servico"] is False

    def test_com_draft_sem_catalogo(self):
        """Teste 4: Sem menção explícita de serviço, mas draft ativo"""
        ctx = {"draft_agendamento": {"servico": "corte"}}
        features = extrair_features_conversa("quero outro horário", ctx=ctx, catalogo_servicos=None)
        assert features["servico_mencionado"] is None
        assert features["tem_contexto_servico"] is False
        assert features["tem_contexto_servico_ou_draft"] is True


class TestClassificarIntencao:
    """Testes de classificar_intencao_conversacional()"""

    def test_novo_agendamento_servico_diferente_draft(self):
        """Teste 5: Novo serviço diferente do rascunho → agendamento_direto"""
        catalogo = ["corte", "escova", "coloracao"]
        ctx = {"draft_agendamento": {"servico": "coloracao"}, "estado_fluxo": "aguardando_data"}
        resultado = classificar_intencao_conversacional(
            "quero agendar escova hoje",
            ctx,
            catalogo_servicos=catalogo
        )
        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"Esperado 'agendamento_direto', obtido {resultado['intencao_conversacional']}"

    def test_ajuste_mesmo_servico(self):
        """Teste 6: Mesmo serviço do draft → ajuste incremental"""
        catalogo = ["corte", "escova"]
        ctx = {"draft_agendamento": {"servico": "corte"}, "estado_fluxo": "aguardando_data"}
        resultado = classificar_intencao_conversacional(
            "quero ver outro horário para corte",
            ctx,
            catalogo_servicos=catalogo
        )
        assert resultado["intencao_conversacional"] == "ajuste_incremental", \
            f"Esperado 'ajuste_incremental', obtido {resultado['intencao_conversacional']}"

    def test_intenção_independente_sem_catalogo(self):
        """Teste 7: Intenção independente de serviço funciona sem catálogo"""
        resultado = classificar_intencao_conversacional(
            "cancela tudo",
            ctx={},
            catalogo_servicos=None
        )
        assert resultado["intencao_conversacional"] == "cancelamento", \
            f"Esperado 'cancelamento', obtido {resultado['intencao_conversacional']}"

    def test_pergunta_sem_catalogo(self):
        """Teste 7b: Pergunta sem contexto funciona sem catálogo"""
        resultado = classificar_intencao_conversacional(
            "qual o valor?",
            ctx={},
            catalogo_servicos=None
        )
        # Pode ser indefinida ou outra intenção, mas não deve quebrar
        assert resultado["intencao_conversacional"] in [
            "indefinida",
            "consulta_disponibilidade_aberta",
            "pedido_aberto_temporal"
        ], f"Resultado inesperado: {resultado['intencao_conversacional']}"


class TestIsolamentoMultiTenant:
    """Teste 8: Isolamento entre tenants"""

    def test_tenant_1_reconhece_seu_servico(self):
        """Tenant 1: "corte" é um serviço válido"""
        catalogo_1 = ["corte", "escova"]
        resultado = classificar_intencao_conversacional(
            "quero marcar corte",
            ctx={},
            catalogo_servicos=catalogo_1
        )
        assert resultado["features"]["servico_mencionado"] == "corte"

    def test_tenant_2_nao_reconhece_servico_de_tenant_1(self):
        """Tenant 2: "corte" NÃO é um serviço válido (catálogo diferente)"""
        catalogo_2 = ["design_sobrancelha", "micropigmentacao"]
        resultado = classificar_intencao_conversacional(
            "quero marcar corte",
            ctx={},
            catalogo_servicos=catalogo_2
        )
        assert resultado["features"]["servico_mencionado"] is None

    def test_cada_tenant_tem_seus_servicos(self):
        """Cada tenant opera independentemente"""
        catalogo_bruna = ["corte", "escova", "coloracao"]
        catalogo_unhas = ["manicure", "pedicure", "esmaltacao"]

        # Para Bruna
        r1 = classificar_intencao_conversacional(
            "quero escova hoje",
            ctx={},
            catalogo_servicos=catalogo_bruna
        )

        # Para salão de unhas
        r2 = classificar_intencao_conversacional(
            "quero manicure hoje",
            ctx={},
            catalogo_servicos=catalogo_unhas
        )

        assert r1["features"]["servico_mencionado"] == "escova"
        assert r2["features"]["servico_mencionado"] == "manicure"


class TestDetectarTipoAjuste:
    """Testes de detectar_tipo_ajuste_incremental()"""

    def test_com_catalogo_detecta_servico(self):
        """Com catálogo, detecta quando é ajuste de serviço"""
        catalogo = ["corte", "escova"]
        resultado = detectar_tipo_ajuste_incremental("quero outra escova", catalogo_servicos=catalogo)
        assert resultado == "servico", f"Esperado 'servico', obtido {resultado}"

    def test_sem_catalogo_nao_assume_servico(self):
        """Sem catálogo, não assume que é ajuste de serviço"""
        resultado = detectar_tipo_ajuste_incremental("quero outro corte", catalogo_servicos=None)
        assert resultado != "servico", f"Não deveria retornar 'servico' sem catálogo"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
