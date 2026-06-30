"""
F8 MVP — TESTE SEQUENCIAL ÚNICO

Um único teste que valida 8 cenários em sequência.
Evita interferência entre testes e problemas de isolamento.
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

FUSO_BR = timezone("America/Sao_Paulo")


@pytest.mark.asyncio
async def test_f8_todos_cenarios():
    """F8-1 até F8-8 em uma sequência única."""

    print("\n" + "="*70)
    print("  F8 MVP — TESTE SEQUENCIAL (F8-1 a F8-8)")
    print("="*70)

    # =========================================================
    # F8-1: Criar ListaEspera
    # =========================================================
    print("\n[F8-1] Criando entrada em ListaEspera...")
    tenant_1 = f"t_f81_{datetime.now().strftime('%H%M%S%f')}"
    cliente_1 = f"c_f81_{datetime.now().strftime('%H%M%S%f')}"
    amanha = (datetime.now(FUSO_BR) + timedelta(days=1)).date().strftime("%Y-%m-%d")

    r1 = await criar_lista_espera(
        tenant_id=tenant_1,
        actor_id=f"whatsapp:{cliente_1}",
        cliente_id=cliente_1,
        cliente_nome="João",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=amanha,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_xyz",
    )
    assert r1.get("status") == "ok", f"F8-1 falhou: {r1}"
    w1_id = r1.get("waitlist_id")
    w1 = await buscar_lista_espera_por_id(tenant_1, w1_id)
    assert w1.get("status") == "ativo", "F8-1: status deveria ser ativo"
    print("OK: F8-1: Criação OK")

    # =========================================================
    # F8-2: Buscar compatível
    # =========================================================
    print("[F8-2] Buscando entrada compatível...")
    await asyncio.sleep(0.01)
    w2_search = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_1,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=amanha,
        hora_desejada="10:00",
        duracao_minutos=30,
    )
    assert w2_search is not None, "F8-2: Não encontrou entrada"
    assert w2_search.get("cliente", {}).get("cliente_nome") == "João", "F8-2: nome diferente"
    print("OK: F8-2: Busca compatível OK")

    # =========================================================
    # F8-3: Marcar como notificado
    # =========================================================
    print("[F8-3] Marcando como notificado...")
    sucesso_3 = await marcar_como_notificado(tenant_1, w1_id)
    assert sucesso_3 is True, "F8-3: falhou ao marcar"
    w3 = await buscar_lista_espera_por_id(tenant_1, w1_id)
    assert w3.get("status") == "notificado", "F8-3: status deveria ser notificado"
    assert w3.get("auditoria", {}).get("tentativas_notificacao") == 1
    print("OK: F8-3: Marcar como notificado OK")

    # =========================================================
    # F8-4: Marcar como convertido
    # =========================================================
    print("[F8-4] Marcando como convertido...")
    sucesso_4 = await marcar_como_convertido(tenant_1, w1_id, "evento_123")
    assert sucesso_4 is True, "F8-4: falhou ao marcar"
    w4 = await buscar_lista_espera_por_id(tenant_1, w1_id)
    assert w4.get("status") == "convertido", "F8-4: status deveria ser convertido"
    assert w4.get("evento_criado_apos_encaixe") == "evento_123"
    print("OK: F8-4: Marcar como convertido OK")

    # =========================================================
    # F8-5: Marcar como cancelado
    # =========================================================
    print("[F8-5] Teste de recusa (marca como cancelado)...")
    tenant_5 = f"t_f85_{datetime.now().strftime('%H%M%S%f')}"
    cliente_5 = f"c_f85_{datetime.now().strftime('%H%M%S%f')}"

    r5 = await criar_lista_espera(
        tenant_id=tenant_5,
        actor_id=f"whatsapp:{cliente_5}",
        cliente_id=cliente_5,
        cliente_nome="Pedro",
        servico="barba",
        profissional_preferido="João",
        data_desejada=amanha,
        hora_desejada="15:00",
        duracao_minutos=20,
        evento_conflitante_id="evt_5",
    )
    w5_id = r5.get("waitlist_id")

    sucesso_5 = await marcar_como_cancelado(tenant_5, w5_id)
    assert sucesso_5 is True
    w5 = await buscar_lista_espera_por_id(tenant_5, w5_id)
    assert w5.get("status") == "cancelado"
    print("OK: F8-5: Marcar como cancelado OK")

    # =========================================================
    # F8-6: FIFO (prioridade)
    # =========================================================
    print("[F8-6] Teste FIFO (primeiro criado tem prioridade)...")
    tenant_6 = f"t_f86_{datetime.now().strftime('%H%M%S%f')}"
    cliente_6a = f"c_f86a_{datetime.now().strftime('%H%M%S%f')}"
    cliente_6b = f"c_f86b_{datetime.now().strftime('%H%M%S%f')}"
    data_6 = "2026-08-01"

    # Primeiro
    await criar_lista_espera(
        tenant_id=tenant_6,
        actor_id=f"whatsapp:{cliente_6a}",
        cliente_id=cliente_6a,
        cliente_nome="Ana",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_6,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_6a",
    )

    await asyncio.sleep(0.05)

    # Segundo
    await criar_lista_espera(
        tenant_id=tenant_6,
        actor_id=f"whatsapp:{cliente_6b}",
        cliente_id=cliente_6b,
        cliente_nome="Bruno",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_6,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_6b",
    )

    # Buscar: Ana deve ser primeiro
    w6_first = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_6,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_6,
        hora_desejada="10:00",
        duracao_minutos=30,
    )
    assert w6_first.get("cliente", {}).get("cliente_nome") == "Ana", "F8-6: Ana deveria ser primeiro"

    # Marcar Ana como notificado
    await marcar_como_notificado(tenant_6, w6_first.get("waitlist_id"))

    # Buscar novamente: Bruno deve ser próximo
    w6_second = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_6,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_6,
        hora_desejada="10:00",
        duracao_minutos=30,
    )
    assert w6_second.get("cliente", {}).get("cliente_nome") == "Bruno", "F8-6: Bruno deveria ser segundo"
    print("OK: F8-6: FIFO OK")

    # =========================================================
    # F8-7: Multi-tenant isolation
    # =========================================================
    print("[F8-7] Teste de isolamento multi-tenant...")
    tenant_7a = f"t_f87a_{datetime.now().strftime('%H%M%S%f')}"
    tenant_7b = f"t_f87b_{datetime.now().strftime('%H%M%S%f')}"
    cliente_7a = f"c_f87a_{datetime.now().strftime('%H%M%S%f')}"
    cliente_7b = f"c_f87b_{datetime.now().strftime('%H%M%S%f')}"
    data_7 = "2026-08-05"

    await criar_lista_espera(
        tenant_id=tenant_7a,
        actor_id=f"whatsapp:{cliente_7a}",
        cliente_id=cliente_7a,
        cliente_nome="Alice",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_7,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_7a",
    )

    await criar_lista_espera(
        tenant_id=tenant_7b,
        actor_id=f"whatsapp:{cliente_7b}",
        cliente_id=cliente_7b,
        cliente_nome="Bob",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_7,
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_7b",
    )

    # Buscar em A
    w7a = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_7a,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_7,
        hora_desejada="10:00",
        duracao_minutos=30,
    )
    assert w7a.get("cliente", {}).get("cliente_nome") == "Alice"

    # Buscar em B
    w7b = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_7b,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada=data_7,
        hora_desejada="10:00",
        duracao_minutos=30,
    )
    assert w7b.get("cliente", {}).get("cliente_nome") == "Bob"

    # Validar isolamento
    assert w7a.get("tenant_id") == tenant_7a
    assert w7b.get("tenant_id") == tenant_7b
    print("OK: F8-7: Isolamento multi-tenant OK")

    # =========================================================
    # F8-8: Duração (waitlist <= disponível)
    # =========================================================
    print("[F8-8] Teste de compatibilidade de duração...")
    tenant_8 = f"t_f88_{datetime.now().strftime('%H%M%S%f')}"
    cliente_8 = f"c_f88_{datetime.now().strftime('%H%M%S%f')}"

    await criar_lista_espera(
        tenant_id=tenant_8,
        actor_id=f"whatsapp:{cliente_8}",
        cliente_id=cliente_8,
        cliente_nome="Carol",
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-10",
        hora_desejada="10:00",
        duracao_minutos=30,
        evento_conflitante_id="evt_8",
    )

    # Vaga com 60 min: deveria encontrar
    w8_ok = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_8,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-10",
        hora_desejada="10:00",
        duracao_minutos=60,
    )
    assert w8_ok is not None, "F8-8: deveria encontrar com duracao maior"

    # Vaga com 20 min: não deveria encontrar
    w8_no = await buscar_proxima_lista_espera_compativel(
        tenant_id=tenant_8,
        servico="corte",
        profissional_preferido="Bruna",
        data_desejada="2026-08-10",
        hora_desejada="10:00",
        duracao_minutos=20,
    )
    assert w8_no is None, "F8-8: não deveria encontrar com duracao menor"
    print("OK: F8-8: Compatibilidade de duração OK")

    # =========================================================
    # RESULTADO FINAL
    # =========================================================
    print("\n" + "="*70)
    print("  OK: TODOS OS 8 CENÁRIOS PASSARAM!")
    print("="*70 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
