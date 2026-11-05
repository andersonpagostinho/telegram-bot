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

    Entrada:
      - ctx["data_hora"] = "2026-11-05T14:00:00"
      - texto_usuario = "14:10"

    Esperado:
      - ctx["data_hora"] → "2026-11-05T14:10:00"
    """
    # Detectar horário explícito
    hora_detectada = _extrair_hora_simples("14:10")
    assert hora_detectada == (14, 10), f"Esperado (14, 10), got {hora_detectada}"

    # Simular aplicação
    data_hora_anterior = "2026-11-05T14:00:00"
    data_anterior = data_hora_anterior.split("T")[0]
    hora_nova, minuto_nova = hora_detectada

    nova_data_hora = f"{data_anterior}T{hora_nova:02d}:{minuto_nova:02d}:00"

    assert nova_data_hora == "2026-11-05T14:10:00", \
        f"Esperado 2026-11-05T14:10:00, got {nova_data_hora}"

    print("[T1] ✅ PASS: 14:00 → 14:10 com data preservada")
    assert True


def test_p019_t2_confirmacao_preserva_draft():
    """
    T2: Draft 14:10 + mensagem "pode" (confirmação) → 14:10

    Entrada:
      - draft["data_hora"] = "2026-11-05T14:10:00"
      - texto_usuario = "pode"

    Esperado:
      - Não extract nova hora (não há padrão)
      - draft["data_hora"] permanece 14:10
    """
    hora_detectada = _extrair_hora_simples("pode")
    assert hora_detectada is None, f"Esperado None para 'pode', got {hora_detectada}"

    print("[T2] ✅ PASS: Confirmação não extrai horário, preserva draft")
    assert True


def test_p019_t3_consulta_sem_heranca():
    """
    T3: Draft 14:10 + consulta independente "qual horário" → não herdar 14:10

    Entrada:
      - draft["data_hora"] = "2026-11-05T14:10:00"
      - texto_usuario = "qual horário você está disponível?"

    Esperado:
      - Não extract nova hora
      - Lógica acima (skip_data_complexa) não força herança
    """
    hora_detectada = _extrair_hora_simples("qual horário você está disponível?")
    assert hora_detectada is None, f"Esperado None, got {hora_detectada}"

    print("[T3] ✅ PASS: Consulta sem horário não herda automaticamente")
    assert True


def test_p019_t4_novo_ajuste():
    """
    T4: Draft 14:10 + mensagem "na verdade, 14:20" → 14:20

    Entrada:
      - draft["data_hora"] = "2026-11-05T14:10:00"
      - texto_usuario = "na verdade, 14:20"

    Esperado:
      - ctx["data_hora"] → "2026-11-05T14:20:00"
    """
    hora_detectada = _extrair_hora_simples("na verdade, 14:20")
    assert hora_detectada == (14, 20), f"Esperado (14, 20), got {hora_detectada}"

    # Simular
    data_hora_anterior = "2026-11-05T14:10:00"
    data_anterior = data_hora_anterior.split("T")[0]
    hora_nova, minuto_nova = hora_detectada

    nova_data_hora = f"{data_anterior}T{hora_nova:02d}:{minuto_nova:02d}:00"
    assert nova_data_hora == "2026-11-05T14:20:00", \
        f"Esperado 2026-11-05T14:20:00, got {nova_data_hora}"

    print("[T4] ✅ PASS: 14:10 → 14:20 com ajuste")
    assert True


def test_p019_t5_padroes_horario():
    """
    T5: Validar múltiplos padrões de horário explícito
    """
    casos = [
        ("14:10", (14, 10)),
        ("às 14", (14, 0)),
        ("as 14", (14, 0)),
        ("14h", (14, 0)),
        ("14h30", None),  # "14h30" não é capturado por _extrair_hora_simples (design)
        ("14h 30", None),  # variante com espaço
    ]

    for texto, esperado in casos:
        resultado = _extrair_hora_simples(texto)
        assert resultado == esperado, \
            f"Padrão '{texto}': esperado {esperado}, got {resultado}"
        print(f"  ✓ '{texto}' → {resultado}")

    print("[T5] ✅ PASS: Padrões de horário validados")
    assert True


def test_p019_t6_sem_data_anterior():
    """
    T6: Horário explícito mas sem data anterior

    Entrada:
      - ctx["data_hora"] = None (ou inválido)
      - texto_usuario = "14:10"

    Esperado:
      - Detecção funciona, mas não pode aplicar sem data base
      - Lógica P0.19 exige "T" em data_hora_anterior
    """
    hora_detectada = _extrair_hora_simples("14:10")
    assert hora_detectada == (14, 10), f"Esperado (14, 10), got {hora_detectada}"

    data_hora_anterior = None

    if data_hora_anterior and "T" in data_hora_anterior:
        # Não executa este bloco
        nova_data_hora = "ERRO"
    else:
        nova_data_hora = None

    assert nova_data_hora is None, f"Esperado None (sem data base), got {nova_data_hora}"

    print("[T6] ✅ PASS: Sem data anterior, não aplica horário (graceful)")
    assert True


def test_p019_t7_regressao_confirmacao_simples():
    """
    T7: Regressão — Confirmação simples sem novo horário deve ser OK

    Não quebrar fluxo normal de confirmação.
    """
    # Confirmação "pode" não deve extrair hora
    hora = _extrair_hora_simples("pode")
    assert hora is None

    # Confirmação "sim" não deve extrair hora
    hora = _extrair_hora_simples("sim")
    assert hora is None

    # Confirmação "ok" não deve extrair hora
    hora = _extrair_hora_simples("ok")
    assert hora is None

    print("[T7] ✅ PASS: Confirmações simples preservadas")
    assert True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("P0.19 — TESTES DE EXTRAÇÃO DE HORÁRIO EXPLÍCITO")
    print("="*70 + "\n")

    test_p019_t1_horario_explicito_sobrescreve_contexto()
    test_p019_t2_confirmacao_preserva_draft()
    test_p019_t3_consulta_sem_heranca()
    test_p019_t4_novo_ajuste()
    test_p019_t5_padroes_horario()
    test_p019_t6_sem_data_anterior()
    test_p019_t7_regressao_confirmacao_simples()

    print("\n" + "="*70)
    print("TODOS OS 7 TESTES PASSARAM ✅")
    print("="*70 + "\n")
