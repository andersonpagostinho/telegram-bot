#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORIA FASE 1 — Validação de Cálculos Aritméticos

Objetivo: Verificar que os cálculos de horário estão corretos.

Cenários:
1. 14:30 + 120 min = 16:30 (permitido até 17:00) ✅
2. 15:30 + 120 min = 17:30 (rejeitado, ultrapassa 17:00) ❌
3. 16:00 + 60 min = 17:00 (permitido, termina exatamente) ✅
4. 16:20 + 60 min = 17:20 (rejeitado, ultrapassa 17:00) ❌
"""

import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.varredura_disponibilidade import varrer_disponibilidade_multisservico
from services.firebase_service_async import salvar_dado_em_path
from services.identidade_service import normalizar_actor_id


async def setup():
    """Setup tenant com agenda seg-sex 09:00-17:00."""
    tenant_id = f"auditoria_fase1_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")

    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
        {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "09:00", "fim": "17:00"},  # seg
                "1": {"aberto": True, "inicio": "09:00", "fim": "17:00"},  # ter
                "2": {"aberto": True, "inicio": "09:00", "fim": "17:00"},  # qua
                "3": {"aberto": True, "inicio": "09:00", "fim": "17:00"},  # qui
                "4": {"aberto": True, "inicio": "09:00", "fim": "17:00"},  # sex
                "5": {"aberto": False},                                    # sab
                "6": {"aberto": False}                                     # dom
            },
            "excecoes_data": {}
        }
    )

    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Profissionais/Bruna",
        {
            "nome": "Bruna",
            "servicos": ["corte", "escova"],
            "precos": {"corte": 50, "escova": 60},
            "duracoes": {"corte": 40, "escova": 20}
        }
    )

    return tenant_id, actor_id


async def test_cenario_1_1400_mais_120_equals_1600():
    """
    Cenário 1: 14:00 + 120 min = 16:00
    Limite: 17:00
    Esperado: PERMITIDO ✅

    Nota: Varredura itera em [0, 20, 40] minutos, não em 30.
    """
    print("\n" + "="*70)
    print("[CENÁRIO 1] 14:00 + 120 min = 16:00 (permitido até 17:00)")
    print("="*70)

    tenant_id, actor_id = await setup()

    try:
        # Cálculo: 14:00 + 120 = 16:00 < 17:00 ✅
        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data="2026-11-16",  # segunda
            intervalo_inicio=14,
            intervalo_fim=17,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=120,
            dono_id=tenant_id
        )

        tem_1400 = any(h["inicio"] == "14:00" for h in resultado["horarios_disponiveis"])
        passou = tem_1400

        print(f"  Horários encontrados: {resultado['horarios_disponiveis']}")
        print(f"  14:00 presente: {tem_1400}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_cenario_2_1520_mais_120_equals_1720():
    """
    Cenário 2: 15:20 + 120 min = 17:20
    Limite: 17:00
    Esperado: REJEITADO ❌

    Nota: Varredura itera em [0, 20, 40] minutos, não em 30.
    """
    print("\n" + "="*70)
    print("[CENÁRIO 2] 15:20 + 120 min = 17:20 (rejeitado, ultrapassa 17:00)")
    print("="*70)

    tenant_id, actor_id = await setup()

    try:
        # Cálculo: 15:20 + 120 = 17:20 > 17:00 ❌
        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data="2026-11-16",  # segunda
            intervalo_inicio=15,
            intervalo_fim=18,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=120,
            dono_id=tenant_id
        )

        tem_1520 = any(h["inicio"] == "15:20" for h in resultado["horarios_disponiveis"])
        passou = not tem_1520  # Deve estar rejeitado

        print(f"  Horários encontrados: {resultado['horarios_disponiveis']}")
        print(f"  15:20 presente: {tem_1520} (deve ser False)")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_cenario_3_1600_mais_60_equals_1700():
    """
    Cenário 3: 16:00 + 60 min = 17:00
    Limite: 17:00
    Esperado: PERMITIDO ✅ (termina exatamente)
    """
    print("\n" + "="*70)
    print("[CENÁRIO 3] 16:00 + 60 min = 17:00 (permitido, termina exatamente)")
    print("="*70)

    tenant_id, actor_id = await setup()

    try:
        # Cálculo: 16:00 + 60 = 17:00 == 17:00 ✅
        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data="2026-11-16",  # segunda
            intervalo_inicio=16,
            intervalo_fim=18,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=60,
            dono_id=tenant_id
        )

        tem_1600 = any(h["inicio"] == "16:00" for h in resultado["horarios_disponiveis"])
        passou = tem_1600

        print(f"  Horários encontrados: {resultado['horarios_disponiveis']}")
        print(f"  16:00 presente: {tem_1600}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_cenario_4_1620_mais_60_equals_1720():
    """
    Cenário 4: 16:20 + 60 min = 17:20
    Limite: 17:00
    Esperado: REJEITADO ❌
    """
    print("\n" + "="*70)
    print("[CENÁRIO 4] 16:20 + 60 min = 17:20 (rejeitado, ultrapassa 17:00)")
    print("="*70)

    tenant_id, actor_id = await setup()

    try:
        # Cálculo: 16:20 + 60 = 17:20 > 17:00 ❌
        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data="2026-11-16",  # segunda
            intervalo_inicio=16,
            intervalo_fim=18,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=60,
            dono_id=tenant_id
        )

        tem_1620 = any(h["inicio"] == "16:20" for h in resultado["horarios_disponiveis"])
        passou = not tem_1620  # Deve estar rejeitado

        print(f"  Horários encontrados: {resultado['horarios_disponiveis']}")
        print(f"  16:20 presente: {tem_1620} (deve ser False)")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def main():
    """Executa testes de cálculo."""
    print("\n" + "="*70)
    print("AUDITORIA FASE 1 — VALIDAÇÃO DE CÁLCULOS ARITMÉTICOS")
    print("Expediente: 09:00-17:00 (seg-sex)")
    print("="*70)

    cenarios = [
        ("14:00 + 120min = 16:00 (✅ permitido)", test_cenario_1_1400_mais_120_equals_1600),
        ("15:20 + 120min = 17:20 (❌ rejeitado)", test_cenario_2_1520_mais_120_equals_1720),
        ("16:00 + 60min = 17:00 (✅ permitido)", test_cenario_3_1600_mais_60_equals_1700),
        ("16:20 + 60min = 17:20 (❌ rejeitado)", test_cenario_4_1620_mais_60_equals_1720),
    ]

    resultados = []
    for nome, teste_func in cenarios:
        try:
            resultado = await teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"  ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO — CÁLCULOS ARITMÉTICOS")
    print("="*70)
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)

    for nome, resultado in resultados:
        status = "✅" if resultado else "❌"
        print(f"{status} {nome}")

    print(f"\nTotal: {passou}/{total} PASSOU")

    return passou == total


if __name__ == "__main__":
    resultado = asyncio.run(main())
    sys.exit(0 if resultado else 1)
