async def processar_comando_voz(update, context, texto):
    texto = texto.lower()

    try:
        if "listar eventos" in texto or "eventos" in texto:
            from handlers.event_handler import list_events
            await list_events(update, context)

        elif "confirmar reunião" in texto:
            from handlers.event_handler import confirmar_reuniao
            context.args = texto.replace("confirmar reunião", "").strip().split()
            await confirmar_reuniao(update, context)

        elif "confirmar presença" in texto:
            from handlers.event_handler import confirmar_presenca
            context.args = texto.replace("confirmar presença", "").strip().split()
            await confirmar_presenca(update, context)

        elif "debug eventos" in texto or "verificar eventos" in texto:
            from handlers.event_handler import debug_eventos
            await debug_eventos(update, context)

        elif "marcar reunião" in texto or "agendar reunião" in texto:
            from handlers.event_handler import add_evento_por_voz
            await add_evento_por_voz(update, context, texto)

        elif "nova tarefa" in texto or "adicionar tarefa" in texto:
            from handlers.task_handler import add_task
            context.args = texto.replace("nova tarefa", "").replace("adicionar tarefa", "").strip().split()
            await add_task(update, context)

        elif "listar tarefas" in texto:
            from handlers.task_handler import list_tasks
            await list_tasks(update, context)

        elif "prioridade" in texto:
            from handlers.task_handler import list_tasks_by_priority
            await list_tasks_by_priority(update, context)

        elif "limpar tarefas" in texto:
            from handlers.task_handler import clear_tasks
            await clear_tasks(update, context)

        elif "meus dados" in texto:
            from handlers.perfil_handler import meus_dados
            await meus_dados(update, context)

        elif "meu estilo" in texto:
            from handlers.perfil_handler import meu_estilo
            await meu_estilo(update, context)

        elif "relatório diário" in texto:
            from handlers.report_handler import gerar_relatorio_diario
            await gerar_relatorio_diario(update, context)

        elif "relatório semanal" in texto:
            from handlers.report_handler import gerar_relatorio_semanal
            await gerar_relatorio_semanal(update, context)

        elif "enviar relatório" in texto:
            from handlers.report_handler import enviar_relatorio_email
            await enviar_relatorio_email(update, context)

        elif "ler e-mails" in texto:
            from handlers.email_handler import ler_emails
            await ler_emails(update, context)

        elif "e-mails prioritários" in texto or "importantes" in texto:
            from handlers.email_handler import emails_prioritarios
            await emails_prioritarios(update, context)

        elif "enviar e-mail" in texto:
            from handlers.email_handler import enviar_email
            context.args = texto.replace("enviar e-mail", "").strip().split()
            await enviar_email(update, context)

        elif "meu e-mail" in texto:
            from handlers.email_handler import definir_email_envio
            context.args = texto.replace("meu e-mail", "").strip().split()
            await definir_email_envio(update, context)

        else:
            await update.message.reply_text("🤔 Não reconheci o comando. Pode repetir de outra forma?")

    except Exception as e:
        print("❌ Erro ao processar comando por voz:", e)
        await update.message.reply_text("❌ Ocorreu um erro ao executar o comando por voz.")
