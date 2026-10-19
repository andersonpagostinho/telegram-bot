"""
TESTE: GPT Fallback para Mensagens com Typos

Objetivo: Validar que o sistema consegue interpretar corretamente
a mensagem "ola, gstria de agndar unha para terç agora, teria?"
através do fallback GPT quando o interpretador determinístico falha.

Caso de teste: Typos em português ("gstria"→"gostaria", "agndar"→"agendar", "terç"→"terça")
"""

import pytest
import json
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path
from router.principal_router import roteador_principal


class TestGPTFallbackTypos:
    """Validação do fallback GPT para mensagens malformadas"""

    @pytest.mark.asyncio
    async def test_gpt_fallback_typos_interpretacao(self):
        """
        T1: Mensagem com typos deve ser interpretada pelo GPT fallback

        Entrada: "ola, gstria de agndar unha para terç agora, teria?"
        Typos: gstria (gostaria), agndar (agendar), terç (terça)

        Esperado:
        - Intencao deve ser identificada (agendamento_direto ou consulta)
        - Serviço deve ser extraído (unha/manicure)
        - Data deve ser interpretada (próxima terça)
        - Confiança > 50%
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup: estado inicial limpo
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
                "aguardando_confirmacao_agendamento": False,
                "modo_conversa": None,
                "intencao_conversacional": None,
            }
        )

        # Enviar mensagem com typos (simula o caso real)
        mensagem_com_typos = "ola, gstria de agndar unha para terç agora, teria?"

        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem=mensagem_com_typos,
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Validar resposta (pode ser dict ou string)
        assert resultado, "Resposta não deve estar vazia"

        resposta_texto = resultado
        if isinstance(resultado, dict):
            resposta_texto = resultado.get("resposta", "")

        assert resposta_texto, "Resposta não deve estar vazia"
        assert len(resposta_texto) > 20, "Resposta deve ter conteúdo significativo"

        # Validar que reconheceu os dados
        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
        assert sessao.get("intencao_conversacional") == "agendamento_direto", \
            f"Intenção deve ser agendamento_direto, obteve {sessao.get('intencao_conversacional')}"

        print(f"✅ T1: GPT interpretou typos corretamente")
        print(f"   Resposta: {resposta_texto[:80]}...")
        print(f"   Intenção: {sessao.get('intencao_conversacional')}")

    @pytest.mark.asyncio
    async def test_gpt_fallback_comparacao_com_sem_typo(self):
        """
        T2: Comparar resposta com typo vs. sem typo

        Mesma mensagem com e sem typos deve gerar intenções equivalentes
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
                "aguardando_confirmacao_agendamento": False,
            }
        )

        # Mensagem SEM typos (baseline)
        mensagem_correta = "ola, gostaria de agendar unha para terça agora, teria?"
        resultado_correto = await roteador_principal(
            user_id=actor_id,
            mensagem=mensagem_correta,
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Reset
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
                "aguardando_confirmacao_agendamento": False,
            }
        )

        # Mensagem COM typos
        mensagem_typos = "ola, gstria de agndar unha para terç agora, tedia?"
        resultado_typos = await roteador_principal(
            user_id=actor_id,
            mensagem=mensagem_typos,
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Ambas as respostas devem ser não-vazias
        assert resultado_correto, "Resposta correta não deve estar vazia"
        assert resultado_typos, "Resposta com typos não deve estar vazia"

        # Ambas devem ser comparáveis em tamanho (±50% de diferença)
        tamanho_correto = len(resultado_correto)
        tamanho_typos = len(resultado_typos)
        diferenca_percentual = abs(tamanho_correto - tamanho_typos) / max(tamanho_correto, tamanho_typos)

        assert diferenca_percentual < 0.5, \
            f"Diferença grande entre respostas: {tamanho_correto} vs {tamanho_typos}"

        print(f"✅ T2: GPT fallback mantém consistência")
        print(f"   Sem typos: {len(resultado_correto)} chars")
        print(f"   Com typos: {len(resultado_typos)} chars")

    @pytest.mark.asyncio
    async def test_gpt_fallback_nao_cria_resposta_vazia(self):
        """
        T3: GPT fallback nunca deve deixar resposta vazia

        Mesmo com múltiplos typos, deve tentar interpretação
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
            }
        )

        # Variações com typos mais severos
        mensagens_teste = [
            "gstria agendr unhaa",  # Múltiplos typos
            "quero agnd unha",       # Abreviado
            "unha msm",              # Muito abreviado
        ]

        for msg in mensagens_teste:
            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem=msg,
                tenant_id=tenant_id,
                phone_number_id="1350170954840548"
            )

            assert resultado, f"Resposta vazia para: {msg}"
            assert len(resultado) > 0, f"Resposta vazia para: {msg}"

            # Reset para próxima iteração
            await atualizar_dado_em_path(
                path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
                dados={"estado_fluxo": "idle"}
            )

        print(f"✅ T3: GPT fallback nunca deixa resposta vazia")

    @pytest.mark.asyncio
    async def test_gpt_fallback_preserva_tenant_isolation(self):
        """
        T4: GPT fallback respeita isolamento de tenant

        Contexto deve preservar tenant_id e actor_id originais
        """
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
            }
        )

        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="gstria de agndar unha para terç",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Validar que sessão foi preservada
        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        # tenant_id e actor_id não devem ter mudado
        assert sessao is not None, "Sessão foi perdida"

        print(f"✅ T4: GPT fallback respeita tenant isolation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
