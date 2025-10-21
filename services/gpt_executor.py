from telegram import Update
from telegram.ext import ContextTypes

# Handlers importados
from handlers.task_handler import add_task_por_gpt, gerar_texto_tarefas, remover_tarefa_por_descricao
from handlers.event_handler import add_evento_por_gpt
from handlers.email_handler import listar_emails_prioritarios, ler_emails_command
from handlers.followup_handler import configurar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.perfil_handler import meu_plano
from utils.plan_utils import verificar_pagamento, verificar_acesso_modulo
from utils.tts_utils import responder_em_audio
from services.firebase_service_async import buscar_subcolecao
from datetime import datetime
from services.email_service import enviar_email_google
from services.event_service_async import cancelar_evento_por_texto

# ✅ Executor de ações baseado no JSON retornado pelo GPT
from services.event_service_async import buscar_eventos_por_intervalo  # Importação necessária

async def executar_acao_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str, dados: dict):
    try:
        print(f"🪵 Ação recebida: {repr(acao)}")  # DEBUG extra

        if not acao or acao.strip() == "":
            return False

        print(f"🔁 Ação recebida: {acao}")
        print(f"📦 Dados: {dados}")

        if acao == "criar_tarefa":
            await add_task_por_gpt(update, context, dados)
            return True

        elif acao == "buscar_tarefas_do_usuario":
            user_id = str(update.message.from_user.id)
            texto_tarefas = await gerar_texto_tarefas(user_id)
            resposta = dados.get("resposta") or "📋 Aqui está sua lista de tarefas:\n"
            await update.message.reply_text(f"{resposta}\n\n{texto_tarefas}", parse_mode="Markdown")
            return True

        elif acao == "criar_evento":
            sucesso = await add_evento_por_gpt(update, context, dados)
            return sucesso  # ✅ True se criou, False se houve conflito

        elif acao == "remover_tarefa":
            descricao = dados.get("descricao")
            if descricao:
                await remover_tarefa_por_descricao(update, context, descricao)
            return True

        elif acao == "cancelar_evento":
            # termo vindo do modelo (ex.: "unha com a Carla amanhã")
            termo = (dados or {}).get("termo")
            if not termo:
                # fallback: usa o texto bruto da mensagem se o modelo não mandou "termo"
                termo = getattr(getattr(update, "message", None), "text", "") or ""

            try:
                ok, msg = await cancelar_evento_por_texto(user_id, termo)
            except Exception as e:
                ok, msg = False, f"❌ Erro ao processar cancelamento: {e}"

            if ok:
                await update.message.reply_text(msg)
            else:
                ajuda = (
                    "Me diga algo como:\n"
                    "• cancelar corte amanhã às 10:00 com Joana\n"
                    "• cancelar unha com Carla dia 20/10 às 15:30"
                )
                await update.message.reply_text(f"{msg}\n\n{ajuda}")

        elif acao == "enviar_email":
            destinatario = dados.get("destinatario")
            assunto = dados.get("assunto")
            corpo = dados.get("corpo")
            user_id = str(update.message.from_user.id)

            if not destinatario or not assunto or not corpo:
                await update.message.reply_text("❌ Dados insuficientes para enviar o e-mail.")
                return False

            # Verifica se o destinatário é e-mail ou nome
            if "@" not in destinatario:
                contatos = await buscar_subcolecao(f"Clientes/{user_id}/Contatos")
                contatos_encontrados = [
                    c for c in contatos.values()
                    if c.get('nome', '').lower() == destinatario.lower()
                ]

                if not contatos_encontrados:
                    await update.message.reply_text(f"❌ Não encontrei e-mail para {destinatario}.")
                    return False

                elif len(contatos_encontrados) == 1:
                    destinatario = contatos_encontrados[0]['email']

                else:
                    opcoes = "\n".join(
                        f"{i+1}. {c['nome']} - {c['email']}" for i, c in enumerate(contatos_encontrados)
                    )
                    context.user_data["contatos_em_espera"] = contatos_encontrados
                    context.user_data["assunto_em_espera"] = assunto
                    context.user_data["mensagem_em_espera"] = corpo

                    await update.message.reply_text(
                        f"📩 Encontrei mais de um contato chamado {destinatario}:\n\n{opcoes}\n\nResponda com o número do contato desejado."
                    )
                    return True

            sucesso = enviar_email(destinatario, assunto, corpo)

            resposta_bot = f"✅ E-mail enviado para {destinatario}." if sucesso else "❌ Erro ao enviar e-mail."
            await update.message.reply_text(resposta_bot)
            return True
            
        elif acao == "buscar_emails":
            await ler_emails_command(update, context)
            return True

        elif acao == "listar_emails_prioritarios":
            await listar_emails_prioritarios(update, context)
            return True

        elif acao == "configurar_avisos":
            await configurar_avisos(update, context, dados)
            return True

        elif acao == "relatorio_diario":
            await relatorio_diario(update, context)
            return True

        elif acao == "relatorio_semanal":
            await relatorio_semanal(update, context)
            return True

        elif acao == "enviar_relatorio_email":
            await enviar_relatorio_email(update, context)
            return True

        elif acao == "verificar_pagamento":
            await verificar_pagamento(update, context)
            return True

        elif acao == "verificar_acesso_modulo":
            modulo = dados.get("modulo")
            if modulo:
                await verificar_acesso_modulo(update, context, modulo)
            return True

        elif acao == "meu_plano":
            await meu_plano(update, context)
            return True

        elif acao == "responder_audio":
            mensagem = dados.get("mensagem")
            if mensagem:
                await responder_em_audio(update, context, mensagem)
            return True

        elif acao == "cadastrar_profissional":
            from handlers.acao_router_handler import executar_acao_por_nome
            await executar_acao_por_nome(update, context, acao, dados)
            return True

        elif acao == "listar_profissionais":
            from handlers.acao_router_handler import executar_acao_por_nome
            await executar_acao_por_nome(update, context, acao, dados)
            return True

        elif acao == "listar_followups":
            from handlers.followup_handler import listar_followups
            await listar_followups(update, context)
            return True

        elif acao == "consultar_preco_servico":
            from handlers.acao_router_handler import consultar_preco_servico
            await consultar_preco_servico(update, context, dados)
            return True

        elif acao == "cancelar_evento":
            # tenta usar o termo vindo do modelo;
            # fallback para o próprio texto do usuário, se necessário
            termo = (dados or {}).get("termo")
            if not termo:
                # se você tiver o update/context aqui, pode usar o texto recebido
                termo = getattr(getattr(update, "message", None), "text", "")

            ok, msg = await cancelar_evento_por_texto(user_id, termo)
            # responda ao usuário
            if ok:
                await update.message.reply_text(msg)
            else:
                # mensagem de ajuda com reforço do termo usado
                ajuda = "Me diga algo como: 'cancelar corte amanhã às 10h com Joana' ou 'cancelar reunião de 25/10 às 14:00'."
                txt = f"{msg}\n\n{ajuda}"
                await update.message.reply_text(txt)

        # 🚀 Novas ações para eventos:
        elif acao == "buscar_eventos_da_semana":
            user_id = str(update.message.from_user.id)
            eventos = await buscar_eventos_por_intervalo(user_id, semana=True)
            resposta = "📅 Eventos da semana:\n" + "\n".join(f"- {e}" for e in eventos) if eventos else "📭 Nenhum evento encontrado esta semana."
            await update.message.reply_text(resposta)
            return True

        elif acao == "buscar_eventos_do_dia":
            dias = dados.get("dias", 0)
            data_str = dados.get("data")
            user_id = str(update.message.from_user.id)

            if data_str:
                dia_especifico = datetime.strptime(data_str, "%Y-%m-%d").date()
                eventos_reais = await buscar_eventos_por_intervalo(user_id, dia_especifico=dia_especifico)
            else:
                eventos_reais = await buscar_eventos_por_intervalo(user_id, dias=dias)

            if eventos_reais:
                resposta = f"📅 Seus eventos:\n" + "\n".join(f"- {e}" for e in eventos_reais)
            else:
                resposta = "📭 Nenhum evento encontrado para o período solicitado."

            await update.message.reply_text(resposta, parse_mode="Markdown")
            return True

        elif acao == "aguardar_arquivo_importacao":
            context.user_data["esperando_planilha"] = True
            resposta = dados.get("resposta", "📂 Envie agora a planilha com os profissionais.")
            await update.message.reply_text(resposta)
            return True

        else:
            await update.message.reply_text(f"⚠️ Ação '{acao}' ainda não suportada.")
            return False

    except Exception as e:
        erro = f"❌ Erro ao executar ação '{acao}': {str(e)}"
        print(erro)
        if hasattr(update, "message") and update.message:
            await update.message.reply_text(erro)
        return False