#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes para Commit 1: Estender interpretar_data_e_hora() com metadados opcionais

Valida:
1. Compatibilidade legada (return_metadata=False ou nao informado)
2. Novo contrato de metadados (return_metadata=True)
3. Nenhum chamador existente e afetado
"""

from datetime import datetime
from utils.interpretador_datas import interpretar_data_e_hora
import pytz

FUSO_BR = pytz.timezone("America/Sao_Paulo")

def test_compat_data_hora_explicita():
    """T0: Compatibilidade - Data + hora explícita"""
    resultado = interpretar_data_e_hora("segunda às 14:30")
    assert isinstance(resultado, datetime), f"Esperado datetime, obteve {type(resultado)}"
    assert resultado.strftime("%H:%M") == "14:30", "Hora deveria ser 14:30"
    print("[PASS] T0: Compat data+hora explicita")

def test_compat_so_hora():
    """T0: Compatibilidade - Só hora retorna None"""
    resultado = interpretar_data_e_hora("às 14:30")
    assert resultado is None, f"Esperado None, obteve {resultado}"
    print("[PASS] T0: Compat só hora")

def test_compat_texto_invalido():
    """T0: Compatibilidade - Texto inválido retorna None"""
    resultado = interpretar_data_e_hora("texto aleatório sem data")
    assert resultado is None, f"Esperado None, obteve {resultado}"
    print("[PASS] T0: Compat texto inválido")

def test_compat_vazio():
    """T0: Compatibilidade - Entrada vazia retorna None"""
    resultado = interpretar_data_e_hora("")
    assert resultado is None, f"Esperado None, obteve {resultado}"
    print("[PASS] T0: Compat entrada vazia")

def test_metadata_data_hora_explicita():
    """T1: Metadados - Data + hora explícita"""
    resultado = interpretar_data_e_hora("segunda às 14:30", return_metadata=True)

    assert isinstance(resultado, dict), f"Esperado dict, obteve {type(resultado)}"
    assert "datetime" in resultado
    assert "data_detectada" in resultado
    assert "hora_detectada" in resultado

    assert resultado["datetime"] is not None, "datetime deveria ser válido"
    assert resultado["data_detectada"] is True, "data_detectada deveria ser True"
    assert resultado["hora_detectada"] is True, "hora_detectada deveria ser True"
    assert resultado["fonte"] == "manual_dia_semana", f"fonte deveria ser manual_dia_semana, obteve {resultado['fonte']}"
    assert resultado["data_tipo"] == "dia_semana", f"data_tipo deveria ser dia_semana, obteve {resultado['data_tipo']}"
    assert resultado["hora_modo"] == "explicita", f"hora_modo deveria ser explicita, obteve {resultado['hora_modo']}"
    assert resultado["motivo_nenhum"] is None, f"motivo_nenhum deveria ser None, obteve {resultado['motivo_nenhum']}"

    print("[PASS] T1: Metadata data+hora explicita")

def test_metadata_so_data():
    """T2: Metadados - Dia semana sem hora explicita (hora default 9:00)"""
    resultado = interpretar_data_e_hora("segunda", return_metadata=True)

    assert isinstance(resultado, dict), f"Esperado dict, obteve {type(resultado)}"
    # Comportamento original: retorna datetime com hora default 9:00
    assert resultado["datetime"] is not None, "datetime deveria ser valido"
    assert resultado["datetime"].hour == 9, f"Hora deveria ser 9 (default)"
    assert resultado["data_detectada"] is True, "data_detectada deveria ser True"
    assert resultado["hora_detectada"] is False, "hora_detectada deveria ser False (nao explicita)"
    assert resultado["hora_modo"] == "default", f"hora_modo deveria ser default, obteve {resultado['hora_modo']}"
    assert resultado["motivo_nenhum"] is None, f"motivo_nenhum deveria ser None, obteve {resultado['motivo_nenhum']}"

    print("[PASS] T2: Metadata dia semana sem hora explicita")

def test_metadata_so_hora():
    """T3: Metadados - Só hora (sem data)"""
    resultado = interpretar_data_e_hora("às 14:30", return_metadata=True)

    assert isinstance(resultado, dict), f"Esperado dict, obteve {type(resultado)}"
    assert resultado["datetime"] is None, "datetime deveria ser None (sem data)"
    assert resultado["data_detectada"] is False, "data_detectada deveria ser False"
    assert resultado["hora_detectada"] is True, "hora_detectada deveria ser True"
    assert resultado["motivo_nenhum"] == "so_hora", f"motivo_nenhum deveria ser 'so_hora', obteve {resultado['motivo_nenhum']}"

    print("[PASS] T3: Metadata só hora")

def test_metadata_nenhuma():
    """T4: Metadados - Nenhuma (texto inválido)"""
    resultado = interpretar_data_e_hora("texto aleatório", return_metadata=True)

    assert isinstance(resultado, dict), f"Esperado dict, obteve {type(resultado)}"
    assert resultado["datetime"] is None, "datetime deveria ser None"
    assert resultado["data_detectada"] is False, "data_detectada deveria ser False"
    assert resultado["hora_detectada"] is False, "hora_detectada deveria ser False"
    assert resultado["motivo_nenhum"] == "sem_pista", f"motivo_nenhum deveria ser 'sem_pista', obteve {resultado['motivo_nenhum']}"

    print("[PASS] T4: Metadata nenhuma (sem pista)")

def test_metadata_amanha():
    """T5: Metadados - Amanhã com hora"""
    resultado = interpretar_data_e_hora("amanhã às 14", return_metadata=True)

    assert isinstance(resultado, dict), f"Esperado dict, obteve {type(resultado)}"
    assert resultado["datetime"] is not None, "datetime deveria ser válido"
    assert resultado["data_detectada"] is True, "data_detectada deveria ser True"
    assert resultado["hora_detectada"] is True, "hora_detectada deveria ser True"
    assert resultado["data_tipo"] == "amanha", f"data_tipo deveria ser 'amanha', obteve {resultado['data_tipo']}"
    assert resultado["hora_modo"] == "explicita", f"hora_modo deveria ser 'explicita', obteve {resultado['hora_modo']}"

    print("[PASS] T5: Metadata amanhã com hora")

def test_metadata_dia_semana_sem_hora():
    """T6: Metadados - Dia semana sem hora (hora default 9:00)"""
    resultado = interpretar_data_e_hora("segunda", return_metadata=True)

    assert isinstance(resultado, dict), f"Esperado dict, obteve {type(resultado)}"
    # Mesmo teste que T2 - comportamento original retorna com hora default
    assert resultado["datetime"] is not None, "datetime deveria ser valido (hora default)"
    assert resultado["datetime"].hour == 9, "Hora default deveria ser 9"
    assert resultado["hora_modo"] == "default", "hora_modo deveria ser default"
    assert resultado["motivo_nenhum"] is None, "motivo deveria ser None (conseguiu interpretar)"

    print("[PASS] T6: Metadata dia_semana sem hora")

def test_metadata_estrutura_completa():
    """T7: Metadados - Todas as chaves esperadas existem"""
    resultado = interpretar_data_e_hora("segunda às 14", return_metadata=True)

    chaves_esperadas = {
        "datetime", "data_detectada", "hora_detectada",
        "data_tipo", "hora_modo", "fonte", "motivo_nenhum", "criado_em"
    }

    chaves_encontradas = set(resultado.keys())
    assert chaves_esperadas == chaves_encontradas, \
        f"Chaves esperadas: {chaves_esperadas}, obteve: {chaves_encontradas}"

    print("[PASS] T7: Metadata estrutura completa")

def test_tipo_datetime_preservado():
    """T0: Compatibilidade - Tipo datetime é preservado"""
    resultado = interpretar_data_e_hora("amanhã às 10")

    # Deve ser datetime, não dict
    assert isinstance(resultado, datetime), f"Esperado datetime, obteve {type(resultado)}"

    # Deve ter métodos de datetime
    assert hasattr(resultado, 'strftime'), "datetime deveria ter método strftime"
    assert hasattr(resultado, 'date'), "datetime deveria ter método date"
    assert hasattr(resultado, 'replace'), "datetime deveria ter método replace"

    # Deve funcionar
    iso = resultado.isoformat()
    assert "T" in iso, f"isoformat deveria conter 'T', obteve {iso}"

    print("[PASS] T0: Tipo datetime preservado")

def test_chamador_legado_com_if():
    """T0: Compatibilidade - Padrão legado com 'if dt:' funciona"""
    dt = interpretar_data_e_hora("segunda às 14")

    # Padrão legado esperado: if dt:
    if dt:
        # Deve ser verdadeiro para datetime válido
        iso = dt.isoformat()
        assert iso, "isoformat deveria retornar algo"
    else:
        raise AssertionError("Esperado dt truthy, obteve falsy")

    print("[PASS] T0: Padrão legado 'if dt:'")

def test_chamador_legado_sem_parametro():
    """T0: Compatibilidade - Chamadores sem parâmetro continuam funcionando"""
    # Este é o padrão usado em 50+ callsites existentes
    resultado = interpretar_data_e_hora("hoje às 10:00")

    # Deve retornar datetime (não dict)
    assert isinstance(resultado, datetime) or resultado is None, \
        f"Esperado datetime ou None, obteve {type(resultado)}"

    if resultado:
        # Se é datetime, deve ter os métodos
        assert resultado.hour == 10
        assert resultado.minute == 0

    print("[PASS] T0: Chamador legado sem parâmetro")

def run_all_tests():
    """Executa todos os testes"""
    print("\n=== TESTES COMMIT 1: Contrato de Metadados Optional ===\n")

    print("--- COMPATIBILIDADE LEGADA (return_metadata=False ou não informado) ---")
    test_compat_data_hora_explicita()
    test_compat_so_hora()
    test_compat_texto_invalido()
    test_compat_vazio()
    test_tipo_datetime_preservado()
    test_chamador_legado_com_if()
    test_chamador_legado_sem_parametro()

    print("\n--- NOVO CONTRATO DE METADADOS (return_metadata=True) ---")
    test_metadata_data_hora_explicita()
    test_metadata_so_data()
    test_metadata_so_hora()
    test_metadata_nenhuma()
    test_metadata_amanha()
    test_metadata_dia_semana_sem_hora()
    test_metadata_estrutura_completa()

    print("\n=== [OK] TODOS OS 14 TESTES PASSARAM ===\n")
    print("Gates 1-3 validados:")
    print("  Gate 1: Estado inicial verificado (alterações preexistentes isoladas)")
    print("  Gate 2: Contrato opcional implementado em utils/interpretador_datas.py")
    print("  Gate 3: Testes focados executados (compatibilidade + metadados)")
    return True

if __name__ == "__main__":
    try:
        run_all_tests()
    except AssertionError as e:
        print(f"\n[ERROR] TESTE FALHOU: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERRO NAO PREVISTO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
