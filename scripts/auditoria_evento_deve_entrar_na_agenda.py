#!/usr/bin/env python3
"""
🔍 AUDITORIA: evento_deve_entrar_na_agenda()

Objetivo: Descobrir por que o evento 7394370553_bruna_2026-06-05_08:00 retorna False

Cenário: Evento possui praticamente todos os campos esperados,
então a falha deve estar em condição específica.

Estratégia: Testar cada condição isoladamente e documentar.
"""

import asyncio
import json
from datetime import datetime

# Importar Firebase
try:
    from services.firebase_service_async import buscar_subcolecao, buscar_dado_em_path
    from services.event_service_async import evento_deve_entrar_na_agenda
    firebase_disponivel = True
except ImportError as e:
    print(f"⚠️ Não conseguiu importar Firebase: {e}")
    firebase_disponivel = False


async def executar_auditoria():
    """Auditoria completa da função evento_deve_entrar_na_agenda()"""

    tenant_id = "7394370553"
    event_id = "7394370553_bruna_2026-06-05_08:00"
    data_evento = "2026-06-05"

    print("=" * 80)
    print(f"[AUDITORIA] evento_deve_entrar_na_agenda()")
    print("=" * 80)
    print(f"\nTenantID: {tenant_id}")
    print(f"EventID:  {event_id}")
    print(f"Data:     {data_evento}")
    print(f"\nData/Hora atual: {datetime.now()}")

    # ETAPA 1: Buscar evento no Firestore
    print("\n" + "=" * 80)
    print("[ETAPA 1] BUSCAR EVENTO NO FIRESTORE")
    print("=" * 80)

    if not firebase_disponivel:
        print("❌ Firebase não disponível. Encerrando.")
        return

    try:
        path_evento = f"Clientes/{tenant_id}/Eventos/{event_id}"
        print(f"Path: {path_evento}")

        evento = await buscar_dado_em_path(path_evento)

        if not evento:
            print(f"❌ EVENTO NÃO ENCONTRADO em {path_evento}")
            print("\n[DIAGNÓSTICO] O evento pode não existir ou estar em outro tenant.")

            # Tentar buscar por padrão
            print(f"\n[TENTATIVA] Buscando TODOS eventos do tenant {tenant_id}...")
            todos_eventos = await buscar_subcolecao(f"Clientes/{tenant_id}/Eventos") or {}
            print(f"Total de eventos encontrados: {len(todos_eventos)}")

            if todos_eventos:
                print("\nIds dos eventos:")
                for eid in list(todos_eventos.keys())[:10]:  # Mostrar primeiros 10
                    print(f"  - {eid}")
                if len(todos_eventos) > 10:
                    print(f"  ... e {len(todos_eventos) - 10} mais")
            else:
                print("❌ Nenhum evento encontrado para este tenant.")

            return

        print(f"✅ Evento encontrado!")
        print(f"\nConteúdo completo do evento (JSON):")
        print(json.dumps(evento, indent=2, default=str))

    except Exception as e:
        print(f"❌ Erro ao buscar evento: {e}")
        return

    # ETAPA 2: Testar cada condição da função
    print("\n" + "=" * 80)
    print("[ETAPA 2] TESTAR CADA CONDIÇÃO (isoladamente)")
    print("=" * 80)

    # Condição 1: tipo dict
    print(f"\n[COND 1] isinstance(evento, dict)?")
    cond1 = isinstance(evento, dict)
    print(f"  Resultado: {cond1}")
    if not cond1:
        print(f"  ❌ FALHA: Evento não é dict")
        return
    else:
        print(f"  ✅ PASS")

    # Condição 2: profissional não vazio
    print(f"\n[COND 2] evento.get('profissional') (não vazio)?")
    profissional = evento.get("profissional")
    print(f"  Valor: '{profissional}' (tipo: {type(profissional).__name__})")
    cond2 = bool(profissional)
    print(f"  bool(profissional): {cond2}")
    if not cond2:
        print(f"  ❌ FALHA: Profissional está vazio ou None")
        print(f"     Condicional retorna False neste ponto.")
        return
    else:
        print(f"  ✅ PASS")

    # Condição 3: status não é cancelado
    print(f"\n[COND 3] status != cancelado/removido/excluído?")
    status = str(evento.get("status") or "").strip().lower()
    print(f"  Valor original: {evento.get('status')}")
    print(f"  Valor normalizado: '{status}'")
    status_bloqueados = ["cancelado", "cancelada", "removido", "removida", "excluido", "excluído"]
    cond3 = status not in status_bloqueados
    print(f"  Status em lista bloqueada? {status in status_bloqueados}")
    print(f"  Condição passa (retorna True)? {cond3}")
    if not cond3:
        print(f"  ❌ FALHA: Status está na lista bloqueada")
        print(f"     Condicional retorna False neste ponto.")
        return
    else:
        print(f"  ✅ PASS")

    # Condição 4: estrutura mínima
    print(f"\n[COND 4] Estrutura mínima (data + hora_inicio + hora_fim)?")
    data = evento.get("data")
    hora_inicio = evento.get("hora_inicio")
    hora_fim = evento.get("hora_fim")
    print(f"  data: {data} (tipo: {type(data).__name__})")
    print(f"  hora_inicio: {hora_inicio} (tipo: {type(hora_inicio).__name__})")
    print(f"  hora_fim: {hora_fim} (tipo: {type(hora_fim).__name__})")
    cond4 = bool(data and hora_inicio and hora_fim)
    print(f"  Todos preenchidos? {cond4}")
    if not cond4:
        print(f"  ❌ FALHA: Falta estrutura mínima")
        print(f"     Condicional retorna False neste ponto.")
        return
    else:
        print(f"  ✅ PASS")

    # Condição 5: data_consulta (opcional)
    print(f"\n[COND 5] data_consulta comparação?")
    data_consulta = None  # Testa com None primeiro
    print(f"  data_consulta passada: {data_consulta}")
    if data_consulta:
        cond5 = evento.get("data") == data_consulta
        print(f"  evento.get('data') == data_consulta? {cond5}")
        if not cond5:
            print(f"  ❌ FALHA: Data do evento não bate com data_consulta")
            print(f"     Condicional retorna False neste ponto.")
            return
    else:
        cond5 = True
        print(f"  data_consulta não foi passada, condição é ignorada")
        print(f"  ✅ PASS (não aplicável)")

    # ETAPA 3: Chamar a função real
    print("\n" + "=" * 80)
    print("[ETAPA 3] CHAMAR FUNÇÃO REAL")
    print("=" * 80)

    resultado_real = evento_deve_entrar_na_agenda(
        evento_id=event_id,
        evento=evento,
        data_consulta=None  # Sem data_consulta
    )

    print(f"\nevento_deve_entrar_na_agenda(")
    print(f"  evento_id='{event_id}',")
    print(f"  evento={{ ... }},")
    print(f"  data_consulta=None")
    print(f") → {resultado_real}")

    if not resultado_real:
        print(f"\n❌ RESULTADO: Função retorna False")
        print(f"\n[DIAGNÓSTICO] As condições testadas acima mostram que TODAS deveriam passar.")
        print(f"Possibilidades:")
        print(f"  1. Condição avaliada diferente da expectativa (valores inesperados)")
        print(f"  2. Formato de campo é diferente do esperado (ex: lista vs string)")
        print(f"  3. Hay um valor nulo/None que não foi visualizado no JSON acima")
        print(f"  4. Campo profissional é string vazia ou falsy de outra forma")
    else:
        print(f"\n✅ RESULTADO: Função retorna True (elegível para agenda)")

    # ETAPA 4: Testar com data_consulta
    print("\n" + "=" * 80)
    print("[ETAPA 4] TESTE COM DATA_CONSULTA")
    print("=" * 80)

    resultado_com_data = evento_deve_entrar_na_agenda(
        evento_id=event_id,
        evento=evento,
        data_consulta=data_evento  # Com data específica
    )

    print(f"\nevento_deve_entrar_na_agenda(")
    print(f"  evento_id='{event_id}',")
    print(f"  evento={{ ... }},")
    print(f"  data_consulta='{data_evento}'")
    print(f") → {resultado_com_data}")

    if evento.get("data") != data_evento:
        print(f"\n⚠️ Data não bate!")
        print(f"  evento.get('data'): {evento.get('data')}")
        print(f"  data_consulta: {data_evento}")

    # ETAPA 5: Teste com data diferente
    print("\n" + "=" * 80)
    print("[ETAPA 5] TESTE COM DATA DIFERENTE (2026-10-03)")
    print("=" * 80)

    resultado_data_diferente = evento_deve_entrar_na_agenda(
        evento_id=event_id,
        evento=evento,
        data_consulta="2026-10-03"  # Data do pedido atual
    )

    print(f"\nevento_deve_entrar_na_agenda(")
    print(f"  evento_id='{event_id}',")
    print(f"  evento={{ ... }},")
    print(f"  data_consulta='2026-10-03'")
    print(f") → {resultado_data_diferente}")

    print(f"\n[DIAGNÓSTICO] Isso é esperado (evento é de junho, pedido é de outubro).")
    print(f"Mas isso explica se a função está sendo chamada com data_consulta passada.")

    # RESUMO FINAL
    print("\n" + "=" * 80)
    print("[RESUMO FINAL]")
    print("=" * 80)
    print(f"\nEvento: {event_id}")
    print(f"evento_deve_entrar_na_agenda(data_consulta=None):      {resultado_real}")
    print(f"evento_deve_entrar_na_agenda(data_consulta='{data_evento}'): {resultado_com_data}")
    print(f"evento_deve_entrar_na_agenda(data_consulta='2026-10-03'): {resultado_data_diferente}")

    print(f"\n[CONCLUSÃO]")
    if not resultado_real:
        print(f"Se resultado_real é False, significa que uma das 4 primeiras condições está falhando.")
        print(f"Revise:")
        print(f"  - Tipo do campo profissional (string? não é None?)")
        print(f"  - Tipo do campo data (string no formato correto?)")
        print(f"  - Tipo do campo hora_inicio (string no formato correto?)")
        print(f"  - Tipo do campo hora_fim (string no formato correto?)")
    else:
        print(f"Evento DEVERIA passar pelo filtro evento_deve_entrar_na_agenda().")
        print(f"Se está sendo descartado em outro lugar, o bloqueador é diferente.")


# Executar
if __name__ == "__main__":
    asyncio.run(executar_auditoria())
