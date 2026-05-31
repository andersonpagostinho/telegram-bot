#!/usr/bin/env python3
"""
ORQUESTRADOR DE AUDITORIA E PATCHES

Fluxo:
1. Recebe comando via argumento
2. Lê arquivos relevantes baseado no comando
3. Usa Claude Haiku para gerar análise inicial
4. Passa para auditoria_gpt (GPT-4o)
5. Loop de refinamento (máx 3 rodadas) se CONDITIONAL
6. Aplica patch se YES
7. Para se NO
8. Salva histórico em logs/orquestrador_{timestamp}.json

Uso:
    python orquestrador.py "investigue o bug de consulta pura"
    python orquestrador.py "revise o código de slots"
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────

# Carregar .env
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("❌ ANTHROPIC_API_KEY não encontrada em .env")
    sys.exit(1)

# Importar Anthropic SDK
try:
    from anthropic import Anthropic
except ImportError:
    print("❌ Instale: pip install anthropic")
    sys.exit(1)

# Importar auditoria_gpt
try:
    from auditoria_gpt import auditar
except ImportError:
    print("❌ auditoria_gpt.py não encontrado")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZAR CLIENTE ANTHROPIC
# ─────────────────────────────────────────────────────────────────────────────

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs"
ROUTER_FILE = PROJECT_ROOT / "router" / "principal_router.py"
HANDLER_FILE = PROJECT_ROOT / "handlers" / "event_handler.py"
CONTEXTO_FILE = PROJECT_ROOT / "utils" / "contexto_temporario.py"

LOGS_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES
# ─────────────────────────────────────────────────────────────────────────────

def ler_arquivo(caminho: str, limite: int = 3000) -> str:
    """Lê arquivo com limite de caracteres."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
            if len(conteudo) > limite:
                return conteudo[:limite] + f"\n... [conteúdo truncado, {len(conteudo)} chars total]"
            return conteudo
    except FileNotFoundError:
        return f"[Arquivo não encontrado: {caminho}]"
    except Exception as e:
        return f"[Erro ao ler: {e}]"

def encontrar_arquivos_relevantes(comando: str) -> dict:
    """Encontra arquivos relevantes baseado no comando."""
    arquivos = {}

    # Mapear palavras-chave para arquivos
    mapeamento = {
        "router": str(ROUTER_FILE),
        "handler": str(HANDLER_FILE),
        "contexto": str(CONTEXTO_FILE),
        "consulta": str(ROUTER_FILE),  # Bugs de consulta estão no router
        "auto-prof": str(ROUTER_FILE),
        "agendamento": str(ROUTER_FILE),
        "slots": str(ROUTER_FILE),
        "draft": str(ROUTER_FILE),
    }

    # Buscar arquivos por palavra-chave
    for palavra, arquivo in mapeamento.items():
        if palavra.lower() in comando.lower():
            arquivos[Path(arquivo).name] = ler_arquivo(arquivo)

    # Se não encontrou nada, pegar arquivos principais
    if not arquivos:
        arquivos["principal_router.py"] = ler_arquivo(str(ROUTER_FILE), 5000)

    return arquivos

def gerar_analise_inicial(comando: str, arquivos: dict) -> str:
    """Usa Claude Haiku para gerar análise inicial."""

    contexto_arquivos = "\n".join(
        f"=== {nome} ===\n{conteudo}"
        for nome, conteudo in arquivos.items()
    )

    prompt = f"""
Você é um auditor técnico da NeoEve.

COMANDO: {comando}

ARQUIVOS RELEVANTES:
{contexto_arquivos}

---

Baseado no comando e nos arquivos, gere uma ANÁLISE INICIAL que:
1. Identifique a causa raiz suspeita
2. Liste o caminho do código envolvido
3. Destaque linhas críticas
4. Proponha uma hipótese de fix

Seja direto e técnico.
"""

    print("\n[HAIKU] Gerando análise inicial...\n")

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    analise = response.content[0].text
    print(analise)
    print()

    return analise

def chamar_auditoria_gpt(codigo: str, logs: str, hipotese: str) -> dict:
    """Chama auditoria_gpt.auditar()."""
    print("[GPT-4O] Enviando para auditoria com GPT-4o...\n")

    resultado = auditar(
        codigo=codigo,
        logs=logs,
        hipotese=hipotese
    )

    print("[GPT-4O] Resposta recebida.\n")

    return resultado

def exibir_resultado(resultado: dict):
    """Exibe resultado de forma legível."""
    print("="*80)
    print("RESULTADO DA AUDITORIA")
    print("="*80 + "\n")

    for chave, valor in resultado.items():
        if chave == "aprovacao":
            status_map = {
                "YES": "✅ APROVADO",
                "NO": "❌ REJEITADO",
                "CONDITIONAL": "⚠️  CONDICIONAL"
            }
            print(f"{chave.upper()}: {status_map.get(valor, valor)}")
        else:
            print(f"{chave.upper()}:")
            if isinstance(valor, str):
                # Truncar linhas muito longas
                linhas = valor.split("\n")
                for linha in linhas[:20]:
                    print(f"  {linha}")
                if len(linhas) > 20:
                    print(f"  ... [{len(linhas) - 20} mais linhas]")
            else:
                print(f"  {valor}")
        print()

def refinar_analise(analise_anterior: str, resultado_gpt: dict, rodada: int) -> str:
    """Refina análise baseado no feedback do GPT."""

    print(f"\n[REFINAMENTO RODADA {rodada}] Analisando feedback do GPT...\n")

    justificativa = resultado_gpt.get("justificativa", "")
    problema = resultado_gpt.get("diagnóstico", "")

    prompt = f"""
Você é um auditor técnico refinando uma análise.

ANÁLISE ANTERIOR:
{analise_anterior}

FEEDBACK DO GPT-4O:
Aprovação: {resultado_gpt.get('aprovacao')}
Diagnóstico: {problema}
Justificativa: {justificativa}

---

Refine a análise para:
1. Responder aos pontos levantados
2. Fortalecer o patch proposto
3. Abordar as regressões possíveis mencionadas

Seja conciso e técnico.
"""

    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    analise_refinada = response.content[0].text
    print(analise_refinada)
    print()

    return analise_refinada

def salvar_historico(historico: list, timestamp: str):
    """Salva histórico em JSON."""
    arquivo = LOGS_DIR / f"orquestrador_{timestamp}.json"

    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Histórico salvo: {arquivo}")

def aplicar_patch(patch_sugerido: str) -> bool:
    """Tenta aplicar patch (interativo)."""
    print("\n" + "="*80)
    print("PATCH SUGERIDO")
    print("="*80 + "\n")
    print(patch_sugerido)
    print()

    resposta = input("Deseja aplicar este patch? (s/n): ").strip().lower()

    if resposta == "s":
        print("\n⚠️  Aplicação de patches requer aprovação manual")
        print("   Copie o patch acima e aplique com ferramentas apropriadas.")
        return True
    else:
        print("\n❌ Patch não aplicado.")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Função principal."""

    if len(sys.argv) < 2:
        print("Uso: python orquestrador.py <comando>")
        print()
        print("Exemplos:")
        print("  python orquestrador.py \"investigue consulta pura\"")
        print("  python orquestrador.py \"revise auto-profissional\"")
        print("  python orquestrador.py \"audit slots\"")
        sys.exit(1)

    comando = " ".join(sys.argv[1:])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "█"*80)
    print("ORQUESTRADOR DE AUDITORIA")
    print("█"*80)
    print(f"\nComando: {comando}")
    print(f"Timestamp: {timestamp}\n")

    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 1: Encontrar arquivos relevantes
    # ─────────────────────────────────────────────────────────────────────────

    print("[ETAPA 1] Encontrando arquivos relevantes...\n")

    arquivos = encontrar_arquivos_relevantes(comando)

    print(f"✅ {len(arquivos)} arquivo(s) carregado(s):")
    for nome in arquivos.keys():
        print(f"   - {nome}")
    print()

    historico = [
        {
            "timestamp": timestamp,
            "comando": comando,
            "etapa": "1_arquivos",
            "arquivos_carregados": list(arquivos.keys())
        }
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 2: Análise inicial com Haiku
    # ─────────────────────────────────────────────────────────────────────────

    print("[ETAPA 2] Gerando análise inicial com Claude Haiku...\n")

    analise_inicial = gerar_analise_inicial(comando, arquivos)

    historico.append({
        "etapa": "2_analise_haiku",
        "analise": analise_inicial
    })

    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 3: Auditoria com GPT-4o (loop até YES ou NO)
    # ─────────────────────────────────────────────────────────────────────────

    rodada_atual = 0
    max_rodadas = 3
    resultado_gpt = None
    analise = analise_inicial

    while rodada_atual < max_rodadas:
        rodada_atual += 1

        print(f"[ETAPA 3.{rodada_atual}] Auditoria com GPT-4o (rodada {rodada_atual}/{max_rodadas})...\n")

        resultado_gpt = chamar_auditoria_gpt(
            codigo="\n".join(arquivos.values()),
            logs="",
            hipotese=analise
        )

        exibir_resultado(resultado_gpt)

        historico.append({
            "etapa": f"3_auditoria_gpt_r{rodada_atual}",
            "resultado": resultado_gpt
        })

        aprovacao = resultado_gpt.get("aprovacao", "").upper()

        if aprovacao == "YES":
            print("✅ APROVAÇÃO CONCEDIDA!")
            break
        elif aprovacao == "NO":
            print("❌ AUDITORIA REJEITOU O PATCH")
            print(f"Motivo: {resultado_gpt.get('justificativa', 'Não especificado')}")

            historico.append({
                "etapa": "4_resultado_final",
                "status": "REJEITADO",
                "motivo": resultado_gpt.get('justificativa')
            })

            salvar_historico(historico, timestamp)
            print("\n❌ Auditoria completada: REJEITADO")
            return

        elif aprovacao == "CONDITIONAL":
            if rodada_atual < max_rodadas:
                print("⚠️  APROVAÇÃO CONDICIONAL - Refinando análise...\n")

                analise = refinar_analise(analise, resultado_gpt, rodada_atual)

                historico.append({
                    "etapa": f"3_refinamento_r{rodada_atual}",
                    "analise_refinada": analise
                })
            else:
                print(f"⚠️  Máximo de rodadas ({max_rodadas}) atingido com CONDITIONAL")
                print("   Considerando como rejeitado por cautela.")

                historico.append({
                    "etapa": "4_resultado_final",
                    "status": "CONDICIONAL_MAX_RODADAS",
                    "rodadas": rodada_atual
                })

                salvar_historico(historico, timestamp)
                print("\n⚠️  Auditoria completada: CONDICIONAL (máximo de rodadas)")
                return
        else:
            print(f"❓ Aprovação desconhecida: {aprovacao}")

    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 4: Aplicação de patch (se aprovado)
    # ─────────────────────────────────────────────────────────────────────────

    if resultado_gpt and resultado_gpt.get("aprovacao", "").upper() == "YES":
        print("\n[ETAPA 4] Patch foi aprovado!\n")

        patch_sugerido = resultado_gpt.get("patch_mínimo", "Nenhum patch sugerido")

        if "sem patch" not in patch_sugerido.lower():
            aplicar_patch(patch_sugerido)

        historico.append({
            "etapa": "4_resultado_final",
            "status": "APROVADO",
            "patch_sugerido": patch_sugerido
        })

    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 5: Salvar histórico
    # ─────────────────────────────────────────────────────────────────────────

    salvar_historico(historico, timestamp)

    print("\n" + "█"*80)
    print("ORQUESTRAÇÃO COMPLETADA")
    print("█"*80)

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
