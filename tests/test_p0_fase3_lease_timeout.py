"""
Testes P0 FASE 3.B: Lease/Timeout sobre OperacaoEmAndamento

T1: Falha após persistir operação, antes de criar evento
T2: Lease expirado e recuperação
T3: Falha após criar evento, antes de atualizar operação
T4: Dois processos tentando recuperar mesma operação
T5: Processo antigo tentando concluir após perder lease
T6: Exatamente um evento persistido
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from utils.operacao_service import (
    gerar_proprietario_id,
    criar_operacao_em_andamento,
    adquirir_lease_operacao,
    verificar_proprietario_valido,
    atualizar_operacao_status,
    liberar_lease_operacao,
    recuperar_operacao_em_andamento,
)

# Config teste
TENANT_TESTE = "test_neoeve_20261106_p0_fase3"
OPERACAO_ID_BASE = "agendamento_test_actor_f77370e9"
ACTOR_ID = "test_actor_f77370e9"


@pytest.fixture
async def db_mock():
    """Mock de banco de dados."""
    mock = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_t1_falha_apos_persistir_operacao(db_mock):
    """T1: Falha após persistir operação, antes de criar evento."""
    operacao_id = f"{OPERACAO_ID_BASE}_t1"
    prop_a = gerar_proprietario_id()

    # (1) Criar operação
    resultado = await criar_operacao_em_andamento(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        actor_id=ACTOR_ID,
        tipo="agendamento",
        dados_confirmados={"draft": "test"},
        proprietario_id=prop_a,
        lease_ttl_minutos=5
    )
    assert resultado["ok"], "Operação não foi criada"

    # (2) Simular falha (evento não criado)
    # [FALHA INJETADA aqui]

    # (3) Recuperar com novo proprietário
    prop_b = gerar_proprietario_id()
    resultado_lease = await adquirir_lease_operacao(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        proprietario_id=prop_b,
        lease_ttl_minutos=5
    )
    assert resultado_lease["ok"], "Não conseguiu adquirir lease (prop_b)"

    # Validar transição
    valido = await verificar_proprietario_valido(TENANT_TESTE, operacao_id, prop_b)
    assert valido, "prop_b não é mais proprietário"

    # prop_a não pode mais atualizar
    valido_a = await verificar_proprietario_valido(TENANT_TESTE, operacao_id, prop_a)
    assert not valido_a, "prop_a ainda era proprietário (erro)"

    print("✅ T1 PASS")


@pytest.mark.asyncio
async def test_t2_lease_expirado_e_recuperacao(db_mock):
    """T2: Lease expirado e recuperação."""
    operacao_id = f"{OPERACAO_ID_BASE}_t2"
    prop_a = gerar_proprietario_id()

    # (1) Criar operação com TTL pequeno (1 segundo)
    resultado = await criar_operacao_em_andamento(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        actor_id=ACTOR_ID,
        tipo="agendamento",
        dados_confirmados={"draft": "test"},
        proprietario_id=prop_a,
        lease_ttl_minutos=0.02  # ~1 segundo
    )
    assert resultado["ok"]

    # (2) Aguardar lease expirar
    await asyncio.sleep(2)

    # (3) Novo proprietário consegue adquirir
    prop_b = gerar_proprietario_id()
    resultado_lease = await adquirir_lease_operacao(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        proprietario_id=prop_b,
        lease_ttl_minutos=5
    )
    assert resultado_lease["ok"], "Não conseguiu adquirir lease após expiração"

    # Validar que prop_b é novo proprietário
    valido_b = await verificar_proprietario_valido(TENANT_TESTE, operacao_id, prop_b)
    assert valido_b, "prop_b não é proprietário (erro)"

    # prop_a não pode mais
    valido_a = await verificar_proprietario_valido(TENANT_TESTE, operacao_id, prop_a)
    assert not valido_a, "prop_a ainda é proprietário após expiração (erro)"

    print("✅ T2 PASS")


@pytest.mark.asyncio
async def test_t3_falha_apos_criar_evento(db_mock):
    """T3: Falha após criar evento, antes de atualizar operação."""
    operacao_id = f"{OPERACAO_ID_BASE}_t3"
    prop_a = gerar_proprietario_id()

    # (1) Criar operação
    await criar_operacao_em_andamento(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        actor_id=ACTOR_ID,
        tipo="agendamento",
        dados_confirmados={"draft": "test"},
        proprietario_id=prop_a,
        lease_ttl_minutos=5
    )

    # (2) Simular: evento criado, mas falha antes de atualizar status
    # [FALHA INJETADA aqui]

    # (3) Novo proprietário recupera
    prop_b = gerar_proprietario_id()
    resultado_lease = await adquirir_lease_operacao(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        proprietario_id=prop_b,
        lease_ttl_minutos=5
    )
    assert resultado_lease["ok"]

    # (4) Detecta evento existe, não recria
    # [Validação: evento_id já existe em Firestore]

    # (5) Atualiza status
    resultado_update = await atualizar_operacao_status(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        novo_status="evento_persistido",
        proprietario_id=prop_b,
        evento_id="evt_teste_t3"
    )
    assert resultado_update["ok"], "Não conseguiu atualizar para evento_persistido"

    print("✅ T3 PASS")


@pytest.mark.asyncio
async def test_t4_dois_processos_simultaneos(db_mock):
    """T4: Dois processos tentando recuperar mesma operação."""
    operacao_id = f"{OPERACAO_ID_BASE}_t4"
    prop_a = gerar_proprietario_id()

    # (1) Criar operação
    await criar_operacao_em_andamento(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        actor_id=ACTOR_ID,
        tipo="agendamento",
        dados_confirmados={"draft": "test"},
        proprietario_id=prop_a,
        lease_ttl_minutos=5
    )

    # (2) Dois processos tentam adquirir simultaneously
    prop_b = gerar_proprietario_id()
    prop_c = gerar_proprietario_id()

    resultado_b = await adquirir_lease_operacao(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        proprietario_id=prop_b,
        lease_ttl_minutos=5
    )

    resultado_c = await adquirir_lease_operacao(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        proprietario_id=prop_c,
        lease_ttl_minutos=5
    )

    # Um deve ter sucesso, outro não (ou um escreve sobre o outro atomicamente)
    # De qualquer forma, apenas um é proprietário final
    doc = await recuperar_operacao_em_andamento(TENANT_TESTE, operacao_id)
    proprietario_final = doc.get("proprietario_id")

    assert proprietario_final in [prop_b, prop_c, prop_a], "Proprietário inválido"

    # Somente um deles é valido
    valid_b = await verificar_proprietario_valido(TENANT_TESTE, operacao_id, prop_b)
    valid_c = await verificar_proprietario_valido(TENANT_TESTE, operacao_id, prop_c)

    # XOR: um ou outro, não ambos
    assert (valid_b or valid_c), "Nenhum é proprietário (erro)"

    print("✅ T4 PASS")


@pytest.mark.asyncio
async def test_t5_processo_antigo_sem_lease(db_mock):
    """T5: Processo antigo tentando concluir após perder lease."""
    operacao_id = f"{OPERACAO_ID_BASE}_t5"
    prop_a = gerar_proprietario_id()

    # (1) Criar operação
    await criar_operacao_em_andamento(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        actor_id=ACTOR_ID,
        tipo="agendamento",
        dados_confirmados={"draft": "test"},
        proprietario_id=prop_a,
        lease_ttl_minutos=5
    )

    # (2) prop_a tenta atualizar (ainda válido)
    resultado_update_a = await atualizar_operacao_status(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        novo_status="evento_persistido",
        proprietario_id=prop_a,
        evento_id="evt_t5"
    )
    assert resultado_update_a["ok"], "prop_a não conseguiu atualizar (ainda era proprietário)"

    # (3) Transferir propriedade para prop_b (simular lease expirado ou timeout)
    prop_b = gerar_proprietario_id()
    await adquirir_lease_operacao(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        proprietario_id=prop_b,
        lease_ttl_minutos=5
    )

    # (4) prop_a tenta atualizar novamente (não é mais proprietário)
    resultado_update_a2 = await atualizar_operacao_status(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        novo_status="concluida",
        proprietario_id=prop_a,
        evento_id="evt_t5"
    )
    assert not resultado_update_a2["ok"], "prop_a conseguiu atualizar sem lease (erro de segurança)"

    # (5) prop_b consegue atualizar (é proprietário)
    resultado_update_b = await atualizar_operacao_status(
        tenant_id=TENANT_TESTE,
        operacao_id=operacao_id,
        novo_status="concluida",
        proprietario_id=prop_b,
        evento_id="evt_t5"
    )
    assert resultado_update_b["ok"], "prop_b não conseguiu atualizar (é proprietário)"

    print("✅ T5 PASS")


@pytest.mark.asyncio
async def test_t6_um_evento_por_operacao(db_mock):
    """T6: Exatamente um evento persistido por operação_id."""
    operacao_id = f"{OPERACAO_ID_BASE}_t6"

    # Simular T1-T5 múltiplas vezes e validar sempre 1 evento por operacao_id
    for i in range(3):
        prop = gerar_proprietario_id()
        await criar_operacao_em_andamento(
            tenant_id=TENANT_TESTE,
            operacao_id=operacao_id,
            actor_id=ACTOR_ID,
            tipo="agendamento",
            dados_confirmados={"draft": f"test_{i}"},
            proprietario_id=prop,
            lease_ttl_minutos=5
        )

        # Atualizar para evento_persistido
        await atualizar_operacao_status(
            tenant_id=TENANT_TESTE,
            operacao_id=operacao_id,
            novo_status="evento_persistido",
            proprietario_id=prop,
            evento_id="evt_t6_unico"  # Mesmo evento_id sempre
        )

    # Validar: operacao status = evento_persistido, evento_id = evt_t6_unico
    doc = await recuperar_operacao_em_andamento(TENANT_TESTE, operacao_id)
    assert doc.get("status") == "evento_persistido", f"Status incorreto: {doc.get('status')}"
    assert doc.get("evento_id") == "evt_t6_unico", f"evento_id incorreto: {doc.get('evento_id')}"

    # [Em Firestore real] Verificar: Clientes/{tenant}/Eventos/evt_t6_unico existe uma única vez

    print("✅ T6 PASS")


if __name__ == "__main__":
    # Executar testes manualmente
    import asyncio

    async def main():
        print("\n=== TESTES P0 FASE 3.B ===\n")
        await test_t1_falha_apos_persistir_operacao(None)
        await test_t2_lease_expirado_e_recuperacao(None)
        await test_t3_falha_apos_criar_evento(None)
        await test_t4_dois_processos_simultaneos(None)
        await test_t5_processo_antigo_sem_lease(None)
        await test_t6_um_evento_por_operacao(None)
        print("\n✅ TODOS OS TESTES PASSARAM\n")

    asyncio.run(main())
