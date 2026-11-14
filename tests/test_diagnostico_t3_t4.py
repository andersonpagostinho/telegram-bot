#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO: Testes 3 e 4 — obter_janela_funcionamento()

Executa isoladamente os testes que falharam.
"""

import asyncio
import sys
import os
import uuid
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.cadastro_inicial_service import salvar_profissional
from services.agenda_service import obter_janela_funcionamento
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from services.identidade_service import normalizar_actor_id


async def setup_tenant_completo():
    """Setup tenant com salão e agenda funcionamento."""
    tenant_id = f"diag_t3t4_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")

    print(f"[SETUP] tenant_id={tenant_id}")
    print(f"[SETUP] actor_id={actor_id}")

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

    print(f"[SETUP] Salão criado: 09:00-18:00 seg-sex")
    return tenant_id, actor_id


async def test_3_obter_janela_heranca():
    """T3: obter_janela_funcionamento() herdava do salão se sem agenda individual."""
    print("\n" + "="*70)
    print("[TESTE 3] obter_janela_funcionamento() — Herança do salão")
    print("="*70)

    tenant_id = None
    actor_id = None

    try:
        tenant_id, actor_id = await setup_tenant_completo()

        print("\n[T3-STEP1] Criar profissional SEM agenda individual...")

        # Criar profissional SEM agenda individual
        servicos_dict = {"corte": {"preco": 50.0, "duracao": 40}}

        print(f"[T3-STEP1A] Chamando salvar_profissional()...")
        print(f"  - user_id={tenant_id}")
        print(f"  - nome=Bruna")
        print(f"  - servicos={servicos_dict}")
        print(f"  - agenda_funcionamento=None")

        await salvar_profissional(
            user_id=tenant_id,
            nome="Bruna",
            servicos=servicos_dict,
            agenda_funcionamento=None
        )

        print(f"[T3-STEP1B] Verificando documento criado...")
        prof_doc = await buscar_dado_em_path(f"Clientes/{tenant_id}/Profissionais/Bruna")
        print(f"  - Documento existe: {prof_doc is not None}")
        print(f"  - Campos: {list(prof_doc.keys()) if prof_doc else 'N/A'}")
        print(f"  - agenda_funcionamento presente: {'agenda_funcionamento' in (prof_doc or {})}")

        print("\n[T3-STEP2] Consultar jornada via obter_janela_funcionamento()...")
        print(f"  - user_id={actor_id}")
        print(f"  - data_str=2026-11-16 (segunda)")
        print(f"  - profissional=Bruna")
        print(f"  - dono_id={tenant_id}")

        janela = await obter_janela_funcionamento(
            user_id=actor_id,
            data_str="2026-11-16",
            profissional="Bruna",
            dono_id=tenant_id
        )

        print(f"\n[T3-STEP3] Resultado obtido:")
        print(f"  - aberto: {janela.get('aberto')}")
        print(f"  - inicio: {janela.get('inicio')}")
        print(f"  - fim: {janela.get('fim')}")
        print(f"  - origem: {janela.get('origem')}")
        print(f"  - tipo: {janela.get('tipo')}")
        print(f"  - motivo: {janela.get('motivo')}")

        print(f"\n[T3-STEP4] Validação:")

        passou = (
            janela.get("aberto") == True and
            janela.get("inicio") == "09:00" and
            janela.get("fim") == "18:00" and
            "fallback_salao" in janela.get("origem", "")
        )

        print(f"  - aberto==True: {janela.get('aberto') == True}")
        print(f"  - inicio==09:00: {janela.get('inicio') == '09:00'}")
        print(f"  - fim==18:00: {janela.get('fim') == '18:00'}")
        print(f"  - origem contém 'fallback_salao': {'fallback_salao' in janela.get('origem', '')}")
        print(f"\n  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")

        return passou

    except Exception as e:
        print(f"\n[T3-ERROR] Exceção capturada:")
        print(f"  - Tipo: {type(e).__name__}")
        print(f"  - Mensagem: {e}")
        print(f"\n[T3-TRACEBACK]")
        traceback.print_exc()
        return False


async def test_4_obter_janela_individual():
    """T4: obter_janela_funcionamento() usa jornada individual quando existe."""
    print("\n" + "="*70)
    print("[TESTE 4] obter_janela_funcionamento() — Jornada individual")
    print("="*70)

    tenant_id = None
    actor_id = None

    try:
        tenant_id, actor_id = await setup_tenant_completo()

        print("\n[T4-STEP1] Criar profissional COM agenda individual...")

        # Criar agenda individual
        agenda_funcionamento = {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "14:00", "fim": "17:00"},
                "1": {"aberto": True, "inicio": "14:00", "fim": "17:00"},
                "2": {"aberto": True, "inicio": "14:00", "fim": "17:00"},
                "3": {"aberto": True, "inicio": "14:00", "fim": "17:00"},
                "4": {"aberto": True, "inicio": "14:00", "fim": "17:00"},
                "5": {"aberto": False},
                "6": {"aberto": False}
            },
            "excecoes_data": {}
        }

        servicos_dict = {"corte": {"preco": 50.0, "duracao": 40}}

        print(f"[T4-STEP1A] Chamando salvar_profissional()...")
        print(f"  - user_id={tenant_id}")
        print(f"  - nome=Carlos")
        print(f"  - servicos={servicos_dict}")
        print(f"  - agenda_funcionamento: 14:00-17:00 seg-sex, dom fechado")

        await salvar_profissional(
            user_id=tenant_id,
            nome="Carlos",
            servicos=servicos_dict,
            agenda_funcionamento=agenda_funcionamento
        )

        print(f"[T4-STEP1B] Verificando documento criado...")
        prof_doc = await buscar_dado_em_path(f"Clientes/{tenant_id}/Profissionais/Carlos")
        print(f"  - Documento existe: {prof_doc is not None}")
        print(f"  - Campos: {list(prof_doc.keys()) if prof_doc else 'N/A'}")
        print(f"  - agenda_funcionamento presente: {'agenda_funcionamento' in (prof_doc or {})}")
        if prof_doc and "agenda_funcionamento" in prof_doc:
            print(f"  - agenda_padrao[0] (segunda): {prof_doc['agenda_funcionamento'].get('agenda_padrao', {}).get('0')}")

        print("\n[T4-STEP2] Consultar jornada via obter_janela_funcionamento()...")
        print(f"  - user_id={actor_id}")
        print(f"  - data_str=2026-11-16 (segunda)")
        print(f"  - profissional=Carlos")
        print(f"  - dono_id={tenant_id}")

        janela = await obter_janela_funcionamento(
            user_id=actor_id,
            data_str="2026-11-16",
            profissional="Carlos",
            dono_id=tenant_id
        )

        print(f"\n[T4-STEP3] Resultado obtido:")
        print(f"  - aberto: {janela.get('aberto')}")
        print(f"  - inicio: {janela.get('inicio')}")
        print(f"  - fim: {janela.get('fim')}")
        print(f"  - origem: {janela.get('origem')}")
        print(f"  - tipo: {janela.get('tipo')}")
        print(f"  - motivo: {janela.get('motivo')}")

        print(f"\n[T4-STEP4] Validação:")

        passou = (
            janela.get("aberto") == True and
            janela.get("inicio") == "14:00" and
            janela.get("fim") == "17:00" and
            "agenda_padrao_profissional" in janela.get("origem", "")
        )

        print(f"  - aberto==True: {janela.get('aberto') == True}")
        print(f"  - inicio==14:00: {janela.get('inicio') == '14:00'}")
        print(f"  - fim==17:00: {janela.get('fim') == '17:00'}")
        print(f"  - origem contém 'agenda_padrao_profissional': {'agenda_padrao_profissional' in janela.get('origem', '')}")
        print(f"\n  Status: {'✅ PASSOU' if passou else '❌ FALHOU'}")

        return passou

    except Exception as e:
        print(f"\n[T4-ERROR] Exceção capturada:")
        print(f"  - Tipo: {type(e).__name__}")
        print(f"  - Mensagem: {e}")
        print(f"\n[T4-TRACEBACK]")
        traceback.print_exc()
        return False


async def main():
    """Executa diagnóstico."""
    print("\n" + "="*70)
    print("DIAGNÓSTICO: TESTES 3 E 4")
    print("="*70)

    resultado_3 = await test_3_obter_janela_heranca()
    resultado_4 = await test_4_obter_janela_individual()

    print("\n" + "="*70)
    print("RESUMO DO DIAGNÓSTICO")
    print("="*70)
    print(f"Teste 3 (herança): {'✅ PASSOU' if resultado_3 else '❌ FALHOU'}")
    print(f"Teste 4 (individual): {'✅ PASSOU' if resultado_4 else '❌ FALHOU'}")


if __name__ == "__main__":
    asyncio.run(main())
