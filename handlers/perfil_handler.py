from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_cliente, buscar_cliente

# ✅ /tipo_negocio petshop
async def set_tipo_negocio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o tipo de negócio. Ex: /tipo_negocio petshop")
        return

    tipo = context.args[0].lower()
    user_id = str(update.message.from_user.id)

    if salvar_cliente(user_id, {"tipo_negocio": tipo}):
        await update.message.reply_text(f"🏪 Tipo de negócio definido como: {tipo}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o tipo de negócio.")

# ✅ /estilo descontraido
async def set_estilo_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o estilo desejado. Ex: /estilo formal")
        return

    estilo = context.args[0].lower()
    user_id = str(update.message.from_user.id)

    if salvar_cliente(user_id, {"estilo_mensagem": estilo}):
        await update.message.reply_text(f"🎨 Estilo de mensagens definido como: {estilo}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o estilo.")

# ✅ /nome_negocio BichoFofo
async def set_nome_negocio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o nome do seu negócio. Ex: /nome_negocio BichoFofo")
        return

    nome = ' '.join(context.args)
    user_id = str(update.message.from_user.id)

    if salvar_cliente(user_id, {"nome_negocio": nome}):
        await update.message.reply_text(f"🏷️ Nome do negócio salvo como: {nome}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o nome do negócio.")

# ✅ /meu_estilo
async def meu_estilo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = buscar_cliente(user_id)

    if not cliente:
        await update.message.reply_text("❌ Nenhum perfil encontrado.")
        return

    tipo = cliente.get("tipo_negocio", "❓ Não definido")
    estilo = cliente.get("estilo_mensagem", "❓ Não definido")
    nome = cliente.get("nome_negocio", "❓ Não definido")

    await update.message.reply_text(
        f"👤 *Seu Perfil de Comunicação:*\n"
        f"- 🏪 Tipo de negócio: *{tipo}*\n"
        f"- 🎨 Estilo: *{estilo}*\n"
        f"- 🏷️ Nome do negócio: *{nome}*",
        parse_mode="Markdown"
    )

# ? /meu_email exemplo@email.com
async def set_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("?? Informe um e-mail. Exemplo:\n/meu_email exemplo@email.com")
        return

    email = context.args[0]
    user_id = str(update.message.from_user.id)

    if salvar_cliente(user_id, {"email": email}):
        await update.message.reply_text(f"?? E-mail salvo com sucesso: {email}")
    else:
        await update.message.reply_text("? Erro ao salvar o e-mail.")
