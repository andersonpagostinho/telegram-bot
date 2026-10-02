from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service_async import salvar_cliente, buscar_cliente, salvar_dado_em_path, buscar_subcolecao
from datetime import datetime
from utils.formatters import formatar_horario_atual
from utils.permissao_utils import verificar_dono

# ✅ /tipo_negocio petshop
async def set_tipo_negocio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o tipo de negócio. Ex: /tipo_negocio petshop")
        return

    tipo = context.args[0].lower()
    user_id = str(update.message.from_user.id)

    if await salvar_cliente(user_id, {"tipo_negocio": tipo}):
        await update.message.reply_text(f"🏪 Tipo de negócio definido como: {tipo}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o tipo de negócio.")

# ✅ /estilo formal
async def set_estilo_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o estilo desejado. Ex: /estilo formal")
        return

    estilo = context.args[0].lower()
    user_id = str(update.message.from_user.id)

    if await salvar_cliente(user_id, {"estilo_mensagem": estilo}):
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

    if await salvar_cliente(user_id, {"nome_negocio": nome}):
        await update.message.reply_text(f"🏷️ Nome do negócio salvo como: {nome}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o nome do negócio.")

# ✅ /meu_estilo
async def meu_estilo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

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

# ✅ /meu_email exemplo@email.com
async def set_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe um e-mail. Exemplo:\n/meu_email exemplo@email.com")
        return

    email = context.args[0]
    user_id = str(update.message.from_user.id)

    if await salvar_cliente(user_id, {"email": email}):
        await update.message.reply_text(f"📧 E-mail salvo com sucesso: {email}")
    else:
        await update.message.reply_text("❌ Erro ao salvar o e-mail.")

# ✅ Comando /meuplano
async def meu_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if not cliente:
        await update.message.reply_text("❌ Nenhum cadastro encontrado. Use /start para começar.")
        return

    nome = cliente.get("nome", "Não informado")
    planos = cliente.get("planosAtivos", [])
    pagamento = "✅ Ativo" if cliente.get("pagamentoAtivo") else "❌ Inativo"
    data_assinatura = cliente.get("dataAssinatura", "❓")
    proximo_pagamento = cliente.get("proximoPagamento", "❓")

    dias_restantes = ""
    try:
        data_final = datetime.fromisoformat(proximo_pagamento)
        dias = (data_final - datetime.now()).days
        dias_restantes = f"\n📅 Dias restantes: *{dias}*" if dias >= 0 else "\n⚠️ Plano vencido"
    except:
        pass

    texto = (
        f"📋 *Informações do seu plano:*\n\n"
        f"👤 Nome: *{nome}*\n"
        f"💳 Pagamento: *{pagamento}*\n"
        f"📦 Planos ativos: *{', '.join(planos) or 'Nenhum'}*\n"
        f"🗓️ Assinatura: *{data_assinatura}*\n"
        f"🔁 Próx. pagamento: *{proximo_pagamento}*"
        f"{dias_restantes}"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")

# ✅ /tipo_usuario dono
async def set_tipo_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o tipo de usuário. Ex: /tipo_usuario dono ou /tipo_usuario cliente")
        return

    tipo = context.args[0].lower()
    if tipo not in ["dono", "cliente"]:
        await update.message.reply_text("❌ Valor inválido. Use apenas 'dono' ou 'cliente'.")
        return

    user_id = str(update.message.from_user.id)
    if await salvar_cliente(user_id, {"tipo_usuario": tipo}):
        await update.message.reply_text(f"🔐 Tipo de usuário definido como: *{tipo}*", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Erro ao salvar o tipo de usuário.")

# ✅ /modo_uso atendimento_cliente
async def set_modo_uso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Informe o modo de uso. Ex: /modo_uso interno ou /modo_uso atendimento_cliente")
        return

    modo = context.args[0].lower()
    if modo not in ["interno", "atendimento_cliente"]:
        await update.message.reply_text("❌ Valor inválido. Use apenas 'interno' ou 'atendimento_cliente'.")
        return

    user_id = str(update.message.from_user.id)
    if await salvar_cliente(user_id, {"modo_uso": modo}):
        await update.message.reply_text(f"🧭 Modo de uso definido como: *{modo}*", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Erro ao salvar o modo de uso.")

# ✅ /meu_perfil
async def meu_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if not cliente:
        await update.message.reply_text("❌ Nenhum perfil encontrado. Use /start para iniciar seu cadastro.")
        return

    nome = cliente.get("nome", "Não informado")
    email = cliente.get("email", "Não informado")
    tipo_usuario = cliente.get("tipo_usuario", "❓ Não definido")
    modo_uso = cliente.get("modo_uso", "❓ Não definido")
    tipo_negocio = cliente.get("tipo_negocio", "❓ Não definido")
    estilo = cliente.get("estilo_mensagem", "❓ Não definido")
    nome_negocio = cliente.get("nome_negocio", "❓ Não definido")

    await update.message.reply_text(
        f"📌 *Seu Perfil Completo:*\n\n"
        f"👤 Nome: *{nome}*\n"
        f"📧 E-mail: *{email}*\n"
        f"🔐 Tipo de usuário: *{tipo_usuario}*\n"
        f"🧭 Modo de uso: *{modo_uso}*\n"
        f"🏪 Tipo de negócio: *{tipo_negocio}*\n"
        f"🏷️ Nome do negócio: *{nome_negocio}*\n"
        f"🎨 Estilo de comunicação: *{estilo}*",
        parse_mode="Markdown"
    )

# ✅ /profissional
async def adicionar_profissional(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🚀 Entrou no handler /profissional")

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("⚠️ Use o formato: /profissional Nome corte,escova")
        return

    nome_prof = context.args[0]
    atividades = ' '.join(context.args[1:]).replace(" ", "").split(",")

    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)
    if not cliente:
        await update.message.reply_text("❌ Perfil não encontrado. Use /start para iniciar.")
        return

    id_negocio = cliente.get("id_negocio", user_id)

    dados = {
        "nome": nome_prof,
        "servicos": atividades
    }

    print(f"📌 Profissional a salvar:\n- Path: Clientes/{id_negocio}/Profissionais/{nome_prof}\n- Dados: {dados}")

    path = f"Clientes/{id_negocio}/Profissionais/{nome_prof}"
    salvo = await salvar_dado_em_path(path, dados)

    if salvo:
        atividades_formatadas = ", ".join(atividades)
        await update.message.reply_text(
            f"👩‍⚕️ Profissional *{nome_prof}* cadastrada com: *{atividades_formatadas}*",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Erro ao salvar profissional.")

# ✅ /listar_profissionais
from services.firebase_service_async import buscar_subcolecao, buscar_cliente, obter_id_dono

async def listar_profissionais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    # 🔍 Verifica se o perfil está cadastrado
    cliente = await buscar_cliente(user_id)
    if not cliente:
        await update.message.reply_text("❌ Perfil não encontrado. Use /start para iniciar.")
        return

    # 🎯 Garante que busca no ID do dono
    id_negocio = await obter_id_dono(user_id)

    profissionais = await buscar_subcolecao(f"Clientes/{id_negocio}/Profissionais")

    if not profissionais:
        await update.message.reply_text("📭 Nenhum profissional cadastrado ainda.")
        return

    mensagem = "👥 *Profissionais cadastrados:*\n\n"
    for nome, dados in profissionais.items():
        servicos = ", ".join(dados.get("servicos", []))
        mensagem += f"• *{nome}* – {servicos}\n"

    await update.message.reply_text(mensagem, parse_mode="Markdown")
