#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE ISOLADO - Validacao de Logica do Filtro Temporal
Data: 2026-10-03
"""

def test_t1_evento_junho_filtrado():
    """T1: Evento de junho (2026-06-05) e filtrado quando pedido e para outubro"""
    eventos_raw = {
        "evento_junho_001": {"data": "2026-06-05", "profissional": "Bruna"},
        "evento_outubro_001": {"data": "2026-10-03", "profissional": "Bruna"}
    }
    data = "2026-10-03"
    eventos_filtrados = {eid: ev for eid, ev in eventos_raw.items() if ev.get("data") == data}

    passed = "evento_junho_001" not in eventos_filtrados
    status = "PASS" if passed else "FAIL"
    print("[%s] T1: Evento de junho filtrado" % status)
    print("  Raw: %d eventos, Filtrado: %d eventos" % (len(eventos_raw), len(eventos_filtrados)))
    return passed

def test_t2_evento_outubro_mantido():
    """T2: Evento de outubro (2026-10-03) e mantido"""
    eventos_raw = {
        "evento_junho_001": {"data": "2026-06-05", "profissional": "Bruna"},
        "evento_outubro_001": {"data": "2026-10-03", "profissional": "Bruna"}
    }
    data = "2026-10-03"
    eventos_filtrados = {eid: ev for eid, ev in eventos_raw.items() if ev.get("data") == data}

    passed = "evento_outubro_001" in eventos_filtrados
    status = "PASS" if passed else "FAIL"
    print("[%s] T2: Evento de outubro mantido" % status)
    return passed

def test_t3_multiplos_eventos_outras_datas():
    """T3: Multiplos eventos de outras datas sao filtrados"""
    eventos_raw = {
        "evento_junho": {"data": "2026-06-05"},
        "evento_julho": {"data": "2026-07-12"},
        "evento_setembro": {"data": "2026-09-28"},
        "evento_outubro_1": {"data": "2026-10-03"},
        "evento_outubro_2": {"data": "2026-10-03"}
    }
    data = "2026-10-03"
    eventos_filtrados = {eid: ev for eid, ev in eventos_raw.items() if ev.get("data") == data}

    passed = len(eventos_filtrados) == 2 and len(eventos_raw) == 5
    status = "PASS" if passed else "FAIL"
    print("[%s] T3: Multiplos eventos de outras datas filtrados" % status)
    print("  Raw: %d eventos, Filtrado: %d eventos" % (len(eventos_raw), len(eventos_filtrados)))
    print("  Reducao: %d%%" % ((len(eventos_raw) - len(eventos_filtrados)) / len(eventos_raw) * 100))
    return passed

def test_t4_eventos_sem_data():
    """T4: Eventos vazios/None nao quebram filtro"""
    eventos_raw = {
        "evento_sem_data": {"profissional": "Bruna"},
        "evento_com_data": {"data": "2026-10-03", "profissional": "Bruna"}
    }
    data = "2026-10-03"

    try:
        eventos_filtrados = {eid: ev for eid, ev in eventos_raw.items() if ev.get("data") == data}
        passed = len(eventos_filtrados) == 1 and "evento_com_data" in eventos_filtrados
        status = "PASS" if passed else "FAIL"
        print("[%s] T4: Eventos vazios nao quebram filtro" % status)
        return passed
    except Exception as e:
        print("[FAIL] T4: Excecao ao filtrar: %s" % str(e))
        return False

def test_t5_estrutura_preservada():
    """T5: Filtro nao altera estrutura/conteudo dos eventos"""
    evento_original = {
        "data": "2026-10-03",
        "hora_inicio": "09:00",
        "profissional": "Bruna",
        "status": "confirmado",
        "cliente_nome": "Joao"
    }
    eventos_raw = {"evento_001": evento_original}
    data = "2026-10-03"
    eventos_filtrados = {eid: ev for eid, ev in eventos_raw.items() if ev.get("data") == data}

    evento_filtrado = eventos_filtrados.get("evento_001")
    passed = evento_filtrado == evento_original
    status = "PASS" if passed else "FAIL"
    print("[%s] T5: Estrutura preservada apos filtro" % status)
    if passed:
        print("  Campos: %s" % list(evento_filtrado.keys()))
    return passed

def main():
    print("\n" + "="*70)
    print("TESTES ISOLADOS - Validacao de Logica do Filtro Temporal")
    print("="*70 + "\n")

    results = [
        test_t1_evento_junho_filtrado(),
        test_t2_evento_outubro_mantido(),
        test_t3_multiplos_eventos_outras_datas(),
        test_t4_eventos_sem_data(),
        test_t5_estrutura_preservada()
    ]

    print("\n" + "="*70)
    passed = sum(results)
    total = len(results)
    print("RESULTADO: %d/%d testes passaram" % (passed, total))
    print("="*70)

    if passed == total:
        print("\n[SUCCESS] Todos os testes passaram!")
        return 0
    else:
        print("\n[WARNING] %d teste(s) falharam" % (total - passed))
        return 1

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
