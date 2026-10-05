#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DIAGNÓSTICO FIRESTORE REAL

Objetivo: Verificar documentos reais em Firestore e reproduzir filtro

APENAS LEITURA — NENHUMA ALTERAÇÃO
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import buscar_subcolecao, buscar_dado_em_path


async def main():
    print("=" * 100)
    print("[DIAGNÓSTICO FIRESTORE REAL] 2026-10-03")
    print("=" * 100)

    tenant_id = "7394370553"
    path_eventos = f"Clientes/{tenant_id}/Eventos"

    # ==================================================
    # 1. LEITURA FIRESTORE REAL
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 1] LEITURA FIRESTORE REAL")
    print("=" * 100)
    print(f"Path: {path_eventos}\n")

    try:
        eventos_raw = await buscar_subcolecao(path_eventos)
    except Exception as e:
        print(f"❌ Erro ao buscar: {e}")
        return

    if not eventos_raw:
        print("❌ Nenhum evento encontrado")
        return

    print(f"✅ Total de documentos no Firestore: {len(eventos_raw)}\n")

    # Análise de datas
    stats = {
        "total": len(eventos_raw),
        "data_2026_10_03": 0,
        "data_2026_06_05": 0,
        "sem_data": 0,
        "data_formato_errado": 0,
        "data_tipo_errado": 0,
        "eventos_junho": [],
        "eventos_outubro": [],
    }

    print("[ANÁLISE DE DATAS]")
    for event_id, evento in eventos_raw.items():
        data_valor = evento.get("data")

        if data_valor is None:
            stats["sem_data"] += 1
        elif not isinstance(data_valor, str):
            stats["data_tipo_errado"] += 1
            print(f"  ⚠️ {event_id}: tipo={type(data_valor).__name__}, valor={data_valor}")
        elif data_valor == "2026-10-03":
            stats["data_2026_10_03"] += 1
            stats["eventos_outubro"].append(event_id)
        elif data_valor == "2026-06-05":
            stats["data_2026_06_05"] += 1
            stats["eventos_junho"].append((event_id, evento))
        else:
            # Verificar formato YYYY-MM-DD
            try:
                datetime.strptime(data_valor, "%Y-%m-%d")
            except ValueError:
                stats["data_formato_errado"] += 1
                print(f"  ⚠️ {event_id}: formato inválido='{data_valor}'")

    print(f"\n  Total documentos:           {stats['total']}")
    print(f"  data == '2026-10-03':       {stats['data_2026_10_03']}")
    print(f"  data == '2026-06-05':       {stats['data_2026_06_05']}")
    print(f"  sem campo data:             {stats['sem_data']}")
    print(f"  data formato inválido:      {stats['data_formato_errado']}")
    print(f"  data tipo inválido:         {stats['data_tipo_errado']}")

    # ==================================================
    # 2. DOCUMENTO ESPECÍFICO
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 2] DOCUMENTO ESPECÍFICO")
    print("=" * 100)

    event_id_target = "7394370553_bruna_2026-06-05_08:00"
    path_target = f"{path_eventos}/{event_id_target}"
    print(f"Path: {path_target}\n")

    try:
        evento_target = await buscar_dado_em_path(path_target)
    except Exception as e:
        print(f"❌ Erro ao buscar: {e}")
        evento_target = None

    if evento_target:
        print(f"✅ Documento encontrado:\n")
        campos_importantes = [
            "id", "profissional", "data", "hora_inicio", "hora_fim",
            "status", "confirmado", "cliente_id"
        ]
        for campo in campos_importantes:
            valor = evento_target.get(campo)
            print(f"  {campo:20} = {repr(valor)}")

        data_real = evento_target.get("data")
        if data_real == "2026-06-05":
            print(f"\n  ✅ Confirmado: data == '2026-06-05'")
        else:
            print(f"\n  ⚠️ VALOR REAL: data == {repr(data_real)} (esperado: '2026-06-05')")
    else:
        print(f"❌ Documento NÃO encontrado")

    # ==================================================
    # 3. OUTROS EVENTOS DE JUNHO
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 3] OUTROS EVENTOS DE JUNHO")
    print("=" * 100)
    print(f"Documentos com data == '2026-06-05': {len(stats['eventos_junho'])}\n")

    for i, (eid, evento) in enumerate(stats["eventos_junho"][:5]):
        print(f"[{i+1}] ID: {eid}")
        print(f"    data: {evento.get('data')}")
        print(f"    profissional: {evento.get('profissional')}")
        print(f"    hora_inicio: {evento.get('hora_inicio')}")
        print()

    if len(stats["eventos_junho"]) > 5:
        print(f"... e {len(stats['eventos_junho']) - 5} mais")

    # ==================================================
    # 4. EVENTOS DE 2026-10-03
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 4] EVENTOS DE 2026-10-03")
    print("=" * 100)
    print(f"Documentos com data == '2026-10-03': {stats['data_2026_10_03']}\n")

    if stats["data_2026_10_03"] == 0:
        print("❌ Não existem eventos com data == '2026-10-03' no Firestore.")
    else:
        for event_id in stats["eventos_outubro"]:
            evento = eventos_raw[event_id]
            print(f"ID: {event_id}")
            print(f"  profissional: {evento.get('profissional')}")
            print(f"  data: {evento.get('data')}")
            print(f"  hora_inicio: {evento.get('hora_inicio')}")
            print(f"  hora_fim: {evento.get('hora_fim')}")
            print(f"  status: {evento.get('status')}")
            print(f"  confirmado: {evento.get('confirmado')}")
            print()

    # ==================================================
    # 5. REPRODUZIR FILTRO TEMPORAL
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 5] REPRODUZIR FILTRO TEMPORAL")
    print("=" * 100)

    data_inicio = data(2026, 10, 3)
    data_fim = date(2026, 10, 3)
    print(f"data_inicio: {data_inicio}")
    print(f"data_fim: {data_fim}\n")

    print("[TESTE DE FILTRO: data_inicio <= data_evento <= data_fim]\n")

    # Testar eventos de junho e outubro
    eventos_teste = stats["eventos_junho"][:3] + [
        (eid, eventos_raw[eid]) for eid in stats["eventos_outubro"][:3]
    ]

    for event_id, evento in eventos_teste:
        data_str = evento.get("data")
        try:
            data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
            passa = data_inicio <= data_evento <= data_fim
            print(f"ID: {event_id}")
            print(f"  data_str: '{data_str}'")
            print(f"  data_evento: {data_evento}")
            print(f"  passa_filtro: {passa}")
            print()
        except ValueError as e:
            print(f"ID: {event_id}")
            print(f"  ❌ Erro ao converter: {e}")
            print()

    # ==================================================
    # 6. EXECUTAR FUNÇÃO REAL
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 6] EXECUTAR FUNÇÃO REAL")
    print("=" * 100)

    try:
        from services.event_service_async import buscar_eventos_por_intervalo

        resultado = await buscar_eventos_por_intervalo(
            tenant_id,
            dia_especifico=date(2026, 10, 3)
        )

        print(f"✅ Função executada com sucesso\n")
        print(f"Quantidade retornada: {len(resultado)}\n")

        if resultado:
            print("[EVENTOS RETORNADOS]")
            for evento in resultado:
                event_id = evento.get("event_id", "???")
                data = evento.get("data")
                print(f"  ID: {event_id}")
                print(f"    data: {data}")
                print(f"    profissional: {evento.get('profissional')}")
                print()
        else:
            print("Nenhum evento retornado (resultado vazio)")

    except Exception as e:
        print(f"❌ Erro ao executar função: {e}")
        import traceback
        traceback.print_exc()

    # ==================================================
    # 7. LOCALIZAR LOG "31"
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 7] ORIGEM DO LOG '31'")
    print("=" * 100)

    from services.event_service_async import buscar_eventos_por_intervalo as func_raw
    import inspect

    source = inspect.getsource(func_raw)
    lines = source.split("\n")

    print("Procurando por logs/prints na função...\n")
    for i, line in enumerate(lines):
        if "print" in line or "Total de eventos" in line or "[DIAG]" in line:
            print(f"[Linha {i}] {line}")

    print("\n[VERIFICAÇÃO]")
    print("Linha 209 (stream()): buscar_subcolecao() retorna TODOS")
    print("Linha 226-250: Loop filtra por data")
    print("Linha 252: return resultado (após filtro)")

    # ==================================================
    # 8. RASTREAMENTO DO EVENTO DE JUNHO
    # ==================================================
    print("\n" + "=" * 100)
    print("[ETAPA 8] RASTREAMENTO DO EVENTO")
    print("=" * 100)

    print(f"Evento: {event_id_target}\n")

    # 1. Entrou no stream()?
    entrou_stream = event_id_target in eventos_raw
    print(f"1. entrou no stream()? {'SIM' if entrou_stream else 'NÃO'}")

    if entrou_stream:
        evento_junho = eventos_raw[event_id_target]
        data_junho = evento_junho.get("data")

        # 2. Passou pelo filtro de data?
        try:
            data_evento_junho = datetime.strptime(data_junho, "%Y-%m-%d").date()
            passa_filtro = date(2026, 10, 3) <= data_evento_junho <= date(2026, 10, 3)
        except:
            passa_filtro = False

        print(f"   data: {data_junho}")
        print(f"2. passou pelo filtro de data? {'SIM' if passa_filtro else 'NÃO'}")

        # 3. Entrou na lista retornada?
        try:
            resultado = await buscar_eventos_por_intervalo(
                tenant_id,
                dia_especifico=date(2026, 10, 3)
            )
            entrou_resultado = any(
                ev.get("event_id") == event_id_target for ev in resultado
            )
        except:
            entrou_resultado = False

        print(f"3. entrou na lista retornada? {'SIM' if entrou_resultado else 'NÃO'}")

        # 4 e 5 dependem de execução completa do handler
        print(f"4. chegou ao event_handler.py? [requer execução completa]")
        print(f"5. chegou a evento_deve_entrar_na_agenda()? [requer execução completa]")

    # ==================================================
    # 10. TABELA FINAL
    # ==================================================
    print("\n" + "=" * 100)
    print("[TABELA FINAL]")
    print("=" * 100)
    print()

    tabela = [
        ("documentos no Firestore", len(eventos_raw)),
        ("data == 2026-10-03", stats["data_2026_10_03"]),
        ("data == 2026-06-05", stats["data_2026_06_05"]),
        ("sem data", stats["sem_data"]),
        ("data formato inválido", stats["data_formato_errado"]),
        ("stream()", len(eventos_raw)),
        ("após filtro temporal", len(resultado) if 'resultado' in locals() else "?"),
        ("retorno da função", len(resultado) if 'resultado' in locals() else "?"),
    ]

    for etapa, qtd in tabela:
        print(f"  {etapa:40} {qtd}")

    # ==================================================
    # CONCLUSÃO
    # ==================================================
    print("\n" + "=" * 100)
    print("[CONCLUSÃO]")
    print("=" * 100)

    if stats["data_2026_10_03"] == 0:
        print("\n❌ NÃO existem eventos com data == '2026-10-03'")
        print(f"   Existem {stats['data_2026_06_05']} eventos com data == '2026-06-05'")
    else:
        print(f"\n✅ Existem {stats['data_2026_10_03']} eventos com data == '2026-10-03'")

    print("\nA/B/C:")
    try:
        if len(resultado) > 0:
            eventos_junho_retornados = [
                ev for ev in resultado if ev.get("data") == "2026-06-05"
            ]
            if eventos_junho_retornados:
                print(f"\n❌ A) Sim, função está retornando eventos de junho: {len(eventos_junho_retornados)}")
            else:
                print(f"\n✅ B) Não, número '31' é apenas documentos brutos antes do filtro")
        else:
            print(f"\n✅ B) Não, função retorna lista vazia (filtro funciona)")
    except:
        print("\n❓ Não foi possível determinar (erro na execução)")


if __name__ == "__main__":
    asyncio.run(main())
