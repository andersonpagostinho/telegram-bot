#gpt actions

from utils.contexto_temporario import salvar_contexto_temporario
from utils.gpt_utils import (
    estimar_duracao,
    formatar_data,
    formatar_descricao_evento,
)


async def executar_acao_gpt_por_confirmacao(user_id, contexto_salvo):
    """Executa a ação pendente conforme confirmação do usuário."""
    acao = contexto_salvo.get("ultima_acao")
    dados = contexto_salvo.get("dados_anteriores", {})

    if not acao:
        return {"resposta": "Não encontrei nenhuma ação pendente para continuar.", "acao": None, "dados": {}}

    if acao == "criar_evento":
        profissional = dados.get("profissional") or contexto_salvo.get("profissional_escolhido")
        servico = dados.get("servico") or contexto_salvo.get("servico")
        data_hora = dados.get("data_hora") or contexto_salvo.get("data_hora")

        dados.update({"profissional": profissional, "servico": servico, "data_hora": data_hora})
        contexto_salvo["dados_anteriores"] = dados
        await salvar_contexto_temporario(user_id, contexto_salvo)

        pendentes = []
        if not profissional:
            pendentes.append("profissional")
        if not servico:
            pendentes.append("serviço")
        if not data_hora:
            pendentes.append("dia e horário")

        if pendentes:
            pendentes_str = ", ".join(pendentes)
            return {
                "resposta": f"👍 Claro! Só preciso que você confirme o {pendentes_str} para seguir com o agendamento.",
                "acao": None,
                "dados": {},
            }

        return {"resposta": "Perfeito, estou criando o evento agora.", "acao": acao, "dados": dados}

    return {"resposta": "Certo, seguindo com a ação anterior.", "acao": acao, "dados": dados}


async def executar_confirmacao_generica(user_id, contexto_salvo):
    """Reexecuta a última ação confirmada com base no contexto salvo."""
    ultima_acao = contexto_salvo.get("ultima_acao")
    ultima_intencao = contexto_salvo.get("ultima_intencao")
    dados_anteriores = contexto_salvo.get("dados_anteriores")

    if not ultima_acao or not dados_anteriores:
        return {
            "resposta": "⚠️ Não encontrei nenhuma ação recente para confirmar.",
            "acao": None,
            "dados": {}
        }

    if ultima_acao == "resolver_fora_do_expediente":
        from services.agenda_service import resolver_fora_do_expediente

        profissional = dados_anteriores.get("profissional")
        data = dados_anteriores.get("data")
        hora_inicio = dados_anteriores.get("hora_inicio")
        servico = dados_anteriores.get("servico")
        origem = dados_anteriores.get("origem")

        resultado = await resolver_fora_do_expediente(
            user_id=user_id,
            data_iso=data,
            hora_inicio=hora_inicio,
            duracao_min=estimar_duracao(servico) if servico else 30,
            profissional=profissional,
            servico=servico,
        )

        horario = None
        data_hora_sugerida = None

        if resultado:
            horario = (
                resultado.get("horario_sugerido")
                or resultado.get("horario")
            )
            data_hora_sugerida = resultado.get("data_hora")

        if horario:
            # monta novo data_hora sugerido
            data_hora_sugerida = data_hora_sugerida or f"{data}T{horario}:00"

            draft = contexto_salvo.get("draft_agendamento") or {}
            draft["profissional"] = profissional
            if servico:
                draft["servico"] = servico
            draft["data_hora"] = data_hora_sugerida
            contexto_salvo["draft_agendamento"] = draft

            contexto_salvo["profissional_escolhido"] = profissional
            if servico:
                contexto_salvo["servico"] = servico
            contexto_salvo["data_hora"] = data_hora_sugerida

            # mantém continuidade
            contexto_salvo["ultima_acao"] = "criar_evento"
            contexto_salvo["ultima_intencao"] = "criar_evento"
            contexto_salvo["dados_anteriores"] = {
                "profissional": profissional,
                "servico": servico,
                "data_hora": data_hora_sugerida,
            }

            await salvar_contexto_temporario(user_id, contexto_salvo)

            # 🔥 se veio de troca de profissional, não repete a explicação do expediente
            if origem == "troca_profissional":
                return {
                    "resposta": f"O horário mais próximo com {profissional} é às {horario}.\nPosso agendar pra você? 😊",
                    "acao": None,
                    "dados": {}
                }

            return {
                "resposta": f"O horário mais próximo com {profissional} é às {horario}.\nPosso seguir com esse horário pra você? 😊",
                "acao": None,
                "dados": {}
            }

        contexto_salvo.update({
            "ultima_acao": None,
            "ultima_intencao": None,
            "dados_anteriores": None,
        })
        await salvar_contexto_temporario(user_id, contexto_salvo)

        if origem == "troca_profissional":
            return {
                "resposta": f"Não encontrei um horário próximo com {profissional} nesse dia. Quer que eu veja outro dia pra você?",
                "acao": None,
                "dados": {}
            }

        return {
            "resposta": "Não encontrei outro horário próximo nesse dia. Quer que eu veja outro dia?",
            "acao": None,
            "dados": {}
        }

    if ultima_acao == "criar_evento":
        profissional = contexto_salvo.get("profissional_escolhido")
        servico = contexto_salvo.get("servico")
        data_hora = dados_anteriores.get("data_hora")

        if profissional and servico and data_hora:
            duracao = estimar_duracao(servico)
            contexto_salvo.update({
                "evento_criado": True,
                "ultima_acao": None,
                "ultima_intencao": None,
                "dados_anteriores": None,
            })
            await salvar_contexto_temporario(user_id, contexto_salvo)
            return {
                "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                "acao": "criar_evento",
                "dados": {
                    "data_hora": data_hora,
                    "descricao": formatar_descricao_evento(servico, profissional),
                    "duracao": duracao,
                    "profissional": profissional,
                },
            }
        else:
            pendentes = []
            if not profissional:
                pendentes.append("profissional")
            if not servico:
                pendentes.append("serviço")
            if not data_hora:
                pendentes.append("dia e horário")
            pendentes_str = ", ".join(pendentes)
            return {
                "resposta": f"⚠️ Para continuar com o agendamento, preciso que você informe o {pendentes_str}.",
                "acao": None,
                "dados": {},
            }

    contexto_salvo.update({
        "ultima_acao": None,
        "ultima_intencao": None,
        "dados_anteriores": None
    })
    await salvar_contexto_temporario(user_id, contexto_salvo)
    return {
        "resposta": f"✅ Ação confirmada: {ultima_intencao.replace('_', ' ').capitalize()}!",
        "acao": ultima_acao,
        "dados": dados_anteriores,
    }