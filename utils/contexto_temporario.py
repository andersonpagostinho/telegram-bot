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
        # 🔥 neutralização (não delete)
        "modo_escolha_horario": False,
        "horarios_sugeridos": [],
        "alternativa_profissional": None,
        "ultima_opcao_profissionais": [],

        # deletes OK
        "aguardando_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
        "dados_anteriores": firestore.DELETE_FIELD,
        "draft_agendamento": {},
        "ultima_acao": None,
        "hora_confirmada": None,
        "sugestoes": [],
        "ultima_consulta": None,
        "data_hora": None,
        "servico": None,
        "profissional_escolhido": None,

        "estado_fluxo": "idle"
    }

    print(f"🧪 [CLEAR CTX] path={path} | payload={payload}", flush=True)
    return await atualizar_dado_em_path(path, payload)