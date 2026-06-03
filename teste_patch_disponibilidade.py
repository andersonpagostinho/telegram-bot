#!/usr/bin/env python3
"""
Teste do patch de disponibilidade em responder_consulta_informativa()

Entrada: "quem você tem disponível amanhã no período da manhã para corte de cabelo"
Resultado esperado: Lista de profissionais reais que fazem corte, SEM [GPT_ROUTE]
"""

import asyncio
import sys
import io
from datetime import datetime, date

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Adicionar projeto ao path
sys.path.insert(0, '/Users/ANDERSON/iCloudDrive/Projeto Mercado Digital/Agente Bot/NeoEve - Empresarial')

from services.informacao_service import responder_consulta_informativa

async def teste_disponibilidade():
    """Testa o novo ramo de disponibilidade."""

    # Usar user_id de teste (será resolvido para dono_id)
    user_id = "usuario_teste_123"

    # Entrada que deveria ativar o novo ramo
    mensagem = "quem você tem disponível amanhã no período da manhã para corte de cabelo"

    print("=" * 80)
    print("[TESTE] Consulta de Disponibilidade")
    print("=" * 80)
    print(f"\n[ENTRADA] {mensagem}")
    print(f"[USER_ID] {user_id}")
    print(f"[DATA_TESTE] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n[EXECUTANDO] responder_consulta_informativa()...")

    try:
        resposta = await responder_consulta_informativa(mensagem, user_id)

        print("\n" + "=" * 80)
        print("[RESULTADO]")
        print("=" * 80)

        if resposta:
            print(f"\n{resposta}")

            # Verificar critérios
            print("\n" + "=" * 80)
            print("[VALIDACAO]")
            print("=" * 80)

            if "[GPT_ROUTE]" in resposta:
                print("[FALHA] Resposta contém [GPT_ROUTE] (caiu para GPT)")
                return False
            else:
                print("[OK] Sem [GPT_ROUTE] (respondeu deterministicamente)")

            if "corte" in resposta.lower():
                print("[OK] Mencionou 'corte' na resposta")
            else:
                print("[AVISO] Não mencionou 'corte' na resposta")

            if "nenhum" in resposta.lower() or "não" in resposta.lower():
                print("[INFO] Respondeu que não há disponibilidade (possível)")
            elif any(prof in resposta for prof in ["Bruna", "Gloria", "Joana", "Maria", "Ana", "Pedro"]):
                print("[OK] Mencionou profissionais reais")
            else:
                print("[INFO] Resposta genérica ou sem nomes específicos")

            return True
        else:
            print("[FALHA] responder_consulta_informativa() retornou None")
            print("        Não reconheceu como consulta de disponibilidade")
            return False

    except Exception as e:
        print(f"\n[ERRO] {type(e).__name__}")
        print(f"       {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    sucesso = await teste_disponibilidade()

    print("\n" + "=" * 80)
    if sucesso:
        print("[OK] TESTE CONCLUÍDO COM SUCESSO")
    else:
        print("[FALHA] TESTE FALHOU")
    print("=" * 80)

    return 0 if sucesso else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
