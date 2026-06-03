#!/usr/bin/env python3
"""Teste isolado de encontrar_servico_mais_proximo()"""

import asyncio
import sys
import io
from datetime import datetime

# Force UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from services.profissional_service import encontrar_servico_mais_proximo

async def main():
    mensagem = "quem você tem disponível amanhã no período da manhã para corte de cabelo"
    user_id = "usuario_teste_123"

    print(f"[TESTE] Extraindo serviço")
    print(f"[MENSAGEM] {mensagem}")
    print(f"[USER_ID] {user_id}\n")

    print("[EXECUTANDO] encontrar_servico_mais_proximo()...")
    resultado = await encontrar_servico_mais_proximo(mensagem, user_id)

    print(f"\n[RESULTADO] {repr(resultado)}")

    if resultado:
        print(f"[OK] Encontrou serviço: '{resultado}'")
    else:
        print("[FALHA] Retornou None")
        print("\n[TESTANDO] Sem user_id (fallback para lista padrão)...")
        resultado2 = await encontrar_servico_mais_proximo(mensagem, None)
        print(f"[RESULTADO_2] {repr(resultado2)}")

asyncio.run(main())
