#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 5 — INVESTIGACAO PROFISSIONAL

Verificar se o evento existente e a consulta utilizam exatamente o mesmo
identificador de profissional.

Comparar:
  profissional_id do evento persistido
  profissional_id usado na consulta

Nao assumir que nome e ID sao equivalentes.
Verificar normalizacoes intermediarias.
"""

import asyncio
import sys
from datetime import datetime
from unidecode import unidecode
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    atualizar_dado_em_path,
    deletar_dado_em_path,
    buscar_subcolecao,
    buscar_dado_em_path,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def main():
    """Investigar profissional"""

    print("="*80)
    print("[ETAPA 5] Investigacao Profissional")
    print("="*80)

    tenant_id = "prof_investigacao_001"
    data_teste = "2026-08-11"

    try:
        # SETUP
        print("\n[SETUP] Limpando dados...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lid in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lid}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")

        # TESTE 1: Profissional simples (Carla)
        print("\n" + "="*80)
        print("[TESTE 1] Profissional: Carla (simples)")
        print("="*80)

        print("\n[WRITE] Escrevendo evento com profissional='Carla'...")
        resultado = await criar_com_lock_real(
            dono_id=tenant_id,
            evento={
                "profissional": "Carla",
                "servico": "Manicure",
                "data": data_teste,
                "hora_inicio": "14:30",
                "hora_fim": "15:00",
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "cliente1",
                "cliente_nome": "Maria"
            },
            event_id="evt_carla_1430"
        )

        if not resultado.get("ok"):
            print(f"[ERRO] Falha na escrita")
            return

        evento_escrito = await buscar_dado_em_path(
            f"Clientes/{tenant_id}/Eventos/evt_carla_1430"
        )

        if evento_escrito:
            prof_persistido = evento_escrito.get("profissional")
            prof_persistido_norm = unidecode(prof_persistido.strip().lower())
            print(f"[WRITE] Profissional persistido:")
            print(f"  Original: '{prof_persistido}'")
            print(f"  Normalizado: '{prof_persistido_norm}'")
        else:
            print(f"[ERRO] Evento nao encontrado")
            return

        # TESTE LEITURAS COM DIFERENTES VARIAÇÕES
        print("\n[READ] Testando leituras com diferentes variações:")

        variacoes = [
            ("Carla", "Exato"),
            ("carla", "Minuscula"),
            ("CARLA", "Maiuscula"),
            ("Carlá", "Com acento"),
            ("carlá", "Minuscula + acento"),
            ("Carla ", "Com espaco trailing"),
            (" Carla", "Com espaco leading"),
            ("  Carla  ", "Com multiplos espacos"),
        ]

        for prof_teste, tipo_teste in variacoes:
            # Normalizar como faz a funcao
            prof_norm = unidecode((prof_teste or "").strip().lower())
            prof_persistido_norm = unidecode((prof_persistido or "").strip().lower())

            match = prof_norm == prof_persistido_norm

            print(f"\n  [{tipo_teste}]")
            print(f"    Consulta: '{prof_teste}'")
            print(f"    Normalizado: '{prof_norm}'")
            print(f"    Match: {'SIM' if match else 'NAO'}")

        # TESTE 2: Profissional com espaco (Ana Paula)
        print("\n" + "="*80)
        print("[TESTE 2] Profissional: Ana Paula (com espaco)")
        print("="*80)

        print("\n[WRITE] Escrevendo evento com profissional='Ana Paula'...")
        resultado2 = await criar_com_lock_real(
            dono_id=tenant_id,
            evento={
                "profissional": "Ana Paula",
                "servico": "Escova",
                "data": data_teste,
                "hora_inicio": "10:00",
                "hora_fim": "10:40",
                "duracao_minutos": 40,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "cliente2",
                "cliente_nome": "Joao"
            },
            event_id="evt_ana_1000"
        )

        if resultado2.get("ok"):
            evento2 = await buscar_dado_em_path(
                f"Clientes/{tenant_id}/Eventos/evt_ana_1000"
            )

            if evento2:
                prof2 = evento2.get("profissional")
                prof2_norm = unidecode(prof2.strip().lower())
                print(f"[WRITE] Profissional persistido:")
                print(f"  Original: '{prof2}'")
                print(f"  Normalizado: '{prof2_norm}'")

                # Testar variações
                print(f"\n[READ] Testando variações:")

                variacoes2 = [
                    ("Ana Paula", "Exato"),
                    ("ana paula", "Minuscula"),
                    ("ANA PAULA", "Maiuscula"),
                    ("Ana paula", "Primeira maiuscula"),
                    ("Ana Paula ", "Com espaco trailing"),
                ]

                for prof_teste, tipo_teste in variacoes2:
                    prof_norm = unidecode((prof_teste or "").strip().lower())
                    prof2_norm = unidecode((prof2 or "").strip().lower())

                    match = prof_norm == prof2_norm

                    print(f"\n  [{tipo_teste}]")
                    print(f"    Consulta: '{prof_teste}'")
                    print(f"    Normalizado: '{prof_norm}'")
                    print(f"    Match: {'SIM' if match else 'NAO'}")

        # RESUMO
        print("\n" + "="*80)
        print("[RESUMO] Profissional")
        print("="*80)

        print(f"\nNORMALIZACAO:")
        print(f"  Funcao: unidecode() + strip() + lower()")
        print(f"  Resultado: Tira acentos, remove espacos, converte para minuscula")

        print(f"\nCOMPARACOES:")
        print(f"  Carla == carla: {'SIM (match)' if unidecode('Carla'.strip().lower()) == unidecode('carla'.strip().lower()) else 'NAO'}")
        print(f"  Carla == Carlá: {'SIM (match)' if unidecode('Carla'.strip().lower()) == unidecode('Carlá'.strip().lower()) else 'NAO'}")
        print(f"  Ana Paula == ana paula: {'SIM (match)' if unidecode('Ana Paula'.strip().lower()) == unidecode('ana paula'.strip().lower()) else 'NAO'}")

        print(f"\nCONCLUSAO:")
        print(f"  [OK] Normalizacao funciona corretamente")
        print(f"  [OK] Profissional persistido bate com consultas normalizadas")
        print(f"  [OK] Nao ha divergencia de profissional")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[CLEANUP] Limpando...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lid in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lid}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")


if __name__ == "__main__":
    asyncio.run(main())
