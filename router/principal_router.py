# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario
from utils.context_manager import atualizar_contexto  # apenas histórico user/bot
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from datetime import datetime, timedelta
from utils.interpretador_datas import interpretar_data_e_hora
import pytz
import re
from unidecode import unidecode


# ----------------------------
# Helpers de NLP simples
# ----------------------------

def eh_consulta(txt: str) -> bool:
    """
    Heurística: detectar mensagens de consulta de agenda/disponibilidade.
    Consulta NUNCA deve agendar.
    """
    t = (txt or "").strip().lower()
    consultas = [
        "como está", "como esta", "agenda",
        "disponível", "disponivel",
        "tem horário", "tem horario",
        "livre", "ocupado", "ocupada",
        "consulta", "consultar",
        "disponibilidade",
    ]
    return any(c in t for c in consultas)


def eh_gatilho_agendar(txt: str) -> bool:
    """
    Gatilho explícito de agendar (decisão final do usuário).
    """
    t = (txt or "").strip().lower()
    gatilhos = ["pode agendar", "pode marcar", "agende", "marque"]
    return any(g in t for g in gatilhos)


def normalizar(texto: str) -> str:
    return unidecode((texto or "").strip().lower())


def formatar_data_hora_br(dt_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_iso)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(dt_iso)


def extrair_servico_do_texto(texto_usuario: str, servicos_disponiveis: list) -> str | None:
    """
    Tenta mapear o texto do usuário para um serviço existente.
    - match por inclusão normalizada (robusto para "corte", "escova", etc.)
    """
    if not servicos_disponiveis:
        return None

    txt = normalizar(texto_usuario)
    if not txt:
        return None

    for s in servicos_disponiveis:
        s_norm = normalizar(str(s))
        if s_norm and s_norm in txt:
            return str(s).strip()

    if len(txt.split()) <= 2:
        for s in servicos_disponiveis:
            if normalizar(str(s)) == txt:
                return str(s).strip()

    return None


def _tem_indicio_de_hora(txt: str) -> bool:
    """
    Evita que interpretar_data_e_hora chute 'amanhã' sem hora.
    Só tenta extrair dt quando houver indício de horário.
    """
    t = (txt or "").lower()
    # 16, 16h, 16:30, às 16, 16 horas
    return bool(re.search(r"\b\d{1,2}(:\d{2})?\b", t) or re.search(r"\b\d{1,2}\s*h\b", t) or "às" in t or "as " in t)


async def extrair_slots_e_mesclar(ctx: dict, texto_usuario: str, dono_id: str) -> dict:
    """
    Sempre-on: extrai e mescla slots em ctx + draft_agendamento sem apagar o que já existe.
    - profissional: por match em nomes do Firebase
    - servico: por match em catálogo (preferindo o profissional detectado se houver)
    - data_hora: só tenta quando há indício de horário (evita chute)
    """
    texto = (texto_usuario or "").strip()
    tnorm = normalizar(texto)
    draft = ctx.get("draft_agendamento") or {}

    # ---------------- data/hora ----------------
    if not (draft.get("data_hora") or ctx.get("data_hora")):
        if _tem_indicio_de_hora(texto):
            dt = interpretar_data_e_hora(texto)  # texto original
            if dt:
                iso = dt.replace(second=0, microsecond=0).isoformat()
                ctx["data_hora"] = iso
                draft["data_hora"] = draft.get("data_hora") or iso

                if not isinstance(ctx.get("ultima_consulta"), dict):
                    ctx["ultima_consulta"] = {}
                ctx["ultima_consulta"]["data_hora"] = iso

    # ---------------- profissionais (sempre) ----------------
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]

    prof_detectado = None
    for nome in nomes_profs:
        if normalizar(nome) in tnorm:
            prof_detectado = nome
            break

    if prof_detectado:
        ctx["profissional_escolhido"] = prof_detectado
        draft["profissional"] = draft.get("profissional") or prof_detectado
        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["profissional"] = prof_detectado

    # ---------------- serviço (sempre) ----------------
    # 1) tenta por serviços do profissional detectado
    servico_detectado = None

    def _match_servico(lista_servs):
        nonlocal servico_detectado
        for s in lista_servs or []:
            s_norm = normalizar(str(s))
            if s_norm and s_norm in tnorm:
                servico_detectado = str(s).strip()
                return True
        return False

    if prof_detectado:
        for p in profs_dict.values():
            if normalizar(p.get("nome", "")) == normalizar(prof_detectado):
                _match_servico(p.get("servicos") or [])
                break

    # 2) fallback: catálogo global
    if not servico_detectado:
        todos = []
        for p in profs_dict.values():
            todos.extend(p.get("servicos") or [])
        # de-dupe mantendo ordem
        vistos = set()
        uniq = []
        for s in todos:
            s2 = str(s).strip()
            if s2 and s2 not in vistos:
                vistos.add(s2)
                uniq.append(s2)
        _match_servico(uniq)

    if servico_detectado:
        ctx["servico"] = servico_detectado
        draft["servico"] = draft.get("servico") or servico_detectado

    if draft:
        ctx["draft_agendamento"] = draft

    return ctx


# ----------------------------
# Router principal
# ----------------------------

async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")

    # ✅ 1) consulta informativa antes de tudo (serviços/preços/perguntas comuns)
    from services.informacao_service import responder_consulta_informativa

    resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
    if resposta_informativa:
        print("🔍 Consulta informativa detectada. Respondendo diretamente.")
        if context is not None:
            await context.bot.send_message(
                chat_id=user_id,
                text=resposta_informativa,
                parse_mode="Markdown",
            )
        return resposta_informativa

    # 🔐 dono do negócio
    dono_id = await obter_id_dono(user_id)

    # ✅ Intercept determinístico: "quem/quais você tem" (não cai no GPT)
    tinfo = normalizar(mensagem)
    if any(x in tinfo for x in ["quais voce tem", "quais você tem", "quem voce tem", "quem você tem", "quais profissionais", "quem atende", "quem faz", "quais serviços", "quais servicos"]):
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        if not profs_dict:
            if context is not None:
                await context.bot.send_message(chat_id=user_id, text="Ainda não há profissionais cadastrados.", parse_mode="Markdown")
            return {"acao": None, "handled": True}

        nomes = []
        servicos = set()
        for p in profs_dict.values():
            nome = (p.get("nome") or "").strip()
            if nome:
                nomes.append(nome)
            for s in (p.get("servicos") or []):
                if s:
                    servicos.add(str(s).strip())

        txt = "*Profissionais:*\n- " + "\n- ".join(sorted(set(nomes)))
        if servicos:
            txt += "\n\n*Serviços:*\n- " + "\n- ".join(sorted(servicos))

        if context is not None:
            await context.bot.send_message(chat_id=user_id, text=txt, parse_mode="Markdown")
        return {"acao": None, "handled": True}

    # 🔄 sessão ativa (fluxos do seu gpt_service)
    sessao = await pegar_sessao(user_id)
    if sessao and sessao.get("estado"):
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_fluxo})
        return resposta_fluxo

    # =========================================================
    # ✅ Estado único do fluxo (estado_fluxo)
    # =========================================================
    texto_usuario = (mensagem or "").strip()
    texto_lower = texto_usuario.lower().strip()

    ctx = await carregar_contexto_temporario(user_id) or {}
    estado_fluxo = (ctx.get("estado_fluxo") or "idle").strip().lower()
    draft = ctx.get("draft_agendamento") or {}

    FUSO_BR = pytz.timezone("America/Sao_Paulo")

    def _agora_br_naive():
        return datetime.now(FUSO_BR).replace(tzinfo=None)

    def _dt_from_iso_naive(iso_str: str):
        try:
            return datetime.fromisoformat(iso_str)
        except Exception:
            return None

    async def _perguntar_amanha_mesmo_horario_e_bloquear(data_hora_iso: str):
        """
        Centraliza o bloqueio de data passada e prepara captura de confirmação.
        """
        if context is not None:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou hoje.\n"
                    "Você quer *amanhã no mesmo horário* ou prefere outro horário?"
                ),
                parse_mode="Markdown",
            )

        ctx["estado_fluxo"] = "aguardando_data"
        ctx["pergunta_amanha_mesmo_horario"] = True
        ctx["data_hora_pendente"] = data_hora_iso
        ctx["data_hora"] = None
        ctx["draft_agendamento"] = ctx.get("draft_agendamento")  # não destrói draft; só invalida data no passado

        if isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"]["data_hora"] = None

        await salvar_contexto_temporario(user_id, ctx)
        return {"acao": None, "handled": True}

    # =========================================================
    # ✅ CONFIRMAÇÃO NO MODO "consultando" -> vira coleta de serviço
    # =========================================================
    def eh_confirmacao(txt: str) -> bool:
        t = (txt or "").strip().lower()

        if "nao" in t or "não" in t:
            return False

        gatilhos = [
            "confirmar", "confirma", "pode agendar", "pode marcar", "agende", "marque",
            "fechar", "ok", "confirmado",
            "sim", "sim por favor", "pode", "pode ser", "pode sim"
        ]
        return any(g in t for g in gatilhos)

    # =========================================================
    # ✅ FIX: Capturar "sim/amanhã então" para "amanhã no mesmo horário"
    # =========================================================
    if ctx.get("pergunta_amanha_mesmo_horario") and (
        eh_confirmacao(texto_lower) or "amanha" in texto_lower or "amanhã" in texto_lower
    ):
        base_iso = ctx.get("data_hora_pendente") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        if not base_iso:
            ctx["estado_fluxo"] = "aguardando_data"
            await salvar_contexto_temporario(user_id, ctx)
            if context is not None:
                await context.bot.send_message(chat_id=user_id, text="Certo — amanhã em qual horário?", parse_mode="Markdown")
            return {"acao": None, "handled": True}

        base_dt = _dt_from_iso_naive(base_iso) if base_iso else None

        if base_dt:
            nova_dt = base_dt + timedelta(days=1)
            nova_iso = nova_dt.replace(second=0, microsecond=0).isoformat()

            ctx["data_hora"] = nova_iso
            ctx["data_hora_pendente"] = None
            ctx["pergunta_amanha_mesmo_horario"] = False

            if not isinstance(ctx.get("ultima_consulta"), dict):
                ctx["ultima_consulta"] = {}
            ctx["ultima_consulta"]["data_hora"] = nova_iso

            draft = ctx.get("draft_agendamento") or {}
            prof = draft.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
            servico = draft.get("servico") or ctx.get("servico")

            if prof and servico:
                ctx["estado_fluxo"] = "aguardando_confirmacao"
                ctx["draft_agendamento"] = {"profissional": prof, "data_hora": nova_iso, "servico": servico, "modo_prechecagem": bool(draft.get("modo_prechecagem"))}
                await salvar_contexto_temporario(user_id, ctx)

                dh_fmt = formatar_data_hora_br(nova_iso)
                if context is not None:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Perfeito. Quer que eu *agende* *{servico}* com *{prof}* em *{dh_fmt}*?\n"
                            "Responda: *confirmar* / *pode marcar*."
                        ),
                        parse_mode="Markdown",
                    )
                return {"acao": None, "handled": True}

            sugestao = ""
            if prof:
                profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
                servs = []
                for p in profs_dict.values():
                    if normalizar(p.get("nome", "")) == normalizar(prof):
                        servs = p.get("servicos") or []
                        break
                if servs:
                    sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": nova_iso, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)

            dh_fmt = formatar_data_hora_br(nova_iso)
            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Fechado — *{dh_fmt}*. Qual serviço vai ser?{sugestao}",
                    parse_mode="Markdown",
                )
            return {"acao": None, "handled": True}

    # =========================================================
    # ✅ SEMPRE-ON: extrair e mesclar slots (prof/serv/dt) antes do resto
    # (mas depois do bloco "amanhã mesmo horário" para não conflitar)
    # =========================================================
    try:
        ctx = await extrair_slots_e_mesclar(ctx, texto_usuario, dono_id)
        await salvar_contexto_temporario(user_id, ctx)
        # recarrega estado/draft caso tenha mudado
        estado_fluxo = (ctx.get("estado_fluxo") or estado_fluxo or "idle").strip().lower()
        draft = ctx.get("draft_agendamento") or {}
    except Exception as e:
        print("⚠️ [slots] Falha ao extrair/mesclar slots:", e, flush=True)

    # ✅ EXTRAÇÃO DE DATA/HORA ANTES DO GPT (CRÍTICO) — mantém seu comportamento original
    #    - Só tenta quando estamos em estados onde faz sentido
    #    - Usa texto original
    # =========================================================
    if estado_fluxo in ("idle", "consultando", "aguardando_data") and not ctx.get("data_hora"):
        dt = interpretar_data_e_hora(texto_usuario)  # texto original
        if dt:
            ctx["data_hora"] = dt.replace(second=0, microsecond=0).isoformat()
            if not isinstance(ctx.get("ultima_consulta"), dict):
                ctx["ultima_consulta"] = {}
            ctx["ultima_consulta"]["data_hora"] = ctx["data_hora"]

            await salvar_contexto_temporario(user_id, ctx)
            print("🕓 [ROUTER] data_hora extraída:", ctx["data_hora"], flush=True)

            dt_naive = _dt_from_iso_naive(ctx["data_hora"])
            if dt_naive and dt_naive <= _agora_br_naive():
                return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

    # ✅ Segurança extra: se ctx já tinha data_hora (de antes) e ela está no passado, bloqueia também
    if ctx.get("data_hora"):
        dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
        if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
            return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

    # =========================================================
    # Se estava "consultando" e usuário confirma, entra em coleta de serviço
    # =========================================================
    if estado_fluxo == "consultando" and eh_confirmacao(texto_lower):
        prof = ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        data_hora = ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")

        if data_hora:
            dt_naive = _dt_from_iso_naive(data_hora)
            if dt_naive and dt_naive <= _agora_br_naive():
                return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        if prof and data_hora:
            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": None,
                "modo_prechecagem": True,
            }
            await salvar_contexto_temporario(user_id, ctx)

            # ✅ CORREÇÃO: busca serviços no dono_id (não user_id)
            profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servicos = []
            for p in profissionais_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servicos = p.get("servicos") or []
                    break

            complemento = ""
            if servicos:
                linhas = [f"- {s}" for s in servicos]
                complemento = "\n\nServiços disponíveis:\n" + "\n".join(linhas)

            data_hora_fmt = formatar_data_hora_br(data_hora)

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Perfeito — com *{prof}* em *{data_hora_fmt}*. Qual serviço vai ser?{complemento}",
                    parse_mode="Markdown",
                )
            return {"acao": None, "handled": True}

    print(
        f"🧭 [estado_fluxo] user={user_id} "
        f"estado_fluxo_raw={ctx.get('estado_fluxo')} "
        f"estado_fluxo_norm={estado_fluxo} "
        f"draft={ctx.get('draft_agendamento')}",
        flush=True,
    )

    # ---------------------------------------------------------
    # 0) Se está aguardando_servico, essa mensagem contém o serviço (e pode conter "com a Bruna")
    # ---------------------------------------------------------
    if estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        draft = ctx.get("draft_agendamento") or {}

        # ✅ extrair profissional do texto tipo: "corte com a bruna"
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]

        tnorm = normalizar(texto_usuario)
        prof_detectado = None
        for nome in nomes_profs:
            if normalizar(nome) in tnorm:
                prof_detectado = nome
                break

        if prof_detectado and " com " in tnorm:
            draft["profissional"] = prof_detectado
            ctx["profissional_escolhido"] = prof_detectado

            # limpa o "com a bruna" do serviço
            # remove variantes comuns "com a", "com o"
            tnorm = re.sub(r"\bcom\s+(a|o)\s+" + re.escape(normalizar(prof_detectado)) + r"\b", "", tnorm).strip()

        # 1) Esta mensagem vira o serviço (ex.: "corte")
        servico_in = (tnorm or "").strip()
        if servico_in:
            draft["servico"] = servico_in.lower()
            ctx["draft_agendamento"] = draft
            ctx["servico"] = draft["servico"]

        # 2) Recalcula chaves do contexto (fonte única)
        prof = draft.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        data_hora = draft.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        servico = draft.get("servico") or ctx.get("servico")

        # 3) Se falta algo, COLETAR (não quebrar fluxo)
        if not data_hora:
            ctx["estado_fluxo"] = "aguardando_data"
            await salvar_contexto_temporario(user_id, ctx)
            if context is not None:
                await context.bot.send_message(chat_id=user_id, text="Qual dia e horário você prefere?", parse_mode="Markdown")
            return {"acao": None, "handled": True}

        if not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            await salvar_contexto_temporario(user_id, ctx)
            if context is not None:
                await context.bot.send_message(chat_id=user_id, text="Qual profissional você prefere?", parse_mode="Markdown")
            return {"acao": None, "handled": True}

        if not servico:
            ctx["estado_fluxo"] = "aguardando_servico"
            await salvar_contexto_temporario(user_id, ctx)
            if context is not None:
                await context.bot.send_message(chat_id=user_id, text="Qual serviço vai ser?", parse_mode="Markdown")
            return {"acao": None, "handled": True}

        # 4) ✅ Segurança: não agendar no passado
        dt_naive = _dt_from_iso_naive(data_hora)
        if dt_naive and dt_naive <= _agora_br_naive():
            return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        # 5) Tudo completo -> confirmação (não agenda direto)
        ctx["estado_fluxo"] = "aguardando_confirmacao"
        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico,
            "modo_prechecagem": bool(draft.get("modo_prechecagem")),
        }
        await salvar_contexto_temporario(user_id, ctx)

        if context is not None:
            dh_fmt = formatar_data_hora_br(data_hora)
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"Confirmando: *{servico}* com *{prof}* em *{dh_fmt}*.\n"
                    "Posso agendar? (responda *confirmar* / *pode marcar*)"
                ),
                parse_mode="Markdown",
            )

        return {"acao": None, "handled": True}

    # ---------------------------------------------------------
    # 0.1) FALLBACK forte:
    # Se por qualquer motivo estado_fluxo ficou "consultando/idle",
    # mas o usuário respondeu um serviço curto e existe ultima_consulta,
    # tratamos como serviço (não volta pro GPT).
    # ---------------------------------------------------------
    if estado_fluxo in ("consultando", "idle"):
        ultima = ctx.get("ultima_consulta") or {}
        prof_u = (ctx.get("profissional_escolhido") or ultima.get("profissional"))
        data_u = (ctx.get("data_hora") or ultima.get("data_hora"))

        if prof_u and data_u and len(normalizar(texto_usuario).split()) <= 5:
            dt_naive = _dt_from_iso_naive(data_u)
            if dt_naive and dt_naive <= _agora_br_naive():
                return await _perguntar_amanha_mesmo_horario_e_bloquear(data_u)

            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof_u):
                    servs = p.get("servicos") or []
                    break

            servico_detectado = extrair_servico_do_texto(texto_usuario, servs)
            if servico_detectado:
                print("🟨 [fallback] Serviço detectado após consulta. Indo para confirmação.", flush=True)

                ctx["estado_fluxo"] = "aguardando_confirmacao"
                ctx["draft_agendamento"] = {
                    "profissional": prof_u,
                    "data_hora": data_u,
                    "servico": servico_detectado,
                    "modo_prechecagem": True,
                }
                ctx["servico"] = servico_detectado
                await salvar_contexto_temporario(user_id, ctx)

                if context is not None:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"Confirmando: *{servico_detectado}* com *{prof_u}* em *{formatar_data_hora_br(data_u)}*.\n"
                            "Posso agendar? (responda *confirmar* / *pode marcar*)"
                        ),
                        parse_mode="Markdown",
                    )
                return {"acao": None, "handled": True}

    # ---------------------------------------------------------
    # 1) Se a mensagem for consulta, marcar estado (sem sobrescrever subfluxos)
    #    ✅ P0.1: consulta com horário específico = PRÉ-CHECAGEM -> pedir serviço (duração)
    # ---------------------------------------------------------
    if eh_consulta(texto_lower) and estado_fluxo == "idle":
        data_hora = ctx.get("data_hora")
        draft = ctx.get("draft_agendamento") or {}
        prof = draft.get("profissional") or ctx.get("profissional_escolhido")
        servico = draft.get("servico") or ctx.get("servico")

        ctx["estado_fluxo"] = "consultando"
        if data_hora or prof:
            ctx["ultima_consulta"] = {"data_hora": data_hora, "profissional": prof}

        # ✅ Se tem horário específico mas não tem profissional ainda, coleta profissional
        if data_hora and not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"

            if not isinstance(ctx.get("ultima_consulta"), dict):
                ctx["ultima_consulta"] = {}
            ctx["ultima_consulta"]["data_hora"] = data_hora

            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": data_hora,
                "servico": None,
                "modo_prechecagem": True,
            }

            await salvar_contexto_temporario(user_id, ctx)

            if context is not None:
                dh_fmt = formatar_data_hora_br(data_hora)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"Para *{dh_fmt}*, qual profissional você prefere?",
                    parse_mode="Markdown",
                )

            return {"acao": None, "handled": True}

        # ✅ P0.1: se há data_hora (consulta específica) e ainda não há serviço, pede serviço
        if data_hora and prof and not servico:
            sugestao = ""

            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": None,
                "modo_prechecagem": True,
            }

            await salvar_contexto_temporario(user_id, ctx)
            print("💾 [P0.1] SALVO:", ctx.get("estado_fluxo"), bool(ctx.get("draft_agendamento")), ctx.get("data_hora"), flush=True)

            if context is not None:
                data_hora_fmt = formatar_data_hora_br(data_hora)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"Para eu confirmar se *cabe* em *{data_hora_fmt}*, preciso do serviço (duração)."
                        f"\nQual serviço vai ser?{sugestao}"
                    ),
                    parse_mode="Markdown",
                )

            return {"acao": None, "handled": True}

        await salvar_contexto_temporario(user_id, ctx)
        # segue para GPT responder a consulta (mas bloquearemos ações mutáveis depois)

    # ---------------------------------------------------------
    # 2) "pode agendar" = decisão final
    # ---------------------------------------------------------
    if eh_gatilho_agendar(texto_lower):
        draft = ctx.get("draft_agendamento") or {}

        data_hora = draft.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        prof = draft.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft.get("servico") or ctx.get("servico")

        if data_hora:
            dt_naive = _dt_from_iso_naive(data_hora)
            if dt_naive and dt_naive <= _agora_br_naive():
                return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        if data_hora and prof:
            if servico:
                ctx["estado_fluxo"] = "agendando"
                await salvar_contexto_temporario(user_id, ctx)

                draft = ctx.get("draft_agendamento") or {}
                data_hora = draft.get("data_hora") or data_hora
                prof = draft.get("profissional") or prof
                servico = draft.get("servico") or servico

                dados_exec = {
                    "servico": servico,
                    "profissional": prof,
                    "data_hora": data_hora,
                    "origem": "auto",
                    "texto_usuario": "confirmar",
                }
                print("✅ [estado_fluxo] Gatilho agendar com contexto completo:", dados_exec, flush=True)
                await executar_acao_gpt(update, context, "criar_evento", dados_exec)

                ctx = await carregar_contexto_temporario(user_id) or {}
                ctx["estado_fluxo"] = "idle"
                ctx["draft_agendamento"] = None
                await salvar_contexto_temporario(user_id, ctx)
                return {"acao": "criar_evento", "handled": True}

            # falta serviço -> pedir só serviço
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break

            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": None,
                "modo_prechecagem": True,
            }
            await salvar_contexto_temporario(user_id, ctx)

            data_hora_fmt = formatar_data_hora_br(data_hora) if data_hora else "esse horário"

            if context is not None:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(f"Perfeito — com *{prof}* em *{data_hora_fmt}*. Qual serviço vai ser?{sugestao}"),
                    parse_mode="Markdown",
                )

            return {"acao": None, "handled": True}

    # =========================================================
    # 3) Chamada normal ao GPT (com contexto do dono)
    # =========================================================
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto["usuario"] = {"user_id": user_id, "id_negocio": dono_id}

    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    contexto["profissionais"] = list(profissionais_dict.values())

    resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)
    print("🧠 resposta_gpt retornada:", resposta_gpt)

    cumprimentos = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "eai", "tudo bem?"]
    if isinstance(resposta_gpt, dict) and resposta_gpt.get("acao") == "buscar_tarefas_do_usuario" and texto_lower in cumprimentos:
        resposta_gpt = {"resposta": "Olá! Como posso ajudar?", "acao": None, "dados": {}}

    if not resposta_gpt or not isinstance(resposta_gpt, dict):
        print("⚠️ Resposta do GPT inválida ou vazia:", resposta_gpt)
        if context is not None:
            await context.bot.send_message(chat_id=user_id, text="❌ Ocorreu um erro ao interpretar sua mensagem.")
        return

    resposta_texto = resposta_gpt.get("resposta")
    acao = resposta_gpt.get("acao")
    dados = resposta_gpt.get("dados", {}) or {}

    # ✅ Exceção: no modo consultando, usuário pode estar ESCOLHENDO uma profissional sugerida
    if estado_fluxo == "consultando":
        opcoes = (ctx.get("ultima_opcao_profissionais") or [])
        if opcoes:
            tnorm = unidecode((texto_lower or "").strip().lower())

            escolhido = None
            for nome in opcoes:
                if unidecode(str(nome).strip().lower()) in tnorm:
                    escolhido = str(nome).strip()
                    break

            if escolhido:
                draft = ctx.get("draft_agendamento") or {}
                ctx["profissional_escolhido"] = escolhido

                dh = draft.get("data_hora") or ctx.get("data_hora")
                if not dh and isinstance(ctx.get("ultima_consulta"), dict):
                    dh = ctx["ultima_consulta"].get("data_hora")
                    if dh:
                        ctx["data_hora"] = dh

                servico_atual = draft.get("servico") or ctx.get("servico")

                if servico_atual and dh:
                    ctx["estado_fluxo"] = "aguardando_confirmacao"
                    ctx["draft_agendamento"] = {
                        "profissional": escolhido,
                        "data_hora": dh,
                        "servico": servico_atual,
                        "modo_prechecagem": bool(draft.get("modo_prechecagem")),
                    }
                    await salvar_contexto_temporario(user_id, ctx)

                    dh_fmt = formatar_data_hora_br(dh)
                    if context is not None:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=(
                                f"Fechado. Quer que eu *agende* *{servico_atual}* com *{escolhido}* em *{dh_fmt}*?\n"
                                "Responda: *confirmar* / *pode marcar*."
                            ),
                            parse_mode="Markdown",
                        )
                    return {"acao": None, "handled": True}

                ctx["estado_fluxo"] = "aguardando_servico"
                ctx["draft_agendamento"] = {
                    "profissional": escolhido,
                    "data_hora": dh,
                    "servico": None,
                    "modo_prechecagem": True,
                }
                await salvar_contexto_temporario(user_id, ctx)

                dh_fmt = formatar_data_hora_br(dh) if dh else ""
                if context is not None:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Perfeito — com *{escolhido}* {('em *'+dh_fmt+'*') if dh_fmt else ''}. Qual serviço vai ser?",
                        parse_mode="Markdown",
                    )
                return {"acao": None, "handled": True}

    # ✅ REGRA DE OURO: se é CONSULTA, bloqueia ações mutáveis vindas do GPT
    if (eh_consulta(texto_lower) or estado_fluxo == "consultando") and acao in ("criar_evento", "cancelar_evento"):
        print(f"🛑 [estado_fluxo] Bloqueado '{acao}' pois mensagem é consulta: '{texto_lower}'", flush=True)
        return {
            "acao": None,
            "handled": True,
            "resposta": (
                "Entendi. Se você quer *agendar*, confirme dizendo:\n"
                "• 'confirmar'  ou  'pode marcar'\n"
                "Se quiser só consultar, pode perguntar normalmente."
            )
        }

    ACOES_SUPORTADAS = {
        "consultar_preco_servico",
        "criar_evento",
        "buscar_eventos_da_semana",
        "criar_tarefa",
        "remover_tarefa",
        "cancelar_evento",
        "listar_followups",
        "cadastrar_profissional",
        "aguardar_arquivo_importacao",
        "enviar_email",
        "organizar_semana",
        "buscar_tarefas_do_usuario",
        "buscar_emails",
        "verificar_pagamento",
        "verificar_acesso_modulo",
        "responder_audio",
        "criar_followup",
        "buscar_eventos_do_dia",
    }

    handled = False

    if acao:
        if acao not in ACOES_SUPORTADAS:
            print(f"⚠️ Ação '{acao}' não suportada. Ignorando...")
            acao = None
            dados = {}
        else:
            handled = await executar_acao_gpt(update, context, acao, dados)

            if acao == "criar_evento":
                return {"acao": "criar_evento", "handled": True}

    if (not acao) and resposta_texto:
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_texto})
        if context is not None:
            await context.bot.send_message(chat_id=user_id, text=resposta_texto, parse_mode="Markdown")
        return {"resposta": resposta_texto}

    if acao:
        return {"acao": acao, "handled": bool(handled)}

    return {"resposta": "❌ Não consegui interpretar sua mensagem."}