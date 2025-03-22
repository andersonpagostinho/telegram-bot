async def processar_comando_voz(update, context, texto):
    texto = texto.lower()

    if "listar eventos" in texto or "eventos" in texto:
        from handlers.event_handler import list_events
        await list_events(update, context)

    elif "listar tarefas" in texto:
        from handlers.task_handler import list_tasks
        await list_tasks(update, context)

    elif "limpar tarefas" in texto:
        from handlers.task_handler import clear_tasks
        await clear_tasks(update, context)

    else:
        await update.message.reply_text("🤔 Não reconheci o comando. Pode repetir de outra forma?")

    elif "marcar reunião" in texto or "agendar reunião" in texto:
       from handlers.event_handler import add_evento_por_voz  # 👈 Você vai criar isso
       await add_evento_por_voz(update, context, texto)
