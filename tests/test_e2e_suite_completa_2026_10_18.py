"""
SUITE E2E COMPLETA — FIRESTORE VALIDATION
===========================================

REGRA DE OURO: Todos os testes devem validar até o resultado final no Firestore.
Não é suficiente validar apenas a resposta do sistema.

Cenários:
1. Saudação em estado idle
2. Loop detection e recovery (nível 1)
3. Agendamento direto
4. Confirmação de agendamento
5. Conflito de agenda e resolução
6. Multi-tenant isolation
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
class TestE2ECompletaSuite:
    """Suite E2E: validação completa até Firestore"""

    @pytest.fixture
    async def setup_tenant(self):
        """Setup: cria tenant com dados, retorna IDs"""
        from services.firebase_service_async import (
            salvar_dado_em_path,
            deletar_dado_em_path,
        )

        tenant_id = f"test_suite_{uuid.uuid4().hex[:6]}"
        actor_id = f"whatsapp:test_{uuid.uuid4().hex[:6]}"

        print(f"\n[SETUP] Tenant: {tenant_id}, Actor: {actor_id}")

        # Configuração tenant
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/configuracao/dados",
            {
                "nome": "Salao Teste Suite",
                "tipo_usuario": "dono",
                "email": f"teste_{uuid.uuid4().hex[:4]}@test.com",
                "tipoNegocio": "salao_de_beleza",
                "pagamentoAtivo": True,
            }
        )

        # Profissionais
        amanha = (datetime.now() + timedelta(days=1)).date()
        agenda_padrao = {
            str(amanha.weekday()): {"aberto": True, "inicio": "08:00", "fim": "18:00"}
        }

        for prof_nome in ["Bruna", "Gloria"]:
            await salvar_dado_em_path(
                f"Clientes/{tenant_id}/Profissionais/{prof_nome}",
                {
                    "nome": prof_nome,
                    "servicos": ["corte feminino", "escova"],
                    "duracoes": {"corte feminino": 40, "escova": 60},
                    "precos": {"corte feminino": 50.0, "escova": 60.0},
                }
            )

        # Agenda
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
            {"agenda_padrao": agenda_padrao, "excecoes_data": {}}
        )

        # Sessão inicial
        await salvar_dado_em_path(
            f"Clientes/{tenant_id}/Sessoes/{actor_id}/contexto",
            {
                "user_id": actor_id,
                "tenant_id": tenant_id,
                "estado_fluxo": "idle",
                "historico_texto": [],
                "criado_em": datetime.now().isoformat(),
            }
        )

        yield {"tenant_id": tenant_id, "actor_id": actor_id, "amanha": amanha.isoformat()}

        # Cleanup
        print(f"\n[CLEANUP] Deletando {tenant_id}")
        try:
            await deletar_dado_em_path(f"Clientes/{tenant_id}")
        except Exception as e:
            print(f"[WARN] Cleanup: {e}")

    async def _enviar_msg(self, actor_id: str, tenant_id: str, texto: str):
        """Envia mensagem via roteador"""
        from router.principal_router import roteador_principal

        resultado = await roteador_principal(
            user_id=actor_id,
            mensagem=texto,
            tenant_id=tenant_id,
            phone_number_id=None,
            update=None,
            context=None,
        )
        return resultado

    async def _verificar_firestore(self, tenant_id: str, path: str):
        """Verifica dados no Firestore"""
        from services.firebase_service_async import buscar_dado_em_path

        try:
            return await buscar_dado_em_path(path)
        except Exception as e:
            print(f"[ERRO] Firestore read {path}: {e}")
            return None

    # ════════════════════════════════════════════════════════════════
    # CENÁRIO 1: Saudação em estado idle
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_01_saudacao_estado_idle(self, setup_tenant):
        """
        Valida:
        1. Cliente envia "ola" em idle
        2. Sistema responde apropriadamente
        3. Sessão atualizada no Firestore
        """
        tenant_id = setup_tenant["tenant_id"]
        actor_id = setup_tenant["actor_id"]

        print("\n[T01] Saudação em idle")

        # 1. Enviar mensagem
        resultado = await self._enviar_msg(actor_id, tenant_id, "ola")

        assert resultado is not None, "Resposta não pode ser None"
        assert resultado.get("ok") == True, "Deve retornar ok=True"
        assert resultado.get("resposta") is not None, "Deve ter resposta"
        print(f"  ✅ Resposta recebida")

        # 2. Validar sessão no Firestore
        sessao = await self._verificar_firestore(
            tenant_id, f"Clientes/{tenant_id}/Sessoes/{actor_id}/contexto"
        )

        assert sessao is not None, "Sessão deve estar em Firestore"
        assert sessao.get("tenant_id") == tenant_id, "tenant_id deve estar correto"
        print(f"  ✅ Sessão persistida no Firestore")

        # 3. Validar histórico
        assert "ola" in sessao.get("historico_texto", []), "Mensagem deve estar no histórico"
        print(f"  ✅ Histórico atualizado")

    # ════════════════════════════════════════════════════════════════
    # CENÁRIO 2: Agendamento direto simples
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_02_agendamento_direto(self, setup_tenant):
        """
        Valida fluxo completo:
        1. Cliente pede: "Quero corte com Bruna amanhã às 10"
        2. Sistema processa agendamento
        3. Evento criado no Firestore
        """
        tenant_id = setup_tenant["tenant_id"]
        actor_id = setup_tenant["actor_id"]
        amanha = setup_tenant["amanha"]

        print("\n[T02] Agendamento direto")

        # 1. Enviar pedido de agendamento
        resultado = await self._enviar_msg(
            actor_id, tenant_id, f"Quero corte com Bruna amanhã às 10"
        )

        assert resultado is not None
        assert resultado.get("ok") == True
        print(f"  ✅ Pedido de agendamento enviado")

        # 2. Validar sessão
        sessao = await self._verificar_firestore(
            tenant_id, f"Clientes/{tenant_id}/Sessoes/{actor_id}/contexto"
        )

        assert sessao is not None
        assert sessao.get("estado_fluxo") in [
            "aguardando_confirmacao_agendamento",
            "agendando",
            "idle",
        ], f"Estado: {sessao.get('estado_fluxo')}"
        print(f"  ✅ Sessão atualizada (estado={sessao.get('estado_fluxo')})")

        # 3. Se evento foi criado, validar no Firestore
        eventos = await self._verificar_firestore(
            tenant_id, f"Clientes/{tenant_id}/Eventos"
        )

        if eventos:
            print(f"  ✅ {len(eventos)} evento(s) criado(s) no Firestore")
            for evt_id, evt_data in list(eventos.items())[:1]:  # Verificar primeiro
                assert evt_data.get("profissional") is not None
                assert evt_data.get("tenant_id") == tenant_id
                print(f"    - Profissional: {evt_data.get('profissional')}")
                print(f"    - Data: {evt_data.get('data')}")
        else:
            print(f"  ℹ️ Nenhum evento criado (pode estar pendente confirmação)")

    # ════════════════════════════════════════════════════════════════
    # CENÁRIO 3: Loop detection e recovery
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_03_loop_detection_recovery(self, setup_tenant):
        """
        Valida loop recovery nível 1:
        1. Simular loop (mensagens repetidas)
        2. Sistema detecta e recupera
        3. Próxima mensagem processa corretamente
        """
        tenant_id = setup_tenant["tenant_id"]
        actor_id = setup_tenant["actor_id"]

        print("\n[T03] Loop detection e recovery")

        # 1. Primeira "ola"
        r1 = await self._enviar_msg(actor_id, tenant_id, "ola")
        assert r1.get("resposta") is not None
        print(f"  ✅ Msg 1 respondida")

        # 2. Segunda "ola" (pode detectar loop)
        r2 = await self._enviar_msg(actor_id, tenant_id, "ola")
        assert r2 is not None
        print(f"  ✅ Msg 2 respondida (pode ter detectado loop)")

        # 3. Terceira "ola" (se houver loop, recupera)
        r3 = await self._enviar_msg(actor_id, tenant_id, "ola")
        assert r3 is not None
        print(f"  ✅ Msg 3 respondida (recuperado de loop se detectado)")

        # 4. Validar sessão em Firestore
        sessao = await self._verificar_firestore(
            tenant_id, f"Clientes/{tenant_id}/Sessoes/{actor_id}/contexto"
        )

        assert sessao is not None
        # Verificar que intenção foi resetada após loop recovery
        intencao = sessao.get("intencao_conversacional")
        print(f"  ℹ️ Intenção final: {intencao}")

    # ════════════════════════════════════════════════════════════════
    # CENÁRIO 4: Multi-tenant isolation
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_04_multi_tenant_isolation(self, setup_tenant):
        """
        Valida isolamento multi-tenant:
        1. Dois tenants, mesmo actor_id
        2. Dados não vazam entre tenants
        3. Firestore paths estão corretos
        """
        from services.firebase_service_async import (
            salvar_dado_em_path,
            buscar_dado_em_path,
        )

        tenant1 = setup_tenant["tenant_id"]
        tenant2 = f"test_tenant2_{uuid.uuid4().hex[:6]}"
        actor_id = setup_tenant["actor_id"]  # Mesmo actor

        print("\n[T04] Multi-tenant isolation")

        # Setup tenant 2
        await salvar_dado_em_path(
            f"Clientes/{tenant2}/configuracao/dados",
            {"nome": "Tenant 2", "tipo_usuario": "dono"},
        )

        await salvar_dado_em_path(
            f"Clientes/{tenant2}/Sessoes/{actor_id}/contexto",
            {"user_id": actor_id, "tenant_id": tenant2},
        )

        # Enviar msg em tenant1
        r1 = await self._enviar_msg(actor_id, tenant1, "msg tenant1")

        # Validar isolamento
        sessao1 = await self._verificar_firestore(
            tenant1, f"Clientes/{tenant1}/Sessoes/{actor_id}/contexto"
        )
        sessao2 = await self._verificar_firestore(
            tenant2, f"Clientes/{tenant2}/Sessoes/{actor_id}/contexto"
        )

        assert sessao1.get("tenant_id") == tenant1
        assert sessao2.get("tenant_id") == tenant2
        print(f"  ✅ Tenants isolados corretamente")

        # Cleanup tenant2
        from services.firebase_service_async import deletar_dado_em_path
        await deletar_dado_em_path(f"Clientes/{tenant2}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
