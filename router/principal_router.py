# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt, processar_com_gpt_com_acao
from utils.context_manager import atualizar_contexto, carregar_contexto_temporario
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import buscar_subcolecao, buscar_documento
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")

    # ✅ Verificar consulta informativa ANTES de tudo
    from services.informacao_service import responder_consulta_informativa

    resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
    if resposta_informativa:
        print("🔍 Consulta informativa detectada. Respondendo diretamente.")
        await context.bot.send_message(chat_id=user_id, text=resposta_informativa, parse_mode="Markdown")
        return resposta_informativa

    # 🔍 Buscar dados do usuário
    usuario_dados = await buscar_documento(f"Clientes/{user_id}/Usuarios/{user_id}")
    if not usuario_dados:
        usuario_dados = {
            "user_id": user_id,
            "nome": "Desconhecido",
            "pagamentoAtivo": False,
            "planosAtivos": [],
            "tipoNegocio": "não informado",
            "modo_uso": "interno",
            "tipo_usuario": "dono"
        }

    # 🔄 Sessão ativa (ex: agendamento, tarefa etc.)
    sessao = await pegar_sessao(user_id)
    if sessao and sessao.get("estado"):
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_fluxo})
        return resposta_fluxo

    # 🧠 Fallback inteligente com GPT contextualizado
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto["usuario"] = usuario_dados
    contexto.setdefault("tarefas", [])
    contexto.setdefault("eventos", [])
    contexto.setdefault("emails", [])
    contexto.setdefault("profissionais", [])
    contexto.setdefault("followups", [])

    profissionais_dict = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    contexto["profissionais"] = list(profissionais_dict.values())

    resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)
    print("🧠 resposta_gpt retornada:", resposta_gpt)

    # 🤝 Cumprimento amigável
    cumprimentos = ["oi", "olá", "bom dia", "boa tarde", "boa noite", "e aí", "tudo bem?"]
    if resposta_gpt.get("acao") == "buscar_tarefas_do_usuario" and mensagem.lower().strip() in cumprimentos:
        resposta_gpt = {
            "resposta": "Olá! Como posso ajudar?",
            "acao": None,
            "dados": {}
        }

    # 🛡️ Validação robusta
    if not resposta_gpt or not isinstance(resposta_gpt, dict):
        print("⚠️ Resposta do GPT inválida ou vazia:", resposta_gpt)
        await context.bot.send_message(chat_id=user_id, text="❌ Ocorreu um erro ao interpretar sua mensagem.")
        return

    resposta_texto = resposta_gpt.get("resposta")
    acao = resposta_gpt.get("acao")
    dados = resposta_gpt.get("dados", {})

    if resposta_texto:
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_texto})

    # ✅ Valida se a ação é suportada antes de executar
    ACOES_SUPORTADAS = {
        "consultar_preco_servico",
        "criar_evento",
        "buscar_eventos_da_semana",
        "criar_tarefa",
        "remover_tarefa",
        "listar_followups",
        "cadastrar_profissional",
        "aguardar_arquivo_importacao",
        "enviar_email",
        "organizar_semana",
        "buscar_tarefas_do_usuario",
        "buscar_emails",
        "verificar_pagamento",
        "verificar_acesso_modulo",
        "responder_audio",
        "criar_followup",
        "cancelar_evento",
        "buscar_eventos_do_dia",
    }

    if acao:
        if acao not in ACOES_SUPORTADAS:
            print(f"⚠️ Ação '{acao}' não suportada. Ignorando...")
            acao = None
            dados = {}
        await executar_acao_gpt(update, context, acao, dados)
    else:
        await context.bot.send_message(chat_id=user_id, text=resposta_texto or "❌ Sem ação definida.")

    return resposta_texto or "❌ Não consegui interpretar sua mensagem."
