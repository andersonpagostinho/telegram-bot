from dotenv import load_dotenv
load_dotenv()

import asyncio
from services.intencao_gpt_service import identificar_intencao_com_gpt

async def testar():
    texto = "quero marcar uma nova reunião com equipe amanhã"
    intencao = await identificar_intencao_com_gpt(texto)
    print("🧠 Intenção detectada:", intencao)

asyncio.run(testar())
