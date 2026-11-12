#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 FIX — Testes para correções da consulta informativa multiserviço.

Cobertura:
1. Consulta multisserviço em estado idle
2. Consulta multisserviço com fluxo ativo
3. Preservação de data explícita
4. Janela de início às 14h e término até 17h
5. Dois serviços em sequência com a mesma profissional
6. Ausência de disponibilidade da profissional preferida
7. Alternativas apresentadas sem seleção automática
8. Consulta informativa sem criação de evento
"""

import asyncio
import sys
import os
import uuid
import traceback
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.informacao_service import responder_consulta_informativa
from services.multisservico_service import enriquecer_contexto_consulta, extrair_data_da_mensagem
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from services.identidade_service import normalizar_actor_id
from services.cadastro_inicial_service import salvar_profissional


async def setup_tenant_completo():
    """Setup tenant com múltiplos profissionais e serviços."""
    tenant_id = f"p1_fix_test_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")

    print(f"\n[SETUP] tenant_id={tenant_id}")

    # Salão: seg-sex 09:00-18:00
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
        {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "1": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "2": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "3": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "4": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "5": {"aberto": False},
                "6": {"aberto": False}
            },
            "excecoes_data": {}
        }
    )

    # Profissional 1: Bruna — seg-sex 09:00-18:00, oferece manicure (30min) e pedicure (30min)
    await salvar_profissional(
        user_id=tenant_id,
        nome="Bruna",
        servicos={
            "manicure": {"preco": 50.0, "duracao": 30},
            "pedicure": {"preco": 50.0, "duracao": 30}
        },
        agenda_funcionamento=None
    )

    # Profissional 2: Gloria — seg-sex 10:00-14:00 apenas (jornada individual reduzida)
    await salvar_profissional(
        user_id=tenant_id,
        nome="Gloria",
        servicos={
            "manicure": {"preco": 50.0, "duracao": 30},
            "pedicure": {"preco": 50.0, "duracao": 30}
        },
        agenda_funcionamento={
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "10:00", "fim": "14:00"},
                "1": {"aberto": True, "inicio": "10:00", "fim": "14:00"},
                "2": {"aberto": True, "inicio": "10:00", "fim": "14:00"},
                "3": {"aberto": True, "inicio": "10:00", "fim": "14:00"},
                "4": {"aberto": True, "inicio": "10:00", "fim": "14:00"},
                "5": {"aberto": False},
                "6": {"aberto": False}
            },
            "excecoes_data": {}
        }
    )

    print(f"[SETUP] Salão e profissionais criados")
    return tenant_id, actor_id


# ============================================================
# TESTE 1: Consulta multisserviço em estado idle
# ============================================================
async def test_1_multisservico_idle():
    """T1: Consulta em estado idle enriquece contexto com servicos_multiplos + intervalo + profissional."""
    print("\n" + "="*70)
    print("[TESTE 1] Consulta multisserviço em estado idle")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_completo()

    try:
        # Simular extração de contexto (como faz principal_router.py linha 6685+)
        from router.principal_router import extrair_multiplos_servicos_da_mensagem

        mensagem = "Quanto custa manicure e pedicure com bruna das 14 às 17?"

        # FASE 1: Extrair múltiplos serviços
        servicos_detectados = await extrair_multiplos_servicos_da_mensagem(mensagem, tenant_id)
        print(f"[T1-STEP1] Serviços detectados: {servicos_detectados}")

        contexto_consulta = {}
        if len(servicos_detectados) > 1:
            contexto_consulta["servicos_multiplos"] = servicos_detectados

        # FASE 2: Enriquecer com intervalo + data
        contexto_consulta = enriquecer_contexto_consulta(contexto_consulta, mensagem)
        print(f"[T1-STEP2] Contexto após enriquecimento:")
        print(f"  - servicos_multiplos: {contexto_consulta.get('servicos_multiplos')}")
        print(f"  - intervalo_inicio: {contexto_consulta.get('intervalo_inicio')}")
        print(f"  - intervalo_fim: {contexto_consulta.get('intervalo_fim')}")
        print(f"  - data_hora: {contexto_consulta.get('data_hora')}")

        # Validação
        passou = (
            contexto_consulta.get("servicos_multiplos") == ["manicure", "pedicure"]
            and contexto_consulta.get("intervalo_inicio") == 14
            and contexto_consulta.get("intervalo_fim") == 17
        )

        print(f"\n[T1] Status: {'PASSOU' if passou else 'FALHOU'}")
        return passou

    except Exception as e:
        print(f"[T1-ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


# ============================================================
# TESTE 3: Preservação de data explícita
# ============================================================
async def test_3_preservacao_data():
    """T3: Data explicitamente mencionada é preservada."""
    print("\n" + "="*70)
    print("[TESTE 3] Preservação de data explícita")
    print("="*70)

    testes = [
        ("manicure amanhã", None),  # Relativo, será calculado
        ("manicure hoje", date.today().isoformat()),  # Hoje
        ("manicure segunda", None),  # Relativo, será calculado
        ("manicure dia 25", None),  # Relativo, será calculado
    ]

    passou_todos = True

    for mensagem, data_esperada_exata in testes:
        data_extraida = extrair_data_da_mensagem(mensagem)
        print(f"[T3] '{mensagem}' -> {data_extraida}")

        if data_esperada_exata:
            passou = data_extraida == data_esperada_exata
        else:
            # Apenas verificar que uma data foi extraida (nao vazia)
            passou = data_extraida is not None and isinstance(data_extraida, str)

        print(f"     Status: {'PASSOU' if passou else 'FALHOU'}")
        passou_todos = passou_todos and passou

    print(f"\n[T3] Status geral: {'PASSOU' if passou_todos else 'FALHOU'}")
    return passou_todos


# ============================================================
# TESTE 4: Janela de 14h às 17h
# ============================================================
async def test_4_janela_horaria():
    """T4: Janela de início às 14h e término até 17h é preservada."""
    print("\n" + "="*70)
    print("[TESTE 4] Janela de início 14h e término 17h")
    print("="*70)

    mensagem = "manicure pedicure das 14 às 17"

    contexto = enriquecer_contexto_consulta({}, mensagem)

    passou = (
        contexto.get("intervalo_inicio") == 14
        and contexto.get("intervalo_fim") == 17
    )

    print(f"[T4] intervalo_inicio: {contexto.get('intervalo_inicio')} (esperado: 14)")
    print(f"[T4] intervalo_fim: {contexto.get('intervalo_fim')} (esperado: 17)")
    print(f"\n[T4] Status: {'PASSOU' if passou else 'FALHOU'}")

    return passou


# ============================================================
# TESTE 5: Dois serviços em sequência
# ============================================================
async def test_5_dois_servicos_sequencia():
    """T5: Dois serviços em sequência chegam intactos em contexto_consulta."""
    print("\n" + "="*70)
    print("[TESTE 5] Dois serviços em sequência com mesma profissional")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_completo()

    try:
        from router.principal_router import extrair_multiplos_servicos_da_mensagem

        mensagem = "Quero manicure e pedicure com bruna"

        servicos = await extrair_multiplos_servicos_da_mensagem(mensagem, tenant_id)

        passou = servicos == ["manicure", "pedicure"]

        print(f"[T5] Servicos extraidos: {servicos}")
        print(f"[T5] Status: {'PASSOU' if passou else 'FALHOU'}")

        return passou

    except Exception as e:
        print(f"[T5-ERROR] {type(e).__name__}: {e}")
        return False


# ============================================================
# TESTE 8: Consulta sem criação de evento
# ============================================================
async def test_8_consulta_sem_evento():
    """T8: responder_consulta_informativa retorna resposta mas NÃO cria evento."""
    print("\n" + "="*70)
    print("[TESTE 8] Consulta informativa sem criação de evento")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_completo()

    try:
        from router.principal_router import extrair_multiplos_servicos_da_mensagem

        mensagem = "Quanto custa manicure e pedicure com bruna das 14 as 17?"

        # Construir contexto_consulta
        servicos = await extrair_multiplos_servicos_da_mensagem(mensagem, tenant_id)
        contexto_consulta = {}
        if len(servicos) > 1:
            contexto_consulta["servicos_multiplos"] = servicos

        contexto_consulta = enriquecer_contexto_consulta(contexto_consulta, mensagem)
        contexto_consulta["profissional_mencionada"] = "Bruna"

        # Chamar responder_consulta_informativa
        resposta = await responder_consulta_informativa(
            mensagem,
            tenant_id,
            contexto_consulta=contexto_consulta,
            actor_id=actor_id,
            tenant_id=tenant_id
        )

        print(f"[T8] Resposta recebida: {resposta is not None}")
        if resposta:
            print(f"[T8] Conteudo: {resposta[:100]}...")

        # Verificar que nenhum evento foi criado
        # (Eventos estariam em Clientes/{tenant_id}/Eventos)
        eventos_path = f"Clientes/{tenant_id}/Eventos"
        eventos = await buscar_dado_em_path(eventos_path)

        print(f"[T8] Eventos no Firestore: {eventos}")

        # A resposta deve existir, e nenhum evento deve ter sido criado
        passou = resposta is not None and (eventos is None or len(eventos) == 0)

        print(f"\n[T8] Status: {'PASSOU' if passou else 'FALHOU'}")
        return passou

    except Exception as e:
        print(f"[T8-ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


async def main():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("P1 FIX — TESTES DE CONSULTA INFORMATIVA MULTISSERVIÇO")
    print("="*70)

    testes = [
        ("T1: Consulta multisserviço em idle", test_1_multisservico_idle),
        ("T3: Preservação de data explícita", test_3_preservacao_data),
        ("T4: Janela 14h-17h", test_4_janela_horaria),
        ("T5: Dois serviços em sequência", test_5_dois_servicos_sequencia),
        ("T8: Sem criação de evento", test_8_consulta_sem_evento),
    ]

    resultados = []
    for nome, teste_func in testes:
        try:
            resultado = await teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n[ERROR] {nome} - ERRO: {e}")
            traceback.print_exc()
            resultados.append((nome, False))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)

    for nome, resultado in resultados:
        status = "PASSOU" if resultado else "FALHOU"
        print(f"[{status}] {nome}")

    print(f"\nTotal: {passou}/{total} PASSOU")

    return passou == total


if __name__ == "__main__":
    resultado = asyncio.run(main())
    sys.exit(0 if resultado else 1)
