from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service_async import salvar_dado_em_path, buscar_subcolecao, limpar_colecao

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

async def testar_firebase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dados = buscar_dados("Clientes")
        await update.message.reply_text(f"✅ Firebase conectado. Clientes encontrados: {len(dados)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao acessar o Firebase: {e}")
