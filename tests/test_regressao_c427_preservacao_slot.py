#!/usr/bin/env python3
"""
Testes de Regressão — C4.2.7: Preservação de Slot vs Heurística

Objetivo: Validar que uma mensagem incremental não sobrescreve um serviço
já existente através de matching heurístico.

Cenários:
T1: "com a bruna" preserva "corte" + atualiza profissional
T2: "pode ser com a bruna" preserva "corte"
T3: "na verdade quero coloracao" TROCA para novo serviço
T4: "quero coloracao" (novo, sem anterior) → detecta
T5: "com a bruna" (sem anterior) → não inventa "coloracao"
T6: "oi" (conversação) → preserva "corte"
T7: "seg ou ter às 15 ou 16" → preserva "corte" com múltiplos horários
T8: "com a Carla" (profissional rejeitado) → preserva "corte" + novo profissional
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from router.principal_router import extrair_slots_e_mesclar
from datetime import datetime


async def test_t1_preserva_corte_com_profissional():
    """T1: "com a bruna" preserva "corte" + atualiza profissional"""
    print("\n" + "="*60)
    print("TEST T1: Preservar 'corte' + atualizar profissional")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": "corte",
            "data_hora": "2026-09-28T17:00:00",
            "profissional": None
        },
        "servico": "corte",
        "data_hora": "2026-09-28T17:00:00",
        "profissional_escolhido": None
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="com a bruna",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")
    profissional_final = resultado.get("profissional_escolhido") or resultado.get("draft_agendamento", {}).get("profissional")

    print(f"Entrada: 'com a bruna'")
    print(f"Serviço esperado: 'corte'")
    print(f"Serviço obtido: '{servico_final}'")
    print(f"Profissional esperado: 'Bruna' (ou 'bruna')")
    print(f"Profissional obtido: '{profissional_final}'")

    assert servico_final == "corte", f"❌ FALHA: serviço mudou para '{servico_final}'"
    assert profissional_final and "bruna" in profissional_final.lower(), f"❌ FALHA: profissional não detectado"
    print("✅ PASS")
    return True


async def test_t2_pode_ser_com_bruna():
    """T2: "pode ser com a bruna" preserva "corte" """
    print("\n" + "="*60)
    print("TEST T2: 'pode ser com a bruna' preserva 'corte'")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": "corte"
        },
        "servico": "corte"
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="pode ser com a bruna",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")
    profissional_final = resultado.get("profissional_escolhido") or resultado.get("draft_agendamento", {}).get("profissional")

    print(f"Entrada: 'pode ser com a bruna'")
    print(f"Serviço esperado: 'corte'")
    print(f"Serviço obtido: '{servico_final}'")
    print(f"Profissional esperado: 'Bruna'")
    print(f"Profissional obtido: '{profissional_final}'")

    assert servico_final == "corte", f"❌ FALHA: serviço mudou para '{servico_final}'"
    print("✅ PASS")
    return True


async def test_t3_troca_para_coloracao():
    """T3: "na verdade quero coloracao" TROCA para novo serviço"""
    print("\n" + "="*60)
    print("TEST T3: 'na verdade quero coloracao' troca serviço")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": "corte"
        },
        "servico": "corte"
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="na verdade quero coloracao",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")

    print(f"Entrada: 'na verdade quero coloracao'")
    print(f"Serviço esperado: 'coloracao'")
    print(f"Serviço obtido: '{servico_final}'")

    assert servico_final == "coloracao", f"❌ FALHA: serviço não trocou para 'coloracao', ficou '{servico_final}'"
    print("✅ PASS")
    return True


async def test_t4_novo_sem_anterior():
    """T4: "quero coloracao" (novo, sem contexto anterior)"""
    print("\n" + "="*60)
    print("TEST T4: 'quero coloracao' (novo) detecta serviço")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": None
        },
        "servico": None
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="quero coloracao",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")

    print(f"Entrada: 'quero coloracao'")
    print(f"Serviço esperado: 'coloracao'")
    print(f"Serviço obtido: '{servico_final}'")

    assert servico_final == "coloracao", f"❌ FALHA: serviço não detectado, ficou '{servico_final}'"
    print("✅ PASS")
    return True


async def test_t5_bruna_sem_anterior_nao_inventa():
    """T5: "com a bruna" (sem anterior) → não inventa "coloracao" """
    print("\n" + "="*60)
    print("TEST T5: 'com a bruna' (sem anterior) não inventa 'coloracao'")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": None
        },
        "servico": None
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="com a bruna",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")
    profissional_final = resultado.get("profissional_escolhido") or resultado.get("draft_agendamento", {}).get("profissional")

    print(f"Entrada: 'com a bruna'")
    print(f"Serviço esperado: None (ou vazio)")
    print(f"Serviço obtido: '{servico_final}'")
    print(f"Profissional esperado: 'Bruna'")
    print(f"Profissional obtido: '{profissional_final}'")

    assert not servico_final or servico_final is None, f"❌ FALHA: inventou serviço '{servico_final}'"
    assert profissional_final and "bruna" in profissional_final.lower(), f"❌ FALHA: profissional não detectado"
    print("✅ PASS")
    return True


async def test_t6_conversacao_pura():
    """T6: "oi" (conversação pura) preserva contexto"""
    print("\n" + "="*60)
    print("TEST T6: 'oi' (conversação) preserva contexto")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": "corte"
        },
        "servico": "corte"
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="oi",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")

    print(f"Entrada: 'oi'")
    print(f"Serviço esperado: 'corte'")
    print(f"Serviço obtido: '{servico_final}'")

    assert servico_final == "corte", f"❌ FALHA: serviço mudou para '{servico_final}'"
    print("✅ PASS")
    return True


async def test_t7_multiplos_horarios():
    """T7: "seg ou ter às 15 ou 16" preserva "corte" com múltiplos horários"""
    print("\n" + "="*60)
    print("TEST T7: Múltiplos horários preserva serviço")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": "corte"
        },
        "servico": "corte"
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="seg ou ter às 15 ou 16",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")

    print(f"Entrada: 'seg ou ter às 15 ou 16'")
    print(f"Serviço esperado: 'corte'")
    print(f"Serviço obtido: '{servico_final}'")

    assert servico_final == "corte", f"❌ FALHA: serviço mudou para '{servico_final}'"
    print("✅ PASS")
    return True


async def test_t8_profissional_rejeitado():
    """T8: "com a Carla" (profissional rejeitado) preserva "corte" """
    print("\n" + "="*60)
    print("TEST T8: 'com a Carla' preserva 'corte' + novo profissional")
    print("="*60)

    ctx = {
        "draft_agendamento": {
            "servico": "corte"
        },
        "servico": "corte",
        "profissional_rejeitado": "Bruna"
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario="com a Carla",
        dono_id="7394370553"
    )

    servico_final = resultado.get("servico") or resultado.get("draft_agendamento", {}).get("servico")
    profissional_final = resultado.get("profissional_escolhido") or resultado.get("draft_agendamento", {}).get("profissional")

    print(f"Entrada: 'com a Carla'")
    print(f"Serviço esperado: 'corte'")
    print(f"Serviço obtido: '{servico_final}'")
    print(f"Profissional esperado: 'Carla'")
    print(f"Profissional obtido: '{profissional_final}'")

    assert servico_final == "corte", f"❌ FALHA: serviço mudou para '{servico_final}'"
    assert profissional_final and "carla" in profissional_final.lower(), f"❌ FALHA: profissional não detectado"
    print("✅ PASS")
    return True


async def main():
    """Executar todos os testes"""
    from dotenv import load_dotenv
    load_dotenv()

    testes = [
        ("T1", test_t1_preserva_corte_com_profissional),
        ("T2", test_t2_pode_ser_com_bruna),
        ("T3", test_t3_troca_para_coloracao),
        ("T4", test_t4_novo_sem_anterior),
        ("T5", test_t5_bruna_sem_anterior_nao_inventa),
        ("T6", test_t6_conversacao_pura),
        ("T7", test_t7_multiplos_horarios),
        ("T8", test_t8_profissional_rejeitado),
    ]

    resultados = []

    print("\n" + "="*60)
    print("REGRESSÃO C4.2.7: Preservação de Slot vs Heurística")
    print("="*60)

    for nome, teste_func in testes:
        try:
            resultado = await teste_func()
            resultados.append((nome, "PASS", None))
        except AssertionError as e:
            print(f"❌ FALHA: {e}")
            resultados.append((nome, "FAIL", str(e)))
        except Exception as e:
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, "ERROR", str(e)))

    # Resumo
    print("\n" + "="*60)
    print("RESUMO DE EXECUÇÃO")
    print("="*60)

    pass_count = sum(1 for _, status, _ in resultados if status == "PASS")
    fail_count = sum(1 for _, status, _ in resultados if status == "FAIL")
    error_count = sum(1 for _, status, _ in resultados if status == "ERROR")

    for nome, status, erro in resultados:
        symbol = "✅" if status == "PASS" else "❌"
        print(f"{symbol} {nome}: {status}")
        if erro:
            print(f"   └─ {erro}")

    print(f"\nTotal: {pass_count} PASS, {fail_count} FAIL, {error_count} ERROR")

    if fail_count == 0 and error_count == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n⚠️  {fail_count + error_count} TESTE(S) FALHARAM")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
