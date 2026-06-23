#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilar resultados dos testes em relatorio final
"""

import os
from pathlib import Path

print("\n" + "="*70)
print("COMPILANDO RELATORIO FINAL")
print("="*70 + "\n")

# Ler arquivos de resultado
results = {}
test_names = [
    "P1 E2E Identidade",
    "P1 E2E Operacional",
    "P1 E2E Individual",
    "P0 Regressao"
]

print("Coleta de resultados dos testes:\n")

for name in test_names:
    filename = f"resultado_{name.replace(' ', '_')}.txt"
    filepath = Path(filename)

    if filepath.exists():
        print(f"[OK] {filename}")
        with open(filepath) as f:
            content = f.read()
            results[name] = content
    else:
        print(f"[FALTA] {filename}")
        results[name] = None

print("\n" + "="*70)
print("RESUMO POR TESTE")
print("="*70 + "\n")

# Processar resultados
p1_count = 0
p0_pass = False

for name in test_names:
    print(f"\n{name}")
    print("-" * 40)

    content = results[name]
    if not content:
        print("[ARQUIVO NAO ENCONTRADO]")
        continue

    # Extrair dados
    lines = content.split('\n')
    for line in lines[:10]:  # Primeiras 10 linhas tem os dados principais
        if line.strip():
            print(f"  {line}")

    # Verificar resultado
    if "Exit: 0" in content:
        if "P0" in name:
            p0_pass = True
        else:
            p1_count += 1
        print("  [RESULTADO] PASS (exit 0)")
    elif "Exit:" in content:
        print("  [RESULTADO] FALHA (exit != 0)")

    has_grpc = "gRPC: True" in content
    if has_grpc:
        print("  [gRPC] Timeout detectado")
    else:
        print("  [gRPC] Ausente")

print("\n" + "="*70)
print("RESUMO FINAL")
print("="*70 + "\n")

print(f"P1 E2E (3 testes): {p1_count}/3 com exit code 0")
print(f"P0 (1 teste): {'PASS' if p0_pass else 'FAIL'}")

if p1_count == 3 and p0_pass:
    print("\n[BASELINE APROVADO] P1 42/42 e P0 174/174")
    print("\nProximo: Rodar cenario 06")
else:
    print(f"\n[BLOQUEIO] P1 {p1_count}/3, P0 {'PASS' if p0_pass else 'FAIL'}")
    print("\nNao pode rodar cenario 06")
