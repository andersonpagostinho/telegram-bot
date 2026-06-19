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

async def salvar_contexto_temporario(user_id: str, contexto: dict, tenant_id: str = None):
    """DEPRECADO: Use salvar_contexto_temporario_v2(dono_id, cliente_id, contexto).

    Função legada mantida APENAS para compatibilidade com código existente.
    ⚠️ NÃO isolado por tenant — pode causar contaminação multi-tenant.

    PATCH DEFENSIVO (2026-06-19):
    - Se tenant_id informado: gravar tenant_id no contexto como guard rail
    - Se tenant_id não informado: logar alerta de risco
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    if not contexto:
        print(f"🚨 [BLOCK SAVE LEGADO] contexto vazio bloqueado em {path}", flush=True)
        return

    # 🔥 merge manual defensivo
    atual = await buscar_dado_em_path(path) or {}
    atual.update(contexto)

    # 🧬 PATCH MT-07: Registrar tenant_id para proteção defensiva
    if tenant_id:
        atual["_tenant_id_guard"] = tenant_id
        print(f"🧪 [CTX_LEGADO_SAVE_COMPAT] path={path} | tenant_id={tenant_id} | guard_adicionado", flush=True)
    else:
        print(f"🚨 [CTX_LEGADO_SAVE_SEM_TENANT] ⚠️ RISCO | path={path} | tenant_id não fornecido", flush=True)

    print(f"🧪 [SAVE CTX LEGADO] ⚠️ NÃO MULTI-TENANT | path={path}", flush=True)

    return await atualizar_dado_em_path(path, atual)


async def carregar_contexto_temporario(user_id: str, tenant_id: str = None):
    """DEPRECADO: Use carregar_contexto_temporario_v2(dono_id, cliente_id).

    Função legada mantida APENAS para compatibilidade com código existente.
    ⚠️ NÃO isolado por tenant — pode retornar dados errados em multi-tenant.

    PATCH DEFENSIVO (2026-06-19):
    - Se tenant_id informado: validar que contexto pertence ao tenant correto
    - Se tenant mismatch: ignorar contexto, logar alerta
    - Se sem tenant_id: logar alerta de risco, mas retornar para compatibilidade
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
    data = await buscar_dado_em_path(path)

    if not data:
        print(f"🚨 [CTX VAZIO DETECTADO LEGADO] path={path}", flush=True)
        return None

    # 🧬 PATCH MT-07: Validar tenant_id se informado
    if tenant_id:
        guard_tenant = data.get("_tenant_id_guard")
        if guard_tenant and guard_tenant != tenant_id:
            print(f"🚨 [CTX_LEGADO_TENANT_MISMATCH] ⚠️ BLOQUEADO | path={path} | esperado={tenant_id} | armazenado={guard_tenant}", flush=True)
            return {}  # Retorna contexto vazio para proteger
        elif not guard_tenant:
            print(f"🚨 [CTX_LEGADO_SEM_TENANT] ⚠️ RISCO | path={path} | contexto não tem guard, ignorando para segurança", flush=True)
            return {}  # Retorna contexto vazio para fluxo crítico
        else:
            # Guard bate, permanecer
            print(f"🧪 [CTX_LEGADO_COMPAT] | path={path} | tenant_id={tenant_id} | guard_validado", flush=True)
    else:
        print(f"🚨 [CTX_LEGADO_SEM_TENANT_PARAM] ⚠️ RISCO | path={path} | tenant_id não fornecido, retornando para compatibilidade apenas", flush=True)

    print(f"🧪 [LOAD CTX LEGADO] ⚠️ NÃO MULTI-TENANT | path={path}", flush=True)
    return data


async def limpar_contexto_agendamento(user_id: str, tenant_id: str = None):
    """DEPRECADO: Use limpar_contexto_agendamento_v2(dono_id, cliente_id).

    Função legada mantida APENAS para compatibilidade com código existente.
    ⚠️ NÃO isolado por tenant.

    PATCH DEFENSIVO (2026-06-19):
    - Se tenant_id informado: validar antes de limpar
    - Se mismatch: logar alerta e não limpar
    - Se sem tenant_id: logar risco
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    # 🧬 PATCH MT-07: Validar tenant antes de limpar
    if tenant_id:
        atual = await buscar_dado_em_path(path) or {}
        guard_tenant = atual.get("_tenant_id_guard")
        if guard_tenant and guard_tenant != tenant_id:
            print(f"🚨 [CTX_LEGADO_CLEAR_MISMATCH] ⚠️ NÃO LIMPANDO | path={path} | esperado={tenant_id} | armazenado={guard_tenant}", flush=True)
            return  # Não limpa contexto de outro tenant
        print(f"🧪 [CTX_LEGADO_CLEAR_COMPAT] | path={path} | tenant_id={tenant_id} | limpando com validação", flush=True)
    else:
        print(f"🚨 [CTX_LEGADO_CLEAR_SEM_TENANT] ⚠️ RISCO | path={path} | tenant_id não fornecido", flush=True)

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

    print(f"🧪 [CLEAR CTX LEGADO] ⚠️ NÃO MULTI-TENANT | path={path}", flush=True)
    return await atualizar_dado_em_path(path, payload)