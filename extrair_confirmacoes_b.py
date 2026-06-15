#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai mensagens Categoria B relacionadas a confirmação de agendamento
Inclui: confirmação, cancelamento, reagendamento, pendente
"""

import os
import re
import sys
from pathlib import Path

# Configurar UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Palavras-chave para identificar mensagens de confirmação
PALAVRAS_CHAVE = [
    'confirma',
    'cancelamento',
    'reagendamento',
    'pendente',
    'confirmado',
    'agendamento',
    'horário',
    'hora',
    'concluído',
    'marcado',
    'reserva',
]

def extrair_confirmacoes():
    """Extrai mensagens de confirmação da auditoria"""

    caminho_auditoria = 'AUDITORIA_MENSAGENS_P1.md'

    if not os.path.exists(caminho_auditoria):
        print(f"Arquivo {caminho_auditoria} não encontrado")
        return

    with open(caminho_auditoria, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Dividir por seção de Categoria B
    if '## B - HUMANIZAR' not in conteudo:
        print("Categoria B não encontrada")
        return

    # Extrair apenas seção B
    inicio_b = conteudo.find('## B - HUMANIZAR')
    fim_c = conteudo.find('## C - REESCREVER', inicio_b)

    if fim_c == -1:
        secao_b = conteudo[inicio_b:]
    else:
        secao_b = conteudo[inicio_b:fim_c]

    # Padrão para extrair mensagens
    # Formato: **Função:** `nome()` (linha XXX) ... **Texto exato:** ```texto```
    padrao = r'\*\*Função:\*\*\s+`([^`]+)`\s+\(linha\s+(\d+)\).*?**Arquivo deve ser extraído do contexto anterior**\n.*?\*\*Texto exato:\*\*\s*```\n(.*?)\n```'

    # Usar padrão mais simples
    linhas = secao_b.split('\n')

    mensagens = []
    i = 0

    while i < len(linhas):
        linha = linhas[i]

        # Procurar por linhas de arquivo (handlers\...)
        if 'handlers\\' in linha and '.py' in linha:
            arquivo = linha.strip().replace('### ', '')
            i += 1

            # Próxima deve ser a função
            while i < len(linhas) and linhas[i].strip() == '':
                i += 1

            if i < len(linhas) and '**Função:**' in linhas[i]:
                # Extrair função e linha
                funcao_linha = linhas[i]
                match_func = re.search(r'\*\*Função:\*\*\s+`([^`]+)`\s+\(linha\s+(\d+)\)', funcao_linha)

                if match_func:
                    funcao = match_func.group(1)
                    num_linha = match_func.group(2)

                    # Procurar texto exato
                    while i < len(linhas) and '**Texto exato:**' not in linhas[i]:
                        i += 1

                    if i < len(linhas):
                        i += 1  # Pular linha "**Texto exato:**"
                        i += 1  # Pular marcador ```

                        # Extrair texto até fechar com ```
                        texto_lines = []
                        while i < len(linhas) and '```' not in linhas[i]:
                            texto_lines.append(linhas[i])
                            i += 1

                        texto = '\n'.join(texto_lines).strip()

                        # Verificar se contém palavras-chave de confirmação
                        texto_lower = texto.lower()
                        if any(palavra in texto_lower for palavra in PALAVRAS_CHAVE):
                            # Encontrar contexto/momento (extrair de descrição anterior se houver)
                            momento = "Fluxo de " + " ".join(palavra.capitalize() for palavra in PALAVRAS_CHAVE if palavra in texto_lower)

                            mensagens.append({
                                'arquivo': arquivo,
                                'linha': num_linha,
                                'funcao': funcao,
                                'texto': texto,
                                'momento': momento
                            })

        i += 1

    return sorted(mensagens, key=lambda x: (x['arquivo'], int(x['linha'])))

def gerar_relatorio(mensagens):
    """Gera relatório de confirmações extraídas"""

    print("\n" + "="*100)
    print("MENSAGENS CATEGORIA B - CONFIRMAÇÕES EXTRAÍDAS")
    print("="*100 + "\n")

    if not mensagens:
        print("Nenhuma mensagem de confirmação encontrada")
        return

    print(f"Total de mensagens: {len(mensagens)}\n")

    # Criar tabela
    print("| # | Arquivo | Linha | Função | Texto | Momento |")
    print("|---|---------|-------|--------|-------|---------|")

    for idx, msg in enumerate(mensagens, 1):
        # Truncar texto para caber na tabela
        texto_curto = msg['texto'][:60].replace('\n', ' ').replace('`', '')
        if len(msg['texto']) > 60:
            texto_curto += "..."

        print(f"| {idx} | {msg['arquivo']} | {msg['linha']} | {msg['funcao']} | {texto_curto} | {msg['momento']} |")

    # Detalhe completo
    print("\n" + "="*100)
    print("DETALHE COMPLETO")
    print("="*100 + "\n")

    for idx, msg in enumerate(mensagens, 1):
        print(f"[CONFIRMAÇÃO-{idx:02d}]")
        print(f"  Arquivo: {msg['arquivo']}")
        print(f"  Linha: {msg['linha']}")
        print(f"  Função: {msg['funcao']}")
        print(f"  Momento: {msg['momento']}")
        print(f"  Texto atual:\n    \"{msg['texto']}\"")
        print()

def salvar_json(mensagens):
    """Salva resultado em JSON para processamento"""
    import json

    with open('CONFIRMACOES_CATEGORIA_B.json', 'w', encoding='utf-8') as f:
        json.dump(mensagens, f, ensure_ascii=False, indent=2)

    print(f"\nArquivo salvo: CONFIRMACOES_CATEGORIA_B.json")

if __name__ == '__main__':
    print("Extração de Mensagens Categoria B - Confirmações\n")

    mensagens = extrair_confirmacoes()

    if mensagens:
        gerar_relatorio(mensagens)
        salvar_json(mensagens)
    else:
        print("Nenhuma mensagem encontrada")
