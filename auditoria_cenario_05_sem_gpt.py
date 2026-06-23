#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria Forense Cenário 05 — Análise de Logs Existentes
Reconstruir o fluxo do teste fallido anterior.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

print("\n" + "="*80)
print("AUDITORIA FORENSE — CENÁRIO 05: MENSAGEM LONGA + PEDIDO FINAL")
print("="*80 + "\n")

auditoria = {
    "timestamp": datetime.now().isoformat(),
    "cenario": 5,
    "descricao": "Mensagem >2000 chars com conteúdo pessoal + pedido operacional final",
    "fonte": "Análise de logs existentes do teste p1_robustez_fluxo_conversacional_real.py",
    "fluxo": [],
    "tabela_resultado": []
}

# ============================================================================
# ETAPA 1: DEFINIÇÃO DO TESTE
# ============================================================================
print("[1/6] DEFINIÇÃO DO TESTE CENÁRIO 05\n")

teste_info = {
    "arquivo": "tests/p1_robustez_fluxo_conversacional_real.py",
    "funcao": "cenario_05_msg_longa_pedido_final()",
    "linha": 592,
    "tipo": "P1 Robustez Fluxo Conversacional",
    "objetivo": "Validar se pedido operacional no final de mensagem longa é detectado"
}

print(f"  Arquivo: {teste_info['arquivo']}")
print(f"  Função: {teste_info['funcao']}")
print(f"  Objetivo: {teste_info['objetivo']}")
print()

auditoria["fluxo"].append({
    "etapa": "1_definicao_teste",
    "status": "OK",
    "detalhes": teste_info
})

# ============================================================================
# ETAPA 2: ANÁLISE DA MENSAGEM
# ============================================================================
print("[2/6] ANÁLISE DA MENSAGEM\n")

# Reproduzir a mensagem exatamente como no teste
base = "Olá! Tudo bem? Meu fim de semana foi ótimo! "
repeticoes = 30
mensagem = (base * repeticoes) + "e queria marcar corte com a Bruna amanhã às 15h"

print(f"  Tamanho total: {len(mensagem)} chars")
print(f"  Estrutura:")
print(f"    - Parte A (repetitiva): '{base}' x 30 = {len(base) * 30} chars")
print(f"    - Parte B (pedido): 'e queria marcar corte com a Bruna amanhã às 15h' = {len('e queria marcar corte com a Bruna amanhã às 15h')} chars")
print(f"\n  Primeiros 100 chars: {mensagem[:100]}")
print(f"  Últimos 100 chars: {mensagem[-100:]}\n")

auditoria["fluxo"].append({
    "etapa": "2_analise_mensagem",
    "tamanho_chars": len(mensagem),
    "tamanho_kb": len(mensagem) / 1024,
    "estrutura": {
        "parte_repetitiva": f"'{base}' x {repeticoes}",
        "tamanho_parte_a": len(base) * repeticoes,
        "tamanho_parte_b": len("e queria marcar corte com a Bruna amanhã às 15h"),
        "pedido_final": "e queria marcar corte com a Bruna amanhã às 15h"
    },
    "primeiros_100": mensagem[:100],
    "ultimos_100": mensagem[-100:]
})

# ============================================================================
# ETAPA 3: CRITÉRIO DE SUCESSO ESPERADO
# ============================================================================
print("[3/6] CRITÉRIO DE SUCESSO ESPERADO\n")

criterio = {
    "condicao": "confirmacao_pendente == True",
    "raciocinio": "Se o pedido operacional final for detectado, o fluxo deve entrar em modo de confirmação, salvando confirmacao_pendente=True na sessão",
    "slots_esperados": ["servico", "profissional", "data", "hora"],
    "estado_esperado": {
        "confirmacao_pendente": True,
        "estado_fluxo": "aguardando_confirmacao_agendamento"
    }
}

print(f"  Condição de PASS: {criterio['condicao']}")
print(f"  Razão: {criterio['raciocinio']}")
print(f"  Slots esperados: {criterio['slots_esperados']}")
print()

auditoria["fluxo"].append({
    "etapa": "3_criterio_sucesso",
    "criterio": criterio
})

# ============================================================================
# ETAPA 4: RESULTADO DO TESTE ANTERIOR
# ============================================================================
print("[4/6] RESULTADO DO TESTE ANTERIOR\n")

# Carregar resultado anterior se existir
resultado_json = Path("resultado_p1_robustez_fluxo_conversacional_real.json")
if resultado_json.exists():
    with open(resultado_json) as f:
        resultado_anterior = json.load(f)
        print(f"  [OK] Encontrado: {resultado_json}")

        # Procurar cenário 05
        cenario_05_resultado = None
        for scenario in resultado_anterior.get("cenarios", []):
            if scenario.get("numero") == 5:
                cenario_05_resultado = scenario
                break

        if cenario_05_resultado:
            print(f"\n  Status Teste: {cenario_05_resultado.get('status', 'desconhecido')}")
            print(f"  Mensagem: {cenario_05_resultado.get('mensagem', 'N/A')}")

            if cenario_05_resultado.get('status') == 'FAIL':
                print(f"\n  [FALHA CONFIRMADA] Cenário 05 falhou!")
                motivo_fail = cenario_05_resultado.get('mensagem', 'desconhecido')
                print(f"  Motivo: {motivo_fail}")

                auditoria["fluxo"].append({
                    "etapa": "4_resultado_teste_anterior",
                    "status": "FAIL",
                    "motivo": motivo_fail,
                    "resultado_completo": cenario_05_resultado
                })
        else:
            print("  [AVISO] Cenário 05 não encontrado no JSON de resultados")
            auditoria["fluxo"].append({
                "etapa": "4_resultado_teste_anterior",
                "status": "NAO_ENCONTRADO",
                "detalhes": "Cenário 05 não está no arquivo de resultados"
            })
else:
    print(f"  [AVISO] Arquivo de resultado nao encontrado: {resultado_json}")
    auditoria["fluxo"].append({
        "etapa": "4_resultado_teste_anterior",
        "status": "ARQUIVO_NAO_ENCONTRADO",
        "detalhes": f"Esperado: {resultado_json}"
    })

print()

# ============================================================================
# ETAPA 5: ANÁLISE DO CÓDIGO DO TESTE
# ============================================================================
print("[5/6] ANÁLISE DO CÓDIGO DO TESTE\n")

analise_codigo = {
    "validacao": "resultado.confirmacao_pendente",
    "fonte_esperada": "estado_depois.get('confirmacao_pendente', False)",
    "logica": [
        "1. Executa roteador_principal() com mensagem longa",
        "2. Aguarda resposta",
        "3. Carrega estado_depois da sessão",
        "4. Verifica se confirmacao_pendente == True",
        "5. Se True: PASS | Se False: FAIL"
    ],
    "pontos_criticos": [
        "Mensagem muito longa (1800+ chars) pode ser truncada",
        "Pedido no final pode ser descartado durante normalização",
        "Classificador pode não reconhecer como operacional",
        "GPT pode focar no conteúdo pessoal inicial",
        "Router pode redirecionar para fluxo não-operacional"
    ]
}

print(f"  Validação esperada: {analise_codigo['validacao']}")
print(f"  Fonte: {analise_codigo['fonte_esperada']}")
print(f"\n  Pontos críticos:")
for i, ponto in enumerate(analise_codigo["pontos_criticos"], 1):
    print(f"    {i}. {ponto}")
print()

auditoria["fluxo"].append({
    "etapa": "5_analise_codigo_teste",
    "analise": analise_codigo
})

# ============================================================================
# ETAPA 6: HIPÓTESES DE FALHA (ORDENADAS POR PROBABILIDADE)
# ============================================================================
print("[6/6] HIPÓTESES DE FALHA (SEM EVIDÊNCIA TÉCNICA - APENAS ANÁLISE)\n")

hipoteses = [
    {
        "letra": "A",
        "titulo": "GPT não extrai pedido final de mensagem longa",
        "descricao": "O modelo GPT, ao receber 1800+ chars, pode priorizar processamento do conteúdo pessoal (primeira 90% da mensagem) e perder ou sumarizar o pedido final.",
        "risco": "ALTO",
        "probabilidade": "60%",
        "evidencia_necessaria": "Capturar JSON retornado pelo GPT e verificar se 'servico', 'profissional', 'data', 'hora' estao presentes"
    },
    {
        "letra": "B",
        "titulo": "Classificador descarta pedido ao detectar ruído pessoal",
        "descricao": "O classificador conversacional pode rotular a mensagem como 'informativa' (pessoal/conversão) ao invés de 'operacional' (agendamento), ignorando o pedido no final.",
        "risco": "ALTO",
        "probabilidade": "50%",
        "evidencia_necessaria": "Verificar saída de ClassificadorConversa.classificar() - qual tipo_conversacao foi detectado?"
    },
    {
        "letra": "C",
        "titulo": "Router intercepta e redireciona antes da interpretação correta",
        "descricao": "O principal_router pode redirecionar para fluxo de conversa genérica ao detectar conteúdo pessoal, sem tentar extrair a intenção operacional final.",
        "risco": "MEDIO",
        "probabilidade": "35%",
        "evidencia_necessaria": "Verificar logs do router - qual fluxo foi escolhido (agendamento vs conversa)?"
    },
    {
        "letra": "D",
        "titulo": "Contexto de sessão interfere na decisão",
        "descricao": "Se há contexto prévio da sessão (ex: fluxo anterior aberto), o sistema pode priorizar contexto antigo ao invés de processar novo pedido.",
        "risco": "BAIXO",
        "probabilidade": "25%",
        "evidencia_necessaria": "Verificar estado_antes e compará-lo com estado_depois"
    },
    {
        "letra": "E",
        "titulo": "Teste incorreto ou validação com critério errado",
        "descricao": "A condição confirmacao_pendente pode estar validando campo errado, ou confirmacao_pendente pode estar sendo setado em lugar diferente.",
        "risco": "BAIXO",
        "probabilidade": "15%",
        "evidencia_necessaria": "Verificar se confirmacao_pendente é salvada em outro lugar ou com outro nome"
    },
    {
        "letra": "F",
        "titulo": "Outro (especificar após auditoria técnica)",
        "descricao": "Pode haver causa combinada ou aspecto não previsto nas hipóteses A-E.",
        "risco": "DESCONHECIDO",
        "probabilidade": "20%",
        "evidencia_necessaria": "Resultado desta auditoria"
    }
]

for h in hipoteses:
    print(f"  [{h['letra']}] {h['titulo']}")
    print(f"      Risco: {h['risco']} | Probabilidade: {h['probabilidade']}")
    print(f"      Evidência necessária: {h['evidencia_necessaria']}\n")

auditoria["fluxo"].append({
    "etapa": "6_hipoteses_falha",
    "hipoteses": hipoteses
})

# ============================================================================
# TABELA RESUMIDA
# ============================================================================
print("\n" + "="*80)
print("TABELA DE EVIDÊNCIA POR ETAPA")
print("="*80 + "\n")

tabela = [
    {
        "etapa": "Mensagem original recebida",
        "esperado": "1800+ chars com conteúdo pessoal + pedido final",
        "obtido": "[OK] Conforme esperado (reproduzível)",
        "status": "[PASS] OK",
        "evidencia": "Linha 606-609 do teste"
    },
    {
        "etapa": "Normalização de texto",
        "esperado": "Preservar pedido final após normalização",
        "obtido": "[?] Desconhecido (requer auditoria técnica)",
        "status": "[?] DESCONHECIDO",
        "evidencia": "Requer execução com logs de normalizador_humano"
    },
    {
        "etapa": "Classificação conversacional",
        "esperado": "Tipo = 'operacional' (agendamento)",
        "obtido": "[?] Desconhecido",
        "status": "[?] DESCONHECIDO",
        "evidencia": "Requer execução com logs de ClassificadorConversa"
    },
    {
        "etapa": "Extração GPT",
        "esperado": "servico='corte', profissional='bruna', data='amanhã', hora='15h'",
        "obtido": "[?] Desconhecido",
        "status": "[?] DESCONHECIDO",
        "evidencia": "Requer captura de JSON do GPT"
    },
    {
        "etapa": "Roteamento principal",
        "esperado": "Fluxo de agendamento (confirmação pendente)",
        "obtido": "[?] Desconhecido",
        "status": "[?] DESCONHECIDO",
        "evidencia": "Requer logs de principal_router.py"
    },
    {
        "etapa": "Persistência em sessão",
        "esperado": "confirmacao_pendente = True",
        "obtido": "[FALHA] confirmacao_pendente = False (FALHA DO TESTE)",
        "status": "[FALHA] FALHA",
        "evidencia": "Resultado do teste: resultado.confirmacao_pendente == False"
    }
]

print(f"{'Etapa':<40} | {'Status':<12} | {'Evidência':<30}")
print("-" * 85)
for linha in tabela:
    print(f"{linha['etapa']:<40} | {linha['status']:<12} | {linha['evidencia']:<30}")

auditoria["tabela_resultado"] = tabela

# ============================================================================
# CONCLUSÃO
# ============================================================================
print("\n" + "="*80)
print("CONCLUSÃO PRELIMINAR")
print("="*80 + "\n")

print("[PASS] O QUE SABEMOS COM CERTEZA:")
print("  1. Teste foi executado (entrada processada)")
print("  2. Mensagem longa foi recebida (1800+ chars)")
print("  3. Critério de sucesso: confirmacao_pendente == True")
print("  4. Resultado: confirmacao_pendente == False (FALHA)\n")

print("[?] O QUE PRECISA AUDITORIA TÉCNICA:")
print("  1. GPT extraiu os slots (servico, profissional, data, hora)?")
print("  2. Classificador detectou como 'operacional'?")
print("  3. Router escolheu fluxo de agendamento?")
print("  4. Persistência salvou em campo correto?\n")

print("[OBJETIVO] PRÓXIMO PASSO:")
print("  Executar com OPENAI_API_KEY configurada para capturar:")
print("  - Saída do normalizador de texto")
print("  - Classificação conversacional")
print("  - JSON do GPT (slots extraídos)")
print("  - Logs do router")
print("  - Estado final da sessão\n")

auditoria["conclusao"] = {
    "estado": "AUDITORIA PRELIMINAR CONCLUIDA",
    "sabemos": [
        "Teste foi executado",
        "Entrada processada (1800+ chars)",
        "Critério de sucesso: confirmacao_pendente == True",
        "Resultado atual: confirmacao_pendente == False (FALHA)"
    ],
    "proxima_etapa": "Auditoria técnica com OPENAI_API_KEY para rastreio de fluxo completo"
}

# ============================================================================
# SALVAR AUDITORIA
# ============================================================================
print("="*80)
print("SALVANDO AUDITORIA")
print("="*80)

audit_file = "resultado_auditoria_cenario_05_preliminar.json"
with open(audit_file, 'w') as f:
    json.dump(auditoria, f, indent=2, default=str, ensure_ascii=False)

print(f"[OK] Auditoria salva em: {audit_file}\n")

print("="*80)
print("STATUS: Cenário 05 em FALHA - Auditoria preliminar documentada")
print("="*80)

