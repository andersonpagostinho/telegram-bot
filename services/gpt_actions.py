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
        return {"resposta": "⚠️ Não encontrei nenhuma ação recente para confirmar.", "acao": None, "dados": {}}

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

    contexto_salvo.update({"ultima_acao": None, "ultima_intencao": None, "dados_anteriores": None})
    await salvar_contexto_temporario(user_id, contexto_salvo)
    return {
        "resposta": f"✅ Ação confirmada: {ultima_intencao.replace('_', ' ').capitalize()}!",
        "acao": ultima_acao,
        "dados": dados_anteriores,
    }
