"""
P0.27.4 — Diagnóstico READ-ONLY: Por que zero locks órfãos?

Investigar os 4 locks de Bruna 10:00 em 2026-11-06:
- bruna_20261106_100000
- bruna_20261106_101000
- bruna_20261106_102000
- bruna_20261106_103000

Verificar:
1. Existem os documentos?
2. Quais são os valores de status, evento_id, expira_em?
3. Existe evento correspondente?
4. Por que P0.27.3 não identificou como órfãos?
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.firebase_service import buscar_dado_em_path, buscar_subcolecao
from services.agenda_lock_service import liberar_locks_orfaos_expirados

TENANT_ID = "7394370553"
FUSO_BR = timezone("America/Sao_Paulo")

# 4 locks de Bruna 10:00 em 2026-11-06
LOCKS_ESPERADOS = [
    "bruna_20261106_100000",
    "bruna_20261106_101000",
    "bruna_20261106_102000",
    "bruna_20261106_103000",
]


async def consultar_locks_diretos():
    """Verificar os 4 documentos diretamente no Firestore"""
    print("\n" + "="*80)
    print("ETAPA 1 — CONSULTAR LOCKS DIRETAMENTE")
    print("="*80)

    locks_encontrados = {}

    for lock_id in LOCKS_ESPERADOS:
        path = f"Clientes/{TENANT_ID}/AgendaLocks/{lock_id}"
        print(f"\n[{lock_id}]")
        print(f"  Path: {path}")

        try:
            lock_doc = await buscar_dado_em_path(path)
            if lock_doc:
                locks_encontrados[lock_id] = lock_doc
                print(f"  ✓ EXISTE")
                print(f"    status: {lock_doc.get('status')}")
                print(f"    evento_id: {lock_doc.get('evento_id')}")
                print(f"    expira_em: {lock_doc.get('expira_em')}")
                print(f"    timestamp_lock: {lock_doc.get('timestamp_lock')}")
                print(f"    timestamp_confirmacao: {lock_doc.get('timestamp_confirmacao')}")
                print(f"    profissional: {lock_doc.get('profissional')}")
                print(f"    bucket: {lock_doc.get('bucket')}")

                # Verificar expiração
                expira_em_str = lock_doc.get("expira_em")
                if expira_em_str:
                    try:
                        expira_em = datetime.fromisoformat(expira_em_str)
                        agora = datetime.now(FUSO_BR) if FUSO_BR else datetime.now()
                        expirado = expira_em <= agora
                        print(f"    Expirado? {expirado} (expira_em <= agora)")
                        print(f"      expira_em: {expira_em}")
                        print(f"      agora: {agora}")
                    except Exception as e:
                        print(f"    ❌ Erro ao verificar expiração: {e}")
            else:
                print(f"  ❌ NÃO EXISTE")
        except Exception as e:
            print(f"  ❌ Erro: {e}")

    print(f"\n\nRESUMO: {len(locks_encontrados)}/{len(LOCKS_ESPERADOS)} locks encontrados")
    return locks_encontrados


async def procurar_evento_correspondente(evento_id: str):
    """Procurar evento correspondente com ID exato e legado"""
    print(f"\n  Procurando evento: {evento_id}")

    # Tentar ID exato
    try:
        evento = await buscar_dado_em_path(f"Clientes/{TENANT_ID}/Eventos/{evento_id}")
        if evento:
            print(f"    ✓ ENCONTRADO (ID exato)")
            return True, "exato"
    except:
        pass

    # Tentar ID legado (remover hora)
    if "_" in evento_id:
        try:
            partes = evento_id.rsplit("_", 1)
            if len(partes) == 2:
                evento_id_legado = partes[0]
                print(f"    Tentando legado: {evento_id_legado}")
                evento = await buscar_dado_em_path(f"Clientes/{TENANT_ID}/Eventos/{evento_id_legado}")
                if evento:
                    print(f"    ✓ ENCONTRADO (ID legado)")
                    return True, "legado"
        except:
            pass

    print(f"    ❌ NÃO ENCONTRADO")
    return False, None


async def analisar_eventos_existentes():
    """Consultar TODOS os eventos e procurar por Bruna em 2026-11-06"""
    print("\n" + "="*80)
    print("ETAPA 2 — PROCURAR EVENTOS CORRESPONDENTES")
    print("="*80)

    # Buscar todos os eventos
    try:
        eventos = await buscar_subcolecao(f"Clientes/{TENANT_ID}/Eventos")
        print(f"\nTotal de eventos no tenant: {len(eventos) if eventos else 0}")

        # Filtrar para 2026-11-06 e profissional Bruna
        relevantes = []
        if eventos:
            for evento_item in eventos:
                evento = evento_item.get("data", evento_item) if isinstance(evento_item, dict) else evento_item

                if isinstance(evento, dict):
                    data = evento.get("data", "")
                    prof = evento.get("profissional", "")
                    hora_inicio = evento.get("hora_inicio", "")
                    evento_id = evento_item.get("id", "") if isinstance(evento_item, dict) and "id" in evento_item else ""

                    if "2026-11-06" in str(data) and "bruna" in str(prof).lower():
                        relevantes.append({
                            "evento_id": evento_id,
                            "data": data,
                            "profissional": prof,
                            "hora_inicio": hora_inicio,
                        })

        if relevantes:
            print(f"\n✓ Eventos de Bruna em 2026-11-06:")
            for ev in relevantes:
                print(f"  ID: {ev['evento_id']}")
                print(f"    data: {ev['data']}, hora_inicio: {ev['hora_inicio']}")
        else:
            print(f"\n❌ Nenhum evento de Bruna em 2026-11-06 encontrado")

        # Comparar com evento_id dos locks
        print(f"\nComparação com locks:")
        for lock_id, lock_data in locks_encontrados.items():
            evento_id = lock_data.get("evento_id", "")
            if evento_id:
                encontrado, tipo = await procurar_evento_correspondente(evento_id)
                if not encontrado:
                    print(f"  {lock_id}: evento_id={evento_id} → ❌ NÃO ENCONTRADO (órfão potencial)")
                else:
                    print(f"  {lock_id}: evento_id={evento_id} → ✓ Encontrado ({tipo})")

    except Exception as e:
        print(f"❌ Erro ao buscar eventos: {e}")
        import traceback
        traceback.print_exc()


async def comparar_com_funcao_p0_27_3():
    """Executar P0.27.3 e comparar com dados diretos"""
    print("\n" + "="*80)
    print("ETAPA 3 — EXECUTAR P0.27.3 E COMPARAR")
    print("="*80)

    print(f"\nExecutando liberar_locks_orfaos_expirados(dono_id='{TENANT_ID}', dry_run=True)...")

    try:
        resultado = await liberar_locks_orfaos_expirados(
            dono_id=TENANT_ID,
            dry_run=True
        )

        print(f"\nResultado da função:")
        print(f"  Identificados: {resultado['identificados']}")
        print(f"  Deletados: {resultado['deletados']}")
        print(f"  Modo: {resultado['modo']}")

        if resultado['identificados'] > 0:
            print(f"\n  Detalhes dos órfãos identificados:")
            for detail in resultado['detalhes']:
                print(f"    - {detail['lock_id']}")
                print(f"      evento_id: {detail['evento_id']}")
                print(f"      expira_em: {detail['expira_em']}")
                print(f"      status: {detail['status']}")
        else:
            print(f"\n  ⚠️ NENHUM ÓRFÃO IDENTIFICADO")

        # Comparar
        print(f"\nComparação:")
        print(f"  Locks encontrados diretamente: {len(locks_encontrados)}")
        print(f"  Locks identificados como órfãos: {resultado['identificados']}")

        if len(locks_encontrados) > 0 and resultado['identificados'] == 0:
            print(f"\n  ⚠️ DIVERGÊNCIA: Locks existem mas nenhum foi classificado como órfão")
            print(f"     Possíveis motivos:")
            print(f"     1. Eventos correspondentes foram encontrados")
            print(f"     2. Locks ainda não expirados (expira_em > agora)")
            print(f"     3. Status não é 'confirmado'")
            print(f"     4. Erro na lógica de filtragem da função")

    except Exception as e:
        print(f"❌ Erro ao executar função: {e}")
        import traceback
        traceback.print_exc()


async def verificar_divergencias():
    """Investigar possíveis divergências"""
    print("\n" + "="*80)
    print("ETAPA 4 — INVESTIGAR DIVERGÊNCIAS")
    print("="*80)

    if not locks_encontrados:
        print("\n❌ Nenhum lock encontrado — investigação concluída")
        return

    print(f"\nAnalisando {len(locks_encontrados)} locks encontrados:")

    for lock_id, lock_data in locks_encontrados.items():
        print(f"\n[{lock_id}]")

        status = lock_data.get("status", "")
        evento_id = lock_data.get("evento_id", "")
        expira_em = lock_data.get("expira_em", "")

        # Verificação 1: Status
        if status != "confirmado":
            print(f"  ⚠️ Status é '{status}', não 'confirmado' → não será considerado órfão")

        # Verificação 2: evento_id
        if not evento_id:
            print(f"  ⚠️ evento_id vazio → seria órfão por falta de ID")
        else:
            print(f"  evento_id: {evento_id}")

        # Verificação 3: Expiração
        if expira_em:
            try:
                expira_em_dt = datetime.fromisoformat(expira_em)
                agora = datetime.now(FUSO_BR) if FUSO_BR else datetime.now()

                # Converter ambos para timestamp para comparação
                expira_timestamp = expira_em_dt.timestamp()
                agora_timestamp = agora.timestamp()

                expirado = expira_timestamp <= agora_timestamp
                dias_restantes = (expira_em_dt - agora).total_seconds() / 86400

                print(f"  expira_em: {expira_em}")
                print(f"  agora: {agora}")
                print(f"  Expirado? {expirado}")
                print(f"  Dias restantes: {dias_restantes:.2f}")

                if not expirado:
                    print(f"  ⚠️ Lock ainda NÃO expirado → não será removido")
            except Exception as e:
                print(f"  ❌ Erro ao verificar expiração: {e}")

        # Verificação 4: Timezone
        print(f"  Verificação de timezone:")
        print(f"    FUSO_BR na função: {FUSO_BR}")
        print(f"    datetime.now() usa timezone local (naive ou UTC?)")


async def main():
    """Executar diagnóstico completo"""
    global locks_encontrados

    print("\n" + "#" * 80)
    print("# P0.27.4 — DIAGNÓSTICO READ-ONLY: Por que zero locks órfãos?")
    print("#" * 80)

    # Etapa 1: Consultar locks diretos
    locks_encontrados = await consultar_locks_diretos()

    # Etapa 2: Procurar eventos correspondentes
    await analisar_eventos_existentes()

    # Etapa 3: Comparar com função P0.27.3
    await comparar_com_funcao_p0_27_3()

    # Etapa 4: Investigar divergências
    await verificar_divergencias()

    print("\n" + "#" * 80)
    print("# P0.27.4 — DIAGNÓSTICO CONCLUÍDO")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
