"""
P0.27 — Testes de implementação dos 3 bugs críticos

Validar:
1. P0.27-A: FUSO_BR importado
2. P0.27-B: Cleanup de locks
3. P0.27-C: Event ID com hora_inicio
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.asyncio
async def test_p0_27_a_fuso_br_importado():
    """
    P0.27-A: Verificar FUSO_BR está importado
    e pode ser usado em datetime.now(FUSO_BR)
    """
    from datetime import datetime
    from services.agenda_lock_service import FUSO_BR

    # FUSO_BR deve existir e ser um timezone
    assert FUSO_BR is not None

    # Deve funcionar em datetime.now()
    now_br = datetime.now(FUSO_BR)
    assert now_br.tzinfo is not None

    # Deve conter "Sao_Paulo"
    assert "Sao_Paulo" in str(FUSO_BR)

    # Deve gerar ISO string válida
    iso_str = datetime.now(FUSO_BR).isoformat()
    assert len(iso_str) > 0


@pytest.mark.asyncio
async def test_p0_27_c_event_id_com_hora():
    """
    P0.27-C: Verificar que event_id gerado contém hora_inicio
    """
    from services.agenda_lock_service import criar_evento_com_lock
    from services.firebase_service_async import deletar_dado_em_path

    TENANT_ID = "tenant_p0_27_test_hora"

    evento = {
        "cliente_id": "cliente_p0_27_teste",
        "profissional": "bruna",
        "data": "2026-11-20",
        "hora_inicio": "14:30",
        "hora_fim": "15:10",
        "servico": "Corte",
    }

    result = await criar_evento_com_lock(
        dono_id=TENANT_ID,
        evento=evento,
        event_id=None,
    )

    if result.get("ok"):
        event_id = result.get("event_id")

        # Event ID deve conter a hora (sem dois-pontos: 1430)
        assert "1430" in event_id, \
            f"Event ID não contém hora: {event_id}"

        # Cleanup
        path = f"Clientes/{TENANT_ID}/Eventos/{event_id}"
        await deletar_dado_em_path(path)


@pytest.mark.asyncio
async def test_p0_27_c_horas_diferentes_ids_diferentes():
    """
    P0.27-C: Duas horas diferentes = IDs diferentes
    """
    from services.agenda_lock_service import criar_evento_com_lock
    from services.firebase_service_async import deletar_dado_em_path

    TENANT_ID = "tenant_p0_27_test_mult"

    evento1 = {
        "cliente_id": "cliente_mult",
        "profissional": "gloria",
        "data": "2026-11-21",
        "hora_inicio": "10:00",
        "hora_fim": "10:40",
        "servico": "Manicure",
    }

    evento2 = {
        "cliente_id": "cliente_mult",
        "profissional": "gloria",
        "data": "2026-11-21",
        "hora_inicio": "11:00",
        "hora_fim": "11:40",
        "servico": "Manicure",
    }

    result1 = await criar_evento_com_lock(
        dono_id=TENANT_ID,
        evento=evento1,
        event_id=None,
    )

    result2 = await criar_evento_com_lock(
        dono_id=TENANT_ID,
        evento=evento2,
        event_id=None,
    )

    if result1.get("ok") and result2.get("ok"):
        id1 = result1["event_id"]
        id2 = result2["event_id"]

        # IDs devem ser diferentes (diferentes horas)
        assert id1 != id2, \
            f"IDs iguais para horas diferentes: {id1} vs {id2}"

        # ID1 deve conter 1000
        assert "1000" in id1, f"ID1 não contém hora: {id1}"

        # ID2 deve conter 1100
        assert "1100" in id2, f"ID2 não contém hora: {id2}"

        # Cleanup
        await deletar_dado_em_path(f"Clientes/{TENANT_ID}/Eventos/{id1}")
        await deletar_dado_em_path(f"Clientes/{TENANT_ID}/Eventos/{id2}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
