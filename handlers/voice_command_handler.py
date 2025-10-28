from services.firebase_service_async import buscar_cliente, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao
from services.gpt_executor import executar_acao_gpt
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.plan_utils import verificar_pagamento  # ✅ usa só pagamento na voz

async def processar_comando_voz(update, context, texto):
    try:
        texto = (texto or "").lower().strip()
        user_id = str(update.effective_user.id)
        print(f"[voice] recebido de {user_id}: '{texto}'")

        # 1) checa pagamento (voz está coberta pelo plano 'secretaria')
        ok = await verificar_pagamento(update, context)
        if not ok:
            return  # mensagem já foi enviada pela função

        # 2) contexto (tenta buscar, sem travar se der erro)
        try:
            tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}
        except Exception as e:
            print(f"[voice] erro ao buscar tarefas: {e}")
            tarefas_dict = {}

        try:
            eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
        except Exception as e:
            print(f"[voice] erro ao buscar eventos: {e}")
            eventos_dict = {}

        tarefas = [t["descricao"] for t in tarefas_dict.values() if isinstance(t, dict) and "descricao" in t]
        eventos = [e["descricao"] for e in eventos_dict.values() if isinstance(e, dict) and "descricao" in e]

        dados_usuario = await buscar_cliente(user_id) or {}

        contexto = {
            "usuario": dados_usuario,
            "tarefas": tarefas,
            "eventos": eventos,
            "emails": []
        }

        # 3) GPT decide
        resultado = await processar_com_gpt_com_acao(texto, contexto, INSTRUCAO_SECRETARIA) or {}
        acao = resultado.get("acao")
        dados = resultado.get("dados", {}) or {}
        resposta = resultado.get("resposta", "✅ Comando processado.")
        print(f"[voice] gpt -> acao={acao} dados={dados} resposta='{resposta[:80]}...'")

        # 4) executa ação (se houver)
        if acao:
            sucesso = await executar_acao_gpt(update, context, acao, dados)
            if not sucesso:
                return

        # 5) responde
        await update.message.reply_text(resposta, parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Erro em processar_comando_voz: {e}")
        await update.message.reply_text(f"❌ Ocorreu um erro ao executar o comando de voz:\n{e}")
