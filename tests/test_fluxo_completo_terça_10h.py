"""
Teste E2E COMPLETO: Validar fluxo terça-feira + horário até o final

Reproduz exatamente:
1. User: "quero agendar para hoje" → rejeita (domingo)
2. User: "marque para terça-feira" → pede horário
3. User: "as 10 horas" → VALIDA que usa TERÇA (não hoje) com horário 10:00

Este teste pega o bug que o teste anterior não pegava porque
continua até a terceira mensagem (incremento de horário).
"""

import pytest
import asyncio
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


@pytest.mark.asyncio
async def test_fluxo_completo_terça_sem_hora_depois_horário():
    """
    Fluxo completo com 3 mensagens:
    1. "hoje" → rejeita (domingo)
    2. "terça" → pede horário (aguardando_horario, data=2026-10-20)
    3. "as 10 horas" → DEVE usar data_hora=2026-10-20 (não 2026-10-18)
    """
    tenant_id = "7394370553"
    actor_id = "whatsapp:5511991382080"

    # ========================================
    # MENSAGEM 1: Rejeita domingo
    # ========================================
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
        mensagem="quero agendar um corte para hoje",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )
    assert "fechado" in resultado1.get("resposta", "").lower()
    print("[MSG1] ✅ Domingo rejeitado")

    # ========================================
    # MENSAGEM 2: Terça sem hora → pede horário
    # ========================================
    resultado2 = await roteador_principal(
        user_id=actor_id,
        mensagem="verdade, marque para terça-feira entao",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )
    assert "horário" in resultado2.get("resposta", "").lower()
    print("[MSG2] ✅ Terça reconhecida, pedindo horário")

    # Validar estado intermediário
    sessao2 = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )
    assert sessao2.get("estado_fluxo") == "aguardando_horario"
    assert sessao2.get("data_hora") == "2026-10-20T00:00:00"  # ← Terça sem hora
    print(f"[MSG2] ✅ Estado: {sessao2.get('estado_fluxo')}, data_hora: {sessao2.get('data_hora')}")

    # ========================================
    # MENSAGEM 3: CRÍTICA - "as 10 horas"
    # Deve usar data_hora=2026-10-20, NÃO data=2026-10-18
    # ========================================
    resultado3 = await roteador_principal(
        user_id=actor_id,
        mensagem="as 10 horas",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta3 = resultado3.get("resposta", "").lower()
    print(f"[MSG3] Resposta: {resposta3[:100]}...")

    # ✅ VALIDAÇÕES CRÍTICAS
    # 1. NÃO deve rejeitar por "fechado" (que aconteceria se usasse 2026-10-18)
    assert "fechado" not in resposta3, \
        f"Deveria usar terça (aberto), não hoje (fechado). Resposta: {resposta3[:200]}"

    # 2. Validar estado final em Firestore
    sessao3 = await buscar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    )

    data_hora_final = sessao3.get("data_hora")
    print(f"[MSG3] data_hora final: {data_hora_final}")

    assert data_hora_final == "2026-10-20T10:00:00", \
        f"data_hora deveria ser 2026-10-20T10:00:00 (terça 10h), mas é {data_hora_final}"

    # 3. Estado deve estar pronto para profissional ou confirmação
    assert sessao3.get("estado_fluxo") in ["aguardando_profissional", "confirmacao_pendente", "agendando"], \
        f"Estado final deveria estar pronto para próximo passo, mas é {sessao3.get('estado_fluxo')}"

    print("✅✅✅ FLUXO COMPLETO PASSOU: terça + 10h usa data correta")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
