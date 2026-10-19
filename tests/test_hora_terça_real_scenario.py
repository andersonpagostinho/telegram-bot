"""
Teste: Reproduzir cenário real do usuário
1. Primeiro: rejeitar "hoje" (domingo)
2. Segundo: "terça-feira" sem hora — deve pedir horário (NÃO 09:00)
"""

import pytest
import asyncio
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


@pytest.mark.asyncio
async def test_rejeicao_hoje_depois_terça_sem_hora():
    """
    Reproduz exatamente:
    1. User: "quero agendar para hoje" → rejeita (domingo fechado)
    2. User: "marque para terça" → deve pedir HORÁRIO, não assume 09:00
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # ======================================
    # PRIMEIRA MENSAGEM: "hoje" (domingo)
    # ======================================
    ctx1 = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "idle",
        "draft_agendamento": None,
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
        dados=ctx1
    )

    resultado1 = await roteador_principal(
        user_id=actor_id,
        mensagem="quero agendar um corte para hoje",  # 18/10 = domingo
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    print(f"\n[RESPOSTA 1] {resultado1.get('resposta', '')[:100]}...")
    assert "fechado" in resultado1.get("resposta", "").lower(), "Deveria rejeitar domingo"

    # ======================================
    # SEGUNDA MENSAGEM: "terça-feira"
    # Estado AGORA é aguardando_data
    # ======================================
    resultado2 = await roteador_principal(
        user_id=actor_id,
        mensagem="verdade, marque para terça feira entao por favor",  # 20/10 = terça
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta2 = resultado2.get("resposta", "").lower()
    print(f"[RESPOSTA 2] {resposta2[:150]}...")

    # ========== VALIDAÇÕES ==========
    # Deve pedir horário, NÃO deve pedir profissional
    assert "horário" in resposta2 or "que horas" in resposta2, \
        f"Deveria pedir HORÁRIO para terça sem hora. Recebeu: {resposta2[:200]}"

    assert "profissional" not in resposta2, \
        f"NÃO deveria pedir profissional (falta hora). Recebeu: {resposta2[:200]}"

    # Verificar estado em Firestore
    sessao_pos = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    assert sessao_pos.get("estado_fluxo") == "aguardando_horario", \
        f"Estado deveria ser 'aguardando_horario', mas é {sessao_pos.get('estado_fluxo')}"

    assert sessao_pos.get("data_sem_hora") == True, \
        f"data_sem_hora deveria ser True"

    assert sessao_pos.get("hora_confirmada") == False, \
        f"hora_confirmada deveria ser False"

    print("✅ TESTE PASSOU: Terça-feira sem hora pede horário corretamente")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
