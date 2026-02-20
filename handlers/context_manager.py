# utils/context_manager.py
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path

CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"

# 🔄 Salvar contexto completo (ou atualizar)
async def salvar_contexto_temporario(user_id: str, novos_dados: dict):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    contexto_atual = await buscar_dado_em_path(path) or {}
    contexto_atual.update(novos_dados)
    return await salvar_dado_em_path(path, contexto_atual)

# 🔍 Carregar contexto salvo
async def carregar_contexto_temporario(user_id: str):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await buscar_dado_em_path(path)

# 🧠 Adicionar nova entrada ao historico e salvar
async def atualizar_contexto(user_id: str, nova_interacao: dict):
    contexto = await carregar_contexto_temporario(user_id) or {"historico": []}
    contexto["historico"].append(nova_interacao)

    # Limitar tamanho do historico
    contexto["historico"] = contexto["historico"][-5:]  # Mantem as ultimas 5 interacoes

    await salvar_contexto_temporario(user_id, contexto)
    return contexto

# 🔍 helper
async def verificar_fim_fluxo_e_limpar(user_id: str, resultado: dict):
    fim_acoes = ["criar_evento", "fim_conversa", "followup_concluido", "relatorio_semanal", "relatorio_diario"]

    if resultado.get("acao") in fim_acoes:
        print("🧹 Limpando contexto após ação final:", resultado.get("acao"))
        await limpar_contexto(user_id)

# 🗑️ Limpar contexto (apagar historico)
async def limpar_contexto(user_id: str):
    await salvar_contexto_temporario(user_id, {"historico": []})
    return True
