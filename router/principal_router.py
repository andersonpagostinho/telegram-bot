# router/principal_router.py

from utils.intencao_utils import identificar_intencao
from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt  # ✅ Correto
from utils.context_manager import atualizar_contexto, carregar_contexto_temporario
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import buscar_subcolecao, buscar_documento
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")
    # 🔍 Buscar dados do usuário em Clientes/{user_id}/Usuarios/{user_id}
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

    # 🔁 Verifica intenção direta (ex: criar tarefa, perguntar preço etc.)
    intencao = identificar_intencao(mensagem)
    if intencao:
        print(f"🚀 Intenção detectada: {intencao}")
        contexto = await carregar_contexto_temporario(user_id) or {}
        contexto["usuario"] = usuario_dados
        contexto.setdefault("tarefas", [])
        contexto.setdefault("eventos", [])
        contexto.setdefault("emails", [])
        contexto.setdefault("profissionais", [])
        contexto.setdefault("followups", [])

        resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_gpt["resposta"]})
        await executar_acao_gpt(update, context, resposta_gpt["acao"], resposta_gpt["dados"])
        return

    # 🔄 Sessão ativa (ex: agendamento em andamento)
    sessao = await pegar_sessao(user_id)
    if sessao and sessao.get("estado"):
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        print("📤 Chamando tratar_mensagem_gpt via principal_router")
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

    # 🤝 Cumprimento amigável
    cumprimentos = ["oi", "olá", "bom dia", "boa tarde", "boa noite", "e aí", "tudo bem?"]
    if resposta_gpt.get("acao") == "buscar_tarefas_do_usuario" and mensagem.lower().strip() in cumprimentos:
        resposta_gpt = {
            "resposta": "Olá! Como posso ajudar?",
            "acao": None,
            "dados": {}
        }

    await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_gpt["resposta"]})

    # 🛡️ Valida se a ação é suportada
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
        "buscar_eventos_do_dia",
    }

    acao = resposta_gpt.get("acao")
    if acao and acao not in ACOES_SUPORTADAS:
        print(f"⚠️ Ação '{acao}' não suportada. Ignorando...")
        resposta_gpt["acao"] = None
        resposta_gpt["dados"] = {}

    await executar_acao_gpt(update, context, resposta_gpt["acao"], resposta_gpt["dados"])
    return resposta_gpt["resposta"]
