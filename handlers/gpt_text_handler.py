from services.gpt_service import processar_com_gpt_com_acao
from services.firebase_service_async import buscar_cliente, buscar_subcolecao
from services.gpt_executor import executar_acao_gpt
from utils.formatters import formatar_horario_atual
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from telegram import Update
from telegram.ext import ContextTypes

async def processar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    user_id = str(update.message.from_user.id)

    # 🛡️ Verifica se o cliente está cadastrado
    dados_usuario = await buscar_cliente(user_id)
    if not dados_usuario:
        await update.message.reply_text(
            "👋 Olá! Eu sou a *NeoEve*, sua secretária virtual inteligente.\n"
            "Se você está me conhecendo agora, digite o comando `/start` para ativar sua assistente personalizada e começar a organizar sua rotina! 🚀",
            parse_mode="Markdown"
        )
        return

    # 🔍 Buscar tarefas e eventos
    tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
    eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    # 🧾 Converter tarefas e eventos em listas simples de descrições
    tarefas = []
    if isinstance(tarefas_dict, dict):
        for k, t in tarefas_dict.items():
            print(f"🔍 Verificando tarefa {k}: {t}")
            if isinstance(t, dict) and "descricao" in t:
                tarefas.append(t["descricao"])

    eventos = []
    if isinstance(eventos_dict, dict):
        eventos = [e["descricao"] for e in eventos_dict.values() if isinstance(e, dict) and "descricao" in e]

    # ✅ Montar contexto com os campos esperados
    usuario = {
        "nome": dados_usuario.get("nome", ""),
        "email": dados_usuario.get("email", ""),
        "tipo_usuario": dados_usuario.get("tipo_usuario", ""),
        "modo_uso": dados_usuario.get("modo_uso", ""),
        "tipo_negocio": dados_usuario.get("tipo_negocio", ""),
        "nome_negocio": dados_usuario.get("nome_negocio", ""),
        "estilo": dados_usuario.get("estilo_mensagem", ""),
        "pagamentoAtivo": dados_usuario.get("pagamentoAtivo", False),
        "planosAtivos": dados_usuario.get("planosAtivos", [])
    }

    contexto = {
        "usuario": usuario,
        "tarefas": tarefas,
        "eventos": eventos,
        "emails": []
    }

    # 🧠 Processar com GPT
    resultado = await processar_com_gpt_com_acao(texto, contexto, INSTRUCAO_SECRETARIA)
    print("🧠 [DEBUG] Resposta estruturada do GPT:", resultado)

    acao = resultado.get("acao")
    dados = resultado.get("dados", {})
    resposta = resultado.get("resposta", "✅ Comando processado.")

    # ⚙️ Executar ação (caso necessário)
    if acao:
        sucesso = await executar_acao_gpt(update, context, acao, dados)
        if not sucesso:
            return

    # 💬 Responder usuário
    await update.message.reply_text(resposta, parse_mode="Markdown")
