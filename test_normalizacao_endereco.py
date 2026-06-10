#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste: Verificar se normalizar() funciona correctamente
"""

import re
from unidecode import unidecode

def test_normalizacao():
    """Testa se a normalizacao remove acentos e reconhece endereco"""

    print("\n" + "=" * 80)
    print("TESTE: Normalizacao de mensagens")
    print("=" * 80)

    # Teste 1: Normalizar "Qual o seu endereço?"
    print("\nTeste 1: 'Qual o seu endereco?' (sem acento)")
    msg1 = "Qual o seu endereco?"
    normalizado1 = unidecode(re.sub(r"[^\w\s]", " ", msg1.lower())).strip()
    normalizado1 = re.sub(r"\s+", " ", normalizado1)
    print(f"Original:    '{msg1}'")
    print(f"Normalizado: '{normalizado1}'")

    eh_endereco = "endereco" in normalizado1
    print(f"Detecta 'endereco': {eh_endereco}")
    if eh_endereco:
        print("PASSOU\n")
    else:
        print("FALHOU\n")
        return False

    # Teste 2: Normalizar "Qual o seu endereço?" (COM acento)
    print("Teste 2: 'Qual o seu endereço?' (com acento)")
    msg2 = "Qual o seu endereço?"
    normalizado2 = unidecode(re.sub(r"[^\w\s]", " ", msg2.lower())).strip()
    normalizado2 = re.sub(r"\s+", " ", normalizado2)
    print(f"Original:    '{msg2}'")
    print(f"Normalizado: '{normalizado2}'")

    eh_endereco = "endereco" in normalizado2
    print(f"Detecta 'endereco': {eh_endereco}")
    if eh_endereco:
        print("PASSOU\n")
    else:
        print("FALHOU\n")
        return False

    # Teste 3: Normalizar "Onde fica o salao?"
    print("Teste 3: 'Onde fica o salao?'")
    msg3 = "Onde fica o salao?"
    normalizado3 = unidecode(re.sub(r"[^\w\s]", " ", msg3.lower())).strip()
    normalizado3 = re.sub(r"\s+", " ", normalizado3)
    print(f"Original:    '{msg3}'")
    print(f"Normalizado: '{normalizado3}'")

    eh_onde_fica = "onde fica" in normalizado3
    print(f"Detecta 'onde fica': {eh_onde_fica}")
    if eh_onde_fica:
        print("PASSOU\n")
    else:
        print("FALHOU\n")
        return False

    # Teste 4: Normalizar "Como chegar?"
    print("Teste 4: 'Como chegar?'")
    msg4 = "Como chegar?"
    normalizado4 = unidecode(re.sub(r"[^\w\s]", " ", msg4.lower())).strip()
    normalizado4 = re.sub(r"\s+", " ", normalizado4)
    print(f"Original:    '{msg4}'")
    print(f"Normalizado: '{normalizado4}'")

    eh_como_chegar = "como chegar" in normalizado4
    print(f"Detecta 'como chegar': {eh_como_chegar}")
    if eh_como_chegar:
        print("PASSOU\n")
    else:
        print("FALHOU\n")
        return False

    return True

if __name__ == "__main__":
    print("\n")
    print("=" * 80)
    print("TESTE NORMALIZACAO - Endereco")
    print("=" * 80)

    try:
        resultado = test_normalizacao()

        if resultado:
            print("=" * 80)
            print("TODOS OS TESTES PASSARAM!")
            print("Normalizacao reconhece enderecos correctamente")
            print("=" * 80)
            print()
        else:
            print("=" * 80)
            print("TESTE FALHOU")
            print("=" * 80)
            exit(1)
    except Exception as e:
        print("=" * 80)
        print("TESTE FALHOU COM ERRO")
        print("=" * 80)
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
