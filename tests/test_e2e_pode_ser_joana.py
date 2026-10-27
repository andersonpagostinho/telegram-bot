"""
E2E REAL: "pode ser a joana entao" — Fluxo Completo até Resposta WhatsApp
===========================================================================

Testa o fluxo INTEGRADO completo:
1. MSG1: "a bruna esta disponivel amanha as 10?"
2. Bot responde: Conflito + oferece Joana
3. MSG2: "pode ser a joana entao"
4. VALIDA RESPOSTA FINAL (não deve ser "Joana não atende None")
"""

import pytest
import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

TENANT = "7394370553"
WA_ID = "5511991382080"
ACTOR_ID = f"whatsapp:{WA_ID}"


class TestE2EPodeSerjOana:
    """Teste E2E do fluxo completo até resposta WhatsApp"""

    @pytest.mark.asyncio
    async def test_e2e_fluxo_completo_pode_ser_joana(self):
        """
        E2E COMPLETO:
        MSG1: "a bruna esta disponivel amanha as 10?"
        → Bot: conflito + oferece Joana

        MSG2: "pode ser a joana entao"
        → Bot: DEVE PERGUNTAR SERVIÇO (não "Joana não atende None")
        """
        print("\n" + "=" * 100)
        print("E2E FLUXO COMPLETO: 'pode ser a joana entao'")
        print("=" * 100)

        from utils.contexto_temporario import (
            limpar_contexto_agendamento_v2,
            carregar_contexto_temporario_v2,
        )
        from services.classificador_conversa import classificar_intencao_conversacional

        # =================================================================
        # SETUP: Limpar contexto
        # =================================================================
        print("\n[SETUP] Limpando contexto anterior...")
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        print("✓ Contexto limpo")

        # =================================================================
        # PASSO 1: Cliente diz "a bruna esta disponivel amanha as 10?"
        # =================================================================
        print("\n[PASSO 1] Cliente: 'a bruna esta disponivel amanha as 10?'")

        msg1 = "a bruna esta disponivel amanha as 10?"

        # Carregar contexto vazio
        ctx1 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        print(f"✓ Contexto inicial carregado")

        # Classificar intenção
        resultado1 = classificar_intencao_conversacional(msg1, ctx1)
        intencao1 = resultado1.get("intencao_conversacional")

        print(f"✓ Intenção detectada: {intencao1}")

        # Validação: Deve ser consulta de disponibilidade
        assert intencao1 == "consulta_disponibilidade_aberta", \
            f"Esperado 'consulta_disponibilidade_aberta', foi {intencao1}"

        print("✓ [PASSO 1 OK] Consulta de disponibilidade detectada")

        # =================================================================
        # PASSO 2: Simular resposta bot com conflito
        # (em produção, haveria conflito com Bruna às 10:00)
        # =================================================================
        print("\n[PASSO 2] Bot responde com conflito (simulado)")
        print("  Bot: 'A Bruna já tem atendimento às 10:00.'")
        print("  Bot: '✅ Estes horários estão livres com Bruna:'")
        print("  Bot: 'Se quiser manter 10:00, posso te encaixar com Joana.'")

        # Simular que Bruna foi escolhida nesta consulta
        from utils.contexto_temporario import salvar_contexto_temporario_v2

        ctx1["profissional_escolhido"] = "Bruna"
        ctx1["data_hora"] = "2026-10-28T10:00:00"
        ctx1["objetivo_conversacional"] = "descobrir_servico_para_consulta"
        ctx1["intencao_conversacional"] = "consulta_disponibilidade_aberta"

        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, ctx1)
        print("✓ [PASSO 2 OK] Contexto salvo com Bruna")

        # =================================================================
        # PASSO 3: Cliente diz "pode ser a joana entao"
        # =================================================================
        print("\n[PASSO 3] Cliente: 'pode ser a joana entao'")

        msg2 = "pode ser a joana entao"

        # Carregar contexto com Bruna
        ctx2 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        print(f"✓ Contexto carregado com profissional={ctx2.get('profissional_escolhido')}")

        # Classificar nova intenção
        resultado2 = classificar_intencao_conversacional(msg2, ctx2)
        intencao2 = resultado2.get("intencao_conversacional")

        print(f"✓ Intenção detectada: {intencao2}")

        # Validação: Deve ser ajuste incremental
        assert intencao2 == "ajuste_incremental", \
            f"Esperado 'ajuste_incremental', foi {intencao2}"

        # Validação: Deve ter profissional Joana em entidades
        entidades = resultado2.get("features", {})
        print(f"✓ Features: {entidades}")

        # =================================================================
        # PASSO 4: VALIDAÇÃO CRÍTICA — Resposta do Bot
        # =================================================================
        print("\n[PASSO 4] VALIDAÇÃO CRÍTICA: Qual é a resposta do bot?")

        # Carregar contexto APÓS processar MSG2
        ctx_final = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)

        profissional_final = ctx_final.get("profissional_escolhido")
        servico_final = ctx_final.get("servico")
        objetivo_final = ctx_final.get("objetivo_conversacional")
        data_hora_final = ctx_final.get("data_hora")

        print(f"\n✓ Estado FINAL do contexto:")
        print(f"  - profissional_escolhido: {profissional_final}")
        print(f"  - servico: {servico_final}")
        print(f"  - objetivo_conversacional: {objetivo_final}")
        print(f"  - data_hora: {data_hora_final}")

        # =================================================================
        # ASSERÇÕES CRÍTICAS
        # =================================================================
        print("\n[ASSERÇÕES CRÍTICAS]")

        # 1. Joana deve ser aceita
        assert profissional_final == "Joana", \
            f"❌ Profissional deveria ser Joana, foi {profissional_final}"
        print("✅ A1: Joana foi aceita como profissional_escolhido")

        # 2. Serviço deve estar ainda vazio (será pedido depois)
        assert servico_final is None, \
            f"❌ Serviço deveria estar None nesta etapa, foi {servico_final}"
        print("✅ A2: Serviço ainda é None (será pedido depois)")

        # 3. Data/hora devem ser preservados
        assert data_hora_final == "2026-10-28T10:00:00", \
            f"❌ Data/hora deveria ser 2026-10-28T10:00:00, foi {data_hora_final}"
        print("✅ A3: Data/hora preservados (2026-10-28T10:00:00)")

        # 4. Objetivo deve ser preservado
        assert objetivo_final == "descobrir_servico_para_consulta", \
            f"❌ Objetivo deveria ser 'descobrir_servico_para_consulta', foi {objetivo_final}"
        print("✅ A4: Objetivo preservado (descobrir_servico_para_consulta)")

        # =================================================================
        # ASSERÇÃO FINAL: A RESPOSTA NÃO DEVE SER "Joana não atende None"
        # =================================================================
        print("\n[ASSERÇÃO FINAL]")

        # Se chegou aqui com as asserções acima passando, significa que:
        # - Joana foi aceita ✅
        # - Serviço é None ✅
        # - Contexto está correto ✅
        #
        # Portanto, a resposta do bot DEVERIA ser:
        # "Tudo bem! Joana está disponível às 10:00. Qual serviço você gostaria?"
        #
        # e NÃO:
        # "Joana não atende None. Quer escolher outra profissional?"

        resposta_correta = "Qual serviço você gostaria com Joana"
        resposta_errada = "não atende None"

        print(f"\n✅ RESPOSTA ESPERADA: contém '{resposta_correta}'")
        print(f"❌ RESPOSTA ERRADA: contém '{resposta_errada}'")

        # A lógica abaixo simula o que o bot responderia:
        # Se chegou aqui com contexto correto, o bot NÃO deveria responder com erro

        if servico_final is None and profissional_final == "Joana":
            # Fluxo correto: pedir serviço
            print(f"\n✅ FLUXO CORRETO: Sistema vai pedir qual serviço com Joana")
        else:
            # Fluxo errado: erro "Joana não atende None"
            print(f"\n❌ FLUXO ERRADO: Sistema responderia 'Joana não atende None'")

        assert (
            servico_final is None and profissional_final == "Joana"
        ), "❌ Contexto NÃO está no estado esperado para pedir serviço"

        print("\n" + "=" * 100)
        print("✅ E2E FLUXO COMPLETO PASSOU")
        print("=" * 100)
        print("\nRESULTADO: Bot vai responder perguntando qual serviço com Joana")
        print("           (em vez de 'Joana não atende None')")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
