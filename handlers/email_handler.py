import os
import re
import json
import base64
import imaplib
import email
import logging
import traceback
import urllib.parse

from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import EmailMessage
from telegram import Update
from telegram.ext import ContextTypes

from utils.tts_utils import responder_em_audio
from utils.context_manager import (
    carregar_contexto_temporario,
    atualizar_contexto,
    limpar_contexto
)
from utils.plan_utils import verificar_pagamento, verificar_acesso_modulo
from utils.priority_utils import classificar_prioridade_email
from services.email_service import (
    ler_emails_google,
    enviar_email_google,
    buscar_contatos_por_nome,
    listar_emails_prioritarios,
    filtrar_emails_prioritarios_por_palavras
)
from services.firebase_service_async import (
    buscar_cliente,
    salvar_cliente,
    buscar_subcolecao,
    salvar_dado_em_path
)
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA, EXTRACAO_DADOS_EMAIL

logger = logging.getLogger(__name__)

# ✅ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    logger.info(f"🚀 Usuário {user_id} iniciou o bot!")

    cliente = await buscar_cliente(user_id)
    if cliente and cliente.get("email_config"):
        await update.message.reply_text("✅ Você já está conectado! Pronto para ler e enviar e-mails. 😊")
        return

    await update.message.reply_text(
        "✉️ Para conectar seu e-mail, me envie as seguintes informações no formato abaixo:\n\n"
        "`email=seuemail@gmail.com; senha_app=abcd-1234-efgh; imap_host=imap.gmail.com; smtp_host=smtp.gmail.com; smtp_port=587`\n\n"
        "🔐 *Importante:* essa senha é gerada como senha de aplicativo no Google. Não é sua senha normal.\n\n"
        "Você pode revogar esse acesso a qualquer momento nas configurações da sua conta Google.",
        parse_mode="Markdown"
    )

    context.user_data["esperando_dados_email"] = True


# ✅ Receber dados do usuário e salvar email_config
async def configurar_email_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    texto = update.message.text.strip()

    if not context.user_data.get("esperando_dados_email"):
        return

    try:
        # Extrair dados do texto
        dados = dict(
            item.strip().split("=")
            for item in texto.split(";")
            if "=" in item
        )

        email = dados.get("email")
        senha_app = dados.get("senha_app")
        imap_host = dados.get("imap_host", "imap.gmail.com")
        smtp_host = dados.get("smtp_host", "smtp.gmail.com")
        smtp_port = int(dados.get("smtp_port", 587))

        if not all([email, senha_app]):
            await update.message.reply_text("❌ E-mail e senha de app são obrigatórios.")
            return

        await salvar_cliente(user_id, {
            "email": email,
            "email_config": {
                "email": email,
                "senha_app": senha_app,
                "imap_host": imap_host,
                "smtp_host": smtp_host,
                "smtp_port": smtp_port
            }
        })

        context.user_data.pop("esperando_dados_email", None)
        await update.message.reply_text("✅ E-mail conectado com sucesso! Agora posso ler e enviar seus e-mails.")
    except Exception as e:
        logger.error(f"❌ Erro ao processar dados de e-mail: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao salvar os dados. Verifique o formato e tente novamente.")

# ✅ /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("📖 Comando /help recebido!")
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/help - Mostra esta mensagem\n"
        "/tarefa - Adiciona uma tarefa\n"
        "/listar - Lista todas as tarefas\n"
        "/limpar - Remove todas as tarefas\n"
        "/ler_emails - Lê os últimos e-mails\n"
        "/emails_prioritarios - Lista e-mails importantes\n"
        "/enviar_email - Envia um e-mail\n"
        "/conectar_email - Conectar seu e-mail ao sistema\n"
    )

# ✅ /conectar_email — configuração IMAP manual
async def conectar_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    context.user_data["esperando_dados_email"] = True

    await update.message.reply_text(
        "📨 Para conectar seu e-mail, envie os dados neste formato:\n\n"
        "`email=seunome@gmail.com; senha_app=abcd-1234-wxyz; imap_host=imap.gmail.com; smtp_host=smtp.gmail.com; smtp_port=587`\n\n"
        "⚠️ Use uma *senha de app* do Gmail, não sua senha normal.\n"
        "Você pode gerar e revogar essa senha a qualquer momento nas configurações da sua conta Google.",
        parse_mode="Markdown"
    )

async def buscar_emails_prioritarios(user_id):
    try:
        cliente = await buscar_cliente(user_id)
        config = cliente.get("email_config")
        if not config:
            print("❌ Configuração de e-mail não encontrada.")
            return []

        email_user = config.get("email")
        senha_app = config.get("senha_app")
        imap_host = config.get("imap_host", "imap.gmail.com")
        remetentes_prioritarios = config.get("remetentes_prioritarios", [])

        if not all([email_user, senha_app, remetentes_prioritarios]):
            print("❌ Dados de conexão ou remetentes prioritários ausentes.")
            return []

        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(email_user, senha_app)
        mail.select("inbox")

        emails_prioritarios = []

        for remetente in remetentes_prioritarios:
            result, data = mail.search(None, f'FROM "{remetente}"')
            ids = data[0].split()

            for i in ids[-10:]:  # limita para não sobrecarregar
                status, msg_data = mail.fetch(i, "(RFC822)")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                assunto = decode_header(msg["Subject"])[0][0]
                assunto = assunto.decode() if isinstance(assunto, bytes) else assunto
                data_raw = msg.get("Date")
                data_dt = parsedate_to_datetime(data_raw)
                if data_dt < datetime.now() - timedelta(days=3):
                    continue

                emails_prioritarios.append(f"📨 {assunto} de {remetente}")

        mail.logout()
        return emails_prioritarios

    except Exception as e:
        print(f"❌ Erro ao buscar e-mails prioritários via IMAP: {e}")
        return []

# ✅ /emails_prioritarios usando IMAP
from services.email_service import listar_emails_prioritarios

async def listar_emails_prioritarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    emails = await listar_emails_prioritarios(user_id)

    if emails:
        resposta = "📧 Emails prioritários:\n" + "\n".join(
            f"- {email['assunto']} de {email['remetente']}\n{email['corpo'][:100]}...\n"
            for email in emails
        )
    else:
        resposta = "📭 Nenhum email prioritário encontrado."

    await update.message.reply_text(resposta)

# ✅ Ler e-mails via GPT usando IMAP
async def ler_email_por_gpt(update, context, dados):
    user_id = str(update.message.from_user.id)
    remetente = dados.get("remetente", "").lower()
    quantidade = int(dados.get("quantidade", 3))

    emails = await ler_emails_google(user_id, num_emails=10)  # já usa IMAP

    if remetente:
        emails = [e for e in emails if remetente in e["remetente"].lower()]

    emails = emails[:quantidade]

    if emails:
        resposta = "📨 Emails encontrados:\n\n" + "\n\n".join(
            f"*De:* {e['remetente']}\n*Assunto:* {e['assunto']}\n{e['corpo'][:300]}..." for e in emails
        )
    else:
        resposta = "📭 Nenhum e-mail encontrado com essas condições."

    await update.message.reply_text(resposta, parse_mode="Markdown")

# ✅ /ler_emails usando IMAP
from services.email_service import ler_emails_google, filtrar_emails_prioritarios_por_palavras
from utils.tts_utils import responder_em_audio

async def ler_emails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    user_id = str(update.message.from_user.id)
    emails = await ler_emails_google(user_id=user_id)  # IMAP

    if emails:
        resposta = "📧 Emails:\n" + "\n".join(
            f"- De: {email.get('remetente', 'Desconhecido')}\n  Assunto: {email.get('assunto', 'Sem assunto')}\n  Mensagem: {email.get('corpo', 'Sem conteúdo')[:300]}..."
            for email in emails
        )
    else:
        resposta = "📭 Nenhum email encontrado."

    await update.message.reply_text(resposta)

    # 🔍 Verifica e avisa sobre prioritários (ex: urgente/importante)
    prioritarios = filtrar_emails_prioritarios_por_palavras(emails, ["urgente", "importante"])
    if prioritarios:
        resumo = "📬 Emails prioritários:\n"
        for email in prioritarios[:3]:
            resumo += f"- {email['assunto']} de {email['remetente']}\n\n"

        await responder_em_audio(update, context, f"Você recebeu {len(prioritarios)} e-mails importantes. Verifique sua caixa de entrada.")
        await update.message.reply_text(resumo)

# ✅ Salvar contato no Firebase se não existir
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path

async def salvar_contato_se_nao_existir(user_id, nome, email):
    nome = nome.strip()
    email = email.strip().lower()
    contatos = await buscar_subcolecao(f"Clientes/{user_id}/Contatos") or {}

    for c in contatos.values():
        c_email = c.get("email", "").strip().lower()
        c_nome = c.get("nome", "").strip().lower()
        if email == c_email or nome.lower() == c_nome:
            print(f"🔍 Contato já existente: {nome} -> {email}")
            return  # Contato já existe

    contato_id = re.sub(r"[^a-z0-9_]+", "_", nome.lower())
    await salvar_dado_em_path(f"Clientes/{user_id}/Contatos/{contato_id}", {
        "nome": nome,
        "email": email
    })
    print(f"✅ Contato salvo: {nome} -> {email}")

async def enviar_email_natural(update, context, texto_usuario):
    user_id = str(update.message.from_user.id)

    # 🔄 Carrega contexto temporário, se necessário
    if "email_em_espera" not in context.user_data:
        contexto_memoria = await carregar_contexto_temporario(user_id)
        if contexto_memoria:
            context.user_data.update(contexto_memoria)

    # 🧠 Detectar e-mail e possível prioridade
    email_match = re.search(r"para\s+(?:o\s+)?([\w\.-]+@[\w\.-]+\.\w+)", texto_usuario, re.IGNORECASE)
    prioridade_match = re.search(r"\b(urgente|importante)\b", texto_usuario.lower())
    corpo_match = re.search(r"(?:sobre|dizendo que|falando que)\s+(.*)", texto_usuario, re.IGNORECASE)

    if email_match:
        email = email_match.group(1)
        corpo = corpo_match.group(1).strip() if corpo_match else "Mensagem automática do assistente."
        prioridade = prioridade_match.group(1).capitalize() if prioridade_match else None

        resposta_bot = f"📩 Posso salvar esse e-mail '{email}' com qual nome?"
        await update.message.reply_text(resposta_bot)

        context.user_data.update({
            "email_em_espera": email,
            "mensagem_em_espera": corpo,
            "prioridade_em_espera": prioridade,
            "estado_envio": "aguardando_nome"
        })

        await salvar_contexto_temporario(user_id, context.user_data)
        await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta_bot})
        return

    # 🧠 Buscar por nome do contato
    if not email_match and "estado_envio" not in context.user_data:
        nome_destino = texto_usuario.strip().replace("envie um email para", "").strip().lower()
        contatos = await buscar_subcolecao(f"Clientes/{user_id}/Contatos") or {}

        email = next((c['email'] for c in contatos.values() if c.get('nome', '').lower() == nome_destino), None)

        if email:
            context.user_data.update({
                "email_em_espera": email,
                "nome_em_espera": nome_destino,
                "estado_envio": "aguardando_assunto"
            })

            resposta_bot = f"📨 Qual o assunto do e-mail para {nome_destino} ({email})?"
            await update.message.reply_text(resposta_bot)
            await salvar_contexto_temporario(user_id, context.user_data)
            await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta_bot})
            return
        else:
            resposta_bot = f"❌ Não encontrei nenhum contato chamado {nome_destino}. Pode informar o e-mail diretamente?"
            await update.message.reply_text(resposta_bot)
            await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta_bot})
            return

    # 📝 Nome aguardado
    if context.user_data.get("estado_envio") == "aguardando_nome":
        nome = texto_usuario.strip()
        context.user_data["nome_em_espera"] = nome

        resposta_bot = "📝 Qual o assunto do e-mail?"
        await update.message.reply_text(resposta_bot)

        context.user_data["estado_envio"] = "aguardando_assunto"
        await salvar_contexto_temporario(user_id, context.user_data)
        await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta_bot})
        return

    # 📝 Assunto aguardado
    if context.user_data.get("estado_envio") == "aguardando_assunto":
        assunto_corpo = texto_usuario.strip()

        nome = context.user_data.get("nome_em_espera")
        email = context.user_data.get("email_em_espera")
        prioridade = context.user_data.get("prioridade_em_espera")
        corpo = context.user_data.get("mensagem_em_espera")

        # Se o texto trouxer "assunto: X corpo: Y"
        assunto_match = re.search(r"(?:assunto[:\-])\s*(.+?)(?:\s+corpo[:\-])", assunto_corpo, re.IGNORECASE)
        corpo_match = re.search(r"(?:corpo[:\-])\s*(.+)", assunto_corpo, re.IGNORECASE)

        if assunto_match and corpo_match:
            assunto = assunto_match.group(1).strip()
            corpo = corpo_match.group(1).strip()
        else:
            assunto = assunto_corpo

        if prioridade:
            assunto = f"{prioridade}: {assunto}"

        # 🧠 Salva contato e envia
        await salvar_contato_se_nao_existir(user_id, nome, email)
        sucesso = await enviar_email_google(user_id, email, assunto, corpo)

        # 🧹 Limpa contexto
        context.user_data.clear()
        await limpar_contexto(user_id)

        resposta_bot = f"✅ E-mail enviado para {nome} ({email})." if sucesso else "❌ Erro ao enviar e-mail."
        await update.message.reply_text(resposta_bot)
        await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta_bot})
        return