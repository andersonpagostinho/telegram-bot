#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar configuracao de encoding UTF-8 a todos os runners de teste
"""

import os
import re
from pathlib import Path

def adicionar_encoding_a_arquivo(arquivo_path):
    """Adiciona reconfiguração de UTF-8 ao arquivo"""
    with open(arquivo_path, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Se já tem sys.stdout.reconfigure, pular
    if 'sys.stdout.reconfigure' in conteudo:
        print(f"  [SKIP] {arquivo_path.name} - já tem reconfiguração")
        return False

    # Se não tem encoding declaration, adicionar
    if '# -*- coding: utf-8 -*-' not in conteudo:
        conteudo = '# -*- coding: utf-8 -*-\n' + conteudo

    # Encontrar a primeira linha com 'import sys' e adicionar reconfiguração depois
    linhas = conteudo.split('\n')
    indice_sys = -1
    indice_path = -1

    for i, linha in enumerate(linhas):
        if 'import sys' in linha and indice_sys == -1:
            indice_sys = i
        if 'sys.path.insert' in linha and indice_path == -1:
            indice_path = i
            break

    if indice_sys >= 0:
        # Adicionar reconfiguração após o import sys (ou após outros imports)
        # Encontrar o próximo import ou a próxima linha não-import
        insercao_indice = indice_sys + 1
        while insercao_indice < len(linhas):
            if linhas[insercao_indice].startswith('import ') or linhas[insercao_indice].startswith('from '):
                insercao_indice += 1
            elif linhas[insercao_indice].strip() == '':
                insercao_indice += 1
            else:
                break

        # Adicionar blank line se necessário
        if insercao_indice < len(linhas) and linhas[insercao_indice].strip() != '':
            linhas.insert(insercao_indice, '')
            insercao_indice += 1

        # Adicionar reconfiguração
        codigo_reconfig = [
            '# Configurar UTF-8 para Windows',
            'if sys.platform == "win32":',
            '    sys.stdout.reconfigure(encoding="utf-8", errors="replace")',
            '    sys.stderr.reconfigure(encoding="utf-8", errors="replace")',
            ''
        ]

        for j, linha in enumerate(codigo_reconfig):
            linhas.insert(insercao_indice + j, linha)

        conteudo_novo = '\n'.join(linhas)

        with open(arquivo_path, 'w', encoding='utf-8') as f:
            f.write(conteudo_novo)

        print(f"  [OK] {arquivo_path.name} - reconfiguração adicionada")
        return True
    else:
        print(f"  [SKIP] {arquivo_path.name} - 'import sys' não encontrado")
        return False

def main():
    diretorio = Path('tests')

    print("Adicionando reconfiguração UTF-8 a todos os runners...\n")

    # Encontrar todos os runners
    runners = sorted(diretorio.glob('runner*.py'))

    if not runners:
        print("Nenhum runner encontrado")
        return

    total = 0
    modificados = 0

    for arquivo in runners:
        total += 1
        if adicionar_encoding_a_arquivo(arquivo):
            modificados += 1

    print(f"\nResumo:")
    print(f"  Total de runners: {total}")
    print(f"  Modificados: {modificados}")
    print(f"  Já com reconfiguração: {total - modificados}")

if __name__ == '__main__':
    main()
