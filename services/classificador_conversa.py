import re
import unicodedata


def normalizar_txt(txt: str) -> str:
    txt = (txt or "").lower().strip()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt


def extrair_features_conversa(texto: str, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)

    tem_fluxo_ativo = bool(ctx.get("estado_fluxo") and ctx.get("estado_fluxo") != "idle")
    tem_confirmacao_pendente = bool(ctx.get("aguardando_confirmacao_agendamento"))
    tem_draft = bool(ctx.get("draft_agendamento"))

    tem_pergunta = "?" in t or t.startswith((
        "tem ", "consegue", "consigo", "da pra", "da para",
        "sera que", "seria possivel", "voce consegue"
    ))

    tem_tempo = bool(
        re.search(r"\b\d{1,2}:\d{2}\b", t)
        or re.search(r"\b\d{1,2}h\b", t)
        or re.search(r"\bdia\s+\d{1,2}\b", t)
        or any(x in t for x in [
            "hoje", "amanha", "depois de amanha",
            "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo",
            "cedo", "manha", "tarde", "noite", "almoco", "fim do dia"
        ])
    )

    tem_pedido = any(x in t for x in [
        "quero", "queria", "preciso", "gostaria",
        "pode", "consegue", "da pra", "da para",
        "ve pra mim", "ve se", "me ajuda", "me encaixa"
    ])

    tem_servico_ou_estetica = any(x in t for x in [
        "cabelo", "unha", "mao", "pe", "sobrancelha",
        "barba", "pele", "rosto", "raiz", "mecha",
        "escova", "corte", "progressiva", "hidratacao",
        "luzes", "depilacao", "alongamento"
    ])

    tem_ajuste = any(x in t for x in [
        "mais cedo", "mais tarde", "outro dia", "outro horario",
        "melhor", "pensei melhor", "trocar", "mudar",
        "adiantar", "atrasar"
    ])

    tem_cancelamento = any(x in t for x in [
        "cancelar", "desmarcar", "nao vou conseguir",
        "nao precisa mais", "deixa pra la"
    ])

    tem_social_forte = any(x in t for x in [
        "kkkk", "rsrs", "churrasco", "almocar", "almoçar",
        "saudade", "te amo", "familia", "mercado",
        "compra pao", "me liga", "depois te conto"
    ])

    return {
        "tem_fluxo_ativo": tem_fluxo_ativo,
        "tem_confirmacao_pendente": tem_confirmacao_pendente,
        "tem_draft": tem_draft,
        "tem_pergunta": tem_pergunta,
        "tem_tempo": tem_tempo,
        "tem_pedido": tem_pedido,
        "tem_servico_ou_estetica": tem_servico_ou_estetica,
        "tem_ajuste": tem_ajuste,
        "tem_cancelamento": tem_cancelamento,
        "tem_social_forte": tem_social_forte,
    }


def classificar_contexto_mensagem(texto: str, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)
    f = extrair_features_conversa(t, ctx)

    if not t:
        return {"modo_conversa": "neutro", "confianca": 0, "motivo": "texto_vazio"}

    score_operacional = 0
    score_pessoal = 0
    motivos = []

    if f["tem_fluxo_ativo"]:
        score_operacional += 35
        motivos.append("fluxo_ativo")

    if f["tem_confirmacao_pendente"]:
        score_operacional += 45
        motivos.append("confirmacao_pendente")

    if f["tem_draft"]:
        score_operacional += 30
        motivos.append("draft_existente")

    if f["tem_servico_ou_estetica"]:
        score_operacional += 35
        motivos.append("contexto_servico_estetica")

    if f["tem_tempo"]:
        score_operacional += 15
        motivos.append("referencia_temporal")

    if f["tem_pedido"]:
        score_operacional += 20
        motivos.append("estrutura_de_pedido")

    if f["tem_pergunta"]:
        score_operacional += 10
        motivos.append("estrutura_de_pergunta")

    if f["tem_ajuste"] and (f["tem_fluxo_ativo"] or f["tem_draft"]):
        score_operacional += 35
        motivos.append("ajuste_sobre_fluxo_existente")

    if f["tem_cancelamento"]:
        score_operacional += 35
        motivos.append("cancelamento_possivel")

    if f["tem_social_forte"]:
        score_pessoal += 40
        motivos.append("contexto_social_forte")

    # Saudação pura sem fluxo não inicia NeoEve
    if t in ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "tudo bem"]:
        if f["tem_fluxo_ativo"] or f["tem_draft"]:
            return {"modo_conversa": "operacional", "confianca": 70, "motivo": "saudacao_dentro_de_fluxo"}
        return {"modo_conversa": "neutro", "confianca": 40, "motivo": "saudacao_sem_contexto"}

    diferenca = score_operacional - score_pessoal

    if score_operacional >= 50 and diferenca >= 15:
        return {
            "modo_conversa": "operacional",
            "confianca": min(score_operacional, 100),
            "motivo": ", ".join(motivos),
            "features": f,
        }

    if score_pessoal >= 40 and score_operacional < 50:
        return {
            "modo_conversa": "pessoal",
            "confianca": min(score_pessoal, 100),
            "motivo": ", ".join(motivos),
            "features": f,
        }

    return {
        "modo_conversa": "neutro",
        "confianca": max(score_operacional, score_pessoal),
        "motivo": ", ".join(motivos) or "sem_sinal_suficiente",
        "features": f,
    }


def classificar_intencao_conversacional(texto: str, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)
    f = extrair_features_conversa(t, ctx)

    if f["tem_cancelamento"]:
        return {"intencao_conversacional": "cancelamento", "confianca": 90, "features": f}

    if f["tem_ajuste"] and (f["tem_fluxo_ativo"] or f["tem_draft"]):
        return {"intencao_conversacional": "ajuste_incremental", "confianca": 90, "features": f}

    if f["tem_pergunta"] and f["tem_tempo"] and not f["tem_servico_ou_estetica"]:
        return {"intencao_conversacional": "consulta_disponibilidade_periodo", "confianca": 80, "features": f}

    if f["tem_pergunta"] and f["tem_servico_ou_estetica"]:
        return {"intencao_conversacional": "consulta_disponibilidade", "confianca": 85, "features": f}

    if f["tem_pedido"] and f["tem_servico_ou_estetica"] and f["tem_tempo"]:
        return {"intencao_conversacional": "agendamento_direto", "confianca": 85, "features": f}

    if f["tem_pedido"] and f["tem_tempo"]:
        return {"intencao_conversacional": "pedido_aberto", "confianca": 75, "features": f}

    if f["tem_servico_ou_estetica"]:
        return {"intencao_conversacional": "consulta_servico", "confianca": 70, "features": f}

    return {"intencao_conversacional": "indefinida", "confianca": 40, "features": f}