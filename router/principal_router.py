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
from utils.gpt_utils import estimar_duracao, formatar_descricao_evento

import pytz
import re
from unidecode import unidecode


# ----------------------------
# Helpers de saída (anti-duplicidade)
# ----------------------------

async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
    return {"handled": True, "already_sent": True}


# ----------------------------
# Helpers de NLP simples
# ----------------------------

def normalizar(texto: str) -> str:
    return unidecode((texto or "").strip().lower())


def formatar_data_hora_br(dt_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_iso)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(dt_iso)


def eh_consulta(txt: str) -> bool:
    """
    Detecta consulta pura.
    Só retorna True quando há forte evidência de pergunta/informação
    e NÃO houver sinais típicos de agendamento/continuidade.
    """
    t = normalizar(txt or "")
    if not t:
        return False

    # ❌ Mensagens curtas/neutras não devem ser tratadas como consulta
    curtas_neutras = {
        "sim", "nao", "não", "ok", "pode", "pode ser", "fechado",
        "esse", "esse ai", "esse aí", "entao", "então",
        "mais tarde", "mais cedo", "outro horario", "outro horário",
        "esse horario", "esse horário", "esse outro",
        "com ela", "com ele", "com a", "com o"
    }
    if t in curtas_neutras:
        return False

    # ❌ Se há indício de horário, tende a ser continuidade/agendamento
    if _tem_indicio_de_hora(t):
        return False

    # ❌ Se há verbos de ação de agendamento, não é consulta
    gatilhos_agendamento = [
        "agendar", "marcar", "confirmar", "confirma", "confirme", "confirmo",
        "pode agendar", "pode marcar", "agenda pra", "agenda para",
        "marca pra", "marca para", "entao marca", "então marca",
        "quero agendar", "quero marcar", "fechar horario", "fechar horário",
        "agenda esse", "marca esse", "entao esse", "então esse"
    ]
    if any(g in t for g in gatilhos_agendamento):
        return False

    # ❌ Frases de continuidade/reação também não são consulta pura
    gatilhos_continuacao = [
        "outro horario", "outro horário",
        "esse horario", "esse horário",
        "mais tarde", "mais cedo",
        "esse outro", "entao esse", "então esse",
        "mas com a", "mas com o", "com ela", "com ele",
        "que pena", "nossa", "serio", "sério",
        "ela nao consegue", "ela não consegue",
        "nao consegue", "não consegue",
        "nao tem jeito", "não tem jeito",
        "que horario tem", "que horário tem"
    ]
    if any(g in t for g in gatilhos_continuacao):
        return False

    # ✅ Consultas claras
    gatilhos_consulta = [
        "quanto custa", "qual o preco", "qual o preço", "valor", "preco", "preço",
        "tem horario", "tem horário", "tem vaga", "tem espaco", "tem espaço",
        "quais horarios", "quais horários", "que horas",
        "agenda da", "como esta a agenda", "como está a agenda",
        "disponivel", "disponível",
        "quais servicos", "quais serviços", "que servicos", "que serviços",
        "quem faz", "quem atende", "faz escova", "faz corte",
        "qual o endereco", "qual o endereço", "onde fica", "localizacao", "localização",
        "qual o telefone", "whatsapp", "zap",
        "funciona hoje", "abre hoje", "fecha hoje", "que horas abre", "que horas fecha",
        "tem promocao", "tem promoção", "promoção", "promocao"
    ]

    # ✅ Pergunta explícita só é consulta se também tiver cara de consulta
    if "?" in txt:
        gatilhos_pergunta_consulta = [
            "quanto", "qual", "quais", "quem", "onde", "como", "valor", "preco", "preço",
            "horario", "horário", "vaga", "espaco", "espaço",
            "servico", "serviço", "endereco", "endereço", "telefone", "whatsapp",
            "funciona", "abre", "fecha", "promocao", "promoção"
        ]
        if any(g in t for g in gatilhos_pergunta_consulta):
            return True

    return any(g in t for g in gatilhos_consulta)

def eh_gatilho_agendar(txt: str) -> bool:
    """
    Gatilho explícito de agendar (decisão final do usuário).
    """
    t = (txt or "").strip().lower()
    gatilhos = ["pode agendar", "pode marcar", "agende", "marque"]
    return any(g in t for g in gatilhos)


def eh_confirmacao(txt: str) -> bool:
    """
    Confirmação genérica (sem depender de comando).
    """
    t = (txt or "").strip().lower()
    if "nao" in t or "não" in t:
        return False
    gatilhos = [
        "confirmar", "confirma", "confirme", "confirmo",   
        "pode agendar", "pode marcar", "agende", "marque",
        "fechar", "ok", "confirmado",
        "sim", "pode", "pode ser", "pode sim", "pode ir", "manda ver"
    ]
    return any(g in t for g in gatilhos)


def _tem_indicio_de_hora(txt: str) -> bool:
    """
    Evita que interpretar_data_e_hora chute 'amanhã' sem hora.
    Só tenta extrair dt quando houver indício de horário.
    """
    t = (txt or "").lower()
    return bool(
        re.search(r"\b\d{1,2}(:\d{2})?\b", t)
        or re.search(r"\b\d{1,2}\s*h\b", t)
        or "às" in t
        or " as " in t
    )


def extrair_servico_do_texto(texto_usuario: str, servicos_disponiveis: list) -> str | None:
    """
    Tenta mapear o texto do usuário para um serviço existente (lista).
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

async def validar_profissional_para_servico(dono_id: str, profissional: str | None, servico: str | None):
    """
    Valida se o profissional executa o serviço.
    Retorna:
      {
        "ok": bool,
        "validos": [nomes]
      }
    """
    if not profissional or not servico:
        return {"ok": False, "validos": []}

    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    # serviços do profissional escolhido
    servicos_prof = []
    for p in profs_dict.values():
        nomep = (p.get("nome") or "").strip()
        if normalizar(nomep) == normalizar(profissional):
            servicos_prof = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
            break

    if any(normalizar(servico) == normalizar(s) for s in servicos_prof):
        return {"ok": True, "validos": []}

    # lista de profissionais válidos para o serviço
    validos = []
    for p in profs_dict.values():
        nomep = (p.get("nome") or "").strip()
        servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
        if nomep and any(normalizar(servico) == normalizar(s) for s in servs):
            validos.append(nomep)

    return {"ok": False, "validos": validos}

# ----------------------------
# auditoria
# ----------------------------

def _audit_confirmacao(tag: str, ctx: dict, texto_usuario: str = ""):
    try:
        draft = ctx.get("draft_agendamento") or {}
        dados_conf = ctx.get("dados_confirmacao_agendamento") or {}

        print(
            f"🧪 [AUDIT-CONF:{tag}] "
            f"texto={texto_usuario!r} | "
            f"estado_fluxo={ctx.get('estado_fluxo')} | "
            f"aguardando_confirmacao_agendamento={ctx.get('aguardando_confirmacao_agendamento')} | "
            f"profissional_escolhido={ctx.get('profissional_escolhido')} | "
            f"servico={ctx.get('servico')} | "
            f"data_hora={ctx.get('data_hora')} | "
            f"ultima_opcao_profissionais={ctx.get('ultima_opcao_profissionais')}",
            flush=True
        )

        print(
            f"🧪 [AUDIT-CONF:{tag}:DRAFT] "
            f"profissional={draft.get('profissional')} | "
            f"servico={draft.get('servico')} | "
            f"data_hora={draft.get('data_hora')} | "
            f"modo_prechecagem={draft.get('modo_prechecagem')}",
            flush=True
        )

        print(
            f"🧪 [AUDIT-CONF:{tag}:DADOS_CONF] "
            f"profissional={dados_conf.get('profissional')} | "
            f"servico={dados_conf.get('servico')} | "
            f"data_hora={dados_conf.get('data_hora')} | "
            f"duracao={dados_conf.get('duracao')} | "
            f"descricao={dados_conf.get('descricao')}",
            flush=True
        )

    except Exception as e:
        print(f"⚠️ Falha em _audit_confirmacao({tag}): {e}", flush=True)

# ----------------------------
# Slots always-on
# ----------------------------

async def extrair_slots_e_mesclar(ctx: dict, texto_usuario: str, dono_id: str) -> dict:
    """
    Sempre-on: extrai slots em ctx + draft_agendamento.

    Regra principal:
    - se o usuário informou explicitamente profissional, serviço ou data/hora
      na mensagem atual, esse valor SOBRESCREVE o anterior.
    - não herda profissional/serviço/data_hora antigos quando a mensagem nova
      já trouxe novos slots claros.
    """
    texto = (texto_usuario or "").strip()
    tnorm = normalizar(texto)
    draft = ctx.get("draft_agendamento") or {}

    # ---------------- profissionais ----------------
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]

    prof_detectado = None
    for nome in nomes_profs:
        if normalizar(nome) in tnorm:
            prof_detectado = nome
            break

    # ---------------- serviço ----------------
    servico_detectado = None

    def _match_servico(lista_servs):
        nonlocal servico_detectado
        for s in lista_servs or []:
            s_norm = normalizar(str(s))
            if s_norm and s_norm in tnorm:
                servico_detectado = str(s).strip()
                return True
        return False

    # 1) serviços do profissional detectado
    if prof_detectado:
        for p in profs_dict.values():
            if normalizar(p.get("nome", "")) == normalizar(prof_detectado):
                _match_servico(p.get("servicos") or [])
                break

    # 2) catálogo global
    if not servico_detectado:
        todos = []
        for p in profs_dict.values():
            todos.extend(p.get("servicos") or [])
        vistos = set()
        uniq = []
        for s in todos:
            s2 = str(s).strip()
            if s2 and s2 not in vistos:
                vistos.add(s2)
                uniq.append(s2)
        _match_servico(uniq)

    # ---------------- data/hora ----------------
    dt_detectado = None
    if _tem_indicio_de_hora(texto):
        dt_detectado = interpretar_data_e_hora(texto)

    # =========================================================
    # REGRA CENTRAL: slot explícito novo SOBRESCREVE o antigo
    # =========================================================

    if dt_detectado:
        iso = dt_detectado.replace(second=0, microsecond=0).isoformat()
        ctx["data_hora"] = iso
        draft["data_hora"] = iso

        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["data_hora"] = iso

    if prof_detectado:
        ctx["profissional_escolhido"] = prof_detectado
        draft["profissional"] = prof_detectado

        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["profissional"] = prof_detectado

    if servico_detectado:
        ctx["servico"] = servico_detectado
        draft["servico"] = servico_detectado

    if draft:
        ctx["draft_agendamento"] = draft

    return ctx
def _tem_referencia_profissional_indireta(tnorm: str) -> bool:
    gat = [
        "ela", "ele", "dela", "dele", "dessa", "desse", "essa", "esse",
        "essa profissional", "esse profissional", "a moça", "o rapaz",
        "com ela", "com ele", "pra ela", "pra ele", "para ela", "para ele",
        "da última", "do último", "da ultima", "do ultimo",
        "dessa ai", "desse ai", "dessa aí", "desse aí",
        "dela aí", "dele aí", "dela ai", "dele ai"
    ]
    return any(g in tnorm for g in gat)


def resolver_profissional_referenciado(tnorm: str, profs_dict: dict, ctx: dict) -> str | None:
    """
    Resolve qual profissional o usuário está referenciando, com prioridade:
    1) nome explícito no texto
    2) profissional do fluxo (draft/profissional_escolhido)
    3) referência indireta (ela/dela/etc.) -> ultima_consulta/profissional_escolhido
    """
    # 1) nome explícito no texto
    for p in (profs_dict or {}).values():
        nomep = (p.get("nome") or "").strip()
        if nomep and normalizar(nomep) in tnorm:
            return nomep

    # 2) profissional do fluxo
    draft = (ctx or {}).get("draft_agendamento") or {}
    prof_fluxo = draft.get("profissional") or (ctx or {}).get("profissional_escolhido")
    if prof_fluxo:
        return prof_fluxo

    # 3) referência indireta -> última consulta / escolhido
    if _tem_referencia_profissional_indireta(tnorm):
        ult_prof = ((ctx or {}).get("ultima_consulta") or {}).get("profissional")
        if ult_prof:
            return ult_prof
        prof_ctx = (ctx or {}).get("profissional_escolhido")
        if prof_ctx:
            return prof_ctx

    return None


def extrair_servico_alvo_binario(tnorm: str, catalogo_servicos: list[str]) -> str | None:
    """
    Pega o 'X' em frases tipo:
    - "ela faz X?"
    - "tem X?"
    - "trabalha com X?"
    E tenta mapear para um serviço do catálogo.
    """
    if not catalogo_servicos:
        return None

    # tira pontuação básica
    t = re.sub(r"[?!.,;:]", " ", tnorm).strip()

    # padrões simples
    padroes = [
        r"\bfaz\s+(.+)$",
        r"\btem\s+(.+)$",
        r"\btrabalha\s+com\s+(.+)$",
        r"\boferece\s+(.+)$",
        r"\batende\s+(.+)$",
    ]

    alvo = None
    for pat in padroes:
        m = re.search(pat, t)
        if m:
            alvo = m.group(1).strip()
            break

    if not alvo:
        return None

    # normaliza alvo e tenta casar com catálogo
    alvo_n = normalizar(alvo)
    if not alvo_n:
        return None

    # match forte: catálogo contido no alvo (ou alvo contido no catálogo)
    for s in catalogo_servicos:
        sn = normalizar(s)
        if not sn:
            continue
        if sn in alvo_n or alvo_n in sn:
            return s

    return None

def tem_contexto_agendamento_ativo(ctx: dict) -> bool:
    ctx = ctx or {}
    draft = ctx.get("draft_agendamento") or {}
    ultima = ctx.get("ultima_consulta") or {}

    return bool(
        ctx.get("aguardando_confirmacao_agendamento")
        or ctx.get("servico")
        or ctx.get("profissional_escolhido")
        or ctx.get("data_hora")
        or draft.get("servico")
        or draft.get("profissional")
        or draft.get("data_hora")
        or ultima.get("profissional")
        or ultima.get("data_hora")
    )


def eh_confirmacao_pendente_ativa(ctx: dict) -> bool:
    ctx = ctx or {}
    return bool(ctx.get("aguardando_confirmacao_agendamento"))


def eh_reacao_a_sugestao(txt: str, ctx: dict) -> bool:
    """
    Reações/dúvidas do usuário quando já existe um fluxo de agendamento.
    Ex.: 'nossa sério que ela não consegue nesse horário?'
    """
    t = normalizar(txt or "")
    if not t:
        return False

    if not tem_contexto_agendamento_ativo(ctx):
        return False

    gatilhos = [
        "nossa", "que pena", "serio", "sério",
        "ela nao consegue", "ela não consegue",
        "nao consegue", "não consegue",
        "nao tem jeito", "não tem jeito",
        "lotado", "cheia", "cheio",
        "mesmo", "de verdade"
    ]
    return any(g in t for g in gatilhos)


def eh_escolha_de_alternativa(txt: str, ctx: dict) -> bool:
    """
    Detecta aceitação/troca de opção dentro de um fluxo já ativo.
    Ex.: '14:40', 'outro horário às 14:40', 'então marca esse'
    """
    t = normalizar(txt or "")
    if not t:
        return False

    if not tem_contexto_agendamento_ativo(ctx):
        return False

    if _tem_indicio_de_hora(t):
        return True

    gatilhos = [
        "outro horario", "outro horário",
        "esse horario", "esse horário",
        "esse", "esse outro",
        "entao marca esse", "então marca esse",
        "entao esse", "então esse",
        "mais tarde", "mais cedo",
        "com ela", "com ele", "com a", "com o",
        "pode ser", "fechado"
    ]
    return any(g in t for g in gatilhos)


def eh_continuacao_de_agendamento(txt: str, ctx: dict) -> bool:
    """
    Guarda-chuva para qualquer continuidade legítima de um fluxo já ativo.
    """
    if not tem_contexto_agendamento_ativo(ctx):
        return False

    t = normalizar(txt or "")
    if not t:
        return False

    if eh_confirmacao(t):
        return True

    if eh_escolha_de_alternativa(t, ctx):
        return True

    if eh_reacao_a_sugestao(t, ctx):
        return True

    # frases como "então marca", "vamos nessa", etc.
    gatilhos_fluxo = [
        "marca", "agenda", "entao", "então", "vamos", "segue", "faz assim"
    ]
    if any(g in t for g in gatilhos_fluxo):
        return True

    return False


# ----------------------------
# Router principal
# ----------------------------

async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")

    texto_usuario = (mensagem or "").strip()
    texto_lower = texto_usuario.lower().strip()
    tnorm = normalizar(texto_usuario)

    # ✅ 2) Contexto temporário do router (estado_fluxo) - vem antes da consulta informativa
    ctx = await carregar_contexto_temporario(user_id) or {}
    estado_fluxo = (ctx.get("estado_fluxo") or "idle").strip().lower()
    draft = ctx.get("draft_agendamento") or {}

    # ✅ 0) Consulta informativa só quando está IDLE (não atrapalha o fluxo de agendamento)
    if estado_fluxo == "idle":
        from services.informacao_service import responder_consulta_informativa
        resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
        if resposta_informativa:
            print("🔍 Consulta informativa detectada (idle). Respondendo diretamente.")
            return await _send_and_stop(context, user_id, resposta_informativa)

    # 🔐 dono do negócio
    dono_id = await obter_id_dono(user_id)

    # ✅ Guard: perguntas de catálogo/menu NÃO podem cair no fluxo legado (evita GPT alucinar lista)
    intencao_catalogo = any(x in tnorm for x in [
        # lista por profissional (A1)
        "cada profissional", "servicos de cada", "serviços de cada",
        "todos os profissionais", "todos profissionais", "todas as profissionais", "todas profissionais",
        "separado por nome", "separados por nome", "por profissional",

        # menus (A)
        "quais profissionais", "lista de profissionais", "me diz os profissionais",
        "quais servicos", "quais serviços", "lista de servicos", "lista de serviços",
        "quais voce tem", "quais você tem", "quem voce tem", "quem você tem",

        # binários/busca (A0)
        "quem faz", "quem atende", "ela faz", "ele faz", "dela", "dele"
    ])

    # ✅ Se existe sessão ativa do fluxo legado, só respeita se NÃO for intenção de catálogo
    sessao = await pegar_sessao(user_id)

    # ✅ Só deixa a sessão legada assumir quando NÃO estamos no fluxo novo de agendamento
    if (not intencao_catalogo) and sessao and sessao.get("estado") and estado_fluxo != "agendando":
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_fluxo})
        return resposta_fluxo

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
        Produto:
        - Se o horário passou e o usuário não informou serviço/profissional,
          primeiro coletar 1 dos dois (serviço OU profissional), com texto humano.
        - Só depois oferecer 'amanhã mesmo horário'.
        """
        draft_local = ctx.get("draft_agendamento") or {}
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft_local.get("servico") or ctx.get("servico")

        # prepara bloqueio de amanhã
        ctx["estado_fluxo"] = "aguardando_data"
        ctx["pergunta_amanha_mesmo_horario"] = True
        ctx["data_hora_pendente"] = data_hora_iso
        ctx["data_hora"] = None

        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["data_hora"] = None

        await salvar_contexto_temporario(user_id, ctx)

        # ✅ primeiro coletar mínimo (serviço OU profissional)
        if not (prof or servico):
            return await _send_and_stop(
                context,
                user_id,
                (
                    f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou.\n"
                    "Só me diz rapidinho: *qual serviço* você quer fazer (ou *com qual profissional* prefere), "
                    "pra eu conferir a agenda certinho."
                )
            )

        # ✅ já tem mínimo → agora sim oferecer amanhã mesmo horário
        return await _send_and_stop(
            context,
            user_id,
            (
                f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou.\n"
                "Quer *amanhã no mesmo horário* ou prefere outro horário?"
            )
        )

    # =========================================================
    # ✅ (A0) Intercept binário: "ela faz X?" / "quem faz X?"
    # =========================================================
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    # catálogo global (união)
    catalogo_global = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_global.append(s)
    catalogo_global = sorted(set(catalogo_global), key=lambda x: normalizar(x))

    # 1) "quem faz X?" -> retorna profissionais que fazem
    if "quem faz" in tnorm or "quem atende" in tnorm:
        serv_alvo = extrair_servico_alvo_binario(tnorm, catalogo_global)
        if serv_alvo:
            fazem = []
            for p in profs_dict.values():
                nomep = (p.get("nome") or "").strip()
                servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                if nomep and any(normalizar(serv_alvo) == normalizar(x) for x in servs):
                    fazem.append(nomep)

            if fazem:
                txt = f"*Quem faz {serv_alvo}:*\n- " + "\n- ".join(sorted(set(fazem)))
                # se estiver em fluxo, puxa para seleção
                if estado_fluxo in ("aguardando_profissional", "aguardando_servico", "aguardando serviço", "aguardando_serviço"):
                    txt += "\n\nCom quem você prefere?"
                return await _send_and_stop(context, user_id, txt)
            else:
                return await _send_and_stop(context, user_id, f"Aqui eu não encontrei ninguém cadastrado para *{serv_alvo}*.")

    # 2) "ela faz X?" / "tem X?" -> responde sim/não (com base no profissional referenciado)
    # Só roda se houver pista de binário
    if any(x in tnorm for x in ["faz ", "tem ", "trabalha com", "oferece ", "atende "]):
        prof_ref = resolver_profissional_referenciado(tnorm, profs_dict, ctx)
        if prof_ref:
            # catálogo do profissional
            servs_prof = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof_ref):
                    servs_prof = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                    break

            serv_alvo = extrair_servico_alvo_binario(tnorm, servs_prof or catalogo_global)
            if serv_alvo:
                tem = any(normalizar(serv_alvo) == normalizar(x) for x in (servs_prof or []))
                if tem:
                    return await _send_and_stop(context, user_id, f"Sim — *{prof_ref}* faz *{serv_alvo}* ✅")
                else:
                    # sugere quem faz (se existir)
                    fazem = []
                    for p in profs_dict.values():
                        nomep = (p.get("nome") or "").strip()
                        servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                        if nomep and any(normalizar(serv_alvo) == normalizar(x) for x in servs):
                            fazem.append(nomep)
                    if fazem:
                        return await _send_and_stop(
                            context,
                            user_id,
                            f"*{prof_ref}* não faz *{serv_alvo}*.\nQuem faz: " + ", ".join(sorted(set(fazem))) + "."
                        )
                    return await _send_and_stop(context, user_id, f"*{prof_ref}* não faz *{serv_alvo}*.")

    # =========================================================
    # ✅ (A1) Intercept: serviços de TODOS os profissionais (por nome)
    # =========================================================
    gatilhos_a1 = [
        "cada profissional",
        "servicos de cada", "serviços de cada",
        "servicos de todas", "serviços de todas",
        "todos profissionais", "todos os profissionais",
        "todas profissionais", "todas as profissionais",
        "separado por nome", "separados por nome",
        "por profissional",
        "lista de servicos", "lista de serviços"
    ]

    if any(x in tnorm for x in gatilhos_a1):
        if not profs_dict:
            return await _send_and_stop(context, user_id, "Ainda não há profissionais cadastrados.")

        linhas = []
        for p in profs_dict.values():
            nome = (p.get("nome") or "").strip()

            raw_servs = p.get("servicos")
            if isinstance(raw_servs, str):
                servs = [s.strip() for s in raw_servs.split(",") if s.strip()]
            elif isinstance(raw_servs, dict):
                servs = [str(k).strip() for k in raw_servs.keys() if str(k).strip()]
            else:
                servs = [str(s).strip() for s in (raw_servs or []) if str(s).strip()]

            if nome:
                if servs:
                    linhas.append(f"- *{nome}:* " + ", ".join(sorted(set(servs), key=lambda x: normalizar(x))))
                else:
                    linhas.append(f"- *{nome}:* (sem serviços cadastrados)")

        txt = "*Serviços por profissional:*\n" + "\n".join(linhas)
        return await _send_and_stop(context, user_id, txt)

    # =========================================================
    # ✅ (A) Intercept contextual: listar profissionais/serviços SOMENTE quando o usuário pede menu
    # =========================================================

    # intenção explícita de menu
    quer_menu_prof = any(x in tnorm for x in [
        "quais profissionais", "quais profissional", "quem atende", "quem voce tem", "quem você tem", "quem tem",
        "me diz os profissionais", "lista de profissionais", "opcoes de profissionais", "opções de profissionais"
    ])

    quer_menu_serv = any(x in tnorm for x in [
        "quais servicos", "quais serviços", "quais voce tem", "quais você tem",
        "me diz os servicos", "me diz os serviços", "lista de servicos", "lista de serviços",
        "opcoes de servicos", "opções de serviços", "quais são os serviços", "quais sao os servicos"
    ])

    # "quem faz" (genérico)
    quem_faz_generico = ("quem faz" in tnorm)

    # em fluxo, só abre menu se usuário pediu menu (não por estar aguardando)
    if estado_fluxo == "aguardando_profissional":
        quer_profissionais = bool(quer_menu_prof or tnorm in ("quais", "quem"))
        quer_servicos = False
    elif estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        quer_servicos = bool(quer_menu_serv or tnorm == "quais")
        quer_profissionais = False
    else:
        quer_profissionais = bool(quer_menu_prof or quem_faz_generico)
        quer_servicos = bool(quer_menu_serv and not quer_profissionais)

    if quer_profissionais or quer_servicos or (quem_faz_generico and estado_fluxo == "idle"):
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        if not profs_dict:
            return await _send_and_stop(context, user_id, "Ainda não há profissionais cadastrados.")

        nomes = []
        servicos = set()
        for p in profs_dict.values():
            nome = (p.get("nome") or "").strip()
            if nome:
                nomes.append(nome)
            for s in (p.get("servicos") or []):
                s = str(s).strip()
                if s:
                    servicos.add(s)

        # 🔎 Resolve profissional (nome explícito OU pronome "ela/dela" via contexto)
        prof_citado = resolver_profissional_referenciado(tnorm, profs_dict, ctx)

        if quer_servicos and not quer_profissionais:
            if prof_citado:
                # ✅ Serviços somente do profissional citado
                servs_prof = []
                for p in profs_dict.values():
                    if normalizar(p.get("nome", "")) == normalizar(prof_citado):
                        servs_prof = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                        break

                if servs_prof:
                    txt = f"*Serviços da {prof_citado}:*\n- " + "\n- ".join(sorted(set(servs_prof)))
                else:
                    txt = f"Não encontrei serviços cadastrados para *{prof_citado}*."
            else:
                # ✅ Serviços gerais do salão (união de todos)
                txt = "*Serviços do salão:*\n- " + "\n- ".join(sorted(servicos)) if servicos else "Ainda não há serviços cadastrados."
        else:
            txt = "*Profissionais:*\n- " + "\n- ".join(sorted(set(nomes)))

        # ✅ Só faz pergunta de coleta se o menu foi pedido DURANTE o fluxo
        menu_dentro_do_fluxo = (estado_fluxo in ("aguardando_profissional", "aguardando_servico", "aguardando serviço", "aguardando_serviço"))

        if menu_dentro_do_fluxo:
            if estado_fluxo == "aguardando_profissional":
                txt += "\n\nQual você prefere?"
            elif estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
                # se o usuário perguntou serviços de um profissional específico, pode perguntar qual vai ser
                # mas só se isso fizer sentido dentro do fluxo (aqui faz)
                txt += "\n\nQual serviço vai ser?"

        return await _send_and_stop(context, user_id, txt)
    # =========================================================
    # ✅ (B) SEMPRE-ON: extrair e mesclar slots (prof/serv/dt)
    # =========================================================
    try:
        # novo pedido de agendamento não deve herdar resíduos de conflito/confirmação anterior
        if eh_gatilho_agendar(texto_lower):
            tnorm_msg = normalizar(texto_usuario)

            profs_dict_tmp = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            nomes_tmp = [str(p.get("nome", "")).strip() for p in profs_dict_tmp.values() if p.get("nome")]

            tem_profissional_expresso = any(normalizar(nome) in tnorm_msg for nome in nomes_tmp)
            tem_data_explicitada = _tem_indicio_de_hora(texto_usuario)

            # catálogo global de serviços
            servicos_tmp = []
            for p in profs_dict_tmp.values():
                servicos_tmp.extend([str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()])

            servicos_tmp = list(dict.fromkeys(servicos_tmp))
            tem_servico_explicito = any(normalizar(s) in tnorm_msg for s in servicos_tmp)

            # limpa resíduos de confirmação/conflito
            ctx.pop("sugestoes", None)
            ctx.pop("alternativa_profissional", None)
            ctx.pop("dados_confirmacao_agendamento", None)
            ctx["aguardando_confirmacao_agendamento"] = False
            ctx["ultima_opcao_profissionais"] = []

            # se o slot NÃO foi dito nesta mensagem, não herdar da consulta antiga
            if tem_profissional_expresso and not tem_servico_explicito:
                ctx.pop("servico", None)
            if isinstance(ctx.get("draft_agendamento"), dict):
                ctx["draft_agendamento"].pop("servico", None)

            if tem_profissional_expresso and not tem_data_explicitada:
                ctx.pop("data_hora", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("data_hora", None)

            if tem_servico_explicito and not tem_profissional_expresso:
                ctx.pop("profissional_escolhido", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("profissional", None)

            if tem_servico_explicito and not tem_data_explicitada:
                ctx.pop("data_hora", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("data_hora", None)

            if tem_data_explicitada and not tem_profissional_expresso:
                ctx.pop("profissional_escolhido", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("profissional", None)

            if tem_data_explicitada and not tem_servico_explicito:
                ctx.pop("servico", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("servico", None)

            # consulta anterior não pode completar pedido novo automaticamente
            if isinstance(ctx.get("ultima_consulta"), dict):
                if not tem_data_explicitada:
                    ctx["ultima_consulta"].pop("data_hora", None)
                if not tem_profissional_expresso:
                    ctx["ultima_consulta"].pop("profissional", None)

        ctx = await extrair_slots_e_mesclar(ctx, texto_usuario, dono_id)
        await salvar_contexto_temporario(user_id, ctx)
        estado_fluxo = (ctx.get("estado_fluxo") or estado_fluxo or "idle").strip().lower()
        draft = ctx.get("draft_agendamento") or {}
    except Exception as e:
        print("⚠️ [slots] Falha ao extrair/mesclar slots:", e, flush=True)

    # =========================================================
    # ✅ (C) Bloqueio de data no passado -> pergunta amanhã mesmo horário
    # =========================================================
    if ctx.get("data_hora"):
        dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
        if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
            return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

    # =========================================================
    # ✅ (D) Capturar "sim/amanhã então" (amanhã mesmo horário)
    # =========================================================
    if ctx.get("pergunta_amanha_mesmo_horario") and (
        eh_confirmacao(texto_lower) or "amanha" in texto_lower or "amanhã" in texto_lower
    ):
        base_iso = ctx.get("data_hora_pendente") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        if not base_iso:
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["pergunta_amanha_mesmo_horario"] = False
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Certo — qual dia e horário você prefere?")

        base_dt = _dt_from_iso_naive(base_iso)
        if not base_dt:
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["pergunta_amanha_mesmo_horario"] = False
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Me manda o dia e horário de novo, por favor.")

        nova_dt = base_dt + timedelta(days=1)
        nova_iso = nova_dt.replace(second=0, microsecond=0).isoformat()

        draft_local = ctx.get("draft_agendamento") or {}
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft_local.get("servico") or ctx.get("servico")

        if not (prof or servico):
            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["pergunta_amanha_mesmo_horario"] = False
            ctx["data_hora"] = nova_iso
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": nova_iso, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(
                context,
                user_id,
                f"Fechado — *{formatar_data_hora_br(nova_iso)}*. Só me diz: qual serviço você quer fazer? (ou com qual profissional prefere)"
            )

        # Atualiza contexto
        ctx["data_hora"] = nova_iso
        ctx["data_hora_pendente"] = None
        ctx["pergunta_amanha_mesmo_horario"] = False
        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["data_hora"] = nova_iso

        # Define próximo passo correto
        if not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["draft_agendamento"] = {"profissional": None, "data_hora": nova_iso, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Perfeito. Qual profissional você prefere?")

        if not servico:
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
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": nova_iso, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(
                context,
                user_id,
                f"Fechado — *{formatar_data_hora_br(nova_iso)}* com *{prof}*. Qual serviço vai ser?{sugestao}"
            )

        # ✅ valida profissional x serviço ANTES de confirmar
        validacao = await validar_profissional_para_servico(dono_id, prof, servico)
        if not validacao["ok"]:
            nomes_validos = validacao["validos"]

            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["profissional_escolhido"] = None
            ctx["ultima_opcao_profissionais"] = nomes_validos
            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": nova_iso,
                "servico": servico,
                "modo_prechecagem": True
            }
            await salvar_contexto_temporario(user_id, ctx)

            lista = ", ".join(nomes_validos) if nomes_validos else "ninguém cadastrado"
            return await _send_and_stop(
                context,
                user_id,
                f"{prof} não faz *{servico}*.\n\n"
                f"Para *{servico}* eu tenho: {lista}.\n"
                "Qual você prefere?"
            )

        # tudo completo -> salva draft e deixa o fluxo principal concluir depois
        ctx["estado_fluxo"] = "agendando"
        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": nova_iso,
            "servico": servico,
            "modo_prechecagem": True
        }
        ctx["pergunta_amanha_mesmo_horario"] = False
        ctx["data_hora_pendente"] = None
        await salvar_contexto_temporario(user_id, ctx)

        return await _send_and_stop(
            context,
            user_id,
            (
                f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(nova_iso)}*.\n"
                f"Responda *sim* para confirmar."
            )
        )

    # =========================================================
    # ✅ (E) Consulta com horário específico = pré-checagem
    # =========================================================
    if eh_consulta(texto_lower) and estado_fluxo == "idle":
        data_hora = ctx.get("data_hora")
        draft_local = ctx.get("draft_agendamento") or {}
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido")
        servico = draft_local.get("servico") or ctx.get("servico")

        ctx["estado_fluxo"] = "consultando"
        if data_hora or prof:
            ctx["ultima_consulta"] = {"data_hora": data_hora, "profissional": prof}

        if data_hora and not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            if not isinstance(ctx.get("ultima_consulta"), dict):
                ctx["ultima_consulta"] = {}
            ctx["ultima_consulta"]["data_hora"] = data_hora

            ctx["draft_agendamento"] = {"profissional": None, "data_hora": data_hora, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Para *{formatar_data_hora_br(data_hora)}*, qual profissional você prefere?"
            )

        if data_hora and prof and not servico:
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
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": data_hora, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Pra eu confirmar se cabe em *{formatar_data_hora_br(data_hora)}*, qual serviço vai ser?{sugestao}"
            )

        await salvar_contexto_temporario(user_id, ctx)

    # =========================================================
    # ✅ (F) Estado aguardando_servico: captura serviço e fecha automático se completo
    # =========================================================
    if estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        draft_local = ctx.get("draft_agendamento") or {}

        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]

        prof_detectado = None
        for nome in nomes_profs:
            if normalizar(nome) in tnorm:
                prof_detectado = nome
                break

        if prof_detectado and " com " in tnorm:
            draft_local["profissional"] = prof_detectado
            ctx["profissional_escolhido"] = prof_detectado
            tnorm_limpo = re.sub(r"\bcom\s+(a|o)\s+" + re.escape(normalizar(prof_detectado)) + r"\b", "", tnorm).strip()
        else:
            tnorm_limpo = tnorm

        servico_in = (tnorm_limpo or "").strip()
        if servico_in:
            draft_local["servico"] = servico_in.lower()
            ctx["servico"] = draft_local["servico"]
            ctx["draft_agendamento"] = draft_local

        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        data_hora = draft_local.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        servico = draft_local.get("servico") or ctx.get("servico")

        if not data_hora:
            ctx["estado_fluxo"] = "aguardando_data"
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual dia e horário você prefere?")

        if not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual profissional você prefere?")

        if not servico:
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual serviço vai ser?")

        dt_naive = _dt_from_iso_naive(data_hora)
        if dt_naive and dt_naive <= _agora_br_naive():
            return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        # ✅ valida profissional x serviço ANTES de confirmar
        validacao = await validar_profissional_para_servico(dono_id, prof, servico)
        if not validacao["ok"]:
            nomes_validos = validacao["validos"]

            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["profissional_escolhido"] = None
            ctx["ultima_opcao_profissionais"] = nomes_validos
            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": data_hora,
                "servico": servico,
                "modo_prechecagem": bool(draft_local.get("modo_prechecagem"))
            }
            await salvar_contexto_temporario(user_id, ctx)

            lista = ", ".join(nomes_validos) if nomes_validos else "ninguém cadastrado"
            return await _send_and_stop(
                context,
                user_id,
                f"{prof} não faz *{servico}*.\n\n"
                f"Para *{servico}* eu tenho: {lista}.\n"
                "Qual você prefere?"
            )

        ctx["estado_fluxo"] = "agendando"
        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico,
            "modo_prechecagem": bool(draft_local.get("modo_prechecagem"))
        }
        await salvar_contexto_temporario(user_id, ctx)

        return await _send_and_stop(
            context,
            user_id,
            (
                f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(data_hora)}*.\n"
                f"Responda *sim* para confirmar."
            )
        )

    # =========================================================
    # ✅ (G) Gatilho explícito "pode agendar/pode marcar"
    # =========================================================
    if eh_gatilho_agendar(texto_lower) or (estado_fluxo == "consultando" and eh_confirmacao(texto_lower)):
        draft_local = ctx.get("draft_agendamento") or {}
        data_hora = draft_local.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft_local.get("servico") or ctx.get("servico")

        if data_hora:
            dt_naive = _dt_from_iso_naive(data_hora)
            if dt_naive and dt_naive <= _agora_br_naive():
                return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        if not prof and not servico:
            ctx["estado_fluxo"] = "aguardando_servico"
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(
                context,
                user_id,
                "Pra eu reservar certinho: qual serviço vai ser e com quem você prefere?"
            )

        if data_hora and prof and not servico:
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
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": data_hora, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Fechado — com *{prof}* em *{formatar_data_hora_br(data_hora)}*. Qual serviço vai ser?{sugestao}"
            )

        if data_hora and servico and not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["draft_agendamento"] = {"profissional": None, "data_hora": data_hora, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Perfeito. Qual profissional você prefere?")

        if not data_hora:
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": None, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual dia e horário você prefere?")

        # ✅ valida profissional x serviço ANTES de confirmar
        validacao = await validar_profissional_para_servico(dono_id, prof, servico)
        if not validacao["ok"]:
            nomes_validos = validacao["validos"]

            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["profissional_escolhido"] = None
            ctx["ultima_opcao_profissionais"] = nomes_validos
            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": data_hora,
                "servico": servico,
                "modo_prechecagem": True
            }
            await salvar_contexto_temporario(user_id, ctx)

            lista = ", ".join(nomes_validos) if nomes_validos else "ninguém cadastrado"
            return await _send_and_stop(
                context,
                user_id,
                f"{prof} não faz *{servico}*.\n\n"
                f"Para *{servico}* eu tenho: {lista}.\n"
                "Qual você prefere?"
            )

        ctx["estado_fluxo"] = "agendando"
        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico,
            "modo_prechecagem": True
        }
        await salvar_contexto_temporario(user_id, ctx)

        return await _send_and_stop(
            context,
            user_id,
            (
                f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(data_hora)}*.\n"
                f"Responda *sim* para confirmar."
            )
        )

    # =========================================================
    # CONFIRMAÇÃO FINAL DE AGENDAMENTO (novo formato vindo do gpt_service)
    # =========================================================
    if eh_confirmacao_pendente_ativa(ctx) and eh_confirmacao(texto_lower):

        _audit_confirmacao("BLOCO_PENDENTE_ENTRADA", ctx, texto_usuario)

        dados_confirmacao = ctx.get("dados_confirmacao_agendamento") or {}

        profissional = dados_confirmacao.get("profissional") or ctx.get("profissional_escolhido")
        servico = dados_confirmacao.get("servico") or ctx.get("servico")
        data_hora = dados_confirmacao.get("data_hora") or ctx.get("data_hora")
        duracao = dados_confirmacao.get("duracao")

        if not duracao and servico:
            duracao = estimar_duracao(servico)

        if profissional and servico and data_hora:
            dados_exec = {
                "profissional": profissional,
                "servico": servico,
                "data_hora": data_hora,
                "duracao": duracao,
                "descricao": formatar_descricao_evento(servico, profissional)
            }

            ctx["aguardando_confirmacao_agendamento"] = False
            ctx.pop("dados_confirmacao_agendamento", None)
            ctx.pop("ultima_opcao_profissionais", None)
            await salvar_contexto_temporario(user_id, ctx)
          
            print("🧪 [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto", flush=True)
            return await executar_acao_gpt(update, context, "criar_evento", dados_exec)

        print("🧪 [AUDIT-CONF:BLOCO_DRAFT] PROFISSIONAL_INVALIDO -> REABRINDO FLUXO", flush=True)
        return await _send_and_stop(
            context,
            user_id,
            "Perdi parte dos dados da confirmação. Me diga novamente o profissional, serviço e horário para eu concluir."
        )

    # =========================================================
    # CONFIRMAÇÃO FINAL DE AGENDAMENTO (fluxo legado por draft)
    # =========================================================
    if estado_fluxo == "agendando" and eh_confirmacao(texto_lower):

        _audit_confirmacao("BLOCO_DRAFT_ENTRADA", ctx, texto_usuario)

        # ✅ Se já existe confirmação estruturada, este bloco legado não pode assumir
        if ctx.get("aguardando_confirmacao_agendamento") and ctx.get("dados_confirmacao_agendamento"):
            pass
        else:
            draft = ctx.get("draft_agendamento") or {}

            profissional = draft.get("profissional")
            servico = draft.get("servico")
            data_hora = draft.get("data_hora")

            if profissional and servico and data_hora:

                # validar se profissional faz o serviço
                profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

                servicos_prof = []
                for p in profs_dict.values():
                    if normalizar(p.get("nome","")) == normalizar(profissional):
                        servicos_prof = p.get("servicos") or []
                        break

                if servico not in servicos_prof:

                    profissionais_validos = []

                    for p in profs_dict.values():
                        nome = p.get("nome")
                        servs = p.get("servicos") or []
                        if servico in servs:
                            profissionais_validos.append(nome)

                    ctx["estado_fluxo"] = "aguardando_profissional"
                    ctx["ultima_opcao_profissionais"] = profissionais_validos
                    ctx["profissional_escolhido"] = None

                    print("🧪 [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto", flush=True)

                    await salvar_contexto_temporario(user_id, ctx)

                    lista = ", ".join(profissionais_validos)

                    print("🧪 [AUDIT-CONF:BLOCO_PENDENTE] FALTOU DADO -> PEDINDO NOVAMENTE", flush=True)

                    return await _send_and_stop(
                        context,
                        user_id,
                        f"{profissional} não faz *{servico}*.\n\n"
                        f"Para *{servico}* eu tenho: {lista}.\n"
                        "Qual você prefere?"
                    )

                # se chegou aqui está válido
                dados_exec = {
                    "servico": servico,
                    "profissional": profissional,
                    "data_hora": data_hora
                }

                ctx["aguardando_confirmacao_agendamento"] = False
                ctx.pop("dados_confirmacao_agendamento", None)
                ctx.pop("ultima_opcao_profissionais", None)
                await salvar_contexto_temporario(user_id, ctx)

                return await executar_acao_gpt(update, context, "criar_evento", dados_exec)

    # =========================================================
    # ESCOLHA DIRETA DE PROFISSIONAL A PARTIR DA ÚLTIMA LISTA
    # =========================================================
    opcoes = ctx.get("ultima_opcao_profissionais") or []

    def _norm_nome(s: str) -> str:
        return normalizar(s or "")

    def _limpar_escolha(txt: str) -> str:
        t = _norm_nome(txt)
        prefixos = [
            "a ", "o ",
            "com a ", "com o ",
            "quero a ", "quero o ",
            "pode ser a ", "pode ser o ",
        ]
        for p in prefixos:
            if t.startswith(p):
                return t[len(p):].strip()
        return t

    escolha_prof = None
    texto_escolha = _limpar_escolha(texto_lower)

    for nome in opcoes:
        if texto_escolha == _norm_nome(nome):
            escolha_prof = nome
            break

    if escolha_prof:

        _audit_confirmacao("ESCOLHA_DIRETA_PROFISSIONAL", ctx, texto_usuario)
        servico = ctx.get("servico") or (ctx.get("draft_agendamento") or {}).get("servico")
        data_hora = ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora")

        if servico and data_hora:
            ctx["profissional_escolhido"] = escolha_prof
            ctx["estado_fluxo"] = "agendando"
            ctx["aguardando_confirmacao_agendamento"] = True
            ctx["dados_confirmacao_agendamento"] = {
                "profissional": escolha_prof,
                "servico": servico,
                "data_hora": data_hora,
                "duracao": estimar_duracao(servico),
                "descricao": formatar_descricao_evento(servico, escolha_prof),
            }
            ctx["draft_agendamento"] = {
                "profissional": escolha_prof,
                "servico": servico,
                "data_hora": data_hora,
                "modo_prechecagem": True
            }
            ctx["ultima_opcao_profissionais"] = []
            await salvar_contexto_temporario(user_id, ctx)

            print("🧪 [AUDIT-CONF:ESCOLHA_DIRETA_PROFISSIONAL] MONTANDO CONFIRMACAO", flush=True)

            return await _send_and_stop(
                context,
                user_id,
                (
                    f"Confirmando: *{servico}* com *{escolha_prof}* "
                    f"em *{formatar_data_hora_br(data_hora)}*.\n"
                    f"Responda *sim* para confirmar."
                )
            )
  
    # =========================================================
    # ✅ (H) Chamada normal ao GPT (com contexto do dono)
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
        return await _send_and_stop(context, user_id, "❌ Ocorreu um erro ao interpretar sua mensagem.")

    resposta_texto = resposta_gpt.get("resposta")
    acao = resposta_gpt.get("acao")
    dados = resposta_gpt.get("dados", {}) or {}

    # ✅ REGRA DE OURO FINAL:
    # Só permite ação mutável quando houver:
    # - continuidade real de agendamento
    # - confirmação pendente
    # Fora disso, consulta pura / desvio bloqueiam criar_evento e cancelar_evento.

    fluxo_agendamento_ativo = tem_contexto_agendamento_ativo(contexto)
    continuando_agendamento = eh_continuacao_de_agendamento(texto_lower, contexto)
    confirmacao_pendente = bool(contexto.get("aguardando_confirmacao_agendamento"))

    consulta_pura = eh_consulta(texto_lower)
    esta_em_modo_consulta = (estado_fluxo == "consultando")

    bloquear_acao_mutavel = False

    if acao in ("criar_evento", "cancelar_evento"):

        # 1) Continuidade real de agendamento sempre libera
        if continuando_agendamento or confirmacao_pendente:
            bloquear_acao_mutavel = False

        # 2) Consulta pura, sem continuidade, bloqueia
        elif consulta_pura:
            bloquear_acao_mutavel = True

        # 3) Se ainda está em modo consulta e a mensagem não é continuidade, bloqueia
        elif esta_em_modo_consulta and not continuando_agendamento:
            bloquear_acao_mutavel = True

        # 4) Se existe fluxo ativo, mas a mensagem atual NÃO é continuação,
        # ainda assim bloqueia ação mutável (ex.: "qual o preço da escova?")
        elif fluxo_agendamento_ativo and not continuando_agendamento:
            bloquear_acao_mutavel = True

    if bloquear_acao_mutavel:
        print(f"🛑 [estado_fluxo] Bloqueado '{acao}' pois mensagem é consulta/desvio: '{texto_lower}'", flush=True)
        return await _send_and_stop(
            context,
            user_id,
            (
                "Entendi. Se você quer *agendar*, me diga:\n"
                "• o *profissional* e o *serviço* (ou eu te ajudo)\n"
                "• o *dia e horário*\n\n"
                "Se quiser só consultar, pode perguntar normalmente."
            )
        )

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
        "buscar_eventos_do_dia",
    }

    handled = False

    if acao:
        if acao not in ACOES_SUPORTADAS:
            print(f"⚠️ Ação '{acao}' não suportada. Ignorando...", flush=True)
            acao = None
            dados = {}
        else:
            handled = await executar_acao_gpt(update, context, acao, dados)

            # Se sua arquitetura depende desse return especial, mantenha
            if acao == "criar_evento":
                return {"acao": "criar_evento", "handled": True}

    if (not acao) and resposta_texto:
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_texto})
        return await _send_and_stop(context, user_id, resposta_texto)

    if acao:
        return {"acao": acao, "handled": bool(handled)}

    return {"resposta": "❌ Não consegui interpretar sua mensagem."}