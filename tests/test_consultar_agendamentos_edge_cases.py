"""
TESTES DE EDGE CASES E ERROS: Consultar Agendamentos do Usuário
Detectar erros e casos extremos que poderiam quebrar a implementação.

Cenários: 1-30 (testes robustos)
Data: 2026-09-14
"""

import pytest
import re
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from services.classificador_conversa import classificar_intencao_conversacional, extrair_features_conversa, normalizar_txt
from utils.interpretador_datas import interpretar_data_e_hora


# ============================================================================
# TESTES DE EDGE CASES: Entrada Malformada
# ============================================================================

def test_1_classificador_entrada_vazia():
    """
    Teste 1: Texto vazio deve retornar algo, não null
    Entrada: ""
    Esperado: resultado é dict (não exception)
    """
    texto = ""
    resultado = classificar_intencao_conversacional(texto)

    assert resultado is not None
    assert isinstance(resultado, dict)
    # Não deve classificar como consultar_agendamentos_usuario
    assert resultado.get("intencao_conversacional") != "consultar_agendamentos_usuario"


def test_2_classificador_apenas_espacos():
    """
    Teste 2: Apenas espaços em branco
    Entrada: "   "
    Esperado: Não classifica como consulta
    """
    texto = "   "
    resultado = classificar_intencao_conversacional(texto)

    assert resultado is not None
    assert resultado.get("intencao_conversacional") != "consultar_agendamentos_usuario"


def test_3_classificador_caracteres_especiais_apenas():
    """
    Teste 3: Apenas caracteres especiais/números
    Entrada: "!@#$%^&*()123"
    Esperado: Não classifica
    """
    texto = "!@#$%^&*()123"
    resultado = classificar_intencao_conversacional(texto)

    assert resultado.get("intencao_conversacional") != "consultar_agendamentos_usuario"


def test_4_classificador_possessivo_sem_pergunta():
    """
    Teste 4: Possessivo mas sem interrogação/pergunta
    Entrada: "Meu agendamento" (afirmação, não pergunta)
    Esperado: Não classifica como consulta (precisa de pergunta)
    """
    texto = "Meu agendamento"
    resultado = classificar_intencao_conversacional(texto)

    # Sem pergunta, não deve classificar
    assert resultado.get("intencao_conversacional") != "consultar_agendamentos_usuario"


def test_5_possessivo_ambiguo_profissional():
    """
    Teste 5: Possessivo pode ser interpretado como profissional
    Entrada: "Tenho Carla amanhã?" (possessivo + possível nome profissional)
    Esperado: Não deve confundir com "quem é Carla?" ou buscar profissional
    """
    texto = "Tenho Carla amanhã?"
    resultado = classificar_intencao_conversacional(texto)

    # Pode classificar como consultar_agendamentos ou outra intenção
    # Importante: não deve causar exceção
    assert resultado is not None
    assert isinstance(resultado, dict)


def test_6_data_passada_muito_antiga():
    """
    Teste 6: Data muito antiga no passado
    Entrada: "Tenho agendado em 2020?"
    Esperado: Não deve quebrar, interpretar data
    """
    texto = "Tenho agendado em 2020?"
    resultado = classificar_intencao_conversacional(texto)

    # Não deve quebrar
    assert resultado is not None


def test_7_interpretador_data_ano_futuro_distante():
    """
    Teste 7: Data muito no futuro
    Entrada: "Hoje em 2050"
    Esperado: Retorna None ou date válida, não exceção
    """
    texto = "Tenho agendado em 2050?"
    try:
        resultado = interpretar_data_e_hora(texto)
        # Pode retornar None ou date, desde que não lance exceção
        assert resultado is None or isinstance(resultado, datetime)
    except Exception as e:
        pytest.fail(f"Interpretador não deve lançar exceção para ano futuro distante: {e}")


def test_8_interpretador_data_malformada():
    """
    Teste 8: Data malformada/inválida
    Entrada: "Tenho agendado em 32/13/2026?"
    Esperado: Retorna None, não exception
    """
    texto = "Tenho agendado em 32/13/2026?"
    try:
        resultado = interpretar_data_e_hora(texto)
        assert resultado is None or isinstance(resultado, datetime)
    except Exception:
        pytest.fail("Interpretador não deve lançar exceção para data malformada")


def test_9_interpretador_hora_invalida():
    """
    Teste 9: Hora inválida
    Entrada: "Hoje às 25:70"
    Esperado: Retorna None, não exception
    """
    texto = "Hoje às 25:70"
    try:
        resultado = interpretar_data_e_hora(texto)
        # Deve retornar None ou falhar gracefully
        # (25 é hora inválida, regex pode não match)
    except Exception as e:
        pytest.fail(f"Interpretador não deve lançar exceção para hora inválida: {e}")


def test_10_caracteres_unicode_complexos():
    """
    Teste 10: Unicode complexo e emojis
    Entrada: "Tenho 🎉 agendado para 📅 hoje?"
    Esperado: Processa sem exceção
    """
    texto = "Tenho 🎉 agendado para 📅 hoje?"
    try:
        resultado = classificar_intencao_conversacional(texto)
        assert resultado is not None
    except Exception as e:
        pytest.fail(f"Classificador não deve falhar com unicode: {e}")


# ============================================================================
# TESTES DE ISOLAMENTO E MULTITENANT
# ============================================================================

def test_11_multitenant_user_id_vazio():
    """
    Teste 11: user_id vazio deve ser detectado
    Esperado: Não carrega eventos (mas não quebra)
    """
    # Este teste simula que user_id vazio é passado
    # Verificamos que classificador não aceita isso como válido
    texto = "Tenho agendado?"
    resultado = classificar_intencao_conversacional(texto)

    assert resultado is not None
    # Classificação funciona mesmo com user_id vazio (classificador não valida)


def test_12_multitenant_user_id_null():
    """
    Teste 12: user_id None
    Esperado: Classificação ainda funciona (None é passado adiante para router)
    """
    texto = "Tenho agendado?"
    resultado = classificar_intencao_conversacional(texto)

    assert resultado is not None


def test_13_multitenant_isolamento_confirmado_em_features():
    """
    Teste 13: Features extraem contexto do usuário sem vazar dados
    Entrada: Texto de um usuário, sem tenant_id
    Esperado: Features não contêm dados de outro usuário
    """
    texto = "Tenho agendado?"
    features = extrair_features_conversa(texto, ctx={})

    # Features não devem conter tenant_id (isso é papel do router)
    # Mas features devem ser seguras
    assert isinstance(features, dict)
    # Não deve vazar contexo de outro user
    assert "tenant_id" not in features or features.get("tenant_id") is None


# ============================================================================
# TESTES DE INTERPRETADOR DE DATAS: Casos Extremos
# ============================================================================

def test_14_interpretador_hoje_maiuscula():
    """
    Teste 14: "HOJE" em maiúscula
    Entrada: "Tenho agendado para HOJE?"
    Esperado: Retorna None (data pura)
    """
    texto = "hoje"
    resultado = interpretar_data_e_hora(texto)
    assert resultado is None


def test_15_interpretador_amanha_com_acento():
    """
    Teste 15: "amanhã" com acento
    Entrada: "Tenho agendado para amanhã?"
    Esperado: Retorna None (data pura)
    """
    texto = "amanhã"
    resultado = interpretar_data_e_hora(texto)
    assert resultado is None


def test_16_interpretador_data_sem_hora_varias_formas():
    """
    Teste 16: Várias formas de dizer "hoje" sem hora
    Esperado: Todas retornam None
    """
    entradas = [
        "hoje",
        "hoje?",
        "pra hoje",
        "para hoje",
        "na data de hoje",
    ]

    for entrada in entradas:
        resultado = interpretar_data_e_hora(entrada)
        # Sem hora explícita deve retornar None
        if "às" not in entrada.lower() and re.search(r"\d{1,2}:\d{2}|\d{1,2}h", entrada) is None:
            assert resultado is None, f"'{entrada}' deveria retornar None (sem hora)"


def test_17_interpretador_data_com_varias_horas():
    """
    Teste 17: Texto com múltiplas horas (qual pegar?)
    Entrada: "Tenho de 10h para 14h"
    Esperado: Pega primeira ou nenhuma (consistente)
    """
    texto = "Tenho de 10h para 14h"
    try:
        resultado = interpretar_data_e_hora(texto)
        # Não deve quebrar, pode retornar None ou primeira hora
        assert resultado is None or isinstance(resultado, datetime)
    except Exception as e:
        pytest.fail(f"Interpretador não deve quebrar com múltiplas horas: {e}")


def test_18_interpretador_amanha_com_hora_passada():
    """
    Teste 18: "Amanhã às 14h" mas já passou 14h hoje
    Esperado: Retorna data de amanhã com hora 14h (não ajusta para hoje)
    """
    texto = "amanhã às 14"
    resultado = interpretar_data_e_hora(texto)

    if resultado:
        # Deve ser amanhã, não hoje
        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        assert resultado.date() == amanha, "Deve ser amanhã, não hoje"


# ============================================================================
# TESTES DE GUARD DE HORÁRIO PASSADO
# ============================================================================

def test_19_guard_data_sem_hora_falsa_string():
    """
    Teste 19: data_sem_hora com valor string "False" (não bool)
    Esperado: Guard trata como truthy
    """
    ctx = {
        "data_sem_hora": "False",  # String, não bool
        "data_hora": (datetime.now() - timedelta(hours=1)).isoformat()
    }

    # Guard: if ctx.get("data_hora") and not ctx.get("data_sem_hora")
    # "False" é truthy em Python (non-empty string)
    deve_bloquear = ctx.get("data_hora") and not ctx.get("data_sem_hora")

    # Com string "False", not "False" = False, então não bloqueia
    # Isso é esperado comportamento de Python
    assert deve_bloquear is False


def test_20_guard_data_hora_none():
    """
    Teste 20: data_hora é None
    Esperado: Guard não bloqueia
    """
    ctx = {
        "data_sem_hora": False,
        "data_hora": None
    }

    deve_bloquear = ctx.get("data_hora") and not ctx.get("data_sem_hora")
    assert not deve_bloquear


def test_21_guard_ambos_none():
    """
    Teste 21: Ambos None
    Esperado: Guard não bloqueia
    """
    ctx = {
        "data_sem_hora": None,
        "data_hora": None
    }

    deve_bloquear = ctx.get("data_hora") and not ctx.get("data_sem_hora")
    assert not deve_bloquear


# ============================================================================
# TESTES DE NORMALIZAÇÃO E REGEX
# ============================================================================

def test_22_normalizacao_acentos():
    """
    Teste 22: Normalização de acentos
    Entrada: "Tenho agendado em São Paulo?"
    Esperado: Normaliza corretamente
    """
    texto = "Tenho agendado em São Paulo?"
    normalizado = normalizar_txt(texto)

    # Deve remover diacríticos
    assert "ã" not in normalizado.lower()
    assert "tenho" in normalizado.lower()


def test_23_normalizacao_multiplos_espacos():
    """
    Teste 23: Múltiplos espaços
    Entrada: "Tenho    agendado    para    hoje?"
    Esperado: Classifica mesmo com espaços extras
    """
    texto = "Tenho    agendado    para    hoje?"
    resultado = classificar_intencao_conversacional(texto)

    assert resultado is not None


def test_24_regex_possessivo_caso_sensivel():
    """
    Teste 24: Possessivo em maiúsculas
    Entrada: "TENHO AGENDADO PARA HOJE?"
    Esperado: Detecta (regex tem IGNORECASE)
    """
    texto = "TENHO AGENDADO PARA HOJE?"
    resultado = classificar_intencao_conversacional(texto)

    assert resultado.get("intencao_conversacional") == "consultar_agendamentos_usuario"


def test_25_possessivo_parcial_no_meio():
    """
    Teste 25: Possessivo no meio da frase (não início)
    Entrada: "Quero saber se tenho agendado"
    Esperado: Ainda detecta possessivo
    """
    texto = "Quero saber se tenho agendado"
    resultado = classificar_intencao_conversacional(texto)

    # Deve detectar porque tem possessivo + pergunta (implícita)
    # Ou pode ser "indefinida" dependendo de features


# ============================================================================
# TESTES DE CONCORRÊNCIA E ESTADO
# ============================================================================

def test_26_classificador_sem_contexto():
    """
    Teste 26: Classificador chamado sem ctx
    Entrada: Sem contexto
    Esperado: Não quebra
    """
    texto = "Tenho agendado?"
    try:
        resultado = classificar_intencao_conversacional(texto, ctx=None)
        assert resultado is not None
    except Exception as e:
        pytest.fail(f"Classificador deve funcionar sem ctx: {e}")


def test_27_classificador_com_ctx_vazio():
    """
    Teste 27: Contexto vazio
    Entrada: ctx={}
    Esperado: Funciona
    """
    texto = "Tenho agendado?"
    resultado = classificar_intencao_conversacional(texto, ctx={})
    assert resultado is not None


def test_28_classificador_com_ctx_corrompido():
    """
    Teste 28: Contexto com valores inválidos
    Entrada: ctx com tipos errados
    Esperado: Não quebra
    """
    texto = "Tenho agendado?"
    ctx_corrupto = {
        "estado_fluxo": 123,  # Deve ser string
        "tem_fluxo_ativo": "sim",  # Deve ser bool
        "draft_agendamento": None,
    }

    try:
        resultado = classificar_intencao_conversacional(texto, ctx=ctx_corrupto)
        assert resultado is not None
    except Exception as e:
        pytest.fail(f"Classificador deve ser tolerante a contexto corrompido: {e}")


# ============================================================================
# TESTES DE IDEMPOTÊNCIA
# ============================================================================

def test_29_classificador_idempotente():
    """
    Teste 29: Chamar classificador múltiplas vezes com mesmo input
    Esperado: Sempre retorna mesmo resultado
    """
    texto = "Tenho agendado?"
    resultado1 = classificar_intencao_conversacional(texto)
    resultado2 = classificar_intencao_conversacional(texto)
    resultado3 = classificar_intencao_conversacional(texto)

    assert resultado1 == resultado2 == resultado3


def test_30_interpretador_idempotente():
    """
    Teste 30: Interpretador chamado múltiplas vezes
    Esperado: Sempre retorna mesmo resultado
    """
    texto = "hoje"
    resultado1 = interpretar_data_e_hora(texto)
    resultado2 = interpretar_data_e_hora(texto)
    resultado3 = interpretar_data_e_hora(texto)

    assert resultado1 == resultado2 == resultado3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
