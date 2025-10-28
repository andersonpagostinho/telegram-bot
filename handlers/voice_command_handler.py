from services.firebase_service_async import buscar_cliente, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao
from services.gpt_executor import executar_acao_gpt
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.plan_utils import verificar_pagamento

async def processar_comando_voz(update, context, texto):
    try:
        texto = (texto or "").lower().strip()
        user_id = str(update.effective_user.id)
        print(f"[voice] recebido de {user_id}: '{texto}'")

        # 1) checa pagamento (não checa “módulo voz”; tudo mapeia para 'secretaria')
        if not await verificar_pagamento(update, context):
            return

        # 2) contexto
        try:
            dados_usuario = await buscar_cliente(user_id)
        except Exception as e:
            print(f"[voice] erro ao buscar cliente: {e}")
            dados_usuario = None

        # Fallback se não achou o cliente por algum motivo
        if not dados_usuario:
            dados_usuario = {
                "nome": (getattr(update.effective_user, "first_name", "") or "Desconhecido"),
                "pagamentoAtivo": True,
                "planosAtivos": ["secretaria"],
                "tipo_usuario": "dono",
                "id_negocio": user_id,
            }

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

        tarefas = [t.get("descricao") for t in tarefas_dict.values() if isinstance(t, dict) and t.get("descricao")]
        eventos = [e.get("descricao") for e in eventos_dict.values() if isinstance(e, dict) and e.get("descricao")]

        contexto = {
            "usuario": dados_usuario,   # ✅ PERFIL REAL ENTRA AQUI
            "tarefas": tarefas,
            "eventos": eventos,
            "emails": []
        }

        # 3) GPT decide (passa user_id e “forçar plano ativo”)
        resultado = await processar_com_gpt_com_acao(
            texto,
            contexto,
            INSTRUCAO_SECRETARIA,
            user_id=user_id,                 # ✅
            forcar_plano_ativo=True          # ✅ evita bloqueio por defaults
        ) or {}

        acao = resultado.get("acao")
        dados = resultado.get("dados", {}) or {}
        resposta = resultado.get("resposta", "✅ Comando processado.")

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
