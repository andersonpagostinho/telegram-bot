from utils.plan_utils import verificar_plano, identificar_plano_por_intencao
from services.firebase_service_async import buscar_cliente, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao
from services.gpt_executor import executar_acao_gpt
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

async def processar_comando_voz(update, context, texto):
    try:
        texto = texto.lower()
        user_id = str(update.message.from_user.id)

        # 🔄 1. Coletar dados do usuário
        dados_usuario = await buscar_cliente(user_id)  # ✅ Correto agora!
        tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
        eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

        tarefas = [t["descricao"] for t in tarefas_dict.values() if "descricao" in t]
        eventos = [e["descricao"] for e in eventos_dict.values() if "descricao" in e]

        contexto = {
            "usuario": dados_usuario,
            "tarefas": tarefas,
            "eventos": eventos,
            "emails": []  # Pode ser preenchido futuramente
        }

        # 🧠 2. Enviar tudo para o GPT decidir
        resultado = await processar_com_gpt_com_acao(texto, contexto, INSTRUCAO_SECRETARIA)

        acao = resultado.get("acao")
        dados = resultado.get("dados", {})
        resposta = resultado.get("resposta", "✅ Comando processado.")

        # ⚙️ 3. Executar ação se houver
        if acao:
            sucesso = await executar_acao_gpt(update, context, acao, dados)
            if not sucesso:
                return  # não envia mais a mensagem padrão

        # 💬 4. Responder ao usuário
        await update.message.reply_text(resposta, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Ocorreu um erro ao executar o comando de voz:\n{e}")
        print(f"❌ Erro em processar_comando_voz: {e}")
