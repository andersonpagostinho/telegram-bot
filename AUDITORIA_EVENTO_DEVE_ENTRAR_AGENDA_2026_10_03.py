#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 AUDITORIA: evento_deve_entrar_na_agenda()

Contexto: Evento 7394370553_bruna_2026-06-05_08:00 retorna False
Expectativa: Evento possui praticamente todos os campos esperados
Objetivo: Descobrir qual condição específica está falhando

Estratégia: Testar cada condição isoladamente com evento real do Firestore
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import buscar_dado_em_path
from services.event_service_async import evento_deve_entrar_na_agenda


async def executar_auditoria():
    """Auditoria completa"""

    tenant_id = "7394370553"
    event_id = "7394370553_bruna_2026-06-05_08:00"
    data_evento = "2026-06-05"

    print("=" * 90)
    print("[AUDITORIA] evento_deve_entrar_na_agenda()")
    print("=" * 90)
    print(f"TenantID: {tenant_id}")
    print(f"EventID:  {event_id}")
    print(f"DataEvento: {data_evento}")

    # ETAPA 1: Buscar evento
    print("\n" + "=" * 90)
    print("[ETAPA 1] BUSCAR EVENTO NO FIRESTORE")
    print("=" * 90)

    path_evento = f"Clientes/{tenant_id}/Eventos/{event_id}"
    print(f"Path: {path_evento}\n")

    try:
        evento = await buscar_dado_em_path(path_evento)
    except Exception as e:
        print(f"❌ ERRO ao buscar: {e}")
        return

    if not evento:
        print(f"❌ EVENTO NÃO ENCONTRADO")
        print(f"\n[DIAGNÓSTICO] O evento não existe em {path_evento}")
        print(f"Possibilidades:")
        print(f"  1. Evento já foi deletado")
        print(f"  2. Evento está em outro tenant")
        print(f"  3. Tenant_id está incorreto")
        return

    print(f"✅ Evento encontrado!\n")
    print(f"Conteúdo (JSON):")
    print(json.dumps(evento, indent=2, default=str))

    # ETAPA 2: Testar cada condição
    print("\n" + "=" * 90)
    print("[ETAPA 2] TESTAR CADA CONDIÇÃO (isoladamente)")
    print("=" * 90)

    falhou_em = None

    # CONDIÇÃO 1: isinstance dict
    print(f"\n[COND 1] isinstance(evento, dict)?")
    cond1_resultado = isinstance(evento, dict)
    print(f"  Resultado: {cond1_resultado}")
    if not cond1_resultado:
        print(f"  ❌ FALHA AQUI: Evento não é dict")
        falhou_em = "COND 1 (type check)"
    else:
        print(f"  ✅ PASS")

    # CONDIÇÃO 2: profissional não vazio
    print(f"\n[COND 2] evento.get('profissional') (não vazio)?")
    prof_valor = evento.get("profissional")
    prof_tipo = type(prof_valor).__name__
    prof_bool = bool(prof_valor)
    print(f"  Valor: {repr(prof_valor)}")
    print(f"  Tipo: {prof_tipo}")
    print(f"  bool(profissional): {prof_bool}")
    if not prof_bool:
        print(f"  ❌ FALHA AQUI: Profissional está vazio, None ou falsy")
        if falhou_em is None:
            falhou_em = "COND 2 (profissional vazio)"
    else:
        print(f"  ✅ PASS")

    # CONDIÇÃO 3: status não cancelado
    print(f"\n[COND 3] status != cancelado/removido/excluído?")
    status_valor = evento.get("status")
    status_normalizado = str(status_valor or "").strip().lower()
    lista_bloqueada = ["cancelado", "cancelada", "removido", "removida", "excluido", "excluído"]
    status_bloqueado = status_normalizado in lista_bloqueada
    print(f"  Valor original: {repr(status_valor)}")
    print(f"  Normalizado: {repr(status_normalizado)}")
    print(f"  Está na lista bloqueada? {status_bloqueado}")
    if status_bloqueado:
        print(f"  ❌ FALHA AQUI: Status está em lista bloqueada")
        if falhou_em is None:
            falhou_em = "COND 3 (status bloqueado)"
    else:
        print(f"  ✅ PASS")

    # CONDIÇÃO 4: estrutura mínima (data + hora_inicio + hora_fim)
    print(f"\n[COND 4] Estrutura mínima (data + hora_inicio + hora_fim)?")
    data_valor = evento.get("data")
    hora_inicio_valor = evento.get("hora_inicio")
    hora_fim_valor = evento.get("hora_fim")
    print(f"  data: {repr(data_valor)} (tipo: {type(data_valor).__name__})")
    print(f"  hora_inicio: {repr(hora_inicio_valor)} (tipo: {type(hora_inicio_valor).__name__})")
    print(f"  hora_fim: {repr(hora_fim_valor)} (tipo: {type(hora_fim_valor).__name__})")

    data_ok = bool(data_valor)
    hora_ini_ok = bool(hora_inicio_valor)
    hora_fim_ok = bool(hora_fim_valor)

    print(f"  data preenchido? {data_ok}")
    print(f"  hora_inicio preenchido? {hora_ini_ok}")
    print(f"  hora_fim preenchido? {hora_fim_ok}")

    cond4_resultado = data_ok and hora_ini_ok and hora_fim_ok
    print(f"  Resultado (AND): {cond4_resultado}")

    if not cond4_resultado:
        print(f"  ❌ FALHA AQUI: Falta estrutura mínima")
        if falhou_em is None:
            if not data_ok:
                falhou_em = "COND 4 (data vazia)"
            elif not hora_ini_ok:
                falhou_em = "COND 4 (hora_inicio vazia)"
            else:
                falhou_em = "COND 4 (hora_fim vazia)"
    else:
        print(f"  ✅ PASS")

    # CONDIÇÃO 5: data_consulta (opcional)
    print(f"\n[COND 5] data_consulta comparação?")
    print(f"  data_consulta não foi passada → condição ignorada")
    print(f"  ✅ PASS (não aplicável)")

    # ETAPA 3: Chamar função real
    print("\n" + "=" * 90)
    print("[ETAPA 3] CHAMAR FUNÇÃO REAL")
    print("=" * 90)

    try:
        resultado_sem_data = evento_deve_entrar_na_agenda(
            evento_id=event_id,
            evento=evento,
            data_consulta=None
        )
        print(f"\nevento_deve_entrar_na_agenda(..., data_consulta=None)")
        print(f"  → {resultado_sem_data}")
    except Exception as e:
        print(f"❌ Erro ao chamar função: {e}")
        resultado_sem_data = None

    try:
        resultado_com_data = evento_deve_entrar_na_agenda(
            evento_id=event_id,
            evento=evento,
            data_consulta=data_evento
        )
        print(f"\nevento_deve_entrar_na_agenda(..., data_consulta='{data_evento}')")
        print(f"  → {resultado_com_data}")
    except Exception as e:
        print(f"❌ Erro ao chamar função: {e}")
        resultado_com_data = None

    # ETAPA 4: Diagnóstico
    print("\n" + "=" * 90)
    print("[ETAPA 4] DIAGNÓSTICO E CONCLUSÃO")
    print("=" * 90)

    if resultado_sem_data is False:
        print(f"\n⚠️ RESULTADO: Função retorna False (mesmo sem data_consulta)")
        print(f"\nIsso significa que uma das 4 condições estruturais está falhando:")
        print(f"  - Tipo do evento não é dict")
        print(f"  - profissional está vazio/None/falsy")
        print(f"  - status está em lista bloqueada")
        print(f"  - Falta data, hora_inicio ou hora_fim")

        if falhou_em:
            print(f"\n📍 FALHA IDENTIFICADA: {falhou_em}")
        else:
            print(f"\n❓ Nenhuma falha óbvia nas condições testadas.")
            print(f"   Possibilidades adicionais:")
            print(f"     1. Condição usada lógica diferente (ex: 'not evento' vs '== None')")
            print(f"     2. Campo tem tipo inesperado (ex: lista, dict)")
            print(f"     3. Normalização de string tem comportamento inesperado")

    elif resultado_sem_data is True:
        print(f"\n✅ RESULTADO: Função retorna True (elegível para agenda)")
        print(f"\n[DIAGNÓSTICO] Evento DEVERIA passar pelo filtro evento_deve_entrar_na_agenda()")
        print(f"Se está sendo descartado, o bloqueador está EM OUTRO LUGAR:")
        print(f"  - Em verificar_conflito_e_sugestoes_profissional() (confere com data_consulta)")
        print(f"  - Em buscar_eventos_por_intervalo() (filtro de data)")
        print(f"  - Em evento_deve_ser_ignorado() (função alternativa?)")
        print(f"  - Em lógica de roteamento/fluxo")

    else:
        print(f"\n❌ ERRO: Função retornou {resultado_sem_data} (inesperado)")

    # CONTEXTO
    print("\n" + "=" * 90)
    print("[CONTEXTO] Informações adicionais")
    print("=" * 90)
    print(f"\nPedido atual: 2026-10-03 09:00–09:30")
    print(f"Evento: 2026-06-05 08:00–??:??")
    print(f"\n[NOTA] Há 5 meses de diferença. Se data_consulta='2026-10-03' for passado,")
    print(f"       evento será descartado por data diferente (COND 5).")
    print(f"       Isso é CORRETO e esperado.")
    print(f"\n[PERGUNTA CRÍTICA] Qual função está chamando evento_deve_entrar_na_agenda()?")
    print(f"  → É verificar_conflito_e_sugestoes_profissional() que passa data_consulta?")
    print(f"  → É buscar_eventos_por_intervalo() que filtra por data?")
    print(f"\nSem responder isso, não conseguimos saber se o filtro está correto ou errado.")


if __name__ == "__main__":
    asyncio.run(executar_auditoria())
