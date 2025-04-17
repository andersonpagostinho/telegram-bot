import asyncio
from services.gpt_service import processar_com_gpt

async def teste():
    resposta = await processar_com_gpt("qual minha agenda de hoje?")
    print(resposta)

asyncio.run(teste())
