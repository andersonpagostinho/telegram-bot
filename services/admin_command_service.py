# services/admin_command_service.py
"""
Camada de comandos administrativos do dono — NeoEve.

Princípios:
  - 100% determinística. Sem GPT.
  - Apenas para dono (obter_id_dono(user_id) == user_id).
  - Draft único: ctx["draft"] com dominio="admin".
  - Estado: ctx["estado_fluxo"] = "aguardando_slots_admin".
  - Executor único: executar_acao_por_nome() em acao_router_handler.
  - Persistência única: acao_router_handler → firebase.
  - Contexto só é limpo após confirmação de sucesso do executor.

Para adicionar novos comandos futuros:
  1. Adicionar entrada em REGISTRO_ADMIN (se usa padrões fixos).
  2. Adicionar _handle_<acao> e _continuar_<acao>.
  3. Adicionar elif em processar_comando_administrativo e _continuar_fluxo_admin.
"""
from __future__ import annotations

import re
from typing import Optional
from unidecode import unidecode as _ud

from services.firebase_service_async import obter_id_dono
from utils.contexto_temporario import salvar_contexto_temporario
from services.cadastro_inicial_service import (
    parse_profissional_frase,
    _split_itens,
    _parse_item_servico,
    _to_float,
    _to_int,
)


# =========================================================
# REGISTRO DE COMANDOS COM PADRÃO FIXO DE NOME
# (comandos onde o nome vem em posição previsível no texto)
# =========================================================

REGISTRO_ADMIN = {
    "excluir_profissional": {
        "padroes": [
            r"(?:excluir|remover|apagar|deletar)\s+(?:profissional\s+)?([A-ZÀ-úa-z][a-zA-ZÀ-ú\s]+?)(?:\s*$)",
        ],
    },
    "cadastrar_profissional": {
        "padroes": [
            r"(?:cadastrar|adicionar)\s+profissional\s+(.+)",
        ],
        "estado_aguardando": "aguardando_slots_admin",
        "slot_faltante": "servicos",
        "pergunta_slot_faltante": (
            "👤 Ótimo! Vou cadastrar *{nome}*.\n\n"
            "Quais serviços ela oferece? Me informe com preço e duração:\n"
            "`corte=50/30, escova=45/40`\n\n"
            "_formato: nome=preço/duração em minutos_"
        ),
    },
}

# Confirmações aceitas para excluir
_CONFIRMACOES = {"sim", "s", "yes", "confirmar", "confirmo", "pode", "claro", "com certeza", "pode sim"}
_NEGACOES     = {"nao", "não", "n", "no", "cancelar", "cancela", "nao quero", "não quero", "desistir"}


# =========================================================
# ENTRY POINT — chamado pelo principal_router.py
# =========================================================

async def processar_comando_administrativo(
    texto: str,
    ctx: dict,
    user_id: str,
    update,
    context,
) -> Optional[dict]:
    """
    Retorna resposta do router (dict com handled=True) ou None.
    None → não é comando admin → router continua normalmente.
    """
    print(f"🔧 [ADMIN] entrada | texto={texto!r}", flush=True)

    # ── 1. Somente dono ───────────────────────────────────────────
    try:
        dono_id = await obter_id_dono(user_id)
    except Exception as e:
        print(f"⚠️ [ADMIN] falha ao obter dono: {e}", flush=True)
        return None

    if dono_id != user_id:
        return None   # cliente final — ignora silenciosamente

    # ── 2. Continuidade de fluxo admin em andamento ───────────────
    draft = ctx.get("draft") or {}
    if draft.get("dominio") == "admin" and draft.get("acao"):
        print(f"🔧 [ADMIN] continuando fluxo | acao={draft.get('acao')}", flush=True)
        return await _continuar_fluxo_admin(texto, ctx, user_id, update, context, draft)

    # ── 3. Detectar nova intenção admin ───────────────────────────
    acao_id, nome_extraido = _detectar_intencao_admin(texto)
    if not acao_id:
        print("🔧 [ADMIN] nenhuma intenção admin detectada", flush=True)
        return None

    print(f"🔧 [ADMIN] intenção detectada | acao={acao_id} | nome={nome_extraido!r}", flush=True)

    # ── 4. Delega ao handler correto ──────────────────────────────
    if acao_id == "cadastrar_profissional":
        return await _handle_cadastrar_profissional(
            texto, ctx, user_id, update, context, nome_extraido
        )
    if acao_id == "adicionar_servico_profissional":
        return await _handle_adicionar_servico_profissional(
            texto, ctx, user_id, update, context
        )
    if acao_id == "excluir_profissional":
        return await _handle_excluir_profissional(
            ctx, user_id, update, context, nome_extraido
        )

    print(f"⚠️ [ADMIN] ação sem handler: {acao_id}", flush=True)
    return None


# =========================================================
# DETECÇÃO DETERMINÍSTICA
# =========================================================

def _detectar_intencao_admin(texto: str) -> tuple[Optional[str], str]:
    """
    1. Tenta REGISTRO_ADMIN (padrões fixos, extrai grupo 1 como nome).
       Ordem importante: excluir antes de cadastrar.
    2. Se não encontrou, testa intenção de adicionar serviço (intent-based).
    Retorna (acao_id, nome_extraido) ou (None, "").
    """
    t = texto.strip()

    # Padrões fixos
    for acao_id, cfg in REGISTRO_ADMIN.items():
        for padrao in cfg.get("padroes", []):
            m = re.search(padrao, t, re.IGNORECASE)
            if m:
                bruto = m.group(1).strip()
                if acao_id == "cadastrar_profissional":
                    # separa nome do bloco de serviços opcional
                    nome = re.split(
                        r"[:,]|\bfaz\b|\bservicos\b|\bserviços\b",
                        bruto, maxsplit=1, flags=re.IGNORECASE,
                    )[0].strip()
                else:
                    nome = bruto
                return acao_id, nome

    # Intent-based: adicionar serviço a profissional existente
    if _eh_intencao_adicionar_servico(texto):
        return "adicionar_servico_profissional", ""

    return None, ""


def _eh_intencao_adicionar_servico(texto: str) -> bool:
    """
    Detecta padrões livres como:
      "agora Carla também faz luzes"
      "inclui luzes para Carla"
      "coloca luzes na Carla"
      "Carla passou a fazer luzes"
    Sem inferir nomes — apenas a presença dos verbos/estruturas.
    """
    t = _ud(texto.lower().strip())

    # "X também faz Y" / "X agora faz Y" / "X agora também faz Y"
    if re.search(r"\b(?:tambem|agora)\s+(?:tambem\s+)?(?:faz|atende|vai\s+fazer)\b", t):
        return True

    # "inclui/adiciona/coloca Y para/na/no X"
    if re.search(r"\b(?:inclui|adiciona|coloca)\b.+\b(?:para|na|no|em|pra)\b", t):
        return True

    # "passou a fazer/atender"
    if re.search(r"\bpassou\s+a\s+(?:fazer|atender)\b", t):
        return True

    return False


# =========================================================
# CONTINUIDADE DE FLUXO MULTI-ETAPA
# =========================================================

async def _continuar_fluxo_admin(
    texto: str,
    ctx: dict,
    user_id: str,
    update,
    context,
    draft: dict,
) -> Optional[dict]:
    acao = draft.get("acao")
    slots = draft.get("slots") or {}

    if acao == "cadastrar_profissional":
        return await _continuar_cadastrar_profissional(
            texto, ctx, user_id, update, context, slots.get("nome", "")
        )

    if acao == "adicionar_servico_profissional":
        return await _continuar_adicionar_servico_profissional(
            texto, ctx, user_id, update, context, slots
        )

    if acao == "excluir_profissional":
        return await _continuar_excluir_profissional(
            texto, ctx, user_id, update, context, slots
        )

    # Ação desconhecida no draft — limpa
    print(f"⚠️ [ADMIN] draft com ação desconhecida: {acao} — limpando", flush=True)
    ctx["draft"] = {}
    ctx["estado_fluxo"] = "idle"
    await salvar_contexto_temporario(user_id, ctx)
    return None


# =========================================================
# ── AÇÃO 1: cadastrar_profissional ───────────────────────
# =========================================================

async def _handle_cadastrar_profissional(
    texto: str,
    ctx: dict,
    user_id: str,
    update,
    context,
    nome_extraido: str,
) -> dict:
    nome_prof, servicos_dict = parse_profissional_frase(texto)
    nome_final = nome_prof or nome_extraido

    if not nome_final:
        await update.message.reply_text(
            "⚠️ Não consegui identificar o nome da profissional.\n"
            "Tente: *cadastrar profissional Inês: corte=50/30, escova=45/40*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    if servicos_dict:
        print(f"🔧 [ADMIN] cadastrar_profissional completo | nome={nome_final}", flush=True)
        return await _executar_cadastrar_profissional(
            ctx, user_id, update, context, nome_final, servicos_dict
        )

    # Nome encontrado, serviços ausentes → salva draft e pergunta
    cfg = REGISTRO_ADMIN["cadastrar_profissional"]
    ctx["estado_fluxo"] = cfg["estado_aguardando"]
    ctx["draft"] = {
        "dominio": "admin",
        "acao": "cadastrar_profissional",
        "slots": {"nome": nome_final},
        "slots_faltantes": [cfg["slot_faltante"]],
    }
    await salvar_contexto_temporario(user_id, ctx)

    print(f"🔧 [ADMIN] cadastrar_profissional aguardando serviços | nome={nome_final}", flush=True)
    await update.message.reply_text(
        cfg["pergunta_slot_faltante"].format(nome=nome_final),
        parse_mode="Markdown",
    )
    return {"handled": True, "already_sent": True}


async def _continuar_cadastrar_profissional(
    texto: str, ctx: dict, user_id: str, update, context, nome: str
) -> dict:
    if not nome:
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        await update.message.reply_text(
            "⚠️ Perdi o nome da profissional. Comece novamente:\n*cadastrar profissional Inês*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    servicos_dict = _parse_servicos_de_texto(texto)

    if not servicos_dict:
        await update.message.reply_text(
            "⚠️ Não entendi os serviços. Use o formato:\n"
            "`corte=50/30, escova=45/40`\n\n_nome=preço/duração em minutos_",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    print(f"🔧 [ADMIN] cadastrar_profissional Etapa 2 | nome={nome} | servicos={servicos_dict}", flush=True)
    return await _executar_cadastrar_profissional(ctx, user_id, update, context, nome, servicos_dict)


async def _executar_cadastrar_profissional(
    ctx: dict, user_id: str, update, context, nome: str, servicos_dict: dict
) -> dict:
    from handlers.acao_router_handler import executar_acao_por_nome

    payload = {"nome": nome, "servicos_dict": servicos_dict}
    print(f"🔧 [ADMIN] → executar cadastrar_profissional | payload={payload}", flush=True)

    try:
        resultado = await executar_acao_por_nome(
            update, context, "cadastrar_profissional", payload
        )
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        print("🔧 [ADMIN] contexto limpo após sucesso", flush=True)
        return resultado or {"handled": True, "already_sent": True}

    except Exception as e:
        print(f"❌ [ADMIN] falha em cadastrar_profissional: {e}", flush=True)
        await update.message.reply_text(
            "❌ Erro ao salvar a profissional. Draft preservado — tente enviar os serviços novamente."
        )
        return {"handled": True, "already_sent": True}


# =========================================================
# ── AÇÃO 2: adicionar_servico_profissional ────────────────
# =========================================================

async def _handle_adicionar_servico_profissional(
    texto: str,
    ctx: dict,
    user_id: str,
    update,
    context,
) -> dict:
    from services.firebase_service_async import buscar_subcolecao

    # Carrega profissionais conhecidas para validar o nome no texto
    profs = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    if not profs:
        await update.message.reply_text(
            "⚠️ Não há profissionais cadastradas ainda.\n"
            "Cadastre primeiro: *cadastrar profissional Carla: corte=50/30*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # Mapa nome_normalizado → nome_real
    nomes_map = {
        _ud(v.get("nome", k).lower()): v.get("nome", k)
        for k, v in profs.items()
    }

    # Busca profissional no texto
    t_norm = _ud(texto.lower())
    prof_encontrada = None
    for nome_norm, nome_real in nomes_map.items():
        if nome_norm and nome_norm in t_norm:
            prof_encontrada = nome_real
            break

    if not prof_encontrada:
        lista = ", ".join(v.get("nome", k) for k, v in profs.items())
        await update.message.reply_text(
            f"⚠️ Não reconheci a profissional na mensagem.\n"
            f"Profissionais cadastradas: *{lista}*\n\n"
            "Tente: *Carla também faz luzes*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # Extrai nome do serviço
    servico_extraido = _extrair_nome_servico(texto, prof_encontrada)

    if not servico_extraido:
        await update.message.reply_text(
            f"⚠️ Não consegui identificar o serviço para *{prof_encontrada}*.\n"
            "Tente: *Carla também faz luzes*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # Salva draft e pergunta preço/duração
    ctx["estado_fluxo"] = "aguardando_slots_admin"
    ctx["draft"] = {
        "dominio": "admin",
        "acao": "adicionar_servico_profissional",
        "slots": {
            "nome": prof_encontrada,
            "servico": servico_extraido,
        },
        "slots_faltantes": ["preco_duracao"],
    }
    await salvar_contexto_temporario(user_id, ctx)

    print(
        f"🔧 [ADMIN] adicionar_servico_profissional aguardando preço/duração | "
        f"prof={prof_encontrada} | servico={servico_extraido}",
        flush=True,
    )
    await update.message.reply_text(
        f"💇 Ótimo! Qual o preço e duração de *{servico_extraido}* com *{prof_encontrada}*?\n\n"
        f"Exemplo: `{servico_extraido}=120/90`\n\n"
        "_formato: preço/duração em minutos_",
        parse_mode="Markdown",
    )
    return {"handled": True, "already_sent": True}


async def _continuar_adicionar_servico_profissional(
    texto: str, ctx: dict, user_id: str, update, context, slots: dict
) -> dict:
    nome = slots.get("nome", "")
    servico = slots.get("servico", "")

    if not nome or not servico:
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        await update.message.reply_text(
            "⚠️ Perdi os dados. Por favor, comece novamente.\n"
            "Ex: *Carla também faz luzes*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    preco, dur = _parse_preco_duracao(texto, servico)

    # P0: preço E duração são obrigatórios — repergunta mantendo draft intacto
    if preco is None or dur is None:
        motivo = ""
        if preco is None and dur is None:
            motivo = "Não entendi o preço nem a duração."
        elif preco is None:
            motivo = "Não entendi o preço."
        else:
            motivo = "Não entendi a duração."

        await update.message.reply_text(
            f"⚠️ {motivo}\n\n"
            f"Informe preço *e* duração de *{servico}*:\n"
            f"`{servico}=120/90`\n\n_formato: preço/duração em minutos_",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    chave = servico.strip().lower()
    servicos_dict = {chave: {"preco": float(preco), "duracao": int(dur)}}

    print(
        f"🔧 [ADMIN] adicionar_servico_profissional Etapa 2 | "
        f"nome={nome} | servico={chave} | servicos_dict={servicos_dict}",
        flush=True,
    )
    return await _executar_adicionar_servico_profissional(
        ctx, user_id, update, context, nome, servicos_dict
    )


async def _executar_adicionar_servico_profissional(
    ctx: dict, user_id: str, update, context, nome: str, servicos_dict: dict
) -> dict:
    from handlers.acao_router_handler import executar_acao_por_nome

    payload = {"nome": nome, "servicos_dict": servicos_dict}
    print(f"🔧 [ADMIN] → executar adicionar_servico_profissional | payload={payload}", flush=True)

    try:
        resultado = await executar_acao_por_nome(
            update, context, "adicionar_servico_profissional", payload
        )
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        print("🔧 [ADMIN] contexto limpo após sucesso", flush=True)
        return resultado or {"handled": True, "already_sent": True}

    except Exception as e:
        print(f"❌ [ADMIN] falha em adicionar_servico_profissional: {e}", flush=True)
        await update.message.reply_text(
            "❌ Erro ao adicionar o serviço. Draft preservado — tente novamente."
        )
        return {"handled": True, "already_sent": True}


# =========================================================
# ── AÇÃO 3: excluir_profissional ─────────────────────────
# =========================================================

async def _handle_excluir_profissional(
    ctx: dict,
    user_id: str,
    update,
    context,
    nome_extraido: str,
) -> dict:
    from services.firebase_service_async import buscar_dado_em_path

    nome_fmt = nome_extraido.strip().title()
    if not nome_fmt:
        await update.message.reply_text(
            "⚠️ Não consegui identificar o nome da profissional.\n"
            "Tente: *excluir profissional Bruna*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # ── Confirma existência ───────────────────────────────────
    path = f"Clientes/{user_id}/Profissionais/{nome_fmt}"
    prof = await buscar_dado_em_path(path)
    if not prof:
        await update.message.reply_text(
            f"⚠️ Não encontrei *{nome_fmt}* no cadastro de profissionais.",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # ── Bloqueia se houver eventos futuros vinculados ─────────
    eventos_futuros = await _buscar_eventos_futuros_profissional(user_id, nome_fmt)
    if eventos_futuros:
        linhas = []
        for ev in eventos_futuros[:5]:   # exibe até 5 para não sobrecarregar
            data = ev.get("data", "?")
            hora = ev.get("hora_inicio", "?")
            desc = ev.get("descricao") or "Agendamento"
            linhas.append(f"• {desc} — {data} às {hora}")
        lista = "\n".join(linhas)
        total = len(eventos_futuros)
        sufixo = f"\n_...e mais {total - 5} agendamentos._" if total > 5 else ""
        await update.message.reply_text(
            f"⛔ Não é possível excluir *{nome_fmt}* pois há *{total}* agendamento(s) futuro(s) vinculado(s):\n\n"
            f"{lista}{sufixo}\n\n"
            "Cancele ou transfira os agendamentos antes de excluir a profissional.",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # ── Salva draft e pede confirmação ───────────────────────
    ctx["estado_fluxo"] = "aguardando_slots_admin"
    ctx["draft"] = {
        "dominio": "admin",
        "acao": "excluir_profissional",
        "slots": {"nome": nome_fmt},
        "aguardando_confirmacao": True,
    }
    await salvar_contexto_temporario(user_id, ctx)

    print(f"🔧 [ADMIN] excluir_profissional aguardando confirmação | nome={nome_fmt}", flush=True)
    await update.message.reply_text(
        f"⚠️ Tem certeza que deseja excluir *{nome_fmt}*?\n\n"
        "Responda *sim* para confirmar ou *não* para cancelar.",
        parse_mode="Markdown",
    )
    return {"handled": True, "already_sent": True}


async def _continuar_excluir_profissional(
    texto: str, ctx: dict, user_id: str, update, context, slots: dict
) -> dict:
    nome = slots.get("nome", "")
    t = _ud(texto.strip().lower())

    if t in _CONFIRMACOES:
        print(f"🔧 [ADMIN] excluir_profissional confirmado | nome={nome}", flush=True)
        return await _executar_excluir_profissional(ctx, user_id, update, context, nome)

    if t in _NEGACOES:
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        await update.message.reply_text(
            f"Tudo bem, *{nome}* não foi removida.",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # Resposta não reconhecida — repergunta sem limpar draft
    await update.message.reply_text(
        f"Não entendi. Deseja excluir *{nome}*?\n"
        "Responda *sim* ou *não*.",
        parse_mode="Markdown",
    )
    return {"handled": True, "already_sent": True}


async def _executar_excluir_profissional(
    ctx: dict, user_id: str, update, context, nome: str
) -> dict:
    from handlers.acao_router_handler import executar_acao_por_nome

    payload = {"nome": nome}
    print(f"🔧 [ADMIN] → executar excluir_profissional | payload={payload}", flush=True)

    try:
        resultado = await executar_acao_por_nome(
            update, context, "excluir_profissional", payload
        )
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        print("🔧 [ADMIN] contexto limpo após excluir", flush=True)
        return resultado or {"handled": True, "already_sent": True}

    except Exception as e:
        print(f"❌ [ADMIN] falha em excluir_profissional: {e}", flush=True)
        await update.message.reply_text(
            "❌ Erro ao excluir a profissional. Draft preservado — tente novamente."
        )
        return {"handled": True, "already_sent": True}


# =========================================================
# HELPERS DE PARSING
# =========================================================

def _parse_servicos_de_texto(texto: str) -> dict:
    """
    Parse determinístico de "corte=50/30, escova=45/40".
    Retorna dict {chave: {preco, duracao}} ou {} se não parseou.
    """
    servicos_dict: dict = {}
    itens = _split_itens(texto)
    for it in itens:
        nome_item, preco, dur = _parse_item_servico(it)
        if not nome_item:
            continue
        chave = nome_item.strip().lower()
        servicos_dict[chave] = {}
        if preco is not None:
            servicos_dict[chave]["preco"] = float(preco)
        if dur is not None:
            servicos_dict[chave]["duracao"] = int(dur)
    return servicos_dict


def _extrair_nome_servico(texto: str, nome_prof: str) -> str:
    """
    Extrai o nome do serviço de frases como:
      "Carla também faz luzes"        → "luzes"
      "inclui luzes para Carla"       → "luzes"
      "coloca luzes na Carla"         → "luzes"
      "Carla passou a fazer botox"    → "botox"
    """
    # Remove nome da profissional do texto para isolar o serviço
    t_sem_prof = re.sub(re.escape(nome_prof), "", texto, flags=re.IGNORECASE).strip()

    # Padrão A: "... faz/atende/vai fazer/passou a fazer [serviço]"
    m = re.search(
        r"\b(?:faz|atende|vai\s+fazer|passou\s+a\s+(?:fazer|atender))\s+([a-zA-ZÀ-ú][a-zA-ZÀ-ú\s]*?)(?:\s*$|\s+(?:para|na|no|em)\b)",
        t_sem_prof,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().lower()

    # Padrão B: "inclui/adiciona/coloca [serviço] para/na ..."
    m = re.search(
        r"\b(?:inclui|adiciona|coloca)\s+([a-zA-ZÀ-ú][a-zA-ZÀ-ú\s]*?)\s+(?:para|na|no|em|pra)\b",
        texto,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().lower()

    return ""


def _parse_preco_duracao(texto: str, nome_servico: str) -> tuple[Optional[float], Optional[int]]:
    """
    Parseia preço e duração da resposta do usuário.
    Aceita:
      "luzes=120/90"   → (120.0, 90)
      "120/90"         → (120.0, 90)
      "120 90"         → (120.0, 90)
      "120"            → (120.0, None)

    Ordem:
      1. Se texto já contém "=" → parse direto (ex: "luzes=120/90")
      2. Sem "=" → prepend nome + "=" para reutilizar o parser
         (ex: "120/90" → "luzes=120/90"; "120 90" → "luzes=120 90")
      3. Fallback raw: "NNN/NNN" ou só "NNN"
    """
    t = texto.strip()

    # 1. Formato explícito com "=" já presente
    if "=" in t:
        _, preco, dur = _parse_item_servico(t)
        if preco is not None or dur is not None:
            return preco, dur

    # 2. Sem "=" → prepend nome para usar o parser existente
    #    "120/90" → "luzes=120/90"  → match no 1º padrão → (120.0, 90) ✓
    #    "120 90" → "luzes=120 90"  → match no 1º padrão → (120.0, 90) ✓
    _, preco2, dur2 = _parse_item_servico(f"{nome_servico}={t}")
    if preco2 is not None or dur2 is not None:
        return preco2, dur2

    # 3. Raw "NNN/NNN" — segurança extra
    m = re.match(r"^(\d+(?:[.,]\d+)?)\s*/\s*(\d+)", t)
    if m:
        return _to_float(m.group(1)), _to_int(m.group(2))

    # 4. Só preço "NNN"
    m = re.match(r"^(\d+(?:[.,]\d+)?)$", t)
    if m:
        return _to_float(m.group(1)), None

    return None, None


async def _buscar_eventos_futuros_profissional(user_id: str, nome_fmt: str) -> list:
    """
    Retorna lista de eventos futuros (data >= hoje) vinculados à profissional.
    Ignora eventos cancelados/removidos.
    Usa comparação com unidecode para lidar com acentos.
    """
    from datetime import date
    from services.firebase_service_async import buscar_subcolecao

    hoje = date.today().isoformat()
    nome_norm = _ud(nome_fmt.lower())
    status_cancelados = {"cancelado", "cancelada", "removido", "removida", "excluido", "excluído"}

    try:
        eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
    except Exception as e:
        print(f"⚠️ [ADMIN] erro ao buscar eventos para excluir_profissional: {e}", flush=True)
        return []

    futuros = []
    for ev in eventos.values():
        if not isinstance(ev, dict):
            continue
        status = (ev.get("status") or "").strip().lower()
        if status in status_cancelados:
            continue
        data_ev = ev.get("data") or ""
        if data_ev < hoje:          # passado ou sem data
            continue
        prof_ev = _ud((ev.get("profissional") or "").strip().lower())
        if prof_ev == nome_norm:
            futuros.append(ev)

    # Ordena por data/hora
    futuros.sort(key=lambda e: (e.get("data", ""), e.get("hora_inicio", "")))
    return futuros
