#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ORQUESTRADOR DE AUDITORIA E GERAÇÃO DE PATCHES (MODO SEGURO)

⚠️  MODO SEGURO - NÃO APLICA PATCHES AUTOMATICAMENTE

Fluxo:
1. Recebe comando via argumento
2. Le arquivos relevantes baseado no comando
3. Usa Claude Haiku para analise inicial
4. Passa para auditoria_gpt (GPT-4o)
5. Loop de refinamento (max 3 rodadas) se CONDITIONAL
6. Se aprovado: GERA ARQUIVO .diff APENAS
7. Se rejeitado: para e exibe motivo
8. Se faltam evidências: retorna NEEDS_MORE_EVIDENCE
9. Salva historico em logs/orquestrador_{timestamp}.json

IMPORTANTE:
- Patches são APENAS GERADOS em formato .diff
- Aplicação manual OBRIGATÓRIA após revisão humana
- Nenhuma modificação automática de arquivos
- ANTHROPIC_API_KEY deve estar em .env (não é editada)

Uso:
    python orquestrador.py "investigue o bug de consulta pura"
    python orquestrador.py "revise o codigo de slots"
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# SETUP SEGURO
# ─────────────────────────────────────────────────────────────────────────────

print("[MODO SEGURO] Carregando configuracoes...\n")

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("[ERROR] ANTHROPIC_API_KEY nao configurada")
    print("[INSTRUCAO] Configure em .env:")
    print("  ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx")
    print("  Obter em: https://console.anthropic.com/keys")
    sys.exit(1)

try:
    from anthropic import Anthropic
except ImportError:
    print("[ERROR] Instale: pip install anthropic")
    print("[INFO] Ou: pip install -r requirements_orquestrador.txt")
    sys.exit(1)

try:
    from auditoria_gpt import auditar
except ImportError:
    print("[ERROR] auditoria_gpt.py nao encontrado")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# INICIALIZAR CLIENTE
# ─────────────────────────────────────────────────────────────────────────────

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs"
PATCHES_DIR = PROJECT_ROOT / "patches"
ROUTER_FILE = PROJECT_ROOT / "router" / "principal_router.py"
HANDLER_FILE = PROJECT_ROOT / "handlers" / "event_handler.py"
CONTEXTO_FILE = PROJECT_ROOT / "utils" / "contexto_temporario.py"

LOGS_DIR.mkdir(exist_ok=True)
PATCHES_DIR.mkdir(exist_ok=True)

print(f"[OK] Diretorios criados:")
print(f"     logs/    → {LOGS_DIR}")
print(f"     patches/ → {PATCHES_DIR}\n")

# ─────────────────────────────────────────────────────────────────────────────
# PROTECOES CONTRA AUTO-APLICACAO
# ─────────────────────────────────────────────────────────────────────────────

BLOQUEADO_FUNCOES = [
    "aplicar_patch",
    "auto_apply",
    "apply_patch",
    "aplicar_automaticamente",
    "auto_aplicar"
]

for funcao in dir():
    if any(bloqueado in funcao.lower() for bloqueado in BLOQUEADO_FUNCOES):
        raise RuntimeError(f"[BLOQUEADO] Funcao de auto-aplicacao detectada: {funcao}")

if "--apply" in sys.argv or "-a" in sys.argv:
    print("[ERRO] Flags --apply e -a estao bloqueadas em modo seguro")
    sys.exit(1)

print("[OK] Protecoes contra auto-aplicacao ativadas\n")

# ─────────────────────────────────────────────────────────────────────────────
# FUNCOES
# ─────────────────────────────────────────────────────────────────────────────

def ler_arquivo(caminho, limite=3000):
    """Le arquivo com limite de caracteres."""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read()
            if len(conteudo) > limite:
                return conteudo[:limite] + f"\n... [truncado, {len(conteudo)} chars total]"
            return conteudo
    except FileNotFoundError:
        return f"[Arquivo nao encontrado: {caminho}]"
    except Exception as e:
        return f"[Erro ao ler: {e}]"

def encontrar_arquivos_relevantes(comando):
    """Encontra arquivos relevantes baseado no comando."""
    arquivos = {}

    mapeamento = {
        "router": str(ROUTER_FILE),
        "handler": str(HANDLER_FILE),
        "contexto": str(CONTEXTO_FILE),
        "consulta": str(ROUTER_FILE),
        "auto-prof": str(ROUTER_FILE),
        "agendamento": str(ROUTER_FILE),
        "slots": str(ROUTER_FILE),
        "draft": str(ROUTER_FILE),
    }

    for palavra, arquivo in mapeamento.items():
        if palavra.lower() in comando.lower():
            arquivos[Path(arquivo).name] = ler_arquivo(arquivo)

    if not arquivos:
        arquivos["principal_router.py"] = ler_arquivo(str(ROUTER_FILE), 5000)

    return arquivos

def gerar_analise_inicial(comando, arquivos):
    """Usa Claude Haiku para gerar analise inicial."""

    contexto_arquivos = "\n".join(
        f"=== {nome} ===\n{conteudo}"
        for nome, conteudo in arquivos.items()
    )

    prompt = f"""
Voce e um auditor tecnico da NeoEve.

COMANDO: {comando}

ARQUIVOS RELEVANTES:
{contexto_arquivos}

---

Baseado no comando e nos arquivos, gere uma ANALISE INICIAL que:
1. Identifique a causa raiz suspeita
2. Liste o caminho do codigo envolvido
3. Destaque linhas criticas
4. Proponha uma hipotese de fix
5. Liste EVIDENCIAS NECESSARIAS:
   - Logs reais
   - Trechos de codigo
   - Testes obrigatorios
   - Stack trace (se houver)

Seja direto e tecnico.
"""

    print("\n[HAIKU] Gerando analise inicial...\n")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    analise = response.content[0].text
    print(analise)
    print()

    return analise

def chamar_auditoria_gpt(codigo, logs, hipotese):
    """Chama auditoria_gpt.auditar()."""
    print("[GPT-4O] Enviando para auditoria com GPT-4o...\n")

    resultado = auditar(
        codigo=codigo,
        logs=logs,
        hipotese=hipotese
    )

    print("[GPT-4O] Resposta recebida.\n")

    return resultado

def exibir_resultado(resultado):
    """Exibe resultado de forma legivel."""
    print("="*80)
    print("RESULTADO DA AUDITORIA")
    print("="*80 + "\n")

    for chave, valor in resultado.items():
        if chave == "aprovacao":
            status_map = {
                "YES": "[OK] APROVADO",
                "NO": "[ERRO] REJEITADO",
                "CONDITIONAL": "[AVISO] CONDICIONAL",
                "NEEDS_MORE_EVIDENCE": "[AVISO] FALTAM EVIDENCIAS"
            }
            print(f"{chave.upper()}: {status_map.get(valor, valor)}")
        else:
            print(f"{chave.upper()}:")
            if isinstance(valor, str):
                linhas = valor.split("\n")
                for linha in linhas[:20]:
                    print(f"  {linha}")
                if len(linhas) > 20:
                    print(f"  ... [{len(linhas) - 20} mais linhas]")
            else:
                print(f"  {valor}")
        print()

def refinar_analise(analise_anterior, resultado_gpt, rodada):
    """Refina analise baseado no feedback do GPT."""

    print(f"\n[REFINAMENTO RODADA {rodada}] Analisando feedback do GPT...\n")

    justificativa = resultado_gpt.get("justificativa", "")
    problema = resultado_gpt.get("diagnostico", "")

    prompt = f"""
Voce e um auditor tecnico refinando uma analise.

ANALISE ANTERIOR:
{analise_anterior}

FEEDBACK DO GPT-4O:
Aprovacao: {resultado_gpt.get('aprovacao')}
Diagnostico: {problema}
Justificativa: {justificativa}

---

Refine a analise para:
1. Responder aos pontos levantados
2. Fortalecer a evidencia do patch proposto
3. Abordar as regressoes possiveis mencionadas
4. EVIDENCIAS CONCRETAS (nao hipoteses)

Seja conciso e tecnico.
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

def gerar_arquivo_diff(patch_sugerido, timestamp):
    """GERA ARQUIVO .diff APENAS (sem aplicar)."""

    arquivo_patch = PATCHES_DIR / f"patch_{timestamp}.diff"

    conteudo_diff = f"""# PATCH SUGERIDO - {timestamp}
# MODO SEGURO: Aplicacao manual OBRIGATORIA
#
# Para aplicar este patch:
# 1. Revisar cuidadosamente
# 2. Executar: patch -p0 < {arquivo_patch.name}
# 3. Testar completamente

{patch_sugerido}
"""

    with open(arquivo_patch, "w", encoding="utf-8") as f:
        f.write(conteudo_diff)

    return arquivo_patch

def salvar_historico(historico, timestamp):
    """Salva historico em JSON."""
    arquivo = LOGS_DIR / f"orquestrador_{timestamp}.json"

    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Historico salvo: {arquivo}")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """Funcao principal (MODO SEGURO)."""

    if len(sys.argv) < 2:
        print("Uso: python orquestrador.py <comando>")
        print()
        print("Exemplos:")
        print("  python orquestrador.py \"investigue consulta pura\"")
        print("  python orquestrador.py \"revise auto-profissional\"")
        print()
        print("[MODO SEGURO] Nenhum patch e aplicado automaticamente")
        print("[MODO SEGURO] Apenas arquivos .diff sao gerados")
        sys.exit(1)

    comando = " ".join(sys.argv[1:])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "="*80)
    print("[MODO SEGURO] ORQUESTRADOR DE AUDITORIA")
    print("="*80)
    print(f"\nComando: {comando}")
    print(f"Timestamp: {timestamp}")
    print("[AVISO] Patches serão APENAS GERADOS, nunca aplicados automaticamente\n")

    # ETAPA 1: Encontrar arquivos

    print("[ETAPA 1] Encontrando arquivos relevantes...\n")

    arquivos = encontrar_arquivos_relevantes(comando)

    print(f"[OK] {len(arquivos)} arquivo(s) carregado(s):")
    for nome in arquivos.keys():
        print(f"   - {nome}")
    print()

    historico = [
        {
            "timestamp": timestamp,
            "comando": comando,
            "modo_seguro": True,
            "etapa": "1_arquivos",
            "arquivos_carregados": list(arquivos.keys())
        }
    ]

    # ETAPA 2: Analise inicial com Haiku

    print("[ETAPA 2] Gerando analise inicial com Claude Haiku...\n")

    analise_inicial = gerar_analise_inicial(comando, arquivos)

    historico.append({
        "etapa": "2_analise_haiku",
        "analise": analise_inicial
    })

    # ETAPA 3: Auditoria com GPT-4o (loop ate YES, NO ou NEEDS_MORE_EVIDENCE)

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
            print("[OK] APROVACAO CONCEDIDA!")
            break

        elif aprovacao == "NO":
            print("[ERRO] AUDITORIA REJEITOU O PATCH")
            print(f"Motivo: {resultado_gpt.get('justificativa', 'Nao especificado')}")

            historico.append({
                "etapa": "4_resultado_final",
                "status": "REJEITADO",
                "motivo": resultado_gpt.get('justificativa')
            })

            salvar_historico(historico, timestamp)
            print("\n[RESULTADO] Auditoria completada: REJEITADO")
            return

        elif aprovacao == "NEEDS_MORE_EVIDENCE":
            print("[AVISO] FALTAM EVIDENCIAS CONCRETAS")
            print(f"Solicita: {resultado_gpt.get('justificativa', 'Veja acima')}")

            historico.append({
                "etapa": "4_resultado_final",
                "status": "INCOMPLETO",
                "evidencias_faltantes": resultado_gpt.get('justificativa')
            })

            salvar_historico(historico, timestamp)
            print("\n[RESULTADO] Auditoria completada: EVIDENCIAS INSUFICIENTES")
            return

        elif aprovacao == "CONDITIONAL":
            if rodada_atual < max_rodadas:
                print("[AVISO] APROVACAO CONDICIONAL - Refinando analise...\n")

                analise = refinar_analise(analise, resultado_gpt, rodada_atual)

                historico.append({
                    "etapa": f"3_refinamento_r{rodada_atual}",
                    "analise_refinada": analise
                })
            else:
                print(f"[AVISO] Maximo de rodadas ({max_rodadas}) atingido com CONDITIONAL")
                print("   Considerando como incompleto.")

                historico.append({
                    "etapa": "4_resultado_final",
                    "status": "CONDICIONAL_MAX_RODADAS",
                    "rodadas": rodada_atual
                })

                salvar_historico(historico, timestamp)
                print("\n[RESULTADO] Auditoria completada: INCONCLUSIVO (max rodadas)")
                return
        else:
            print(f"[?] Aprovacao desconhecida: {aprovacao}")

    # ETAPA 4: Gerar arquivo .diff (NUNCA APLICAR)

    if resultado_gpt and resultado_gpt.get("aprovacao", "").upper() == "YES":
        print("\n[ETAPA 4] GERANDO ARQUIVO .diff\n")

        patch_sugerido = resultado_gpt.get("patch_minimo", "Nenhum patch sugerido")

        if "sem patch" not in patch_sugerido.lower():

            arquivo_patch = gerar_arquivo_diff(patch_sugerido, timestamp)

            print("[OK] ARQUIVO PATCH GERADO")
            print(f"    Arquivo: {arquivo_patch}")
            print(f"    Caminho: {arquivo_patch.absolute()}\n")

            print("[IMPORTANTE] Para aplicar este patch:")
            print("   1. REVISAR CUIDADOSAMENTE O ARQUIVO .diff")
            print("   2. TESTAR EM AMBIENTE DE DESENVOLVIMENTO")
            print("   3. Somente DEPOIS aplicar: patch -p0 < patch_*.diff")
            print()
            print("[AVISO] Nenhum arquivo sera modificado automaticamente")

            historico.append({
                "etapa": "4_resultado_final",
                "status": "PATCH_GERADO",
                "arquivo_patch": str(arquivo_patch),
                "patch_sugerido": patch_sugerido,
                "aplicacao": "MANUAL - OBRIGATORIA REVISAO HUMANA"
            })
        else:
            historico.append({
                "etapa": "4_resultado_final",
                "status": "APROVADO_SEM_PATCH",
                "observacao": "Nenhum patch necessario"
            })

    # ETAPA 5: Salvar historico

    salvar_historico(historico, timestamp)

    print("\n" + "="*80)
    print("[MODO SEGURO] ORQUESTRACAO COMPLETADA")
    print("="*80)
    print()
    print("[LEMBRETE] Aplicacao manual obrigatoria apos revisao humana")

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[AVISO] Interrompido pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
