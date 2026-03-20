# utils/context_manager.py
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path

CONTEXT_PATH_TEMPLATE = "Clientes/{user_id}/MemoriaTemporaria/contexto"

# 🔄 Salvar contexto completo (ou atualizar)
async def salvar_contexto_temporario(user_id: str, contexto: dict):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await atualizar_dado_em_path(path, contexto)  # merge=True

# 🔍 Carregar contexto salvo
async def carregar_contexto_temporario(user_id: str):
    path = CONTEXT_PATH_TEMPLATE.format(user_id=user_id)
    return await buscar_dado_em_path(path)

# 🧠 Atualiza histórico apenas se for diferente da última entrada
async def atualizar_contexto(user_id: str, nova_interacao: dict):
    contexto = await carregar_contexto_temporario(user_id) or {}
    historico = contexto.setdefault("historico", [])

    if not historico or historico[-1] != nova_interacao:
        historico.append(nova_interacao)
        contexto["historico"] = historico[-5:]  # mantém só os últimos 5
        await salvar_contexto_temporario(user_id, contexto)

    return contexto

async def limpar_contexto(user_id: str):
    await salvar_contexto_temporario(user_id, {"historico": []})
    return True

# 🧹 Limpa apenas o contexto relacionado a agendamento
async def limpar_contexto_agendamento(user_id: str):
    contexto = await carregar_contexto_temporario(user_id) or {}

    campos_para_remover = [
        # núcleo do fluxo
        "estado_fluxo",
        "draft_agendamento",
        "aguardando_confirmacao_agendamento",
        "dados_confirmacao_agendamento",

        # slots e espelhos legados
        "data_hora",
        "servico",
        "profissional_escolhido",
        "ultima_opcao_profissionais",

        # conflito / sugestão
        "sugestoes",
        "alternativa_profissional",

        # confirmação / execução
        "evento_criado",
        "ultima_acao",
        "ultima_intencao",
        "dados_anteriores",
        "data_hora_confirmada",

        # auxiliares do router
        "pergunta_amanha_mesmo_horario",
        "data_hora_pendente",
        "ultima_consulta",
    ]

    for campo in campos_para_remover:
        contexto.pop(campo, None)

    contexto["estado_fluxo"] = "idle"

    await salvar_contexto_temporario(user_id, contexto)
    print("🧹 Contexto de agendamento limpo com sucesso.")
    return True