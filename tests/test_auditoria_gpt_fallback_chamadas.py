"""
AUDITORIA: Verificar chamadas ao GPT fallback - Deve ser chamado APENAS uma vez

Objetivo:
1. Validar que GPT não é chamado para mensagens já interpretadas deterministically
2. Validar que GPT é chamado APENAS UMA VEZ para mensagens malformadas
3. Identificar se há sobrescrita desnecessária de class_intencao
4. Verificar se classificador determinístico pode vir APÓS GPT
"""

import pytest
from unittest.mock import patch, AsyncMock
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


class TestAuditoriaGPTCallCount:
    """Auditoria de contagem de chamadas ao GPT"""

    @pytest.mark.asyncio
    async def test_01_mensagem_valida_deterministica_sem_gpt(self):
        """
        T1: Mensagem válida reconhecida deterministically
        NÃO deve chamar GPT fallback em nenhum ponto

        Entrada: "Quero agendar corte feminino para terça-feira às 14h"
        Esperado: 0 chamadas ao GPT (todos os sinais presentes)
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        with patch('services.gpt_service.interpretar_linguagem_operacional_gpt',
                   new_callable=AsyncMock) as mock_gpt:

            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="Quero agendar corte feminino para terça-feira às 14h",
                tenant_id=tenant_id,
                phone_number_id="1350170954840548"
            )

            # GPT NÃO deve ser chamado para mensagem válida
            call_count = mock_gpt.call_count
            assert call_count == 0, f"T1 FAIL: GPT chamado {call_count} vezes (esperado 0)"
            print(f"✅ T1: Mensagem deterministica NÃO acionou GPT ({call_count} chamadas)")

    @pytest.mark.asyncio
    async def test_02_mensagem_typos_apenas_uma_chamada_gpt(self):
        """
        T2: Mensagem com typos deve chamar GPT apenas UMA VEZ

        Entrada: "ola, gstria de agndar unha para terç agora"
        Esperado: 1 chamada ao GPT (máximo)
        Não esperado: 2+ chamadas (reclassificação após GPT)
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        with patch('services.gpt_service.interpretar_linguagem_operacional_gpt',
                   new_callable=AsyncMock) as mock_gpt:

            # Configure o mock para retornar interpretação válida
            mock_gpt.return_value = {
                "intencao": "agendamento_direto",
                "tipo_ajuste": "data",
                "entidades": {"servico": "unha", "data": "terça-feira"},
                "confianca": 85
            }

            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="ola, gstria de agndar unha para terç agora, tedia?",
                tenant_id=tenant_id,
                phone_number_id="1350170954840548"
            )

            # GPT deve ser chamado, mas apenas UMA VEZ
            call_count = mock_gpt.call_count
            assert call_count <= 1, f"T2 FAIL: GPT chamado {call_count} vezes (esperado <=1)"
            assert call_count >= 1, f"T2 FAIL: GPT NÃO foi chamado (esperado >=1)"

            print(f"✅ T2: GPT fallback acionado {call_count} vez(es) para typos")

    @pytest.mark.asyncio
    async def test_03_confirmacao_pendente_nao_chama_gpt_fallback(self):
        """
        T3: Quando há confirmação pendente, NÃO deve chamar GPT fallback

        Entrada: Confirmação ativa + mensagem com typos
        Esperado: 0 chamadas ao GPT (fluxo protegido)
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup: confirmação pendente
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "agendando",
                "aguardando_confirmacao_agendamento": True,
                "dados_confirmacao_agendamento": {
                    "servico": "corte feminino",
                    "profissional": "Carla",
                    "data_hora": "2026-10-21T14:00:00"
                }
            }
        )

        with patch('services.gpt_service.interpretar_linguagem_operacional_gpt',
                   new_callable=AsyncMock) as mock_gpt:

            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="gstria de mudar",  # typo + alteração
                tenant_id=tenant_id,
                phone_number_id="1350170954840548"
            )

            # GPT NÃO deve ser chamado quando há confirmação pendente
            call_count = mock_gpt.call_count
            assert call_count == 0, f"T3 FAIL: GPT chamado {call_count} vezes (esperado 0 em confirmação)"
            print(f"✅ T3: Confirmação pendente protegida - GPT NÃO acionado")

    @pytest.mark.asyncio
    async def test_04_gpt_retorna_indefinida_nao_continua(self):
        """
        T4: Se GPT retorna "indefinida", não deve continuar como se fosse sucesso

        Entrada: Mensagem muito ambígua
        Esperado: GPT acionado, retorna indefinida, sistema não cria evento
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        with patch('services.gpt_service.interpretar_linguagem_operacional_gpt',
                   new_callable=AsyncMock) as mock_gpt:

            # Configure o mock para retornar indefinida
            mock_gpt.return_value = {
                "intencao": "indefinida",
                "tipo_ajuste": None,
                "entidades": {},
                "confianca": 20
            }

            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="blablabla xyz",  # Mensagem sem sentido
                tenant_id=tenant_id,
                phone_number_id="1350170954840548"
            )

            # Sistema deve retornar erro gracioso, não criar evento
            assert resultado, "Resposta não deve estar vazia"

            # Verificar que não criou agendamento
            sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
            assert sessao.get("estado_fluxo") != "agendando", \
                "T4 FAIL: Não deveria estar agendando após GPT indefinida"

            print(f"✅ T4: GPT indefinida retorna graciosamente sem criar evento")

    @pytest.mark.asyncio
    async def test_05_multiplas_mensagens_nao_reutiliza_gpt(self):
        """
        T5: Cada nova mensagem reavalia deterministically primeiro

        Não esperado: Sistema reutiliza resultado GPT anterior
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        # Mensagem 1: Com typos
        resultado1 = await roteador_principal(
            user_id=actor_id,
            mensagem="gstria de agndar unha",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Mensagem 2: Válida (sem typos)
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}  # Reset
        )

        with patch('services.gpt_service.interpretar_linguagem_operacional_gpt',
                   new_callable=AsyncMock) as mock_gpt:

            resultado2 = await roteador_principal(
                user_id=actor_id,
                mensagem="Quero corte feminino para terça às 14h",
                tenant_id=tenant_id,
                phone_number_id="1350170954840548"
            )

            # Mensagem 2 é válida → GPT NÃO deve ser chamado
            call_count = mock_gpt.call_count
            assert call_count == 0, f"T5 FAIL: GPT chamado {call_count} vezes para mensagem válida"

            print(f"✅ T5: Múltiplas mensagens reavaliadas independentemente")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
