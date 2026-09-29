"""
P0.4-VALIDAÇÃO 1 — Teste DELETE_FIELD com Firestore REAL

Objetivo: Provar que limpar_contexto_agendamento_v2() realmente remove
campos transitórios usando firestore.DELETE_FIELD com merge=True.

Usa Firebase REAL (não mock).
"""

import pytest
import pytest_asyncio
from datetime import datetime
import uuid
from google.cloud import firestore

from utils.contexto_temporario import (
    limpar_contexto_agendamento_v2,
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2
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
        "tenant": f"tenant_p04_delete_{uuid.uuid4().hex[:8]}",
        "user": f"user_p04_delete_{uuid.uuid4().hex[:8]}"
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
async def test_delete_field_realmente_remove_campos(test_ids, cleanup_test):
    """
    TESTE CRÍTICO: Validar que DELETE_FIELD remove campos do Firestore real.

    Cenário:
    1. Criar documento com campos transitórios de agendamento
    2. Chamar limpar_contexto_agendamento_v2()
    3. Ler novamente do Firestore
    4. Validar que campos foram removidos completamente
    """

    dono_id = test_ids["tenant"]
    cliente_id = test_ids["user"]
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    # ========================================================
    # PASSO 1: CRIAR DOCUMENTO COM ESTADO RESIDUAL
    # ========================================================
    print("\n[P0.4] PASSO 1: Criar documento com estado residual")

    documento_inicial = {
        # Metadados estruturais
        "actor_id": cliente_id,
        "tenant_id": dono_id,
        "tipo_usuario": "cliente",

        # Histórico (deve ser preservado)
        "historico_texto": ["mensagem1", "mensagem2"],

        # Campos transitórios de agendamento (devem ser removidos)
        "estado_fluxo": "agendando",
        "aguardando_confirmacao_agendamento": True,
        "intencao_conversacional": "confirmacao_agendamento",
        "objetivo_conversacional": "criar_evento",
        "tipo_ajuste_incremental": "alteracao_horario",

        # Draft (deve ser removido)
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T09:00:00"
        },

        # Dados de confirmação (devem ser removidos)
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T09:00:00",
            "duracao": 30,
            "descricao": "Corte com Bruna"
        },

        # Escolhas (devem ser removidas)
        "profissional_escolhido": "Bruna",
        "servico": "corte",
        "data_hora": "2026-09-29T09:00:00",

        # Sugestões (devem ser removidas)
        "modo_escolha_horario": True,
        "horarios_sugeridos": ["09:00", "10:00"],
        "alternativa_profissional": ["Paula", "Sofia"],

        # Timestamp
        "_created_at": datetime.now().isoformat()
    }

    # Salvar documento inicial
    await salvar_dado_em_path(path, documento_inicial)
    print(f"[OK] Documento criado com {len(documento_inicial)} campos")

    # Validar que foi criado
    doc_antes = await buscar_dado_em_path(path)
    assert doc_antes is not None
    assert doc_antes.get("estado_fluxo") == "agendando"
    assert doc_antes.get("intencao_conversacional") == "confirmacao_agendamento"
    assert "draft_agendamento" in doc_antes
    assert "dados_confirmacao_agendamento" in doc_antes
    print("[OK] Documento validado com estado inicial")

    # ========================================================
    # PASSO 2: EXECUTAR CLEANUP
    # ========================================================
    print("\n[P0.4] PASSO 2: Executar limpar_contexto_agendamento_v2()")

    result = await limpar_contexto_agendamento_v2(dono_id, cliente_id)
    print(f"[P0.4] Cleanup retornou: {result}")
    assert result is True, f"Cleanup falhou: {result}"

    # ========================================================
    # PASSO 3: LER NOVAMENTE DO FIRESTORE
    # ========================================================
    print("\n[P0.4] PASSO 3: Ler documento após cleanup")

    doc_depois = await buscar_dado_em_path(path)
    assert doc_depois is not None, "Documento foi deletado (erro!)"
    print(f"[OK] Documento continua existindo com {len(doc_depois)} campos")

    # ========================================================
    # PASSO 4: VALIDAR ESTADO APÓS CLEANUP
    # ========================================================
    print("\n[P0.4] PASSO 4: Validar estado após cleanup")

    # ✅ ESTADO deve ser "idle"
    assert doc_depois.get("estado_fluxo") == "idle", \
        f"estado_fluxo={doc_depois.get('estado_fluxo')} (esperado: idle)"
    print("[PASS] estado_fluxo == idle")

    # ✅ CONFIRMAÇÃO deve ser False
    assert doc_depois.get("aguardando_confirmacao_agendamento") is False, \
        f"aguardando_confirmacao_agendamento={doc_depois.get('aguardando_confirmacao_agendamento')} (esperado: False)"
    print("[PASS] aguardando_confirmacao_agendamento == False")

    # ✅ CAMPOS TRANSITÓRIOS devem ser REMOVIDOS (não existir no documento)
    campos_transitorios = [
        "intencao_conversacional",
        "objetivo_conversacional",
        "tipo_ajuste_incremental",
        "draft_agendamento",
        "dados_confirmacao_agendamento",
        "profissional_escolhido",
        "servico",
        "data_hora",
        "modo_escolha_horario",
        "horarios_sugeridos",
        "alternativa_profissional"
    ]

    print("\n[P0.4] Validando que campos transitórios foram removidos:")
    for campo in campos_transitorios:
        assert campo not in doc_depois, \
            f"[FAIL] Campo '{campo}' ainda existe! Valor: {doc_depois.get(campo)}"
        print(f"  [PASS] {campo} foi removido")

    # ========================================================
    # PASSO 5: VALIDAR QUE METADADOS FORAM PRESERVADOS
    # ========================================================
    print("\n[P0.4] PASSO 5: Validar que metadados foram preservados")

    campos_preservados = {
        "actor_id": cliente_id,
        "tenant_id": dono_id,
        "tipo_usuario": "cliente",
        "historico_texto": ["mensagem1", "mensagem2"]
    }

    for campo, valor_esperado in campos_preservados.items():
        valor_real = doc_depois.get(campo)
        assert valor_real == valor_esperado, \
            f"[FAIL] Campo '{campo}': esperado {valor_esperado}, obtido {valor_real}"
        print(f"  [PASS] {campo} = {valor_real}")

    # ========================================================
    # RESULTADO FINAL
    # ========================================================
    print("\n" + "="*60)
    print("[P0.4] TESTE PASSOU - DELETE_FIELD + historico_texto PRESERVADO")
    print("="*60)
    print("\nRESULTADO:")
    print("- DELETE_FIELD com merge=True: OK FUNCIONA")
    print("- Campos transitórios removidos: OK SIM")
    print("- historico_texto PRESERVADO: OK SIM")
    print("- Campos metadados preservados: OK SIM")
    print("- Estado virou idle: OK SIM")
    print("- Confirmação virou False: OK SIM")
    print("\nCONCLUSÃO: Cleanup CORRIGIDO - historico_texto preservado")
    print("Firestore real validado com sucesso.")
    print("="*60 + "\n")

    return True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
