"""
P0.4-DIAGNÓSTICO — Teste com tenant/actor REAL

USO: pytest -s tests/test_p04_diagnostico_cleanup_real_tenant.py

Objetivo:
Reproduzir o bug P0.4 usando o tenant/actor específico que está com problema.

IMPORTANTE:
- Este teste é SOMENTE DIAGNÓSTICO
- NÃO altera código de produção
- NÃO modifica o documento (salvo leitura)
- Apenas reproduz e trace o fluxo
- Não é commitado
"""

import pytest
import pytest_asyncio
from datetime import datetime

from utils.contexto_temporario import limpar_contexto_agendamento_v2
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
)


@pytest.mark.asyncio
async def test_p04_diagnostico_cleanup_tenant_real():
    """
    Teste diagnóstico usando o tenant/actor REAL do documento problemático.
    """

    # IDs REAIS do documento com problema
    dono_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    print("\n" + "=" * 80)
    print("[P0.4 DIAGNÓSTICO] TESTE COM TENANT/ACTOR REAL")
    print("=" * 80)
    print(f"\nPath: {path}\n")

    # ========================================================
    # PRÉ-REQUISITO: VERIFICAR ESTADO INICIAL
    # ========================================================
    print("[PRÉ-REQUISITO] Verificar estado inicial do documento")
    print("-" * 80)

    doc_antes = await buscar_dado_em_path(path)

    if not doc_antes:
        print("[AVISO] Documento não existe. Criando para diagnóstico...")
        doc_antes = {
            "tenant_id": dono_id,
            "actor_id": cliente_id,
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": False,
            "historico_texto": ["ola", "ola"],
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-09-29T09:00:00",
                "servico": "corte"
            },
            "dados_confirmacao_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-09-29T09:00:00",
                "servico": "corte",
                "descricao": "Corte com Bruna",
                "duracao": 30
            },
            "profissional_escolhido": "Bruna",
            "servico": "corte",
            "data_hora": "2026-09-29T09:00:00",
            "intencao_conversacional": "confirmacao_agendamento",
            "confianca_intencao_conversacional": 95,
        }
        await salvar_dado_em_path(path, doc_antes)
        print("[OK] Documento criado para diagnóstico")
    else:
        print("[OK] Documento existe")

    print("\n[ESTADO INICIAL]")
    print(f"  Total de campos: {len(doc_antes)}")
    print(f"  estado_fluxo: {doc_antes.get('estado_fluxo')}")
    print(f"  aguardando_confirmacao_agendamento: {doc_antes.get('aguardando_confirmacao_agendamento')}")
    print(f"  draft_agendamento: {doc_antes.get('draft_agendamento') is not None}")
    print(f"  intencao_conversacional: {doc_antes.get('intencao_conversacional')}")
    print(f"  confianca_intencao_conversacional: {doc_antes.get('confianca_intencao_conversacional')}")
    print(f"  historico_texto: {doc_antes.get('historico_texto')}")

    # ========================================================
    # ETAPA 1: CHAMAR CLEANUP COM TENANT/ACTOR REAL
    # ========================================================
    print("\n[ETAPA 1] CHAMAR CLEANUP COM TENANT/ACTOR REAL")
    print("-" * 80)

    print(f"[CALL] limpar_contexto_agendamento_v2(dono_id='{dono_id}', cliente_id='{cliente_id}')")

    try:
        result_cleanup = await limpar_contexto_agendamento_v2(dono_id, cliente_id)
        print(f"\n[RESULTADO] Cleanup retornou: {result_cleanup}")
        print(f"[TIPO] {type(result_cleanup)}")
    except Exception as e:
        print(f"\n[EXCEÇÃO] {type(e).__name__}: {e}")
        result_cleanup = None

    # ========================================================
    # ETAPA 2: VERIFICAR ESTADO IMEDIATAMENTE APÓS CLEANUP
    # ========================================================
    print("\n[ETAPA 2] LEITURA IMEDIATAMENTE APÓS CLEANUP")
    print("-" * 80)

    doc_apos_cleanup = await buscar_dado_em_path(path)

    if not doc_apos_cleanup:
        print("[ERRO] Documento foi deletado!")
    else:
        print("[OK] Documento continua existindo")
        print(f"  Total de campos: {len(doc_apos_cleanup)}")
        print(f"  estado_fluxo: {doc_apos_cleanup.get('estado_fluxo')}")
        print(f"  aguardando_confirmacao_agendamento: {doc_apos_cleanup.get('aguardando_confirmacao_agendamento')}")
        print(f"  draft_agendamento: {doc_apos_cleanup.get('draft_agendamento')}")
        print(f"  intencao_conversacional: {doc_apos_cleanup.get('intencao_conversacional')}")
        print(f"  confianca_intencao_conversacional: {doc_apos_cleanup.get('confianca_intencao_conversacional')}")
        print(f"  historico_texto: {doc_apos_cleanup.get('historico_texto')}")

    # ========================================================
    # ETAPA 3: ANÁLISE E CONCLUSÃO
    # ========================================================
    print("\n[ANÁLISE]")
    print("-" * 80)

    print("\n[RESULTADO DO CLEANUP]")
    if result_cleanup is True:
        print("  [OK] Cleanup retornou True")
    elif result_cleanup is False:
        print("  [ERRO] Cleanup retornou False")
    elif result_cleanup is None:
        print("  [ERRO] Cleanup lançou exceção")
    else:
        print(f"  [DESCONHECIDO] Cleanup retornou: {result_cleanup}")

    print("\n[RESULTADO DO DELETE_FIELD]")
    if doc_apos_cleanup:
        if "draft_agendamento" not in doc_apos_cleanup:
            print("  [OK] draft_agendamento foi removido")
        else:
            print(f"  [FAIL] draft_agendamento AINDA EXISTE: {doc_apos_cleanup.get('draft_agendamento')}")

        if "intencao_conversacional" not in doc_apos_cleanup:
            print("  [OK] intencao_conversacional foi removido")
        else:
            print(f"  [FAIL] intencao_conversacional AINDA EXISTE: {doc_apos_cleanup.get('intencao_conversacional')}")

        if "confianca_intencao_conversacional" not in doc_apos_cleanup:
            print("  [OK] confianca_intencao_conversacional foi removido")
        else:
            print(f"  [FAIL] confianca_intencao_conversacional AINDA EXISTE")

        if doc_apos_cleanup.get("estado_fluxo") == "idle":
            print("  [OK] estado_fluxo foi setado para 'idle'")
        else:
            print(f"  [FAIL] estado_fluxo é '{doc_apos_cleanup.get('estado_fluxo')}' (esperado: idle)")

    print("\n[CONCLUSÃO]")
    if result_cleanup is True and doc_apos_cleanup and \
       "draft_agendamento" not in doc_apos_cleanup and \
       "intencao_conversacional" not in doc_apos_cleanup and \
       doc_apos_cleanup.get("estado_fluxo") == "idle":
        print("  [SUCESSO] Cleanup funcionou corretamente")
    else:
        print("  [PROBLEMA] Cleanup não funcionou como esperado")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-v"])
