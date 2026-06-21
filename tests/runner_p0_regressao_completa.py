"""
Runner Agregado P0 — Regressão Completa
Executa todas as 9 baterias P0 certificadas em sequência
Total esperado: 174/174 PASS

Baterias:
1. p0_bateria_real_fluxo_completo_conflito_a_criacao.py — 7
2. p0_bateria_real_cancelamento_completo.py — 15
3. p0_real_confirmacao_pendente_completo.py — 17
4. p0_real_mudanca_contexto_completo.py — 25
5. p0_real_multi_entidades_completo.py — 15
6. p0_real_ajuste_incremental_avancado.py — 20
7. p0_real_notificacoes_e2e.py — 20
8. p0_real_admin_dono_completo.py — 25
9. p0_real_profissional_completo.py — 30
"""

import sys
import os
import json
import subprocess
from datetime import datetime
import pytz

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Baterias certificadas (nome arquivo, cenários esperados, nome JSON resultado esperado)
BATERIAS_P0 = [
    ("p0_bateria_real_fluxo_completo_conflito_a_criacao.py", 7, "resultado_bateria_p0_fluxo.json"),
    ("p0_bateria_real_cancelamento_completo.py", 15, "resultado_p0_cancelamento_completo.json"),
    ("p0_real_confirmacao_pendente_completo.py", 17, "resultado_p0_confirmacao_pendente.json"),
    ("p0_real_mudanca_contexto_completo.py", 25, "resultado_p0_mudanca_contexto.json"),
    ("p0_real_multi_entidades_completo.py", 15, "resultado_p0_multi_entidades.json"),
    ("p0_real_ajuste_incremental_avancado.py", 20, "resultado_p0_ajuste_incremental.json"),
    ("p0_real_notificacoes_e2e.py", 20, "resultado_p0_notificacoes_e2e.json"),
    ("p0_real_admin_dono_completo.py", 25, "resultado_p0_admin_dono.json"),
    ("p0_real_profissional_completo.py", 30, "resultado_p0_profissional.json"),
]

TOTAL_CENARIOS_ESPERADOS = sum(cenarios for _, cenarios, _ in BATERIAS_P0)


def print_header():
    print("=" * 80)
    print("REGRESSÃO COMPLETA P0 — 174/174 PASS ESPERADOS")
    print("=" * 80)
    print()


def print_bateria_header(numero, nome, esperados):
    print(f"[BATERIA {numero}] {nome}")
    print(f"           Cenários esperados: {esperados}")
    print()


def verificar_bateria_existe(nome):
    """Verifica se arquivo da bateria existe."""
    path = os.path.join(os.path.dirname(__file__), nome)
    return os.path.exists(path)


def executar_bateria(nome):
    """Executa uma bateria e retorna resultado."""
    path = os.path.join(os.path.dirname(__file__), nome)

    try:
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos por bateria
        )

        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "executada": True
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": 124,
            "stdout": "",
            "stderr": "TIMEOUT: Bateria demorou mais de 5 minutos",
            "executada": False
        }
    except Exception as e:
        return {
            "exit_code": 255,
            "stdout": "",
            "stderr": str(e),
            "executada": False
        }


def extrair_resultado_json(json_path):
    """Tenta extrair resultado de arquivo JSON."""
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Padrões esperados em JSON (múltiplas variações)
            if "passed" in data and "total" in data:
                return (data["passed"], data["total"])
            elif "passou" in data and "total" in data:
                return (data["passou"], data["total"])
            elif "cenarios_passou" in data and "total_cenarios" in data:
                return (data["cenarios_passou"], data["total_cenarios"])
            elif "passadas" in data and "total" in data:
                return (data["passadas"], data["total"])
            elif "passou" in data and isinstance(data["passou"], int):
                # Se apenas "passou" está presente, asumir que é total igual ao campo
                total = data.get("total", data.get("total_cenarios", data["passou"]))
                return (data["passou"], total)
    except Exception:
        pass

    return None


def extrair_resultado_stdout(stdout):
    """Extrai resultado de uma bateria do output (stdout)."""
    import re

    # Padrões possíveis (em ordem de prioridade)
    patterns = [
        # "Passaram: 7/7"
        (r'Passaram\s*:\s*(\d+)\s*/\s*(\d+)', True),
        # "Passou: X/Y" (sem "ram", variação)
        (r'Passou\s*:\s*(\d+)\s*/\s*(\d+)', True),
        # "RESULTADO FINAL: 30/30 PASSOU"
        (r'RESULTADO\s+FINAL\s*:\s*(\d+)\s*/\s*(\d+)\s*PASSOU', True),
        # "X/Y PASSED" ou "X/Y PASS"
        (r'(\d+)\s*/\s*(\d+)\s*(?:PASSED|PASS)', False),
        # "X/Y passed"
        (r'(\d+)\s*/\s*(\d+)\s*passed', False),
        # "Cenários executados: X/Y" + "Passou: X"
        (r'Cenários\s+executados\s*:\s*(\d+)\s*/\s*(\d+)', False),
        # "X/Y cenários passaram"
        (r'(\d+)\s*/\s*(\d+)\s*cenários\s+passaram', False),
        # "X cenários de Y passaram"
        (r'(\d+)\s+cenários?\s+de\s+(\d+)\s+passaram', False),
    ]

    for pattern, is_exact in patterns:
        if is_exact:
            # Buscar padrão exato (mais rigoroso)
            match = re.search(pattern, stdout, re.IGNORECASE)
        else:
            # Buscar padrão flexível
            match = re.search(pattern, stdout, re.IGNORECASE)

        if match:
            try:
                passed = int(match.group(1))
                total = int(match.group(2))
                return (passed, total)
            except (ValueError, IndexError):
                continue

    return None


def extrair_resultado_bateria(stdout, json_path=None):
    """
    Extrai resultado de uma bateria (ordem de extração A→B→C→D).

    A) Tentar JSON
    B) Parsear stdout
    C) Se exit_code == 0 e stdout contém marcador, aceitar PASS
    D) Se exit_code != 0, FAIL sempre (já tratado no main)
    """
    # Ordem A: Tentar JSON
    if json_path:
        resultado_json = extrair_resultado_json(json_path)
        if resultado_json:
            return resultado_json

    # Ordem B: Parsear stdout
    resultado_stdout = extrair_resultado_stdout(stdout)
    if resultado_stdout:
        return resultado_stdout

    # Se nada foi encontrado
    return None


def main():
    print_header()

    # Fase 1: Verificar se todas as baterias existem
    print("[FASE 1] Verificando existência de baterias...")
    print()

    baterias_existentes = []
    baterias_faltando = []

    for numero, (nome, esperados, json_resultado) in enumerate(BATERIAS_P0, 1):
        if verificar_bateria_existe(nome):
            print(f"  [OK] Bateria {numero}: {nome}")
            baterias_existentes.append((numero, nome, esperados, json_resultado))
        else:
            print(f"  [ERRO] Bateria {numero} NÃO ENCONTRADA: {nome}")
            baterias_faltando.append((numero, nome))

    print()

    if baterias_faltando:
        print("[ERRO] Baterias certificadas faltando:")
        for numero, nome in baterias_faltando:
            print(f"       {numero}. {nome}")
        print()
        print("[RESULTADO] FAIL — Baterias faltando")
        return False

    print(f"[OK] Todas as {len(baterias_existentes)} baterias encontradas")
    print()

    # Fase 2: Executar cada bateria
    print("[FASE 2] Executando baterias em sequência...")
    print()

    resultados = []
    total_cenarios_passados = 0

    for numero, nome, esperados, json_resultado in baterias_existentes:
        print_bateria_header(numero, nome, esperados)

        resultado = executar_bateria(nome)

        # Construir path do JSON de resultado
        json_path = os.path.join(os.path.dirname(__file__), json_resultado)

        if resultado["exit_code"] != 0:
            print(f"  [ERRO] Exit code: {resultado['exit_code']}")
            if resultado["stderr"]:
                stderr_lines = resultado["stderr"].split('\n')[:3]
                for line in stderr_lines:
                    if line.strip():
                        print(f"         {line}")
            resultado_bateria = {
                "numero": numero,
                "nome": nome,
                "esperados": esperados,
                "passados": 0,
                "status": "FALHA",
                "exit_code": resultado["exit_code"]
            }
        else:
            # Extrair resultado (Ordem: JSON → stdout)
            resultado_extraido = extrair_resultado_bateria(resultado["stdout"], json_path)

            if resultado_extraido:
                passados, total = resultado_extraido

                # Validar se resultado corresponde ao esperado
                if passados == esperados and passados == total:
                    print(f"  [OK] {passados}/{total} cenários passaram")
                    status = "PASS"
                    total_cenarios_passados += passados
                else:
                    print(f"  [AVISO] {passados}/{total} cenários passaram (esperado {esperados})")
                    status = "FALHA"

                resultado_bateria = {
                    "numero": numero,
                    "nome": nome,
                    "esperados": esperados,
                    "passados": passados,
                    "total": total,
                    "status": status,
                    "exit_code": resultado["exit_code"]
                }
            else:
                # Ordem C: Se exit_code == 0 e stdout contém marcador, aceitar como PASS?
                # Neste caso, vamos marcar como INDETERMINADO e requerer resultado claro
                print(f"  [AVISO] Não conseguiu extrair resultado do output")
                print(f"         Procurado em: {json_resultado}")

                resultado_bateria = {
                    "numero": numero,
                    "nome": nome,
                    "esperados": esperados,
                    "passados": 0,
                    "status": "INDETERMINADO",
                    "exit_code": resultado["exit_code"],
                    "nota": "Resultado não extraído"
                }

        resultados.append(resultado_bateria)
        print()

    # Fase 3: Gerar relatório consolidado
    print("[FASE 3] Gerando relatório consolidado...")
    print()

    resultado_consolidado = {
        "data": datetime.now(pytz.UTC).isoformat(),
        "total_baterias": len(baterias_existentes),
        "total_cenarios_esperados": TOTAL_CENARIOS_ESPERADOS,
        "total_cenarios_passados": total_cenarios_passados,
        "baterias": resultados,
        "status_final": "PASS" if total_cenarios_passados == TOTAL_CENARIOS_ESPERADOS else "FAIL"
    }

    # Salvar resultado em JSON
    resultado_json_path = os.path.join(os.path.dirname(__file__), "resultado_p0_regressao_completa.json")
    with open(resultado_json_path, 'w') as f:
        json.dump(resultado_consolidado, f, indent=2)

    print(f"[OK] Resultado salvo em: resultado_p0_regressao_completa.json")
    print()

    # Resumo final
    print("=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print()
    print(f"Total de baterias:      {len(baterias_existentes)}/9")
    print(f"Total de cenários:      {total_cenarios_passados}/{TOTAL_CENARIOS_ESPERADOS}")
    print()

    for resultado in resultados:
        status_icon = "[OK]" if resultado["status"] == "PASS" else "[ERRO]"
        print(f"{status_icon} {resultado['numero']:2}. {resultado['nome']:50} — {resultado.get('passados', 0):3}/{resultado['esperados']:3}")

    print()
    print("=" * 80)

    if resultado_consolidado["status_final"] == "PASS":
        print(f"[SUCESSO] REGRESSÃO COMPLETA: {total_cenarios_passados}/{TOTAL_CENARIOS_ESPERADOS} PASS")
        print("=" * 80)
        return True
    else:
        print(f"[FALHA] REGRESSÃO INCOMPLETA: {total_cenarios_passados}/{TOTAL_CENARIOS_ESPERADOS} PASS")
        print("=" * 80)
        return False


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
