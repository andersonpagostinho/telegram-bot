#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analisador de testes para Matriz de Migração Mock → Real
Clasifica cada teste por necessidade de realismo Firestore/E2E
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Mapeamento de testes com características
TESTES_ANALISE = {
    # ===== TESTES DE REGRESSÃO P0 (CRÍTICOS) =====
    "runner_regressao_p0_agendamento_critico.py": {
        "nome": "Regressão P0 - Agendamento Crítico",
        "objetivo": "16 testes de fluxo de agendamento (profissional incompatível, confirmação, etc)",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "ALTO - Mock não detecta conflitos reais de horário, sobrescritas, contaminação multi-tenant",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Conflito, confirmação pendente, sugestão são críticos"
    },

    "runner_stress_negativos_agendamento_p0.py": {
        "nome": "Stress P0 - Negativos de Agendamento",
        "objetivo": "Testa serviço inválido, profissional não encontrado, data inválida",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - Validações podem não refletir restrições reais de Firestore",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Serviço incompatível com profissional é crítico"
    },

    # ===== TESTES DE PERSISTÊNCIA REAL (JÁ IMPLEMENTADOS) =====
    "runner_p0_persistencia_real.py": {
        "nome": "P0 Persistência Real",
        "objetivo": "6 testes com Firestore real: agendamento, cancelamento, profissional, contexto",
        "fluxo": "P0",
        "usa_mock": False,
        "usa_firestore_real": True,
        "cria_evento_real": True,
        "salva_contexto_real": True,
        "risco": "NENHUM - 100% com dados reais",
        "classificacao": "C",
        "prioridade": "N/A",
        "motivo": "Já implementado com sucesso"
    },

    # ===== TESTES DE STRESS (MOCK) =====
    "runner_stress_confirmacao_agendamento.py": {
        "nome": "Stress - Confirmação de Agendamento",
        "objetivo": "Múltiplas confirmações em sequência",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - Não detecta race conditions reais",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Confirmação pendente é crítico"
    },

    "runner_stress_conflito_aceite_sugestao.py": {
        "nome": "Stress - Conflito + Sugestão",
        "objetivo": "Validar conflito de horário e sugestão de alternativas",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "ALTO - Conflito real depende de Firestore, mock não valida",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Sugestão de horário é crítica, precisa de conflito real"
    },

    "runner_stress_conflito_aceite_confirmacao_final.py": {
        "nome": "Stress - Conflito + Confirmação Final",
        "objetivo": "Conflito seguido de aceitar sugestão e confirmar",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "ALTO - Cascata de operações críticas com mock",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Conflito → Sugestão → Confirmação é fluxo crítico"
    },

    "runner_stress_confirmacao_pendente.py": {
        "nome": "Stress - Confirmação Pendente",
        "objetivo": "Múltiplas confirmações pendentes simultâneas",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "ALTO - Múltiplas transações sem Firestore real",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Multi-tenant + confirmação pendente precisa ser real"
    },

    "runner_stress_profissional_alternativo_completo.py": {
        "nome": "Stress - Profissional Alternativo",
        "objetivo": "Trocar profissional quando principal não atende",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - Troca de profissional precisa validar compatibilidade real",
        "classificacao": "B",
        "prioridade": "P0_REAL_2",
        "motivo": "Profissional incompatível é validado real"
    },

    "runner_stress_multi_entidades.py": {
        "nome": "Stress - Multi-entidades",
        "objetivo": "Múltiplos usuários/tenants simultâneos",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "CRÍTICO - Multi-tenant sem Firestore real pode contaminar",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Isolamento de tenant é crítico e deve ser testado real"
    },

    "runner_stress_multientidades_agendamento.py": {
        "nome": "Stress - Multi-entidades Agendamento",
        "objetivo": "Múltiplos tenants fazendo agendamentos",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "CRÍTICO - Contaminação multi-tenant com mock",
        "classificacao": "B",
        "prioridade": "P0_REAL_1",
        "motivo": "Multi-tenant em fluxo crítico"
    },

    "runner_stress_interrupcao_informativa_completo.py": {
        "nome": "Stress - Interrupção Informativa",
        "objetivo": "Pergunta informativa não deve limpar draft de agendamento",
        "fluxo": "P1",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - Contexto persistido pode ser perdido",
        "classificacao": "B",
        "prioridade": "P1_REAL",
        "motivo": "Preservação de contexto em P1"
    },

    "runner_stress_mudanca_contexto_fluxo_ativo.py": {
        "nome": "Stress - Mudança de Contexto em Fluxo Ativo",
        "objetivo": "Mudar contexto sem perder estado do fluxo",
        "fluxo": "P1",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - Mudança de contexto sem persistência real",
        "classificacao": "B",
        "prioridade": "P1_REAL",
        "motivo": "Contexto persistido em mudança"
    },

    "runner_stress_rajada_agendamento.py": {
        "nome": "Stress - Rajada de Agendamento",
        "objetivo": "Múltiplos agendamentos em sequência rápida",
        "fluxo": "P0",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "ALTO - Race conditions não detectadas",
        "classificacao": "B",
        "prioridade": "P0_REAL_2",
        "motivo": "Rajadas precisam de Firestore para detectar conflitos"
    },

    # ===== DRY RUN / AUDITORIA =====
    "runner_dry_run.py": {
        "nome": "Dry Run Principal",
        "objetivo": "Validação isolada de lógica determinística",
        "fluxo": "Todos",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "BAIXO - Apenas lógica determinística",
        "classificacao": "A",
        "prioridade": "N/A",
        "motivo": "Mock aceitável para lógica pura"
    },

    # ===== TESTES DE ONBOARDING =====
    "runner_onboarding_endereco_dono.py": {
        "nome": "Onboarding - Endereço do Dono",
        "objetivo": "Fluxo de coleta de endereço",
        "fluxo": "Setup",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "BAIXO - Setup não crítico para agendamento",
        "classificacao": "A",
        "prioridade": "N/A",
        "motivo": "Setup pode permanecer mockado"
    },

    # ===== TESTES P1 =====
    "test_clienteprofile_p1.py": {
        "nome": "P1 - ClienteProfile",
        "objetivo": "Validação de ClienteProfile",
        "fluxo": "P1",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - ClienteProfile com mock pode não refletir Firestore",
        "classificacao": "B",
        "prioridade": "P1_REAL",
        "motivo": "Leitura ClienteProfile deve ser real"
    },

    "test_p1_2a_leitura_clienteprofile.py": {
        "nome": "P1 - Leitura ClienteProfile 2A",
        "objetivo": "Segunda leitura de ClienteProfile",
        "fluxo": "P1",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "MÉDIO - ClienteProfile com mock",
        "classificacao": "B",
        "prioridade": "P1_REAL",
        "motivo": "Leitura ClienteProfile é crítica em P1"
    },

    # ===== DEBUG / DESENVOLVIMENTO =====
    "debug/teste_contexto_merge.py": {
        "nome": "Debug - Merge de Contexto",
        "objetivo": "Validar comportamento de merge em contexto",
        "fluxo": "Dev",
        "usa_mock": True,
        "usa_firestore_real": False,
        "cria_evento_real": False,
        "salva_contexto_real": False,
        "risco": "NENHUM - Debug local",
        "classificacao": "A",
        "prioridade": "N/A",
        "motivo": "Debug pode ficar como está"
    },
}

def gerar_matriz():
    """Gera matriz consolidada de migração."""

    # Análise rápida
    total = len(TESTES_ANALISE)
    mock_aceitavel = sum(1 for t in TESTES_ANALISE.values() if t["classificacao"] == "A")
    deve_virar_real = sum(1 for t in TESTES_ANALISE.values() if t["classificacao"] == "B")
    ja_real = sum(1 for t in TESTES_ANALISE.values() if t["classificacao"] == "C")
    e2e_candidatos = sum(1 for t in TESTES_ANALISE.values() if t["classificacao"] == "D")

    # Prioridades críticas
    p0_real_1 = [
        k for k, v in TESTES_ANALISE.items()
        if v.get("prioridade") == "P0_REAL_1"
    ]

    print(f"\n{'='*80}")
    print(f"MATRIZ DE MIGRACAO MOCK PARA REAL")
    print(f"{'='*80}\n")

    print(f"RESUMO EXECUTIVO:")
    print(f"  Total de testes analisados: {total}")
    print(f"  Mock aceitável (A): {mock_aceitavel}")
    print(f"  Deve virar real (B): {deve_virar_real}")
    print(f"  Já é real (C): {ja_real}")
    print(f"  E2E Telegram candidato (D): {e2e_candidatos}")
    print()

    print(f"TOP 10 MIGRAÇÕES CRÍTICAS (P0_REAL_1):")
    for i, teste in enumerate(p0_real_1[:10], 1):
        info = TESTES_ANALISE[teste]
        print(f"  {i}. {info['nome']}")
        print(f"     Risco: {info['risco']}")
    print()

    # Gerar tabela
    print(f"MATRIZ DETALHADA:")
    print(f"\n{'Arquivo':<50} {'Classificação':<15} {'Prioridade':<12}")
    print(f"{'-'*77}")

    for arquivo, info in sorted(TESTES_ANALISE.items()):
        classificacao = f"  {info['classificacao']}"  # A/B/C/D
        prioridade = info["prioridade"][:20] if len(info["prioridade"]) <= 20 else info["prioridade"][:17] + "..."
        print(f"{arquivo[:48]:<50} {classificacao:<15} {prioridade:<12}")

    return {
        "total": total,
        "mock_aceitavel": mock_aceitavel,
        "deve_virar_real": deve_virar_real,
        "ja_real": ja_real,
        "e2e_candidatos": e2e_candidatos,
        "p0_real_1_count": len(p0_real_1),
        "testes": TESTES_ANALISE
    }

if __name__ == "__main__":
    resultado = gerar_matriz()

    # Salvar JSON
    with open("tests/matriz_migracao_mock_real.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Matriz salva em: tests/matriz_migracao_mock_real.json")
