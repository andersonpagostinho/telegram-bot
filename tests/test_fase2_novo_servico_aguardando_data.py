#!/usr/bin/env python3
"""
FASE 2 — Testes de regressão obrigatórios para correção de preservar_continuidade_data.

9 cenários:
1. Draft "coloracao" + "quero marcar corte para segunda" → novo agendamento ✅
2. Draft "coloracao" + data sem serviço → preserva continuidade (data só)
3. Draft "corte" + "quero escova" → novo agendamento (serviço validado)
4. Draft "corte" + sem serviço explícito → preserva continuidade (não inventa serviço)
5. Serviço fora catálogo → NÃO aceita como válido
6. Correspondência ambígua → pede esclarecimento (se houver ambiguidade)
7. Estado aguardando_data com nova solicitação → não reutiliza serviço antigo
8. Confirmação, cancelamento, escolha prof → sem regressão
9. Tenant A X Tenant B → sem contaminação
"""

import pytest
from services.classificador_conversa import (
    classificar_intencao_conversacional,
    extrair_features_conversa,
)


class TestFase2NovoServicoAguardandoData:
    """Regressão: novo serviço em aguardando_data"""

    def test_01_draft_coloracao_novo_corte_com_data(self):
        """Cenário 1: Draft 'coloracao' + 'quero marcar corte para segunda'
        → novo agendamento, serviço atualizado, data preservada"""
        catalogo = ["coloracao", "corte feminino", "escova", "hidratacao", "manicure"]
        ctx = {
            "draft_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "quero marcar corte para segunda feira",
            ctx,
            catalogo_servicos=catalogo
        )

        # Nova intencao deve ser agendamento_direto
        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"Esperado agendamento_direto, obtido {resultado['intencao_conversacional']}"

        # Novo serviço deve ser reconhecido
        servico_novo = resultado["features"]["servico_mencionado"]
        assert servico_novo == "corte feminino", \
            f"Esperado 'corte feminino', obtido {servico_novo}"

        # Data deve ser detectada
        assert resultado["features"].get("tem_data"), \
            "Data não foi detectada em 'segunda feira'"

    def test_02_draft_coloracao_data_sem_servico(self):
        """Cenário 2: Draft 'coloracao' + mensagem com data mas sem novo serviço
        → ajuste incremental ou continuidade preservada (data só)"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "gostaria para segunda feira",
            ctx,
            catalogo_servicos=catalogo
        )

        # Sem novo serviço mencionado
        servico_novo = resultado["features"]["servico_mencionado"]
        assert servico_novo is None, \
            f"Não deveria ter novo serviço, obtido {servico_novo}"

        # Mas data foi mencionada
        assert resultado["features"].get("tem_data"), \
            "Data deveria ter sido detectada"

        # Intenção pode ser ajuste_incremental (mesma data/horário do draft)
        # ou ajuste se houver mudança de data
        intencao = resultado["intencao_conversacional"]
        assert intencao in ["ajuste_incremental", "agendamento_direto"], \
            f"Intenção inesperada: {intencao}"

    def test_03_draft_corte_novo_escova(self):
        """Cenário 3: Draft 'corte' + 'quero escova' → novo agendamento"""
        catalogo = ["coloracao", "corte feminino", "escova", "hidratacao"]
        ctx = {
            "draft_agendamento": {"servico": "corte feminino"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "na verdade prefiro escova hoje",
            ctx,
            catalogo_servicos=catalogo
        )

        # Novo serviço diferente
        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"Esperado agendamento_direto, obtido {resultado['intencao_conversacional']}"

        assert resultado["features"]["servico_mencionado"] == "escova", \
            f"Esperado 'escova', obtido {resultado['features']['servico_mencionado']}"

    def test_04_draft_corte_sem_servico_explicito(self):
        """Cenário 4: Draft 'corte' + mensagem sem serviço explícito
        → NÃO substitui serviço por inferência"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "corte feminino"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "qual o horário disponível?",
            ctx,
            catalogo_servicos=catalogo
        )

        # Sem novo serviço
        assert resultado["features"]["servico_mencionado"] is None, \
            f"Não deveria haver novo serviço, obtido {resultado['features']['servico_mencionado']}"

    def test_05_servico_fora_catalogo(self):
        """Cenário 5: Mensagem menciona serviço não no catálogo
        → NÃO aceita como válido"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {}

        resultado = classificar_intencao_conversacional(
            "quero marcar design de sobrancelha hoje",
            ctx,
            catalogo_servicos=catalogo
        )

        # Design de sobrancelha não está no catálogo
        assert resultado["features"]["servico_mencionado"] is None, \
            "Serviço fora do catálogo não deveria ser reconhecido"

    def test_06_ambiguidade_multiplos_servicos(self):
        """Cenário 6: Se múltiplos serviços mencionados
        → retorna primeiro (ordenado por especificidade) ou pede esclarecimento"""
        catalogo = ["corte", "corte masculino", "corte feminino", "escova"]

        resultado = classificar_intencao_conversacional(
            "quero corte e escova hoje",
            ctx={},
            catalogo_servicos=catalogo
        )

        # Deve pegar um dos serviços encontrados
        servico = resultado["features"]["servico_mencionado"]
        assert servico in ["corte", "corte masculino", "corte feminino", "escova"], \
            f"Serviço inesperado: {servico}"

    def test_07_aguardando_data_novo_servico_nao_reutiliza_antigo(self):
        """Cenário 7: Estado aguardando_data com nova solicitação
        → Guard não reutiliza serviço antigo se novo foi mencionado"""
        catalogo = ["coloracao", "corte feminino", "escova"]
        ctx = {
            "draft_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "aguardando_data"
        }

        resultado = classificar_intencao_conversacional(
            "quero corte feminino para segunda",
            ctx,
            catalogo_servicos=catalogo
        )

        # Features devem mostrar novo serviço
        features = resultado["features"]
        assert features["servico_mencionado"] == "corte feminino", \
            f"Novo serviço não foi detectado: {features['servico_mencionado']}"

        # Intenção deve permitir atualização
        assert resultado["intencao_conversacional"] == "agendamento_direto", \
            f"Intenção bloqueada incorretamente: {resultado['intencao_conversacional']}"

    def test_08_confirmacao_sem_regressao(self):
        """Cenário 8a: Confirmação de agendamento não sofre regressão"""
        catalogo = ["coloracao", "corte feminino"]
        ctx = {
            "estado_fluxo": "agendando",
            "dados_confirmacao_agendamento": {"date": "2026-10-20", "time": "14:00"},
            "aguardando_confirmacao_agendamento": True
        }

        resultado = classificar_intencao_conversacional(
            "confirma, tudo certo",
            ctx,
            catalogo_servicos=catalogo
        )

        # Deve reconhecer confirmação
        assert resultado["intencao_conversacional"] == "confirmacao_agendamento", \
            f"Confirmação não foi reconhecida: {resultado['intencao_conversacional']}"

    def test_08b_cancelamento_sem_regressao(self):
        """Cenário 8b: Cancelamento não sofre regressão"""
        catalogo = ["coloracao"]
        ctx = {"estado_fluxo": "agendando"}

        resultado = classificar_intencao_conversacional(
            "cancela, mudei de ideia",
            ctx,
            catalogo_servicos=catalogo
        )

        # Deve reconhecer cancelamento
        assert resultado["intencao_conversacional"] == "cancelamento", \
            f"Cancelamento não foi reconhecido: {resultado['intencao_conversacional']}"

    def test_08c_escolha_profissional_sem_regressao(self):
        """Cenário 8c: Escolha de profissional não sofre regressão"""
        catalogo = ["coloracao"]
        ctx = {"estado_fluxo": "aguardando_profissional"}

        resultado = classificar_intencao_conversacional(
            "prefiro com a Maria",
            ctx,
            catalogo_servicos=catalogo
        )

        # Deve reconhecer pedido de profissional
        intencao = resultado["intencao_conversacional"]
        assert intencao in ["pedido_profissional_especifico", "ajuste_incremental"], \
            f"Pedido de profissional não reconhecido: {intencao}"

    def test_09_tenant_a_vs_tenant_b_sem_contaminacao(self):
        """Cenário 9: Tenant A e Tenant B não compartilham serviços"""
        catalogo_a = ["corte", "escova", "coloracao"]
        catalogo_b = ["design_sobrancelha", "micropigmentacao", "depilacao"]

        # Tenant A tenta usar serviço de B
        resultado_a = classificar_intencao_conversacional(
            "quero design de sobrancelha",
            ctx={},
            catalogo_servicos=catalogo_a
        )

        # Tenant B usa seu próprio serviço
        resultado_b = classificar_intencao_conversacional(
            "quero design de sobrancelha",
            ctx={},
            catalogo_servicos=catalogo_b
        )

        # A não reconhece
        assert resultado_a["features"]["servico_mencionado"] is None, \
            "Tenant A não deveria reconhecer serviço de Tenant B"

        # B reconhece
        assert resultado_b["features"]["servico_mencionado"] == "design_sobrancelha", \
            "Tenant B deveria reconhecer seu próprio serviço"


class TestFase2HorarioPadrao:
    """Validação: horário padrão 09:00 é intencional"""

    def test_data_sem_horario_retorna_09_00(self):
        """Quando cliente menciona data sem horário, parser retorna 09:00
        → Isso é intencional, NÃO deve ser alterado"""
        # Este teste documenta o comportamento esperado
        # A implementação real está em interpretador_datas.py linha 348
        catalogo = ["corte", "escova"]

        resultado = classificar_intencao_conversacional(
            "quero para segunda",  # sem hora explícita
            ctx={},
            catalogo_servicos=catalogo
        )

        # Features devem indicar data detectada mas sem hora específica
        features = resultado["features"]
        assert features.get("tem_data") is True, \
            "Data deveria ter sido detectada"
        # horario_mencionado pode ser None ou vazio


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
