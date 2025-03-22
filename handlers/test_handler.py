from services.firebase_service import salvar_dados, buscar_dados
from telegram import Update
from telegram.ext import CallbackContext

async def testar_firebase(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    dados_teste = {"teste": "ok", "user": user_id}

    resultado = salvar_dados("teste_collection", dados_teste)  # ✅ Correção aqui

    if resultado:
        await update.message.reply_text("✅ Dados de teste salvos no Firebase.")
    else:
        await update.message.reply_text("❌ Falha ao salvar os dados no Firebase.")

async def verificar_firebase(update: Update, context: CallbackContext) -> None:
    dados = buscar_dados("teste_collection")  # ✅ Correção aqui

    if dados:
        resposta = "\n".join(str(dado) for dado in dados)  # Formatar os dados
        await update.message.reply_text(f"🔍 Dados encontrados:\n{resposta}")
    else:
        await update.message.reply_text("❌ Nenhum dado encontrado no Firebase.")