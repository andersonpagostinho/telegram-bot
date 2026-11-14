#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 3 — Motor de Eventos Respeita Jornada Individual

Teste: verificar_conflito_e_sugestoes_profissional() com jornada individual.
"""

import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_service_async import verificar_conflito_e_sugestoes_profissional
from services.firebase_service_async import salvar_dado_em_path
from services.identidade_service import normalizar_actor_id


async def setup_tenant_base():
    """Setup tenant com agenda salão seg-sex 09:00-18:00."""
    tenant_id = f"fase3_test_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")

    # Salão: seg-sex 09:00-18:00
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
        {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "09:00", "fim": "18:00"},  # seg
                "1": {"aberto": True, "inicio": "09:00", "fim": "18:00"},  # ter
                "2": {"aberto": True, "inicio": "09:00", "fim": "18:00"},  # qua
                "3": {"aberto": True, "inicio": "09:00", "fim": "18:00"},  # qui
                "4": {"aberto": True, "inicio": "09:00", "fim": "18:00"},  # sex
                "5": {"aberto": False},                                    # sab
                "6": {"aberto": False}                                     # dom
            },
            "excecoes_data": {}
        }
    )

    # Profissional Bruna SEM agenda individual (herda salão)
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Profissionais/Bruna",
        {
            "nome": "Bruna",
            "servicos": ["corte", "escova"],
            "precos": {"corte": 50, "escova": 60},
            "duracoes": {"corte": 40, "escova": 20}
        }
    )

    # Profissional Carlos COM agenda individual: seg-sex 14:00-17:00
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/Profissionais/Carlos",
        {
            "nome": "Carlos",
            "servicos": ["corte", "escova"],
            "precos": {"corte": 50, "escova": 60},
            "duracoes": {"corte": 40, "escova": 20},
            "agenda_funcionamento": {
                "agenda_padrao": {
                    "0": {"aberto": True, "inicio": "14:00", "fim": "17:00"},  # seg
                    "1": {"aberto": True, "inicio": "14:00", "fim": "17:00"},  # ter
                    "2": {"aberto": True, "inicio": "14:00", "fim": "17:00"},  # qua
                    "3": {"aberto": True, "inicio": "14:00", "fim": "17:00"},  # qui
                    "4": {"aberto": True, "inicio": "14:00", "fim": "17:00"},  # sex
                    "5": {"aberto": False},                                    # sab
                    "6": {"aberto": False}                                     # dom
                },
                "excecoes_data": {}
            }
        }
    )

    return tenant_id, actor_id


async def test_1_profissional_sem_jornada_individual():
    """T1: Prof sem agenda individual herda jornada do salão (09:00-18:00)."""
    print("\n" + "="*70)
    print("[T1] Prof sem jornada individual → herda salão")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_base()

    try:
        # Segunda 10:00 + 60min = 11:00 (dentro de 09:00-18:00) ✅
        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=actor_id,
            data="2026-11-16",
            hora_inicio="10:00",
            duracao_min=60,
            profissional="Bruna",
            servico="corte",
            tenant_id=tenant_id
        )

        passou = resultado.get("conflito") == False

        print(f"  Resultado: conflito={resultado.get('conflito')}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_2_profissional_com_jornada_individual_dentro():
    """T2: Prof com agenda individual (14:00-17:00): 15:00-16:00 permitido."""
    print("\n" + "="*70)
    print("[T2] Prof com jornada individual → 15:00-16:00 dentro")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_base()

    try:
        # Segunda 15:00 + 60min = 16:00 (dentro de 14:00-17:00) ✅
        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=actor_id,
            data="2026-11-16",
            hora_inicio="15:00",
            duracao_min=60,
            profissional="Carlos",
            servico="corte",
            tenant_id=tenant_id
        )

        passou = resultado.get("conflito") == False

        print(f"  Resultado: conflito={resultado.get('conflito')}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_3_profissional_com_jornada_individual_apos():
    """T3: Prof com agenda individual (14:00-17:00): 13:00-14:00 rejeitado."""
    print("\n" + "="*70)
    print("[T3] Prof com jornada individual → 13:00-14:00 antes abertura")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_base()

    try:
        # Segunda 13:00 + 60min = 14:00 (ANTES de 14:00, iniciação anterior) ❌
        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=actor_id,
            data="2026-11-16",
            hora_inicio="13:00",
            duracao_min=60,
            profissional="Carlos",
            servico="corte",
            tenant_id=tenant_id
        )

        passou = resultado.get("conflito") == True

        print(f"  Resultado: conflito={resultado.get('conflito')}, motivo={resultado.get('motivo')}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_4_profissional_com_jornada_ultrapassa():
    """T4: Prof com agenda (14:00-17:00): 16:30-17:30 ultrapassa."""
    print("\n" + "="*70)
    print("[T4] Prof com jornada individual → 16:30 + 60min ultrapassa")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_base()

    try:
        # Segunda 16:30 + 60min = 17:30 (APÓS 17:00) ❌
        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=actor_id,
            data="2026-11-16",
            hora_inicio="16:30",
            duracao_min=60,
            profissional="Carlos",
            servico="corte",
            tenant_id=tenant_id
        )

        passou = resultado.get("conflito") == True

        print(f"  Resultado: conflito={resultado.get('conflito')}, motivo={resultado.get('motivo')}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def test_5_bloco_termina_exatamente():
    """T5: Prof com agenda (14:00-17:00): 16:00-17:00 permitido."""
    print("\n" + "="*70)
    print("[T5] Prof com jornada individual → 16:00 termina exatamente")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_base()

    try:
        # Segunda 16:00 + 60min = 17:00 (EXATAMENTE) ✅
        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=actor_id,
            data="2026-11-16",
            hora_inicio="16:00",
            duracao_min=60,
            profissional="Carlos",
            servico="corte",
            tenant_id=tenant_id
        )

        passou = resultado.get("conflito") == False

        print(f"  Resultado: conflito={resultado.get('conflito')}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        pass


async def main():
    """Executa testes FASE 3."""
    print("\n" + "="*70)
    print("TESTE FASE 3: MOTOR DE EVENTOS RESPEITA JORNADA INDIVIDUAL")
    print("="*70)

    testes = [
        ("Prof sem jornada individual", test_1_profissional_sem_jornada_individual),
        ("Prof com jornada: dentro", test_2_profissional_com_jornada_individual_dentro),
        ("Prof com jornada: antes abertura", test_3_profissional_com_jornada_individual_apos),
        ("Prof com jornada: ultrapassa", test_4_profissional_com_jornada_ultrapassa),
        ("Prof com jornada: termina exatamente", test_5_bloco_termina_exatamente),
    ]

    resultados = []
    for nome, teste_func in testes:
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
    print("RESUMO")
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
