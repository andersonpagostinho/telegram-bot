# services/admin_command_service.py
"""
Camada de comandos administrativos do dono — NeoEve.

Princípios:
  - 100% determinística. Sem GPT.
  - Apenas para dono (obter_id_dono(user_id) == user_id).
  - Draft único: ctx["draft"] com dominio="admin".
  - Estado: ctx["estado_fluxo"] = "aguardando_slots_admin".
  - Executor único: executar_acao_por_nome() em acao_router_handler.
  - Persistência única: acao_router_handler → cadastro_inicial_service.
  - Contexto só é limpo após confirmação de sucesso do executor.

Para adicionar novos comandos futuros:
  1. Adicionar entrada em REGISTRO_ADMIN.
  2. Adicionar handler _handle_<acao> e _continuar_<acao>.
  3. Adicionar elif em processar_comando_administrativo e _continuar_fluxo_admin.
"""
from __future__ import annotations

import re
from typing import Optional

from services.firebase_service_async import obter_id_dono
from utils.contexto_temporario import salvar_contexto_temporario
from services.cadastro_inicial_service import (
    parse_profissional_frase,
    _split_itens,
    _parse_item_servico,
)


# =========================================================
# REGISTRO DE COMANDOS ADMINISTRATIVOS
# Descreve detecção e estado — nunca persistência direta.
# =========================================================

REGISTRO_ADMIN = {
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

    Posição no router: antes da CAMADA 0 (classificador neutro).
    """
    print(f"🔧 [ADMIN] processar_comando_administrativo | texto={texto!r}", flush=True)

    # ── 1. Somente dono ───────────────────────────────────────────
    try:
        dono_id = await obter_id_dono(user_id)
    except Exception as e:
        print(f"⚠️ [ADMIN] falha ao obter dono: {e}", flush=True)
        return None

    if dono_id != user_id:
        print(
            f"🔧 [ADMIN] ignorado — user_id={user_id} não é dono (dono={dono_id})",
            flush=True,
        )
        return None

    # ── 2. Continuidade de fluxo admin já em andamento ────────────
    draft = ctx.get("draft") or {}
    if draft.get("dominio") == "admin" and draft.get("acao"):
        print(
            f"🔧 [ADMIN] continuando fluxo | acao={draft.get('acao')}",
            flush=True,
        )
        return await _continuar_fluxo_admin(texto, ctx, user_id, update, context, draft)

    # ── 3. Detectar nova intenção admin ───────────────────────────
    acao_id, nome_extraido = _detectar_intencao_admin(texto)
    if not acao_id:
        print("🔧 [ADMIN] nenhuma intenção admin detectada", flush=True)
        return None

    print(
        f"🔧 [ADMIN] intenção detectada | acao={acao_id} | nome={nome_extraido!r}",
        flush=True,
    )

    # ── 4. Delega ao handler da ação ──────────────────────────────
    if acao_id == "cadastrar_profissional":
        return await _handle_cadastrar_profissional(
            texto, ctx, user_id, update, context, nome_extraido
        )

    print(f"⚠️ [ADMIN] ação detectada sem handler: {acao_id}", flush=True)
    return None


# =========================================================
# DETECÇÃO DETERMINÍSTICA
# =========================================================

def _detectar_intencao_admin(texto: str) -> tuple[Optional[str], str]:
    """
    Varre REGISTRO_ADMIN com os padrões de cada ação.
    Retorna (acao_id, nome_extraido) ou (None, "").
    Sem GPT. Sem heurística.
    """
    t = texto.strip()
    for acao_id, cfg in REGISTRO_ADMIN.items():
        for padrao in cfg["padroes"]:
            m = re.search(padrao, t, re.IGNORECASE)
            if m:
                bruto = m.group(1).strip()
                # Separa nome do bloco de serviços se vier na mesma mensagem
                nome = re.split(
                    r"[:,]|\bfaz\b|\bservicos\b|\bserviços\b",
                    bruto,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0].strip()
                return acao_id, nome

    return None, ""


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
    """
    Retoma fluxo admin interrompido.
    Lê draft["acao"] para saber qual handler chamar.
    """
    acao = draft.get("acao")

    if acao == "cadastrar_profissional":
        nome = (draft.get("slots") or {}).get("nome", "")
        return await _continuar_cadastrar_profissional(
            texto, ctx, user_id, update, context, nome
        )

    # Draft de ação desconhecida — limpa e deixa o router lidar
    print(f"⚠️ [ADMIN] draft com ação desconhecida: {acao} — limpando", flush=True)
    ctx["draft"] = {}
    ctx["estado_fluxo"] = "idle"
    await salvar_contexto_temporario(user_id, ctx)
    return None


# =========================================================
# HANDLER: cadastrar_profissional — Etapa 1 (detecção)
# =========================================================

async def _handle_cadastrar_profissional(
    texto: str,
    ctx: dict,
    user_id: str,
    update,
    context,
    nome_extraido: str,
) -> dict:
    """
    Primeira mensagem detectada como cadastrar_profissional.
    Tenta extrair nome + serviços da mesma frase.
    Se tiver tudo → executa direto.
    Se faltar serviços → salva draft e pergunta.
    """
    nome_prof, servicos_dict = parse_profissional_frase(texto)

    # parse_profissional_frase pode não extrair o nome em frases muito simples
    nome_final = nome_prof or nome_extraido

    if not nome_final:
        await update.message.reply_text(
            "⚠️ Não consegui identificar o nome da profissional.\n"
            "Tente: *cadastrar profissional Inês: corte=50/30, escova=45/40*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    if servicos_dict:
        # Mensagem completa — executa sem multi-etapa
        print(
            f"🔧 [ADMIN] cadastrar_profissional completo na Msg 1 | "
            f"nome={nome_final} | servicos={servicos_dict}",
            flush=True,
        )
        return await _executar_cadastrar_profissional(
            ctx, user_id, update, context, nome_final, servicos_dict
        )

    # Nome sem serviços → salva draft e pergunta
    cfg = REGISTRO_ADMIN["cadastrar_profissional"]
    ctx["estado_fluxo"] = cfg["estado_aguardando"]
    ctx["draft"] = {
        "dominio": "admin",
        "acao": "cadastrar_profissional",
        "slots": {"nome": nome_final},
        "slots_faltantes": [cfg["slot_faltante"]],
    }
    await salvar_contexto_temporario(user_id, ctx)

    print(
        f"🔧 [ADMIN] cadastrar_profissional aguardando serviços | nome={nome_final}",
        flush=True,
    )
    pergunta = cfg["pergunta_slot_faltante"].format(nome=nome_final)
    await update.message.reply_text(pergunta, parse_mode="Markdown")
    return {"handled": True, "already_sent": True}


# =========================================================
# HANDLER: cadastrar_profissional — Etapa 2 (continuidade)
# =========================================================

async def _continuar_cadastrar_profissional(
    texto: str,
    ctx: dict,
    user_id: str,
    update,
    context,
    nome: str,
) -> dict:
    """
    Segunda mensagem: usuário respondeu com os serviços.
    Parse determinístico — sem GPT.
    """
    if not nome:
        # Draft corrompido — limpa e pede recomeço
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        await update.message.reply_text(
            "⚠️ Perdi o nome da profissional. Por favor, comece novamente:\n"
            "*cadastrar profissional Inês*",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    # Parse determinístico dos serviços
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

    if not servicos_dict:
        # Formato não reconhecido — repergunta sem limpar draft
        await update.message.reply_text(
            "⚠️ Não entendi os serviços. Use o formato:\n"
            "`corte=50/30, escova=45/40`\n\n"
            "_nome=preço/duração em minutos_",
            parse_mode="Markdown",
        )
        return {"handled": True, "already_sent": True}

    print(
        f"🔧 [ADMIN] cadastrar_profissional Etapa 2 | nome={nome} | servicos={servicos_dict}",
        flush=True,
    )
    return await _executar_cadastrar_profissional(
        ctx, user_id, update, context, nome, servicos_dict
    )


# =========================================================
# EXECUTOR — monta payload e chama executor único
# =========================================================

async def _executar_cadastrar_profissional(
    ctx: dict,
    user_id: str,
    update,
    context,
    nome: str,
    servicos_dict: dict,
) -> dict:
    """
    Monta payload estruturado e delega ao executor único.
    Não persiste diretamente no Firebase.

    Limpeza de contexto ocorre SOMENTE após sucesso confirmado do executor.
    Se o executor falhar, draft e estado_fluxo são preservados.
    """
    from handlers.acao_router_handler import executar_acao_por_nome

    payload = {
        "nome": nome,
        "servicos_dict": servicos_dict,
    }

    print(
        f"🔧 [ADMIN] → executar_acao_por_nome cadastrar_profissional | payload={payload}",
        flush=True,
    )

    try:
        resultado = await executar_acao_por_nome(
            update, context, "cadastrar_profissional", payload
        )

        # ── Sucesso: limpa contexto admin ─────────────────────────
        ctx["draft"] = {}
        ctx["estado_fluxo"] = "idle"
        await salvar_contexto_temporario(user_id, ctx)
        print("🔧 [ADMIN] contexto admin limpo após sucesso", flush=True)

        return resultado or {"handled": True, "already_sent": True}

    except Exception as e:
        # ── Falha: preserva draft para tentativa futura ───────────
        print(f"❌ [ADMIN] falha ao executar cadastrar_profissional: {e}", flush=True)
        await update.message.reply_text(
            "❌ Erro ao salvar a profissional. O cadastro foi preservado — "
            "tente enviar os serviços novamente."
        )
        return {"handled": True, "already_sent": True}
