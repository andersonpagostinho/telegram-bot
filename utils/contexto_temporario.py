from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from google.cloud import firestore
import traceback

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

async def salvar_sessao_temporaria(actor_id: str, contexto: dict, tenant_id: str):
    """Salvar sessão isolada por tenant_id + actor_id (NOVO PATH — SEGURO).

    PATCH P0 (2026-06-19):
    Path: Clientes/{tenant_id}/Sessoes/{actor_id}

    Adicionado:
    - guard_tenant: tenant_id (validação defensiva)
    - actor_id: actor_id (rastreabilidade)
    - updated_at: timestamp
    - schema_version: 2 (para versionamento)
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório para salvar sessão")
    if not actor_id:
        raise ValueError("actor_id é obrigatório para salvar sessão")
    if not contexto:
        print(f"🚨 [BLOCK SAVE] contexto vazio bloqueado", flush=True)
        return False

    from datetime import datetime

    path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 🔥 merge manual defensivo
    atual = await buscar_dado_em_path(path) or {}
    atual.update(contexto)

    # 🔥 PATCH P0.4: Adicionar metadados de segurança
    atual["_tenant_id_guard"] = tenant_id
    atual["_actor_id"] = actor_id
    atual["_updated_at"] = datetime.now().isoformat()
    atual["_schema_version"] = 2

    print(f"[DIAG] [SAVE SESSAO v2] path={path} | tenant={tenant_id} | actor={actor_id}", flush=True)
    print(f"[SESSION_STORE] write_path={path} | tenant={tenant_id} | actor={actor_id}", flush=True)

    return await atualizar_dado_em_path(path, atual)


# ALIAS para compatibilidade (nome antigo)
async def salvar_contexto_temporario_v2(dono_id: str, cliente_id: str, contexto: dict):
    """ALIAS: Use salvar_sessao_temporaria() em novo código."""
    return await salvar_sessao_temporaria(cliente_id, contexto, dono_id)


async def carregar_sessao_temporaria(actor_id: str, tenant_id: str):
    """Carregar sessão isolada por tenant_id + actor_id (NOVO PATH — SEGURO).

    PATCH P0.3 (2026-06-19) — Read-through com migração:
    1. Tenta novo path: Clientes/{tenant_id}/Sessoes/{actor_id}
    2. Se vazio, tenta legado SOMENTE se tiver guard_tenant == tenant_id
    3. Se legado válido, migra imediatamente para novo path
    4. Se legado sem guard ou guard diferente, retorna {}

    Path novo: Clientes/{tenant_id}/Sessoes/{actor_id}
    Path legado: Clientes/{actor_id}/MemoriaTemporaria/contexto (com validação)
    """
    if not tenant_id:
        raise ValueError("tenant_id é obrigatório para carregar sessão")
    if not actor_id:
        raise ValueError("actor_id é obrigatório para carregar sessão")

    path_novo = f"Clientes/{tenant_id}/Sessoes/{actor_id}"

    # 1️⃣ Tenta novo path primeiro (PATCH P0.3: read-through)
    data_novo = await buscar_dado_em_path(path_novo)
    if data_novo:
        print(f"[DIAG] [LOAD SESSAO v2] path={path_novo} | source=novo | tenant={tenant_id} | actor={actor_id}", flush=True)
        print(f"[SESSION_STORE] read_path={path_novo} | write_path={path_novo} | same_path=True", flush=True)
        return data_novo

    # 2️⃣ Fallback legado com validação STRICT (PATCH P0.3)
    print(f"[DIAG] [LOAD SESSAO v2 FALLBACK] tentando legado para {actor_id}", flush=True)

    path_legado = f"Clientes/{actor_id}/MemoriaTemporaria/contexto"
    data_legado = await buscar_dado_em_path(path_legado)

    if not data_legado:
        print(f"🚨 [SESSAO VAZIA] path_novo={path_novo} | path_legado={path_legado}", flush=True)
        return {}

    # 3️⃣ Validar guard_tenant no legado
    guard_tenant = data_legado.get("_tenant_id_guard")

    if not guard_tenant:
        print(f"🚨 [SESSAO LEGADO SEM GUARD] RECUSADA | path={path_legado} | tenant={tenant_id}", flush=True)
        return {}

    if guard_tenant != tenant_id:
        print(f"🚨 [SESSAO LEGADO TENANT MISMATCH] RECUSADA | esperado={tenant_id} | armazenado={guard_tenant}", flush=True)
        return {}

    # 4️⃣ Legado válido — migrar para novo path imediatamente (PATCH P0.3)
    print(f"[DIAG] [SESSAO LEGADO MIGRADA] from={path_legado} to={path_novo}", flush=True)

    # Copiar para novo path com metadados
    from datetime import datetime
    data_migrada = dict(data_legado)
    data_migrada["_tenant_id_guard"] = tenant_id
    data_migrada["_actor_id"] = actor_id
    data_migrada["_updated_at"] = datetime.now().isoformat()
    data_migrada["_schema_version"] = 2
    data_migrada["_migrado_em"] = datetime.now().isoformat()

    await atualizar_dado_em_path(path_novo, data_migrada)
    print(f"[SESSION_STORE] read_path={path_legado} → migrado para write_path={path_novo} | same_path=False (mas migrado)", flush=True)

    return data_migrada


# ALIAS para compatibilidade (nome antigo)
async def carregar_contexto_temporario_v2(dono_id: str, cliente_id: str):
    """ALIAS: Use carregar_sessao_temporaria() em novo código."""
    return await carregar_sessao_temporaria(cliente_id, dono_id)


async def limpar_contexto_agendamento_v2(dono_id: str, cliente_id: str):
    """[PATCH P0] Limpeza centralizada com DELETE_FIELD.

    Limpa TODOS os campos transitórios de conversa/fluxo.
    Preserva APENAS metadados estruturais.

    Path: Clientes/{dono_id}/Sessoes/{cliente_id}
    """
    if not dono_id:
        raise ValueError("dono_id é obrigatório para limpar contexto multi-tenant")
    if not cliente_id:
        raise ValueError("cliente_id é obrigatório para limpar contexto")

    from datetime import datetime

    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    # [PATCH P0] DELETE_FIELD para TODOS os campos transitórios
    # Mantém APENAS: estado_fluxo, aguardando_confirmacao_* e metadados estruturais
    payload = {
        # [OK] METADADOS ESTRUTURAIS — preservar
        "estado_fluxo": "idle",
        "aguardando_confirmacao_agendamento": False,
        "aguardando_confirmacao_cancelamento": False,
        "ultima_acao": "contexto_limpo",
        "_updated_at": datetime.now().isoformat(),

        # [ERROR] CAMPOS TRANSITÓRIOS — DELETE_FIELD (remover completamente)
        # Fluxo de agendamento
        "draft_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_anteriores": firestore.DELETE_FIELD,
        "profissional_escolhido": firestore.DELETE_FIELD,
        "data_hora": firestore.DELETE_FIELD,
        "servico": firestore.DELETE_FIELD,
        "hora_confirmada": firestore.DELETE_FIELD,
        "evento_criado": firestore.DELETE_FIELD,

        # Fluxo de cancelamento
        "cancelamento_pendente": firestore.DELETE_FIELD,
        "evento_id_candidato_cancelamento": firestore.DELETE_FIELD,
        "candidatos_cancelamento": firestore.DELETE_FIELD,

        # Interpretação conversacional
        "interpretacao_conversacional": firestore.DELETE_FIELD,
        "intencao_conversacional": firestore.DELETE_FIELD,
        "objetivo_conversacional": firestore.DELETE_FIELD,
        "tipo_ajuste_incremental": firestore.DELETE_FIELD,
        "modo_conversa": firestore.DELETE_FIELD,

        # Escolha de horários
        "modo_escolha_horario": firestore.DELETE_FIELD,
        "horarios_sugeridos": firestore.DELETE_FIELD,
        "sugestoes": firestore.DELETE_FIELD,

        # Sugestões e alternativas
        "alternativa_profissional": firestore.DELETE_FIELD,
        "ultima_opcao_profissionais": firestore.DELETE_FIELD,

        # Histórico e consultas
        "historico_texto": firestore.DELETE_FIELD,
        "ultima_consulta": firestore.DELETE_FIELD,
        "ultima_intencao": firestore.DELETE_FIELD,

        # Questões sobre repetição
        "pergunta_amanha_mesmo_horario": firestore.DELETE_FIELD,
        "data_hora_pendente": firestore.DELETE_FIELD,
    }

    print(f"[PATCH_P0_CLEAR] path={path} | dono={dono_id} | cliente={cliente_id}", flush=True)
    print(f"[PATCH_P0_CLEAR] DELETE_FIELD count: {len([v for v in payload.values() if v is firestore.DELETE_FIELD])}", flush=True)

    return await atualizar_dado_em_path(path, payload)


# ========== VERSÃO LEGADA (DEPRECADA) — APENAS COMPATIBILIDADE ==========

async def salvar_contexto_temporario(user_id: str, contexto: dict, tenant_id: str = None):
    """DEPRECADO: Use salvar_contexto_temporario_v2(dono_id, cliente_id, contexto).

    Função legada mantida APENAS para compatibilidade com código existente.
    [WARN] NÃO isolado por tenant — pode causar contaminação multi-tenant.

    PATCH P0 (2026-06-19):
    - Se tenant_id ausente: BLOQUEAR salva, retornar False, logar crítico
    - Se tenant_id informado: salvar com guard_tenant para leitura validada
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    if not contexto:
        print(f"🚨 [BLOCK SAVE LEGADO] contexto vazio bloqueado em {path}", flush=True)
        return False

    # 🔥 PATCH P0.1: Bloquear escrita sem tenant_id
    if not tenant_id:
        stack = "".join(traceback.format_stack(limit=15))
        print(
            f"🚨 [CTX_SAVE_BLOQUEADO_SEM_TENANT] CRÍTICO | path={path} | tenant_id não fornecido, salvamento RECUSADO\n"
            f"STACK TRACE COMPLETO:\n{stack}",
            flush=True
        )
        return False

    # [DIAGNOSTICO_P0] Path legado
    print(f"[DIAG_SALVAR] path_legado={path} | tenant_id={tenant_id} | user_id={user_id}", flush=True)

    # 🔥 merge manual defensivo
    atual = await buscar_dado_em_path(path) or {}
    print(f"[DIAG_SALVAR] antes_merge: estado_fluxo={atual.get('estado_fluxo')} | cancelamento_pendente={bool(atual.get('cancelamento_pendente'))}", flush=True)

    atual.update(contexto)

    print(f"[DIAG_SALVAR] depois_merge: estado_fluxo={atual.get('estado_fluxo')} | cancelamento_pendente={bool(atual.get('cancelamento_pendente'))} | keys_atualizadas={list(contexto.keys())}", flush=True)

    # 🧬 PATCH MT-07: Registrar tenant_id para proteção defensiva
    atual["_tenant_id_guard"] = tenant_id
    print(f"[DIAG] [CTX_LEGADO_SAVE_COMPAT] path={path} | tenant_id={tenant_id} | guard_adicionado", flush=True)

    print(f"[SAVE_CTX_LEGADO] [AVISO] NAO MULTI-TENANT | path={path}", flush=True)

    resultado = await atualizar_dado_em_path(path, atual)
    print(f"[DIAG_SALVAR] resultado_save={resultado} | tipo={type(resultado)}", flush=True)
    return resultado


async def carregar_contexto_temporario(user_id: str, tenant_id: str = None):
    """DEPRECADO: Use carregar_contexto_temporario_v2(dono_id, cliente_id).

    Função legada mantida APENAS para compatibilidade com código existente.
    [WARN] NÃO isolado por tenant — pode retornar dados errados em multi-tenant.

    PATCH P0 (2026-06-19):
    - Se tenant_id ausente: BLOQUEAR leitura, retornar {}, logar crítico
    - Se tenant_id informado: validar que contexto pertence ao tenant correto
    - Se tenant mismatch: retornar {}, logar crítico
    - Se sem guard: retornar {}, logar crítico
    """
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    # [DIAGNOSTICO_P0] Rastrear carregamento
    print(f"[DIAG_CARREGAR] path_legado={path} | tenant_id={tenant_id} | user_id={user_id}", flush=True)

    data = await buscar_dado_em_path(path)

    print(f"[DIAG_CARREGAR] lido_legado: existe={bool(data)} | estado_fluxo={data.get('estado_fluxo') if data else None} | cancelamento_pendente={bool(data.get('cancelamento_pendente')) if data else None}", flush=True)

    if not data:
        print(f"[CTX VAZIO DETECTADO LEGADO] path={path}", flush=True)
        return None

    # 🔥 PATCH P0.1: Bloquear leitura sem tenant_id
    if not tenant_id:
        stack = "".join(traceback.format_stack(limit=15))
        print(
            f"🚨 [CTX_BLOQUEADO_SEM_TENANT] CRÍTICO | path={path} | tenant_id não fornecido, leitura RECUSADA\n"
            f"STACK TRACE COMPLETO:\n{stack}",
            flush=True
        )
        return {}

    # 🧬 PATCH MT-07: Validar tenant_id se informado
    guard_tenant = data.get("_tenant_id_guard")

    print(f"[DIAG_CARREGAR] guard_validacao: guard_tenant={guard_tenant} | esperado={tenant_id} | match={guard_tenant == tenant_id}", flush=True)

    # 🔥 PATCH P0.2: Bloquear se sem guard (contexto antigo/comprometido)
    if not guard_tenant:
        print(f"🚨 [CTX_LEGADO_SEM_GUARD] CRÍTICO | path={path} | contexto legado sem guard_tenant, leitura RECUSADA", flush=True)
        return {}

    # 🔥 PATCH P0.3: Bloquear se tenant mismatch
    if guard_tenant != tenant_id:
        print(f"🚨 [CTX_LEGADO_TENANT_MISMATCH] CRÍTICO | path={path} | tenant mismatch: esperado={tenant_id} | armazenado={guard_tenant}, leitura RECUSADA", flush=True)
        return {}

    # Guard bate, permitir
    print(f"[CTX_LEGADO_COMPAT] | path={path} | tenant_id={tenant_id} | guard_validado", flush=True)

    print(f"[DIAG_CARREGAR] retornando_legado: estado_fluxo={data.get('estado_fluxo')} | cancelamento_pendente={bool(data.get('cancelamento_pendente'))}", flush=True)
    print(f"[LOAD_CTX_LEGADO] [AVISO] NAO MULTI-TENANT | path={path}", flush=True)
    return data


async def limpar_contexto_agendamento(user_id: str, tenant_id: str = None):
    """[PATCH P0] Limpeza legada com DELETE_FIELD (compatibilidade).

    [WARN] DEPRECADO: Use limpar_contexto_agendamento_v2(dono_id, cliente_id).
    Mantida APENAS para compatibilidade com código existente.

    PATCH P0 (2026-06-19):
    - DELETE_FIELD para TODOS os campos transitórios
    - Validação tenant se informado
    - Bloqueia se tenant mismatch
    """
    from datetime import datetime

    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    # 🧬 PATCH MT-07: Validar tenant antes de limpar
    if tenant_id:
        atual = await buscar_dado_em_path(path) or {}
        guard_tenant = atual.get("_tenant_id_guard")
        if guard_tenant and guard_tenant != tenant_id:
            print(f"🚨 [CTX_LEGADO_CLEAR_MISMATCH] [WARN] NÃO LIMPANDO | path={path} | esperado={tenant_id} | armazenado={guard_tenant}", flush=True)
            return  # Não limpa contexto de outro tenant
        print(f"[DIAG] [CTX_LEGADO_CLEAR_COMPAT] | path={path} | tenant_id={tenant_id} | limpando com validação", flush=True)
    else:
        print(f"🚨 [CTX_LEGADO_CLEAR_SEM_TENANT] [WARN] RISCO | path={path} | tenant_id não fornecido", flush=True)

    # [PATCH P0] DELETE_FIELD para TODOS os campos transitórios
    payload = {
        # [OK] METADADOS ESTRUTURAIS — preservar
        "estado_fluxo": "idle",
        "aguardando_confirmacao_agendamento": False,
        "aguardando_confirmacao_cancelamento": False,
        "ultima_acao": "contexto_limpo",
        "_updated_at": datetime.now().isoformat(),

        # [ERROR] CAMPOS TRANSITÓRIOS — DELETE_FIELD (remover completamente)
        # Fluxo de agendamento
        "draft_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_anteriores": firestore.DELETE_FIELD,
        "profissional_escolhido": firestore.DELETE_FIELD,
        "data_hora": firestore.DELETE_FIELD,
        "servico": firestore.DELETE_FIELD,
        "hora_confirmada": firestore.DELETE_FIELD,
        "evento_criado": firestore.DELETE_FIELD,

        # Fluxo de cancelamento
        "cancelamento_pendente": firestore.DELETE_FIELD,
        "evento_id_candidato_cancelamento": firestore.DELETE_FIELD,
        "candidatos_cancelamento": firestore.DELETE_FIELD,

        # Interpretação conversacional
        "interpretacao_conversacional": firestore.DELETE_FIELD,
        "intencao_conversacional": firestore.DELETE_FIELD,
        "objetivo_conversacional": firestore.DELETE_FIELD,
        "tipo_ajuste_incremental": firestore.DELETE_FIELD,
        "modo_conversa": firestore.DELETE_FIELD,

        # Escolha de horários
        "modo_escolha_horario": firestore.DELETE_FIELD,
        "horarios_sugeridos": firestore.DELETE_FIELD,
        "sugestoes": firestore.DELETE_FIELD,

        # Sugestões e alternativas
        "alternativa_profissional": firestore.DELETE_FIELD,
        "ultima_opcao_profissionais": firestore.DELETE_FIELD,

        # Histórico e consultas
        "historico_texto": firestore.DELETE_FIELD,
        "ultima_consulta": firestore.DELETE_FIELD,
        "ultima_intencao": firestore.DELETE_FIELD,

        # Questões sobre repetição
        "pergunta_amanha_mesmo_horario": firestore.DELETE_FIELD,
        "data_hora_pendente": firestore.DELETE_FIELD,
    }

    print(f"[PATCH_P0_CLEAR] [WARN] LEGADO path={path} | user_id={user_id}", flush=True)
    print(f"[PATCH_P0_CLEAR] DELETE_FIELD count: {len([v for v in payload.values() if v is firestore.DELETE_FIELD])}", flush=True)

    return await atualizar_dado_em_path(path, payload)