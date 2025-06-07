# utils/context_manager.py
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path

CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"

# 🔄 Salvar contexto completo (ou atualizar)
async def salvar_contexto_temporario(user_id: str, contexto: dict):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await salvar_dado_em_path(path, contexto)

# 🗑️ Resetar contexto completo
async def resetar_contexto(user_id: str):
    await salvar_contexto_temporario(user_id, {})
    return True

# 🔍 Carregar contexto salvo
async def carregar_contexto_temporario(user_id: str):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await buscar_dado_em_path(path)

# 🧠 Atualiza histórico apenas se for diferente da última entrada
async def atualizar_contexto(user_id: str, nova_interacao: dict):
    contexto = await carregar_contexto_temporario(user_id) or {}
    historico = contexto.setdefault("historico", [])

    if not historico or historico[-1] != nova_interacao:
        historico.append(nova_interacao)
        contexto["historico"] = historico[-5:]  # mantém só os últimos 5
        await salvar_contexto_temporario(user_id, contexto)

    return contexto

# 🗑️ Limpar contexto (apagar historico)
async def limpar_contexto(user_id: str):
    await salvar_contexto_temporario(user_id, {"historico": []})
    return True
