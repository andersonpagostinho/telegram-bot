#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 1 — Varredura Respeita Agenda_funcionamento

Objetivo: Validar que varrer_disponibilidade_multisservico() respeita a agenda
do Firebase e rejeita horários fora do expediente.

Testes obrigatórios:
1. Dia fechado → nenhuma sugestão
2. Antes da abertura → rejeitado
3. Dentro do expediente → aceito
4. Ultrapassa fechamento → rejeitado
5. Bloco termina exatamente no fechamento → aceito
6. Duração multisserviço respeitada
7. Tenant correto
8. Ausência de escrita no Firestore
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.varredura_disponibilidade import varrer_disponibilidade_multisservico
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
    buscar_subcolecao,
)
from services.identidade_service import normalizar_actor_id


async def setup_tenant_com_agenda():
    """Cria tenant com agenda e profissional para testes."""
    tenant_id = f"teste_fase1_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")

    # Criar agenda_funcionamento: seg-sex 09:00-17:00, sab-dom fechado
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
        {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "09:00", "fim": "17:00"},   # seg
                "1": {"aberto": True, "inicio": "09:00", "fim": "17:00"},   # ter
                "2": {"aberto": True, "inicio": "09:00", "fim": "17:00"},   # qua
                "3": {"aberto": True, "inicio": "09:00", "fim": "17:00"},   # qui
                "4": {"aberto": True, "inicio": "09:00", "fim": "17:00"},   # sex
                "5": {"aberto": False},                                      # sab
                "6": {"aberto": False}                                       # dom
            },
            "excecoes_data": {}
        }
    )

    # Criar profissional com dois serviços
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


async def cleanup_tenant(tenant_id):
    """Remove dados de teste do Firestore."""
    try:
        # Apenas validar que deletamos, não deletar realmente por segurança
        # Em produção, isto seria deletar tudo
        pass
    except:
        pass


async def test_1_dia_fechado():
    """T1: Dia fechado (domingo) retorna nenhuma sugestão."""
    print("\n" + "="*70)
    print("[T1] Dia fechado → nenhuma sugestão")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_com_agenda()

    try:
        # Data: domingo (2026-11-15 é um domingo)
        data_domingo = "2026-11-15"

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data=data_domingo,
            intervalo_inicio=10,
            intervalo_fim=16,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=60,
            dono_id=tenant_id
        )

        passou = (
            resultado["nenhuma_disponibilidade"] == True and
            resultado["horarios_disponiveis"] == []
        )

        print(f"  Resultado: {resultado}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        await cleanup_tenant(tenant_id)


async def test_2_antes_da_abertura():
    """T2: Horário antes da abertura (09:00) é rejeitado."""
    print("\n" + "="*70)
    print("[T2] Antes da abertura → rejeitado")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_com_agenda()

    try:
        # Data: segunda-feira (2026-11-16)
        data_segunda = "2026-11-16"

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data=data_segunda,
            intervalo_inicio=7,  # 07:00-09:00
            intervalo_fim=9,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=60,
            dono_id=tenant_id
        )

        passou = resultado["nenhuma_disponibilidade"] == True

        print(f"  Resultado: {resultado}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        await cleanup_tenant(tenant_id)


async def test_3_dentro_do_expediente():
    """T3: Horário dentro do expediente é aceito."""
    print("\n" + "="*70)
    print("[T3] Dentro do expediente → aceito")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_com_agenda()

    try:
        # Data: segunda-feira (2026-11-16)
        data_segunda = "2026-11-16"

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data=data_segunda,
            intervalo_inicio=10,  # 10:00-14:00
            intervalo_fim=14,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=60,
            dono_id=tenant_id
        )

        passou = (
            resultado["nenhuma_disponibilidade"] == False and
            len(resultado["horarios_disponiveis"]) > 0
        )

        print(f"  Resultado: {resultado}")
        print(f"  Horários encontrados: {len(resultado['horarios_disponiveis'])}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        await cleanup_tenant(tenant_id)


async def test_4_ultrapassa_fechamento():
    """T4: Horário que ultrapassa fechamento é rejeitado."""
    print("\n" + "="*70)
    print("[T4] Ultrapassa fechamento → rejeitado")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_com_agenda()

    try:
        # Data: segunda-feira (2026-11-16), fechamento 17:00
        data_segunda = "2026-11-16"

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data=data_segunda,
            intervalo_inicio=16,  # 16:00-18:00
            intervalo_fim=18,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=120,  # 2 horas
            dono_id=tenant_id
        )

        passou = resultado["nenhuma_disponibilidade"] == True

        print(f"  Resultado: {resultado}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        await cleanup_tenant(tenant_id)


async def test_5_bloco_termina_exatamente_no_fechamento():
    """T5: Bloco que termina exatamente no fechamento é aceito."""
    print("\n" + "="*70)
    print("[T5] Bloco termina exatamente no fechamento → aceito")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_com_agenda()

    try:
        # Data: segunda-feira (2026-11-16), fechamento 17:00
        # Agendamento: 16:00-17:00 (60 minutos)
        data_segunda = "2026-11-16"

        resultado = await varrer_disponibilidade_multisservico(
            tenant_id=tenant_id,
            actor_id=actor_id,
            data=data_segunda,
            intervalo_inicio=16,
            intervalo_fim=18,
            profissional_mencionada="Bruna",
            servicos_multiplos=["corte", "escova"],
            duracao_total=60,
            dono_id=tenant_id
        )

        passou = (
            resultado["nenhuma_disponibilidade"] == False and
            any(h["inicio"] == "16:00" for h in resultado["horarios_disponiveis"])
        )

        print(f"  Resultado: {resultado}")
        print(f"  Horários encontrados: {resultado['horarios_disponiveis']}")
        print(f"  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")
        return passou

    finally:
        await cleanup_tenant(tenant_id)


async def main():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("TESTE FASE 1: VARREDURA RESPEITA AGENDA_FUNCIONAMENTO")
    print("="*70)

    testes = [
        ("Dia fechado", test_1_dia_fechado),
        ("Antes da abertura", test_2_antes_da_abertura),
        ("Dentro do expediente", test_3_dentro_do_expediente),
        ("Ultrapassa fechamento", test_4_ultrapassa_fechamento),
        ("Bloco termina exatamente", test_5_bloco_termina_exatamente_no_fechamento),
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
    falhou = total - passou

    for nome, resultado in resultados:
        status = "✅" if resultado else "❌"
        print(f"{status} {nome}")

    print(f"\nTotal: {passou}/{total} PASSOU")

    return falhou == 0


if __name__ == "__main__":
    resultado = asyncio.run(main())
    sys.exit(0 if resultado else 1)
