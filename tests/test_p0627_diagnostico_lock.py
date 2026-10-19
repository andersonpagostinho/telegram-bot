"""
DIAGNÓSTICO P0.6.2.7 — Entender fluxo de lock atomicamente seguro.

Executar UMA requisição (não concorrência) para validar:
1. Lock é criado
2. Evento é criado
3. Estado final correto
"""

import pytest
import uuid
from datetime import datetime
from pytz import timezone

from services.agenda_lock_service import criar_evento_com_lock
from services.firebase_service_async import salvar_dado_em_path
from firebase_admin import firestore

FUSO_BR = timezone("America/Sao_Paulo")

@pytest.mark.asyncio
async def test_diagnostico_uma_requisicao_simples():
    """Uma único requisição, nenhuma concorrência. Deve funcionar 100%."""

    tenant_id = f"test_diag_{uuid.uuid4().hex[:8]}"
    dono_id = tenant_id

    # Setup mínimo
    db = firestore.client()
    config = {
        "nome": "Teste Diagnóstico",
        "email": "diag@test.local"
    }
    await salvar_dado_em_path(f"Clientes/{tenant_id}/Configuracao", config)

    # Evento
    data_evento = datetime.now(FUSO_BR).date().isoformat()
    evento = {
        "cliente_id": "cliente_test",
        "profissional": "Bruna",
        "data": data_evento,
        "hora_inicio": "10:00",
        "hora_fim": "11:00",
        "servico": "manicure",
        "duracao_minutos": 60,
        "confirmado": True,
        "status": "confirmado",
        "id": f"evento_test_{uuid.uuid4().hex[:4]}"
    }

    print(f"\n[DIAG] Criando evento: {evento['id']}")
    print(f"       Profissional: {evento['profissional']}, {evento['data']} {evento['hora_inicio']}-{evento['hora_fim']}")

    resultado = await criar_evento_com_lock(dono_id, evento, evento["id"])

    print(f"\n[RESULTADO]")
    print(f"  ok={resultado.get('ok')}")
    print(f"  motivo={resultado.get('motivo')}")
    print(f"  tipo_erro={resultado.get('tipo_erro')}")
    print(f"  evento_id={resultado.get('evento_id')}")

    if resultado.get("ok"):
        # Verificar locks
        locks = list(db.collection("Clientes").document(tenant_id).collection("AgendaLocks").stream())
        print(f"\n[LOCKS] {len(locks)} locks criados:")
        for lock in locks:
            lock_data = lock.to_dict()
            print(f"  - {lock.id}: status={lock_data.get('status')}")

        # Verificar eventos
        eventos = list(db.collection("Clientes").document(tenant_id).collection("Eventos").stream())
        print(f"\n[EVENTOS] {len(eventos)} eventos criados:")
        for ev in eventos:
            ev_data = ev.to_dict()
            print(f"  - {ev.id}: {ev_data.get('profissional')} {ev_data.get('data')} {ev_data.get('hora_inicio')}")
    else:
        print(f"\n[ERRO] Falha ao criar evento: {resultado.get('motivo')}")

    # Cleanup
    try:
        events_ref = db.collection("Clientes").document(tenant_id).collection("Eventos")
        for doc in events_ref.stream():
            doc.reference.delete()
        locks_ref = db.collection("Clientes").document(tenant_id).collection("AgendaLocks")
        for doc in locks_ref.stream():
            doc.reference.delete()
        db.collection("Clientes").document(tenant_id).delete()
    except:
        pass

    assert resultado.get("ok"), f"Falha: {resultado.get('motivo')}"
    print(f"\n✅ TESTE PASSOU")

if __name__ == "__main__":
    pytest.main([__file__, "-vvs"])
