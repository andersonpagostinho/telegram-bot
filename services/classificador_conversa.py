import re
import unicodedata


def normalizar_txt(txt: str) -> str:
    txt = (txt or "").lower().strip()
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt if not unicodedata.combining(c))


def _tem(regex: str, t: str) -> bool:
    return bool(re.search(regex, t, flags=re.IGNORECASE))


def extrair_servico_do_catalogo(texto: str, catalogo_servicos: list[str] | None = None) -> str | None:
    """
    Extrai primeiro serviço mencionado que corresponde ao catálogo do tenant.

    Ordem de preferência:
    1. Match exato em ordem de tamanho descrescente (mais específico primeiro)
    2. Match de prefixo
    3. Match de truncamento
    """
    if not catalogo_servicos:
        return None

    t = normalizar_txt(texto)
    if not t:
        return None

    # Ordenar por tamanho DESC, depois manter ordem original para tiebreak determinístico
    servicos_com_indice = [(i, s) for i, s in enumerate(catalogo_servicos)]
    servicos_ordenados = sorted(servicos_com_indice, key=lambda x: len(normalizar_txt(x[1])), reverse=True)

    # FASE 1: Match exato (palavra inteira)
    for _, servico in servicos_ordenados:
        servico_norm = normalizar_txt(servico)
        if not servico_norm:
            continue
        if re.search(rf"\b{re.escape(servico_norm)}\b", t):
            return servico

    # FASE 2: Match de prefixo (primeira palavra)
    for _, servico in servicos_ordenados:
        servico_norm = normalizar_txt(servico)
        if not servico_norm:
            continue
        servico_palavras = servico_norm.split()
        if servico_palavras:
            primeira_palavra = servico_palavras[0]
            if re.search(rf"\b{re.escape(primeira_palavra)}\b", t):
                return servico

    # FASE 3: Match de truncamento ("cort" → "corte")
    for _, servico in servicos_ordenados:
        servico_norm = normalizar_txt(servico)
        if not servico_norm:
            continue
        servico_palavras = servico_norm.split()
        if servico_palavras:
            primeira_palavra = servico_palavras[0]
            if len(primeira_palavra) >= 3:
                truncamentos_texto = re.findall(r"\b\w+\b", t)
                for trunc in truncamentos_texto:
                    if len(trunc) >= 3 and primeira_palavra.startswith(trunc):
                        candidatos = [
                            s for _, s in servicos_ordenados
                            if normalizar_txt(s).split()[0].startswith(trunc)
                        ]
                        if len(candidatos) == 1:
                            return servico

    return None


def extrair_features_conversa(texto: str, ctx: dict | None = None, catalogo_servicos: list[str] | None = None, catalogo_profissionais: list[str] | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)

    estado_fluxo = ctx.get("estado_fluxo")

    tem_fluxo_ativo = bool(estado_fluxo and estado_fluxo != "idle")

    # FASE 4: Validar que draft é válido, não apenas se existe
    from services.draft_validator import eh_draft_valido_para_retomar
    draft = ctx.get("draft_agendamento")
    tem_draft = bool(draft and eh_draft_valido_para_retomar(draft, estado_fluxo))
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
    # P0.6.2: Adicionar "prefiro", "preferi", "escolho" para capturar mudanças de serviço
    tem_pedido = _tem(
        r"\b(quero|queria|preciso|gostaria|pode|consegue|consigo|ve|vê|ajuda|encaixa|resolver|fazer|prefiro|preferi|escolho)\b",
        t
    )

    # Indefinição operacional: cliente não sabe exatamente o horário/serviço
    tem_indefinido = _tem(
        r"\b(algo|alguma|algum|qualquer|coisa|encaixe|um horario|uma hora|um tempo|uma vaga)\b",
        t
    )

    # Domínio de serviço/beleza/atendimento
    # Usar catálogo dinâmico do tenant se disponível
    servico_mencionado = extrair_servico_do_catalogo(t, catalogo_servicos)
    tem_contexto_servico = bool(servico_mencionado)

    # P0: Contexto de serviço via draft (quando texto não menciona serviço explicitamente)
    # Permite que perguntas durante agendamento considerem o serviço do draft
    # Ex: "quais você tem?" com draft={servico: "corte"} → tem contexto
    servico_do_draft = ((ctx or {}).get("draft_agendamento") or {}).get("servico")
    tem_contexto_servico_ou_draft = tem_contexto_servico or bool(servico_do_draft)

    # Ajuste sobre algo anterior
    tem_ajuste = _tem(
        r"\b(mais cedo|mais tarde|outro|outra|trocar|mudar|adiantar|atrasar|pensei melhor|melhor)\b",
        t
    )

    # Cancelamento/desistência
    tem_cancelamento = _tem(
        r"\b(cancelar|cancela|desmarcar|nao vou|não vou|nao consigo|não consigo|nao precisa|não precisa|deixa pra la|deixa pra lá)\b",
        t
    )

    # Agradecimento/encerramento social
    tem_agradecimento = _tem(
        r"\b(obrigado|obrigada|valeu|grato|grata|brigado|brigada|thanks|thanks!|thank you|de nada|fica bem|até logo|tchau|bye|ciao|falou|abraço)\b",
        t
    )

    # Social forte: só pesa contra se não houver sinal operacional suficiente
    tem_social = _tem(
        r"\b(kkkk|rsrs|churrasco|almocar|almoçar|saudade|te amo|familia|família|"
        r"mercado|compra|pao|pão|me liga|depois te conto|festa|barzinho)\b",
        t
    )
    # Referência a profissional: "com [nome]", "trocar profissional", ou "[nome profissional] [verbo]"
    # Padrão básico: validar contra catálogo (não aceitar qualquer palavra após "com")
    tem_ref_profissional_basico = False

    # P0 FIX: "com [QUALQUER_COISA]" é genérico demais → valida apenas contra catálogo
    # Exemplo de falso positivo: "com você" não é referência profissional
    if catalogo_profissionais:
        for prof_nome in catalogo_profissionais:
            prof_norm = normalizar_txt(prof_nome)
            # Match "com [profissional_exato]" com word boundaries
            if _tem(rf"\bcom\s+{re.escape(prof_norm)}\b", t):
                tem_ref_profissional_basico = True
                break

    # Padrões fixos que não requerem catálogo (sempre válidos)
    if not tem_ref_profissional_basico:
        tem_ref_profissional_basico = _tem(
            r"\b(trocar profissional|outra profissional|outro profissional)\b",
            t
        )

    # Padrão dinâmico: profissional no contexto OU na própria mensagem + verbo de disponibilidade
    tem_ref_profissional_dinamica = False

    # 🔥 P0 FIX: Reconhecimento determinístico de profissional em estado aguardando_profissional
    # Se cliente está aguardando escolher profissional, qualquer nome do catálogo é uma resposta válida
    tem_ref_profissional_catalogo = False
    if estado_fluxo == "aguardando_profissional" and catalogo_profissionais:
        for prof_nome in catalogo_profissionais:
            if normalizar_txt(prof_nome) in t:
                tem_ref_profissional_catalogo = True
                break

    # 1. Procurar profissional no contexto (sempre checar)
    profissional_ctx = ctx.get("profissional_escolhido") or (ctx.get("draft_agendamento") or {}).get("profissional")

    # 2. Procurar profissional NA MENSAGEM (usar catálogo dinâmico do tenant)
    profissional_msg = None
    if catalogo_profissionais:
        for prof in catalogo_profissionais:
            if normalizar_txt(prof) in t:
                profissional_msg = prof
                break

    # Usar profissional do contexto OU da mensagem (prioridade contexto)
    profissional_para_buscar = profissional_ctx or profissional_msg

    if profissional_para_buscar:
        # Procurar por profissional + verbo de disponibilidade
        prof_normalized = profissional_para_buscar.lower().strip()
        tem_ref_profissional_dinamica = _tem(
            rf"\b{re.escape(prof_normalized)}\s+(esta|está|tem|consegue|pode|faz|disponi|tá|é)",
            t
        )

    tem_ref_profissional = tem_ref_profissional_basico or tem_ref_profissional_dinamica or tem_ref_profissional_catalogo

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
        "tem_contexto_servico_ou_draft": tem_contexto_servico_ou_draft,
        "servico_mencionado": servico_mencionado,
        "tem_ajuste": tem_ajuste,
        "tem_cancelamento": tem_cancelamento,
        "tem_agradecimento": tem_agradecimento,
        "tem_social": tem_social,
        "tem_ref_profissional": tem_ref_profissional,
        "tem_referencia_pessoa_profissional": tem_referencia_pessoa_profissional,
        "tem_duvida_confianca_profissional": tem_duvida_confianca_profissional,
    }
    
def classificar_contexto_mensagem(texto: str, ctx: dict | None = None, catalogo_servicos: list[str] | None = None, catalogo_profissionais: list[str] | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)
    f = extrair_features_conversa(t, ctx, catalogo_servicos=catalogo_servicos, catalogo_profissionais=catalogo_profissionais)

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

def detectar_tipo_ajuste_incremental(texto: str, catalogo_servicos: list[str] | None = None) -> str:
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

    # serviço — usar catálogo dinâmico do tenant
    if catalogo_servicos:
        servico_mencionado = extrair_servico_do_catalogo(t, catalogo_servicos)
        if servico_mencionado:
            return "servico"

    return "indefinido"

def classificar_intencao_conversacional(texto: str, ctx: dict | None = None, catalogo_servicos: list[str] | None = None, catalogo_profissionais: list[str] | None = None) -> dict:
    ctx = ctx or {}
    t = normalizar_txt(texto)
    f = extrair_features_conversa(t, ctx, catalogo_servicos=catalogo_servicos, catalogo_profissionais=catalogo_profissionais)

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

    # 🔒 NOVO: Detectar novo agendamento APENAS se todas as condições se cumprem (conservador)
    # Novo agendamento com serviço explicitamente mencionado
    servico_mencionado = f.get("servico_mencionado")
    if servico_mencionado and f["tem_pedido"] and f["tem_tempo"]:
        servico_draft = (ctx.get("draft_agendamento") or {}).get("servico")

        if servico_draft and servico_mencionado != servico_draft:
            return {
                "intencao_conversacional": "agendamento_direto",
                "tipo_ajuste_incremental": None,
                "confianca": 85,
                "features": f,
                "motivo": "novo_servico_diferente_draft"
            }
        elif not servico_draft:
            return {
                "intencao_conversacional": "agendamento_direto",
                "tipo_ajuste_incremental": None,
                "confianca": 85,
                "features": f,
                "motivo": "novo_servico_sem_draft"
            }

    # 🔥 EXCEÇÃO: Pergunta clara de disponibilidade (tem_pergunta + tem_tempo + tem_ref_profissional)
    # DEVE ser consulta_disponibilidade_aberta MESMO com draft existente
    # Exemplos: "a bruna esta disponivel amanha as 10?" (pergunta + tempo + profissional)
    if f["tem_pergunta"] and f["tem_tempo"] and f.get("tem_ref_profissional"):
        return {"intencao_conversacional": "consulta_disponibilidade_aberta", "confianca": 88, "features": f}

    if (f["tem_ajuste"] or f.get("tem_ref_profissional")) and (f["tem_fluxo_ativo"] or f["tem_draft"]):

        tipo_ajuste = detectar_tipo_ajuste_incremental(texto, catalogo_servicos=catalogo_servicos)

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

    # Consulta de disponibilidade: pergunta + tempo + (indefinido OU referência profissional específica)
    if f["tem_pergunta"] and f["tem_tempo"] and (f["tem_indefinido"] or f["tem_ref_profissional"]):
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

    # 🔥 FIX P0.6.1: Detectar mudança de agendamento mesmo com "?" (cortesia)
    # Se há pedido + tempo + draft, é agendamento (não consulta)
    # Caso: "agendar unha para terça, teria?" → agendamento, não consulta
    if f["tem_pedido"] and f["tem_tempo"] and f.get("tem_contexto_servico_ou_draft"):
        return {
            "intencao_conversacional": "agendamento_direto",
            "tipo_ajuste_incremental": None,
            "confianca": 85,
            "features": f,
            "motivo": "agendamento_com_draft_existente"
        }

    # P0: Usar contexto_servico_ou_draft para permitir perguntas com contexto do draft
    # Nota: Apenas se NÃO há sinais claros de agendamento (pedido + tempo)
    if f["tem_pergunta"] and f.get("tem_contexto_servico_ou_draft"):
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

    # 🔥 ÚLTIMO RECURSO: Referência contextual a profissional em estado de erro
    # Se tudo mais falhou mas há referência a pessoa + profissionais válidos oferecidos
    # Exemplos: "ok, pode ser ela então" em contexto com profissionais_validos
    profissionais_validos = ctx.get("profissionais_validos", [])
    if (
        f.get("tem_referencia_pessoa_profissional")
        and profissionais_validos
        and f["tem_draft"]
        and ctx.get("motivo_estado") == "profissional_nao_atende_servico"
    ):
        return {
            "intencao_conversacional": "ajuste_incremental",
            "tipo_ajuste_incremental": "profissional",
            "confianca": 75,
            "features": f,
            "motivo": "referencia_contextual_profissional_ultimo_recurso"
        }

    return {"intencao_conversacional": "indefinida", "confianca": 40, "features": f}

def classificar_intencao_com_contexto(
    texto: str,
    contexto: dict | None = None,
    catalogo_servicos: list[str] | None = None,
    catalogo_profissionais: list[str] | None = None
) -> dict:
    """
    Wrapper contextual que enriquece a classificação com informações de mudança de assunto.

    Preserva resultado de classificar_intencao_conversacional() e adiciona:
    - é_mudanca_assunto: bool
    - contexto_ativo: dict com draft, estado, confirmação
    - recomendacao_acao: str declarativa
    - necessita_esclarecimento: bool

    Não modifica Firestore, draft ou estado.
    """
    contexto = contexto or {}

    # 1. Chamar classificador existente (preservar integralmente)
    resultado_base = classificar_intencao_conversacional(
        texto, contexto,
        catalogo_servicos=catalogo_servicos,
        catalogo_profissionais=catalogo_profissionais
    )

    # 2. Extrair contexto ativo
    draft_agendamento = contexto.get("draft_agendamento")
    estado_fluxo = contexto.get("estado_fluxo")
    confirmacao_pendente = contexto.get("aguardando_confirmacao_agendamento", False)

    contexto_ativo = {
        "draft_agendamento": draft_agendamento,
        "estado_fluxo": estado_fluxo,
        "confirmacao_pendente": confirmacao_pendente,
        "proxima_acao_esperada": _extrair_proxima_acao_esperada(estado_fluxo, draft_agendamento)
    }

    # 3. Detectar mudança de assunto
    é_mudanca_assunto = _detectar_mudanca_assunto(
        texto,
        resultado_base.get("intencao_conversacional"),
        contexto_ativo,
        catalogo_servicos,
        catalogo_profissionais
    )

    # 4. Determinar recomendação de ação
    recomendacao_acao = _determinar_recomendacao_acao(
        resultado_base.get("intencao_conversacional"),
        é_mudanca_assunto,
        confirmacao_pendente,
        draft_agendamento
    )

    # 5. Verificar se necessita esclarecimento
    necessita_esclarecimento = resultado_base.get("intencao_conversacional") == "indefinida"

    # 6. Retornar resultado enriquecido
    return {
        **resultado_base,
        "é_mudanca_assunto": é_mudanca_assunto,
        "contexto_ativo": contexto_ativo,
        "recomendacao_acao": recomendacao_acao,
        "necessita_esclarecimento": necessita_esclarecimento
    }


def _extrair_proxima_acao_esperada(estado_fluxo: str | None, draft: dict | None) -> str | None:
    """Extrai qual é o próximo passo esperado baseado no estado."""
    if not draft:
        return None

    if not draft.get("servico"):
        return "aguardando_servico"
    elif not draft.get("profissional"):
        return "aguardando_profissional"
    elif not draft.get("data_hora"):
        return "aguardando_data_hora"
    else:
        return "aguardando_confirmacao"


def _detectar_mudanca_assunto(
    texto: str,
    intencao_base: str,
    contexto_ativo: dict,
    catalogo_servicos: list[str] | None = None,
    catalogo_profissionais: list[str] | None = None
) -> bool:
    """
    Detecta se a mensagem é uma mudança de assunto durante um agendamento.

    Mudança de assunto = pergunta/ajuda FORA do contexto de agendamento esperado
    """
    draft = contexto_ativo.get("draft_agendamento")
    estado = contexto_ativo.get("estado_fluxo")
    proxima_acao = contexto_ativo.get("proxima_acao_esperada")

    if not draft:
        return False

    if proxima_acao == "aguardando_servico" and intencao_base in ["agendamento_direto", "consulta_disponibilidade_servico"]:
        return False
    if proxima_acao == "aguardando_profissional" and intencao_base in ["ajuste_incremental", "agendamento_direto"]:
        return False
    if proxima_acao == "aguardando_data_hora" and intencao_base in ["ajuste_incremental", "agendamento_direto"]:
        return False
    if proxima_acao == "aguardando_confirmacao" and intencao_base in ["confirmacao_agendamento", "negacao_confirmacao_agendamento"]:
        return False

    intencoes_mudanca_assunto = {
        "consulta_disponibilidade_servico",
        "consulta_servico",
        "consultar_agendamentos_usuario",
        "duvida_confianca_profissional",
        "consulta_disponibilidade_aberta"
    }

    if intencao_base in intencoes_mudanca_assunto:
        if estado == "idle" or not estado:
            return False
        return True

    return False


def _determinar_recomendacao_acao(
    intencao: str,
    é_mudanca_assunto: bool,
    confirmacao_pendente: bool,
    draft: dict | None
) -> str:
    """Determina a ação recomendada para gpt_service.py."""

    if é_mudanca_assunto and confirmacao_pendente:
        return "responder_mudanca_em_confirmacao"

    if é_mudanca_assunto and draft:
        return "responder_mudanca_preservar_draft"

    if intencao == "indefinida":
        return "pedir_esclarecimento"

    if intencao in ["confirmacao_agendamento", "negacao_confirmacao_agendamento"]:
        return "processar_confirmacao"

    if intencao in ["ajuste_incremental", "agendamento_direto"]:
        return "continuar_agendamento"

    if intencao == "cancelamento":
        return "processar_cancelamento"

    return "processar_gpt_normal"

def classificar_negacao_confirmacao(texto: str, ctx: dict | None = None) -> bool:
    t = normalizar_txt(texto or "")

    negativos = {
        "nao", "n", "negativo", "recuso", "nope", "nunca"
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
        "nao mesmo",
        "nao, obrigado",
        "passo",
        "na verdade nao",
        "era so pra conferir",
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
    # CAMADA 0: Seleção de Evento (Número)
    # =====================================================
    # P0: Seleção por número somente se há resumo_eventos com múltiplos
    if ctx and "cancelamento_pendente" in ctx:
        cp = ctx.get("cancelamento_pendente", {})
        resumo_eventos = cp.get("resumo_eventos", [])

        if resumo_eventos:
            # Tentar extrair número puro: "1", "2", "3", etc.
            numero_match = re.match(r"^(\d+)", t)
            if numero_match:
                idx = int(numero_match.group(1)) - 1
                if 0 <= idx < len(resumo_eventos):
                    return "selecao_numero"

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


def resolver_referencias_contextuais(
    texto: str,
    contexto: dict | None = None,
    catalogo_profissionais: list[str] | None = None,
    catalogo_servicos: list[str] | None = None
) -> dict:
    """
    Resolve referências implícitas (anáforas) em mensagem conversacional.

    Entrada:
    - texto: mensagem atual do usuário
    - contexto: estado do agendamento (draft, estado_fluxo, etc.)
    - catalogo_profissionais: lista de nomes válidos
    - catalogo_servicos: lista de serviços válidos

    Saída estruturada:
    {
        "referencias_detectadas": bool,
        "profissional_referenciada": str | None,
        "servico_referenciado": str | None,
        "tipo_referencia": str,  # "pronome" | "ordinal" | "temporal" | "composta" | "nenhuma"
        "necessita_esclarecimento": bool,
        "candidatos_profisionais": list,
        "candidatos_servicos": list,
        "confianca": int (0-100),
        "motivo": str
    }

    Não executa ações, apenas interpreta.
    """
    contexto = contexto or {}
    t = normalizar_txt(texto)

    # Resultado padrão
    resultado = {
        "referencias_detectadas": False,
        "profissional_referenciada": None,
        "servico_referenciado": None,
        "tipo_referencia": "nenhuma",
        "necessita_esclarecimento": False,
        "candidatos_profissionais": [],
        "candidatos_servicos": [],
        "confianca": 0,
        "motivo": "Nenhuma referência contextual detectada"
    }

    # 0. REFERÊNCIAS COMPOSTAS (PRIMEIRO — maior especificidade)
    tem_outro_servico = _tem(r"\b(outro servico|outro serviço|outra coisa)\b", t)
    tem_pronome_ela = _tem(r"\b(com\s+ela|ela|a ela)\b", t)
    tem_pronome_ele = _tem(r"\b(com\s+ele|ele|o ele)\b", t)

    tem_composta = (tem_outro_servico and (tem_pronome_ela or tem_pronome_ele)) or \
                   _tem(r"\b(mesmo servico|mesmo serviço).*\b(com\s+outra|outra profissional)\b", t)

    if tem_composta:
        prof_anterior = contexto.get("profissional_escolhido") or \
                       (contexto.get("draft_agendamento") or {}).get("profissional")

        resultado["referencias_detectadas"] = True
        resultado["tipo_referencia"] = "composta"
        resultado["necessita_esclarecimento"] = True
        resultado["confianca"] = 70
        resultado["motivo"] = "Referência composta (serviço + profissional) detectada"

        if prof_anterior:
            resultado["profissional_referenciada"] = prof_anterior

        return resultado

    # 1. PRONOMES PESSOAIS
    if tem_pronome_ela or tem_pronome_ele:
        # Buscar profissional escolhido anteriormente
        prof_anterior = contexto.get("profissional_escolhido") or \
                       (contexto.get("draft_agendamento") or {}).get("profissional")

        if prof_anterior:
            resultado["referencias_detectadas"] = True
            resultado["profissional_referenciada"] = prof_anterior
            resultado["tipo_referencia"] = "pronome"
            resultado["confianca"] = 95
            resultado["motivo"] = f"Pronome 'ela/ele' resolvido para profissional anterior: {prof_anterior}"
            return resultado
        else:
            resultado["referencias_detectadas"] = True
            resultado["necessita_esclarecimento"] = True
            resultado["tipo_referencia"] = "pronome"
            resultado["confianca"] = 30
            resultado["motivo"] = "Pronome 'ela/ele' sem referência anterior - ambíguo"
            return resultado

    # 2. ORDINAIS E INDEFINIDOS (apenas "outra/outro" profissional SEM pronome)
    tem_outra = _tem(r"\b(a outra|outra profissional)\b", t)
    tem_outro = _tem(r"\b(o outro|outro profissional)\b", t)

    if tem_outra or tem_outro:
        # Não selecionar por posição - apenas marcar como ordinário
        resultado["referencias_detectadas"] = True
        resultado["tipo_referencia"] = "ordinal"
        resultado["necessita_esclarecimento"] = True
        resultado["confianca"] = 50
        resultado["motivo"] = "Ordinário 'outra/outro profissional' detectado - requer determinismo"
        return resultado

    # 3. REFERÊNCIAS TEMPORAIS
    tem_naquele_horario = _tem(r"\b(naquele horario|naquele horário|mesmo horario|mesmo horário)\b", t)
    tem_mais_tarde = _tem(r"\b(mais tarde|um pouco mais tarde|depois)\b", t)
    tem_mais_cedo = _tem(r"\b(mais cedo|um pouco mais cedo)\b", t)

    if tem_naquele_horario or tem_mais_tarde or tem_mais_cedo:
        hora_anterior = (contexto.get("draft_agendamento") or {}).get("data_hora") or \
                       (contexto.get("ultima_consulta") or {}).get("data_hora")

        if hora_anterior:
            resultado["referencias_detectadas"] = True
            resultado["tipo_referencia"] = "temporal"
            resultado["confianca"] = 80
            resultado["motivo"] = f"Referência temporal detectada para {hora_anterior}"
            # Não fazer cálculo aqui - deixar para motor determinístico
            resultado["necessita_esclarecimento"] = False if tem_naquele_horario else True
            return resultado

    # 4. SERVIÇOS (apenas ordinário SEM pronome)
    if tem_outro_servico and not (tem_pronome_ela or tem_pronome_ele):
        resultado["referencias_detectadas"] = True
        resultado["tipo_referencia"] = "ordinal"
        resultado["necessita_esclarecimento"] = True
        resultado["confianca"] = 60
        resultado["motivo"] = "Ordinário 'outro serviço' detectado"
        return resultado

    return resultado