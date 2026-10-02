from services.firebase_service_async import buscar_cliente, buscar_subcolecao
from services.gpt_service import processar_com_gpt_com_acao
from services.gpt_executor import executar_acao_gpt
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

async def processar_comando_voz(update, context, texto):
    try:
        # ✅ chat_id e user_id sempre definidos
        chat_id = update.effective_chat.id
        user_id = str(update.effective_user.id)

        # 🔤 normaliza o texto transcrito
        texto = (texto or "").strip()

        # [TESTE_SURI] 1️⃣ TEXTO TRANSCRITO
        print(f"[TESTE_SURI] 1️⃣ TEXTO_TRANSCRITO: {repr(texto)}", flush=True)

        # 🔄 1) Coletar dados do usuário
        dados_usuario = await buscar_cliente(user_id) or {}
        tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas") or {}
        eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}

        tarefas = [
            t.get("descricao")
            for t in tarefas_dict.values()
            if isinstance(t, dict) and t.get("descricao")
        ]
        eventos = [
            e.get("descricao")
            for e in eventos_dict.values()
            if isinstance(e, dict) and e.get("descricao")
        ]

        # ⚙️ 2) Contexto enviado ao GPT (força plano ativo pra não bloquear na voz)
        contexto = {
            "user_id": user_id,
            "usuario": {
                **dados_usuario,
                "pagamentoAtivo": True,
                "planosAtivos": list(set((dados_usuario.get("planosAtivos") or []) + ["secretaria"])),
            },
            "pagamentoAtivo": True,
            "planosAtivos": list(set((dados_usuario.get("planosAtivos") or []) + ["secretaria"])),
            "tarefas": tarefas,
            "eventos": eventos,
            "emails": [],
        }

        # 🧠 3) Decisão + ação (passa SEMPRE o user_id correto)
        resultado = await processar_com_gpt_com_acao(
            texto_usuario=texto,
            contexto=contexto,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,  # ✅ corrigido
        )

        acao = resultado.get("acao")
        dados = resultado.get("dados", {}) or {}
        resposta = resultado.get("resposta", "✅ Comando processado.")

        # [TESTE_SURI] 2️⃣ JSON BRUTO DO GPT
        print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: acao={repr(acao)}", flush=True)
        print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: dados_keys={list((dados or {}).keys())}", flush=True)
        if "cliente_nome" in (dados or {}):
            print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: cliente_nome={repr(dados.get('cliente_nome'))}", flush=True)
        if "profissional" in (dados or {}):
            print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: profissional={repr(dados.get('profissional'))}", flush=True)
        if "servico" in (dados or {}):
            print(f"[TESTE_SURI] 2️⃣ JSON_DO_GPT: servico={repr(dados.get('servico'))}", flush=True)

        # 🚀 4) Executa ação (se houver)
        if acao:
            sucesso = await executar_acao_gpt(update, context, acao, dados)
            if sucesso is False:
                return

        # 💬 5) Responde ao usuário
        if getattr(update, "message", None):
            await update.message.reply_text(resposta, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=chat_id, text=resposta, parse_mode="Markdown")

    except Exception as e:
        erro = f"❌ Ocorreu um erro ao executar o comando de voz:\n{e}"
        try:
            if getattr(update, "message", None):
                await update.message.reply_text(erro)
            else:
                await context.bot.send_message(chat_id=chat_id, text=erro)
        except Exception:
            pass
        print(f"❌ Erro em processar_comando_voz: {e}")
