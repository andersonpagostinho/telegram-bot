from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import atualizar_dado_em_path

# ✅ Comando de teste para salvar avisos no Firebase
async def testar_avisos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    path = f"Usuarios/{user_id}/configuracoes/avisos"
    dados = {
        "horarios": ["10:30", "14:00", "19:00"]
    }

    sucesso = atualizar_dado_em_path(path, dados)
    if sucesso:
        await update.message.reply_text("✅ Horários salvos com sucesso no Firebase!")
    else:
        await update.message.reply_text("❌ Falha ao salvar horários no Firebase.")
