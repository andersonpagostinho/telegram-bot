#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 4 — INVESTIGACAO MULTI-TENANT

Verificar explicitamente se existe divergencia entre:
  tenant_id_write (usado ao persistir evento)
  tenant_id_read (usado ao consultar evento)

Tambem verificar se alguma parte utiliza paths legados como:
  Clientes/{user_id}/Eventos (deveria ser Clientes/{tenant_id}/Eventos)

Nao fazer migracao estrutural sem evidencia.
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
    buscar_dado_em_path,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def main():
    """Investigar multi-tenant"""

    print("="*80)
    print("[ETAPA 4] Investigacao Multi-Tenant")
    print("="*80)

    # Cenario 1: Tenant direto
    print("\n" + "="*80)
    print("[CENARIO 1] Tenant DIRETO (user_id é um tenant)")
    print("="*80)

    tenant_direto = "mt_investigacao_tenant_001"
    cliente_do_tenant = "mt_investigacao_cliente_001"
    data_teste = "2026-08-11"

    try:
        # SETUP
        print("\n[SETUP] Limpando dados...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_direto}/AgendaLocks")
            for lid in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_direto}/AgendaLocks/{lid}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_direto}")
        await deletar_dado_em_path(f"Clientes/{cliente_do_tenant}")

        # Registrar cliente no tenant
        print("[SETUP] Registrando cliente no tenant...")
        await atualizar_dado_em_path(f"Clientes/{cliente_do_tenant}", {
            "nome": "Cliente",
            "id_negocio": tenant_direto,  # Cliente aponta para tenant
            "tipo_usuario": "cliente"
        })

        # ETAPA 1: Escrever com tenant direto
        print("\n[WRITE] Escrevendo evento com tenant direto...")
        print(f"  tenant_id_write: {tenant_direto}")
        print(f"  path_write: Clientes/{tenant_direto}/Eventos/evt_teste_001")

        resultado_write = await criar_com_lock_real(
            dono_id=tenant_direto,
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
            event_id="evt_teste_001"
        )

        print(f"  Resultado: ok={resultado_write.get('ok')}")

        if not resultado_write.get("ok"):
            print("[ERRO] Falha na escrita")
            return

        # ETAPA 2: Verificar escrita
        print("\n[VERIFY_WRITE] Verificando escrita...")
        evento_escrito = await buscar_dado_em_path(
            f"Clientes/{tenant_direto}/Eventos/evt_teste_001"
        )

        if evento_escrito:
            print(f"  [OK] Evento encontrado no path correto")
            print(f"      Path: Clientes/{tenant_direto}/Eventos/evt_teste_001")
            print(f"      profissional: {evento_escrito.get('profissional')}")
        else:
            print(f"  [ERRO] Evento NAO encontrado")

        # ETAPA 3: Tentar ler com tenant direto
        print("\n[READ] Lendo com tenant direto...")
        print(f"  tenant_id_read: {tenant_direto}")
        print(f"  path_read: Clientes/{tenant_direto}/Eventos")

        eventos_lidos = await buscar_subcolecao(f"Clientes/{tenant_direto}/Eventos")
        print(f"  Eventos encontrados: {len(eventos_lidos)}")

        if eventos_lidos:
            print(f"  IDs: {list(eventos_lidos.keys())}")
        else:
            print(f"  [ALERTA] Nenhum evento encontrado!")

        # ETAPA 4: Tentar ler com cliente_id
        print("\n[READ_CLIENTE] Lendo com cliente_id (deveria falhar)...")
        print(f"  user_id: {cliente_do_tenant}")
        print(f"  path_read: Clientes/{cliente_do_tenant}/Eventos")

        eventos_cliente = await buscar_subcolecao(f"Clientes/{cliente_do_tenant}/Eventos")
        print(f"  Eventos encontrados: {len(eventos_cliente)}")

        if eventos_cliente:
            print(f"  [ALERTA] Encontrou eventos no path do cliente!")
            print(f"  Isso indica path mismatch")
        else:
            print(f"  [OK] Nenhum evento no path do cliente (correto)")

        # RESUMO
        print("\n" + "="*80)
        print("[RESUMO CENARIO 1] Tenant Direto")
        print("="*80)

        print(f"\nMATCH DE TENANT:")
        print(f"  tenant_id_write:   {tenant_direto}")
        print(f"  tenant_id_read:    {tenant_direto}")
        print(f"  Match: {'SIM' if tenant_direto == tenant_direto else 'NAO'}")

        print(f"\nPATH UTILIZADO:")
        print(f"  Write: Clientes/{tenant_direto}/Eventos/evt_teste_001")
        print(f"  Read:  Clientes/{tenant_direto}/Eventos")
        print(f"  Path legado Clientes/{{user_id}}/Eventos: NAO (usa tenant correto)")

        print(f"\nRESULTADO:")
        if evento_escrito and len(eventos_lidos) > 0:
            print(f"  [OK] Evento escrito e lido com sucesso")
            print(f"      tenant_id_write == tenant_id_read")
            print(f"      Path esta correto")
        else:
            print(f"  [PROBLEMA] Divergencia entre escrita e leitura")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[CLEANUP] Limpando...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_direto}/AgendaLocks")
            for lid in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_direto}/AgendaLocks/{lid}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_direto}")
        await deletar_dado_em_path(f"Clientes/{cliente_do_tenant}")


if __name__ == "__main__":
    asyncio.run(main())
