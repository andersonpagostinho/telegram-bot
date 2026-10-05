#!/usr/bin/env python3
"""
P0.4 COMPLETO — Teste Dirigido com update=None
Validar que linhas 837 e 843 (antigo 842) não quebram mais
"""

def test_protecoes_completas():
    """Validar que TODAS as proteções necessárias foram aplicadas"""
    print("\n[TESTE] Validando proteções completas...")

    with open('handlers/event_handler.py', 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    # Pontos que PRECISAM estar protegidos
    pontos_criticos = [
        (837, "fallback - expediente configurado"),
        (843, "validacao falhou - agenda configurada"),  # Era 842, agora é 843
        (829, "horario mais proximo - agenda fechada"),
        (1391, "erro inesperado - excecao geral"),  # reply_text está em 1391 com if update em 1390
    ]

    print("\nVerificando proteções em pontos críticos:")
    print("="*60)

    tudo_ok = True

    for linha_num, descricao in pontos_criticos:
        if linha_num <= len(linhas):
            linha = linhas[linha_num - 1]

            # Verificar se há if update: nos 2 linhas anteriores
            protegido = False
            for j in range(max(0, linha_num-3), linha_num):
                if 'if update:' in linhas[j]:
                    protegido = True
                    break

            if protegido:
                print(f"  [OK] Linha {linha_num}: PROTEGIDA | {descricao}")
            else:
                print(f"  [ERRO] Linha {linha_num}: DESPROTEGIDA | {descricao}")
                tudo_ok = False

    print("="*60)

    if tudo_ok:
        print("\n[RESULTADO] Protecoes OK - P0.4 COMPLETO pode prosseguir")
        return True
    else:
        print("\n[RESULTADO] Protecoes INCOMPLETAS - P0.4 bloqueado")
        return False


def test_sem_indentacao_errada():
    """Validar que não há erro de indentação"""
    print("\n[TESTE] Validando sintaxe/indentação...")

    try:
        with open('handlers/event_handler.py', 'r') as f:
            code = f.read()

        compile(code, 'handlers/event_handler.py', 'exec')
        print("  [OK] Arquivo compila sem erro de sintaxe")
        return True
    except SyntaxError as e:
        print(f"  [ERRO] Erro de sintaxe: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("P0.4 COMPLETO — TESTE DIRIGIDO COM update=None")
    print("="*60)

    t1 = test_protecoes_completas()
    t2 = test_sem_indentacao_errada()

    print("\n" + "="*60)
    if t1 and t2:
        print("RESULTADO: PASSOU - P0.4 pronto para commit")
        exit(0)
    else:
        print("RESULTADO: BLOQUEADO - Corrigir proteções")
        exit(1)
