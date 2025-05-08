from datetime import datetime, timedelta
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path
from services.session_service import criar_ou_atualizar_sessao, pegar_sessao, resetar_sessao, sincronizar_contexto
from services.profissional_service import buscar_profissionais_por_servico

async def verificar_disponibilidade_profissional(data, user_id):
    data_hora_inicio = datetime.fromisoformat(data["data_hora"])
    data_hora_fim = data_hora_inicio + timedelta(minutes=data["duracao"])
    profissionais_solicitados = data["profissionais"]

    eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    profissionais_disponiveis = []

    for prof in profissionais_solicitados:
        conflitos = [
            e for e in eventos_dict.values()
            if e.get("descricao", "").lower().find(prof.lower()) != -1
            and not (
                data_hora_fim <= datetime.fromisoformat(e["hora_inicio"]) or
                data_hora_inicio >= datetime.fromisoformat(e["hora_fim"])
            )
        ]
        if not conflitos:
            profissionais_disponiveis.append(prof)

    return {
        "resposta": f"Profissionais disponíveis para {data_hora_inicio.strftime('%d/%m às %H:%M')}: {', '.join(profissionais_disponiveis) if profissionais_disponiveis else 'Nenhum'}",
        "disponiveis": profissionais_disponiveis
    }

async def tratar_mensagem_usuario(user_id, mensagem):
    sessao = pegar_sessao(user_id)

    if not sessao:
        criar_ou_atualizar_sessao(user_id, {
            "estado": "aguardando_servico"
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return "Oi! Qual serviço você deseja agendar?"

    elif sessao["estado"] == "aguardando_servico":
        criar_ou_atualizar_sessao(user_id, {
            "estado": "aguardando_data",
            "servico": mensagem
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return f"Beleza! Qual a data para o {mensagem}?"

    elif sessao["estado"] == "aguardando_data":
        criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "aguardando_horario",
            "data": mensagem
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return f"Perfeito. E qual horário?"

    elif sessao["estado"] == "aguardando_horario":
        hora = mensagem
        criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "aguardando_profissional",
            "hora": hora
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))

        try:
            servico = sessao.get("servico")
            if not servico:
                return "⚠️ Algo deu errado, o serviço anterior não foi salvo. Vamos tentar de novo?"

            data_hora_iso = datetime.strptime(f"{sessao['data']} {hora}", "%d/%m/%Y %H:%M").isoformat()
            profissionais_filtrados = await buscar_profissionais_por_servico([servico], user_id)
            profissionais_teste = list(profissionais_filtrados.keys())

            disponibilidade = await verificar_disponibilidade_profissional({
                "data_hora": data_hora_iso,
                "duracao": 60,
                "profissionais": profissionais_teste
            }, user_id)

            criar_ou_atualizar_sessao(user_id, {
                **sessao,
                "estado": "aguardando_profissional",
                "hora": hora,
                "disponiveis": disponibilidade["disponiveis"]
            })
            await sincronizar_contexto(user_id, pegar_sessao(user_id))

            return f"Profissionais disponíveis: {', '.join(disponibilidade['disponiveis'])}. Com quem deseja agendar?"
        except Exception as e:
            return f"❌ Erro ao verificar disponibilidade: {str(e)}"

    elif sessao["estado"] == "aguardando_profissional":
        profissional_escolhido = mensagem.strip().capitalize()
        disponiveis = sessao.get("disponiveis", [])

        if profissional_escolhido not in disponiveis:
            return f"❌ {profissional_escolhido} não está disponível para esse horário. Escolha entre: {', '.join(disponiveis)}."

        criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "completo",
            "profissional": profissional_escolhido
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))

        try:
            servico = sessao.get("servico")
            data = sessao.get("data")
            hora = sessao.get("hora")

            data_hora_inicio = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M")
            data_hora_fim = data_hora_inicio + timedelta(minutes=60)

            evento = {
                "descricao": f"{servico} com {profissional_escolhido}",
                "hora_inicio": data_hora_inicio.isoformat(),
                "hora_fim": data_hora_fim.isoformat(),
                "profissional": profissional_escolhido,
                "status": "pendente",
                "criado_em": datetime.now().isoformat()
            }

            evento_id = f"{data_hora_inicio.strftime('%Y%m%d%H%M')}_{servico.replace(' ', '_')}_{profissional_escolhido}"
            await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{evento_id}", evento)

            # ✅ Agendar notificação automática
            from services.notificacao_service import criar_notificacao_agendada
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=evento["descricao"],
                data=data_hora_inicio.strftime("%Y-%m-%d"),
                hora_inicio=data_hora_inicio.strftime("%H:%M"),
                canal="telegram",
                minutos_antes=30
            )

            resetar_sessao(user_id)

            return f"✅ Agendamento confirmado com *{profissional_escolhido}* para *{servico}* em *{data}* às *{hora}*."

        except Exception as e:
            return f"❌ Erro ao salvar agendamento: {str(e)}"

    else:
        return "Algo deu errado. Vamos começar de novo?"

# ✅ Exporte aqui para evitar erros de importação
executar_fluxo_com_gpt = tratar_mensagem_usuario
tratar_mensagem_gpt = tratar_mensagem_usuario

__all__ = ["executar_fluxo_com_gpt", "tratar_mensagem_gpt"]
