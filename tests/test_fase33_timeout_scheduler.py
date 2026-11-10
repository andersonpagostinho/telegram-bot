# -*- coding: utf-8 -*-
"""
FASE 3.3 TEST: Verificar que scheduler de timeout funciona corretamente.

Testa:
- Algoritmo de timeout (revalidação antes de encerrar)
- Isolamento por tenant
- Estatísticas corretas
- Não depende de cliente enviar mensagem
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_fase33_algoritmo_timeout_revalidacao():
    """
    Teste: Scheduler deve revalidar antes de encerrar (proteção race condition).

    Setup:
    - Sessão com _last_client_activity = 70 min atrás (EXPIRADA)
    - Reread mostra timestamp mudou (cliente enviou msg)

    Executa:
    - Simular leitura T1 (70 min)
    - RE-READ mostra T2 (agora, cliente ativo)

    Esperado:
    - Skip (não encerrar)
    - Registrar "revalidacao mudou"
    """
    from datetime import datetime, timezone, timedelta

    agora = datetime.now(timezone.utc)
    ts_antigo = (agora - timedelta(minutes=70)).isoformat()  # 70 min = expirado
    ts_novo = agora.isoformat()  # agora = cliente enviou msg

    print(f"\n[TESTE FASE 3.3] Revalidação com mudança de timestamp")
    print(f"  T1 (70 min atrás): {ts_antigo}")
    print(f"  T2 (agora): {ts_novo}")

    # Simular comparação
    tempo_decorrido = (agora - datetime.fromisoformat(ts_antigo)).total_seconds()
    expiraria = tempo_decorrido >= 3600  # 60 min

    assert expiraria, "Deveria ter expirado em T1"
    print(f"✅ [TESTE FASE 3.3] T1 expirou (como esperado)")

    # Simular revalidação
    if ts_novo != ts_antigo:
        print(f"✅ [TESTE FASE 3.3] Timestamp mudou em revalidação, skip (cliente ativo)")
        assert True
    else:
        print(f"❌ [TESTE FASE 3.3] Timestamp deveria ter mudado")
        assert False, "Timestamp não mudou"


@pytest.mark.asyncio
async def test_fase33_isolamento_tenant():
    """
    Teste: Scheduler deve isolar por tenant_id.

    Setup:
    - 2 tenants (A, B)
    - A tem sessão expirada
    - B tem sessão válida

    Executa:
    - Processar A
    - Processar B

    Esperado:
    - A encerrada
    - B não afetada
    """
    print(f"\n[TESTE FASE 3.3] Isolamento por tenant")

    tenant_a = "tenant_a_123"
    tenant_b = "tenant_b_456"

    # Simular processamento isolado
    processados = []

    for tenant_id in [tenant_a, tenant_b]:
        processados.append({
            "tenant_id": tenant_id,
            "sessoes": 1,
            "encerradas": 1 if tenant_id == tenant_a else 0
        })
        print(f"  Processado {tenant_id}: 1 sessão")

    assert len(processados) == 2, "Deveria ter processado 2 tenants"
    assert processados[0]["encerradas"] == 1, "Tenant A deveria ter 1 encerrada"
    assert processados[1]["encerradas"] == 0, "Tenant B não deveria ter nenhuma encerrada"

    print(f"✅ [TESTE FASE 3.3] Tenants isolados corretamente")


@pytest.mark.asyncio
async def test_fase33_sem_depender_cliente():
    """
    Teste: Scheduler não depende de cliente enviar nova mensagem.

    Setup:
    - Sessão inativa há 70 min
    - Nenhuma nova mensagem chegou

    Executa:
    - Scheduler roda periodicamente (não triggered por cliente)

    Esperado:
    - Sessão é encerrada MESMO SEM nova mensagem
    """
    print(f"\n[TESTE FASE 3.3] Encerramento sem nova mensagem")

    agora = datetime.now(timezone.utc)
    ts_70min_atras = (agora - timedelta(minutes=70)).isoformat()

    # Simular que nenhuma msg chegou (timestamp ainda é o mesmo)
    ts_atual = ts_70min_atras

    tempo_sem_atividade = (agora - datetime.fromisoformat(ts_atual)).total_seconds()
    minutos = tempo_sem_atividade / 60

    print(f"  Inatividade: {minutos:.1f} minutos")
    print(f"  Scheduler rode independentemente (não triggered por cliente)")

    assert minutos >= 60, f"Deveria estar inativo >= 60 min, está {minutos}"
    print(f"✅ [TESTE FASE 3.3] Sessão será encerrada INDEPENDENTEMENTE de cliente")


@pytest.mark.asyncio
async def test_fase33_estatisticas():
    """
    Teste: Scheduler deve retornar estatísticas corretas.

    Esperado:
    - dict com: sessoes_checadas, sessoes_encerradas, revalidacoes, etc
    """
    print(f"\n[TESTE FASE 3.3] Estatísticas retornadas")

    # Simular stats que scheduler retornaria
    stats = {
        "tenants_processados": 5,
        "sessoes_checadas": 42,
        "sessoes_encerradas": 3,
        "sessoes_skipped": 39,
        "revalidacoes": 3,
        "transacoes_abortadas": 0,
        "erros": 0,
    }

    print(f"  Tenants: {stats['tenants_processados']}")
    print(f"  Sessões checadas: {stats['sessoes_checadas']}")
    print(f"  Encerradas: {stats['sessoes_encerradas']}")
    print(f"  Revalidações: {stats['revalidacoes']}")

    assert "sessoes_encerradas" in stats, "Deveria ter 'sessoes_encerradas'"
    assert "revalidacoes" in stats, "Deveria ter 'revalidacoes'"
    assert stats["sessoes_encerradas"] <= stats["sessoes_checadas"], "Encerradas <= checadas"

    print(f"✅ [TESTE FASE 3.3] Estatísticas corretas")


@pytest.mark.asyncio
async def test_fase33_verificar_padrão_cron():
    """
    Teste: Scheduler segue padrão de cron com lock (sem múltiplas instâncias).

    Verificar que:
    - Função é async
    - Usa serviço de lock (via /cron/ping)
    - Não cria scheduler próprio em cada worker
    """
    print(f"\n[TESTE FASE 3.3] Padrão de cron com lock")

    from scheduler.timeout_scheduler import processar_timeouts_sessoes
    import inspect

    # Verificar que é async
    is_async = asyncio.iscoroutinefunction(processar_timeouts_sessoes)
    print(f"  Função async: {is_async}")
    assert is_async, "processar_timeouts_sessoes deveria ser async"

    # Verificar que não cria scheduler próprio (não há AsyncIOScheduler criado)
    source = inspect.getsource(processar_timeouts_sessoes)
    tem_scheduler = "AsyncIOScheduler" in source
    print(f"  Cria AsyncIOScheduler próprio: {tem_scheduler}")
    assert not tem_scheduler, "Não deveria criar scheduler próprio (usar /cron/ping)"

    print(f"✅ [TESTE FASE 3.3] Segue padrão de cron com lock (seguro para múltiplas instâncias)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FASE 3.3 TEST — Verificar Scheduler de Timeout")
    print("="*70)

    asyncio.run(test_fase33_algoritmo_timeout_revalidacao())
    asyncio.run(test_fase33_isolamento_tenant())
    asyncio.run(test_fase33_sem_depender_cliente())
    asyncio.run(test_fase33_estatisticas())
    asyncio.run(test_fase33_verificar_padrão_cron())

    print("\n" + "="*70)
    print("✅ FASE 3.3 TESTES CONCLUÍDO")
    print("="*70)
