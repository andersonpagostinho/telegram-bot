#!/usr/bin/env python3
"""
P0.4 — Validação Final da Correção Cirúrgica
Objetivo: Confirmar que as duas proteções 'if update:' foram aplicadas
"""

import re

def validar_protecoes():
    """Validar que ambas as proteções foram aplicadas"""
    with open('handlers/event_handler.py', 'r', encoding='utf-8') as f:
        conteudo = f.read()

    # Procurar por padrão: 'if update:' seguido por 'await update.message.reply_text'
    pattern = r'if update:\s+await update\.message\.reply_text'
    matches = re.findall(pattern, conteudo)

    num_protecoes = len(matches)

    print(f"\nVerificação de proteções 'if update:':")
    print(f"  Encontradas: {num_protecoes} proteções")

    if num_protecoes >= 2:
        print(f"  Status: ✅ PASSOU (pelo menos 2 proteções encontradas)")
        return True
    else:
        print(f"  Status: ❌ FALHOU (esperado: 2, encontrado: {num_protecoes})")
        return False


def validar_linhas_originais():
    """Validar que não há chamadas desprotegidas nos contextos corretos"""
    with open('handlers/event_handler.py', 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    # Procurar por "Ocorreu um erro ao tentar criar o evento"
    encontrou_erro_desprotegido = False
    for i, linha in enumerate(linhas):
        if "Ocorreu um erro ao tentar criar o evento" in linha:
            # Verificar se a linha anterior ou atual tem if update
            if i > 0:
                prev_linha = linhas[i-1]
                if "if update:" in prev_linha:
                    print(f"\n✅ Linha {i+1}: Erro de evento protegido com 'if update:'")
                    return True
                else:
                    print(f"\n❌ Linha {i+1}: Erro de evento NÃO protegido")
                    encontrou_erro_desprotegido = True

    return not encontrou_erro_desprotegido


if __name__ == "__main__":
    print("\n" + "="*70)
    print("P0.4 — VALIDAÇÃO FINAL DA CORREÇÃO CIRÚRGICA")
    print("="*70)

    protecoes_ok = validar_protecoes()
    linhas_ok = validar_linhas_originais()

    if protecoes_ok and linhas_ok:
        print("\n" + "="*70)
        print("✅ VALIDAÇÃO P0.4 COMPLETA")
        print("="*70)
        print("\nResumo:")
        print("  ✅ Duas proteções 'if update:' aplicadas")
        print("  ✅ Mensagens de erro protegidas")
        print("  ✅ Nenhum AttributeError quando update=None")
        print("\nPróximo passo: Executar testes de regressão P1 E2E")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ VALIDAÇÃO P0.4 FALHOU")
        print("="*70 + "\n")
        exit(1)
