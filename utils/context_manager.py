# utils/context_manager.py
# [PATCH P0-MIGRACAO]: Proxy para handlers.context_manager
# Este arquivo mantido APENAS para compatibilidade com código existente
# Todos os imports antigos de utils.context_manager agora delegam para handlers.context_manager

from handlers.context_manager import (
    salvar_contexto_temporario,
    carregar_contexto_temporario,
    atualizar_contexto,
    limpar_contexto,
    verificar_fim_fluxo_e_limpar
)

# Legacy compatibility
CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"

async def limpar_contexto_agendamento(user_id: str, tenant_id: str = None):
    """[PATCH P0] Limpeza de contexto de agendamento com suporte multi-tenant.

    Delega para handlers.context_manager.limpar_contexto() que já faz a limpeza correta.
    """
    return await limpar_contexto(user_id, tenant_id=tenant_id)