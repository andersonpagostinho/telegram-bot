# handlers/acao_router_handler.py
import inspect

async def executar_acao_por_nome(update, context, acao, dados):
    user_id = str(update.message.from_user.id)

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

        elif acao == "criar_evento":
            from .event_handler import add_evento_por_gpt
            await executar_se_coroutine(add_evento_por_gpt, update, context, dados)

        elif acao == "enviar_email":
            from .email_handler import enviar_email_por_gpt
            await executar_se_coroutine(enviar_email_por_gpt, update, context, dados)

        elif acao == "organizar_semana":
            from services.firebase_service_async import buscar_subcolecao
            from services.gpt_service import organizar_semana_com_gpt

            tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
            eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

            tarefas = [t["descricao"] for t in tarefas_dict.values() if "descricao" in t]
            eventos = [e["descricao"] for e in eventos_dict.values() if "descricao" in e]

            resposta = await organizar_semana_com_gpt(tarefas, eventos)
            await update.message.reply_text(resposta, parse_mode="Markdown")

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
                await update.message.reply_text("📭 Nenhum profissional cadastrado ainda.")
                return

            mensagem = "👥 *Profissionais cadastrados:*\n\n"
            for nome, dados in profissionais.items():
                servicos = ", ".join(dados.get("servicos", []))
                mensagem += f"• *{nome}* – {servicos}\n"

            await update.message.reply_text(mensagem, parse_mode="Markdown")

        else:
            await update.message.reply_text(f"⚠️ Ação desconhecida: {acao}")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao executar ação '{acao}': {e}")
        print(f"❌ Erro em executar_acao_por_nome: {e}")
