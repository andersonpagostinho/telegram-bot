"""
Scanner esttico de mensagens - NeoEve
Objetivo: Mapear todas as mensagens enviadas ao cliente
Sem alterar cdigo - apenas anlise esttica
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

# Padres a buscar
PATTERNS = [
    r'\.reply_text\(',
    r'\.send_message\(',
    r'\._send_and_stop\(',
    r'\._send_and_stop_ctx\(',
    r'resposta\s*=\s*["\']',
    r'mensagem\s*=\s*["\']',
    r'text\s*=\s*["\']',
    r'msg\s*=\s*["\']',
    r'resposta\s*\+=\s*["\']',
    r'msg\s*\+=\s*["\']',
]

DIRETRIOS = ['router', 'handlers', 'services', 'scheduler']

class MessageAuditor:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.mensagens = []
        self.arquivos_processados = 0
        self.linhas_analisadas = 0

    def categorizar_mensagem(self, texto: str, contexto: str) -> str:
        """Categoriza a mensagem baseado no contedo"""
        texto_lower = texto.lower()

        if any(w in texto_lower for w in ['agendar', 'agenda', 'servio', 'servico', 'qual']):
            return 'agendamento'
        elif any(w in texto_lower for w in ['conflito', 'existe um evento', 'horrio ocupado', 'horario ocupado', 'j existe']):
            return 'conflito'
        elif any(w in texto_lower for w in ['alternativa', 'alternativo', 'preferir', 'prefere', '']):
            return 'sugestao'
        elif any(w in texto_lower for w in ['confirma', 'tudo bem', 'perfeito', 'correto']):
            return 'confirmacao'
        elif any(w in texto_lower for w in ['cancelar', 'cancelamento', 'remover']):
            return 'cancelamento'
        elif any(w in texto_lower for w in ['reagendar', 'remarcar', 'mudar', 'alterar horario', 'alterar horrio']):
            return 'reagendamento'
        elif any(w in texto_lower for w in ['servios', 'servicos', 'disponvel', 'disponivel']):
            return 'consulta'
        elif any(w in texto_lower for w in ['profissional', 'profissionais', 'nome']):
            return 'consulta'
        elif any(w in texto_lower for w in ['preo', 'valor', 'tabela', 'custo', 'preco']):
            return 'consulta'
        elif any(w in texto_lower for w in ['admin', 'dono', 'bloqueio', 'configurar', 'usurio']):
            return 'admin'
        else:
            return 'desconhecido'

    def classificar_risco(self, mensagem: str, categoria: str) -> str:
        """Classifica risco operacional"""
        # A = no mexer (crtico para funcionamento)
        criticos = ['', '', 'erro', 'conflito', 'existe', 'horrio ocupado']
        if any(c in mensagem for c in criticos):
            return 'A'

        # C = reescrever (UX ruim)
        reescrever = ['?', 'qual opo', 'prefere', 'mltiplo']
        if any(r in mensagem.lower() for r in reescrever):
            return 'C'

        # B = pode humanizar
        return 'B'

    def extrair_mensagem(self, linha: str) -> str:
        """Extrai a mensagem string da linha"""
        # Tenta extrair string entre aspas
        match_simples = re.search(r'[=\+]\s*["\']([^"\']{10,150})["\']', linha)
        if match_simples:
            return match_simples.group(1)

        match_f = re.search(r'f["\']([^"\']{10,150})["\']', linha)
        if match_f:
            return match_f.group(1)

        # Se no encontrou, retorna preview da linha
        return linha.strip()[:100]

    def extrair_chamada(self, linha: str) -> str:
        """Extrai o tipo de chamada usada"""
        if 'reply_text' in linha:
            return 'reply_text()'
        elif 'send_message' in linha:
            return 'send_message()'
        elif '_send_and_stop_ctx' in linha:
            return '_send_and_stop_ctx()'
        elif '_send_and_stop' in linha:
            return '_send_and_stop()'
        elif '=' in linha:
            if 'resposta' in linha:
                return 'resposta ='
            elif 'mensagem' in linha:
                return 'mensagem ='
            elif 'text' in linha:
                return 'text ='
            elif 'msg' in linha:
                return 'msg ='
        return 'atribuio'

    def processar_arquivo(self, caminho_arquivo: str):
        """Processa um arquivo Python"""
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()

            funcao_atual = 'unknown'

            for num_linha, linha in enumerate(linhas, 1):
                self.linhas_analisadas += 1

                # Detecta funo atual
                if linha.strip().startswith('def ') or linha.strip().startswith('async def '):
                    match_func = re.search(r'def\s+(\w+)', linha)
                    if match_func:
                        funcao_atual = match_func.group(1)

                # Verifica padres
                for pattern in PATTERNS:
                    if re.search(pattern, linha):
                        mensagem_texto = self.extrair_mensagem(linha)
                        chamada = self.extrair_chamada(linha)
                        categoria = self.categorizar_mensagem(mensagem_texto, linha)
                        risco = self.classificar_risco(mensagem_texto, categoria)

                        # Caminho relativo
                        caminho_rel = os.path.relpath(caminho_arquivo, self.base_path)

                        self.mensagens.append({
                            'arquivo': caminho_rel,
                            'linha': num_linha,
                            'funcao': funcao_atual,
                            'trecho': mensagem_texto,
                            'chamada': chamada,
                            'categoria': categoria,
                            'classificacao': risco
                        })
                        break  # Uma match por linha  suficiente

        except Exception as e:
            print(f"  [AVISO] Erro ao processar {caminho_arquivo}: {e}")

    def varrer_diretorios(self):
        """Varre todos os diretrios Python"""
        print("Varrendo diretrios...")

        for dir_nome in DIRETRIOS:
            dir_path = os.path.join(self.base_path, dir_nome)
            if not os.path.isdir(dir_path):
                print(f"   Diretrio no encontrado: {dir_path}")
                continue

            print("  " + dir_nome + "/ ... ", end='', flush=True)

            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.py'):
                        arquivo_full = os.path.join(root, file)
                        self.processar_arquivo(arquivo_full)
                        self.arquivos_processados += 1

            print("[OK] (" + str(len([m for m in self.mensagens if dir_nome in m['arquivo']])) + " mensagens)")

    def gerar_markdown(self, caminho_saida: str):
        """Gera relatrio em Markdown"""
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write("# AUDITORIA DE MENSAGENS - NEOEVE\n\n")
            f.write(f"**Data:** {__import__('datetime').datetime.now().isoformat()}\n")
            f.write(f"**Total:** {len(self.mensagens)} mensagens encontradas\n")
            f.write(f"**Arquivos:** {self.arquivos_processados} Python files analisados\n")
            f.write(f"**Linhas:** {self.linhas_analisadas} linhas varridas\n\n")

            # Resumo por categoria
            f.write("## Resumo por Categoria\n\n")
            categorias = {}
            for msg in self.mensagens:
                cat = msg['categoria']
                categorias[cat] = categorias.get(cat, 0) + 1

            for cat in sorted(categorias.keys()):
                f.write(f"- **{cat}**: {categorias[cat]} mensagens\n")

            # Resumo por risco
            f.write("\n## Resumo por Classificao de Risco\n\n")
            riscos = {}
            for msg in self.mensagens:
                risco = msg['classificacao']
                riscos[risco] = riscos.get(risco, 0) + 1

            for risco in ['A', 'B', 'C']:
                if risco in riscos:
                    f.write(f"- **{risco}**: {riscos[risco]} mensagens\n")

            # Tabela detalhada
            f.write("\n## Tabela Detalhada\n\n")
            f.write("| ID | Arquivo | Linha | Funo | Categoria | Risco | Trecho |\n")
            f.write("|----|---------|----|---------|-----------|-------|--------|\n")

            for i, msg in enumerate(self.mensagens, 1):
                trecho = msg['trecho'][:60].replace('|', '\\|')
                f.write(f"| {i} | {msg['arquivo']} | {msg['linha']} | {msg['funcao']} | {msg['categoria']} | **{msg['classificacao']}** | {trecho}... |\n")

            # Detalhes por risco
            f.write("\n## Detalhes por Classificao de Risco\n\n")

            for risco_letra in ['A', 'B', 'C']:
                mensagens_risco = [m for m in self.mensagens if m['classificacao'] == risco_letra]
                if not mensagens_risco:
                    continue

                if risco_letra == 'A':
                    titulo = "**A - NO MEXER** (Crtico para funcionamento)"
                elif risco_letra == 'B':
                    titulo = "**B - Pode humanizar** (Melhorar tom sem quebrar lgica)"
                else:
                    titulo = "**C - Reescrever** (Redesign recomendado)"

                f.write(f"\n### {titulo}\n\n")

                for msg in mensagens_risco[:10]:  # Primeiras 10
                    f.write(f"- `{msg['arquivo']}:{msg['linha']}` em `{msg['funcao']}()`\n")
                    f.write(f"  - Chamada: `{msg['chamada']}`\n")
                    f.write(f"  - Categoria: `{msg['categoria']}`\n")
                    f.write(f"  - Texto: \"{msg['trecho']}\"\n\n")

                if len(mensagens_risco) > 10:
                    f.write(f"... e mais {len(mensagens_risco) - 10} mensagens de risco {risco_letra}\n\n")

        print(f" Markdown gerado: {caminho_saida}")

    def gerar_json(self, caminho_saida: str):
        """Gera relatrio em JSON"""
        relatorio = {
            'metadata': {
                'data': __import__('datetime').datetime.now().isoformat(),
                'total_mensagens': len(self.mensagens),
                'arquivos_analisados': self.arquivos_processados,
                'linhas_analisadas': self.linhas_analisadas
            },
            'mensagens': self.mensagens
        }

        with open(caminho_saida, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print(f" JSON gerado: {caminho_saida}")

    def executar(self):
        """Executa a auditoria completa"""
        print("\n" + "="*80)
        print("AUDITOR DE MENSAGENS - NEOEVE")
        print("="*80 + "\n")

        self.varrer_diretorios()

        print(f"\nResultados:")
        print(f"  Total de mensagens encontradas: {len(self.mensagens)}")
        print(f"  Arquivos processados: {self.arquivos_processados}")
        print(f"  Linhas analisadas: {self.linhas_analisadas}\n")

        # Gerar arquivos
        base_out = os.path.join(self.base_path, 'AUDITORIA_MENSAGENS_RAW')
        self.gerar_markdown(f"{base_out}.md")
        self.gerar_json(f"{base_out}.json")

        print("\n" + "="*80)
        print(" AUDITORIA COMPLETA")
        print("="*80 + "\n")


if __name__ == '__main__':
    # Diretrio base  o projeto
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    auditor = MessageAuditor(base)
    auditor.executar()
