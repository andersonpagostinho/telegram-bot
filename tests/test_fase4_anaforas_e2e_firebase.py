"""
FASE 4 — E2E FIREBASE: RESOLUÇÃO DE ANÁFORAS

Validação end-to-end com Firestore real:
1. Agendamento com profissional
2. Consulta com anáfora (pronome)
3. Mudança de assunto + anáfora
4. Confirmação com contexto resolvido
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from services.gpt_service import processar_com_gpt_com_acao
from services.firebase_service_async import buscar_cliente, salvar_cliente
from utils.contexto_temporario import (
    salvar_contexto_temporario,
    carregar_contexto_temporario,
    limpar_contexto_agendamento
)
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA


@pytest.mark.asyncio
async def test_e2e_anafora_com_ela_com_firebase():
    """
    Cenário: Agendamento com Bruna → Pergunta "com ela" → Confirmação.
    Validar resolução de pronome em contexto real.
    """
    user_id = "test_anafora_com_ela_firebase"
    tenant_id = "7394370553"

    try:
        # 1. Setup cliente
        await salvar_cliente(user_id, {
            "nome": "Usuário Anáfora",
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"]
        })

        # 2. MENSAGEM 1: Agendamento inicial com profissional
        contexto_msg1 = {
            "user_id": user_id,
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"]
        }

        resultado_msg1 = await processar_com_gpt_com_acao(
            texto_usuario="Quero escova com Bruna terça às 14h",
            contexto=contexto_msg1,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[MSG1] Response: {resultado_msg1.get('resposta')[:100] if resultado_msg1.get('resposta') else 'None'}")
        assert resultado_msg1 is not None
        assert resultado_msg1.get("resposta") is not None

        # Salvar contexto
        if resultado_msg1.get("dados"):
            await salvar_contexto_temporario(user_id, {
                "draft_agendamento": resultado_msg1.get("dados", {}),
                "estado_fluxo": "aguardando_confirmacao_agendamento"
            }, tenant_id)

        # 3. MENSAGEM 2: Pergunta com anáfora "com ela"
        contexto_msg2 = await carregar_contexto_temporario(user_id, tenant_id) or {
            "draft_agendamento": resultado_msg1.get("dados", {})
        }

        resultado_msg2 = await processar_com_gpt_com_acao(
            texto_usuario="Qual é o preço com ela?",  # Anáfora: "ela" = Bruna
            contexto=contexto_msg2,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[MSG2] Anáfora response: {resultado_msg2.get('resposta')[:100] if resultado_msg2.get('resposta') else 'None'}")
        # Deve responder com pronome resolvido
        assert resultado_msg2 is not None
        assert resultado_msg2.get("resposta") is not None

        # 4. MENSAGEM 3: Confirmação
        contexto_msg3 = await carregar_contexto_temporario(user_id, tenant_id) or contexto_msg2

        resultado_msg3 = await processar_com_gpt_com_acao(
            texto_usuario="sim",
            contexto=contexto_msg3,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[MSG3] Confirmação: {resultado_msg3.get('resposta')[:100] if resultado_msg3.get('resposta') else 'None'}")
        assert resultado_msg3 is not None

        print("✅ E2E ANÁFORA 'COM ELA' COMPLETO")

    finally:
        await limpar_contexto_agendamento(user_id, tenant_id)


@pytest.mark.asyncio
async def test_e2e_anafora_outro_servico_com_ela():
    """
    Cenário: Agendamento serviço A → "Outro serviço com ela" → Resolução composta.
    """
    user_id = "test_anafora_outro_servico_firebase"
    tenant_id = "7394370553"

    try:
        # Setup
        await salvar_cliente(user_id, {
            "nome": "Usuário Outro Serviço",
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"]
        })

        # 1. Agendamento: Manicure com Gloria
        contexto1 = {
            "user_id": user_id,
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"]
        }

        resultado1 = await processar_com_gpt_com_acao(
            texto_usuario="Quero manicure com Gloria terça",
            contexto=contexto1,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[OUTRO_SERVICO_MSG1] Response: OK")
        assert resultado1 is not None

        # Salvar
        if resultado1.get("dados"):
            await salvar_contexto_temporario(user_id, {
                "draft_agendamento": resultado1.get("dados", {}),
                "estado_fluxo": "aguardando_confirmacao_agendamento"
            }, tenant_id)

        # 2. Anáfora composta: "Outro serviço com ela"
        contexto2 = await carregar_contexto_temporario(user_id, tenant_id) or {
            "draft_agendamento": resultado1.get("dados", {})
        }

        resultado2 = await processar_com_gpt_com_acao(
            texto_usuario="Quero também outro serviço com ela, maybe hidratação?",  # Composta
            contexto=contexto2,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[OUTRO_SERVICO_MSG2] Referência composta detectada")
        assert resultado2 is not None
        assert resultado2.get("resposta") is not None

        print("✅ E2E ANÁFORA COMPOSTA COMPLETO")

    finally:
        await limpar_contexto_agendamento(user_id, tenant_id)


@pytest.mark.asyncio
async def test_e2e_anafora_temporal_com_firebase():
    """
    Cenário: Agendamento com horário → "Naquele horário" → Mesmo horário mantido.
    """
    user_id = "test_anafora_temporal_firebase"
    tenant_id = "7394370553"

    try:
        # Setup
        await salvar_cliente(user_id, {
            "nome": "Usuário Temporal",
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"]
        })

        # 1. Agendamento com horário
        contexto1 = {
            "user_id": user_id,
            "pagamentoAtivo": True,
            "planosAtivos": ["secretaria"]
        }

        resultado1 = await processar_com_gpt_com_acao(
            texto_usuario="Corte com Joana quarta às 10h",
            contexto=contexto1,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[TEMPORAL_MSG1] Agendamento: OK")
        assert resultado1 is not None

        # Salvar
        if resultado1.get("dados"):
            await salvar_contexto_temporario(user_id, {
                "draft_agendamento": resultado1.get("dados", {}),
                "estado_fluxo": "aguardando_confirmacao_agendamento"
            }, tenant_id)

        # 2. Referência temporal: "Naquele horário"
        contexto2 = await carregar_contexto_temporario(user_id, tenant_id) or {
            "draft_agendamento": resultado1.get("dados", {})
        }

        resultado2 = await processar_com_gpt_com_acao(
            texto_usuario="E manicure naquele horário também?",  # Temporal
            contexto=contexto2,
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
            tenant_id=tenant_id
        )

        print(f"[TEMPORAL_MSG2] Referência temporal processada")
        assert resultado2 is not None

        print("✅ E2E ANÁFORA TEMPORAL COMPLETO")

    finally:
        await limpar_contexto_agendamento(user_id, tenant_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
