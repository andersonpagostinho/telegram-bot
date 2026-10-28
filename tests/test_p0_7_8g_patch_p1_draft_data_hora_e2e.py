"""
P0.7.8G — Testes E2E com Firestore Real

Incidente real em 27/10/2026:
- Cliente: Pergunta sobre manicure após Gloria ser rejeitada
- draft_agendamento.data_hora = "2026-10-28T10:00:00"
- ctx.data_hora = None (segunda mensagem sem data nova)
- Bruna ocupada às 10h
- Esperado: Bruna NÃO oferecida

Regra de Ouro: Todos os testes validam até Firestore real.
"""

import pytest
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from datetime import datetime
import uuid


@pytest.mark.asyncio
async def test_t1_e2e_patch_p1_bruna_ocupada_nao_oferecida():
    """
    T1 E2E: Bruna ocupada às 10h não é oferecida quando cliente pergunta
    "tem outra que faz manicure?" (segunda mensagem, sem data/hora nova)

    Setup:
    - Tenant: 7394370553
    - Profissionais: Bruna (manicure/pedicure), Gloria (corte/escova)
    - Evento: Bruna ocupada em 2026-10-28 10:00-10:30 (manicure)
    - Contexto: draft_agendamento.data_hora = "2026-10-28T10:00:00"
    """
    tenant_id = "7394370553"
    wa_id = "5511999999999"  # ID fixo para teste (menos variável)
    actor_canonico = f"whatsapp:{wa_id}"

    # SETUP 1: Criar contexto com draft herdado
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "aguardando_profissional",
        "motivo_estado": "profissional_nao_atende_servico",
        "servico": "manicure",
        "profissional_rejeitado": "Gloria",
        "profissionais_validos": ["Bruna"],
        "data_hora": None,  # ← SEM data_hora em ctx
        "aguardando_confirmacao_agendamento": False,  # EXPLICITAR
        "draft_agendamento": {
            "data_hora": "2026-10-28T10:00:00",  # ← Horário herdado no draft
            "servico": "manicure",
            "profissional": None,
            "modo_prechecagem": True
        }
    }

    # Salvar em AMBOS os caminhos que o roteador procura:
    # 1. Path novo (com tenant_id)
    path1 = f"Clientes/{tenant_id}/Sessoes/{actor_canonico}"
    await atualizar_dado_em_path(path=path1, dados=ctx_inicial)
    print(f"\n[DEBUG-SETUP] Contexto salvo em: {path1}")

    # 2. Path legado (compatibilidade)
    path2 = f"Clientes/{wa_id}/MemoriaTemporaria/contexto"
    await atualizar_dado_em_path(path=path2, dados=ctx_inicial)
    print(f"[DEBUG-SETUP] Contexto salvo em: {path2}")

    # 3. Verificar se foi salvo
    verificado = await buscar_dado_em_path(path=path1)
    print(f"[DEBUG-SETUP] Verificação leitura path1: {bool(verificado)} | motivo_estado={verificado.get('motivo_estado') if verificado else None}")

    # SETUP 2: Criar evento real de Bruna ocupada em 28/10/2026 10:00-10:30
    evento_bruna_ocupada = {
        "id": "evt_bruna_manicure_10h",
        "profissional": "bruna",
        "data": "2026-10-28",
        "hora_inicio": "10:00",
        "hora_fim": "10:30",
        "duracao_minutos": 30,
        "status": "confirmado",
        "servico": "manicure",
        "cliente_wa_id": "5511987654321",
        "timestamp_criacao": datetime.now().isoformat()
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Eventos/evt_bruna_manicure_10h",
        dados=evento_bruna_ocupada
    )

    # EXECUTE: Chamar roteador com segunda mensagem
    print(f"\n[DEBUG-EXECUTE] Chamando roteador_principal com:")
    print(f"  user_id={wa_id}")
    print(f"  tenant_id={tenant_id}")
    print(f"  actor_canonico={actor_canonico}")
    print(f"  mensagem='tem outra que faz manicure?'")

    resultado = await roteador_principal(
        user_id=wa_id,  # SEM prefixo
        mensagem="mas a gloria nao faz manicure. tem outra que faz manicure?",
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    print(f"\n[DEBUG-RESULT] resultado['resposta'][:200] = {resultado.get('resposta', '')[:200]}")

    # VALIDAR
    resposta = resultado.get("resposta", "").lower()
    print(f"\n[T1 E2E] Resposta: {resposta[:200]}")

    # Bruna ocupada → resposta deve indicar indisponibilidade
    # "Os profissionais que fazem manicure estão ocupados nesse horário"
    assert "ocupado" in resposta or "ocupadas" in resposta or "outro horário" in resposta, \
        f"Resposta deveria indicar que Bruna está ocupada. Recebeu: {resposta}"

    # Não deve oferecer Bruna como disponível
    assert "bruna" not in resposta or "não" in resposta or "ocupad" in resposta, \
        f"Bruna não deveria ser oferecida como disponível. Recebeu: {resposta}"

    # Verificar estado da sessão após (path legado)
    sessao_pos = await buscar_dado_em_path(
        path=f"Clientes/{wa_id}/MemoriaTemporaria/contexto"
    )

    # Estado deve permanecer "aguardando_profissional"
    assert sessao_pos.get("estado_fluxo") == "aguardando_profissional", \
        f"Estado deveria manter 'aguardando_profissional', mas é {sessao_pos.get('estado_fluxo')}"

    # draft_agendamento.data_hora deve ser preservado
    draft = sessao_pos.get("draft_agendamento") or {}
    assert draft.get("data_hora") == "2026-10-28T10:00:00", \
        f"data_hora no draft deveria ser preservado, mas é {draft.get('data_hora')}"

    print("✅ T1 E2E PASS: Bruna ocupada não oferecida (Firestore real)")


@pytest.mark.asyncio
async def test_t2_e2e_bruna_livre_oferecida():
    """
    T2 E2E: Bruna LIVRE às 11h É oferecida como alternativa
    (contraste positivo para T1)
    """
    tenant_id = "7394370553"
    wa_id = "5511988888888"  # ID fixo diferente de T1
    actor_canonico = f"whatsapp:{wa_id}"

    # SETUP: Contexto com draft herdado (SEM evento ocupado para Carla)
    ctx_inicial = {
        "tipo_usuario": "cliente",
        "estado_fluxo": "aguardando_profissional",
        "motivo_estado": "profissional_nao_atende_servico",
        "servico": "manicure",
        "profissional_rejeitado": "Gloria",
        "profissionais_validos": ["Carla"],  # Usar Carla para evitar conflito T1/T2
        "data_hora": None,
        "aguardando_confirmacao_agendamento": False,
        "draft_agendamento": {
            "data_hora": "2026-10-28T14:00:00",  # Horário bem diferente
            "servico": "manicure",
            "profissional": None
        }
    }

    await atualizar_dado_em_path(
        path=f"Clientes/{tenant_id}/Sessoes/{actor_canonico}",
        dados=ctx_inicial
    )
    await atualizar_dado_em_path(
        path=f"Clientes/{wa_id}/MemoriaTemporaria/contexto",
        dados=ctx_inicial
    )

    # Nenhum evento para Bruna às 11h (fica livre)

    # EXECUTE
    resultado = await roteador_principal(
        user_id=wa_id,  # SEM prefixo
        mensagem="mas a gloria nao faz manicure. tem outra que faz manicure?",  # Mesmo padrão de T1
        tenant_id=tenant_id,
        phone_number_id="1350170954840548"
    )

    resposta = resultado.get("resposta", "").lower()
    print(f"\n[T2 E2E] Resposta (T2): {resposta[:200]}")

    # Carla livre → deve oferecer
    assert "carla" in resposta and ("verificar" in resposta or "posso" in resposta), \
        f"Resposta deveria oferecer Carla. Recebeu: {resposta}"

    # Não deve indicar ocupação
    assert "ocupado" not in resposta and "ocupadas" not in resposta, \
        f"Não deveria indicar ocupação. Recebeu: {resposta}"

    print("✅ T2 E2E PASS: Carla livre oferecida (Firestore real)")


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
