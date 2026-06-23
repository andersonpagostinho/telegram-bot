# -*- coding: utf-8 -*-
"""
Handler isolado para confirmação/negação pendente.

Responsabilidade única: Tomar decisão determinística quando há
confirmacao_pendente=True, antes de qualquer processamento lateral.

Este handler é chamado ANTES de:
- CONSULTA_INFORMATIVA_IDLE
- NEOEVE_NEUTRA
- Classificador GPT
- Ajuste incremental

Garantias:
- Não altera agenda/conflito/evento
- Não altera prompts GPT
- Não altera onboarding
- Retorna estrutura simples: (tratado, acao, motivo)
"""


async def resolver_confirmacao_pendente(
    ctx: dict,
    texto_normalizado: str,
    tenant_id: str,
    user_id: str,
    funcoes: dict = None
) -> dict:
    """
    Resolve confirmação/negação pendente com lógica determinística.

    Args:
        ctx: Contexto carregado da sessão
        texto_normalizado: Texto já normalizado (lowercase, sem acentos)
        tenant_id: Tenant para multi-tenant safety
        user_id: Actor ID para segurança
        funcoes: Dict com 'eh_confirmacao' e 'eh_desistencia_fluxo' callables

    Returns:
        {
            "tratado": bool,           # True se decisão foi tomada
            "acao": str or None,       # "negar" | "confirmar" | None
            "motivo": str or None,     # Explicação da decisão
            "ctx_modificado": dict,    # Contexto se acao != None
        }
    """
    ctx = ctx or {}
    funcoes = funcoes or {}

    # Guard: multi-tenant safety
    if not tenant_id or not user_id:
        return {
            "tratado": False,
            "acao": None,
            "motivo": "seguranca_falha",
            "ctx_modificado": None,
        }

    # Guard: confirmacao_pendente deve estar True
    confirmacao_pendente = (
        ctx.get("aguardando_confirmacao_agendamento")
        or ctx.get("confirmacao_pendente")
    )

    if not confirmacao_pendente:
        return {
            "tratado": False,
            "acao": None,
            "motivo": "sem_confirmacao_pendente",
            "ctx_modificado": None,
        }

    eh_desistencia = funcoes.get("eh_desistencia_fluxo")
    eh_confirmacao = funcoes.get("eh_confirmacao")

    # Decisão 1: Negação/Desistência (prioridade máxima)
    if eh_desistencia and eh_desistencia(texto_normalizado):
        print(f"[LOTE_3E_NEGACAO_EARLY] Negação detectada: {texto_normalizado[:50]}", flush=True)

        ctx_modificado = ctx.copy()
        ctx_modificado["aguardando_confirmacao_agendamento"] = False
        ctx_modificado["confirmacao_pendente"] = False
        ctx_modificado["dados_confirmacao_agendamento"] = {}
        ctx_modificado["draft_agendamento"] = {}
        ctx_modificado["estado_fluxo"] = "idle"
        ctx_modificado["objetivo_conversacional"] = None
        ctx_modificado["tipo_ajuste_incremental"] = None
        ctx_modificado["intencao_conversacional"] = None

        return {
            "tratado": True,
            "acao": "negar",
            "motivo": "desistencia_detectada",
            "ctx_modificado": ctx_modificado,
        }

    # Decisão 2: Confirmação
    if eh_confirmacao and eh_confirmacao(texto_normalizado):
        print(f"[LOTE_3E_CONFIRMACAO_EARLY] Confirmação detectada: {texto_normalizado[:50]}", flush=True)

        ctx_modificado = ctx.copy()
        ctx_modificado["intencao_conversacional"] = "confirmacao_agendamento"

        return {
            "tratado": True,
            "acao": "confirmar",
            "motivo": "confirmacao_detectada",
            "ctx_modificado": ctx_modificado,
        }

    # Decisão 3: Sem ação determinística
    return {
        "tratado": False,
        "acao": None,
        "motivo": "sem_decisao_deterministica",
        "ctx_modificado": None,
    }
