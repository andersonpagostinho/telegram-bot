import re
import unicodedata


def normalizar_txt(txt: str) -> str:
    txt = (txt or "").lower().strip()
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt if not unicodedata.combining(c))


def _tem(regex: str, t: str) -> bool:
    return bool(re.search(regex, t, flags=re.IGNORECASE))


def extrair_features_conversa(texto: str, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)

    estado_fluxo = ctx.get("estado_fluxo")

    tem_fluxo_ativo = bool(estado_fluxo and estado_fluxo != "idle")
    tem_draft = bool(ctx.get("draft_agendamento"))
    tem_confirmacao_pendente = bool(ctx.get("aguardando_confirmacao_agendamento"))

    # Estrutura interrogativa, não frase fixa
    tem_pergunta = (
        "?" in t
        or _tem(r"^(tem|da|dá|consegue|pode|sera|será|existe|consigo)\b", t)
    )

    # Referência temporal ampla
    tem_tempo = (
        _tem(r"\b\d{1,2}:\d{2}\b", t)
        or _tem(r"\b\d{1,2}h\b", t)
        or _tem(r"\bdia\s+\d{1,2}\b", t)
        or _tem(r"\b(hoje|amanha|amanhã|segunda|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo)\b", t)
        or _tem(r"\b(cedo|manha|manhã|tarde|noite|almoco|almoço|fim do dia|meio dia)\b", t)
    )

    # Pedido amplo: intenção de obter ação/ajuda
    tem_pedido = _tem(
        r"\b(quero|queria|preciso|gostaria|pode|consegue|consigo|ve|vê|ajuda|encaixa|resolver|fazer)\b",
        t
    )

    # Indefinição operacional: cliente não sabe exatamente o horário/serviço
    tem_indefinido = _tem(
        r"\b(algo|alguma|algum|qualquer|coisa|encaixe|um horario|uma hora|um tempo|uma vaga)\b",
        t
    )

    # Domínio de serviço/beleza/atendimento
    tem_contexto_servico = _tem(
        r"\b(cabelo|unha|mao|mão|pe|pé|sobrancelha|barba|pele|rosto|raiz|mecha|"
        r"escova|corte|progressiva|hidratacao|hidratação|luzes|depilacao|depilação|"
        r"alongamento|manicure|pedicure|botox|coloracao|coloração)\b",
        t
    )

    # Ajuste sobre algo anterior
    tem_ajuste = _tem(
        r"\b(mais cedo|mais tarde|outro|outra|trocar|mudar|adiantar|atrasar|pensei melhor|melhor)\b",
        t
    )

    # Cancelamento/desistência
    tem_cancelamento = _tem(
        r"\b(cancelar|desmarcar|nao vou|não vou|nao consigo|não consigo|nao precisa|não precisa|deixa pra la|deixa pra lá)\b",
        t
    )

    # Social forte: só pesa contra se não houver sinal operacional suficiente
    tem_social = _tem(
        r"\b(kkkk|rsrs|churrasco|almocar|almoçar|saudade|te amo|familia|família|"
        r"mercado|compra|pao|pão|me liga|depois te conto|festa|barzinho)\b",
        t
    )

    return {
        "tem_fluxo_ativo": tem_fluxo_ativo,
        "tem_draft": tem_draft,
        "tem_confirmacao_pendente": tem_confirmacao_pendente,
        "tem_pergunta": tem_pergunta,
        "tem_tempo": tem_tempo,
        "tem_pedido": tem_pedido,
        "tem_indefinido": tem_indefinido,
        "tem_contexto_servico": tem_contexto_servico,
        "tem_ajuste": tem_ajuste,
        "tem_cancelamento": tem_cancelamento,
        "tem_social": tem_social,
    }


def classificar_contexto_mensagem(texto: str, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)
    f = extrair_features_conversa(t, ctx)

    if not t:
        return {"modo_conversa": "neutro", "confianca": 0, "motivo": "texto_vazio", "features": f}

    score_operacional = 0
    score_pessoal = 0
    motivos = []

    # Continuidade tem prioridade
    if f["tem_fluxo_ativo"]:
        score_operacional += 35
        motivos.append("fluxo_ativo")

    if f["tem_draft"]:
        score_operacional += 30
        motivos.append("draft_existente")

    if f["tem_confirmacao_pendente"]:
        score_operacional += 45
        motivos.append("confirmacao_pendente")

    # Composições estruturais
    if f["tem_contexto_servico"]:
        score_operacional += 35
        motivos.append("contexto_servico")

    if f["tem_pedido"] and f["tem_contexto_servico"]:
        score_operacional += 35
        motivos.append("pedido_com_servico")

    if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]:
        score_operacional += 45
        motivos.append("busca_aberta_temporal")

    if f["tem_pedido"] and f["tem_tempo"]:
        score_operacional += 30
        motivos.append("pedido_temporal")

    if f["tem_pergunta"] and f["tem_contexto_servico"]:
        score_operacional += 30
        motivos.append("pergunta_sobre_servico")

    if f["tem_ajuste"] and (f["tem_fluxo_ativo"] or f["tem_draft"]):
        score_operacional += 45
        motivos.append("ajuste_de_fluxo")

    if f["tem_cancelamento"] and (f["tem_fluxo_ativo"] or f["tem_draft"] or f["tem_contexto_servico"]):
        score_operacional += 45
        motivos.append("cancelamento_operacional")

    # Social só bloqueia se não houver composição operacional forte
    if f["tem_social"]:
        score_pessoal += 45
        motivos.append("social_forte")

    # Saudação isolada não inicia atendimento
    if t in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "tudo bem"}:
        if f["tem_fluxo_ativo"] or f["tem_draft"]:
            return {"modo_conversa": "operacional", "confianca": 70, "motivo": "saudacao_dentro_de_fluxo", "features": f}
        return {"modo_conversa": "neutro", "confianca": 40, "motivo": "saudacao_sem_contexto", "features": f}

    diferenca = score_operacional - score_pessoal

    if f["tem_social"]:
        score_pessoal += 45
        motivos.append("social_forte")

    # ---------------------------------------------------------
    # Pergunta temporal aberta quase sempre é operacional
    # ---------------------------------------------------------
    if (
        f["tem_pergunta"]
        and f["tem_tempo"]
        and f["tem_indefinido"]
    ):
        score_operacional += 10
        motivos.append("boost_busca_aberta")

    diferenca = score_operacional - score_pessoal

    if score_operacional >= 45 and diferenca >= 5:
        return {
            "modo_conversa": "operacional",
            "confianca": min(score_operacional, 100),
            "motivo": ", ".join(motivos),
            "features": f,
        }

    if score_pessoal >= 45 and score_operacional < 50:
        return {
            "modo_conversa": "pessoal",
            "confianca": min(score_pessoal, 100),
            "motivo": ", ".join(motivos),
            "features": f,
        }

    return {
        "modo_conversa": "neutro",
        "confianca": max(score_operacional, score_pessoal),
        "motivo": ", ".join(motivos) or "sem_composicao_suficiente",
        "features": f,
    }

def detectar_tipo_ajuste_incremental(texto: str) -> str:
    t = normalizar_txt(texto)

    # horário
    if (
        _tem(r"\b(cedo|mais cedo|mais tarde|horario|horário|manha|manhã|tarde|noite)\b", t)
        or _tem(r"\b\d{1,2}:\d{2}\b", t)
        or _tem(r"\b\d{1,2}h\b", t)
    ):
        return "horario"

    # profissional
    if _tem(r"\b(com|trocar para|outra profissional|outro profissional)\b", t):
        return "profissional"

    # data
    if _tem(
        r"\b(amanha|amanhã|hoje|segunda|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo|outro dia)\b",
        t
    ):
        return "data"

    # serviço
    if _tem(
        r"\b(corte|escova|hidratacao|hidratação|luzes|coloracao|coloração|manicure|pedicure|unha)\b",
        t
    ):
        return "servico"

    return "indefinido"

def classificar_intencao_conversacional(texto: str, ctx: dict | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)
    f = extrair_features_conversa(t, ctx)

    if f["tem_cancelamento"]:
        return {"intencao_conversacional": "cancelamento", "confianca": 90, "features": f}

    if f["tem_ajuste"] and (f["tem_fluxo_ativo"] or f["tem_draft"]):

        tipo_ajuste = detectar_tipo_ajuste_incremental(texto)

        return {
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": tipo_ajuste,
            "confianca": 90,
            "features": f
        }

    if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]:
        return {"intencao_conversacional": "consulta_disponibilidade_aberta", "confianca": 88, "features": f}

    if f["tem_pergunta"] and f["tem_contexto_servico"]:
        return {"intencao_conversacional": "consulta_disponibilidade_servico", "confianca": 85, "features": f}

    if f["tem_pedido"] and f["tem_contexto_servico"] and f["tem_tempo"]:
        return {"intencao_conversacional": "agendamento_direto", "confianca": 85, "features": f}

    if f["tem_pedido"] and f["tem_tempo"]:
        return {"intencao_conversacional": "pedido_aberto_temporal", "confianca": 75, "features": f}

    if f["tem_contexto_servico"]:
        return {"intencao_conversacional": "consulta_servico", "confianca": 70, "features": f}

    return {"intencao_conversacional": "indefinida", "confianca": 40, "features": f}