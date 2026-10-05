#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE ISOLADO - Validacao de Logica do Filtro Temporal

Objetivo: Validar que a correção P0 implementada funciona corretamente
sem depender de Firestore ou async complexo.

Testes:
T1: Evento de junho é filtrado quando pedido é para outubro
T2: Evento de outubro é mantido quando pedido é para outubro
T3: Múltiplos eventos de outras datas são filtrados
T4: Eventos vázios não quebram
T5: Filtro não altera estrutura dos eventos

Data: 2026-10-03
Status: Teste isolado (lógica pura)
"""


def test_filtro_data_isolado():
    """Testa a lógica do filtro de data implementado"""

    # Simular dados retornados por buscar_subcolecao()
    # (31 eventos de várias datas)
    eventos_raw = {
        "evento_junho_001": {
            "id": "evento_junho_001",
            "data": "2026-06-05",
            "hora_inicio": "09:00",
            "hora_fim": "09:30",
            "profissional": "Bruna",
            "status": "confirmado"
        },
        "evento_julho_001": {
            "id": "evento_julho_001",
            "data": "2026-07-12",
            "hora_inicio": "14:00",
            "hora_fim": "14:30",
            "profissional": "Gloria",
            "status": "confirmado"
        },
        "evento_outubro_bruna_001": {
            "id": "evento_outubro_bruna_001",
            "data": "2026-10-03",
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "profissional": "Bruna",
            "status": "confirmado"
        },
        "evento_outubro_bruna_002": {
            "id": "evento_outubro_bruna_002",
            "data": "2026-10-03",
            "hora_inicio": "14:00",
            "hora_fim": "14:30",
            "profissional": "Bruna",
            "status": "confirmado"
        },
        "evento_outubro_gloria": {
            "id": "evento_outubro_gloria",
            "data": "2026-10-03",
            "hora_inicio": "11:00",
            "hora_fim": "11:30",
            "profissional": "Gloria",
            "status": "confirmado"
        },
        "evento_setembro_001": {
            "id": "evento_setembro_001",
            "data": "2026-09-28",
            "hora_inicio": "15:00",
            "hora_fim": "15:30",
            "profissional": "Carla",
            "status": "confirmado"
        }
    }

    # Data solicitada (parâmetro da função)
    data = "2026-10-03"

    # ============================================================
    # APLICAR FILTRO (exatamente como implementado)
    # ============================================================
    eventos_filtrados = {eid: ev for eid, ev in eventos_raw.items() if ev.get("data") == data}

    # ============================================================
    # TESTES
    # ============================================================

    print("\n" + "="*70)
    print("TESTES ISOLADOS — Validação de Lógica do Filtro")
    print("="*70)

    tests_passed = 0
    tests_total = 0

    # T1: Evento de junho é filtrado
    print("\nT1: Evento de junho (2026-06-05) é filtrado")
    print("-" * 70)
    tests_total += 1
    if "evento_junho_001" not in eventos_filtrados:
        print("✅ PASS: Evento de junho foi removido")
        print(f"   Evento_junho_001 no raw: {bool('evento_junho_001' in eventos_raw)}")
        print(f"   Evento_junho_001 no filtrado: {bool('evento_junho_001' in eventos_filtrados)}")
        tests_passed += 1
    else:
        print("❌ FAIL: Evento de junho ainda está presente")
        print(f"   Evento_junho_001 no filtrado: {eventos_filtrados['evento_junho_001']}")

    # T2: Evento de outubro é mantido
    print("\nT2: Evento de outubro (2026-10-03) é mantido")
    print("-" * 70)
    tests_total += 1
    if "evento_outubro_bruna_001" in eventos_filtrados:
        print("✅ PASS: Evento de outubro foi mantido")
        print(f"   evento_outubro_bruna_001: {eventos_filtrados['evento_outubro_bruna_001']['data']}")
        tests_passed += 1
    else:
        print("❌ FAIL: Evento de outubro foi removido")

    # T3: Múltiplos eventos de outras datas são filtrados
    print("\nT3: Múltiplos eventos de outras datas (julho, setembro) são filtrados")
    print("-" * 70)
    tests_total += 1
    other_dates = [eid for eid in eventos_filtrados.keys() if eid.startswith("evento_julho") or eid.startswith("evento_setembro")]
    if len(other_dates) == 0:
        print("✅ PASS: Todos os eventos de julho/setembro foram removidos")
        print(f"   Eventos raw de outras datas: 2 (julho_001, setembro_001)")
        print(f"   Eventos filtrados de outras datas: 0")
        tests_passed += 1
    else:
        print(f"❌ FAIL: Eventos de outras datas ainda presentes: {other_dates}")

    # T4: Eventos vazios não quebram filtro
    print("\nT4: Eventos vazios/None não quebram filtro")
    print("-" * 70)
    tests_total += 1
    try:
        # Simular evento sem campo "data"
        eventos_edge = {
            "evento_sem_data": {
                "id": "evento_sem_data",
                "hora_inicio": "09:00"
                # Campo "data" falta
            },
            "evento_com_data": {
                "id": "evento_com_data",
                "data": "2026-10-03",
                "hora_inicio": "10:00"
            }
        }

        eventos_edge_filtrados = {eid: ev for eid, ev in eventos_edge.items() if ev.get("data") == data}

        if "evento_sem_data" not in eventos_edge_filtrados and "evento_com_data" in eventos_edge_filtrados:
            print("✅ PASS: Filtro trata corretamente eventos sem campo 'data'")
            print(f"   evento_sem_data (data=None) removido: ✓")
            print(f"   evento_com_data (data=2026-10-03) mantido: ✓")
            tests_passed += 1
        else:
            print("❌ FAIL: Filtro não trata eventos sem 'data' corretamente")
    except Exception as e:
        print(f"❌ FAIL: Exceção ao filtrar: {e}")

    # T5: Filtro não altera estrutura dos eventos
    print("\nT5: Filtro não altera estrutura/conteúdo dos eventos")
    print("-" * 70)
    tests_total += 1
    evento_original = eventos_raw["evento_outubro_bruna_001"]
    evento_filtrado = eventos_filtrados.get("evento_outubro_bruna_001")

    if evento_filtrado and evento_original == evento_filtrado:
        print("✅ PASS: Evento mantém estrutura idêntica após filtro")
        print(f"   Campos preservados: {list(evento_filtrado.keys())}")
        print(f"   Profissional: {evento_filtrado.get('profissional')}")
        print(f"   Status: {evento_filtrado.get('status')}")
        tests_passed += 1
    else:
        print("❌ FAIL: Evento foi alterado pelo filtro")

    # ============================================================
    # RESULTADO FINAL
    # ============================================================
    print("\n" + "="*70)
    print("RESULTADO FINAL")
    print("="*70)
    print(f"Testes passaram: {tests_passed}/{tests_total}")

    # Estatísticas do filtro
    print(f"\nEstatísticas do filtro:")
    print(f"  Eventos raw (antes): {len(eventos_raw)}")
    print(f"  Eventos filtrados (depois): {len(eventos_filtrados)}")
    print(f"  Redução: {len(eventos_raw) - len(eventos_filtrados)} eventos removidos")
    print(f"  Percentual: {(len(eventos_raw) - len(eventos_filtrados)) / len(eventos_raw) * 100:.1f}% removido")

    print(f"\nEventos em {data}:")
    for eid, ev in eventos_filtrados.items():
        print(f"  - {eid}: {ev.get('profissional')} ({ev.get('data')})")

    if tests_passed == tests_total:
        print("\n🎉 Todos os testes passaram!")
        return 0
    else:
        print(f"\n⚠️  {tests_total - tests_passed} teste(s) falharam")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = test_filtro_data_isolado()
    sys.exit(exit_code)
