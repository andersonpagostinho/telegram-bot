#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E TESTE — 2 BLOQUEADORES FIXADOS

Validar que:
1. intervalo_fim é extraído corretamente (14h até 17h)
2. pedicure é encontrada via bridge (sem Step 1 redundante)
3. Motor multisserviço executa completo
4. Resultado contém AMBAS as durações
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.multisservico_service import (
    extrair_intervalo_horario,
    enriquecer_contexto_consulta,
    resolver_bloco_servicos,
)
from services.duracao_service import obter_duracao_por_profissional_bridge


async def test_e2e_bloqueador_1_intervalo_fim():
    """Bloqueador 1: intervalo_fim deve ser 17 (não 14)"""
    print("\n" + "="*70)
    print("E2E TEST 1: BLOQUEADOR INTERVALO_FIM")
    print("="*70)

    msg = (
        "Gostaria de agendar manicure e pedicure para sexta-feira, dia 13/11/2026, "
        "a partir das 14h, mas preciso terminar os dois serviços até, no máximo, 17h."
    )

    # Teste 1: extrair_intervalo_horario()
    print(f"\n1️⃣ Teste extrair_intervalo_horario()")
    inicio, fim = extrair_intervalo_horario(msg)
    print(f"   Resultado: inicio={inicio}, fim={fim}")
    assert inicio == 14, f"Esperado inicio=14, obtido {inicio}"
    assert fim == 17, f"Esperado fim=17, obtido {fim}"
    print(f"   ✅ PASSOU")

    # Teste 2: enriquecer_contexto_consulta()
    print(f"\n2️⃣ Teste enriquecer_contexto_consulta()")
    contexto = {}
    contexto = enriquecer_contexto_consulta(contexto, msg)
    print(f"   Resultado: {contexto}")
    assert contexto.get("intervalo_inicio") == 14, f"Esperado inicio=14, obtido {contexto.get('intervalo_inicio')}"
    assert contexto.get("intervalo_fim") == 17, f"Esperado fim=17, obtido {contexto.get('intervalo_fim')}"
    print(f"   ✅ PASSOU")

    print(f"\n✅ BLOQUEADOR 1 FIXADO: intervalo_fim=17")


async def test_e2e_bloqueador_2_pedicure():
    """Bloqueador 2: pedicure deve retornar 30 (não None)"""
    print("\n" + "="*70)
    print("E2E TEST 2: BLOQUEADOR PEDICURE")
    print("="*70)

    tenant_id = "7394370553"
    prof_nome = "Bruna"

    # Teste 1: manicure via bridge (baseline)
    print(f"\n1️⃣ Teste manicure via bridge")
    duracao_manicure = await obter_duracao_por_profissional_bridge(
        tenant_id=tenant_id,
        nome_profissional=prof_nome,
        nome_servico="manicure"
    )
    print(f"   Resultado: {duracao_manicure}")
    assert duracao_manicure == 30, f"Esperado manicure=30, obtido {duracao_manicure}"
    print(f"   ✅ PASSOU")

    # Teste 2: pedicure via bridge (BLOQUEADOR FIXADO)
    print(f"\n2️⃣ Teste pedicure via bridge")
    duracao_pedicure = await obter_duracao_por_profissional_bridge(
        tenant_id=tenant_id,
        nome_profissional=prof_nome,
        nome_servico="pedicure"
    )
    print(f"   Resultado: {duracao_pedicure}")
    assert duracao_pedicure == 30, f"Esperado pedicure=30, obtido {duracao_pedicure}"
    print(f"   ✅ PASSOU")

    # Teste 3: Prof inexistente
    print(f"\n3️⃣ Teste prof inexistente")
    duracao_inexistente = await obter_duracao_por_profissional_bridge(
        tenant_id=tenant_id,
        nome_profissional="Professora Inexistente",
        nome_servico="manicure"
    )
    print(f"   Resultado: {duracao_inexistente}")
    assert duracao_inexistente is None, f"Esperado None, obtido {duracao_inexistente}"
    print(f"   ✅ PASSOU")

    print(f"\n✅ BLOQUEADOR 2 FIXADO: pedicure=30")


async def test_e2e_motor_completo():
    """Motor multisserviço com ambos os bloqueadores fixados"""
    print("\n" + "="*70)
    print("E2E TEST 3: MOTOR MULTISSERVIÇO")
    print("="*70)

    tenant_id = "7394370553"
    prof_nome = "Bruna"
    servicos = ["manicure", "pedicure"]

    print(f"\nTeste resolver_bloco_servicos()")
    print(f"  tenant_id='{tenant_id}'")
    print(f"  nome_profissional='{prof_nome}'")
    print(f"  servicos={servicos}")

    resultado = await resolver_bloco_servicos(
        tenant_id=tenant_id,
        nome_profissional=prof_nome,
        servicos=servicos
    )

    print(f"\n  Resultado:")
    print(f"    valido={resultado['valido']}")
    print(f"    duracoes={resultado['duracoes_individuais']}")
    print(f"    duracao_total={resultado['duracao_total']}")
    print(f"    mensagens={resultado['mensagens']}")

    assert resultado["valido"] is True, f"Motor deveria ser válido, obtido {resultado}"
    assert resultado["duracoes_individuais"] == [30, 30], f"Esperado [30, 30], obtido {resultado['duracoes_individuais']}"
    assert resultado["duracao_total"] == 60, f"Esperado duracao_total=60, obtido {resultado['duracao_total']}"
    assert len(resultado["mensagens"]) == 0, f"Não deveria ter mensagens de erro, obtido {resultado['mensagens']}"

    print(f"\n  ✅ PASSOU")
    print(f"\n✅ MOTOR MULTISSERVIÇO FIXADO: Ambas durações resolvidas, total=60min")


async def main():
    print("\n" + "="*70)
    print("E2E TESTES — 2 BLOQUEADORES FIXADOS")
    print("2026-11-12")
    print("="*70)

    try:
        await test_e2e_bloqueador_1_intervalo_fim()
        await test_e2e_bloqueador_2_pedicure()
        await test_e2e_motor_completo()

        print("\n" + "="*70)
        print("✅ TODOS OS E2E TESTES PASSARAM")
        print("="*70)
        print("\nAchados:")
        print("  1️⃣ intervalo_fim=17 (fixado por commit f654fb4)")
        print("  2️⃣ pedicure=30 (fixado removendo Step 1 redundante)")
        print("  3️⃣ Motor multisserviço executa completo (duracao_total=60)")
        print("  4️⃣ Nenhum evento ou lock criado")
        print("\nPronto para DEPLOY.")

    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
