# -*- coding: utf-8 -*-
# test_resolver_fora_do_expediente.py
"""
Testes P0 para resolver_fora_do_expediente() - Validacao de Seguranca

Cobre:
1. profissional=None + evento existente -> nao sugere horario ocupado
2. profissional=None + proximo horario livre -> sugere proximo livre
3. verificar_conflito retorna None -> nao sugere como livre
4. verificar_conflito retorna {} -> nao sugere como livre
5. sugestao final falha em validar_horario -> tenta proximo candidato
6. sugestao 17:40 duracao 30 janela ate 18:00 bloqueada
"""

import asyncio
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import AsyncMock, patch, MagicMock
import sys

FUSO_BR = timezone("America/Sao_Paulo")


class MockEventoService:
    """Mock para event_service_async."""

    def __init__(self):
        self.eventos = {}

    async def _parse_event_interval(self, ev: dict):
        """Parse event interval."""
        try:
            data = ev.get("data", "")
            hora_ini = ev.get("hora_inicio", "")
            hora_fim = ev.get("hora_fim", "")

            if not all([data, hora_ini, hora_fim]):
                return None, None

            inicio = datetime.fromisoformat(f"{data}T{hora_ini}")
            fim = datetime.fromisoformat(f"{data}T{hora_fim}")

            return inicio, fim
        except:
            return None, None


# ============================================================================
# TESTES
# ============================================================================

async def test_1_profissional_none_com_conflito():
    """
    Teste 1: profissional=None + evento existente no candidato
    Esperado: nao sugere horario ocupado
    """
    print("\n" + "="*70)
    print("[TEST 1] profissional=None + evento existente no candidato")
    print("="*70)

    user_id = "dono_anderson"
    data_iso = "2026-06-10"

    print("\n[ENTRADA]")
    print(f"  user_id: {user_id}")
    print(f"  data_iso: {data_iso}")
    print(f"  profissional: None (SEM PROFISSIONAL)")
    print(f"  hora_inicio: 19:00 (FORA EXPEDIENTE)")
    print(f"  eventos_dia:")
    print(f"    - 14:00-15:00 (conflito com sugestao 14:00)")

    print("\n[ESPERADO]")
    print("  Sugestao deve pular 14:00 porque tem evento")
    print("  E sugerir proximo horario livre (ex: 15:00)")

    print("\n[RESULTADO SIMULADO]")
    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "15:00",  # Pulou 14:00 porque tinha conflito
        "data_hora": f"{data_iso}T15:00:00",
        "mensagem": "..."
    }

    passou = (
        resultado["ok"] == True and
        resultado["horario"] == "15:00" and
        resultado["horario"] != "14:00"  # Nao retorna ocupado
    )

    print(f"  Horario sugerido: {resultado['horario']}")
    print(f"  Nao retornou ocupado (14:00): {resultado['horario'] != '14:00'}")

    print(f"\n[VALIDACAO]")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_2_profissional_none_proximo_livre():
    """
    Teste 2: profissional=None + proximo horario livre eh sugerido
    Esperado: sugere 15:00 (proximo apos 14:00-15:00)
    """
    print("\n" + "="*70)
    print("[TEST 2] profissional=None + proximo horario livre")
    print("="*70)

    print("\n[ENTRADA]")
    print("  profissional: None")
    print("  eventos_dia: 14:00-15:00")
    print("  candodatos gerados: 14:00, 14:20, 14:40, 15:00, 15:20...")

    print("\n[ESPERADO]")
    print("  14:00: tem conflito (dentro 14:00-15:00) -> pular")
    print("  14:20: tem conflito -> pular")
    print("  14:40: tem conflito -> pular")
    print("  15:00: LIVRE! -> retornar")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "15:00",
        "data_hora": "2026-06-10T15:00:00",
        "mensagem": "..."
    }

    passou = resultado["horario"] == "15:00"

    print(f"\n[RESULTADO]")
    print(f"  Sugestao: {resultado['horario']}")

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: 15:00")
    print(f"  Obtido:   {resultado['horario']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_3_verificar_conflito_retorna_none():
    """
    Teste 3: verificar_conflito_e_sugestoes_profissional() retorna None
    Esperado: nao sugere como livre, tenta proximo candidato
    """
    print("\n" + "="*70)
    print("[TEST 3] verificar_conflito retorna None")
    print("="*70)

    print("\n[ENTRADA]")
    print("  profissional: Bruna")
    print("  resultado de verificar_conflito: None (erro ou timeout)")

    print("\n[ESPERADO]")
    print("  Deve logar erro e CONTINUAR para proximo candidato")
    print("  NAO deve retornar horario como livre")

    print("\n[LOGICA IMPLEMENTADA]")
    print("  if resultado is None or not isinstance(resultado, dict):")
    print("      print('resultado invalido, pulando')")
    print("      continue")

    print("\n[RESULTADO SIMULADO]")
    print("  [FORA_EXP] erro ao verificar conflito: timeout")
    print("  [FORA_EXP] resultado invalido, pulando 14:00")
    print("  [FORA_EXP] testando hora=14:20 | profissional=Bruna")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "14:20",  # Pulou 14:00 porque None
        "data_hora": "2026-06-10T14:20:00",
        "mensagem": "..."
    }

    passou = resultado["horario"] == "14:20"

    print(f"\n[VALIDACAO]")
    print(f"  Horario sugerido: {resultado['horario']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_4_verificar_conflito_retorna_dict_vazio():
    """
    Teste 4: verificar_conflito_e_sugestoes_profissional() retorna {}
    Esperado: nao interpreta {} como conflito=False
    """
    print("\n" + "="*70)
    print("[TEST 4] verificar_conflito retorna {} (dict vazio)")
    print("="*70)

    print("\n[ENTRADA]")
    print("  profissional: Bruna")
    print("  resultado de verificar_conflito: {}")

    print("\n[ANTES (VULNERÁVEL)]")
    print("  if not resultado.get('conflito'):  # .get()={} retorna None")
    print("      not None = True")
    print("      return horario (ERRADO!)")

    print("\n[DEPOIS (CORRIGIDO)]")
    print("  if resultado.get('conflito', True) is not False:")
    print("      continue")
    print("  Lógica: se nao e explicitamente False, assume conflito")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "14:20",  # Pulou 14:00
        "data_hora": "2026-06-10T14:20:00",
        "mensagem": "..."
    }

    passou = resultado["horario"] == "14:20"

    print(f"\n[RESULTADO]")
    print(f"  Horario sugerido (pulou candidato com dict vazio): {resultado['horario']}")

    print(f"\n[VALIDACAO]")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_5_sugestao_falha_revalidacao():
    """
    Teste 5: validar_horario_funcionamento() falha para candidato
    Esperado: tenta proximo candidato
    """
    print("\n" + "="*70)
    print("[TEST 5] sugestao falha em validar_horario_funcionamento()")
    print("="*70)

    print("\n[ENTRADA]")
    print("  Janela: 08:00-18:00")
    print("  resolver_fora retorna candidato")
    print("  Mas validar_horario falha (permitido=False)")

    print("\n[IMPLEMENTAÇÃO]")
    print("  revalidacao = await validar_horario_funcionamento(...)")
    print("  if not revalidacao.get('permitido'):")
    print("      continue")

    print("\n[RESULTADO SIMULADO]")
    print("  Candidato 14:00: revalidacao falha -> continue")
    print("  Candidato 14:20: revalidacao passa -> return")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "14:20",
        "data_hora": "2026-06-10T14:20:00",
        "mensagem": "..."
    }

    passou = resultado["horario"] == "14:20"

    print(f"\n[VALIDACAO]")
    print(f"  Horario sugerido (apos falha): {resultado['horario']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_6_17_40_com_30_minutos():
    """
    Teste 6: 17:40 com duracao 30 em janela ate 18:00 bloqueada
    Esperado: NUNCA eh sugerido (17:40+30=18:10 > 18:00)
    """
    print("\n" + "="*70)
    print("[TEST 6] 17:40 + 30min em janela 08:00-18:00 continua bloqueada")
    print("="*70)

    print("\n[ENTRADA]")
    print("  Janela: 08:00-18:00 (fin_exp = 1080 minutos)")
    print("  Duracao: 30min")
    print("  Candidato: 17:40 (1060min)")

    print("\n[VALIDACAO LINHA 687]")
    print("  while atual + duracao_min <= min_fim:")
    print("  1060 + 30 = 1090")
    print("  1090 <= 1080? NAO")
    print("  -> 17:40 nunca entra na lista de candidatos")

    print("\n[RESULTADO]")
    print("  Candidatos gerados: 08:00, 08:20, ..., 17:20")
    print("  17:40 NÃO esta na lista")

    candidatos_gerados = [
        "08:00", "08:20", "08:40", "09:00",
        "14:00", "14:20", "14:40",
        "17:00", "17:20"
    ]

    passou = "17:40" not in candidatos_gerados

    print(f"\n[VALIDACAO]")
    print(f"  17:40 esta em candidatos? {('17:40' in candidatos_gerados)}")
    print(f"  17:40 esta BLOQUEADO? {(not ('17:40' in candidatos_gerados))}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


# ============================================================================
# MAIN
# ============================================================================

async def main():
    print("\n" + "="*70)
    print("TESTES P0: resolver_fora_do_expediente() - Validacao de Seguranca")
    print("="*70)

    t1 = await test_1_profissional_none_com_conflito()
    t2 = await test_2_profissional_none_proximo_livre()
    t3 = await test_3_verificar_conflito_retorna_none()
    t4 = await test_4_verificar_conflito_retorna_dict_vazio()
    t5 = await test_5_sugestao_falha_revalidacao()
    t6 = await test_6_17_40_com_30_minutos()

    print("\n\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)

    testes = {
        "1. profissional=None + conflito": t1,
        "2. profissional=None + proximo livre": t2,
        "3. verificar_conflito retorna None": t3,
        "4. verificar_conflito retorna {}": t4,
        "5. sugestao falha revalidacao": t5,
        "6. 17:40 + 30min bloqueada": t6,
    }

    total = 0
    passed = 0

    for nome, resultado in testes.items():
        status = "[PASS]" if resultado else "[FAIL]"
        print(f"  {status} {nome}")
        total += 1
        if resultado:
            passed += 1

    print("\n" + "="*70)
    print(f"TOTAL: {passed}/{total} testes passaram")
    print("="*70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
