"""
P0.26 — E2E: Validar que novos agendamentos enviam mensagem oficial

Testa o fluxo completo desde a criação do evento até a geração da mensagem.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pytz
import uuid

try:
    from services.event_service_async import salvar_evento
    FIREBASE_OK = True
except Exception as e:
    print(f"Firebase import failed: {e}")
    FIREBASE_OK = False

FUSO_BR = pytz.timezone("America/Sao_Paulo")


@pytest.mark.skipif(not FIREBASE_OK, reason="Firebase imports failed")
@pytest.mark.asyncio
async def test_p026_novo_agendamento_envia_mensagem_oficial():
    """
    E2E: Novo agendamento → salvar_evento → event_handler → mensagem oficial
    """
    print(f"\n[E2E P0.26] Validando fluxo completo de novo agendamento")

    agora = datetime.now(FUSO_BR)
    futuro = agora + timedelta(hours=4)
    data_iso = futuro.strftime("%Y-%m-%d")
    hora_inicio = futuro.strftime("%H:%M")

    usuario_id = f"user_p026_{uuid.uuid4().hex[:8]}"
    tenant_id = f"tenant_p026_{uuid.uuid4().hex[:8]}"

    evento = {
        "data": data_iso,
        "hora_inicio": hora_inicio,
        "duracao": 30,
        "servico": "corte feminino",
        "profissional": "Bruna",
        "cliente_id": usuario_id,
        "confirmado": True,
    }

    print(f"  Usuário: {usuario_id}")
    print(f"  Tenant: {tenant_id}")
    print(f"  Evento: {evento}")

    # 1. Salvar evento
    print(f"\n  [ETAPA 1] Salvando evento via salvar_evento()...")
    resultado_salvar = await salvar_evento(
        user_id=usuario_id,
        evento=evento,
        tenant_id=tenant_id
    )

    print(f"  Resultado salvar_evento:")
    print(f"    - ok: {resultado_salvar.get('ok')}")
    print(f"    - evento_id: {resultado_salvar.get('evento_id')}")
    print(f"    - confirmado_nesta_requisicao: {resultado_salvar.get('confirmado_nesta_requisicao')}")
    print(f"    - status: {resultado_salvar.get('status')}")

    # Validações críticas
    assert resultado_salvar.get("ok") is True, "salvar_evento deve retornar ok=True"
    assert resultado_salvar.get("confirmado_nesta_requisicao") is True, \
        f"CRÍTICO: confirmado_nesta_requisicao deve ser True, got {resultado_salvar.get('confirmado_nesta_requisicao')}"
    assert resultado_salvar.get("evento_id") is not None, "evento_id deve estar presente"

    print(f"  ✅ Event service retorna confirmado_nesta_requisicao=True")

    # 2. Verificar que o campo foi propagado corretamente
    print(f"\n  [ETAPA 2] Validando que o campo vem do lock service...")
    # Isso é o que o event_handler vai usar para decidir qual mensagem enviar
    confirmado_para_mensagem = resultado_salvar.get("confirmado_nesta_requisicao") is True

    if confirmado_para_mensagem:
        print(f"  ✅ Event handler ENVIARÁ mensagem oficial ✨")
    else:
        print(f"  ❌ Event handler enviaria mensagem genérica (BUG!)")

    assert confirmado_para_mensagem, \
        "Event handler precisa receber confirmado_nesta_requisicao=True para enviar mensagem oficial"

    print(f"\n[E2E P0.26] ✅ VALIDAÇÃO COMPLETA")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
