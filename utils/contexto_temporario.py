from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from google.cloud import firestore

async def salvar_contexto_temporario(user_id: str, contexto: dict):
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    if not contexto:
        print(f"🚨 [BLOCK SAVE] contexto vazio bloqueado em {path}", flush=True)
        return

    # 🔥 merge manual defensivo
    atual = await buscar_dado_em_path(path) or {}

    atual.update(contexto)

    print(f"🧪 [SAVE CTX] path={path} | contexto_final={atual}", flush=True)

    return await atualizar_dado_em_path(path, atual)

async def carregar_contexto_temporario(user_id: str):
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
    data = await buscar_dado_em_path(path)

    if not data:
        print(f"🚨 [CTX VAZIO DETECTADO] path={path}", flush=True)

    print(f"🧪 [LOAD CTX] path={path} | data={data}", flush=True)
    return data

async def limpar_contexto_agendamento(user_id: str):
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    payload = {
        "modo_escolha_horario": firestore.DELETE_FIELD,
        "horarios_sugeridos": firestore.DELETE_FIELD,
        "alternativa_profissional": firestore.DELETE_FIELD,
        "aguardando_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_anteriores": firestore.DELETE_FIELD,
        "draft_agendamento": firestore.DELETE_FIELD,
        "ultima_acao": firestore.DELETE_FIELD,
        "hora_confirmada": firestore.DELETE_FIELD,
        "ultima_opcao_profissionais": firestore.DELETE_FIELD,
        "sugestoes": firestore.DELETE_FIELD,
        "ultima_consulta": firestore.DELETE_FIELD,
        "data_hora": firestore.DELETE_FIELD,
        "servico": firestore.DELETE_FIELD,
        "profissional_escolhido": firestore.DELETE_FIELD,
        "pergunta_amanha_mesmo_horario": firestore.DELETE_FIELD,
        "data_hora_pendente": firestore.DELETE_FIELD,
        "estado_fluxo": "idle"
    }

    print(f"🧪 [CLEAR CTX] path={path} | payload={payload}", flush=True)
    return await atualizar_dado_em_path(path, payload)