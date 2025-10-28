from services.firebase_service_async import buscar_cliente, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao
from services.gpt_executor import executar_acao_gpt
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.plan_utils import verificar_pagamento,verificar_plano

async def processar_comando_voz(update, context, texto):
    try:
        texto = (texto or "").lower().strip()
        user_id = str(update.message.from_user.id)

        # 🔄 1. Coletar dados do usuário
        dados_usuario = await buscar_cliente(user_id) or {}
        tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}
        eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}

        tarefas = [t.get("descricao") for t in tarefas_dict.values() if isinstance(t, dict) and t.get("descricao")]
        eventos = [e.get("descricao") for e in eventos_dict.values() if isinstance(e, dict) and e.get("descricao")]

        # ⚙️ 2. Contexto enviado ao GPT (FORÇANDO plano OK para não bloquear)
        contexto = {
            "user_id": user_id,
            "usuario": {
                **dados_usuario,
                "pagamentoAtivo": True,                     # 🔒 não bloqueie por plano na voz
                "planosAtivos": list(set((dados_usuario.get("planosAtivos") or []) + ["secretaria"]))
            },
            "pagamentoAtivo": True,
            "planosAtivos": list(set((dados_usuario.get("planosAtivos") or []) + ["secretaria"])),
            "tarefas": tarefas,
            "eventos": eventos,
            "emails": []
        }

        # 🧠 3. Decisão + ação
        resultado = await processar_com_gpt_com_acao(
            texto_usuario=texto,
            contexto=contexto,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=str(chat_id),            # ✅ passa o uid certo
        )

        acao = resultado.get("acao")
        dados = resultado.get("dados", {})
        resposta = resultado.get("resposta", "✅ Comando processado.")

        if acao:
            sucesso = await executar_acao_gpt(update, context, acao, dados)
            if sucesso is False:
                return

        await update.message.reply_text(resposta, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Ocorreu um erro ao executar o comando de voz:\n{e}")
        print(f"❌ Erro em processar_comando_voz: {e}")
