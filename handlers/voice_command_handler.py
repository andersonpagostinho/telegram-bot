from utils.intencao_utils import identificar_intencao
from utils.plan_utils import verificar_plano, identificar_plano_por_intencao
from services.firebase_service import buscar_cliente
from services.gpt_service import processar_com_gpt
from services.intencao_gpt_service import identificar_intencao_com_gpt

async def processar_comando_voz(update, context, texto):
    texto = texto.lower()

    # 🔎 1. Tenta identificar intenção com regras fixas
    intencao = identificar_intencao(texto)

    # 🧠 2. Se não reconheceu, tenta via GPT (intenção)
    if not intencao:
        intencao = await identificar_intencao_com_gpt(texto)

    # 💬 3. Se nem o GPT entendeu como intenção, responde com o próprio GPT
    if not intencao:
        resposta_gpt = await processar_com_gpt(texto)
        await update.message.reply_text(resposta_gpt)
        return

    user_id = str(update.message.from_user.id)

    # 🔒 Verifica se o plano permite esse comando
    plano_necessario = identificar_plano_por_intencao(intencao)
    acesso_liberado = await verificar_plano(user_id, plano_necessario)

    if not acesso_liberado:
        await update.message.reply_text("⚠️ Seu plano está inativo ou não inclui este módulo.")
        return

    try:
        if intencao == "start":
            from handlers.bot import start
            await start(update, context)

        elif intencao == "help":
            from handlers.bot import help_command
            await help_command(update, context)

        elif intencao == "meusdados":
            from handlers.perfil_handler import meus_dados
            await meus_dados(update, context)

        elif intencao == "meuestilo":
            from handlers.perfil_handler import meu_estilo
            await meu_estilo(update, context)

        elif intencao == "adicionar_tarefa":
            from handlers.task_handler import add_task
            await add_task(update, context)

        elif intencao == "listar_tarefas":
            from handlers.task_handler import list_tasks
            await list_tasks(update, context)

        elif intencao == "listar_prioridade":
            from handlers.task_handler import list_tasks_by_priority
            await list_tasks_by_priority(update, context)

        elif intencao == "limpar_tarefas":
            from handlers.task_handler import clear_tasks
            await clear_tasks(update, context)

        elif intencao == "adicionar_evento":
            from handlers.event_handler import add_evento_por_voz
            await add_evento_por_voz(update, context, texto)

        elif intencao == "listar_eventos":
            from handlers.event_handler import list_events
            await list_events(update, context)

        elif intencao == "confirmar_reuniao":
            from handlers.event_handler import confirmar_reuniao
            await confirmar_reuniao(update, context)

        elif intencao == "confirmar_presenca":
            from handlers.event_handler import confirmar_presenca
            await confirmar_presenca(update, context)

        elif intencao == "debug_eventos":
            from handlers.event_handler import debug_eventos
            await debug_eventos(update, context)

        elif intencao == "conectar_email":
            from handlers.email_handler import conectar_email
            await conectar_email(update, context)

        elif intencao == "authcallback":
            from handlers.email_handler import auth_callback
            await auth_callback(update, context)

        elif intencao == "ler_emails":
            from handlers.email_handler import ler_emails_command
            await ler_emails_command(update, context)

        elif intencao == "emails_prioritarios":
            from handlers.email_handler import listar_emails_prioritarios
            await listar_emails_prioritarios(update, context)

        elif intencao == "enviar_email":
            from handlers.email_handler import enviar_email_command
            await enviar_email_command(update, context)

        elif intencao == "meu_email":
            from handlers.email_handler import definir_email_envio
            await definir_email_envio(update, context)

        elif intencao == "relatorio_diario":
            from handlers.report_handler import gerar_relatorio_diario
            await gerar_relatorio_diario(update, context)

        elif intencao == "relatorio_semanal":
            from handlers.report_handler import gerar_relatorio_semanal
            await gerar_relatorio_semanal(update, context)

        elif intencao == "enviar_relatorio_email":
            from handlers.report_handler import enviar_relatorio_email
            await enviar_relatorio_email(update, context)

        elif intencao == "definir_tipo_negocio":
            from handlers.perfil_handler import definir_tipo_negocio
            await definir_tipo_negocio(update, context)

        elif intencao == "definir_estilo":
            from handlers.perfil_handler import definir_estilo
            await definir_estilo(update, context)

        elif intencao == "definir_nome_negocio":
            from handlers.perfil_handler import definir_nome_negocio
            await definir_nome_negocio(update, context)

        elif intencao == "meusfollowups":
            from handlers.followup_handler import listar_followups
            await listar_followups(update, context)

        elif intencao == "concluir_followup":
            texto_lower = texto.lower()
            for padrao in [
                "já fiz o follow-up com", "pode apagar o follow-up de",
                "concluir o follow-up com", "já falei com",
                "já entrei em contato com", "remover o follow-up do",
                "apagar o follow-up de", "deletar o da loja", "concluir follow-up com"
            ]:
                if padrao in texto_lower:
                    nome_cliente = texto_lower.split(padrao)[-1].strip()
                    context.args = nome_cliente.split()
                    from handlers.followup_handler import concluir_followup
                    await concluir_followup(update, context)
                    return

        elif intencao == "criar_followup":
            texto_lower = texto.lower()
            for padrao in [
                "fazer follow-up com", "registrar follow-up com",
                "marcar follow-up com", "agendar follow-up com",
                "adicionar follow-up com", "novo follow-up com"
            ]:
                if padrao in texto_lower:
                    nome_cliente = texto_lower.split(padrao)[-1].strip()
                    context.args = nome_cliente.split()
                    from handlers.followup_handler import criar_followup
                    await criar_followup(update, context)
                    return

        elif intencao == "configurar_avisos":
            import re
            from datetime import datetime
            from handlers.followup_handler import configurar_avisos

            horarios_brutos = re.findall(r'\d{1,2}[:h]?\d{0,2}', texto)

            horarios_formatados = []
            for h in horarios_brutos:
                h = h.replace("h", ":")
                if ":" not in h:
                    h += ":00"
                try:
                    datetime.strptime(h, "%H:%M")
                    horarios_formatados.append(h)
                except ValueError:
                    continue

            horarios_formatados = horarios_formatados[:3]

            if not horarios_formatados:
                await update.message.reply_text(
                    "❌ Não entendi os horários. Diga algo como: *me avise às 09:00, 13:00 e 17:00*",
                    parse_mode="Markdown"
                )
                return

            context.args = horarios_formatados
            await configurar_avisos(update, context)

        else:
            await update.message.reply_text("🤔 Não reconheci o comando. Pode tentar de outra forma?")

    except Exception as e:
        await update.message.reply_text(f"❌ Ocorreu um erro ao executar o comando de voz:\n{e}")
