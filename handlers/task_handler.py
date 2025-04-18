# handlers/task_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from services.firebase_service_async import client
from utils.formatters import formatar_horario_atual

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_subcolecao,
    limpar_colecao
)
from utils.priority_utils import detectar_prioridade_tarefa
from utils.plan_utils import verificar_acesso_modulo, verificar_pagamento

# ✅ Adicionar uma nova tarefa manualmente
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

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

    tarefa_id = str(datetime.now().timestamp()).replace(".", "")
    path = f"Clientes/{user_id}/Tarefas/{tarefa_id}"

    if await salvar_dado_em_path(path, tarefa_data):
        await update.message.reply_text(f"✅ Tarefa adicionada: {descricao} (Prioridade: {prioridade})")
    else:
        await update.message.reply_text("❌ Erro ao salvar a tarefa. Tente novamente.")


# ✅ Função auxiliar que retorna a lista como texto
async def gerar_texto_tarefas(user_id: str):
    tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")

    tarefas_validas = [
        t for t in tarefas_dict.values()
        if isinstance(t, dict) and "descricao" in t
    ]

    if not tarefas_validas:
        return "📭 Nenhuma tarefa encontrada."

    resposta = "📌 Suas tarefas:\n" + "\n".join(
        f"- {t['descricao']} ({t.get('prioridade', 'baixa')})"
        for t in tarefas_validas
    )
    return resposta

# ✅ Mantém o comando funcionando
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    resposta = await gerar_texto_tarefas(user_id)
    await update.message.reply_text(resposta)


# ✅ Listar tarefas por prioridade
async def list_tasks_by_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")

    if not tarefas_dict:
        await update.message.reply_text("📭 Nenhuma tarefa encontrada.")
        return

    prioridade_ordem = {"alta": 1, "média": 2, "baixa": 3}
    tarefas_ordenadas = sorted(
        tarefas_dict.values(),
        key=lambda x: prioridade_ordem.get(x.get("prioridade", "baixa"), 3)
    )

    resposta = "📌 Tarefas por prioridade:\n" + "\n".join(
        f"- {t['descricao']} ({t.get('prioridade', 'baixa')})"
        for t in tarefas_ordenadas
    )
    await update.message.reply_text(resposta)


# ✅ Limpar todas as tarefas do usuário
async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    path = f"Clientes/{user_id}/Tarefas"

    if await limpar_colecao(path):
        await update.message.reply_text("🗑️ Todas as tarefas foram removidas.")
    else:
        await update.message.reply_text("❌ Erro ao limpar as tarefas.")


# ✅ Adicionar tarefas via GPT (pode ser múltiplas)
async def add_task_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    tarefas = dados.get("tarefas") or []
    descricao = dados.get("descricao")

    if descricao and descricao not in tarefas:
        tarefas.append(descricao)

    if not tarefas:
        await update.message.reply_text("⚠️ Nenhuma tarefa identificada.")
        return

    user_id = str(update.message.from_user.id)
    adicionadas = 0

    for desc in tarefas:
        prioridade = detectar_prioridade_tarefa(desc, user_id)
        tarefa_data = {"descricao": desc, "prioridade": prioridade}
        tarefa_id = str(datetime.now().timestamp()).replace(".", "")
        path = f"Clientes/{user_id}/Tarefas/{tarefa_id}"

        if await salvar_dado_em_path(path, tarefa_data):
            adicionadas += 1

    if adicionadas:
        await update.message.reply_text(f"✅ {adicionadas} tarefa(s) adicionada(s).")
    else:
        await update.message.reply_text("❌ Nenhuma tarefa foi adicionada.")

# ✅ Remover tarefa específica pela descrição
async def remover_tarefa_por_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE, descricao: str):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    tarefas_ref = client.collection("Clientes").document(user_id).collection("Tarefas")

    try:
        query = tarefas_ref.where("descricao", "==", descricao).stream()
        encontrados = [doc async for doc in query]

        if not encontrados:
            await update.message.reply_text(f"❌ Nenhuma tarefa encontrada com a descrição: {descricao}")
            return

        for doc in encontrados:
            await doc.reference.delete()

        await update.message.reply_text(f"🗑️ Tarefa removida com sucesso: {descricao}")
    except Exception as e:
        print(f"❌ Erro ao remover tarefa: {e}")
        await update.message.reply_text("❌ Erro ao tentar remover a tarefa. Tente novamente.")

