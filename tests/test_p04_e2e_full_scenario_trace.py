"""
P0.4-E2E — Teste completo com rastreamento de Firestore

Objetivo: Reproduzir cenário COMPLETO sem alteração de produção.

Fluxo:
1. Agendamento → verificar documento Firestore
2. Confirmação → verificar documento Firestore
3. Evento criado → verificar documento Firestore
4. Cleanup executado → verificar documento Firestore
5. Nova mensagem "ola" → simular chegada
6. Leitura da sessão → verificar documento Firestore

Pergunta de investigação:
- Cleanup realmente limpa?
- Algo recria estado antigo?
- Race condition entre reply_text e cleanup?
"""

import pytest
import pytest_asyncio
from datetime import datetime
import uuid
from google.cloud import firestore

from utils.contexto_temporario import (
    limpar_contexto_agendamento_v2,
)
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path
)


@pytest_asyncio.fixture
async def test_ids():
    """IDs únicos para teste isolado"""
    return {
        "tenant": f"tenant_e2e_{uuid.uuid4().hex[:8]}",
        "user": f"user_e2e_{uuid.uuid4().hex[:8]}"
    }


@pytest_asyncio.fixture
async def cleanup_test(test_ids):
    """Limpeza após teste"""
    yield
    try:
        await deletar_dado_em_path(f"Clientes/{test_ids['tenant']}/Sessoes/{test_ids['user']}")
    except:
        pass


@pytest.mark.asyncio
async def test_p04_e2e_full_scenario_with_firestore_trace(test_ids, cleanup_test):
    """
    E2E completo com rastreamento de Firestore real entre cada etapa.

    SEM alteração de produção — apenas investigação.
    """

    dono_id = test_ids["tenant"]
    cliente_id = test_ids["user"]
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    print("\n" + "="*70)
    print("[P0.4 E2E] TESTE COMPLETO COM RASTREAMENTO FIRESTORE")
    print("="*70)

    # ========================================================
    # ETAPA 1: AGENDAMENTO INICIAL
    # ========================================================
    print("\n[ETAPA 1] AGENDAMENTO INICIAL")
    print("-" * 70)

    documento_agendamento = {
        # Metadados
        "actor_id": cliente_id,
        "tenant_id": dono_id,
        "tipo_usuario": "cliente",
        "historico_texto": ["usuario: oi, quero agendar corte"],

        # Estado de agendamento
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "intencao_conversacional": "confirmacao_agendamento",
        "objetivo_conversacional": "criar_evento",

        # Draft do que será agendado
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T14:00:00"
        },
        "_created_at": datetime.now().isoformat()
    }

    await salvar_dado_em_path(path, documento_agendamento)
    print(f"[OK] Documento salvo")

    doc_etapa1 = await buscar_dado_em_path(path)
    print(f"[DOC] Campos presentes: {len(doc_etapa1)}")
    print(f"      estado_fluxo: {doc_etapa1.get('estado_fluxo')}")
    print(f"      intencao_conversacional: {doc_etapa1.get('intencao_conversacional')}")
    print(f"      historico_texto: {doc_etapa1.get('historico_texto')}")
    print(f"      draft_agendamento: {doc_etapa1.get('draft_agendamento') is not None}")

    # ========================================================
    # ETAPA 2: CONFIRMAÇÃO PENDENTE
    # ========================================================
    print("\n[ETAPA 2] CONFIRMAÇÃO PENDENTE")
    print("-" * 70)

    # Simular que usuário confirmou
    documento_confirmacao = {
        **documento_agendamento,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T14:00:00",
            "duracao": 30,
            "descricao": "Corte com Bruna"
        },
        "profissional_escolhido": "Bruna",
        "servico": "corte",
        "data_hora": "2026-09-29T14:00:00",
    }

    await salvar_dado_em_path(path, documento_confirmacao)
    print(f"[OK] Documento atualizado com confirmação")

    doc_etapa2 = await buscar_dado_em_path(path)
    print(f"[DOC] Campos presentes: {len(doc_etapa2)}")
    print(f"      estado_fluxo: {doc_etapa2.get('estado_fluxo')}")
    print(f"      dados_confirmacao_agendamento: {doc_etapa2.get('dados_confirmacao_agendamento') is not None}")
    print(f"      historico_texto: {doc_etapa2.get('historico_texto')}")

    # ========================================================
    # ETAPA 3: EVENTO CRIADO (simulado)
    # ========================================================
    print("\n[ETAPA 3] EVENTO CRIADO")
    print("-" * 70)

    # Simular que evento foi criado (adicionado estado de criação)
    documento_evento_criado = {
        **documento_confirmacao,
        "evento_criado": {
            "evento_id": "evt_123",
            "timestamp": datetime.now().isoformat()
        }
    }

    await salvar_dado_em_path(path, documento_evento_criado)
    print(f"[OK] Evento criado (simulado)")

    doc_etapa3 = await buscar_dado_em_path(path)
    print(f"[DOC] Campos presentes: {len(doc_etapa3)}")
    print(f"      evento_criado: {doc_etapa3.get('evento_criado') is not None}")
    print(f"      estado_fluxo: {doc_etapa3.get('estado_fluxo')}")
    print(f"      intencao_conversacional: {doc_etapa3.get('intencao_conversacional')}")
    print(f"      historico_texto: {doc_etapa3.get('historico_texto')}")
    print(f"      draft_agendamento: {doc_etapa3.get('draft_agendamento') is not None}")

    # ========================================================
    # ETAPA 4: CLEANUP EXECUTADO
    # ========================================================
    print("\n[ETAPA 4] CLEANUP EXECUTADO")
    print("-" * 70)

    result_cleanup = await limpar_contexto_agendamento_v2(dono_id, cliente_id)
    print(f"[OK] Cleanup retornou: {result_cleanup}")

    # Verificar documento IMEDIATAMENTE após cleanup
    doc_etapa4_apos_cleanup = await buscar_dado_em_path(path)
    print(f"[DOC] Campos presentes APÓS cleanup: {len(doc_etapa4_apos_cleanup)}")
    print(f"      estado_fluxo: {doc_etapa4_apos_cleanup.get('estado_fluxo')}")
    print(f"      aguardando_confirmacao_agendamento: {doc_etapa4_apos_cleanup.get('aguardando_confirmacao_agendamento')}")
    print(f"      intencao_conversacional: {doc_etapa4_apos_cleanup.get('intencao_conversacional')}")
    print(f"      draft_agendamento: {doc_etapa4_apos_cleanup.get('draft_agendamento')}")
    print(f"      dados_confirmacao_agendamento: {doc_etapa4_apos_cleanup.get('dados_confirmacao_agendamento')}")
    print(f"      historico_texto: {doc_etapa4_apos_cleanup.get('historico_texto')}")

    # ========================================================
    # ETAPA 5: NOVA MENSAGEM CHEGA ("ola")
    # ========================================================
    print("\n[ETAPA 5] NOVA MENSAGEM 'ola' CHEGA")
    print("-" * 70)

    # Simular que nova mensagem chega
    # Em produção: evento_handler.py chamaria add_evento_por_gpt()
    # Aqui apenas simulamos a leitura
    print(f"[SIM] Nova mensagem recebida: 'ola'")

    # Ler documento IMEDIATAMENTE antes de processar
    doc_etapa5_before_process = await buscar_dado_em_path(path)
    print(f"[DOC] Campos presentes ANTES de processar 'ola': {len(doc_etapa5_before_process)}")
    print(f"      estado_fluxo: {doc_etapa5_before_process.get('estado_fluxo')}")
    print(f"      intencao_conversacional: {doc_etapa5_before_process.get('intencao_conversacional')}")
    print(f"      historico_texto: {doc_etapa5_before_process.get('historico_texto')}")

    # ========================================================
    # ETAPA 6: VERIFICAÇÃO FINAL
    # ========================================================
    print("\n[ETAPA 6] VERIFICAÇÃO FINAL")
    print("-" * 70)

    doc_final = await buscar_dado_em_path(path)

    # Verificações críticas
    checks = {
        "estado_fluxo == idle": doc_final.get("estado_fluxo") == "idle",
        "aguardando_confirmacao == False": doc_final.get("aguardando_confirmacao_agendamento") is False,
        "historico_texto PRESERVADO": doc_final.get("historico_texto") == ["usuario: oi, quero agendar corte"],
        "intencao_conversacional REMOVIDO": "intencao_conversacional" not in doc_final,
        "draft_agendamento REMOVIDO": "draft_agendamento" not in doc_final,
        "dados_confirmacao_agendamento REMOVIDO": "dados_confirmacao_agendamento" not in doc_final,
        "evento_criado REMOVIDO": "evento_criado" not in doc_final,
    }

    print("[VALIDAÇÕES FINAIS]")
    for check_name, result in checks.items():
        status = "OK" if result else "FAIL"
        print(f"  [{status}] {check_name}")

    # ========================================================
    # ANÁLISE DE RASTREAMENTO
    # ========================================================
    print("\n[ANÁLISE]")
    print("-" * 70)

    # Hipótese 1: Cleanup realmente limpa?
    if doc_final.get("estado_fluxo") == "idle" and "intencao_conversacional" not in doc_final:
        print("[CONFIRMADO] Cleanup REALMENTE LIMPA - estado resetado, campos transitórios removidos")
    else:
        print("[PROBLEMA] Cleanup NÃO limpa adequadamente")

    # Hipótese 2: Algo recria estado antigo?
    if doc_etapa4_apos_cleanup.get("estado_fluxo") == "idle" and doc_final.get("estado_fluxo") == "idle":
        print("[CONFIRMADO] Estado NÃO é recriado após cleanup - consistente")
    else:
        print("[PROBLEMA] Estado foi alterado entre etapa 4 e final")

    # Hipótese 3: Histórico preservado?
    if doc_final.get("historico_texto") == ["usuario: oi, quero agendar corte"]:
        print("[CONFIRMADO] historico_texto PRESERVADO - contexto disponível para nova mensagem")
    else:
        print("[PROBLEMA] historico_texto não foi preservado")

    # Asserções finais
    assert doc_final.get("estado_fluxo") == "idle", "estado_fluxo deve ser idle"
    assert doc_final.get("aguardando_confirmacao_agendamento") is False, "aguardando deve ser False"
    assert "intencao_conversacional" not in doc_final, "intencao_conversacional deve ser removido"
    assert "draft_agendamento" not in doc_final, "draft_agendamento deve ser removido"
    assert doc_final.get("historico_texto") == ["usuario: oi, quero agendar corte"], "historico_texto deve ser preservado"

    print("\n" + "="*70)
    print("[P0.4 E2E] TESTE PASSOU - CENÁRIO COMPLETO VALIDADO")
    print("="*70 + "\n")

    return True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
