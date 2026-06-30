"""
F8 MVP — TESTES CORE DE LISTA DE ESPERA

Versão simplificada focando na funcionalidade central:
- Criar entrada
- Buscar compatível (FIFO)
- Marcar como notificado/convertido/cancelado
- Validar tenant isolation
- Validar sem dependências complexas

Testes: F8-1 a F8-8 (validações de core)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

from services.lista_espera_service import (
    criar_lista_espera,
    buscar_proxima_lista_espera_compativel,
    marcar_como_notificado,
    marcar_como_convertido,
    marcar_como_cancelado,
    buscar_lista_espera_por_id,
)
from services.firebase_service_async import (
    buscar_subcolecao,
    deletar_dado_em_path,
)

FUSO_BR = timezone("America/Sao_Paulo")


def gerar_tenant_teste():
    """ID único de tenant."""
    return f"tenant_t_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def gerar_cliente_id():
    """ID único de cliente."""
    return f"cli_t_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


@pytest.mark.asyncio
async def test_f8_1_criar_lista_espera():
    """[F8-1] Criar entrada quando cliente aceita entrar."""
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    amanha = (datetime.now(FUSO_BR) + timedelta(days=1)).date().strftime("%Y-%m-%d")

    # Criar ListaEspera
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="João",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=amanha,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_xyz",
    )

    assert resultado.get("status") == "ok"
    waitlist_id = resultado.get("waitlist_id")

    # Validar em Firestore
    doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc is not None
    assert doc.get("status") == "ativo"
    assert doc.get("servico_desejado", {}).get("servico") == "corte"
    assert doc.get("cliente", {}).get("cliente_nome") == "João"
    assert doc.get("auditoria", {}).get("criado_em") is not None

    print("✅ F8-1: Criação de ListaEspera funcionando")


@pytest.mark.asyncio
async def test_f8_2_buscar_compativel():
    """[F8-2] Buscar entrada compatível (FIFO)."""
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()
    data_str = "2026-07-10"

    # Criar entrada
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Maria",
        servico="escova",
        profissional_preferido="Carol",
        data_desejada=data_str,
        hora_desejada="14:00",
        duracao_minutos=45,
        evento_conflitante_id="evt_1",
    )

    # Buscar compatível
    waitlist = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="escova",
        profissional_preferido="Carol",
        data_desejada=data_str,
        hora_desejada="14:00",
        duracao_minutos=45,
    )

    assert waitlist is not None
    assert waitlist.get("cliente", {}).get("cliente_nome") == "Maria"
    print("✅ F8-2: Busca de compatível funcionando")


@pytest.mark.asyncio
async def test_f8_3_marcar_notificado():
    """[F8-3] Marcar como notificado após cancelamento."""
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    # Criar e buscar
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Pedro",
        servico="massagem",
        profissional_preferido="Tania",
        data_desejada="2026-07-15",
        hora_desejada="11:00",
        duracao_minutos=60,
        evento_conflitante_id="evt_2",
    )
    waitlist_id = resultado.get("waitlist_id")

    # Marcar como notificado
    sucesso = await marcar_como_notificado(tenant_id, waitlist_id)
    assert sucesso is True

    # Validar
    doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc.get("status") == "notificado"
    assert doc.get("auditoria", {}).get("ultima_notificacao_em") is not None
    assert doc.get("auditoria", {}).get("tentativas_notificacao") == 1

    print("✅ F8-3: Marcar como notificado funcionando")


@pytest.mark.asyncio
async def test_f8_4_marcar_convertido():
    """[F8-4] Marcar como convertido após evento criado."""
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    # Criar e notificar
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Ana",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-07-20",
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_3",
    )
    waitlist_id = resultado.get("waitlist_id")

    await marcar_como_notificado(tenant_id, waitlist_id)

    # Marcar como convertido
    sucesso = await marcar_como_convertido(tenant_id, waitlist_id, "evento_123")
    assert sucesso is True

    # Validar
    doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc.get("status") == "convertido"
    assert doc.get("evento_criado_apos_encaixe") == "evento_123"
    assert doc.get("auditoria", {}).get("confirmado_em") is not None

    print("✅ F8-4: Marcar como convertido funcionando")


@pytest.mark.asyncio
async def test_f8_5_marcar_cancelado():
    """[F8-5] Marcar como cancelado quando cliente recusa."""
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    # Criar
    resultado = await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Bruno",
        servico="barba",
        profissional_preferido="João",
        data_desejada="2026-07-25",
        hora_desejada="15:00",
        duracao_minutos=20,
        evento_conflitante_id="evt_4",
    )
    waitlist_id = resultado.get("waitlist_id")

    # Marcar como cancelado
    sucesso = await marcar_como_cancelado(tenant_id, waitlist_id)
    assert sucesso is True

    # Validar
    doc = await buscar_lista_espera_por_id(tenant_id, waitlist_id)
    assert doc.get("status") == "cancelado"

    print("✅ F8-5: Marcar como cancelado funcionando")


@pytest.mark.asyncio
async def test_f8_6_fifo_prioridade():
    """[F8-6] FIFO: primeiro criado tem prioridade."""
    tenant_id = gerar_tenant_teste()
    data_str = "2026-08-01"

    # Cliente 1 (primeiro)
    cliente_1 = gerar_cliente_id()
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_1}",
        cliente_id=cliente_1,
        cliente_nome="Xavier",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_5a",
    )

    # Pequeno delay
    await asyncio.sleep(0.1)

    # Cliente 2 (depois)
    cliente_2 = gerar_cliente_id()
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_2}",
        cliente_id=cliente_2,
        cliente_nome="Yasmin",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_5b",
    )

    # Buscar: deve retornar Cliente 1 (FIFO)
    waitlist = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    assert waitlist.get("cliente", {}).get("cliente_nome") == "Xavier"

    # Marcar primeiro como notificado
    await marcar_como_notificado(tenant_id, waitlist.get("waitlist_id"))

    # Buscar novamente: deve retornar Cliente 2 (próximo na fila)
    waitlist2 = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_str,
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    assert waitlist2.get("cliente", {}).get("cliente_nome") == "Yasmin"

    print("✅ F8-6: FIFO funcionando")


@pytest.mark.asyncio
async def test_f8_7_multi_tenant():
    """[F8-7] Multi-tenant isolation."""
    tenant_a = gerar_tenant_teste()
    tenant_b = gerar_tenant_teste()
    cliente_a = gerar_cliente_id()
    cliente_b = gerar_cliente_id()

    # Criar em Tenant A
    await criar_lista_espera(
        tenant_id=tenant_a,
        actor_id=f"whatsapp:{cliente_a}",
        cliente_id=cliente_a,
        cliente_nome="Alice",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-05",
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_a",
    )

    # Criar em Tenant B (mesmo horário)
    await criar_lista_espera(
        tenant_id=tenant_b,
        actor_id=f"whatsapp:{cliente_b}",
        cliente_id=cliente_b,
        cliente_nome="Bob",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-05",
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_b",
    )

    # Buscar em Tenant A
    waitlist_a = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_a,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-05",
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Buscar em Tenant B
    waitlist_b = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_b,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-05",
        hora_desejada="10:00",
        duracao_minutos=30,
    )

    # Validar isolamento
    assert waitlist_a.get("cliente", {}).get("cliente_nome") == "Alice"
    assert waitlist_b.get("cliente", {}).get("cliente_nome") == "Bob"
    assert waitlist_a.get("tenant_id") == tenant_a
    assert waitlist_b.get("tenant_id") == tenant_b

    print("✅ F8-7: Multi-tenant isolation funcionando")


@pytest.mark.asyncio
async def test_f8_8_compatibilidade_duracao():
    """[F8-8] Duração: waitlist pode ter duracao <= disponível."""
    tenant_id = gerar_tenant_teste()
    cliente_id = gerar_cliente_id()

    # Cliente aguarda 30 min
    await criar_lista_espera(
        tenant_id=tenant_id,
        actor_id=f"whatsapp:{cliente_id}",
        cliente_id=cliente_id,
        cliente_nome="Carol",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-10",
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_8",
    )

    # Vaga com 60 min (maior que esperado: OK)
    waitlist = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-10",
        hora_desejada="10:00",
        duracao_minutos=60,  # Mais tempo disponível
    )

    assert waitlist is not None  # Deve encontrar

    # Vaga com 20 min (menor que esperado: NÃO)
    waitlist_menor = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_id,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-10",
        hora_desejada="10:00",
        duracao_minutos=20,  # Menos tempo disponível
    )

    assert waitlist_menor is None  # Não deve encontrar

    print("✅ F8-8: Validação de duração funcionando")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
