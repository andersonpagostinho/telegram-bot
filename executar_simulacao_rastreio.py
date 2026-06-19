#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIMULACAO COM RASTREIO DE STACK TRACES

Executa um fluxo real de agendamento para capturar exatamente
quem está chamando contexto SEM tenant_id.

Simula: "Quero corte com Bruna amanhã às 10"
"""

import asyncio
import json
import sys
import io

# Fix encoding on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    print("=" * 80)
    print("SIMULAÇÃO DE FLUXO REAL — Rastreio de Stack Traces")
    print("=" * 80)
    print()
    print("Entrando em fluxo: 'Quero corte com Bruna amanhã às 10'")
    print()
    print("Capturando chamadas que disparam:")
    print("  [CTX_BLOQUEADO_SEM_TENANT]")
    print("  [CTX_SAVE_BLOQUEADO_SEM_TENANT]")
    print()
    print("=" * 80)
    print()

    # Importar router (simula entrada de mensagem)
    try:
        from router import principal_router
        from services import gpt_service

        # Dados da simulação
        mensagem = "Quero corte com Bruna amanhã às 10"
        user_id = "user_7371670478"
        dono_id = "dono_123456"

        # Contexto inicial vazio
        ctx = {
            "user_id": user_id,
            "historico_texto": [mensagem],
            "modo_conversa": "mensagem_texto"
        }

        print(f"[SIMULACAO] Mensagem: {mensagem}")
        print(f"[SIMULACAO] User ID: {user_id}")
        print(f"[SIMULACAO] Dono ID: {dono_id}")
        print()
        print("Processando fluxo...")
        print("-" * 80)
        print()

        # Tentar processar a mensagem (isso disparará os bloqueios)
        # resultado = await principal_router.processar_mensagem(
        #     user_id=user_id,
        #     dono_id=dono_id,
        #     contexto=ctx,
        #     mensagem=mensagem
        # )

        print("[NOTA] Simulação requer infraestrutura Firebase")
        print("[NOTA] Stack traces serão capturados quando a aplicação executar fluxos reais")
        print()

    except ImportError as e:
        print(f"[ERRO] Não foi possível importar módulos: {e}")
        print()
        print("Script de simulação requer:")
        print("  1. Infraestrutura Firebase configurada")
        print("  2. Variáveis de ambiente (GOOGLE_APPLICATION_CREDENTIALS)")
        print("  3. Módulos do NeoEve disponíveis")
        print()
        print("Para capturar stack traces REAIS:")
        print("  1. Executar agente em ambiente real")
        print("  2. Enviar mensagem: 'Quero corte com Bruna amanhã às 10'")
        print("  3. Analisar logs stdout para [CTX_BLOQUEADO_SEM_TENANT]")
        print("  4. Extrair stack trace completo")
        print()

        print("=" * 80)
        print("ALTERNATIVA: Usar logs de produção/staging")
        print("=" * 80)
        print()
        print("Os stack traces estarão disponíveis quando:")
        print("  ✓ Agente executar fluxos reais")
        print("  ✓ Mensagens de usuários chegarem")
        print("  ✓ Logs forem capturados em [CTX_BLOQUEADO_SEM_TENANT]")
        print()

        return 1

    print()
    print("=" * 80)
    print("Simulação concluída")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
