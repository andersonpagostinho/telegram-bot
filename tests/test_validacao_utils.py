"""
[TEST] C3.17-I1: Testes Unitarios da Funcao de Validacao Centralizada
======================================================================

Objetivo: Validar que validar_tipo_usuario() e normalizar_tipo_usuario()
funcionam corretamente em todos os casos.

Testes obrigatorios: I1-T01 a I1-T15
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validacao_utils import validar_tipo_usuario, normalizar_tipo_usuario


def test_i1_t01_validar_dono():
    """I1-T01: validar_tipo_usuario('dono') == True"""
    assert validar_tipo_usuario("dono") is True
    print("[PASS] I1-T01")


def test_i1_t02_validar_profissional():
    """I1-T02: validar_tipo_usuario('profissional') == True"""
    assert validar_tipo_usuario("profissional") is True
    print("[PASS] I1-T02")


def test_i1_t03_validar_cliente():
    """I1-T03: validar_tipo_usuario('cliente') == True"""
    assert validar_tipo_usuario("cliente") is True
    print("[PASS] I1-T03")


def test_i1_t04_validar_dono_uppercase():
    """I1-T04: validar_tipo_usuario('DONO') == True"""
    assert validar_tipo_usuario("DONO") is True
    print("[PASS] I1-T04")


def test_i1_t05_validar_profissional_espacos():
    """I1-T05: validar_tipo_usuario(' Profissional ') == True"""
    assert validar_tipo_usuario(" Profissional ") is True
    print("[PASS] I1-T05")


def test_i1_t06_validar_cliente_espacos():
    """I1-T06: validar_tipo_usuario('cliente ') == True"""
    assert validar_tipo_usuario("cliente ") is True
    print("[PASS] I1-T06")


def test_i1_t07_validar_vazio():
    """I1-T07: validar_tipo_usuario('') == False"""
    assert validar_tipo_usuario("") is False
    print("[PASS] I1-T07")


def test_i1_t08_validar_administrador():
    """I1-T08: validar_tipo_usuario('administrador') == False"""
    assert validar_tipo_usuario("administrador") is False
    print("[PASS] I1-T08")


def test_i1_t09_validar_admin():
    """I1-T09: validar_tipo_usuario('admin') == False"""
    assert validar_tipo_usuario("admin") is False
    print("[PASS] I1-T09")


def test_i1_t10_validar_none():
    """I1-T10: validar_tipo_usuario(None) == False"""
    assert validar_tipo_usuario(None) is False
    print("[PASS] I1-T10")


def test_i1_t11_validar_numero():
    """I1-T11: validar_tipo_usuario(123) == False"""
    assert validar_tipo_usuario(123) is False
    print("[PASS] I1-T11")


def test_i1_t12_normalizar_dono():
    """I1-T12: normalizar_tipo_usuario(' DONO ') == 'dono'"""
    assert normalizar_tipo_usuario(" DONO ") == "dono"
    print("[PASS] I1-T12")


def test_i1_t13_normalizar_profissional():
    """I1-T13: normalizar_tipo_usuario('profissional') == 'profissional'"""
    assert normalizar_tipo_usuario("profissional") == "profissional"
    print("[PASS] I1-T13")


def test_i1_t14_normalizar_cliente():
    """I1-T14: normalizar_tipo_usuario('cliente') == 'cliente'"""
    assert normalizar_tipo_usuario("cliente") == "cliente"
    print("[PASS] I1-T14")


def test_i1_t15_normalizar_invalido():
    """I1-T15: normalizar_tipo_usuario('admin') is None"""
    assert normalizar_tipo_usuario("admin") is None
    print("[PASS] I1-T15")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("C3.17-I1 - TESTES UNITARIOS (I1-T01 a I1-T15)")
    print("="*70 + "\n")

    try:
        test_i1_t01_validar_dono()
        test_i1_t02_validar_profissional()
        test_i1_t03_validar_cliente()
        test_i1_t04_validar_dono_uppercase()
        test_i1_t05_validar_profissional_espacos()
        test_i1_t06_validar_cliente_espacos()
        test_i1_t07_validar_vazio()
        test_i1_t08_validar_administrador()
        test_i1_t09_validar_admin()
        test_i1_t10_validar_none()
        test_i1_t11_validar_numero()
        test_i1_t12_normalizar_dono()
        test_i1_t13_normalizar_profissional()
        test_i1_t14_normalizar_cliente()
        test_i1_t15_normalizar_invalido()

        print("\n" + "="*70)
        print("RESULTADO: 15/15 PASS")
        print("="*70 + "\n")

    except AssertionError as e:
        print(f"\nFALHA: {e}")
        import traceback
        traceback.print_exc()
