# utils/context_manager.py
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path

CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"

# 🔄 Salvar contexto completo (ou atualizar)
async def salvar_contexto_temporario(user_id: str, contexto: dict):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await salvar_dado_em_path(path, contexto)

# 🔍 Carregar contexto salvo
async def carregar_contexto_temporario(user_id: str):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await buscar_dado_em_path(path)

# 🧠 Adicionar nova entrada ao historico e salvar
async def atualizar_contexto(user_id: str, nova_interacao: dict):
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto.setdefault("historico", []).append(nova_interacao)

    # Limitar tamanho do historico
    contexto["historico"] = contexto["historico"][-5:]

    await salvar_contexto_temporario(user_id, contexto)
    return contexto

# 🗑️ Limpar contexto (apagar historico)
async def limpar_contexto(user_id: str):
    await salvar_contexto_temporario(user_id, {"historico": []})
    return True
