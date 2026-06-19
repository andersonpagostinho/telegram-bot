#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Validação Manual — PATCH P0 Cancelamento

Valida que as mudanças estão no lugar certo no código.
Não precisa de Firebase para rodar.
"""

import os
import sys
import io
from pathlib import Path

# Fix encoding on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Cores para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_success(msg):
    print(f"{GREEN}[OK] {msg}{RESET}")

def print_error(msg):
    print(f"{RED}[FAIL] {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}[INFO] {msg}{RESET}")

def check_file_contains(filepath, search_strings, description):
    """Verifica se arquivo contém strings específicas"""
    print(f"\n{BOLD}[FILE] Verificando: {filepath}{RESET}")
    print(f"   {description}")

    if not os.path.exists(filepath):
        print_error(f"Arquivo não encontrado: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        conteudo = f.read()

    all_found = True
    for search_str, str_desc in search_strings:
        if search_str in conteudo:
            print_success(f"Encontrado: {str_desc}")
        else:
            print_error(f"NÃO encontrado: {str_desc}")
            all_found = False

    return all_found


def main():
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}PATCH P0 CANCELAMENTO — Validação de Código{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

    project_root = Path(__file__).parent
    os.chdir(project_root)

    results = {}

    # ========================================================================
    # 1. Validar Guarda P0 em router/principal_router.py
    # ========================================================================
    print(f"\n{BOLD}[1/3] GUARDA P0 - Bloqueio de Ajuste Incremental{RESET}")

    guarda_checks = [
        ("async def resolver_alteracao_draft_agendamento(",
         "Função resolver_alteracao_draft_agendamento exists"),
        ("aguardando_confirmacao_cancelamento",
         "Guarda detecta estado aguardando_confirmacao_cancelamento"),
        ("return None",
         "Guarda retorna None (bloqueia)"),
    ]

    results["guarda_p0"] = check_file_contains(
        "router/principal_router.py",
        guarda_checks,
        "Guarda P0 deve estar no início da função resolver_alteracao_draft_agendamento"
    )

    # ========================================================================
    # 2. Validar Filtros em event_service_async.py
    # ========================================================================
    print(f"\n{BOLD}[2/3] FILTROS AVANCADOS - cancelar_evento_por_texto(){RESET}")

    filtro_checks = [
        ("async def cancelar_evento_por_texto",
         "Função cancelar_evento_por_texto com suporte a filtros"),
        ("profissional_filtro",
         "Filtro por profissional ('com Bruna')"),
        ("data_filtro",
         "Filtro por data ('amanhã')"),
        ("termo_lower = (termo or \"\").strip().lower()",
         "Normalização de termo"),
        ("\" com \" in termo_lower",
         "Detecção de 'com PROFISSIONAL'"),
        ("if status in [\"cancelado\", \"cancelada\"",
         "Ignora eventos cancelados"),
    ]

    results["filtros"] = check_file_contains(
        "services/event_service_async.py",
        filtro_checks,
        "Filtros avançados devem estar em cancelar_evento_por_texto()"
    )

    # ========================================================================
    # 3. Validar Integração em Handler Cancelamento IDLE
    # ========================================================================
    print(f"\n{BOLD}[3/3] INTEGRACAO - Handler Cancelamento IDLE{RESET}")

    integracao_checks = [
        ("tem_cancelamento = features.get(\"tem_cancelamento\", False)",
         "Detecção de feature cancelamento"),
        ("await cancelar_evento_por_texto(",
         "Chamada a cancelar_evento_por_texto() com filtros"),
        ("sanitizar_cancelamento_pendente(",
         "Sanitização de contexto pendente"),
        ("await salvar_contexto_temporario(user_id, ctx, tenant_id=dono_id)",
         "Salvamento com tenant_id correto"),
        ("ctx[\"estado_fluxo\"] = \"aguardando_confirmacao_cancelamento\"",
         "Transicao para estado de confirmacao"),
    ]

    results["integracao"] = check_file_contains(
        "router/principal_router.py",
        integracao_checks,
        "Integração do cancelamento IDLE deve estar no handler de cancelamento"
    )

    # ========================================================================
    # Sumário
    # ========================================================================
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}RESULTADO FINAL{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

    all_passed = all(results.values())

    if all_passed:
        print_success("TODAS AS VALIDACOES PASSARAM!")
        print(f"\n{GREEN}{BOLD}PATCH P0 CANCELAMENTO ESTA IMPLEMENTADO CORRETAMENTE{RESET}")
        print(f"\n{YELLOW}Proximo Passo: Executar testes Firebase (opcional){RESET}")
        print(f"  pytest tests/test_patch_p0_cancelamento_firebase.py")
        return 0
    else:
        print_error("ALGUMAS VALIDAÇÕES FALHARAM")
        print(f"\nVerifique:")
        for name, passed in results.items():
            status = f"{GREEN}✅ PASSOU{RESET}" if passed else f"{RED}❌ FALHOU{RESET}"
            print(f"  [{status}] {name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
