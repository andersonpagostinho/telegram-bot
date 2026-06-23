#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processar resultados de validacao e gerar relatorio final
"""

import json
import sys
from pathlib import Path

print("\n" + "="*70)
print("PROCESSANDO RESULTADOS DA VALIDACAO")
print("="*70 + "\n")

# Tentar ler arquivo de resultados
resultado_file = Path("validacao_resultados.json")

if not resultado_file.exists():
    print("[ERRO] Arquivo validacao_resultados.json nao encontrado")
    print("Testes ainda podem estar em execucao")
    sys.exit(1)

try:
    with open(resultado_file) as f:
        results = json.load(f)
except Exception as e:
    print(f"[ERRO] Falha ao ler resultados: {e}")
    sys.exit(1)

print(f"[OK] Lidos {len(results)} resultados de teste\n")

# Processar resultados
print("RESUMO POR TESTE")
print("="*70 + "\n")

p1_results = []
p0_result = None

for r in results:
    teste = r['teste']
    exit_code = r['exit_code']
    funcional = r['resultado_funcional']
    grpc = r['grpc_timeout']
    classificacao = r['classificacao']

    print(f"Teste: {teste}")
    print(f"  Exit code: {exit_code}")
    print(f"  Resultado funcional: {funcional}")
    print(f"  gRPC timeout: {grpc}")
    print(f"  Classificacao: {classificacao}")
    print()

    if "P1" in teste:
        p1_results.append({
            'nome': teste,
            'exit_code': exit_code,
            'funcional': funcional,
            'classificacao': classificacao
        })
    elif "P0" in teste:
        p0_result = {
            'nome': teste,
            'exit_code': exit_code,
            'funcional': funcional,
            'classificacao': classificacao
        }

# Tabela final
print("="*70)
print("TABELA FINAL DE RESULTADOS")
print("="*70 + "\n")

print(f"{'Suite':<30} | {'Exit':<5} | {'Resultado':<10} | {'Classificacao':<30}")
print("-"*80)

for r in p1_results:
    print(f"{r['nome']:<30} | {r['exit_code']:<5} | {r['funcional']:<10} | {r['classificacao']:<30}")

if p0_result:
    print(f"{p0_result['nome']:<30} | {p0_result['exit_code']:<5} | {p0_result['funcional']:<10} | {p0_result['classificacao']:<30}")

print()

# Verificar se pode rodar cenario 06
p1_all_pass = all(r['exit_code'] == 0 for r in p1_results)
p0_pass = p0_result and p0_result['exit_code'] == 0

print("\nCRITERIO PARA CENARIO 06:")
print(f"  P1 (3 suites): {len([r for r in p1_results if r['exit_code'] == 0])}/3 com exit code 0")
print(f"  P0 (1 suite): {'1/1 OK' if p0_pass else '0/1 FALHA'}")

if p1_all_pass and p0_pass:
    print("\n[OK] PODE RODAR CENARIO 06")
    sys.exit(0)
else:
    print("\n[BLOQUEIO] NAO PODE RODAR CENARIO 06")
    sys.exit(1)
