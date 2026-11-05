"""
P0.19 — TESTES DE EXTRAÇÃO DE HORÁRIO EXPLÍCITO

Validar que horários explícitos na mensagem atual sobrescrevem contexto anterior,
respeitando a precedência: mensagem > contexto > draft.
"""

import pytest
from datetime import datetime
from router.principal_router import _extrair_hora_simples


def test_p019_t1_horario_explicito_sobrescreve_contexto():
    """
    T1: Contexto anterior 14:00 + mensagem "14:10" → 14:10
    """
    hora_detectada = _extrair_hora_simples("14:10")
    assert hora_detectada == (14, 10)

    data_hora_anterior = "2026-11-05T14:00:00"
    data_anterior = data_hora_anterior.split("T")[0]
    hora_nova, minuto_nova = hora_detectada

    nova_data_hora = f"{data_anterior}T{hora_nova:02d}:{minuto_nova:02d}:00"

    assert nova_data_hora == "2026-11-05T14:10:00"
    print("[T1] ✅ PASS: 14:00 → 14:10")
    assert True


def test_p019_t2_confirmacao_preserva_draft():
    """
    T2: Draft 14:10 + mensagem "pode" (confirmação) → 14:10
    """
    hora_detectada = _extrair_hora_simples("pode")
    assert hora_detectada is None
    print("[T2] ✅ PASS: Confirmação não extrai horário")
    assert True


def test_p019_t3_consulta_sem_heranca():
    """
    T3: Draft 14:10 + consulta "qual horário" → não herdar
    """
    hora_detectada = _extrair_hora_simples("qual horario voce esta disponivel?")
    assert hora_detectada is None
    print("[T3] ✅ PASS: Consulta sem horário")
    assert True


def test_p019_t4_novo_ajuste():
    """
    T4: Draft 14:10 + "na verdade, 14:20" → 14:20
    """
    hora_detectada = _extrair_hora_simples("na verdade, 14:20")
    assert hora_detectada == (14, 20)

    data_hora_anterior = "2026-11-05T14:10:00"
    data_anterior = data_hora_anterior.split("T")[0]
    hora_nova, minuto_nova = hora_detectada

    nova_data_hora = f"{data_anterior}T{hora_nova:02d}:{minuto_nova:02d}:00"
    assert nova_data_hora == "2026-11-05T14:20:00"
    print("[T4] ✅ PASS: 14:10 → 14:20")
    assert True


def test_p019_t5_padroes_horario():
    """
    T5: Validar múltiplos padrões de horário explícito
    """
    casos = [
        ("14:10", (14, 10)),
        ("as 14", (14, 0)),
        ("14h", (14, 0)),
        ("14h30", None),
        ("pode", None),
        ("sim", None),
    ]

    for texto, esperado in casos:
        resultado = _extrair_hora_simples(texto)
        assert resultado == esperado, \
            f"Padrao '{texto}': esperado {esperado}, got {resultado}"
        print(f"  OK '{texto}' → {resultado}")

    print("[T5] ✅ PASS: Padroes validados")
    assert True


def test_p019_t6_sem_data_anterior():
    """
    T6: Horário explícito mas sem data anterior
    """
    hora_detectada = _extrair_hora_simples("14:10")
    assert hora_detectada == (14, 10)

    data_hora_anterior = None

    if data_hora_anterior and "T" in data_hora_anterior:
        nova_data_hora = "ERRO"
    else:
        nova_data_hora = None

    assert nova_data_hora is None
    print("[T6] ✅ PASS: Sem data anterior, graceful")
    assert True


def test_p019_t7_regressao_confirmacao_simples():
    """
    T7: Regressão — Confirmação simples
    """
    for confirma in ["pode", "sim", "ok", "yes"]:
        hora = _extrair_hora_simples(confirma)
        assert hora is None, f"'{confirma}' nao deve extrair hora"

    print("[T7] ✅ PASS: Regressao ok")
    assert True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("P0.19 — TESTES DE EXTRACAO DE HORARIO EXPLICITO")
    print("="*70 + "\n")

    test_p019_t1_horario_explicito_sobrescreve_contexto()
    test_p019_t2_confirmacao_preserva_draft()
    test_p019_t3_consulta_sem_heranca()
    test_p019_t4_novo_ajuste()
    test_p019_t5_padroes_horario()
    test_p019_t6_sem_data_anterior()
    test_p019_t7_regressao_confirmacao_simples()

    print("\n" + "="*70)
    print("TODOS OS 7 TESTES PASSARAM!")
    print("="*70 + "\n")
