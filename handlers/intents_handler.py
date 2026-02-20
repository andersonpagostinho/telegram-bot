from services.firebase_service_async import buscar_subcolecao  # ✅ Firebase assíncrono
from services.email_service import ler_emails, filtrar_emails_prioritarios_por_palavras
from services.gpt_service import organizar_semana_com_gpt

async def acao_organizar_semana(user_id):
    # ✅ Buscar tarefas do Firebase
    tarefas = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
    tarefas_lista = [tarefa["descricao"] for tarefa in tarefas.values()] if tarefas else []

    # ✅ Buscar eventos do Firebase
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")
    eventos_lista = [evento["descricao"] for evento in eventos.values()] if eventos else []

    # ✅ Buscar e-mails e extrair alertas
    emails = await ler_emails(user_id=user_id)
    palavras_chave = ["pagamento", "vencimento", "boleto", "fatura"]
    alertas = filtrar_emails_prioritarios_por_palavras(emails, palavras_chave)
    
    if alertas:
        eventos_lista += [f"⚠️ Alerta de e-mail: {email['assunto']}" for email in alertas]

    # ✅ Chamar GPT com tudo isso
    resposta = await organizar_semana_com_gpt(tarefas_lista, eventos_lista, dia_inicio="hoje")
    return resposta