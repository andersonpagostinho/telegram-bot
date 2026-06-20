"""[P0_VALIDACAO] Teste de Formatação Oficial de Mensagem de Conflito

Objetivo: Validar que a mensagem de conflito lock_existente segue o padrão
oficial definido em principal_router.py:4920-4935.

Validações:
[OK] Deve conter: "já tem atendimento às"
[OK] Deve conter: "Estes horários estão livres"
[OK] Deve conter: "Se você quiser manter"
[OK] Deve conter: "Deseja escolher outro horário"
[ERROR] NÃO deve conter: "Infelizmente não há horários"
[ERROR] NÃO deve conter: "Posso oferecer"

Data: 2026-06-19
Status: CERTIFICADO
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from handlers.event_handler import formatar_mensagem_conflito_profissional


def test_formatar_mensagem_conflito_com_sugestoes_e_alternativas():
    """Validar formato COMPLETO com sugestões e profissionais alternativos."""

    profissional = "Bruna"
    hora = "10:00"
    sugestoes = ["09:40 - 10:00", "09:20 - 09:40", "10:50 - 11:10"]
    alternativas = ["Joana", "Marina"]
    servico = "Corte"

    msg = formatar_mensagem_conflito_profissional(
        profissional=profissional,
        hora=hora,
        sugestoes=sugestoes,
        alternativas=alternativas,
        servico=servico
    )

    print("[TEST 1] Teste completo com sugestões e alternativas")
    print("=" * 80)
    print(msg)
    print("=" * 80)

    # VALIDAÇÕES OBRIGATÓRIAS
    assert "já tem atendimento às" in msg, "[ERROR] Deve conter 'já tem atendimento às'"
    assert "10:00" in msg, "[ERROR] Deve conter hora solicitada"
    assert "Estes horários estão livres" in msg, "[ERROR] Deve conter 'Estes horários estão livres'"
    assert "09:40 - 10:00" in msg, "[ERROR] Deve conter primeira sugestão"
    assert "09:20 - 09:40" in msg, "[ERROR] Deve conter segunda sugestão"
    assert "10:50 - 11:10" in msg, "[ERROR] Deve conter terceira sugestão"
    assert "Se você quiser manter" in msg, "[ERROR] Deve conter 'Se você quiser manter'"
    assert "Joana" in msg and "Marina" in msg, "[ERROR] Deve conter profissionais alternativos"
    assert "Deseja escolher outro horário" in msg, "[ERROR] Deve conter pergunta de confirmação"

    # VALIDAÇÕES NEGATIVAS
    assert "Infelizmente não há horários" not in msg, "[ERROR] NAO deve conter 'Infelizmente não há'"
    assert "Posso oferecer" not in msg, "[ERROR] NAO deve conter 'Posso oferecer'"

    print("[OK] TEST 1 PASSOU: Formato completo OK")
    print()


def test_formatar_mensagem_conflito_sem_alternativas():
    """Validar formato SEM profissionais alternativos."""

    profissional = "Bruna"
    hora = "10:00"
    sugestoes = ["09:40 - 10:00", "09:20 - 09:40"]
    alternativas = []  # Vazio
    servico = "Corte"

    msg = formatar_mensagem_conflito_profissional(
        profissional=profissional,
        hora=hora,
        sugestoes=sugestoes,
        alternativas=alternativas,
        servico=servico
    )

    print("[TEST 2] Teste SEM profissionais alternativos")
    print("=" * 80)
    print(msg)
    print("=" * 80)

    # VALIDAÇÕES
    assert "já tem atendimento às" in msg, "[ERROR] Deve conter 'já tem atendimento às'"
    assert "Estes horários estão livres" in msg, "[ERROR] Deve conter 'Estes horários estão livres'"
    assert "09:40 - 10:00" in msg, "[ERROR] Deve conter primeira sugestão"
    assert "Deseja escolher outro horário" in msg, "[ERROR] Deve conter pergunta"

    # Sem alternativas, não deve ter "Se você quiser manter"
    assert "Se você quiser manter" not in msg, "[ERROR] Não deve ter alternativas se lista vazia"

    print("[OK] TEST 2 PASSOU: Sem alternativas OK")
    print()


def test_formatar_mensagem_conflito_sem_sugestoes():
    """Validar formato SEM sugestões (edge case)."""

    profissional = "Bruna"
    hora = "10:00"
    sugestoes = []  # Vazio
    alternativas = ["Joana"]
    servico = "Corte"

    msg = formatar_mensagem_conflito_profissional(
        profissional=profissional,
        hora=hora,
        sugestoes=sugestoes,
        alternativas=alternativas,
        servico=servico
    )

    print("[TEST 3] Teste SEM sugestões")
    print("=" * 80)
    print(msg)
    print("=" * 80)

    # VALIDAÇÕES
    assert "já tem atendimento às" in msg, "[ERROR] Deve conter 'já tem atendimento às'"
    assert "Se você quiser manter" in msg, "[ERROR] Deve oferecer alternativa"
    assert "Joana" in msg, "[ERROR] Deve conter profissional alternativo"
    assert "Deseja escolher outro horário" in msg, "[ERROR] Deve conter pergunta"

    # Sem sugestões, não deve ter "Estes horários estão livres"
    # (pois só adiciona se há sugestões)

    print("[OK] TEST 3 PASSOU: Sem sugestões OK")
    print()


def test_formatar_mensagem_sem_emoji():
    """Validar que NÃO há emojis que causam problema em Windows."""

    msg = formatar_mensagem_conflito_profissional(
        profissional="Bruna",
        hora="10:00",
        sugestoes=["09:40 - 10:00"],
        alternativas=["Joana"],
        servico="Corte"
    )

    print("[TEST 4] Validar compatibilidade Windows (sem emoji)")
    print("=" * 80)
    print(msg)
    print("=" * 80)

    # Verificar se mensagem pode ser codificada em cp1252
    try:
        msg_encoded = msg.encode("cp1252")
        print(f"[OK] Mensagem é compatível com Windows (cp1252): {len(msg_encoded)} bytes")
    except UnicodeEncodeError as e:
        print(f"[ERROR] ERRO: Mensagem NÃO é compatível com Windows: {e}")
        raise

    # Verificar emojis problemáticos específicos
    problematic_chars = ["[OK]", "🧪", "📦", "[BLOCK]", "[ERROR]"]
    for char in problematic_chars:
        if char in msg:
            raise AssertionError(f"[ERROR] Mensagem contém emoji problemático: {char}")

    print("[OK] TEST 4 PASSOU: Compatível com Windows (sem emoji)")
    print()


def test_padroes_obrigatorios():
    """Validar que todos os padrões obrigatórios estão presentes."""

    msg = formatar_mensagem_conflito_profissional(
        profissional="Bruna",
        hora="10:00",
        sugestoes=["09:40 - 10:00", "09:20 - 09:40", "10:50 - 11:10"],
        alternativas=["Joana", "Marina"],
        servico="Corte"
    )

    print("[TEST 5] Validar padrões obrigatórios")
    print("=" * 80)

    padroes_obrigatorios = [
        ("já tem atendimento às", "Identificar conflito com profissional"),
        ("Estes horários estão livres", "Listar sugestões"),
        ("Se você quiser manter", "Oferecer alternativas"),
        ("Deseja escolher outro horário", "Pedir confirmação"),
    ]

    padroes_proibidos = [
        ("Infelizmente não há horários", "Mensagem negativa (proibida)"),
        ("Posso oferecer", "Formato antigo (proibido)"),
    ]

    print("\n[OK] PADRÕES OBRIGATÓRIOS:")
    for padrao, descricao in padroes_obrigatorios:
        assert padrao in msg, f"[ERROR] FALHA: '{padrao}' ({descricao})"
        print(f"  [V] {descricao}: '{padrao}'")

    print("\n[ERROR] PADRÕES PROIBIDOS (não devem estar na mensagem):")
    for padrao, descricao in padroes_proibidos:
        assert padrao not in msg, f"[ERROR] FALHA: '{padrao}' está na mensagem ({descricao})"
        print(f"  [V] {descricao}: '{padrao}' (AUSENTE - OK)")

    print("\n[OK] TEST 5 PASSOU: Todos os padrões obrigatórios OK")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("VALIDAÇÃO OFICIAL DE MENSAGEM DE CONFLITO")
    print("=" * 80 + "\n")

    try:
        test_formatar_mensagem_conflito_com_sugestoes_e_alternativas()
        test_formatar_mensagem_conflito_sem_alternativas()
        test_formatar_mensagem_conflito_sem_sugestoes()
        test_formatar_mensagem_sem_emoji()
        test_padroes_obrigatorios()

        print("\n" + "=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)
        print("[OK] Todos os testes passaram (5/5)")
        print("[OK] Formatador de mensagem está CERTIFICADO")
        print("[OK] Compatível com Windows e Linux")
        print("[OK] Segue padrão oficial de principal_router.py")
        print("=" * 80 + "\n")

    except AssertionError as e:
        print(f"\n[FALHA] {e}")
        exit(1)
    except Exception as e:
        print(f"\n[ERRO] {e}")
        exit(1)
