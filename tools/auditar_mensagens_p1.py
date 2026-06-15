"""
Auditoria P1 - Mensagens com rastreamento de origem
Objetivo: Extrair strings literais reais e classificar por risco operacional
"""

import os
import re
from pathlib import Path
from typing import List, Dict

DIRETÓRIOS = ['router', 'handlers', 'services', 'scheduler']

class AuditoriaP1:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.mensagens_literais = []
        self.categorizacoes = {'A': [], 'B': [], 'C': []}

    def extrair_strings_literais(self, arquivo: str, conteudo: str) -> List[Dict]:
        """Extrai todas as strings literais do código"""
        mensagens = []
        linhas = conteudo.split('\n')

        # Padrões para encontrar strings literais entre aspas
        padrao_strings = [
            r'reply_text\s*\(\s*["\']([^"\']{10,})["\']',
            r'send_message\s*\([^,]*,\s*text\s*=\s*["\']([^"\']{10,})["\']',
            r'_send_and_stop\s*\(\s*["\']([^"\']{10,})["\']',
            r'resposta\s*=\s*["\']([^"\']{10,})["\'](?!\s*\+)',
            r'mensagem\s*=\s*["\']([^"\']{10,})["\']',
            r'msg\s*=\s*["\']([^"\']{10,})["\'](?!\s*\+)',
        ]

        for num_linha, linha in enumerate(linhas, 1):
            for pattern in padrao_strings:
                matches = re.finditer(pattern, linha)
                for match in matches:
                    texto = match.group(1)
                    if len(texto) >= 10:  # Mínimo de 10 caracteres
                        mensagens.append({
                            'arquivo': arquivo,
                            'linha': num_linha,
                            'texto': texto,
                            'linha_completa': linha.strip()
                        })

        return mensagens

    def extrair_funcao(self, linhas: List[str], num_linha: int) -> str:
        """Encontra a função que contém a linha"""
        for i in range(num_linha - 1, -1, -1):
            linha = linhas[i]
            if re.match(r'\s*(def|async def)\s+(\w+)', linha):
                match = re.search(r'(def|async def)\s+(\w+)', linha)
                if match:
                    return match.group(2)
        return 'unknown'

    def classificar_mensagem(self, texto: str, arquivo: str, funcao: str) -> str:
        """Classifica a mensagem em A, B ou C"""
        texto_lower = texto.lower()

        # CATEGORIA A - NÃO MEXER (crítico operacional)
        a_patterns = [
            'já existe um evento',
            'conflito',
            'horário ocupado',
            'horario ocupado',
            'disponibilidade',
            'alternativa',
            'alternativo',
            'não consegui',
            'nao consegui',
            'erro ao',
            'erro',
            'sugestão',
            'sugestao',
            'preferir outro',
            'horários alternativos',
            'horarios alternativos',
            'disponível',
            'disponivel',
            'conflito de',
        ]

        if any(p in texto_lower for p in a_patterns):
            return 'A'

        # CATEGORIA C - REESCREVER (robôtico/genérico)
        c_patterns = [
            'responda sim',
            'responda não',
            'responda nao',
            'opção inválida',
            'opcao invalida',
            'comando desconhecido',
            'não entendi',
            'nao entendi',
            'qual opção',
            'qual opcao',
            'número inválido',
            'numero invalido',
            'tente novamente',
            'tente de novo',
            'comando inválido',
            'comando invalido',
        ]

        if any(p in texto_lower for p in c_patterns):
            return 'C'

        # CATEGORIA B - PODE HUMANIZAR (coleta/confirmação)
        b_patterns = [
            'qual serviço',
            'qual servico',
            'qual profissional',
            'qual horário',
            'qual horario',
            'confirma',
            'tudo bem',
            'perfeito',
            'correto',
            'cancelamento',
            'reagendar',
            'remarcar',
            'mudar',
            'consulta',
            'como você',
            'como voce',
            'qual é',
            'qual eh',
        ]

        if any(p in texto_lower for p in b_patterns):
            return 'B'

        # Padrão: se tem emoji com informação estruturada, é B
        if any(emoji in texto for emoji in ['📅', '⏰', '👥', '💰', '📧', '📋']):
            return 'B'

        # Default: B (mensagens neutras de interação)
        return 'B'

    def processar_diretorios(self):
        """Processa todos os diretórios"""
        print("Processando diretórios para extrair strings literais...")

        for dir_nome in DIRETÓRIOS:
            dir_path = os.path.join(self.base_path, dir_nome)
            if not os.path.isdir(dir_path):
                continue

            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.py'):
                        arquivo_full = os.path.join(root, file)
                        arquivo_rel = os.path.relpath(arquivo_full, self.base_path)

                        try:
                            with open(arquivo_full, 'r', encoding='utf-8') as f:
                                conteudo = f.read()

                            strings = self.extrair_strings_literais(arquivo_rel, conteudo)
                            linhas = conteudo.split('\n')

                            for msg in strings:
                                funcao = self.extrair_funcao(linhas, msg['linha'])
                                classificacao = self.classificar_mensagem(msg['texto'], arquivo_rel, funcao)

                                self.mensagens_literais.append({
                                    'categoria': classificacao,
                                    'quantidade': 1,
                                    'arquivo': arquivo_rel,
                                    'funcao': funcao,
                                    'texto': msg['texto'],
                                    'linha': msg['linha'],
                                    'risco': self.descrever_risco(classificacao)
                                })

                                self.categorizacoes[classificacao].append({
                                    'arquivo': arquivo_rel,
                                    'funcao': funcao,
                                    'texto': msg['texto'],
                                    'linha': msg['linha']
                                })

                        except Exception as e:
                            pass

    def descrever_risco(self, categoria: str) -> str:
        """Descreve o risco operacional"""
        if categoria == 'A':
            return 'CRITICO - Não mexer, afeta fluxo operacional'
        elif categoria == 'B':
            return 'MEDIO - Pode humanizar sem quebrar lógica'
        else:
            return 'BAIXO - Deve reescrever para melhor UX'

    def gerar_markdown(self, caminho_saida: str):
        """Gera relatório em Markdown"""
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write("# AUDITORIA P1 - MENSAGENS COM RASTREAMENTO\n\n")
            f.write(f"**Data:** 2026-06-14\n")
            f.write(f"**Total de mensagens literais:** {len(self.mensagens_literais)}\n\n")

            # Resumo por categoria
            f.write("## Resumo por Categoria\n\n")
            f.write("| Categoria | Quantidade | Descrição |\n")
            f.write("|-----------|-----------|----------|\n")
            f.write(f"| A (Não mexer) | {len(self.categorizacoes['A'])} | Crítico operacional |\n")
            f.write(f"| B (Humanizar) | {len(self.categorizacoes['B'])} | Pode melhorar tom |\n")
            f.write(f"| C (Reescrever) | {len(self.categorizacoes['C'])} | Robôtico/Genérico |\n\n")

            # Detalhes por categoria
            for categoria in ['A', 'B', 'C']:
                if categoria == 'A':
                    titulo = "## A - NÃO MEXER (Crítico Operacional)"
                    desc = "Mensagens que afetam a lógica operacional e não devem ser alteradas"
                elif categoria == 'B':
                    titulo = "## B - HUMANIZAR (Pode Melhorar Ton)"
                    desc = "Mensagens de coleta/confirmação que podem ser humanizadas"
                else:
                    titulo = "## C - REESCREVER (Robôtico/Genérico)"
                    desc = "Mensagens excessivamente robóticas que devem ser reescritas"

                mensagens = self.categorizacoes[categoria]
                if not mensagens:
                    continue

                f.write(f"{titulo}\n\n")
                f.write(f"{desc}\n\n")
                f.write(f"**Total:** {len(mensagens)} mensagens\n\n")

                # Agrupar por arquivo
                por_arquivo = {}
                for msg in mensagens:
                    arquivo = msg['arquivo']
                    if arquivo not in por_arquivo:
                        por_arquivo[arquivo] = []
                    por_arquivo[arquivo].append(msg)

                for arquivo in sorted(por_arquivo.keys()):
                    f.write(f"### {arquivo}\n\n")

                    for msg in por_arquivo[arquivo]:
                        f.write(f"**Função:** `{msg['funcao']}()` (linha {msg['linha']})\n\n")
                        f.write(f"**Texto exato:**\n```\n{msg['texto']}\n```\n\n")
                        f.write(f"**Risco:** {self.descrever_risco(categoria)}\n\n")
                        f.write("---\n\n")

        print(f"Markdown gerado: {caminho_saida}")

    def executar(self):
        """Executa a auditoria completa"""
        print("\n" + "="*80)
        print("AUDITORIA P1 - MENSAGENS COM RASTREAMENTO DE ORIGEM")
        print("="*80 + "\n")

        self.processar_diretorios()

        print(f"\nResultados:")
        print(f"  Mensagens literais encontradas: {len(self.mensagens_literais)}")
        print(f"    - Categoria A: {len(self.categorizacoes['A'])}")
        print(f"    - Categoria B: {len(self.categorizacoes['B'])}")
        print(f"    - Categoria C: {len(self.categorizacoes['C'])}\n")

        # Gerar arquivo
        base_out = os.path.join(self.base_path, 'AUDITORIA_MENSAGENS_P1')
        self.gerar_markdown(f"{base_out}.md")

        print("\n" + "="*80)
        print("AUDITORIA P1 CONCLUIDA")
        print("="*80 + "\n")


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auditor = AuditoriaP1(base)
    auditor.executar()
