import asyncio
import os
from dotenv import load_dotenv

# 👇 Carrega as variáveis do .env
load_dotenv()

# ✅ Ajuste o caminho conforme sua estrutura
from services.firebase_service_async import buscar_subcolecao

async def testar_buscar_tarefas():
    user_id = "7394370553"  # Use um ID que você sabe que tem tarefas
    path = f"Clientes/{user_id}/Tarefas"
    
    print(f"\n🔎 Buscando tarefas em: {path}")
    tarefas = await buscar_subcolecao(path)
    
    if tarefas:
        print(f"\n✅ Tarefas encontradas para o usuário {user_id}:\n")
        for id, dados in tarefas.items():
            print(f"📝 {id} → {dados}")
    else:
        print("\n⚠️ Nenhuma tarefa encontrada.")

if __name__ == "__main__":
    asyncio.run(testar_buscar_tarefas())
