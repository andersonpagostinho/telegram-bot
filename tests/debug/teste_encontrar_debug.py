#!/usr/bin/env python3
"""Debug detalhado"""

import asyncio
import sys
import io
from datetime import datetime

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')

from services.firebase_service_async import obter_id_dono

async def main():
    user_id = "usuario_teste_123"

    print(f"[TESTE] obter_id_dono('{user_id}')")

    try:
        resultado = await obter_id_dono(user_id)
        print(f"[OK] Resultado: {repr(resultado)}")
    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {str(e)}")

asyncio.run(main())
