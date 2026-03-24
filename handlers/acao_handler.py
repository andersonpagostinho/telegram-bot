import re
from datetime import datetime, timedelta
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path, buscar_cliente
from services.session_service import criar_ou_atualizar_sessao, pegar_sessao, resetar_sessao, sincronizar_contexto
from services.profissional_service import (
    buscar_profissionais_por_servico,
    gerar_mensagem_profissionais_disponiveis,
    buscar_profissionais_disponiveis_no_horario,
)
from services.normalizacao_service import encontrar_servico_mais_proximo
from unidecode import unidecode
from utils.interpretador_datas import interpretar_data_e_hora
from services.informacao_service import responder_consulta_informativa

def estimar_duracao_servico(servico) -> int:
    """
    MVP: estima duração do serviço.
    Se vier lista, soma as durações.
    Depois isso pode ser trocado por duração cadastrada no Firebase.
    """
    mapa = {
        "escova": 40,
        "corte": 60,
        "hidratação": 50,
        "hidratacao": 50,
        "coloração": 120,
        "coloracao": 120,
        "luzes": 150,
        "progressiva": 180,
        "manicure": 40,
        "pedicure": 50,
        "sobrancelha": 30,
    }

    if isinstance(servico, list):
        total = 0
        for s in servico:
            chave = str(s).strip().lower()
            total += mapa.get(chave, 60)
        return total if total > 0 else 60

    chave = str(servico or "").strip().lower()
    return mapa.get(chave, 60)


def parse_servicos_em_ordem(texto: str, servicos_disponiveis: list[str], max_itens: int = 2):
    """
    Retorna:
      - None se não encontrar nada
      - str se encontrar 1 serviço
      - list[str] se encontrar 2 serviços (em ordem)
    """
    if not texto or not servicos_disponiveis:
        return None

    t = unidecode(texto.lower())

    # normaliza catálogo
    catalogo = []
    for s in servicos_disponiveis:
        s_txt = str(s).strip()
        if not s_txt:
            continue
        catalogo.append((s_txt, unidecode(s_txt.lower())))

    achados = []
    for original, norm in catalogo:
        pattern = r"\b" + re.escape(norm) + r"\b"
        m = re.search(pattern, t)
        if m:
            achados.append((m.start(), original))

    if not achados:
        return None

    achados.sort(key=lambda x: x[0])

    vistos = set()
    em_ordem = []
    for _, s in achados:
        k = unidecode(s.lower().strip())
        if k in vistos:
            continue
        vistos.add(k)
        em_ordem.append(s)
        if len(em_ordem) >= max_itens:
            break

    if len(em_ordem) == 1:
        return em_ordem[0]
    return em_ordem


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
        # 1) Monta catálogo de serviços (união de todos os profissionais)
        profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
        servicos_set = set()
        for p in profissionais.values():
            for serv in (p.get("servicos") or []):
                s = str(serv).lower().strip()
                if s:
                    servicos_set.add(s)

        catalogo = sorted(list(servicos_set))

        # 2) Tenta parsear 2 serviços em ordem (split)
        servicos_parseados = parse_servicos_em_ordem(mensagem, catalogo, max_itens=2)

        # 3) Se não achou 2, cai no seu normalizador atual (1 serviço)
        if not servicos_parseados:
            servico_normalizado = await encontrar_servico_mais_proximo(mensagem, user_id)
            if not servico_normalizado:
                if servicos_set:
                    servicos_formatados = "\n".join([f"• {s.capitalize()}" for s in sorted(servicos_set)])
                    return (
                        "Não entendi o serviço. Você pode escolher um destes:\n\n"
                        f"{servicos_formatados}\n\n"
                        "Qual você deseja?"
                    )
                return "Não entendi o serviço. Qual serviço você deseja agendar?"

            # salva 1 serviço (string) — comportamento antigo
            await criar_ou_atualizar_sessao(user_id, {
                **sessao,
                "estado": "aguardando_data",
                "servico": servico_normalizado
            })
            await sincronizar_contexto(user_id, pegar_sessao(user_id))
            return f"Beleza! Qual a data para o serviço *{servico_normalizado}*?"

        # 4) Se achou 1 ou 2 pelo parser, salva:
        if isinstance(servicos_parseados, list) and len(servicos_parseados) == 2:
            await criar_ou_atualizar_sessao(user_id, {
                **sessao,
                "estado": "aguardando_data",
                "servico": servicos_parseados  # <-- lista com 2 serviços (ordem do texto)
            })
            await sincronizar_contexto(user_id, pegar_sessao(user_id))
            return f"Perfeito! Qual a data para *{servicos_parseados[0]} + {servicos_parseados[1]}*?"
        else:
            # veio só 1 serviço pelo parser (string)
            await criar_ou_atualizar_sessao(user_id, {
                **sessao,
                "estado": "aguardando_data",
                "servico": servicos_parseados
            })
            await sincronizar_contexto(user_id, pegar_sessao(user_id))
            return f"Beleza! Qual a data para o serviço *{servicos_parseados}*?"

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
        return "Perfeito. E qual horário?"

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
            servicos_busca = servico if isinstance(servico, list) else [servico]

            profissionais_filtrados = await buscar_profissionais_por_servico(servicos_busca, user_id)
            print("🔍 Profissionais compatíveis com o serviço:", profissionais_filtrados.keys())
            duracao_min = estimar_duracao_servico(servico)

            disponiveis_dict = await buscar_profissionais_disponiveis_no_horario(
                user_id=user_id,
                data=data_obj,
                hora=hora,
                duracao=duracao_min
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
                "duracao": duracao_min,
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
        texto_normalizado = unidecode((mensagem or "").lower())
        print("📨 Mensagem recebida:", mensagem)
        print("🔍 Texto normalizado:", texto_normalizado)

        sessao = await pegar_sessao(user_id)
        disponiveis = sessao.get("disponiveis", [])
        disponiveis_normalizados = [unidecode(p.lower()) for p in disponiveis]

        # ✅ PATCH PRODUTO: "quais tem / quem você tem" aqui significa "quais PROFISSIONAIS estão disponíveis"
        # Não lista serviços/atividades.
        if any(k in texto_normalizado for k in [
            "quais tem", "quais voce tem", "quais você tem",
            "quem voce tem", "quem você tem",
            "quais profissionais", "quem atende", "quem tem"
        ]):
            if disponiveis:
                lista = ", ".join(disponiveis)
                servico_atual = sessao.get("servico", "esse serviço")
                data_atual = sessao.get("data", "")
                hora_atual = sessao.get("hora", "")
                # resposta direta e contextual (produto)
                return f"Para *{servico_atual}* em *{data_atual}* às *{hora_atual}*, tenho disponível: {lista}. Qual você prefere?"
            return "Nesse horário, não tenho ninguém disponível. Quer tentar outro horário?"

        # ⏱️ Detecta nova data e hora na mesma mensagem
        data_hora_detectada = interpretar_data_e_hora(mensagem)
        print("🕵️‍♂️ Data/hora detectada:", data_hora_detectada)
        if data_hora_detectada:
            nova_data = data_hora_detectada.date().strftime("%d/%m/%Y")
            nova_hora = data_hora_detectada.time().strftime("%H:%M")
            data_obj = data_hora_detectada.date()
            servico = sessao.get("servico")

            if servico:
                servicos_busca = servico if isinstance(servico, list) else [servico]

                profissionais_filtrados = await buscar_profissionais_por_servico(servicos_busca, user_id)
                duracao_min = estimar_duracao_servico(servico)

                disponiveis_dict = await buscar_profissionais_disponiveis_no_horario(
                    user_id=user_id,
                    data=data_obj,
                    hora=nova_hora,
                    duracao=duracao_min
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
                    "duracao": duracao_min,
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

        # ✅ Se não encontrou profissional, pede para informar
        if not profissional_escolhido:
            return "Qual profissional você prefere? (ex: Joana, Bruna, Carla...)"

        # ✅ Se o nome não está na lista de disponíveis para o serviço, já orienta
        if profissional_escolhido not in disponiveis:
            lista = ", ".join(disponiveis) if disponiveis else "nenhuma"
            return f"Para *{sessao.get('servico','esse serviço')}*, eu tenho disponível: {lista}. Qual delas você prefere?"

        # ✅ Agora sim: profissional é válido e está entre os disponíveis.
        # Checa conflito real no horário desejado.
        from services.event_service_async import verificar_conflito_e_sugestoes_profissional

        # sessao["data"] vem como "dd/mm/YYYY" -> converter para "YYYY-MM-DD"
        data_raw = (sessao.get("data") or "").strip()
        try:
            data_iso = datetime.strptime(data_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            return "⚠️ Não entendi a data. Pode enviar no formato 28/02/2026?"

        hora_raw = (sessao.get("hora") or "").strip()

        # ✅ Duração: por enquanto 60; depois você troca por estimar_duracao(servico) ou duração cadastrada.
        duracao_min = int(sessao.get("duracao") or estimar_duracao_servico(sessao.get("servico")))

        conflito_info = await verificar_conflito_e_sugestoes_profissional(
            user_id=user_id,
            data=data_iso,
            hora_inicio=hora_raw,
            duracao_min=duracao_min,
            profissional=profissional_escolhido,
            servico=sessao.get("servico", ""),
        )

        if conflito_info.get("conflito"):
            resposta = f"⚠️ {profissional_escolhido} está com horário ocupado para {hora_raw}.\n"

            sugestoes = conflito_info.get("sugestoes") or []
            if sugestoes:
                resposta += "🕒 Horários alternativos disponíveis:\n" + "\n".join([f"🔄 {h}" for h in sugestoes]) + "\n"

            alt = conflito_info.get("profissional_alternativo")
            if alt:
                resposta += f"💡 Para esse mesmo horário, *{alt}* está disponível.\nDeseja agendar com ela?"

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

        # ✅ Se tudo certo, FECHAMENTO AUTOMÁTICO com segurança (reserva + janela de desfazer)
        try:
            servico = sessao.get("servico")
            data = sessao.get("data")
            hora = sessao.get("hora")

            data_hora_inicio = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M")
            duracao_min = int(sessao.get("duracao") or estimar_duracao_servico(servico))
            data_hora_fim = data_hora_inicio + timedelta(minutes=duracao_min)

            # ✅ evento reservado (não confirmado ainda)
            evento = {
                "descricao": f"{servico} com {profissional_escolhido}",
                "hora_inicio": data_hora_inicio.isoformat(),
                "hora_fim": data_hora_fim.isoformat(),
                "duracao": duracao_min,
                "profissional": profissional_escolhido,
                "status": "reservado",
                "confirmado": False,
                "criado_em": datetime.now().isoformat(),
                "expira_em": (datetime.now() + timedelta(minutes=2)).isoformat()
            }

            if sessao.get("nome_cliente"):
                evento["nome_cliente"] = sessao["nome_cliente"]

            evento_id = f"{data_hora_inicio.strftime('%Y%m%d%H%M')}_{servico.replace(' ', '_')}_{profissional_escolhido}"

            # 🔒 Idempotência mínima: se já existe esse evento_id, não duplica
            existente = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
            if evento_id not in existente:
                await salvar_dado_em_path(f"Clientes/{user_id}/Eventos/{evento_id}", evento)

            # ✅ agenda “confirmação automática” em 2 minutos (usando sua infra de NotificacoesAgendadas)
            from services.notificacao_service import criar_notificacao_agendada
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=f"CONFIRMAR_RESERVA::{evento_id}",
                data=(datetime.now() + timedelta(minutes=2)).strftime("%d/%m/%Y"),
                hora_inicio=(datetime.now() + timedelta(minutes=2)).strftime("%H:%M"),
                minutos_antes=0,
                destinatario_user_id=user_id,
                alvo_evento={"evento_id": evento_id}
            )

            # ✅ mensagem humana + opção de desfazer
            msg = (
                f"Confirmando: *{servico}* com *{profissional_escolhido}* em *{data}* às *{hora}*.\n"
                f"Já reservei esse horário pra você ✅\n\n"
                f"Se quiser mudar, responda *alterar* ou *cancelar*."
            )
            return msg

        except Exception as e:
            return f"❌ Erro ao reservar agendamento: {str(e)}"

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