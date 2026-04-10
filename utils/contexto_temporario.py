from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path

async def salvar_contexto_temporario(user_id: str, contexto: dict):
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
    print(f"🧪 [SAVE CTX] path={path} | contexto={contexto}", flush=True)
    # ✅ merge=True (não apaga outros campos do documento)
    return await atualizar_dado_em_path(path, contexto)

async def carregar_contexto_temporario(user_id: str):
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
    data = await buscar_dado_em_path(path)
    print(f"🧪 [LOAD CTX] path={path} | data={data}", flush=True)
    return data