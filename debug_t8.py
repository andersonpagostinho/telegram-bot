import asyncio
from utils.operacao_service import (
    adquirir_lease_operacao,
    gerar_proprietario_id,
    criar_operacao_em_andamento
)

async def test():
    tenant_a = 'debug_a'
    tenant_b = 'debug_b'
    op_id = 'op_inexistente'

    # Teste 1: Adquirir lease de operacao inexistente
    print("Teste 1: Adquirir lease de operacao inexistente em tenant_a")
    prop = gerar_proprietario_id()
    resultado = await adquirir_lease_operacao(
        tenant_id=tenant_a,
        operacao_id=op_id,
        proprietario_id=prop,
        lease_ttl_minutos=5
    )
    print(f"  Resultado: ok={resultado.get('ok')}, motivo={resultado.get('motivo')}")

    # Teste 2: Criar em A, tentar adquirir em B
    print("\nTeste 2: Criar em A, tentar adquirir em B")
    prop_a = gerar_proprietario_id()
    op_id_2 = 'op_em_a'

    await criar_operacao_em_andamento(
        tenant_id=tenant_a,
        operacao_id=op_id_2,
        actor_id='user',
        tipo='agendamento',
        dados_confirmados={},
        proprietario_id=prop_a,
        lease_ttl_minutos=5
    )
    print(f"  Criado em tenant_a: {op_id_2}")

    # Tentar adquirir em tenant_b
    prop_b = gerar_proprietario_id()
    resultado2 = await adquirir_lease_operacao(
        tenant_id=tenant_b,  # <-- tenant B, not A
        operacao_id=op_id_2,
        proprietario_id=prop_b,
        lease_ttl_minutos=5
    )
    print(f"  Resultado (B adquirindo de A): ok={resultado2.get('ok')}, motivo={resultado2.get('motivo')}")

asyncio.run(test())
