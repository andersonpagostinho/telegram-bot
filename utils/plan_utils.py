from services.firebase_service import buscar_cliente
from telegram import Update
from telegram.ext import ContextTypes

# ✅ Verifica se o pagamento está ativo (sem checar o módulo)
async def verificar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)

    if not cliente or not cliente.get("pagamentoAtivo", False):
        await update.message.reply_text("⚠️ Seu plano está inativo. Acesse o painel para renovar.")
        return False

    return True

# ✅ Verifica se o usuário pode usar um módulo (sem mensagens)
async def verificar_plano(user_id: str, modulo: str) -> bool:
    cliente = buscar_cliente(user_id)

    if not cliente:
        return False  # Cliente não cadastrado

    if not cliente.get("pagamentoAtivo", False):
        return False  # Pagamento inativo

    planos = cliente.get("planosAtivos", [])
    if modulo not in planos:
        return False  # Módulo não incluso no plano

    return True

# ✅ Verifica plano com mensagens (para handlers Telegram)
async def verificar_acesso_modulo(update: Update, context: ContextTypes.DEFAULT_TYPE, modulo: str) -> bool:
    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)

    if not cliente:
        await update.message.reply_text("⚠️ Não encontramos seu cadastro. Use /start para começar.")
        return False

    if not cliente.get("pagamentoAtivo", False):
        await update.message.reply_text("⚠️ Seu plano está inativo. Acesse o painel para renovar.")
        return False

    planos = cliente.get("planosAtivos", [])
    if modulo not in planos:
        await update.message.reply_text(
            f"🚫 Este comando faz parte do módulo *{modulo}*, que não está ativo na sua conta.",
            parse_mode="Markdown"
        )
        return False

    return True

# ✅ Detecta qual plano é necessário com base na intenção
def identificar_plano_por_intencao(intencao: str) -> str:
    if intencao in [
        "adicionar_tarefa", "listar_tarefas", "listar_prioridade", "limpar_tarefas"
    ]:
        return "secretaria"
    elif intencao in [
        "adicionar_evento", "listar_eventos", "confirmar_reuniao", "confirmar_presenca", "debug_eventos"
    ]:
        return "secretaria"
    elif intencao in [
        "conectar_email", "ler_emails", "emails_prioritarios", "enviar_email", "meu_email", "authcallback"
    ]:
        return "secretaria"
    elif intencao in [
        "relatorio_diario", "relatorio_semanal", "enviar_relatorio_email"
    ]:
        return "secretaria"
    elif intencao in [
        "definir_tipo_negocio", "definir_estilo", "definir_nome_negocio"
    ]:
        return "secretaria"
    else:
        return "secretaria"  # Por padrão, tudo entra na "secretaria"
