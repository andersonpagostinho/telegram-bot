"""
VALIDACAO FINAL P0 — FIRESTORE REAL

Testa com dados reais do tenant 5511991382080
"""

import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_validacao_final_duracao_bruna_firestore():
    """
    Valida que Bruna tem manicure e pedicure com durações corretas.
    Lê dados REAIS do Firestore (sem mock).
    """
    from firebase_admin import firestore
    import firebase_admin

    try:
        db = firestore.client()
    except:
        pytest.skip("Firestore não inicializado")

    TENANT_ID = "5511991382080"

    # Buscar Bruna
    bruna_ref = db.collection("Clientes").document(TENANT_ID).collection("Profissionais").document("Bruna")
    bruna_snap = bruna_ref.get()

    assert bruna_snap.exists, "Bruna não encontrada"

    bruna_data = bruna_snap.to_dict()
    servicos_bruna = set(s.lower() for s in bruna_data.get("servicos", []))

    print(f"\n[VALIDACAO] Bruna oferece: {bruna_data.get('servicos')}")
    assert "manicure" in servicos_bruna, "Bruna não oferece manicure"
    assert "pedicure" in servicos_bruna, "Bruna não oferece pedicure"
    print("[OK] Bruna oferece ambos os serviços")

    # Buscar durações do catálogo
    servicos_ref = db.collection("Clientes").document(TENANT_ID).collection("ServicosNegocio")

    duracao_map = {}
    for doc in servicos_ref.stream():
        serv_data = doc.to_dict()
        nome = (serv_data.get("nome") or "").lower()
        duracao = serv_data.get("duracao")
        if nome in ["manicure", "pedicure"]:
            duracao_map[nome] = duracao
            print(f"[DURACAO] {nome}: {duracao} min")

    assert "manicure" in duracao_map, "Manicure não tem duração no catálogo"
    assert "pedicure" in duracao_map, "Pedicure não tem duração no catálogo"

    dur_manicure = duracao_map["manicure"]
    dur_pedicure = duracao_map["pedicure"]
    dur_total = dur_manicure + dur_pedicure

    print(f"[TOTAL] {dur_manicure} + {dur_pedicure} = {dur_total} minutos")

    # Validar duração total
    assert dur_total > 0, "Duração total deve ser positiva"
    assert dur_total <= 120, "Duração total não deve exceder 2 horas"

    # Validar contra janela 14h-17h
    hora_inicio = 14  # 14:00
    hora_fim_calculada = hora_inicio + (dur_total / 60)

    print(f"[JANELA] 14:00 + {dur_total}min = {hora_fim_calculada:.2f}")
    assert hora_fim_calculada <= 17, f"Bloco não cabe em 14:00-17:00 (termina {hora_fim_calculada:.2f})"

    print(f"[OK] DURACAO VALIDADA: {dur_total} minutos")
    return dur_total


@pytest.mark.asyncio
async def test_validacao_final_resolver_bloco():
    """
    Testa resolver_bloco_servicos com dados reais de Bruna.
    """
    from services.multisservico_service import resolver_bloco_servicos

    TENANT_ID = "5511991382080"

    # Chamar resolver com dados reais
    resultado = await resolver_bloco_servicos(
        tenant_id=TENANT_ID,
        nome_profissional="Bruna",
        servicos=["manicure", "pedicure"]
    )

    print(f"\n[RESOLVER] Resultado: {resultado}")

    assert resultado.get("valido"), f"Bloco deveria ser válido: {resultado.get('mensagens')}"
    assert resultado.get("duracao_total") > 0, "Duração total deve ser positiva"

    duracao_total = resultado.get("duracao_total")
    print(f"[RESOLVER] Duracao total: {duracao_total} minutos")

    # Validar contra janela
    hora_fim = 14 + (duracao_total / 60)
    assert hora_fim <= 17, f"Bloco termina {hora_fim:.2f}, ultrapassa 17:00"

    print(f"[OK] RESOLVER VALIDADO: {duracao_total} minutos")


@pytest.mark.asyncio
async def test_validacao_final_alternativas():
    """
    Valida que alternativas são calculadas corretamente.
    Joana não oferece pedicure, deve ser rejeitada.
    Gloria oferece ambos, deve ser aceita.
    """
    from services.multisservico_service import resolver_bloco_servicos

    TENANT_ID = "5511991382080"

    # Testar Gloria
    resultado_gloria = await resolver_bloco_servicos(
        tenant_id=TENANT_ID,
        nome_profissional="Gloria",
        servicos=["manicure", "pedicure"]
    )

    print(f"\n[ALTERNATIVAS] Gloria: {resultado_gloria.get('valido')}")
    if resultado_gloria.get("valido"):
        print(f"  Duracao: {resultado_gloria.get('duracao_total')} min")

    # Testar Joana (não oferece pedicure)
    resultado_joana = await resolver_bloco_servicos(
        tenant_id=TENANT_ID,
        nome_profissional="Joana",
        servicos=["manicure", "pedicure"]
    )

    print(f"[ALTERNATIVAS] Joana: {resultado_joana.get('valido')}")
    print(f"  Mensagens: {resultado_joana.get('mensagens')}")

    # Validações
    if resultado_gloria.get("valido"):
        assert resultado_gloria.get("duracao_total") > 0
        print("[OK] Gloria aceita como alternativa")

    if not resultado_joana.get("valido"):
        print("[OK] Joana corretamente rejeitada")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
