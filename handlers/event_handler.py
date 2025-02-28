import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_dados, buscar_dados

logger = logging.getLogger(__name__)

# ✅ Adicionar um evento à agenda
async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para o evento.")
        return

    evento_data = {"descricao": descricao, "confirmado": False}
    salvar_dados("Eventos", evento_data)
    await update.message.reply_text(f"📅 Evento adicionado: {descricao}")

# ✅ Listar eventos agendados
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    eventos = buscar_dados("Eventos")
    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return
    
    resposta = "📅 Eventos agendados:\n" + "\n".join(f"- {e['descricao']} ({'✅ Confirmado' if e.get('confirmado') else '❌ Pendente'})" for e in eventos)
    await update.message.reply_text(resposta)

# ✅ Confirmar um evento agendado
async def confirmar_reuniao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento que deseja confirmar.")
        return

    eventos = buscar_dados("Eventos")
    for evento in eventos:
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            salvar_dados("Eventos", evento)
            await update.message.reply_text(f"✅ Evento confirmado: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")

# ✅ Confirmar presença em um evento
async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    eventos = buscar_dados("Eventos")
    for evento in eventos:
        if evento["descricao"].lower() == descricao.lower():
            evento["confirmado"] = True
            salvar_dados("Eventos", evento)
            await update.message.reply_text(f"✅ Presença confirmada no evento: {descricao}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")
