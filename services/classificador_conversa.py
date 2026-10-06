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
        or _tem(r"\b(quem|qual|quais|quando|onde|como)\b", t)
        or _tem(r"\bquem\s+(voce|você)?\s*tem\b", t)
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
    tem_ref_profissional = _tem(
        r"\b(com\s+[a-zA-ZÀ-ÿ]+|trocar profissional|outra profissional|outro profissional)\b",
        t
    )

    # Dúvida/insegurança sobre profissional — por composição, não frase fixa
    tem_sinal_qualidade_confianca = _tem(
        r"\b(boa|bom|melhor|bem|qualidade|confio|confiavel|confiável|experiente|recomenda|indicaria|segura|seguro|habilidosa|habilidoso|caprichosa|caprichoso)\b",
        t
    )

    tem_sinal_inseguranca = _tem(
        r"\b(conheco|conheço|nunca|primeira vez|nao sei|não sei|duvida|dúvida|receio|medo|estranho|estranha)\b",
        t
    )

    tem_sinal_comparacao = _tem(
        r"\b(quanto|igual|comparado|comparada|melhor|pior|mesmo nivel|mesmo nível|parecida|parecido)\b",
        t
    )

    tem_referencia_pessoa_profissional = (
        _tem(r"\b(ela|ele|profissional|cabeleireira|manicure|atendente|pessoa)\b", t)
        or tem_ref_profissional
        or bool(ctx.get("profissional_escolhido"))
        or bool((ctx.get("draft_agendamento") or {}).get("profissional"))
    )

    tem_duvida_confianca_profissional = (
        tem_confirmacao_pendente
        and tem_pergunta
        and tem_referencia_pessoa_profissional
        and (
            tem_sinal_qualidade_confianca
            or tem_sinal_inseguranca
            or tem_sinal_comparacao
        )
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
        "tem_ref_profissional": tem_ref_profissional,
        "tem_duvida_confianca_profissional": tem_duvida_confianca_profissional,
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

    # Consulta de disponibilidade: pergunta + temporal + serviço
    if f["tem_pergunta"] and f["tem_tempo"] and f["tem_contexto_servico"]:
        score_operacional += 45
        motivos.append("consulta_disponibilidade")
        print("[CLASSIFICADOR_FIX] consulta_disponibilidade=True", flush=True)

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

    if _tem(r"\b(com\s+[a-zA-ZÀ-ÿ]+|trocar para|outra profissional|outro profissional)\b", t):
        return "profissional"

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

    # 🔒 RESPECT LOTE_3B: Se LOTE_3B já setou intenção P0 determinística, respeitá-la
    # (LOTE_3B é mais preciso que classificador genérico)
    intencao_p0_pre_existente = ctx.get("intencao_conversacional")
    if intencao_p0_pre_existente in ["confirmacao_agendamento", "negacao_confirmacao_agendamento"]:
        return {
            "intencao_conversacional": intencao_p0_pre_existente,
            "tipo_ajuste_incremental": None,
            "confianca": 95,  # Alta confiança porque LOTE_3B já validou
            "features": f,
            "motivo": "respeitando_lote_3b"
        }

    # =====================================================
    # 🔥 NEGAÇÃO / DESISTÊNCIA EM CONFIRMAÇÃO PENDENTE
    # GPT/classificador interpreta; router executa.
    # =====================================================
    if ctx.get("aguardando_confirmacao_agendamento") is True:
        if classificar_negacao_confirmacao(texto, ctx):
            return {
                "intencao_conversacional": "negacao_confirmacao_agendamento",
                "tipo_ajuste_incremental": None,
                "confianca": 90,
                "features": f
            }

    # =====================================================
    # DÚVIDA / INSEGURANÇA SOBRE PROFISSIONAL
    # Não executa ação. Só permite resposta humana guiada.
    # =====================================================
    if f.get("tem_duvida_confianca_profissional"):
        return {
            "intencao_conversacional": "duvida_confianca_profissional",
            "tipo_ajuste_incremental": None,
            "confianca": 92,
            "features": f
        }

    if f["tem_cancelamento"]:
        return {"intencao_conversacional": "cancelamento", "confianca": 90, "features": f}

    if (f["tem_ajuste"] or f.get("tem_ref_profissional")) and (f["tem_fluxo_ativo"] or f["tem_draft"]):

        tipo_ajuste = detectar_tipo_ajuste_incremental(texto)

        return {
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": tipo_ajuste,
            "confianca": 90,
            "features": f
        }

    # ✅ NOVO: Detectar consulta dos próprios agendamentos do usuário
    # Padrão: pergunta + tempo + posessivo (tenho, meu, agendado, marcado)
    tem_posessivo = _tem(r"\b(tenho|meu|minha|meus|minhas|agendado|marcado|compromisso|o que tenho|qual é meu)\b", t)
    if f["tem_pergunta"] and f["tem_tempo"] and tem_posessivo:
        return {"intencao_conversacional": "consultar_agendamentos_usuario", "confianca": 85, "features": f}

    if f["tem_pergunta"] and f["tem_tempo"] and f["tem_indefinido"]:
        return {"intencao_conversacional": "consulta_disponibilidade_aberta", "confianca": 88, "features": f}

    # 🔒 EXCEÇÃO: fluxo operacional ativo + serviço + tempo = ajuste de horário (não consulta)
    # Regra: em contexto de confirmação pendente, "pode ver?" + "às 10" é ajuste, não consulta
    if (
        f["tem_fluxo_ativo"]
        and f["tem_contexto_servico"]
        and f["tem_tempo"]
    ):
        return {
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": "horario",
            "confianca": 90,
            "features": f,
        }

    # ✅ NOVO: Detectar consulta dos próprios agendamentos por serviço específico
    # Padrão: pergunta + serviço + posessivo (tenho, meu, agendado)
    tem_posessivo_servico = _tem(r"\b(tenho|meu|minha|agendado|marcado)\b", t) and f["tem_contexto_servico"]
    if f["tem_pergunta"] and tem_posessivo_servico:
        return {"intencao_conversacional": "consultar_agendamentos_usuario", "confianca": 85, "features": f}

    if f["tem_pergunta"] and f["tem_contexto_servico"]:
        return {"intencao_conversacional": "consulta_disponibilidade_servico", "confianca": 85, "features": f}

    if f["tem_pedido"] and f["tem_contexto_servico"] and f["tem_tempo"]:
        return {"intencao_conversacional": "agendamento_direto", "confianca": 85, "features": f}

    if f["tem_pedido"] and f["tem_tempo"]:
        return {"intencao_conversacional": "pedido_aberto_temporal", "confianca": 75, "features": f}

    if f["tem_contexto_servico"] and (f["tem_fluxo_ativo"] or f["tem_draft"]):
        return {
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": "servico",
            "confianca": 90,
            "features": f
        }

    if f["tem_contexto_servico"]:
        return {"intencao_conversacional": "consulta_servico", "confianca": 70, "features": f}

    return {"intencao_conversacional": "indefinida", "confianca": 40, "features": f}

def classificar_negacao_confirmacao(texto: str, ctx: dict | None = None) -> bool:
    t = normalizar_txt(texto or "")

    negativos = {
        "nao", "n", "negativo", "recuso"
    }

    if t in negativos:
        return True

    sinais_negacao = [
        "nao quero",
        "nao precisa",
        "melhor nao",
        "deixa",
        "esquece",
        "cancela",
        "desisti",
        "vou ver depois",
        "depois eu vejo",
        "agora nao",
    ]

    return any(s in t for s in sinais_negacao)


def classificar_confirmacao_cancelamento(texto: str, ctx: dict | None = None) -> str:
    """
    Classifica resposta de usuário a confirmação de cancelamento de evento.

    Contexto: estado_fluxo == "aguardando_confirmacao_cancelamento"

    Retorna EXATAMENTE UMA destas categorias:
    - "confirmacao"  → Usuário confirma o cancelamento
    - "negacao"      → Usuário rejeita o cancelamento
    - "ambiguo"      → Resposta indeterminada (requer clarificação)

    Responsabilidades:
    - Interpreta apenas, não executa ações
    - Não acessa Firestore
    - Não busca eventos
    - Não modifica contexto

    Semântica crítica:
    - "cancela" = CONFIRMAÇÃO (não negação!)
    - "pode" sozinho = AMBÍGUO (não confirmação!)
    - "deixa para depois" = AMBÍGUO (não negação!)
    - Frases complexas = AMBÍGUO
    """

    if not texto:
        return "ambiguo"

    t = normalizar_txt(texto or "")

    # =====================================================
    # CAMADA 1: Confirmações Simples (Match Exato)
    # =====================================================
    confirmacoes_simples = {"sim", "s", "ok", "claro", "isso", "isso mesmo", "mesmo"}
    if t in confirmacoes_simples:
        return "confirmacao"

    # =====================================================
    # CAMADA 2: Negações Simples (Match Exato)
    # =====================================================
    negacoes_simples = {"nao", "não"}
    if t in negacoes_simples:
        return "negacao"

    # =====================================================
    # CAMADA 3: Análise Composicional
    # =====================================================

    # CONFIRMAÇÃO: "pode" + verbo de ação (mas NÃO se for remarcação)
    if "pode" in t and ("cancelar" in t or "desmarcar" in t or "fazer" in t):
        # Verificar se não há pedido de remarcação simultâneo
        if not ("e marca" in t or "e coloca" in t or "e marcar" in t):
            return "confirmacao"

    # CONFIRMAÇÃO: "sim" + reafirmação inequívoca
    if "sim" in t and ("pode" in t or "ok" in t or "claro" in t or "mesmo" in t):
        return "confirmacao"

    # CONFIRMAÇÃO: "cancela" isolado (usuário confirma explicitamente)
    if t == "cancela" or t == "cancele":
        return "confirmacao"

    # NEGAÇÃO: "nao quero" ou "não quero"
    if "nao quero" in t or "não quero" in t:
        return "negacao"

    # NEGAÇÃO: "deixa como está" (manutenção status quo)
    if "deixa" in t and ("como" in t or "esta" in t or "está" in t):
        return "negacao"

    # NEGAÇÃO: "não precisa" ou "nao precisa"
    if "nao precisa" in t or "não precisa" in t:
        return "negacao"

    # NEGAÇÃO: "não cancele" ou "nao cancele"
    if ("nao cancele" in t or "não cancele" in t or
        "nao cancela" in t or "não cancela" in t):
        return "negacao"

    # NEGAÇÃO: "esquece" ou "esqueça"
    if "esquece" in t or "esqueça" in t:
        return "negacao"

    # NEGAÇÃO: "melhor não" ou "melhor nao"
    if ("melhor nao" in t or "melhor não" in t):
        return "negacao"

    # =====================================================
    # CAMADA 4: Baixa Confiança
    # =====================================================
    if "acho que" in t:
        return "ambiguo"

    # =====================================================
    # CAMADA 5: Ambiguidades Explícitas
    # =====================================================

    # Incerteza explícita
    if t in ["talvez", "talvez sim", "talvez não", "talvez nao"]:
        return "ambiguo"

    if "talvez" in t:
        return "ambiguo"

    # "não sei"
    if "nao sei" in t or "não sei" in t:
        return "ambiguo"

    # Adiamentos: "depois eu vejo", "vou pensar", etc.
    if ("depois" in t and ("vejo" in t or "pensar" in t or "ver" in t)):
        return "ambiguo"

    # "deixa para depois" (sem "como está" = ambíguo)
    if "deixa" in t and "depois" in t:
        return "ambiguo"

    # "pode" SOZINHO (sem verbo de ação)
    if t == "pode":
        return "ambiguo"

    # "pode ser"
    if "pode ser" in t:
        return "ambiguo"

    # Impossibilidade/mudança de circunstância (NÃO é negação)
    if "nao consigo" in t or "não consigo" in t:
        return "ambiguo"

    if "nao vou conseguir" in t or "não vou conseguir" in t:
        return "ambiguo"

    # "não vou" (dupla interpretação)
    if t == "nao vou" or t == "não vou":
        return "ambiguo"

    # "vamos ver"
    if "vamos ver" in t or "vamos vendo" in t:
        return "ambiguo"

    # Frases complexas com múltiplas interpretações
    # Padrão: expressão emocional + "deixa" + tempo
    if re.search(r"(pena|triste|ruins|que pior).*deixa", t):
        return "ambiguo"

    if re.search(r"deixa.*outra hora", t):
        return "ambiguo"

    # Pedidos de remarcação/alteração
    if ("marca" in t and "outro" in t) or ("marca" in t and "amanha" in t) or ("marca" in t and "amanhã" in t):
        return "ambiguo"

    if "coloca" in t and ("outro" in t or "amanha" in t or "amanhã" in t):
        return "ambiguo"

    if "mudar" in t and ("horario" in t or "horário" in t):
        return "ambiguo"

    # =====================================================
    # FALLBACK: Qualquer outra coisa
    # =====================================================
    return "ambiguo"