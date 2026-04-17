# handlers/acao_router_handler.py
import inspect
from datetime import datetime
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path
from services.profissional_service import obter_precos_servico, encontrar_servico_mais_proximo
from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario


async def executar_acao_por_nome(update, context, acao, dados):
    user_id = str(update.message.from_user.id)

    # 🔤 Normaliza nomes de ação vindos do LLM (sinônimos/variações)
    def normalizar_acao(nome: str | None) -> str | None:
        if not nome:
            return None
        mapa = {
            "listar_tarefas": "buscar_tarefas_do_usuario",
            "ver_tarefas": "buscar_tarefas_do_usuario",
            "mostrar_tarefas": "buscar_tarefas_do_usuario",
            "minhas_tarefas": "buscar_tarefas_do_usuario",
            # extras relacionadas a tarefas
            "listar_prioridade": "listar_tarefas_por_prioridade",
            "limpar_tarefas": "limpar_tarefas_do_usuario",
            "adicionar_tarefa": "criar_tarefa",
        }
        return mapa.get(nome, nome)

    acao = normalizar_acao(acao)

    async def executar_se_coroutine(func, *args):
        print(f"⚙️ Função chamada: {func.__name__}")
        resultado = func(*args)
        print(f"🔁 Tipo do resultado: {type(resultado)}")
        if inspect.isawaitable(resultado):
            print("⏳ Resultado é awaitable, aguardando...")
            return await resultado
        print("🚫 Resultado não é awaitable.")
        return resultado

    try:
        print(f"\n➡️ Executando ação: {acao}")
        print(f"📦 Dados recebidos do GPT: {dados}")

        if acao in ["adicionar_tarefa", "criar_tarefa"]:
            from .task_handler import add_task_por_gpt
            await executar_se_coroutine(add_task_por_gpt, update, context, dados)

        elif acao == "buscar_tarefas_do_usuario":
            from .task_handler import gerar_texto_tarefas
            user_id = str(update.message.from_user.id)
            texto = await gerar_texto_tarefas(user_id)
            resposta = dados.get("resposta") or "Aqui estão suas tarefas:"
            await update.message.reply_text(f"{resposta}\n\n{texto}", parse_mode="Markdown")
            return {
                "resposta": f"{resposta}\n\n{texto}",
                "acao": "buscar_tarefas_do_usuario",
                "dados": {"tarefas": texto}
            }

        # 🆕 Listar tarefas por prioridade
        elif acao == "listar_tarefas_por_prioridade":
            from .task_handler import list_tasks_by_priority
            await executar_se_coroutine(list_tasks_by_priority, update, context, {})
            return {
                "resposta": "Listando tarefas por prioridade…",
                "acao": "listar_tarefas_por_prioridade",
                "dados": {}
            }

        # 🧹 Limpar todas as tarefas
        elif acao == "limpar_tarefas_do_usuario":
            from .task_handler import clear_tasks
            await executar_se_coroutine(clear_tasks, update, context, {})
            return {
                "resposta": "Limpando tarefas do usuário…",
                "acao": "limpar_tarefas_do_usuario",
                "dados": {}
            }

        elif acao == "criar_evento":
            user_id = str(update.message.from_user.id)
            contexto = await carregar_contexto_temporario(user_id)
            resposta_usuario = update.message.text.lower()
            alternativa = (contexto.get("alternativa_profissional") or "").lower()

            if alternativa and alternativa in resposta_usuario:
                print(f"🔁 Substituindo profissional original '{dados.get('profissional')}' pela alternativa '{alternativa}'")
                dados["profissional"] = alternativa.capitalize()

            from .event_handler import add_evento_por_gpt
            print("🟢 Chamando add_evento_por_gpt com dados:", dados)
            await executar_se_coroutine(add_evento_por_gpt, update, context, dados)

        elif acao == "enviar_email":
            from .email_handler import enviar_email_por_gpt
            await executar_se_coroutine(enviar_email_por_gpt, update, context, dados)

        elif acao == "ler_email":
            from .email_handler import ler_email_por_gpt
            await executar_se_coroutine(ler_email_por_gpt, update, context, dados)

        elif acao == "organizar_semana":
            from services.firebase_service_async import buscar_subcolecao
            from services.gpt_service import organizar_semana_com_gpt

            tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
            eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

            tarefas = [t["descricao"] for t in tarefas_dict.values() if "descricao" in t]
            eventos = [e["descricao"] for e in eventos_dict.values() if "descricao" in e]

            resposta = await organizar_semana_com_gpt(tarefas, eventos)
            await update.message.reply_text(resposta, parse_mode="Markdown")
            return {
                "resposta": resposta,
                "acao": "organizar_semana",
                "dados": {"tarefas": tarefas, "eventos": eventos}
            }

        elif acao == "criar_followup":
            from .followup_handler import criar_followup_por_gpt
            await executar_se_coroutine(criar_followup_por_gpt, update, context, dados)

        elif acao == "concluir_followup":
            from .followup_handler import concluir_followup_por_gpt
            await executar_se_coroutine(concluir_followup_por_gpt, update, context, dados)

        elif acao == "cadastrar_profissional":
            from services.firebase_service_async import salvar_dado_em_path

            nome = dados.get("nome")
            servicos = dados.get("servicos", [])

            if not nome or not servicos:
                await update.message.reply_text("⚠️ Dados incompletos para cadastrar profissional.")
                return

            path = f"Clientes/{user_id}/Profissionais/{nome}"
            dados_profissional = {
                "nome": nome,
                "servicos": servicos
            }

            print(f"📌 Salvando profissional via GPT:\n- Path: {path}\n- Dados: {dados_profissional}")
            salvo = await salvar_dado_em_path(path, dados_profissional)

            if salvo:
                servicos_formatados = ", ".join(servicos)
                await update.message.reply_text(
                    f"✅ Profissional *{nome}* cadastrada com: *{servicos_formatados}*",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Erro ao salvar a profissional.")

        elif acao == "listar_profissionais":
            from services.firebase_service_async import buscar_subcolecao

            profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

            if not profissionais:
                await update.message.reply_text("📬 Nenhum profissional cadastrado ainda.")
                return

            mensagem = "👥 *Profissionais cadastrados:*\n\n"
            for nome, dados in profissionais.items():
                servicos = ", ".join(dados.get("servicos", []))
                mensagem += f"• *{nome}* – {servicos}\n"

            await update.message.reply_text(mensagem, parse_mode="Markdown")
            return {
                "resposta": mensagem,
                "acao": "listar_profissionais",
                "dados": profissionais
            }

        elif acao == "bloquear_agenda_salao":
            from services.agenda_service import bloquear_datas_agenda_salao, normalizar_lista_datas

            datas = (dados or {}).get("datas") or []
            motivo = (dados or {}).get("motivo") or "fechado"

            datas = normalizar_lista_datas(datas)

            if not datas:
                msg = "⚠️ Não consegui identificar as datas para bloquear a agenda."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_salao",
                    "dados": {}
                }

            sucesso = await bloquear_datas_agenda_salao(
                user_id=user_id,
                datas=datas,
                motivo=motivo
            )

            if not sucesso:
                msg = "❌ Não consegui salvar o bloqueio da agenda."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_salao",
                    "dados": {"datas": datas, "motivo": motivo}
                }

            # 🧹 limpa contexto de agendamento
            ctx = await carregar_contexto_temporario(user_id) or {}
            ctx["estado_fluxo"] = "idle"
            ctx.pop("draft_agendamento", None)
            ctx.pop("data_hora", None)

            # opcional, mas eu recomendo fortemente já limpar também:
            ctx.pop("servico", None)
            ctx.pop("profissional_escolhido", None)
            ctx.pop("ultima_consulta", None)
            ctx.pop("aguardando_confirmacao_agendamento", None)
            ctx.pop("dados_confirmacao_agendamento", None)

            await salvar_contexto_temporario(user_id, ctx)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                "Perfeito 😊\n"
                "Fechei a agenda destes dias:\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)
            return {
                "resposta": resposta,
                "acao": "bloquear_agenda_salao",
                "dados": {
                    "datas": datas,
                    "motivo": motivo
                }
            }

        elif acao == "definir_meio_periodo_salao":
            from services.agenda_service import definir_janela_especial_agenda_salao, normalizar_lista_datas
            from utils.context_manager import limpar_contexto_agendamento
            
            datas = (dados or {}).get("datas") or []
            inicio = (dados or {}).get("inicio")
            fim = (dados or {}).get("fim")
            motivo = (dados or {}).get("motivo") or "expediente_reduzido"
  
            datas = normalizar_lista_datas(datas)

            if not datas or not inicio or not fim:
                msg = "⚠️ Não consegui identificar corretamente o período de atendimento."
                await update.message.reply_text(msg)
                return

            sucesso = await definir_janela_especial_agenda_salao(
                user_id=user_id,
                datas=datas,
                inicio=inicio,
                fim=fim,
                motivo=motivo
            )

            if not sucesso:
                msg = "❌ Não consegui salvar o horário especial."
                await update.message.reply_text(msg)
                return

            # 🧹 limpa contexto de agendamento
            await limpar_contexto_agendamento(user_id)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                "Perfeito 😊\n"
                f"Ajustei o atendimento destes dias para:\n"
                f"{inicio} às {fim}\n\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)

            return {
                "resposta": resposta,
                "acao": "definir_meio_periodo_salao",
                "dados": dados
            }  

        elif acao == "bloquear_agenda_profissional":
            from services.agenda_service import bloquear_agenda_profissional, normalizar_lista_datas
            from utils.context_manager import limpar_contexto_agendamento

            profissional = (dados or {}).get("profissional")
            datas = (dados or {}).get("datas") or []
            motivo = (dados or {}).get("motivo") or "indisponivel"

            profissional = (profissional or "").strip()
            datas = normalizar_lista_datas(datas)

            if not profissional or not datas:
                msg = "⚠️ Não consegui identificar corretamente o profissional ou as datas do bloqueio."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_profissional",
                    "dados": {}
                }

            sucesso = await bloquear_agenda_profissional(
                user_id=user_id,
                profissional=profissional,
                datas=datas,
                motivo=motivo
            )

            if not sucesso:
                msg = f"❌ Não consegui salvar o bloqueio da agenda de {profissional}."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_profissional",
                    "dados": dados
                }

            await limpar_contexto_agendamento(user_id)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                f"Perfeito 😊\n"
                f"Bloqueei a agenda de {profissional} nestes dias:\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)
            return {
                "resposta": resposta,
                "acao": "bloquear_agenda_profissional",
                "dados": {
                    "profissional": profissional,
                    "datas": datas,
                    "motivo": motivo
                }
            }

        elif acao == "definir_meio_periodo_profissional":
            from services.agenda_service import definir_janela_especial_profissional, normalizar_lista_datas
            from utils.context_manager import limpar_contexto_agendamento

            profissional = (dados or {}).get("profissional")
            datas = (dados or {}).get("datas") or []
            inicio = (dados or {}).get("inicio")
            fim = (dados or {}).get("fim")
            motivo = (dados or {}).get("motivo") or "expediente_reduzido"

            profissional = (profissional or "").strip()
            datas = normalizar_lista_datas(datas)

            if not profissional or not datas or not inicio or not fim:
                msg = "⚠️ Não consegui identificar corretamente o profissional ou o período especial."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_definir_meio_periodo_profissional",
                    "dados": {}
                }

            sucesso = await definir_janela_especial_profissional(
                user_id=user_id,
                profissional=profissional,
                datas=datas,
                inicio=inicio,
                fim=fim,
                motivo=motivo
            )

            if not sucesso:
                msg = f"❌ Não consegui salvar o horário especial de {profissional}."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_definir_meio_periodo_profissional",
                    "dados": dados
                }

            await limpar_contexto_agendamento(user_id)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                f"Perfeito 😊\n"
                f"Ajustei o atendimento de {profissional} para:\n"
                f"{inicio} às {fim}\n\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)
            return {
                "resposta": resposta,
                "acao": "definir_meio_periodo_profissional",
                "dados": {
                    "profissional": profissional,
                    "datas": datas,
                    "inicio": inicio,
                    "fim": fim,
                    "motivo": motivo
                }
            }

        elif acao == "verificar_disponibilidade_profissional":
            from services.profissional_service import buscar_profissionais_por_servico
            from .acao_handler import verificar_disponibilidade_profissional

            servicos = dados.get("servicos", [])
            profissionais_filtrados = await buscar_profissionais_por_servico(servicos, user_id)

            if not profissionais_filtrados:
                await update.message.reply_text("😕 Nenhum profissional oferece todos esses serviços.")
                return

            resultado = await verificar_disponibilidade_profissional({
                "data_hora": dados["data_hora"],
                "duracao": dados["duracao"],
                "profissionais": list(profissionais_filtrados.keys())
            }, user_id)

            await update.message.reply_text(resultado["resposta"], parse_mode="Markdown")
            return {
                "resposta": resultado["resposta"],
                "acao": "verificar_disponibilidade_profissional",
                "dados": resultado
            }

        elif acao == "consultar_preco_servico":
             return await consultar_preco_servico(update, context, dados)

        else:
            await update.message.reply_text(f"⚠️ Ação desconhecida: {acao}")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao executar ação '{acao}': {e}")
        print(f"❌ Erro em executar_acao_por_nome: {e}")

async def consultar_preco_servico(update, context, dados):
    user_id = str(update.message.from_user.id)
    servico = dados.get("servico", "").lower()
    profissional_nome = dados.get("profissional")

    if not servico:
        msg = "❌ Não consegui identificar o serviço."
        await update.message.reply_text(msg)
        return {
            "resposta": msg,
            "acao": "erro_consulta_preco",
            "dados": {}
        }

    if profissional_nome:
        preco = await obter_precos_servico(user_id, servico, profissional_nome)
        if preco is not None:
            try:
                valor_formatado = f"{float(preco):.2f}"
            except Exception:
                valor_formatado = str(preco)
            resposta = (
                f"O preço de *{servico}* com *{profissional_nome}* é R$ {valor_formatado}"
            )
        else:
            resposta = (
                f"Infelizmente não temos o preço de {servico} com {profissional_nome} ainda."
            )
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return {
            "resposta": resposta,
            "acao": "resposta_preco",
            "dados": {"servico": servico, "profissional": profissional_nome}
        }

    precos = await obter_precos_servico(user_id, servico)

    if precos:
        resposta = f"Valores de *{servico}*:\n"
        for nome, preco in precos.items():
            try:
                valor_formatado = f"{float(preco):.2f}"
            except Exception:
                valor_formatado = str(preco)
            resposta += f"- *{nome}*: R$ {valor_formatado}\n"
    else:
        resposta = f"Infelizmente não temos esse preço ainda."

    await update.message.reply_text(resposta, parse_mode="Markdown")
    return {
        "resposta": resposta,
        "acao": "resposta_preco",
        "dados": {"servico": servico}
    }

async def consultar_tabela_geral_de_precos(update, user_id):
    precos = await obter_precos_servico(user_id)
    if not precos:
        await update.message.reply_text("Ainda não temos uma tabela de preços cadastrada.")
        return

    resposta = "*Tabela de Preços:*\n"
    for servico, precos_por_prof in precos.items():
        resposta += f"\n*{servico.title()}*\n"
        for prof, valor in precos_por_prof.items():
            resposta += f"- {prof}: R$ {valor:.2f}\n"

    await update.message.reply_text(resposta, parse_mode="Markdown")
    return {
        "resposta": resposta,
        "acao": "tabela_geral_precos",
        "dados": precos
    }
