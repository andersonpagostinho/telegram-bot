from telegram import Update
from telegram.ext import ContextTypes

# Handlers importados
from handlers.task_handler import add_task_por_gpt, gerar_texto_tarefas, remover_tarefa_por_descricao
from handlers.event_handler import add_agenda
from handlers.email_handler import enviar_email_command, listar_emails_prioritarios, ler_emails_command
from handlers.followup_handler import configurar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.perfil_handler import meu_plano
from utils.plan_utils import verificar_pagamento, verificar_acesso_modulo
from utils.tts_utils import responder_em_audio

# ✅ Executor de ações baseado no JSON retornado pelo GPT
async def executar_acao_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str, dados: dict):
    try:
        print(f"🪵 Ação recebida: {repr(acao)}")  # DEBUG extra

        if not acao or acao.strip() == "":
            resposta = dados.get("resposta", "📋 Aqui estão suas tarefas:")
            await update.message.reply_text(resposta, parse_mode="Markdown")
            return

        print(f"🔁 Ação recebida: {acao}")
        print(f"📦 Dados: {dados}")

        if acao == "criar_tarefa":
            await add_task_por_gpt(update, context, dados)

        elif acao == "buscar_tarefas_do_usuario":
            user_id = str(update.message.from_user.id)
            texto_tarefas = await gerar_texto_tarefas(user_id)
            resposta = dados.get("resposta") or "📋 Aqui está sua lista de tarefas:\n"
            await update.message.reply_text(f"{resposta}\n\n{texto_tarefas}", parse_mode="Markdown")

        elif acao == "criar_evento":
            from handlers.event_handler import add_evento_por_gpt
            await add_evento_por_gpt(update, context, dados)  # ✅ certo

        elif acao == "remover_tarefa":
            descricao = dados.get("descricao")
            if descricao:
                await remover_tarefa_por_descricao(update, context, descricao)


        elif acao == "enviar_email":
            await enviar_email_command(update, context, dados)

        elif acao == "buscar_emails":
            await ler_emails_command(update, context)

        elif acao == "listar_emails_prioritarios":
            await listar_emails_prioritarios(update, context)

        elif acao == "configurar_avisos":
            await configurar_avisos(update, context, dados)

        elif acao == "relatorio_diario":
            await relatorio_diario(update, context)

        elif acao == "relatorio_semanal":
            await relatorio_semanal(update, context)

        elif acao == "enviar_relatorio_email":
            await enviar_relatorio_email(update, context)

        elif acao == "verificar_pagamento":
            await verificar_pagamento(update, context)

        elif acao == "verificar_acesso_modulo":
            modulo = dados.get("modulo")
            if modulo:
                await verificar_acesso_modulo(update, context, modulo)

        elif acao == "meu_plano":
            await meu_plano(update, context)

        elif acao == "responder_audio":
            mensagem = dados.get("mensagem")
            if mensagem:
                await responder_em_audio(update, context, mensagem)

        else:
            await update.message.reply_text(f"⚠️ Ação '{acao}' ainda não suportada.")
    except Exception as e:
        erro = f"❌ Erro ao executar ação '{acao}': {str(e)}"
        print(erro)
        if hasattr(update, "message") and update.message:
            await update.message.reply_text(erro)