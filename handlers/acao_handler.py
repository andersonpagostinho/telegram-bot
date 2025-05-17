from datetime import datetime, timedelta
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path, buscar_cliente
from services.session_service import criar_ou_atualizar_sessao, pegar_sessao, resetar_sessao, sincronizar_contexto
from services.profissional_service import buscar_profissionais_por_servico, gerar_mensagem_profissionais_disponiveis, buscar_profissionais_disponiveis_no_horario
from services.normalizacao_service import encontrar_servico_mais_proximo

async def verificar_disponibilidade_profissional(data, user_id):
    """
    Verifica se os profissionais solicitados estão livres no horário desejado.
    Espera os campos: 'data_hora' (ISO), 'duracao' (minutos), 'profissionais' (lista de nomes)
    """
    data_hora_inicio = datetime.fromisoformat(data["data_hora"])
    data_hora_fim = data_hora_inicio + timedelta(minutes=data["duracao"])
    profissionais_solicitados = data["profissionais"]

    eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}

    profissionais_disponiveis = []

    for prof in profissionais_solicitados:
        conflitos = [
            e for e in eventos_dict.values()
            if e.get("data") == data_hora_inicio.strftime("%Y-%m-%d")
            and e.get("profissional", "").lower() == prof.lower()
            and not (
                data_hora_fim <= datetime.fromisoformat(f"{e['data']}T{e['hora_inicio']}")
                or data_hora_inicio >= datetime.fromisoformat(f"{e['data']}T{e['hora_fim']}")
            )
        ]
        if not conflitos:
            profissionais_disponiveis.append(prof)

    return {
        "resposta": (
            f"Profissionais disponíveis para {data_hora_inicio.strftime('%d/%m às %H:%M')}: "
            f"{', '.join(profissionais_disponiveis) if profissionais_disponiveis else 'Nenhum'}"
        ),
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
        servico_normalizado = await encontrar_servico_mais_proximo(mensagem, user_id)

        if not servico_normalizado:
            return "Desculpe, não entendi o serviço. Pode tentar reformular?"

        criar_ou_atualizar_sessao(user_id, {
            "estado": "aguardando_data",
            "servico": servico_normalizado
        })

        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return f"Beleza! Qual a data para o serviço *{servico_normalizado}*?"

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
        try:
            servico = sessao.get("servico")
            if not servico:
                return "⚠️ Algo deu errado, o serviço anterior não foi salvo. Vamos tentar de novo?"

            data_obj = datetime.strptime(sessao["data"], "%d/%m/%Y").date()

            print("📋 Todos os profissionais:", await buscar_subcolecao(f"Clientes/{user_id}/Profissionais"))
            profissionais_filtrados = await buscar_profissionais_por_servico([servico], user_id)
            print("🔍 Profissionais compatíveis com o serviço:", profissionais_filtrados.keys())
            disponiveis_dict = await buscar_profissionais_disponiveis_no_horario(
                user_id=user_id,
                data=data_obj,
                hora=hora,
                duracao=60
            )
            print("🕒 Profissionais livres nesse horário:", disponiveis_dict.keys())

            disponiveis = {
                nome: profissionais_filtrados[nome]
                for nome in disponiveis_dict
                if nome in profissionais_filtrados
            }
            print("✅ Profissionais finais disponíveis (compatíveis + livres):", disponiveis.keys())

            criar_ou_atualizar_sessao(user_id, {
                **sessao,
                "estado": "aguardando_profissional",
                "hora": hora,
                "disponiveis": list(disponiveis.keys())
            })
            await sincronizar_contexto(user_id, pegar_sessao(user_id))

            mensagem = gerar_mensagem_profissionais_disponiveis(
                servico=servico,
                data=data_obj,
                hora=hora,
                disponiveis=disponiveis,
                todos=await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
            )
            print(f"\n📤 MENSAGEM FINAL PARA USUÁRIO:\n{mensagem}")
            return mensagem

        except Exception as e:
            return f"❌ Erro ao verificar disponibilidade: {str(e)}"

    elif sessao["estado"] == "aguardando_profissional":
        profissional_escolhido = mensagem.strip().capitalize()
        disponiveis = sessao.get("disponiveis", [])

        if profissional_escolhido not in disponiveis:
            from services.event_service_async import verificar_conflito_e_sugestoes_profissional

            conflito_info = await verificar_conflito_e_sugestoes_profissional(
                user_id=user_id,
                data=sessao["data"],
                hora_inicio=sessao["hora"],
                duracao_min=60,
                profissional=profissional_escolhido,
                servico=sessao.get("servico", "")
            )

            resposta = f"⚠️ {profissional_escolhido} está com horário ocupado para {sessao['hora']}.\n"

            if conflito_info["sugestoes"]:
                resposta += "🕒 Horários alternativos disponíveis:\n" + "\n".join([f"🔄 {h}" for h in conflito_info["sugestoes"]]) + "\n"

            if conflito_info["profissional_alternativo"]:
                resposta += f"💡 Para esse mesmo horário, {conflito_info['profissional_alternativo']} está disponível.\nDeseja agendar com ela?"

            return resposta

        cliente = await buscar_cliente(user_id)
        is_dono = cliente.get("tipo_usuario") == "dono"

        criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "aguardando_nome_cliente" if is_dono else "completo",
            "profissional": profissional_escolhido
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))

        if is_dono:
            return "👤 Para quem é esse agendamento? (digite o nome da cliente ou deixe em branco)"

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
   
            if sessao.get("nome_cliente"):
                evento["nome_cliente"] = sessao["nome_cliente"]

            evento_id = f"{data_hora_inicio.strftime('%Y%m%d%H%M')}_{servico.replace(' ', '_')}_{profissional_escolhido}"
            await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{evento_id}", evento)

            # ✅ Agendar notificação automática
            from services.notificacao_service import criar_notificacao_agendada
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=f"{evento['descricao']} para {evento['nome_cliente']}" if "nome_cliente" in evento else evento["descricao"],
                data=data_hora_inicio.strftime("%Y-%m-%d"),
                hora_inicio=data_hora_inicio.strftime("%H:%M"),
                canal="telegram",
                minutos_antes=30
            )

            resetar_sessao(user_id)

            return f"✅ Agendamento confirmado com *{profissional_escolhido}* para *{servico}* em *{data}* às *{hora}*."

        except Exception as e:
            return f"❌ Erro ao salvar agendamento: {str(e)}"

    elif sessao["estado"] == "aguardando_nome_cliente":
        nome_cliente = mensagem.strip()
        criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "completo",
            "nome_cliente": nome_cliente if nome_cliente else None
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return await tratar_mensagem_usuario(user_id, "")

    else:
        return "Algo deu errado. Vamos começar de novo?"

# ✅ Exporte aqui para evitar erros de importação
executar_fluxo_com_gpt = tratar_mensagem_usuario
tratar_mensagem_gpt = tratar_mensagem_usuario

__all__ = ["executar_fluxo_com_gpt", "tratar_mensagem_gpt"]
