#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO: Por que verificar_conflito_e_sugestoes_profissional() retorna eventos vazios?

Teste isolado para validar cada etapa da busca de eventos.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    buscar_subcolecao,
    atualizar_dado_em_path,
    obter_id_dono,
    deletar_dado_em_path,
)
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def teste_diagnostico():
    """Teste isolado de cada etapa"""

    tenant_id = "diag_teste_busca_eventos"
    cliente_id = "diag_cliente_teste_001"
    data_teste = "2026-08-11"

    print("="*80)
    print("DIAGNÓSTICO: Busca de Eventos em verificar_conflito")
    print("="*80)

    try:
        # SETUP
        print("\n[SETUP] Limpando dados antigos...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lock_id in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lock_id}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")
        await deletar_dado_em_path(f"Clientes/{cliente_id}")

        print("[SETUP] Registrando cliente...")
        cliente_doc = {
            "nome": "Cliente Diagnostico",
            "id_negocio": tenant_id,
            "tipo_usuario": "cliente"
        }
        await atualizar_dado_em_path(f"Clientes/{cliente_id}", cliente_doc)

        # ETAPA 1: Criar evento
        print("\n" + "="*80)
        print("ETAPA 1: Criar evento bloqueante")
        print("="*80)

        evento = {
            "descricao": "Manicure (diagnóstico)",
            "profissional": "Carla",
            "servico": "Manicure",
            "data": data_teste,
            "hora_inicio": "14:30",
            "hora_fim": "15:00",
            "duracao": 30,
            "duracao_minutos": 30,
            "confirmado": True,
            "status": "confirmado",
            "cliente_id": "outro_cliente_456",
            "cliente_nome": "Maria"
        }

        resultado = await criar_com_lock_real(
            dono_id=tenant_id,
            evento=evento,
            event_id=f"evt_diag_{data_teste}_1430"
        )
        print(f"[ETAPA1] Resultado: {resultado}")

        if not resultado.get("ok"):
            print(f"[FALHA] Evento não foi criado: {resultado}")
            return

        print("[OK] Evento criado com sucesso")

        # ETAPA 2: Buscar eventos direto (sem passar por verificar_conflito)
        print("\n" + "="*80)
        print("ETAPA 2: Buscar eventos DIRETO com buscar_subcolecao()")
        print("="*80)

        print(f"[BUSCA] Procurando em: Clientes/{tenant_id}/Eventos")
        eventos_direto = await buscar_subcolecao(f"Clientes/{tenant_id}/Eventos")
        print(f"[RESULTADO] Eventos encontrados: {len(eventos_direto)}")
        for eid, ev in eventos_direto.items():
            print(f"  - {eid}: {ev.get('descricao')} ({ev.get('hora_inicio')}-{ev.get('hora_fim')})")

        # ETAPA 3: Chamar verificar_conflito (com delay)
        print("\n" + "="*80)
        print("ETAPA 3: Chamar verificar_conflito_e_sugestoes_profissional()")
        print("="*80)

        print("[AGUARDANDO] 3 segundos para replicação...")
        await asyncio.sleep(3)

        print(f"[CHAMADA] Validando Corte 14:00-14:45 com Carla")
        resultado_validacao = await verificar_conflito_e_sugestoes_profissional(
            user_id=tenant_id,  # ← Passando tenant direto
            data=data_teste,
            hora_inicio="14:00",
            duracao_min=45,
            profissional="Carla",
            servico="Corte"
        )

        print(f"[RESULTADO] Conflito: {resultado_validacao.get('conflito')}")
        print(f"[RESULTADO] Sugestões: {len(resultado_validacao.get('sugestoes', []))}")

        # ETAPA 4: Chamar com cliente_id (simular cliente)
        print("\n" + "="*80)
        print("ETAPA 4: Chamar com cliente_id (não tenant)")
        print("="*80)

        print(f"[CHAMADA] Validando com cliente_id: {cliente_id}")
        resultado_validacao_cliente = await verificar_conflito_e_sugestoes_profissional(
            user_id=cliente_id,  # ← Passando cliente
            data=data_teste,
            hora_inicio="14:00",
            duracao_min=45,
            profissional="Carla",
            servico="Corte"
        )

        print(f"[RESULTADO] Conflito: {resultado_validacao_cliente.get('conflito')}")
        print(f"[RESULTADO] Sugestões: {len(resultado_validacao_cliente.get('sugestoes', []))}")

        # ETAPA 5: Comparar
        print("\n" + "="*80)
        print("ETAPA 5: Diagnóstico")
        print("="*80)

        print(f"\nResumo:")
        print(f"  Evento criado? SIM")
        print(f"  Eventos encontrados (busca direta)? {'SIM' if eventos_direto else 'NÃO'}")
        print(f"  Conflito detectado (tenant)? {resultado_validacao.get('conflito')}")
        print(f"  Conflito detectado (cliente)? {resultado_validacao_cliente.get('conflito')}")

        # DIAGNÓSTICO
        if not eventos_direto:
            print(f"\n[DIAGNÓSTICO] PROBLEMA: Evento não está em Firestore!")
            print(f"             Tipo de erro: PERSISTÊNCIA")
            print(f"             Ação: Verificar criar_com_lock_real()")
        elif not resultado_validacao.get('conflito') and not resultado_validacao_cliente.get('conflito'):
            print(f"\n[DIAGNÓSTICO] PROBLEMA: Evento em Firestore mas não detectado!")
            print(f"             Tipo de erro: FILTRO ou NORMALIZAÇÃO")
            print(f"             Ação: Verificar evento_deve_entrar_na_agenda() ou normalizar_hora")
        else:
            print(f"\n[DIAGNÓSTICO] OK: Conflito detectado corretamente")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n" + "="*80)
        print("Limpando dados de diagnóstico...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lock_id in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lock_id}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")
        print("Concluído.")


if __name__ == "__main__":
    asyncio.run(teste_diagnostico())
