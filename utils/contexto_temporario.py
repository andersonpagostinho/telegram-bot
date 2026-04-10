from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path

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