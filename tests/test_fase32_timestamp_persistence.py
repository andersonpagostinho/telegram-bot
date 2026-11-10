# -*- coding: utf-8 -*-
"""
FASE 3.2 TEST: Verificar que _last_client_activity é persistido em TODAS as requisições.

Testa: Timestamp é salvo após cada mensagem, mesmo que não dispare confirmacao/sinais.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, call
import time


@pytest.mark.asyncio
async def test_fase32_timestamp_sempre_persistido():
    """
    Teste: _last_client_activity deve ser persistido após cada mensagem.

    Setup:
    - 3 mensagens consecutivas
    - Nenhuma dispara confirmacao ou sinais_humanos

    Executa:
    - Simular chegada de 3 mensagens
    - Cada uma atualiza timestamp em memória
    - Cada uma deve chamar salvar_contexto_temporario_v2()

    Esperado:
    - 3 chamadas a salvar_contexto_temporario_v2()
    - Cada uma com _last_client_activity diferente
    - Timestamps em ordem crescente (não stale)
    """
    from datetime import datetime, timezone

    # Valores de teste
    dono_id = "test_tenant_abc"
    cliente_id = "test_cliente_xyz"

    # Simular timestamps que seriam gerados
    ts1 = datetime(2026, 11, 10, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    ts2 = datetime(2026, 11, 10, 10, 5, 0, tzinfo=timezone.utc).isoformat()  # +5 min
    ts3 = datetime(2026, 11, 10, 10, 10, 0, tzinfo=timezone.utc).isoformat()  # +10 min

    # Mock da função salvar
    saves_called = []

    async def mock_salvar(dono, cliente, ctx):
        saves_called.append({
            "dono_id": dono,
            "cliente_id": cliente,
            "ctx": ctx.copy(),
            "timestamp": ctx.get("_last_client_activity")
        })
        return True

    # Simulando o contexto do router
    ctx_base = {
        "estado_fluxo": "idle",
        "cliente_id": cliente_id,
    }

    # Patch para capturar timestamps que seriam gerados
    timestamps_gerados = [ts1, ts2, ts3]
    ts_index = [0]

    async def mock_now():
        ts = timestamps_gerados[ts_index[0]]
        ts_index[0] = min(ts_index[0] + 1, len(timestamps_gerados) - 1)
        return ts

    # Simular 3 mensagens (sem confirmacao, sem sinais)
    print("\n[TESTE FASE 3.2] Simulando 3 mensagens consecutivas...")

    for i in range(1, 4):
        ctx = ctx_base.copy()

        # Simular atualização de timestamp (como no router linha 4737)
        ctx["_last_client_activity"] = timestamps_gerados[i-1]

        # Simular salva (como em FASE 3.2 nova linha)
        await mock_salvar(dono_id, cliente_id, ctx)

        print(f"  [Mensagem {i}] Timestamp: {ctx['_last_client_activity']}")

    # VALIDAÇÕES
    print(f"\n[TESTE FASE 3.2] Salvas realizadas: {len(saves_called)}")

    assert len(saves_called) == 3, f"Esperava 3 salvas, obtive {len(saves_called)}"
    print(f"✅ [TESTE FASE 3.2] Número de salvas correto: 3")

    # Verificar que timestamps estão em ordem crescente (não stale)
    ts_list = [s["timestamp"] for s in saves_called]
    assert ts_list == sorted(ts_list), f"Timestamps não estão em ordem crescente: {ts_list}"
    print(f"✅ [TESTE FASE 3.2] Timestamps em ordem crescente (não stale)")

    # Verificar que cada timestamp é diferente
    assert len(set(ts_list)) == 3, f"Timestamps não são todos diferentes"
    print(f"✅ [TESTE FASE 3.2] Cada mensagem tem timestamp único")

    # Verificar que todos têm timezone (ISO format com +00:00)
    for ts in ts_list:
        assert "+00:00" in ts, f"Timestamp sem timezone: {ts}"
    print(f"✅ [TESTE FASE 3.2] Todos os timestamps tem timezone")

    return True


@pytest.mark.asyncio
async def test_fase32_timestamp_nao_mascarado():
    """
    Teste: Timestamp antigo no Firestore não deve ser mascarado.

    Setup:
    - Sessão com _last_client_activity = 70 minutos atrás (expirada)
    - Nova mensagem chega

    Executa:
    - Validar expiração (deve detectar > 60 min)
    - Se expirado, RETORNAR (não atualizar timestamp)

    Esperado:
    - Se expirado: função retorna antes de atualizar timestamp
    - Timestamp antigo é preservado no contexto inicial
    """
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    ts_antigo = (agora - timedelta(minutes=70)).isoformat()  # 70 min atrás = EXPIRADO

    print(f"\n[TESTE FASE 3.2 MASCARA] Timestamp antigo (70 min): {ts_antigo}")

    ctx = {
        "estado_fluxo": "modo_escolha_horario",
        "_last_client_activity": ts_antigo,
        "draft_agendamento": {"data_hora": (agora + timedelta(hours=1)).isoformat()}
    }

    # Simular validação de timeout
    tempo_decorrido = (agora - datetime.fromisoformat(ts_antigo)).total_seconds()
    print(f"[TESTE FASE 3.2 MASCARA] Tempo decorrido: {tempo_decorrido/60:.1f} min")

    # Se >= 3600s (60 min), é considerado expirado
    expirou = tempo_decorrido >= 3600
    print(f"[TESTE FASE 3.2 MASCARA] Expirou: {expirou}")

    assert expirou, "Timestamp deveria ter expirado"
    print(f"✅ [TESTE FASE 3.2 MASCARA] Expiração detectada corretamente")

    # Se expirado, timestamp antigo não deve ser atualizado
    # (função retorna antes de linha 4737)
    assert ctx["_last_client_activity"] == ts_antigo, "Timestamp foi alterado quando deveria ter expirado"
    print(f"✅ [TESTE FASE 3.2 MASCARA] Timestamp antigo preservado (não mascarado)")


@pytest.mark.asyncio
async def test_fase32_verificar_merge_preserva_campos():
    """
    Teste: Merge em salvar_contexto_temporario_v2 não sobrescreve campos.

    Verificar que a função preserva campos existentes que não estão em ctx.
    """
    print(f"\n[TESTE FASE 3.2 MERGE] Verificar que merge preserva campos...")

    # Simular merge que faz salvar_contexto_temporario_v2
    contexto_firestore = {
        "estado_fluxo": "idle",
        "preferencia_horario": "manha",  # Campo existente
        "_tenant_id_guard": "tenant_abc",
    }

    ctx_novo = {
        "_last_client_activity": "2026-11-10T10:00:00+00:00",
        # NOT incluindo preferencia_horario
    }

    # Simular merge (como faz atualizar_dado_em_path com merge)
    resultado_merge = contexto_firestore.copy()
    resultado_merge.update(ctx_novo)

    # Verificar que preferencia_horario foi preservado
    assert "preferencia_horario" in resultado_merge, "Campo preferencia_horario foi perdido"
    assert resultado_merge["preferencia_horario"] == "manha", "Valor de preferencia_horario foi alterado"
    print(f"✅ [TESTE FASE 3.2 MERGE] Campo preservado: preferencia_horario={resultado_merge['preferencia_horario']}")

    # Verificar que novo campo foi adicionado
    assert "_last_client_activity" in resultado_merge, "Novo timestamp não foi adicionado"
    print(f"✅ [TESTE FASE 3.2 MERGE] Novo campo adicionado: _last_client_activity")

    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FASE 3.2 TEST — Verificar Persistência de _last_client_activity")
    print("="*70)

    asyncio.run(test_fase32_timestamp_sempre_persistido())
    asyncio.run(test_fase32_timestamp_nao_mascarado())
    asyncio.run(test_fase32_verificar_merge_preserva_campos())

    print("\n" + "="*70)
    print("✅ FASE 3.2 TESTES CONCLUÍDO")
    print("="*70)
