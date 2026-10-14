"""
P0 - Testes da Alternativa A: Nova feature tem_contexto_servico_ou_draft

Validações:
- Feature original mantém semântica
- Nova feature considera draft.servico
- Pergunta durante draft é classificada corretamente
- Sem regressão em outros fluxos (cancelamento, ajuste, agendamento)
- Sem listas fixas de padrões
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.classificador_conversa import (
    extrair_features_conversa,
    classificar_intencao_conversacional,
    normalizar_txt
)


def test_feature_original_sem_draft():
    """T1: Feature original sem draft deve funcionar normalmente"""
    texto = "tem corte disponível?"
    f = extrair_features_conversa(texto, ctx={})

    assert f["tem_pergunta"] is True, "Deve detectar pergunta"
    assert f["tem_contexto_servico"] is True, "Deve detectar 'corte' no texto"
    assert f.get("tem_contexto_servico_ou_draft") is True, "Nova feature deve ser True (por tem_contexto_servico)"
    print("[T1] PASS: Feature original sem draft funciona")


def test_feature_nova_com_draft():
    """T2: Nova feature com draft.servico deve ser True mesmo sem serviço no texto"""
    texto = "quais você tem?"
    ctx = {"draft_agendamento": {"servico": "corte", "profissional": "Bruna"}}
    f = extrair_features_conversa(texto, ctx)

    assert f["tem_pergunta"] is True, "Deve detectar pergunta"
    assert f["tem_contexto_servico"] is False, "Texto não menciona serviço"
    assert f.get("tem_contexto_servico_ou_draft") is True, "Nova feature deve ser True (via draft)"
    print("[T2] PASS: Nova feature com draft funciona")


def test_feature_nova_sem_draft():
    """T3: Nova feature sem draft deve ser False se texto também não tem serviço"""
    texto = "quais você tem?"
    ctx = {}
    f = extrair_features_conversa(texto, ctx)

    assert f["tem_pergunta"] is True
    assert f["tem_contexto_servico"] is False, "Texto não menciona serviço"
    assert f.get("tem_contexto_servico_ou_draft") is False, "Nova feature False sem draft/serviço"
    print("[T3] PASS: Nova feature sem draft é False")


def test_feature_nova_draft_sem_servico():
    """T4: Draft sem serviço não deve ativar nova feature"""
    texto = "quais você tem?"
    ctx = {"draft_agendamento": {"profissional": "Bruna"}}  # Sem servico
    f = extrair_features_conversa(texto, ctx)

    assert f["tem_contexto_servico"] is False
    assert f.get("tem_contexto_servico_ou_draft") is False, "Sem serviço no draft"
    print("[T4] PASS: Draft sem servico não ativa nova feature")


def test_classificacao_pergunta_com_draft():
    """T5: Pergunta durante draft deve ser classificada como consulta_disponibilidade_servico"""
    texto = "quais você tem?"
    ctx = {"draft_agendamento": {"servico": "corte"}, "estado_fluxo": "agendando"}
    resultado = classificar_intencao_conversacional(texto, ctx)

    assert resultado["intencao_conversacional"] == "consulta_disponibilidade_servico", \
        f"Esperado 'consulta_disponibilidade_servico', got {resultado['intencao_conversacional']}"
    print("[T5] PASS: Pergunta com draft classificada como consulta_disponibilidade_servico")


def test_cancelamento_mantém_semantica():
    """T6: Cancelamento não deve ser afetado pela nova feature"""
    texto = "nao vou"
    ctx = {"draft_agendamento": {"servico": "corte"}}
    resultado = classificar_intencao_conversacional(texto, ctx)

    assert resultado["intencao_conversacional"] == "cancelamento", \
        f"Cancelamento deve funcionar, got {resultado['intencao_conversacional']}"
    print("[T6] PASS: Cancelamento mantém semântica")


def test_ajuste_incremental_mantém_semantica():
    """T7: Ajuste incremental não deve ser afetado (não alteramos linha 376 ainda)"""
    texto = "quero trocar de profissional"
    ctx = {"draft_agendamento": {"servico": "corte"}, "estado_fluxo": "agendando"}
    resultado = classificar_intencao_conversacional(texto, ctx)

    assert resultado["intencao_conversacional"] == "ajuste_incremental", \
        f"Ajuste deve funcionar, got {resultado['intencao_conversacional']}"
    print("[T7] PASS: Ajuste incremental mantém semântica")


def test_pergunta_sem_draft_nao_afetada():
    """T8: Pergunta normal sem draft deve funcionar como antes"""
    texto = "tem corte?"
    ctx = {}
    resultado = classificar_intencao_conversacional(texto, ctx)

    # Pode ser "consulta_servico" ou outro, mas não deve ser "indefinida"
    assert resultado["intencao_conversacional"] in ["consulta_servico", "consulta_disponibilidade_servico"], \
        f"Pergunta normal deve classificar, got {resultado['intencao_conversacional']}"
    print("[T8] PASS: Pergunta sem draft não é afetada")


def test_variacoes_pergunta_com_draft():
    """T9: Variações de pergunta com draft devem todos classificar como consulta_disponibilidade_servico"""
    variacoes = [
        "quais você tem?",
        "quem faz escova?",
        "tem profissional disponível?",
        "qual profissional posso escolher?"
    ]
    ctx = {"draft_agendamento": {"servico": "escova"}, "estado_fluxo": "agendando"}

    for texto in variacoes:
        resultado = classificar_intencao_conversacional(texto, ctx)
        assert resultado["intencao_conversacional"] == "consulta_disponibilidade_servico", \
            f"Falhou para '{texto}': got {resultado['intencao_conversacional']}"

    print(f"[T9] PASS: Todas as {len(variacoes)} variações classificadas corretamente")


def test_sem_lista_fixa():
    """T10: Solução não usa lista fixa de padrões (verifica que código não tem strings fixas)"""
    import inspect
    from services.classificador_conversa import extrair_features_conversa

    source = inspect.getsource(extrair_features_conversa)

    # Deve não conter lista fixa de padrões como
    # ("quais voce tem", "quais profissionais", ...)
    assert '("quais voce tem"' not in source, "Não deve ter lista fixa"
    assert '"quem tem"' not in source, "Não deve ter lista fixa"
    assert '"quem atende"' not in source, "Não deve ter lista fixa"

    print("[T10] PASS: Sem lista fixa de padrões")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTES UNITARIOS: Alternativa A - Nova Feature Contextual")
    print("="*80 + "\n")

    test_feature_original_sem_draft()
    test_feature_nova_com_draft()
    test_feature_nova_sem_draft()
    test_feature_nova_draft_sem_servico()
    test_classificacao_pergunta_com_draft()
    test_cancelamento_mantém_semantica()
    test_ajuste_incremental_mantém_semantica()
    test_pergunta_sem_draft_nao_afetada()
    test_variacoes_pergunta_com_draft()
    test_sem_lista_fixa()

    print("\n" + "="*80)
    print("RESULTADO: 10/10 TESTES PASSARAM")
    print("="*80 + "\n")
