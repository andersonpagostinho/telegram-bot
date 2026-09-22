#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE SIMPLES: ALTERAR AGENDAMENTO

Teste minimalista focado em validar funcionamento básico de reagendamento.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    deletar_dado_em_path, buscar_dado_em_path, buscar_subcolecao
)
from services.event_service_async import alterar_agendamento
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def teste_simples():
    tenant = "teste_alt_simples"
    cliente = "cliente_teste"

    print("[SETUP] Limpando...")
    try:
        locks = await buscar_subcolecao(f"Clientes/{tenant}/AgendaLocks") or {}
        for lid in locks.keys():
            await deletar_dado_em_path(f"Clientes/{tenant}/AgendaLocks/{lid}")
        await deletar_dado_em_path(f"Clientes/{tenant}")
    except:
        pass

    print("[ETAPA 1] Criar evento original...")
    resultado1 = await criar_com_lock_real(
        dono_id=tenant,
        evento={
            "profissional": "Carla",
            "servico": "Manicure",
            "data": "2026-08-11",
            "hora_inicio": "14:30",
            "hora_fim": "15:00",
            "duracao_minutos": 30,
            "confirmado": True,
            "status": "confirmado",
            "cliente_id": cliente,
            "cliente_nome": "Teste"
        },
        event_id="evt_001"
    )

    if not resultado1.get("ok"):
        print(f"[FALHA] Nao consegui criar evento: {resultado1}")
        return False

    print("[OK] Evento original criado")

    # Verificar que evento existe
    evento_original = await buscar_dado_em_path(f"Clientes/{tenant}/Eventos/evt_001")
    print(f"[VERIFY] Evento original no DB: {evento_original is not None}")

    print("\n[ETAPA 2] Alterar para novo horario...")
    resultado2 = await alterar_agendamento(
        user_id=cliente,
        event_id="evt_001",
        nova_data="2026-08-12",
        nova_hora_inicio="10:00",
        nova_duracao_minutos=30,
        tenant_id=tenant  # Passar tenant direto para simplificar
    )

    print(f"[RESULTADO] Alteracao: ok={resultado2.get('ok')}, motivo={resultado2.get('motivo')}")

    if not resultado2.get("ok"):
        print(f"[FALHA] {resultado2.get('motivo')}")
        return False

    novo_id = resultado2.get("evento_id")
    print(f"[OK] Novo evento criado: {novo_id}")

    print("\n[ETAPA 3] Validar evento antigo cancelado...")
    evento_antigo = await buscar_dado_em_path(f"Clientes/{tenant}/Eventos/evt_001")
    if evento_antigo:
        status = evento_antigo.get("status", "").lower()
        print(f"[CHECK] Status do evento antigo: {status}")
        if status == "cancelado":
            print("[OK] Evento antigo foi cancelado")
        else:
            print(f"[AVISO] Evento ainda tem status: {status}")

    print("\n[ETAPA 4] Validar evento foi alterado (MESMO ID)...")
    evento_alterado = await buscar_dado_em_path(f"Clientes/{tenant}/Eventos/evt_001")
    if evento_alterado:
        print(f"[OK] Evento {novo_id} alterado com sucesso (MESMO ID)")
        print(f"    Data original: 2026-08-11, Data atual: {evento_alterado.get('data')}")
        print(f"    Hora original: 14:30, Hora atual: {evento_alterado.get('hora_inicio')}")
        print(f"    Profissional: {evento_alterado.get('profissional')}")

        # Verificar histórico
        historico = evento_alterado.get("historico_alteracoes", [])
        print(f"    Histórico de alteracoes: {len(historico)} registros")

        # Validar dados
        sucesso = (
            evento_alterado.get("data") == "2026-08-12" and
            evento_alterado.get("hora_inicio") == "10:00" and
            len(historico) > 0
        )

        if sucesso:
            print(f"[OK] Evento preservou ID e registrou alteracao")
        else:
            print(f"[FALHA] Dados inconsistentes")

        return sucesso

    print(f"[FALHA] Evento nao encontrado no DB")
    return False


async def main():
    try:
        resultado = await teste_simples()
        if resultado:
            print("\n[SUCESSO] Teste passou")
            return 0
        else:
            print("\n[FALHA] Teste falhou")
            return 1
    except Exception as e:
        print(f"\n[ERRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
