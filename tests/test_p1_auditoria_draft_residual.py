"""
P1 AUDITORIA — Draft Residual Após Profissional Não Atender

Objetivo: Validar a CAUSA P1-C identificada na auditoria

Teste com tenant/actor REAL.

USO: pytest -s tests/test_p1_auditoria_draft_residual.py
"""

import pytest
import pytest_asyncio
from datetime import datetime

from router.principal_router import roteador_principal
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
)


@pytest.mark.asyncio
async def test_p1_draft_residual_apos_profissional_nao_atende():
    """
    Teste de reprodução da CAUSA P1-C:

    1. Usuário: "quero corte para amanha as 9 com carla"
       → Sistema: carla não atende corte
       → Estado: motivo_estado=profissional_nao_atende_servico

    2. Usuário: "ola"
       → Sistema: "Desculpe, não entendi. Para corte, pode escolher: X"
       → Estado: ??? draft persiste?
    """

    # IDs REAIS
    dono_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    print("\n" + "="*80)
    print("[P1 AUDITORIA] Draft Residual Após Profissional Não Atender")
    print("="*80 + "\n")

    # ========================================================
    # SETUP: Criar sessão inicial
    # ========================================================
    print("[SETUP] Criando sessão inicial com contexto limpo")

    doc_initial = {
        "tenant_id": dono_id,
        "actor_id": cliente_id,
        "estado_fluxo": "idle",
        "historico_texto": [],
        "modo_conversa": "convite_agendamento",
    }
    await salvar_dado_em_path(path, doc_initial)
    print("[OK] Sessão criada\n")

    # ========================================================
    # PASSO 1: Simular "quero corte para amanha as 9 com carla"
    # ========================================================
    print("[PASSO 1] Entrada: 'quero corte para amanha as 9 com carla'")
    print("-" * 80)

    contexto_msg1 = None
    resultado_msg1 = await roteador_principal(
        texto="quero corte para amanha as 9 com carla",
        user_id=cliente_id,
        context=contexto_msg1,
        custom_context={
            "dono_id": dono_id,
            "cliente_id": cliente_id
        }
    )

    print(f"[RESPOSTA] {resultado_msg1.get('resposta', 'N/A')[:100]}...\n")

    # Verificar estado após PASSO 1
    print("[LEITURA] Estado após PASSO 1")
    doc_apos_p1 = await buscar_dado_em_path(path)

    if doc_apos_p1:
        print(f"  estado_fluxo: {doc_apos_p1.get('estado_fluxo')}")
        print(f"  motivo_estado: {doc_apos_p1.get('motivo_estado')}")
        print(f"  draft_agendamento: {bool(doc_apos_p1.get('draft_agendamento'))}")
        print(f"  profissional_rejeitado: {doc_apos_p1.get('profissional_rejeitado')}")
        print(f"  profissionais_validos: {doc_apos_p1.get('profissionais_validos')}")
    print()

    # ========================================================
    # PASSO 2: Simular "ola" (entrada indefinida)
    # ========================================================
    print("[PASSO 2] Entrada: 'ola' (entrada indefinida)")
    print("-" * 80)

    # Carregar contexto atualizado
    contexto_msg2 = await buscar_dado_em_path(path)

    resultado_msg2 = await roteador_principal(
        texto="ola",
        user_id=cliente_id,
        context=contexto_msg2,
        custom_context={
            "dono_id": dono_id,
            "cliente_id": cliente_id
        }
    )

    print(f"[RESPOSTA] {resultado_msg2.get('resposta', 'N/A')[:100]}...\n")

    # Verificar estado após PASSO 2 — VERIFICAÇÃO CRÍTICA
    print("[LEITURA] Estado após PASSO 2 — VERIFICAÇÃO CRÍTICA")
    doc_apos_p2 = await buscar_dado_em_path(path)

    if doc_apos_p2:
        print(f"  estado_fluxo: {doc_apos_p2.get('estado_fluxo')}")
        print(f"  motivo_estado: {doc_apos_p2.get('motivo_estado')}")
        print(f"  draft_agendamento: {bool(doc_apos_p2.get('draft_agendamento'))}")
        print(f"  profissional_rejeitado: {doc_apos_p2.get('profissional_rejeitado')}")
        print(f"  intencao_conversacional: {doc_apos_p2.get('intencao_conversacional')}")
    print()

    # ========================================================
    # ANÁLISE: Confirmar CAUSA P1-C
    # ========================================================
    print("[ANÁLISE] Validar CAUSA P1-C")
    print("-" * 80)

    # Critério 1: draft_agendamento persiste?
    draft_persiste = "draft_agendamento" in doc_apos_p2 and doc_apos_p2.get("draft_agendamento")
    print(f"  ✓ draft_agendamento persiste: {draft_persiste}")

    # Critério 2: motivo_estado persiste?
    motivo_persiste = doc_apos_p2.get("motivo_estado") == "profissional_nao_atende_servico"
    print(f"  ✓ motivo_estado persiste: {motivo_persiste}")

    # Critério 3: estado_fluxo DEVERIA ser 'idle' mas é 'aguardando_profissional'?
    estado_incorreto = doc_apos_p2.get("estado_fluxo") == "aguardando_profissional"
    print(f"  ✓ estado_fluxo permanece aguardando_profissional: {estado_incorreto}")

    # Critério 4: intencao_conversacional é 'indefinida'?
    intencao_indefinida = doc_apos_p2.get("intencao_conversacional") == "indefinida"
    print(f"  ✓ intencao_conversacional = indefinida: {intencao_indefinida}")

    print()

    # ========================================================
    # CONCLUSÃO
    # ========================================================
    print("[CONCLUSÃO]")
    print("-" * 80)

    causa_p1c_confirmada = (
        draft_persiste
        and motivo_persiste
        and estado_incorreto
        and intencao_indefinida
    )

    if causa_p1c_confirmada:
        print("✅ CAUSA P1-C CONFIRMADA")
        print("   Cleanup NÃO ocorre; SAVE posterior recria o estado")
        print("   - draft_agendamento: persistido")
        print("   - motivo_estado: persistido")
        print("   - estado_fluxo: persistido (aguardando_profissional)")
        print("   - intencao: classificada como indefinida")
    else:
        print("❌ CAUSA P1-C NÃO CONFIRMADA")
        if not draft_persiste:
            print("   - draft_agendamento FOI removido (inesperado)")
        if not motivo_persiste:
            print("   - motivo_estado FOI removido (inesperado)")
        if not estado_incorreto:
            print(f"   - estado_fluxo foi alterado para: {doc_apos_p2.get('estado_fluxo')}")
        if not intencao_indefinida:
            print(f"   - intencao foi alterada para: {doc_apos_p2.get('intencao_conversacional')}")

    print("\n" + "="*80 + "\n")

    # Assertar resultado
    assert causa_p1c_confirmada, (
        f"CAUSA P1-C não validada. "
        f"Esperado: draft_persiste + motivo_persiste + estado_erro + intencao_indef, "
        f"Obtido: {draft_persiste} + {motivo_persiste} + {estado_incorreto} + {intencao_indefinida}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-v"])
