"""
Teste de Dashboard com dados REAIS do Firestore

Objetivo:
1. Criar dados de teste conhecidos em um tenant
2. Executar métricas do dashboard
3. Validar contra valores esperados
4. Garantir isolamento multi-tenant
5. Limpar dados de teste após validação
"""

import asyncio
import sys
from datetime import datetime, timedelta, date
from pytz import timezone

# Importar serviços
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_subcolecao,
    deletar_dado_em_path,
    obter_id_dono,
)
from services.dashboard_service import (
    obter_resumo_hoje,
    obter_resumo_semana,
    obter_metricas_profissionais,
    obter_metricas_clientes,
    obter_metricas_servicos,
    obter_alertas_operacionais,
    obter_dashboard_completo,
)

FUSO_BR = timezone("America/Sao_Paulo")

# Tenant de teste (use um ID que você controla)
TENANT_TEST = "tenant_f9_teste_001"

# Dados de teste que vamos criar
HOJE = datetime.now(FUSO_BR)
ONTEM = HOJE - timedelta(days=1)
SEMANA_ATRÁS = HOJE - timedelta(days=7)

print(f"[TEST] Data base: {HOJE.date().isoformat()}")
print(f"[TEST] Ontem: {ONTEM.date().isoformat()}")
print(f"[TEST] Semana atrás: {SEMANA_ATRÁS.date().isoformat()}")


async def criar_evento_teste(tenant_id: str, evento_id: str, evento_data: dict) -> bool:
    """Cria um evento de teste no Firestore."""
    path = f"Clientes/{tenant_id}/Eventos/{evento_id}"
    try:
        await salvar_dado_em_path(path, evento_data)
        print(f"[OK] Evento criado: {evento_id}")
        return True
    except Exception as e:
        print(f"[ERR] Erro ao criar evento {evento_id}: {e}")
        return False


async def limpar_eventos_teste(tenant_id: str) -> bool:
    """Remove todos os eventos de teste."""
    try:
        eventos = await buscar_subcolecao(f"Clientes/{tenant_id}/Eventos") or {}

        for evt_id in eventos.keys():
            path = f"Clientes/{tenant_id}/Eventos/{evt_id}"
            await deletar_dado_em_path(path)

        print(f"[OK] Limpeza concluída ({len(eventos)} eventos removidos)")
        return True
    except Exception as e:
        print(f"[ERR] Erro ao limpar: {e}")
        return False


async def criar_dados_teste():
    """Cria um conjunto de dados conhecidos para teste."""
    print("\n" + "=" * 80)
    print("CRIANDO DADOS DE TESTE NO FIRESTORE")
    print("=" * 80)

    # Limpar primeiro
    await limpar_eventos_teste(TENANT_TEST)

    hoje_iso = HOJE.date().isoformat()
    ontem_iso = ONTEM.date().isoformat()
    semana_atrás_iso = SEMANA_ATRÁS.date().isoformat()

    eventos_teste = [
        # [OK] HOJE: 2 confirmados, 1 cancelado = 3 eventos
        {
            "id": "evt_hoje_001",
            "data": {
                "descricao": "Corte de cabelo - Maria",
                "data": hoje_iso,
                "hora_inicio": "09:00",
                "hora_fim": "09:30",
                "duracao": 30,
                "confirmado": True,
                "status": "confirmado",
                "link": "",
                "cliente_id": "cli_001",
                "cliente_nome": "Maria Silva",
                "profissional": "Carla",
            }
        },
        {
            "id": "evt_hoje_002",
            "data": {
                "descricao": "Escova - Ana",
                "data": hoje_iso,
                "hora_inicio": "14:00",
                "hora_fim": "14:30",
                "duracao": 30,
                "confirmado": True,
                "status": "confirmado",
                "link": "",
                "cliente_id": "cli_002",
                "cliente_nome": "Ana Costa",
                "profissional": "Bruna",
            }
        },
        {
            "id": "evt_hoje_003",
            "data": {
                "descricao": "Manicure - João (CANCELADO)",
                "data": hoje_iso,
                "hora_inicio": "10:00",
                "hora_fim": "10:30",
                "duracao": 30,
                "confirmado": False,
                "status": "cancelado",
                "link": "",
                "cliente_id": "cli_003",
                "cliente_nome": "João",
                "profissional": "Carla",
            }
        },
        # ONTEM: 1 concluído (para histórico)
        {
            "id": "evt_ontem_001",
            "data": {
                "descricao": "Corte - Pedro",
                "data": ontem_iso,
                "hora_inicio": "11:00",
                "hora_fim": "11:30",
                "duracao": 30,
                "confirmado": True,
                "status": "concluido",
                "link": "",
                "cliente_id": "cli_004",
                "cliente_nome": "Pedro",
                "profissional": "Carla",
            }
        },
        # SEMANA ANTERIOR: 2 eventos (para teste de período)
        {
            "id": "evt_semana_001",
            "data": {
                "descricao": "Escova - Paula",
                "data": semana_atrás_iso,
                "hora_inicio": "09:00",
                "hora_fim": "09:30",
                "duracao": 30,
                "confirmado": True,
                "status": "concluido",
                "link": "",
                "cliente_id": "cli_005",
                "cliente_nome": "Paula",
                "profissional": "Bruna",
            }
        },
    ]

    # Criar todos os eventos
    for evento in eventos_teste:
        await criar_evento_teste(TENANT_TEST, evento["id"], evento["data"])

    print(f"\n[OK] {len(eventos_teste)} eventos criados com sucesso")
    return len(eventos_teste)


async def validar_resumo_hoje():
    """Valida resumo de hoje."""
    print("\n" + "=" * 80)
    print("TESTE 1: RESUMO DE HOJE")
    print("=" * 80)

    resumo = await obter_resumo_hoje(TENANT_TEST)

    print(f"Total agendamentos: {resumo.agendamentos_total}")
    print(f"  Confirmados: {resumo.agendamentos_confirmados}")
    print(f"  Cancelados: {resumo.agendamentos_cancelados}")
    print(f"  Concluídos: {resumo.agendamentos_concluidos}")
    print(f"Taxa ocupação: {resumo.taxa_ocupacao:.1f}%")
    print(f"Taxa cancelamento: {resumo.taxa_cancelamento:.1f}%")
    print(f"Encaixes: {resumo.encaixes_convertidos}")
    print(f"Fila ativa: {resumo.fila_espera_ativa}")

    # Validar
    assert resumo.agendamentos_total == 3, f"Esperava 3, got {resumo.agendamentos_total}"
    assert resumo.agendamentos_confirmados == 2, f"Esperava 2 confirmados, got {resumo.agendamentos_confirmados}"
    assert resumo.agendamentos_cancelados == 1, f"Esperava 1 cancelado, got {resumo.agendamentos_cancelados}"
    assert resumo.taxa_ocupacao == (2 / 3 * 100), f"Esperava 66.7%, got {resumo.taxa_ocupacao:.1f}%"

    print("[OK] PASSOU!")
    return True


async def validar_resumo_semana():
    """Valida resumo de semana."""
    print("\n" + "=" * 80)
    print("TESTE 2: RESUMO DA SEMANA")
    print("=" * 80)

    resumo = await obter_resumo_semana(TENANT_TEST)

    print(f"Total agendamentos: {resumo.agendamentos_total}")
    print(f"  Confirmados: {resumo.agendamentos_confirmados}")
    print(f"  Cancelados: {resumo.agendamentos_cancelados}")
    print(f"  Concluídos: {resumo.agendamentos_concluidos}")
    print(f"Taxa ocupação: {resumo.taxa_ocupacao:.1f}%")

    # Esperamos ao menos os 3 de hoje (semana começa em seg)
    assert resumo.agendamentos_total >= 3, f"Esperava >= 3, got {resumo.agendamentos_total}"

    print("[OK] PASSOU!")
    return True


async def validar_metricas_profissionais():
    """Valida métricas de profissionais."""
    print("\n" + "=" * 80)
    print("TESTE 3: MÉTRICAS DE PROFISSIONAIS")
    print("=" * 80)

    profs = await obter_metricas_profissionais(TENANT_TEST)

    print(f"Total profissionais: {len(profs)}")
    for prof in profs:
        print(f"  {prof.profissional}: {prof.atendimentos} atendimentos, "
              f"{prof.ocupacao_percentual:.1f}% ocupação, "
              f"R${prof.faturamento_estimado:.2f}")

    # Esperamos pelo menos 2 profissionais (Carla e Bruna)
    assert len(profs) >= 2, f"Esperava >= 2 profissionais, got {len(profs)}"

    # Carla deve ter 3 atendimentos (2 hoje + 1 ontem)
    carla = next((p for p in profs if p.profissional == "Carla"), None)
    if carla:
        print(f"\n  [OK] Carla encontrada: {carla.atendimentos} atendimentos")
        assert carla.atendimentos >= 3, f"Esperava >= 3 para Carla"

    print("[OK] PASSOU!")
    return True


async def validar_metricas_clientes():
    """Valida métricas de clientes."""
    print("\n" + "=" * 80)
    print("TESTE 4: MÉTRICAS DE CLIENTES")
    print("=" * 80)

    metricas = await obter_metricas_clientes(TENANT_TEST)

    print(f"Clientes novos (7d): {metricas.clientes_novos_7_dias}")
    print(f"Clientes recorrentes: {metricas.clientes_recorrentes}")
    print(f"Sem retorno 30d: {metricas.clientes_sem_retorno_30_dias}")
    print(f"Top clientes: {metricas.top_clientes}")

    # Validar tipos
    assert isinstance(metricas.clientes_novos_7_dias, int), "clientes_novos deve ser int"
    assert isinstance(metricas.clientes_recorrentes, int), "clientes_recorrentes deve ser int"

    print("[OK] PASSOU!")
    return True


async def validar_metricas_servicos():
    """Valida métricas de serviços."""
    print("\n" + "=" * 80)
    print("TESTE 5: MÉTRICAS DE SERVIÇOS")
    print("=" * 80)

    servicos = await obter_metricas_servicos(TENANT_TEST)

    print(f"Total serviços: {len(servicos)}")
    for srv in servicos:
        print(f"  {srv.servico}: {srv.quantidade} vezes, "
              f"ticket ~R${srv.ticket_medio:.2f}, "
              f"duração {srv.duracao_media_estimada}min")

    # Esperamos alguns serviços
    assert len(servicos) > 0, "Deve ter pelo menos 1 serviço"

    print("[OK] PASSOU!")
    return True


async def validar_alertas():
    """Valida geração de alertas."""
    print("\n" + "=" * 80)
    print("TESTE 6: ALERTAS OPERACIONAIS")
    print("=" * 80)

    alertas = await obter_alertas_operacionais(TENANT_TEST)

    print(f"Total alertas: {len(alertas)}")
    for alerta in alertas:
        print(f"  [{alerta.severidade}] {alerta.tipo}: {alerta.descricao}")

    # Validar tipos
    for alerta in alertas:
        assert alerta.severidade in ["info", "warning", "critical"]
        assert isinstance(alerta.acoes_sugeridas, list)

    print("[OK] PASSOU!")
    return True


async def validar_isolamento_multitenant():
    """Valida isolamento entre tenants."""
    print("\n" + "=" * 80)
    print("TESTE 7: ISOLAMENTO MULTI-TENANT")
    print("=" * 80)

    # Criar segundo tenant com dados diferentes
    tenant_2 = "tenant_f9_teste_002"

    # Criar 1 evento no tenant 2
    evento_t2 = {
        "descricao": "Evento tenant 2",
        "data": HOJE.date().isoformat(),
        "hora_inicio": "15:00",
        "hora_fim": "15:30",
        "duracao": 30,
        "confirmado": True,
        "status": "confirmado",
        "link": "",
        "cliente_id": "cli_t2_001",
        "cliente_nome": "Cliente T2",
        "profissional": "Prof T2",
    }

    await criar_evento_teste(tenant_2, "evt_t2_001", evento_t2)

    # Buscar dashboards de ambos
    resumo_t1 = await obter_resumo_hoje(TENANT_TEST)
    resumo_t2 = await obter_resumo_hoje(tenant_2)

    print(f"Tenant 1 (teste): {resumo_t1.agendamentos_total} eventos")
    print(f"Tenant 2 (isolado): {resumo_t2.agendamentos_total} eventos")

    # Validar isolamento
    assert resumo_t1.agendamentos_total > resumo_t2.agendamentos_total, \
        "Tenant 1 deve ter mais eventos"

    # Limpar tenant 2
    await limpar_eventos_teste(tenant_2)

    print("[OK] PASSOU!")
    return True


async def validar_dashboard_completo():
    """Valida dashboard completo."""
    print("\n" + "=" * 80)
    print("TESTE 8: DASHBOARD COMPLETO")
    print("=" * 80)

    dashboard = await obter_dashboard_completo(TENANT_TEST)

    print(f"Timestamp: {dashboard.timestamp}")
    print(f"Resumo hoje: {dashboard.resumo_hoje.agendamentos_total} eventos")
    print(f"Resumo semana: {dashboard.resumo_semana.agendamentos_total} eventos")
    print(f"Profissionais: {len(dashboard.metricas_profissionais)}")
    print(f"Serviços: {len(dashboard.metricas_servicos)}")
    print(f"Alertas: {len(dashboard.alertas)}")

    # Validar estrutura
    assert dashboard.timestamp is not None
    assert dashboard.resumo_hoje is not None
    assert dashboard.resumo_semana is not None
    assert isinstance(dashboard.metricas_profissionais, list)
    assert isinstance(dashboard.metricas_servicos, list)
    assert isinstance(dashboard.alertas, list)

    print("[OK] PASSOU!")
    return True


async def main():
    """Executa todos os testes."""
    print("\n" + "=" * 80)
    print("AUDITORIA DE DASHBOARD COM FIRESTORE REAL")
    print("=" * 80)
    print(f"Tenant de teste: {TENANT_TEST}")

    try:
        # 1. Criar dados
        count = await criar_dados_teste()

        # 2. Executar validações
        results = []
        results.append(("Resumo Hoje", await validar_resumo_hoje()))
        results.append(("Resumo Semana", await validar_resumo_semana()))
        results.append(("Profissionais", await validar_metricas_profissionais()))
        results.append(("Clientes", await validar_metricas_clientes()))
        results.append(("Serviços", await validar_metricas_servicos()))
        results.append(("Alertas", await validar_alertas()))
        results.append(("Isolamento", await validar_isolamento_multitenant()))
        results.append(("Dashboard Completo", await validar_dashboard_completo()))

        # 3. Resumo
        print("\n" + "=" * 80)
        print("RESUMO DOS TESTES")
        print("=" * 80)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for nome, result in results:
            status = "[OK] PASSOU" if result else "[ERR] FALHOU"
            print(f"{status}: {nome}")

        print(f"\nTotal: {passed}/{total} testes passaram")

        if passed == total:
            print("\n🎉 TODOS OS TESTES PASSARAM!")
        else:
            print(f"\n[WARN] {total - passed} testes falharam")

        # 4. Limpar dados
        print("\n" + "=" * 80)
        print("LIMPEZA")
        print("=" * 80)
        await limpar_eventos_teste(TENANT_TEST)

    except Exception as e:
        print(f"\n[ERR] ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
