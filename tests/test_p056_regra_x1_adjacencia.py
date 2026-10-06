#!/usr/bin/env python3
"""P0.5.6 — Teste da Regra X1: Rejeitar Adjacencia em Sugestoes

Objetivo: Validar que candidatos com adjacencia exata (N_fim == E_ini ou N_ini == E_fim)
sejam rejeitados nas sugestoes de horario.

Regra X1: Alem de rejeitar sobreposicao real, rejeitar:
  - N_fim == E_ini (novo termina quando evento comeca)
  - N_ini == E_fim (novo comeca quando evento termina)
"""

import asyncio
import sys
from datetime import datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.formatters import (
    _calcular_blocos_livres,
    gerar_sugestoes_de_horario,
)
from services.event_service_async import verificar_encaixe_exato


async def test_t1_novo_termina_no_inicio_evento():
    """T1: Evento 09:00-09:30, Candidato 09:30-10:00 => REJEITADO"""
    print("\n[T1] Novo termina no inicio do evento")

    data = datetime(2026, 10, 6)
    evento = (
        datetime(2026, 10, 6, 9, 0),
        datetime(2026, 10, 6, 9, 30)
    )
    candidato_inicio = datetime(2026, 10, 6, 9, 30)
    duracao = 30

    ocupados = [evento]
    sugestoes = gerar_sugestoes_de_horario(candidato_inicio, ocupados, duracao)

    esperado = "09:30 - 10:00"
    if esperado in sugestoes:
        print(f"[FAIL] {esperado} foi retornada mas deveria ser rejeitada")
        return False

    print(f"[OK] {esperado} foi corretamente rejeitada")
    return True


async def test_t2_novo_comeca_no_fim_evento():
    """T2: Evento 09:00-09:30, Candidato 08:30-09:00 => REJEITADO"""
    print("\n[T2] Novo comeca no fim do evento")

    data = datetime(2026, 10, 6)
    evento = (
        datetime(2026, 10, 6, 9, 0),
        datetime(2026, 10, 6, 9, 30)
    )
    candidato_inicio = datetime(2026, 10, 6, 8, 30)
    duracao = 30

    ocupados = [evento]
    sugestoes = gerar_sugestoes_de_horario(candidato_inicio, ocupados, duracao)

    esperado = "08:30 - 09:00"
    if esperado in sugestoes:
        print(f"[FAIL] {esperado} foi retornada mas deveria ser rejeitada")
        return False

    print(f"[OK] {esperado} foi corretamente rejeitada")
    return True


async def test_t3_novo_termina_no_inicio_evento2():
    """T3: Evento 10:00-10:30, Candidato 09:30-10:00 => REJEITADO"""
    print("\n[T3] Novo termina no inicio do segundo evento")

    data = datetime(2026, 10, 6)
    evento = (
        datetime(2026, 10, 6, 10, 0),
        datetime(2026, 10, 6, 10, 30)
    )
    candidato_inicio = datetime(2026, 10, 6, 9, 30)
    duracao = 30

    ocupados = [evento]
    sugestoes = gerar_sugestoes_de_horario(candidato_inicio, ocupados, duracao)

    esperado = "09:30 - 10:00"
    if esperado in sugestoes:
        print(f"[FAIL] {esperado} foi retornada mas deveria ser rejeitada")
        return False

    print(f"[OK] {esperado} foi corretamente rejeitada")
    return True


async def test_t4_novo_comeca_no_fim_evento2():
    """T4: Evento 10:00-10:30, Candidato 10:30-11:00 => REJEITADO"""
    print("\n[T4] Novo comeca no fim do segundo evento")

    data = datetime(2026, 10, 6)
    evento = (
        datetime(2026, 10, 6, 10, 0),
        datetime(2026, 10, 6, 10, 30)
    )
    candidato_inicio = datetime(2026, 10, 6, 10, 30)
    duracao = 30

    ocupados = [evento]
    sugestoes = gerar_sugestoes_de_horario(candidato_inicio, ocupados, duracao)

    esperado = "10:30 - 11:00"
    if esperado in sugestoes:
        print(f"[FAIL] {esperado} foi retornada mas deveria ser rejeitada")
        return False

    print(f"[OK] {esperado} foi corretamente rejeitada")
    return True


async def test_t5_sobreposicao_real():
    """T5: Evento 09:00-09:30, Candidato 09:20-09:50 => REJEITADO"""
    print("\n[T5] Sobreposicao real")

    data = datetime(2026, 10, 6)
    evento = (
        datetime(2026, 10, 6, 9, 0),
        datetime(2026, 10, 6, 9, 30)
    )
    candidato_inicio = datetime(2026, 10, 6, 9, 20)
    duracao = 30

    ocupados = [evento]
    sugestoes = gerar_sugestoes_de_horario(candidato_inicio, ocupados, duracao)

    esperado = "09:20 - 09:50"
    if esperado in sugestoes:
        print(f"[FAIL] {esperado} foi retornada mas deveria ser rejeitada")
        return False

    print(f"[OK] {esperado} foi corretamente rejeitada")
    return True


async def test_t6_sem_adjacencia_nem_sobreposicao():
    """T6: Evento 09:00-09:30, Candidato 10:00-10:30 => PERMITIDO"""
    print("\n[T6] Sem adjacencia nem sobreposicao")

    data = datetime(2026, 10, 6)
    evento = (
        datetime(2026, 10, 6, 9, 0),
        datetime(2026, 10, 6, 9, 30)
    )
    candidato_inicio = datetime(2026, 10, 6, 10, 0)
    duracao = 30

    ocupados = [evento]
    sugestoes = gerar_sugestoes_de_horario(candidato_inicio, ocupados, duracao)

    esperado = "10:00 - 10:30"
    if esperado not in sugestoes:
        print(f"[FAIL] {esperado} deveria ser retornada")
        return False

    print(f"[OK] {esperado} foi corretamente permitida")
    return True


async def test_t7_cenario_original():
    """T7: Cenario original - 09:30-10:00 nao pode aparecer"""
    print("\n[T7] Cenario original com dois eventos")

    data = datetime(2026, 10, 6)
    eventos = [
        (datetime(2026, 10, 6, 9, 0), datetime(2026, 10, 6, 9, 30)),
        (datetime(2026, 10, 6, 10, 0), datetime(2026, 10, 6, 10, 30)),
    ]
    solicitacao_inicio = datetime(2026, 10, 6, 9, 20)
    duracao = 30

    sugestoes = gerar_sugestoes_de_horario(solicitacao_inicio, eventos, duracao)

    nao_permitida = "09:30 - 10:00"
    if nao_permitida in sugestoes:
        print(f"[FAIL] {nao_permitida} foi retornada nas sugestoes")
        print(f"   Sugestoes: {sugestoes}")
        return False

    print(f"[OK] {nao_permitida} foi corretamente excluida das sugestoes")
    print(f"   Sugestoes retornadas: {sugestoes}")
    return True


async def main():
    print("=" * 80)
    print("TESTES DA REGRA X1: REJEICAO DE ADJACENCIA")
    print("=" * 80)

    testes = [
        test_t1_novo_termina_no_inicio_evento,
        test_t2_novo_comeca_no_fim_evento,
        test_t3_novo_termina_no_inicio_evento2,
        test_t4_novo_comeca_no_fim_evento2,
        test_t5_sobreposicao_real,
        test_t6_sem_adjacencia_nem_sobreposicao,
        test_t7_cenario_original,
    ]

    resultados = []
    for teste in testes:
        try:
            resultado = await teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            resultados.append(False)

    print("\n" + "=" * 80)
    print(f"RESULTADO: {sum(resultados)}/{len(resultados)} testes passaram")
    print("=" * 80)

    return all(resultados)


if __name__ == "__main__":
    sucesso = asyncio.run(main())
    sys.exit(0 if sucesso else 1)
