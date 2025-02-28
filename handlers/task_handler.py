import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_dados, buscar_dados, deletar_colecao

logger = logging.getLogger(__name__)

# ✅ Adicionar uma nova tarefa
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para a tarefa.")
        return

    tarefa_data = {"descricao": descricao, "prioridade": "baixa"}
    try:
        salvar_dados("Tarefas", tarefa_data)
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao}")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar tarefa: {e}")
        await update.message.reply_text("❌ Erro ao adicionar a tarefa. Tente novamente.")

# ✅ Listar todas as tarefas
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tarefas = buscar_dados("Tarefas")
        if not tarefas:
            await update.message.reply_text("📭 Nenhuma tarefa encontrada.")
            return

        resposta = "📌 Suas tarefas:\n" + "\n".join(f"- {t['descricao']} ({t.get('prioridade', 'baixa')})" for t in tarefas)
        await update.message.reply_text(resposta)
    except Exception as e:
        logger.error(f"❌ Erro ao buscar tarefas: {e}")
        await update.message.reply_text("❌ Erro ao listar as tarefas. Tente novamente.")

# ✅ Listar tarefas ordenadas por prioridade
async def list_tasks_by_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tarefas = buscar_dados("Tarefas")
        prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
        tarefas_ordenadas = sorted(tarefas, key=lambda x: prioridade_ordem.get(x.get("prioridade", "baixa"), 3))

        if not tarefas_ordenadas:
            await update.message.reply_text("📭 Nenhuma tarefa encontrada.")
            return

        resposta = "📌 Tarefas por prioridade:\n" + "\n".join(f"- {t['descricao']} ({t.get('prioridade', 'baixa')})" for t in tarefas_ordenadas)
        await update.message.reply_text(resposta)
    except Exception as e:
        logger.error(f"❌ Erro ao ordenar tarefas por prioridade: {e}")
        await update.message.reply_text("❌ Erro ao listar as tarefas por prioridade. Tente novamente.")

# ✅ Limpar todas as tarefas
async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        deletar_colecao("Tarefas")
        await update.message.reply_text("🗑️ Todas as tarefas foram removidas com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao limpar tarefas: {e}")
        await update.message.reply_text("❌ Erro ao limpar as tarefas. Tente novamente.")
