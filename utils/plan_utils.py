from services.firebase_service_async import buscar_cliente
from telegram import Update
from telegram.ext import ContextTypes

# --- alias simples de módulos para seus planos reais ---
def _normalizar_modulo(modulo: str) -> str:
    m = (modulo or "").strip().lower()
    alias = {
        "voz": "secretaria",
        "áudio": "secretaria",
        "audio": "secretaria",
        "asr": "secretaria",
        # adicione outros atalhos se precisar
    }
    return alias.get(m, m)

async def verificar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if not cliente:
        await update.message.reply_text("⚠️ Não encontramos seu cadastro. Use /start para começar.")
        return False

    if not cliente.get("pagamentoAtivo", False):
        await update.message.reply_text("⚠️ Seu plano está inativo. Acesse o painel para renovar.")
        return False

    return True

async def verificar_plano(user_id: str, modulo: str) -> bool:
    cliente = await buscar_cliente(user_id)
    if not cliente or not cliente.get("pagamentoAtivo", False):
        return False

    planos = [str(p).lower() for p in (cliente.get("planosAtivos") or [])]
    modulo_norm = _normalizar_modulo(modulo)
    return modulo_norm in planos

async def verificar_acesso_modulo(update: Update, context: ContextTypes.DEFAULT_TYPE, modulo: str) -> bool:
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if not cliente:
        await update.message.reply_text("⚠️ Não encontramos seu cadastro. Use /start para começar.")
        return False

    if not cliente.get("pagamentoAtivo", False):
        await update.message.reply_text("⚠️ Seu plano está inativo. Acesse o painel para renovar.")
        return False

    planos = [str(p).lower() for p in (cliente.get("planosAtivos") or [])]
    modulo_norm = _normalizar_modulo(modulo)
    if modulo_norm not in planos:
        await update.message.reply_text(
            f"🚫 Este comando faz parte do módulo *{modulo_norm}*, que não está ativo na sua conta.",
            parse_mode="Markdown"
        )
        return False

    return True

def identificar_plano_por_intencao(intencao: str) -> str:
    # Você já mapeia tudo para 'secretaria'; mantenho assim
    return "secretaria"
