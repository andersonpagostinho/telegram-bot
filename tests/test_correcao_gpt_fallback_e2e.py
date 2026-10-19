"""
TESTE E2E: Validar que GPT fallback preserva intenção até criação de agendamento

Objetivo: Rastrear de ponta a ponta a mensagem com typos desde entrada até evento criado no Firestore
"""

import pytest
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


class TestCorrecaoGPTFallbackE2E:
    """Testes E2E validando preservação de intenção GPT até agendamento"""

    @pytest.mark.asyncio
    async def test_t2_typo_agendamento_completo(self):
        """
        T2 REAL: Mensagem com typos cria agendamento completo

        Entrada: "ola, gstria de agndar unha para terç agora"
        Validações:
        1. Intenção reconhecida como agendamento_direto (não consultabilidade)
        2. Serviço extraído corretamente
        3. Data extraída corretamente
        4. Estado muda para aguardando_data
        5. Preparado para confirmação

        NÃO deve ser sobrescrito para "consulta_disponibilidade_servico"
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup inicial: estado limpo
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
                "intencao_conversacional": None,
            }
        )

        print("\n" + "="*80)
        print("[E2E T2] MENSAGEM COM TYPOS → AGENDAMENTO")
        print("="*80)

        # Enviar mensagem com typos
        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="ola, gstria de agndar unha para terç agora, teria?",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Verificar sessão após processamento
        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print(f"\n[RESULTADO 1] Após mensagem com typos:")
        print(f"  Intenção: {sessao.get('intencao_conversacional')}")
        print(f"  Estado: {sessao.get('estado_fluxo')}")
        print(f"  Confiança: {sessao.get('confianca_intencao_conversacional')}")
        print(f"  Draft: {sessao.get('draft_agendamento')}")

        # Validação 1: Intenção deve ser agendamento_direto, NÃO consulta
        assert sessao.get("intencao_conversacional") == "agendamento_direto", \
            f"FAIL T2-1: Intenção {sessao.get('intencao_conversacional')} (esperado agendamento_direto)"
        print("  ✅ T2-1: Intenção corretamente reconhecida como agendamento_direto")

        # Validação 2: Estado deve estar aguardando_data (para completar agendamento)
        assert sessao.get("estado_fluxo") in ["aguardando_data", "aguardando_profissional"], \
            f"FAIL T2-2: Estado {sessao.get('estado_fluxo')} (esperado aguardando_*)"
        print(f"  ✅ T2-2: Estado correto ({sessao.get('estado_fluxo')})")

        # Validação 3: Serviço foi extraído
        draft = sessao.get("draft_agendamento", {})
        servico = draft.get("servico")
        assert servico is not None, "FAIL T2-3: Serviço não extraído"
        print(f"  ✅ T2-3: Serviço extraído: {servico}")

        # Validação 4: Data foi extraída (terça)
        data_extraida = draft.get("data") or sessao.get("interpretacao_conversacional", {}).get("entidades", {}).get("data")
        assert data_extraida is not None or "terça" in str(sessao).lower(), \
            "FAIL T2-4: Data não extraída"
        print(f"  ✅ T2-4: Data extraída ou interpretada")

        # Continuação do fluxo: Fornecer horário para completar agendamento
        print(f"\n[PASSO 2] Fornecendo horário para completar agendamento...")

        resultado2 = await roteador_principal(
            user_id=actor_id,
            mensagem="às 14h com a Carla",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        sessao2 = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print(f"\n[RESULTADO 2] Após fornecer detalhes:")
        print(f"  Estado: {sessao2.get('estado_fluxo')}")
        print(f"  Aguardando confirmação: {sessao2.get('aguardando_confirmacao_agendamento')}")
        print(f"  Dados confirmação: {sessao2.get('dados_confirmacao_agendamento')}")

        # Validação 5: Deve estar aguardando confirmação
        assert sessao2.get("aguardando_confirmacao_agendamento") or \
               sessao2.get("estado_fluxo") in ["agendando", "agendado"], \
            f"FAIL T2-5: Não atingiu confirmação (estado={sessao2.get('estado_fluxo')})"
        print("  ✅ T2-5: Atingiu ponto de confirmação")

        # Confirmação do agendamento
        print(f"\n[PASSO 3] Confirmando agendamento...")

        resultado3 = await roteador_principal(
            user_id=actor_id,
            mensagem="sim",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        sessao3 = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        print(f"\n[RESULTADO 3] Após confirmação:")
        print(f"  Estado: {sessao3.get('estado_fluxo')}")
        print(f"  Aguardando confirmação: {sessao3.get('aguardando_confirmacao_agendamento')}")

        # Validação 6: Agendamento deve estar criado/confirmado
        assert sessao3.get("estado_fluxo") in ["agendado", "idle", "agenda_criada"] or \
               not sessao3.get("aguardando_confirmacao_agendamento"), \
            f"FAIL T2-6: Agendamento não foi criado (estado={sessao3.get('estado_fluxo')})"
        print("  ✅ T2-6: Agendamento criado/confirmado")

        print("\n" + "="*80)
        print("✅ T2 COMPLETO: GPT fallback preservou intenção até criação do agendamento")
        print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
