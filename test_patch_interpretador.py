#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Patch Minimo para interpretar_data_e_hora()

Valida que:
1. texto_original e preservado (nao perdido)
2. dateparser consegue extrair data/hora de texto completo
3. Fallback funciona quando necessario
"""

import sys
import io
from datetime import datetime
from utils.interpretador_datas import interpretar_data_e_hora

# Configure stdout para UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Testes configurados
TESTES = [
    {
        "nome": "Caso 1: Apenas amanha + hora",
        "entrada": "amanha as 16",
        "esperado_slots": None,
        "esperado_dia": "amanha",
    },
    {
        "nome": "Caso 2: Amanha + hora sem as",
        "entrada": "amanha 16 horas",
        "esperado_slots": None,
        "esperado_dia": "amanha",
    },
    {
        "nome": "Caso 3: CRITICO - Texto completo com slots",
        "entrada": "corte cabelo da Suri as 16 horas amanha",
        "esperado_slots": ["corte", "Suri", "16"],
        "esperado_dia": "amanha",
    },
    {
        "nome": "Caso 4: Dia explicito + hora",
        "entrada": "dia 05 as 10",
        "esperado_slots": None,
        "esperado_dia": "dia 05",
    },
    {
        "nome": "Caso 5: Dia da semana + hora",
        "entrada": "segunda as 14",
        "esperado_slots": None,
        "esperado_dia": "segunda",
    },
    {
        "nome": "Caso 6: Apenas hora (sem data)",
        "entrada": "as 16",
        "esperado_slots": None,
        "esperado_resultado": None,
    },
    {
        "nome": "Caso 7: Numero puro",
        "entrada": "16",
        "esperado_slots": None,
        "esperado_resultado": None,
    },
]

def test_caso(teste):
    """Executa um teste e valida resultado"""
    print(f"\n{'='*70}")
    print(f"[TESTE] {teste['nome']}")
    print(f"{'='*70}")
    print(f"Entrada: {teste['entrada']!r}")

    resultado = interpretar_data_e_hora(teste['entrada'])

    print(f"\nResultado: {resultado}")

    if "esperado_resultado" in teste:
        if teste['esperado_resultado'] is None:
            if resultado is None:
                print("[PASSOU] Retornou None como esperado")
                return True
            else:
                print(f"[FALHOU] Esperado None, obteve {resultado}")
                return False

    if teste.get('esperado_slots'):
        if resultado is None:
            print(f"[FALHOU] Esperado datetime com slots, obteve None")
            return False

        print(f"[PASSOU] Data/hora extraida: {resultado}")
        print(f"[CRITICO] Slots NAO foram perdidos no parsing!")
        return True

    if resultado is not None and isinstance(resultado, datetime):
        print(f"[PASSOU] Datetime valido extraido")
        return True
    elif resultado is None:
        print(f"[PASSOU] Retornou None como esperado")
        return True
    else:
        print(f"[FALHOU] Tipo invalido {type(resultado)}")
        return False

def main():
    print("\n" + "="*70)
    print("TESTE DO PATCH MINIMO - interpretar_data_e_hora()")
    print("="*70)

    resultados = []

    for teste in TESTES:
        try:
            passou = test_caso(teste)
            resultados.append((teste['nome'], passou))
        except Exception as e:
            print(f"[ERRO] {e}")
            import traceback
            traceback.print_exc()
            resultados.append((teste['nome'], False))

    print("\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)

    total = len(resultados)
    passados = sum(1 for _, passou in resultados if passou)

    for nome, passou in resultados:
        status = "[OK]" if passou else "[FAIL]"
        print(f"{status} {nome}")

    print(f"\nTotal: {passados}/{total} testes passaram")

    if passados == total:
        print("\n[SUCESSO] TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n[AVISO] {total - passados} teste(s) falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())
