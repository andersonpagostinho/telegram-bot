#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 3 — DIAGNOSTICO DE LEITURA

Rastrear por que verificar_conflito_e_sugestoes_profissional() retorna eventos vazios
Usar os logs de diagnóstico adicionados
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    atualizar_dado_em_path,
    deletar_dado_em_path,
    buscar_subcolecao,
)
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def main():
    """Diagnosticar leitura de eventos"""

    tenant_id = "diagnostico_leitura_001"
    cliente_id = "diagnostico_cliente_001"
    data_teste = "2026-08-11"

    print("="*80)
    print("[ETAPA 3] Diagnostico de leitura - verificar_conflito")
    print("="*80)

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

        print("[SETUP] Registrando cliente...")
        await atualizar_dado_em_path(f"Clientes/{cliente_id}", {
            "nome": "Cliente Diagnostico",
            "id_negocio": tenant_id,
            "tipo_usuario": "cliente"
        })

        # ETAPA 1: Criar evento bloqueante
        print("\n[ETAPA 1] Criar evento bloqueante...")
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
                "cliente_id": "outro_cliente",
                "cliente_nome": "Maria"
            },
            event_id=f"evt_diag_{data_teste}_1430"
        )

        if not resultado.get("ok"):
            print(f"[FALHA] Evento nao foi criado: {resultado}")
            return

        print(f"[OK] Evento criado com sucesso")

        # ETAPA 2: Chamar verificar_conflito COM DIAGNOSTICO
        print("\n" + "="*80)
        print("[ETAPA 2] Chamar verificar_conflito_e_sugestoes_profissional()")
        print("="*80)

        print("\n>>> Chamando com tenant_id DIRETO (veja os logs de diagnóstico):\n")

        resultado_diag = await verificar_conflito_e_sugestoes_profissional(
            user_id=tenant_id,
            data=data_teste,
            hora_inicio="14:00",
            duracao_min=90,
            profissional="Carla",
            servico="Corte + Hidratacao"
        )

        print(f"\n>>> Resultado final:")
        print(f"[RESULTADO] Conflito: {resultado_diag.get('conflito')}")
        print(f"[RESULTADO] Sugestoes: {len(resultado_diag.get('sugestoes', []))}")

        # ETAPA 3: Analise dos logs
        print("\n" + "="*80)
        print("[ETAPA 3] Analise dos logs de diagnostico")
        print("="*80)

        print(f"\nOs logs acima mostram:")
        print(f"1. tenant_id efetivo calculado")
        print(f"2. Path consultado no Firestore")
        print(f"3. Quantidade de eventos encontrados")
        print(f"4. IDs dos eventos encontrados")
        print(f"5. Cada evento processado (motivo de descarte ou inclusao)")
        print(f"6. Total de eventos considerados para conflito")
        print(f"7. Resultado final (conflito ou nao)")

        print(f"\n>>> Perguntas chave respondidas pelos logs:")
        print(f"- Por que eventos estao vazios?")
        print(f"- Qual path está sendo consultado?")
        print(f"- Quantos eventos existem?")
        print(f"- Por que cada evento foi descartado?")
        print(f"- Qual foi o resultado final da validacao?")

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
