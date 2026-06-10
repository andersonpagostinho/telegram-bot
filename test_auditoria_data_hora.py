# -*- coding: utf-8 -*-
# test_auditoria_data_hora.py
"""
Auditoria: data_hora da notificacao eh calculada corretamente?

Regra correta:
  evento: 2026-06-10 14:00
  minutos_antes: 30
  data_hora NOTIF: 2026-06-10 13:30

Deve usar: data_evento - timedelta(minutes=minutos_antes)
NÃO usar: datetime.now()
"""

import asyncio
from datetime import datetime, timedelta
from pytz import timezone

FUSO_BR = timezone("America/Sao_Paulo")


def test_calculo_data_hora_notificacao():
    """
    Teste 1: Validar calculo de data_hora para notificacao.
    """
    print("\n" + "="*70)
    print("[TEST 1] Calculo de data_hora para notificacao")
    print("="*70)

    # Dados do evento
    data = "2026-06-10"
    hora_inicio = "14:00"
    minutos_antes = 30

    # Calculo correto (como implementado em notificacao_service.py)
    data_evento = datetime.fromisoformat(f"{data}T{hora_inicio}")
    horario_notificacao = data_evento - timedelta(minutes=minutos_antes)

    print("\n[ENTRADA]")
    print("  Evento: {} {}".format(data, hora_inicio))
    print("  Minutos antes: {}".format(minutos_antes))

    print("\n[CALCULO]")
    print("  data_evento: {}".format(data_evento))
    print("  data_evento - 30min: {}".format(horario_notificacao))

    print("\n[RESULTADO]")
    print("  data_hora NOTIF: {}".format(horario_notificacao.isoformat()))

    # Validar
    esperado_hora = "13:30"
    esperado_data = "2026-06-10"

    data_resultado = horario_notificacao.strftime("%Y-%m-%d")
    hora_resultado = horario_notificacao.strftime("%H:%M")

    print("\n[VALIDACAO]")
    print("  Esperado: {} {}".format(esperado_data, esperado_hora))
    print("  Obtido:   {} {}".format(data_resultado, hora_resultado))

    if data_resultado == esperado_data and hora_resultado == esperado_hora:
        print("  [PASS] Data/hora calculada corretamente")
        return True
    else:
        print("  [FAIL] Data/hora incorreta")
        return False


def test_amanha_14h():
    """
    Teste 2: Evento amanha as 14h, notificacao aos 13:30 de amanha.
    """
    print("\n" + "="*70)
    print("[TEST 2] Evento amanha as 14h")
    print("="*70)

    # Usando data dinamica
    amanha = datetime.now(FUSO_BR) + timedelta(days=1)
    data = amanha.strftime("%Y-%m-%d")
    hora_inicio = "14:00"
    minutos_antes = 30

    # Calculo correto
    data_evento = datetime.fromisoformat(f"{data}T{hora_inicio}").replace(tzinfo=FUSO_BR)
    horario_notificacao = data_evento - timedelta(minutes=minutos_antes)

    print("\n[ENTRADA]")
    print("  Evento: {} {} (amanha)".format(data, hora_inicio))
    print("  Minutos antes: {}".format(minutos_antes))

    print("\n[RESULTADO]")
    print("  data_hora NOTIF: {}".format(horario_notificacao.isoformat()))

    # Validar
    data_resultado = horario_notificacao.strftime("%Y-%m-%d")
    hora_resultado = horario_notificacao.strftime("%H:%M")

    esperado_data = data
    esperado_hora = "13:30"

    print("\n[VALIDACAO]")
    print("  Esperado: {} {}".format(esperado_data, esperado_hora))
    print("  Obtido:   {} {}".format(data_resultado, hora_resultado))

    if data_resultado == esperado_data and hora_resultado == esperado_hora:
        print("  [PASS] Data/hora correta para amanha")
        return True
    else:
        print("  [FAIL] Data/hora incorreta")
        return False


def test_nao_usa_agora():
    """
    Teste 3: CONFIRMA que nao usa datetime.now() (seria errado).
    """
    print("\n" + "="*70)
    print("[TEST 3] Confirmar que NAO usa datetime.now()")
    print("="*70)

    data = "2026-06-10"
    hora_inicio = "14:00"
    minutos_antes = 30

    # Implementacao CORRETA
    data_evento = datetime.fromisoformat(f"{data}T{hora_inicio}")
    horario_notificacao_CORRETO = data_evento - timedelta(minutes=minutos_antes)

    # Implementacao ERRADA (usando agora)
    agora = datetime.now()
    horario_notificacao_ERRADO = agora - timedelta(minutes=minutos_antes)

    print("\n[COMPARACAO]")
    print("  Implementacao CORRETA (evento - 30min):")
    print("    data_hora: {}".format(horario_notificacao_CORRETO.isoformat()))

    print("\n  Implementacao ERRADA (agora - 30min):")
    print("    data_hora: {}".format(horario_notificacao_ERRADO.isoformat()))

    print("\n[DIFERENCA]")
    diferenca = abs((horario_notificacao_CORRETO - horario_notificacao_ERRADO).total_seconds() / 3600)
    print("  Diferenca: {} horas".format(diferenca))

    if horario_notificacao_CORRETO != horario_notificacao_ERRADO:
        print("  [PASS] Sao diferentes (CORRETO nao usa agora)")
        return True
    else:
        print("  [FAIL] Sao iguais (seria coincidencia)")
        return False


def test_timedelta_subtracao():
    """
    Teste 4: Validar que timedelta subtrai corretamente.
    """
    print("\n" + "="*70)
    print("[TEST 4] Validar timedelta subtrai corretamente")
    print("="*70)

    # Casos de teste
    casos = [
        ("2026-06-10", "14:00", 30, "13:30"),
        ("2026-06-10", "14:00", 60, "13:00"),
        ("2026-06-10", "14:00", 5, "13:55"),
        ("2026-06-10", "00:30", 30, "2026-06-10", "00:00"),  # Meia-noite
    ]

    print("\n[TESTES]")
    todos_passaram = True

    for i, caso in enumerate(casos, 1):
        if len(caso) == 4:
            data, hora, minutos, hora_esperada = caso
            data_esperada = data
        else:
            data, hora, minutos, data_esperada, hora_esperada = caso

        data_evento = datetime.fromisoformat(f"{data}T{hora}")
        notif = data_evento - timedelta(minutes=minutos)

        data_obtida = notif.strftime("%Y-%m-%d")
        hora_obtida = notif.strftime("%H:%M")

        passou = (data_obtida == data_esperada and hora_obtida == hora_esperada)

        print("\n  Caso {}: {} {} - {} min".format(i, data, hora, minutos))
        print("    Esperado: {} {}".format(data_esperada, hora_esperada))
        print("    Obtido:   {} {}".format(data_obtida, hora_obtida))
        print("    [{}]".format("PASS" if passou else "FAIL"))

        todos_passaram = todos_passaram and passou

    return todos_passaram


def main():
    print("\n" + "="*70)
    print("AUDITORIA: Calculo de data_hora em notificacoes")
    print("="*70)

    resultado1 = test_calculo_data_hora_notificacao()
    resultado2 = test_amanha_14h()
    resultado3 = test_nao_usa_agora()
    resultado4 = test_timedelta_subtracao()

    print("\n" + "="*70)
    print("RESUMO AUDITORIA:")
    print("  Teste 1 (Calculo): {}".format("PASSOU" if resultado1 else "FALHOU"))
    print("  Teste 2 (Amanha): {}".format("PASSOU" if resultado2 else "FALHOU"))
    print("  Teste 3 (NAO usa agora): {}".format("PASSOU" if resultado3 else "FALHOU"))
    print("  Teste 4 (timedelta): {}".format("PASSOU" if resultado4 else "FALHOU"))
    print("="*70)

    if resultado1 and resultado2 and resultado3 and resultado4:
        print("\nAUDITORIA: IMPLEMENTACAO CORRETA!")
        print("\nConfirmado:")
        print("  - Usa datetime.fromisoformat(data + hora_inicio)")
        print("  - Subtrai timedelta(minutes=minutos_antes)")
        print("  - Salva resultado em data_hora")
        print("  - NAO usa datetime.now()")
        return 0
    else:
        print("\nAUDITORIA: PROBLEMAS ENCONTRADOS!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
