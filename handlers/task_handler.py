from telegram import Update
from telegram.ext import ContextTypes
from services.firebase_service import salvar_dados, buscar_dados, limpar_colecao
from utils.priority_utils import detectar_prioridade_tarefa
from utils.plan_utils import verificar_acesso_modulo, verificar_pagamento  # ✅ Novo

# ✅ Adicionar uma nova tarefa
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para a tarefa.")
        return

    user_id = str(update.message.from_user.id)
    prioridade = detectar_prioridade_tarefa(descricao, user_id)

    tarefa_data = {
        "descricao": descricao,
        "prioridade": prioridade
    }

    if salvar_dados("Tarefas", tarefa_data):
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao} (Prioridade: {prioridade})")
    else:
        await update.message.reply_text("❌ Erro ao salvar a tarefa. Tente novamente.")

# ✅ Listar todas as tarefas
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    tarefas = buscar_dados("Tarefas")
    if not tarefas:
        await update.message.reply_text("📭 Nenhuma tarefa encontrada.")
        return

    resposta = "📌 Suas tarefas:\n" + "\n".join(f"- {t['descricao']} ({t.get('prioridade', 'baixa')})" for t in tarefas)
    await update.message.reply_text(resposta)

# ✅ Listar por prioridade
async def list_tasks_by_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    tarefas = buscar_dados("Tarefas")
    if not tarefas:
        await update.message.reply_text("📭 Nenhuma tarefa encontrada.")
        return

    prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
    tarefas_ordenadas = sorted(tarefas, key=lambda x: prioridade_ordem.get(x.get("prioridade", "baixa"), 3))

    resposta = "📌 Tarefas por prioridade:\n" + "\n".join(f"- {t['descricao']} ({t.get('prioridade', 'baixa')})" for t in tarefas_ordenadas)
    await update.message.reply_text(resposta)

# ✅ Limpar todas as tarefas
async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context):
        return

    if not await verificar_acesso_modulo(update, context, "secretaria"):
        return

    if limpar_colecao("Tarefas"):
        await update.message.reply_text("🗑️ Todas as tarefas foram removidas.")
    else:
        await update.message.reply_text("❌ Erro ao limpar as tarefas.")