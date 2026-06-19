from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from google.cloud import firestore

# ============================================================================
# PATCH MT-07: Contexto isolado por tenant (dono_id)
#
# Funções novas (recomendadas):
#   salvar_contexto_temporario_v2(dono_id, cliente_id, contexto)
#   carregar_contexto_temporario_v2(dono_id, cliente_id)
#
# Funções legadas (deprecadas, usar apenas com fallback explícito):
#   salvar_contexto_temporario(user_id, contexto) — USAR SOMENTE PARA COMPATIBILIDADE
#   carregar_contexto_temporario(user_id) — USAR SOMENTE PARA COMPATIBILIDADE
# ============================================================================

# ========== VERSÃO NOVA (RECOMENDADA) — ISOLADO POR TENANT ==========

async def salvar_contexto_temporario_v2(dono_id: str, cliente_id: str, contexto: dict):
    """Salvar contexto isolado por dono_id (tenant) + cliente_id.

    PATCH MT-07: Contextualiza multi-tenant.
    Path: Clientes/{dono_id}/Sessoes/{cliente_id}
    """
    if not dono_id:
        raise ValueError("dono_id é obrigatório para salvar contexto multi-tenant")
    if not cliente_id:
        raise ValueError("cliente_id é obrigatório para salvar contexto")

    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    if not contexto:
        print(f"🚨 [BLOCK SAVE] contexto vazio bloqueado em {path}", flush=True)
        return

    # 🔥 merge manual defensivo
    atual = await buscar_dado_em_path(path) or {}
    atual.update(contexto)

    print(f"🧪 [SAVE CTX v2] path={path} | dono={dono_id} | cliente={cliente_id} | contexto_final={atual}", flush=True)

    return await atualizar_dado_em_path(path, atual)


async def carregar_contexto_temporario_v2(dono_id: str, cliente_id: str):
    """Carregar contexto isolado por dono_id (tenant) + cliente_id.

    PATCH MT-07: Contextualiza multi-tenant.
    Path: Clientes/{dono_id}/Sessoes/{cliente_id}
    """
    if not dono_id:
        raise ValueError("dono_id é obrigatório para carregar contexto multi-tenant")
    if not cliente_id:
        raise ValueError("cliente_id é obrigatório para carregar contexto")

    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"
    data = await buscar_dado_em_path(path)

    if not data:
        print(f"🚨 [CTX VAZIO DETECTADO v2] path={path} | dono={dono_id} | cliente={cliente_id}", flush=True)

    print(f"🧪 [LOAD CTX v2] path={path} | dono={dono_id} | cliente={cliente_id} | data={data}", flush=True)
    return data


async def limpar_contexto_agendamento_v2(dono_id: str, cliente_id: str):
    """Limpar contexto isolado por dono_id (tenant) + cliente_id.

    PATCH MT-07: Contextualiza multi-tenant.
    Path: Clientes/{dono_id}/Sessoes/{cliente_id}
    """
    if not dono_id:
        raise ValueError("dono_id é obrigatório para limpar contexto multi-tenant")
    if not cliente_id:
        raise ValueError("cliente_id é obrigatório para limpar contexto")

    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    payload = {
        "modo_escolha_horario": False,
        "horarios_sugeridos": [],
        "alternativa_profissional": None,
        "ultima_opcao_profissionais": [],

        "aguardando_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_anteriores": firestore.DELETE_FIELD,

        "draft_agendamento": {},
        "ultima_acao": None,
        "ultima_intencao": None,

        "hora_confirmada": None,
        "sugestoes": [],
        "ultima_consulta": None,

        "data_hora": None,
        "servico": None,
        "profissional_escolhido": None,

        "historico_texto": [],

        "evento_criado": False,

        "pergunta_amanha_mesmo_horario": False,
        "data_hora_pendente": None,

        "objetivo_conversacional": None,
        "intencao_conversacional": None,
        "modo_conversa": None,

        "estado_fluxo": "idle"
    }

    print(f"🧪 [CLEAR CTX v2] path={path} | dono={dono_id} | cliente={cliente_id} | payload_keys={list(payload.keys())}", flush=True)
    return await atualizar_dado_em_path(path, payload)


# ========== VERSÃO LEGADA (DEPRECADA) — APENAS COMPATIBILIDADE ==========

async def salvar_contexto_temporario(user_id: str, contexto: dict):
    """DEPRECADO: Use salvar_contexto_temporario_v2(dono_id, cliente_id, contexto).

    Função legada mantida APENAS para compatibilidade com código existente.
    ⚠️ NÃO isolado por tenant — pode causar contaminação multi-tenant.
    ⚠️ Usar somente se dono_id não disponível (ex: migração).
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    if not contexto:
        print(f"🚨 [BLOCK SAVE LEGADO] contexto vazio bloqueado em {path}", flush=True)
        return

    # 🔥 merge manual defensivo
    atual = await buscar_dado_em_path(path) or {}
    atual.update(contexto)

    print(f"🧪 [SAVE CTX LEGADO] ⚠️ NÃO MULTI-TENANT | path={path} | contexto_final={atual}", flush=True)

    return await atualizar_dado_em_path(path, atual)


async def carregar_contexto_temporario(user_id: str):
    """DEPRECADO: Use carregar_contexto_temporario_v2(dono_id, cliente_id).

    Função legada mantida APENAS para compatibilidade com código existente.
    ⚠️ NÃO isolado por tenant — pode retornar dados errados em multi-tenant.
    ⚠️ Usar somente se dono_id não disponível (ex: migração).
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
    data = await buscar_dado_em_path(path)

    if not data:
        print(f"🚨 [CTX VAZIO DETECTADO LEGADO] path={path}", flush=True)

    print(f"🧪 [LOAD CTX LEGADO] ⚠️ NÃO MULTI-TENANT | path={path} | data={data}", flush=True)
    return data


async def limpar_contexto_agendamento(user_id: str):
    """DEPRECADO: Use limpar_contexto_agendamento_v2(dono_id, cliente_id).

    Função legada mantida APENAS para compatibilidade com código existente.
    ⚠️ NÃO isolado por tenant.
    ⚠️ Usar somente se dono_id não disponível (ex: migração).
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    payload = {
        "modo_escolha_horario": False,
        "horarios_sugeridos": [],
        "alternativa_profissional": None,
        "ultima_opcao_profissionais": [],

        "aguardando_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_anteriores": firestore.DELETE_FIELD,

        "draft_agendamento": {},
        "ultima_acao": None,
        "ultima_intencao": None,

        "hora_confirmada": None,
        "sugestoes": [],
        "ultima_consulta": None,

        "data_hora": None,
        "servico": None,
        "profissional_escolhido": None,

        "historico_texto": [],

        "evento_criado": False,

        "pergunta_amanha_mesmo_horario": False,
        "data_hora_pendente": None,

        "objetivo_conversacional": None,
        "intencao_conversacional": None,
        "modo_conversa": None,

        "estado_fluxo": "idle"
    }

    print(f"🧪 [CLEAR CTX LEGADO] ⚠️ NÃO MULTI-TENANT | path={path} | payload={payload}", flush=True)
    return await atualizar_dado_em_path(path, payload)