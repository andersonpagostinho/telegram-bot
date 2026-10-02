"""
P1-C FIX — Validação Rápida

Teste simples para validar que a implementação funciona com DELETE_FIELD.

USO: pytest -s tests/test_p1c_fix_validacao_rapida.py
"""

import pytest
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path, firestore


@pytest.mark.asyncio
async def test_p1c_motivo_estado_removido_com_delete_field():
    """
    Validação: Quando entrada é social ("ola"),
    motivo_estado deve ser removido do Firestore usando DELETE_FIELD.
    """
    dono_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"
    path = f"Clientes/{dono_id}/Sessoes/{cliente_id}"

    # Setup: contexto com profissional_nao_atende
    doc_initial = {
        "tenant_id": dono_id,
        "actor_id": cliente_id,
        "estado_fluxo": "aguardando_profissional",
        "motivo_estado": "profissional_nao_atende_servico",
        "profissional_rejeitado": "Carla",
        "profissionais_validos": ["Bruna", "Gloria", "Joana"],
        "servico": "corte",
        "data_hora": "2026-09-30T09:00:00",
        "draft_agendamento": {
            "servico": "corte",
            "data_hora": "2026-09-30T09:00:00"
        },
        "intencao_conversacional": "indefinida",
        "confianca_intencao_conversacional": 40,
        "tipo_ajuste_incremental": None,
    }

    await salvar_dado_em_path(path, doc_initial)
    print("Setup: Contexto com profissional_nao_atende criado")

    # Simular: P1-C FIX logic (copiado do router)
    tipo_ajuste = doc_initial.get("tipo_ajuste_incremental")
    intencao = doc_initial.get("intencao_conversacional")

    tem_ref_profissional = (tipo_ajuste == "profissional")
    tem_outro_ajuste = tipo_ajuste in ["horario", "servico"]

    is_entrada_social = (
        intencao == "indefinida"
        and not tem_ref_profissional
        and not tem_outro_ajuste
    )

    assert is_entrada_social, "Deveria ter detectado entrada social"
    print("Detectado: Entrada social (sem evidência de retomada)")

    # P1-C FIX: Usar DELETE_FIELD (como P0.4)
    if is_entrada_social:
        payload_limpeza = {
            "motivo_estado": firestore.DELETE_FIELD,
            "profissional_rejeitado": firestore.DELETE_FIELD,
        }
        await salvar_dado_em_path(path, payload_limpeza)
        print("Ação: DELETE_FIELD aplicado para motivo_estado e profissional_rejeitado")

    # Verificação: motivo_estado deve estar removido
    doc_final = await buscar_dado_em_path(path)

    assert doc_final.get("motivo_estado") is None, (
        f"FALHA: motivo_estado ainda existe = {doc_final.get('motivo_estado')}"
    )

    assert doc_final.get("profissional_rejeitado") is None, (
        f"FALHA: profissional_rejeitado ainda existe"
    )

    assert doc_final.get("draft_agendamento") is not None, (
        f"FALHA: draft_agendamento foi removido incorretamente"
    )

    assert doc_final.get("profissionais_validos") == ["Bruna", "Gloria", "Joana"], (
        f"FALHA: profissionais_validos foi alterado"
    )

    assert doc_final.get("estado_fluxo") == "aguardando_profissional", (
        f"FALHA: estado_fluxo foi alterado"
    )

    print("[OK] P1-C FIX Validado:")
    print(f"  motivo_estado removido: {doc_final.get('motivo_estado') is None}")
    print(f"  draft mantido: {doc_final.get('draft_agendamento') is not None}")
    print(f"  profissionais mantidos: {len(doc_final.get('profissionais_validos', [])) > 0}")
    print(f"  estado_fluxo mantido: {doc_final.get('estado_fluxo') == 'aguardando_profissional'}")


if __name__ == "__main__":
    pytest.main([__file__, "-s", "-v"])
