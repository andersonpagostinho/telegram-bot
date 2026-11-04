"""
Teste de continuidade de identidade — user_id FIXO
"""
import pytest
from utils.contexto_temporario import carregar_contexto_temporario_v2

@pytest.mark.asyncio
async def test_continuidade_actor_id():
    """
    Verificar que M1 → M2 usam o MESMO actor_id
    """
    from router.principal_router import roteador_principal

    tenant_id = "7394370553"
    # User_id FIXO, nenhum UUID
    user_id = "5511991111111"
    expected_actor_id = f"whatsapp:{user_id}"

    print(f"\n=== TESTE IDENTIDADE ===")
    print(f"Tenant: {tenant_id}")
    print(f"User_id: {user_id}")
    print(f"Expected actor_id: {expected_actor_id}")

    # M1
    print(f"\n[M1] Enviando...")
    await roteador_principal(
        user_id=user_id,
        mensagem="a bruna esta disponivel amanha as 10?",
        tenant_id=tenant_id,
        phone_number_id="123456"
    )

    ctx_m1 = await carregar_contexto_temporario_v2(tenant_id, expected_actor_id)
    m1_actor_id = f"whatsapp:{ctx_m1.get('_actor_id', user_id).split(':')[-1] if ctx_m1.get('_actor_id') else user_id}"
    print(f"[M1] Actor_id encontrado: {m1_actor_id}")

    # M2
    print(f"\n[M2] Enviando...")
    await roteador_principal(
        user_id=user_id,
        mensagem="fora ela tem alguma outra que faz manicure?",
        tenant_id=tenant_id,
        phone_number_id="123456"
    )

    ctx_m2 = await carregar_contexto_temporario_v2(tenant_id, expected_actor_id)
    m2_actor_id = f"whatsapp:{ctx_m2.get('_actor_id', user_id).split(':')[-1] if ctx_m2.get('_actor_id') else user_id}"
    print(f"[M2] Actor_id encontrado: {m2_actor_id}")

    # M3
    print(f"\n[M3] Enviando...")
    await roteador_principal(
        user_id=user_id,
        mensagem="ok pode ser com a bruna",
        tenant_id=tenant_id,
        phone_number_id="123456"
    )

    ctx_m3 = await carregar_contexto_temporario_v2(tenant_id, expected_actor_id)
    m3_actor_id = f"whatsapp:{ctx_m3.get('_actor_id', user_id).split(':')[-1] if ctx_m3.get('_actor_id') else user_id}"
    print(f"[M3] Actor_id encontrado: {m3_actor_id}")

    # Validar
    print(f"\n=== RESULTADO ===")
    print(f"M1 actor_id: {m1_actor_id}")
    print(f"M2 actor_id: {m2_actor_id}")
    print(f"M3 actor_id: {m3_actor_id}")
    print(f"Esperado:   {expected_actor_id}")

    assert m1_actor_id == expected_actor_id, f"M1 actor_id divergiu: {m1_actor_id} != {expected_actor_id}"
    assert m2_actor_id == expected_actor_id, f"M2 actor_id divergiu: {m2_actor_id} != {expected_actor_id}"
    assert m3_actor_id == expected_actor_id, f"M3 actor_id divergiu: {m3_actor_id} != {expected_actor_id}"

    print("✅ IDENTIDADE CONTÍNUA")
