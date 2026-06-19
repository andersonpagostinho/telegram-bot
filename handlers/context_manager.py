# handlers/context_manager.py
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from utils.contexto_temporario import (
    salvar_contexto_temporario as salvar_v1_com_guard,
    carregar_contexto_temporario as carregar_v1_com_guard
)

CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"

# [SAVE] Salvar contexto completo (ou atualizar)
async def salvar_contexto_temporario(user_id: str, novos_dados: dict, tenant_id: str = None):
    """Salva contexto com guard rail se tenant_id fornecido."""
    # P0-003: Use v1 com guard rail se tenant_id disponivel
    if tenant_id:
        return await salvar_v1_com_guard(user_id, novos_dados, tenant_id=tenant_id)

    # Fallback: usar path legado direto (com log de risco)
    print(f"[AVISO] salvar_contexto_temporario sem tenant_id: {user_id} | risco multi-tenant", flush=True)
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    contexto_atual = await buscar_dado_em_path(path) or {}
    contexto_atual.update(novos_dados)
    return await salvar_dado_em_path(path, contexto_atual)

# [LOAD] Carregar contexto salvo
async def carregar_contexto_temporario(user_id: str, tenant_id: str = None):
    """Carrega contexto com guard rail se tenant_id fornecido."""
    # P0-003: Use v1 com guard rail se tenant_id disponivel
    if tenant_id:
        return await carregar_v1_com_guard(user_id, tenant_id=tenant_id)

    # Fallback: usar path legado direto (com log de risco)
    print(f"[AVISO] carregar_contexto_temporario sem tenant_id: {user_id} | risco multi-tenant", flush=True)
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await buscar_dado_em_path(path)

# [BRAIN] Adicionar nova entrada ao historico e salvar
async def atualizar_contexto(user_id: str, nova_interacao: dict, tenant_id: str = None):
    contexto = await carregar_contexto_temporario(user_id, tenant_id=tenant_id) or {"historico": []}
    contexto["historico"].append(nova_interacao)

    # Limitar tamanho do historico
    contexto["historico"] = contexto["historico"][-5:]  # Mantem ultimas 5 interacoes

    await salvar_contexto_temporario(user_id, contexto, tenant_id=tenant_id)
    return contexto

# [CHECK] helper
async def verificar_fim_fluxo_e_limpar(user_id: str, resultado: dict, tenant_id: str = None):
    fim_acoes = ["criar_evento", "fim_conversa", "followup_concluido", "relatorio_semanal", "relatorio_diario"]

    if resultado.get("acao") in fim_acoes:
        print(f"[CLEANUP] Limpando contexto apos acao final: {resultado.get('acao')}", flush=True)
        await limpar_contexto(user_id, tenant_id=tenant_id)

# [DELETE] Limpar contexto (apagar historico)
async def limpar_contexto(user_id: str, tenant_id: str = None):
    await salvar_contexto_temporario(user_id, {"historico": []}, tenant_id=tenant_id)
    return True
