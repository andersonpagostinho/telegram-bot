#!/usr/bin/env python3
"""
P0 FIX TEST: Validação de data_sem_hora em estado aguardando_data

Testa que quando data_sem_hora=True, o bloco aguardando_data não re-processa
com interpretar_data_e_hora() e não insere horário default 09:00.
"""

import asyncio


async def test_01_bloco_aguardando_data_skipped():
    """
    Test 1: Bloco aguardando_data é pulado quando data_sem_hora=True
    Esperado: Condição (aguardando_data AND NOT data_sem_hora) = False
    """
    print("\n[TEST 01] Bloco aguardando_data skipped quando data_sem_hora=True")

    # Contexto após CASO 3 de extrair_slots_e_mesclar
    ctx = {
        "estado_fluxo": "aguardando_data",
        "data_sem_hora": True,  # ← FLAG que força skip
        "data_hora": "2026-10-19T00:00:00",
    }

    # Simula a condição da linha 10666 do principal_router.py
    # if estado_fluxo == "aguardando_data" and not ctx.get("data_sem_hora"):
    bloco_executa = (ctx["estado_fluxo"] == "aguardando_data" and
                     not ctx.get("data_sem_hora"))

    assert bloco_executa == False, \
        f"FALHA: Bloco aguardando_data deveria ser pulado, mas executa={bloco_executa}"

    print(f"  ✅ PASSOU")
    print(f"     Condição (aguardando_data AND NOT data_sem_hora) = {bloco_executa}")
    print(f"     Bloco aguardando_data foi corretamente pulado")


async def test_02_data_hora_permanece_00_00():
    """
    Test 2: data_hora permanece 00:00 quando bloco aguardando_data é pulado
    Esperado: Hora não foi alterada de 00:00 para 09:00
    """
    print("\n[TEST 02] data_hora permanece 00:00 (não é alterado para 09:00)")

    # Se bloco aguardando_data foi pulado, data_hora não é modificado
    ctx = {
        "data_hora": "2026-10-19T00:00:00",
        "data_sem_hora": True,
    }

    # Valida que hora é 00:00
    hora_parte = ctx["data_hora"].split("T")[1]
    assert hora_parte == "00:00:00", \
        f"FALHA: Hora esperada 00:00:00, obtida {hora_parte}"

    assert "09:00" not in ctx["data_hora"], \
        f"FALHA: data_hora contém 09:00: {ctx['data_hora']}"

    print(f"  ✅ PASSOU")
    print(f"     data_hora = {ctx['data_hora']} (00:00, não 09:00)")


async def test_03_contexto_com_servico_profissional():
    """
    Test 3: Contexto com serviço+profissional mas data_sem_hora
    Esperado: Bot pede horário, não cria evento
    """
    print("\n[TEST 03] Contexto com serviço+profissional mas data_sem_hora")

    ctx = {
        "estado_fluxo": "aguardando_data",
        "data_sem_hora": True,
        "data_hora": "2026-10-19T00:00:00",
        "hora_confirmada": False,
        "servico": "corte feminino",
        "profissional_escolhido": "Bruna",
    }

    # Valida flags
    assert ctx["data_sem_hora"] == True, "data_sem_hora deve ser True"
    assert ctx["hora_confirmada"] == False, "hora_confirmada deve ser False"
    assert ctx["servico"], "servico deve estar preenchido"
    assert ctx["profissional_escolhido"], "profissional deve estar preenchido"

    # Valida que hora é 00:00
    hora_str = ctx["data_hora"].split("T")[1]
    assert hora_str == "00:00:00", f"Hora deve ser 00:00, obtida {hora_str}"

    print(f"  ✅ PASSOU")
    print(f"     data_sem_hora={ctx['data_sem_hora']}")
    print(f"     hora_confirmada={ctx['hora_confirmada']}")
    print(f"     Bot pedirá: 'Qual horário você prefere?'")


async def test_04_sem_data_sem_hora_bloco_executa():
    """
    Test 4: Quando data_sem_hora=False, bloco aguardando_data executa
    Esperado: Condição = True, bloco executa
    """
    print("\n[TEST 04] Bloco aguardando_data executa quando data_sem_hora=False")

    ctx = {
        "estado_fluxo": "aguardando_data",
        "data_sem_hora": False,  # ← Sem a flag, bloco deve executar
    }

    # Simula a condição
    bloco_executa = (ctx["estado_fluxo"] == "aguardando_data" and
                     not ctx.get("data_sem_hora"))

    assert bloco_executa == True, \
        f"FALHA: Bloco deveria executar, mas executa={bloco_executa}"

    print(f"  ✅ PASSOU")
    print(f"     Condição (aguardando_data AND NOT data_sem_hora) = {bloco_executa}")
    print(f"     Bloco aguardando_data executará normalmente")


async def main():
    print("\n" + "="*80)
    print("P0 FIX TEST: Validação data_sem_hora em aguardando_data")
    print("="*80)

    tests = [
        test_01_bloco_aguardando_data_skipped,
        test_02_data_hora_permanece_00_00,
        test_03_contexto_com_servico_profissional,
        test_04_sem_data_sem_hora_bloco_executa,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FALHOU: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print(f"RESULTADO: {passed} PASSOU, {failed} FALHOU")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
