#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes unitarios para Commit 2: Logica de salvamento de metadados

Nao requer OpenAI, Firestore ou credenciais externas.
Valida apenas a logica de deciso sobre quando salvar metadados.
"""

from utils.interpretador_datas import interpretar_data_e_hora

def simular_salvamento_metadata(dt_e_meta):
    """
    Simula a logica de Gate 1:
    'Salvar ctx["_temporal_metadata"] somente se ha informacao util'
    """
    if dt_e_meta.get("data_detectada") or dt_e_meta.get("hora_detectada"):
        return {
            "data_detectada": dt_e_meta.get("data_detectada"),
            "hora_detectada": dt_e_meta.get("hora_detectada"),
            "data_tipo": dt_e_meta.get("data_tipo"),
            "hora_modo": dt_e_meta.get("hora_modo"),
            "fonte": dt_e_meta.get("fonte"),
            "motivo_nenhum": dt_e_meta.get("motivo_nenhum"),
        }
    return None

def test_salva_data_hora_explicita():
    """T1: Data+hora explicita = salva metadados"""
    meta = interpretar_data_e_hora("segunda as 14:30", return_metadata=True)
    resultado = simular_salvamento_metadata(meta)

    assert resultado is not None, "Deveria salvar metadados"
    assert resultado["data_detectada"] is True
    assert resultado["hora_detectada"] is True
    assert resultado["hora_modo"] == "explicita"
    print("[PASS] T1: Salva data+hora explicita")

def test_salva_dia_semana_sem_hora():
    """T2: Dia semana sem hora = salva (data_detectada=True)"""
    meta = interpretar_data_e_hora("segunda", return_metadata=True)
    resultado = simular_salvamento_metadata(meta)

    assert resultado is not None, "Deveria salvar (tem data)"
    assert resultado["data_detectada"] is True
    assert resultado["hora_detectada"] is False
    assert resultado["hora_modo"] == "default"
    print("[PASS] T2: Salva dia semana (hora default)")

def test_salva_so_hora():
    """T3: So hora = salva (hora_detectada=True)"""
    meta = interpretar_data_e_hora("as 14:30", return_metadata=True)
    resultado = simular_salvamento_metadata(meta)

    assert resultado is not None, "Deveria salvar (tem hora)"
    assert resultado["data_detectada"] is False
    assert resultado["hora_detectada"] is True
    assert resultado["motivo_nenhum"] == "so_hora"
    print("[PASS] T3: Salva so hora")

def test_nao_salva_sem_pista():
    """T4: Sem pista = nao salva (guardiao IF bloqueia)"""
    meta = interpretar_data_e_hora("texto aleatorio", return_metadata=True)
    resultado = simular_salvamento_metadata(meta)

    assert resultado is None, "Nao deveria salvar (sem pista temporal)"
    print("[PASS] T4: Nao salva sem pista")

def test_nao_salva_entrada_vazia():
    """T5: Entrada vazia = nao salva"""
    meta = interpretar_data_e_hora("", return_metadata=True)
    resultado = simular_salvamento_metadata(meta)

    assert resultado is None, "Nao deveria salvar entrada vazia"
    print("[PASS] T5: Nao salva entrada vazia")

def test_compatibilidade_datetime_retorno():
    """T6: Quando return_metadata=False, continua retornando datetime | None"""
    # Sem metadados = compatibilidade preservada
    resultado = interpretar_data_e_hora("segunda as 14:30")

    # Deve ser datetime, nao dict
    from datetime import datetime
    assert isinstance(resultado, datetime), f"Esperado datetime, obteve {type(resultado)}"
    assert resultado.hour == 14
    assert resultado.minute == 30
    print("[PASS] T6: Compatibilidade datetime preservada")

def test_preserva_comportamento_so_hora():
    """T7: Behavior original de 'so hora' = None (sem data)"""
    # Original: "as 14" retorna None (nao assume data)
    resultado_compat = interpretar_data_e_hora("as 14")
    assert resultado_compat is None, "Comportamento original: so hora = None"

    # Com metadata: mostra que hora foi detectada
    meta = interpretar_data_e_hora("as 14", return_metadata=True)
    assert meta["datetime"] is None
    assert meta["hora_detectada"] is True
    assert meta["data_detectada"] is False
    assert meta["motivo_nenhum"] == "so_hora"
    print("[PASS] T7: Preserva comportamento original so_hora")

def test_hora_modo_vs_hora_detectada():
    """T8: Distinguir 'hora_modo=default' de 'hora_detectada=True'"""
    # Dia semana sem hora: default (nao informado)
    meta_default = interpretar_data_e_hora("segunda", return_metadata=True)
    assert meta_default["hora_modo"] == "default"
    assert meta_default["hora_detectada"] is False  # Nao foi informado!

    # Dia semana com hora: explicita (informado)
    meta_explicita = interpretar_data_e_hora("segunda as 14", return_metadata=True)
    assert meta_explicita["hora_modo"] == "explicita"
    assert meta_explicita["hora_detectada"] is True  # Foi informado!

    print("[PASS] T8: hora_modo vs hora_detectada diferenciados")

def run_all_tests():
    """Executa todos os testes"""
    print("\n=== TESTES COMMIT 2: Logica de Salvamento de Metadados ===\n")

    try:
        test_salva_data_hora_explicita()
        test_salva_dia_semana_sem_hora()
        test_salva_so_hora()
        test_nao_salva_sem_pista()
        test_nao_salva_entrada_vazia()
        test_compatibilidade_datetime_retorno()
        test_preserva_comportamento_so_hora()
        test_hora_modo_vs_hora_detectada()

        print("\n=== [OK] TODOS OS 8 TESTES PASSARAM ===\n")
        print("Gate 2 validado:")
        print("  - Logica de salvamento de _temporal_metadata correta")
        print("  - Guardiao IF evita sobrescrever com dados vazios")
        print("  - Compatibilidade datetime preservada")
        print("  - Comportamento original mantido")
        return True
    except AssertionError as e:
        print(f"\n[ERROR] TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = run_all_tests()
    exit(0 if resultado else 1)
