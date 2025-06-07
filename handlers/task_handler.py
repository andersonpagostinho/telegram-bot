# handlers/task_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from services.firebase_service_async import client, buscar_cliente
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

    user_id = str(update.message.from_user.id)  # ✅ Define antes de usar
    cliente = await buscar_cliente(user_id)

    if cliente.get("tipo_usuario") != "dono":
        await update.message.reply_text("⚠️ Apenas o dono pode acessar tarefas.")
        return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Você precisa informar uma descrição para a tarefa.")
        return

    prioridade = detectar_prioridade_tarefa(descricao, user_id)

    tarefa_data = {
        "descricao": descricao,
        "prioridade": prioridade
    }

    tarefa_id = str(datetime.now().timestamp()).replace(".", "")
    path = f"Clientes/{user_id}/Tarefas/{tarefa_id}"

    if await salvar_dado_em_path(path, tarefa_data):
        try:
            from services.notificacao_service import criar_notificacao_agendada
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=descricao,
                data=datetime.now().strftime("%Y-%m-%d"),
                hora_inicio=(datetime.now() + timedelta(minutes=30)).strftime("%H:%M"),
                minutos_antes=0,
                canal="telegram"
            )
        except Exception as e:
            print(f"⚠️ Erro ao criar notificação da tarefa: {e}")

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

# ✅ Listar tarefas (somente para o dono)
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if cliente.get("tipo_usuario") != "dono":
        await update.message.reply_text("⚠️ Apenas o dono pode visualizar as tarefas.")
        return

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


# ✅ Limpar todas as tarefas (somente para o dono)
async def clear_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if cliente.get("tipo_usuario") != "dono":
        await update.message.reply_text("⚠️ Apenas o dono pode limpar as tarefas.")
        return

    from services.firebase_service_async import buscar_subcolecao, deletar_dado_em_path

    tarefas = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}

    if not tarefas:
        await update.message.reply_text("📭 Nenhuma tarefa para remover.")
        return

    for tarefa_id in tarefas.keys():
        await deletar_dado_em_path(f"Clientes/{user_id}/Tarefas/{tarefa_id}")

    await update.message.reply_text("🧹 Todas as tarefas foram removidas com sucesso.")

# ✅ Adicionar tarefas via GPT (somente para o dono)
async def add_task_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if cliente.get("tipo_usuario") != "dono":
        await update.message.reply_text("⚠️ Apenas o dono pode adicionar tarefas.")
        return

    tarefas = dados.get("tarefas") or []
    descricao = dados.get("descricao")

    if descricao and descricao not in tarefas:
        tarefas.append(descricao)

    if not tarefas:
        await update.message.reply_text("⚠️ Nenhuma tarefa identificada.")
        return

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

# ✅ Remover tarefas por descrição (aceita lista e ignora maiúsculas)
async def remover_tarefa_por_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE, descricao):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    cliente = await buscar_cliente(user_id)

    if cliente.get("tipo_usuario") != "dono":
        await update.message.reply_text("⚠️ Apenas o dono pode remover tarefas.")
        return

    tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")

    if isinstance(descricao, str):
        descricao = [descricao]

    removidas = []
    nao_encontradas = []

    from services.firebase_service_async import deletar_dado_em_path  # ✅ se ainda não importado

    for desc in descricao:
        encontrada = False
        for task_id, tarefa in tarefas_dict.items():
            if tarefa.get("descricao", "").lower() == desc.lower():
                path = f"Clientes/{user_id}/Tarefas/{task_id}"
                await deletar_dado_em_path(path)
                removidas.append(tarefa.get("descricao", desc))
                encontrada = True
                break

        if not encontrada:
            nao_encontradas.append(desc)

    resposta = ""
    if removidas:
        resposta += f"🗑️ Tarefas removidas com sucesso: {', '.join(removidas)}\n"
    if nao_encontradas:
        resposta += f"⚠️ Não encontrei: {', '.join(nao_encontradas)}"

    await update.message.reply_text(resposta.strip())