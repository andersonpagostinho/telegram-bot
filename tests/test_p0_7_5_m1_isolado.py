"""
Teste M1 isolado com ID único — Verificar estado_fluxo no Firestore
"""
import pytest
import asyncio
from datetime import datetime
from utils.contexto_temporario import carregar_contexto_temporario_v2

@pytest.mark.asyncio
async def test_m1_isolado_estado_fluxo():
    """
    Teste M1 com actor_id único (sem conflito de sessão anterior)
    Verificar: estado_fluxo deve ser "aguardando_servico" após M1
    """
    from router.principal_router import roteador_principal

    tenant_id = "7394370553"
    # Usar timestamp para ID único
    import time
    ts = str(int(time.time() * 1000))[-8:]
    wa_id = f"5511991999{ts}"
    actor_id = f"whatsapp:{wa_id}"

    print(f"\n=== M1 ISOLADO ===")
    print(f"wa_id: {wa_id}, actor_id: {actor_id}")

    # M1
    resposta_m1 = await roteador_principal(
        user_id=wa_id,
        mensagem="a bruna esta disponivel amanha as 10?",
        tenant_id=tenant_id,
        phone_number_id="123456"
    )

    print(f"[M1] Resposta: {str(resposta_m1)[:100]}")

    # Ler Firestore
    ctx_m1 = await carregar_contexto_temporario_v2(tenant_id, actor_id)

    print(f"\n=== FIRESTORE APÓS M1 ===")
    print(f"estado_fluxo: {ctx_m1.get('estado_fluxo')} (esperado: aguardando_servico)")
    print(f"intencao: {ctx_m1.get('intencao_conversacional')}")
    print(f"draft: {ctx_m1.get('draft_agendamento')}")

    assert ctx_m1.get("estado_fluxo") == "aguardando_servico", \
        f"M1 deve setar estado para aguardando_servico, mas tem {ctx_m1.get('estado_fluxo')}"

    print("✅ M1 PASSOU")
