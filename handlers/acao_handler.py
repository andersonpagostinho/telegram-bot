from datetime import datetime, timedelta
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path, buscar_cliente
from services.session_service import criar_ou_atualizar_sessao, pegar_sessao, resetar_sessao, sincronizar_contexto
from services.profissional_service import buscar_profissionais_por_servico, gerar_mensagem_profissionais_disponiveis, buscar_profissionais_disponiveis_no_horario 
from services.normalizacao_service import encontrar_servico_mais_proximo
from unidecode import unidecode
from utils.interpretador_datas import interpretar_data_e_hora
from services.informacao_service import responder_consulta_informativa


async def verificar_disponibilidade_profissional(data, user_id):
    print("⚠️ [acao_handler] tratador direto foi chamado!")
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
    print("⚠️ [acao_handler] tratador direto foi chamado!")

    # 🧠 Verifica se a mensagem é uma consulta informativa
    resposta_info = await responder_consulta_informativa(mensagem, user_id)
    if resposta_info:
        return resposta_info

    sessao = await pegar_sessao(user_id)

    if not sessao:
        await criar_ou_atualizar_sessao(user_id, {"estado": "aguardando_servico"})
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return "Oi! Qual serviço você deseja agendar?"

    elif sessao["estado"] == "aguardando_servico":
        servico_normalizado = await encontrar_servico_mais_proximo(mensagem, user_id)

        if not servico_normalizado:
            profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")
            servicos_set = set()
            for p in profissionais:
                for serv in p.get("servicos", []):
                    servicos_set.add(serv.lower().strip())

            if servicos_set:
                servicos_formatados = "\n".join([f"• {s.capitalize()}" for s in sorted(servicos_set)])
                return (
                    "✨ Aqui estão os serviços disponíveis no momento:\n\n"
                    f"{servicos_formatados}\n\n"
                    "Qual deles você gostaria?"
                )
            return "❌ Nenhum serviço foi encontrado no sistema. Verifique com o administrador."

        await criar_ou_atualizar_sessao(user_id, {
            "estado": "aguardando_data",
            "servico": servico_normalizado
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return f"Beleza! Qual a data para o serviço *{servico_normalizado}*?"

    elif sessao["estado"] == "aguardando_data":
        # tenta interpretar a data informada e salvar normalizada
        dt = interpretar_data_e_hora(mensagem)
        if dt:
            data_norm = dt.date().strftime("%d/%m/%Y")
        else:
            # fallback: salva como veio (mas isso é o que dá problema)
            data_norm = mensagem.strip()

        await criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "aguardando_horario",
            "data": data_norm
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return f"Perfeito. E qual horário?"

    elif sessao["estado"] == "aguardando_horario":
        try:
            import re

            hora_raw = (mensagem or "").strip()
            texto = hora_raw.lower()

            # Detecta "só hora"
            so_hora = bool(re.match(r"^(?:às|as)?\s*\d{1,2}(:\d{2})?\s*(?:h\d{0,2})?$", texto))

            if not so_hora:
                # Se veio data+hora (ex: "20/02 15:20" ou "amanhã 15:20")
                dt_mix = interpretar_data_e_hora(mensagem)
                if dt_mix:
                    await criar_ou_atualizar_sessao(user_id, {
                        **sessao,
                        "data": dt_mix.date().strftime("%d/%m/%Y"),
                        "hora": dt_mix.strftime("%H:%M"),
                    })
                    await sincronizar_contexto(user_id, pegar_sessao(user_id))
                    sessao = await pegar_sessao(user_id)
                    hora_raw = sessao.get("hora") or hora_raw

            hora = hora_raw

            servico = sessao.get("servico")

            if not servico:
                return "⚠️ Algo deu errado, o serviço anterior não foi salvo. Vamos tentar de novo?"

            # garante data válida na sessão
            data_str = (sessao.get("data") or "").strip()

            data_obj = None
            try:
                data_obj = datetime.strptime(data_str, "%d/%m/%Y").date()
            except Exception:
                # tenta interpretar novamente com interpretador inteligente
                dt_data = interpretar_data_e_hora(data_str)
                if dt_data:
                    data_obj = dt_data.date()
                    # salva corrigido na sessão
                    await criar_ou_atualizar_sessao(user_id, {**sessao, "data": data_obj.strftime("%d/%m/%Y")})
                    sessao = await pegar_sessao(user_id)

            if not data_obj:
                return "📅 Não entendi a data. Pode informar no formato 20/02/2026 ou dizer 'amanhã'?"

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

            await criar_ou_atualizar_sessao(user_id, {
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
        texto_normalizado = unidecode(mensagem.lower())
        print("📨 Mensagem recebida:", mensagem)
        print("🔍 Texto normalizado:", texto_normalizado)
        sessao = await pegar_sessao(user_id)
        disponiveis = sessao.get("disponiveis", [])
        disponiveis_normalizados = [unidecode(p.lower()) for p in disponiveis]

        # ⏱️ Detecta nova data e hora na mesma mensagem
        data_hora_detectada = interpretar_data_e_hora(mensagem)
        print("🕵️‍♂️ Data/hora detectada:", data_hora_detectada)
        if data_hora_detectada:
            nova_data = data_hora_detectada.date().strftime("%d/%m/%Y")
            nova_hora = data_hora_detectada.time().strftime("%H:%M")
            data_obj = data_hora_detectada.date()
            servico = sessao.get("servico")

            if servico:
                profissionais_filtrados = await buscar_profissionais_por_servico([servico], user_id)
                disponiveis_dict = await buscar_profissionais_disponiveis_no_horario(
                    user_id=user_id,
                    data=data_obj,
                    hora=nova_hora,
                    duracao=60
                )
                disponiveis = {
                    nome: profissionais_filtrados[nome]
                    for nome in disponiveis_dict
                    if nome in profissionais_filtrados
                }

                await criar_ou_atualizar_sessao(user_id, {
                    **sessao,
                    "data": nova_data,
                    "hora": nova_hora,
                    "disponiveis": list(disponiveis.keys()),
                    "estado": "aguardando_profissional"
                })
                await sincronizar_contexto(user_id, pegar_sessao(user_id))

                if not disponiveis:
                    return f"❌ Nenhum profissional disponível para {nova_data} às {nova_hora}. Deseja tentar outro horário?"

        # 🎯 Identifica profissional com base na mensagem original
        profissional_escolhido = None
        for nome in disponiveis:
            if unidecode(nome.lower()) in texto_normalizado:
                profissional_escolhido = nome
                break

        #if not profissional_escolhido:
        #    return "🔄 Estamos no meio de um agendamento. Por favor, diga o nome da profissional, a data ou o horário desejado para continuar."

        # ⛔ Verifica conflitos
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

        # ✅ Se tudo certo, segue fluxo para confirmar agendamento
        cliente = await buscar_cliente(user_id)
        is_dono = cliente.get("tipo_usuario") == "dono"

        await criar_ou_atualizar_sessao(user_id, {
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

            from services.notificacao_service import criar_notificacao_agendada
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=descricao,
                data=data,
                hora_inicio=hora_inicio,
                minutos_antes=30,
                destinatario_user_id=user_id,  # padrão: quem está no chat recebe
                alvo_evento={"data": data, "hora_inicio": hora_inicio}
            )
            await resetar_sessao(user_id)

            return f"✅ Agendamento confirmado com *{profissional_escolhido}* para *{servico}* em *{data}* às *{hora}*."

        except Exception as e:
            return f"❌ Erro ao salvar agendamento: {str(e)}"

    elif sessao["estado"] == "aguardando_nome_cliente":
        nome_cliente = mensagem.strip()
        await criar_ou_atualizar_sessao(user_id, {
            **sessao,
            "estado": "completo",
            "nome_cliente": nome_cliente if nome_cliente else None
        })
        await sincronizar_contexto(user_id, pegar_sessao(user_id))
        return await tratar_mensagem_usuario(user_id, "")

    else:
        return "Algo deu errado. Vamos começar de novo?"

__all__ = [
    "verificar_disponibilidade_profissional",
    "tratar_mensagem_usuario",
]