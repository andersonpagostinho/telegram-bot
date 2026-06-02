async def precheck_e_confirmacao_agendamento(
    context,
    user_id: str,
    ctx: dict,
    servico: str,
    prof: str,
    data_hora: str,
    dono_id: str,
):
    """
    Executa pré-check oficial: validação profissional + conflito + confirmação.
    Equivalente às linhas 6987-7136 do router/principal_router.py

    Paths:
        1. Validação falha: retorna erro, estado = aguardando_profissional
        2. Conflito detectado: retorna sugestões, estado = aguardando_escolha_horario
        3. Sem conflito: retorna confirmação, estado = agendando
    """

    # =========================================================
    # VALIDAÇÃO: profissional x serviço
    # =========================================================
    validacao = await validar_profissional_para_servico(dono_id, prof, servico)
    if not validacao["ok"]:
        nomes_validos = validacao["validos"]

        ctx["estado_fluxo"] = "aguardando_profissional"
        ctx["profissional_escolhido"] = None
        ctx["ultima_opcao_profissionais"] = nomes_validos

        ctx["aguardando_confirmacao_agendamento"] = False
        ctx.pop("dados_confirmacao_agendamento", None)

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

    # =========================================================
    # 🔥 PRE-CHECAGEM DE CONFLITO
    # =========================================================
    print("🔥 [PRE-CHECK] Executando verificação de conflito...", flush=True)
    dt_obj = datetime.fromisoformat(data_hora)

    conflito_info = await verificar_conflito_e_sugestoes_profissional(
        user_id=user_id,
        data=dt_obj.strftime("%Y-%m-%d"),
        hora_inicio=dt_obj.strftime("%H:%M"),
        duracao_min=estimar_duracao(servico),
        profissional=prof,
        servico=servico
    )
    print("🔥 [PRE-CHECK RESULTADO]:", conflito_info, flush=True)

    # =========================================================
    # ❌ TEM CONFLITO → SUGERE ALTERNATIVAS
    # =========================================================
    if conflito_info.get("conflito"):

        sugestoes = conflito_info.get("sugestoes") or []
        alternativo = conflito_info.get("profissional_alternativo")

        # 🔥 salva estado de escolha ANTES de responder
        ctx["estado_fluxo"] = "aguardando_escolha_horario"
        ctx["servico"] = servico
        ctx["profissional_escolhido"] = prof
        ctx["data_hora"] = data_hora
        ctx["ultima_acao"] = "criar_evento"
        ctx["aguardando_confirmacao_agendamento"] = False
        ctx["dados_confirmacao_agendamento"] = None

        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico,
            "modo_prechecagem": True
        }

        # 🔥 formata sugestões
        horarios_formatados = []
        for h in sugestoes[:3]:
            if hasattr(h, "strftime"):
                horarios_formatados.append(h.strftime("%H:%M"))
            else:
                h_str = str(h).strip()
                if " - " in h_str:
                    horarios_formatados.append(h_str)
                else:
                    horarios_formatados.append(h_str)

        ctx["horarios_sugeridos"] = horarios_formatados
        ctx["alternativa_profissional"] = alternativo
        ctx["ultima_opcao_profissionais"] = [prof] + ([alternativo] if alternativo else [])
        ctx["modo_escolha_horario"] = True

        await salvar_contexto_temporario(user_id, ctx)

        print(
            f"🧪 [POS-SAVE CONFLITO] estado_fluxo={ctx.get('estado_fluxo')} | "
            f"modo_escolha_horario={ctx.get('modo_escolha_horario')} | "
            f"horarios_sugeridos={ctx.get('horarios_sugeridos')} | "
            f"data_hora={ctx.get('data_hora')} | "
            f"draft={ctx.get('draft_agendamento')}",
            flush=True
        )

        # 🔥 monta resposta com sugestões
        hora_original = datetime.fromisoformat(data_hora).strftime("%H:%M")

        msg = f"⛔ A *{prof}* já tem atendimento às *{hora_original}*.\n"

        if sugestoes:
            msg += f"\n✅ Estes horários estão livres com *{prof}*:\n"
            for h in sugestoes[:3]:
                if hasattr(h, "strftime"):
                    h = h.strftime("%H:%M")
                msg += f"🔄 {h}\n"

        if alternativo:
            msg += f"\n💡 Se quiser manter *{hora_original}*, posso te encaixar com *{alternativo}*.\n"

        msg += "\nVocê prefere outro horário ou manter o horário com outro profissional?"

        return await _send_and_stop(context, user_id, msg)

    # =========================================================
    # ✅ SEM CONFLITO → CONFIRMA AGENDAMENTO
    # =========================================================

    ctx["estado_fluxo"] = "agendando"

    ctx["draft_agendamento"] = {
        "profissional": prof,
        "data_hora": data_hora,
        "servico": servico,
        "modo_prechecagem": True
    }

    ctx["aguardando_confirmacao_agendamento"] = True

    ctx["dados_confirmacao_agendamento"] = {
        "profissional": prof,
        "servico": servico,
        "data_hora": data_hora,
        "duracao": estimar_duracao(servico),
        "descricao": formatar_descricao_evento(servico, prof),
    }

    ctx["ultima_opcao_profissionais"] = [prof]

    await salvar_contexto_temporario(user_id, ctx)

    return await _send_and_stop(
        context,
        user_id,
        (
            f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(data_hora)}*.\n"
            f"Responda *sim* para confirmar."
        )
    )
