from services.firebase_service_async import buscar_cliente

# ✅ Verifica se o usuário é dono do negócio
async def verificar_dono(user_id: str):
    cliente = await buscar_cliente(user_id)
    return cliente and cliente.get("id_negocio") == user_id