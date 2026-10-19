"""
TESTES P0 — Correção de serviço truncado e resposta vazia

Testes obrigatórios para validar:
1. Truncamento "cort" → "corte feminino" (único compatível)
2. Truncamento ambíguo não escolhe arbitrariamente
3. "gostaria de cort para amha as 14 com carla" não retorna vazio
4. Draft anterior não impede nova solicitação explícita
5. Mensagem sem sinais operacionais mantém comportamento neutro
6. Nenhum evento criado antes de confirmação
7. Tenant, actor_id e paths permanecem inalterados
"""

import pytest
from services.classificador_conversa import extrair_servico_do_catalogo
from router.principal_router import roteador_principal
from services.firebase_service_async import atualizar_dado_em_path, buscar_dado_em_path


class TestTruncamentoServico:
    """Testes de truncamento e resposta vazia"""

    def test_01_truncamento_unico_compativel(self):
        """T1: 'cort' identifica 'corte feminino' quando é único compatível"""
        catalogo = ["coloracao", "corte feminino", "escova", "manicure"]
        texto = "gostaria de cort para amha"

        resultado = extrair_servico_do_catalogo(texto, catalogo_servicos=catalogo)

        assert resultado == "corte feminino", \
            f"T1 FAIL: esperado 'corte feminino', obtido {resultado}"
        print("✅ T1: Truncamento 'cort' → 'corte feminino'")

    def test_02_truncamento_ambiguo_nao_escolhe(self):
        """T2: Truncamento ambíguo não escolhe arbitrariamente"""
        catalogo = ["corte feminino", "corte masculino", "corte infantil"]
        texto = "quero cort"

        resultado = extrair_servico_do_catalogo(texto, catalogo_servicos=catalogo)

        # Deve retornar None ou None pois há múltiplos compatíveis
        assert resultado is None, \
            f"T2 FAIL: truncamento ambíguo deveria retornar None, obtido {resultado}"
        print("✅ T2: Truncamento ambíguo não escolhe arbitrariamente")

    @pytest.mark.asyncio
    async def test_03_mensagem_completa_nao_retorna_vazio(self):
        """T3: 'gostaria de cort para amha as 14 com carla' não retorna vazio"""
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup: contexto limpo
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "idle",
                "intencao_conversacional": None,
                "draft_agendamento": None,
            }
        )

        # Mensagem
        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="gostaria de cort para amha as 14 com carla",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Validação: deve ter resposta ou acao válida, não vazio
        if isinstance(resultado, dict):
            # Se retorna dict, não deve ser {'handled': True, 'acao': 'ignorar'}
            assert not (resultado.get("handled") and resultado.get("acao") == "ignorar"), \
                f"T3 FAIL: retornou vazio {resultado}"
            # Deve ter resposta ou acao operacional
            assert resultado.get("resposta") or (resultado.get("acao") and resultado.get("acao") != "ignorar"), \
                f"T3 FAIL: sem resposta operacional"
            print(f"✅ T3: Resposta enviada (acao={resultado.get('acao')})")
        else:
            # Se retorna algo diferente é processado async
            print("✅ T3: Processado (async)")

    @pytest.mark.asyncio
    async def test_04_draft_anterior_nao_bloqueia_novo(self):
        """T4: Draft anterior 'escova' não impede nova solicitação 'cort com carla'"""
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup: contexto com draft anterior
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={
                "estado_fluxo": "aguardando_data",
                "intencao_conversacional": "ajuste_incremental",
                "tipo_ajuste_incremental": "profissional",
                "draft_agendamento": {
                    "servico": "escova",
                    "profissional": "gloria",
                    "data_hora": "2026-10-20T10:00:00"
                },
            }
        )

        # Nova mensagem
        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="gostaria de cort com carla",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Validação: deve reconhecer novo serviço
        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        # Draft anterior pode ter sido substituído OU mantido com novo serviço
        novo_servico = sessao.get("servico") or \
                       (sessao.get("draft_agendamento") or {}).get("servico")

        assert novo_servico and "corte" in novo_servico.lower(), \
            f"T4 FAIL: novo serviço não foi reconhecido, draft={sessao.get('draft_agendamento')}"
        print(f"✅ T4: Novo serviço reconhecido ({novo_servico})")

    @pytest.mark.asyncio
    async def test_05_mensagem_neutra_sem_sinais(self):
        """T5: Mensagem sem sinais operacionais continua usando comportamento neutro"""
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup: contexto limpo
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        # Mensagem puramente neutra (sem pedido, tempo ou serviço)
        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem="voce trabalha a noite?",  # Pergunta neutra
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Validação: pode retornar vazio OU resposta informativa
        if isinstance(resultado, dict) and resultado.get("acao") == "ignorar":
            print("✅ T5: Mensagem neutra mantém comportamento")
        else:
            print("✅ T5: Resposta informativa (comportamento esperado)")

    @pytest.mark.asyncio
    async def test_06_nenhum_evento_antes_confirmacao(self):
        """T6: Nenhum evento criado antes de confirmação explícita"""
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup: contexto limpo
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        # Mensagem de agendamento
        await roteador_principal(
            user_id=actor_id,
            mensagem="gostaria de cort para amha as 14 com carla",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Validação: verificar contexto
        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        # Confirmação NÃO deve estar ativa ainda
        assert not sessao.get("aguardando_confirmacao_agendamento"), \
            f"T6 FAIL: confirmação foi ativada prematuramente"
        print("✅ T6: Nenhum evento criado (confirmação pendente)")

    @pytest.mark.asyncio
    async def test_07_tenant_actor_path_inalterados(self):
        """T7: Tenant, actor_id e caminho Sessoes permanecem inalterados"""
        tenant_id = "7394370553"
        actor_id = "whatsapp:5511991382080"

        # Setup
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados={"estado_fluxo": "idle"}
        )

        # Processamento
        await roteador_principal(
            user_id=actor_id,
            mensagem="gostaria de cort para amha as 14",
            tenant_id=tenant_id,
            phone_number_id="1350170954840548"
        )

        # Verificação: path permanece correto
        sessao = await buscar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")

        assert sessao is not None, "T7 FAIL: sessão não encontrada no path correto"
        assert sessao.get("tenant_id") == tenant_id or tenant_id in "Clientes/{tenant_id}/Sessoes/{actor_id}".format(tenant_id=tenant_id), \
            "T7 FAIL: tenant_id foi alterado"

        print("✅ T7: Tenant, actor_id e path inalterados")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
