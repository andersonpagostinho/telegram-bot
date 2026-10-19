"""
E2E Teste Firebase Real: Cliente NOVO, Pergunta sobre PROFISSIONAL ESPECÍFICO

Entrada: "sabe se a bruna está disponível amanhã às 10?"

Esperado:
- Sistema detecta profissional (Bruna) e data/hora (amanhã às 10)
- Pode ser interpretado como consulta pura sobre disponibilidade específica
- Deveria responder com horários de Bruna OU confirmar disponibilidade
"""

import pytest
import time

E2E_TENANT_ID = "7394370553"


@pytest.mark.asyncio
async def test_e2e_firebase_real_profissional_especifico():
    """
    E2E Firebase Real: Cliente novo pergunta sobre profissional específico.

    Entrada: "sabe se a bruna está disponível amanhã às 10?"

    Esperado: Sistema responde apropriadamente (lista horários, confirma, pede serviço, etc)
    """
    from router.principal_router import roteador_principal
    from utils.contexto_temporario import carregar_contexto_temporario

    # Novo user_id único
    timestamp_ms = int(time.time() * 1000)
    user_id_novo = f"551199{timestamp_ms % 10000000:07d}"

    print("\n" + "="*90)
    print("E2E FIREBASE REAL — Pergunta Sobre Profissional Específico")
    print("="*90)

    print(f"\n[SETUP]")
    print(f"  Tenant: {E2E_TENANT_ID}")
    print(f"  User ID novo: {user_id_novo}")
    print(f"  Entrada: 'sabe se a bruna está disponível amanhã às 10?'")

    # Validar contexto vazio
    ctx_inicial = await carregar_contexto_temporario(
        E2E_TENANT_ID, user_id_novo
    ) or {}

    print(f"\n[PRÉ-TESTE]")
    print(f"  Contexto vazio? {len(ctx_inicial) == 0}")
    assert len(ctx_inicial) == 0, "Contexto deve estar vazio para novo cliente"

    # ============================================================
    # TESTE: Enviar pergunta sobre profissional específico
    # ============================================================
    print(f"\n[ENTRADA]")
    print(f'  "sabe se a bruna está disponível amanhã às 10?"')

    resposta = await roteador_principal(
        user_id=user_id_novo,
        mensagem="sabe se a bruna está disponível amanhã às 10?",
        tenant_id=E2E_TENANT_ID,
        context=None,
    )

    assert isinstance(resposta, dict), f"Esperava dict, obteve: {type(resposta)}"
    resposta_texto = resposta.get("resposta", "")

    print(f"\n[RESPOSTA]")
    print(f"─" * 90)
    print(resposta_texto)
    print(f"─" * 90)

    # ============================================================
    # ANÁLISE
    # ============================================================
    print(f"\n[ANÁLISE]")

    # 1. Detectou Bruna?
    tem_bruna = "bruna" in resposta_texto.lower()
    print(f"  Menciona Bruna: {tem_bruna}")

    # 2. Detectou data/hora?
    tem_data_hora = "10:00" in resposta_texto or "10h" in resposta_texto or "amanhã" in resposta_texto.lower()
    print(f"  Menciona data/hora: {tem_data_hora}")

    # 3. Sistema perguntou qual serviço?
    tem_pergunta_servico = "serviço" in resposta_texto.lower() or "qual" in resposta_texto.lower()
    print(f"  Pergunta qual serviço: {tem_pergunta_servico}")

    # 4. Confirmou disponibilidade?
    tem_confirmacao = "disponível" in resposta_texto.lower() or "temos" in resposta_texto.lower()
    print(f"  Confirma/menciona disponibilidade: {tem_confirmacao}")

    # 5. Não reutilizou confirmacao anterior
    tem_reapresentacao = "só confirmando" in resposta_texto.lower()
    assert not tem_reapresentacao, "Não deveria reapresentar confirmacao (não há anterior)"
    print(f"  NÃO reutilizou confirmacao anterior: ✅")

    # ============================================================
    # CONTEXTO PÓS-RESPOSTA
    # ============================================================
    print(f"\n[CONTEXTO PÓS-RESPOSTA]")
    ctx_apos = await carregar_contexto_temporario(
        E2E_TENANT_ID, user_id_novo
    ) or {}

    campos = ["intencao_conversacional", "estado_fluxo", "draft_agendamento"]
    for campo in campos:
        valor = ctx_apos.get(campo)
        if valor:
            print(f"  {campo}: {valor}")

    # Validação crítica
    if ctx_apos.get("aguardando_confirmacao_agendamento"):
        servico = ctx_apos.get("servico")
        assert servico is not None, "Não deveria ter confirmacao com servico=None"
        print(f"  ✅ Se tem confirmacao: serviço é válido")

    print(f"\n" + "="*90)
    print("✅ TESTE PASSOU")
    print("="*90)

    return {
        "entrada": "sabe se a bruna está disponível amanhã às 10?",
        "resposta": resposta_texto,
        "contexto": ctx_apos
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
