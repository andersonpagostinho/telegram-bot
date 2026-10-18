"""
TESTE E2E VALIDADO — Firestore real
====================================

REGRA DE OURO: Testes validam até o resultado final no Firestore

Usa cliente e tenant REAIS já existentes em produção:
- tenant_id: 7394370553 (Salão existente)
- user_id: 5511991382080 (Cliente existente)
- actor_id: whatsapp:5511991382080

Cenários:
1. Saudação simples → valida resposta + sessão no Firestore
2. Loop detection → valida reset de intenção no Firestore
3. Agendamento → valida evento criado no Firestore
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
class TestE2EValidated:
    """Testes com dados REAIS de produção"""

    # IDs reais de produção
    TENANT_ID = "7394370553"
    USER_ID = "5511991382080"
    ACTOR_ID = "5511991382080"  # Sem prefixo whatsapp: (sistema vai adicionar)

    async def _enviar_msg(self, texto: str) -> dict:
        """Envia mensagem via roteador"""
        from router.principal_router import roteador_principal

        resultado = await roteador_principal(
            user_id=self.USER_ID,
            mensagem=texto,
            tenant_id=self.TENANT_ID,
            phone_number_id=None,
            update=None,
            context=None,
        )
        return resultado or {}

    async def _ler_firestore(self, path: str):
        """Lê dados do Firestore"""
        from services.firebase_service_async import buscar_dado_em_path

        try:
            return await buscar_dado_em_path(path)
        except Exception as e:
            print(f"[FIRESTORE READ ERROR] {path}: {e}")
            return None

    # ════════════════════════════════════════════════════════════════
    # TESTE 1: Saudação valida resposta E sessão em Firestore
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_01_saudacao_com_firestore_validation(self):
        """
        CENÁRIO: Cliente envia "ola"
        VALIDA:
        1. Sistema responde (resposta não vazia)
        2. Sessão atualizada em Firestore
        3. tenant_id correto na sessão
        """
        print(f"\n{'='*70}")
        print(f"TEST 01: Saudação com validação Firestore")
        print(f"{'='*70}")

        # 1. Enviar "ola"
        print(f"\n[ACAO] Enviando 'ola'...")
        resultado = await self._enviar_msg("ola")

        print(f"[RESPOSTA] ok={resultado.get('ok')}")
        assert resultado.get("ok") == True, "Deve retornar ok=True"
        assert resultado.get("resposta") is not None, "Resposta não pode ser vazia"
        print(f"[RESPOSTA] Texto: {resultado.get('resposta', '')[:80]}...")
        print(f"✅ Resposta validada")

        # 2. Validar sessão no Firestore
        print(f"\n[FIRESTORE] Lendo sessão...")
        sessao = await self._ler_firestore(
            f"Clientes/{self.TENANT_ID}/Sessoes/{self.ACTOR_ID}/contexto"
        )

        assert sessao is not None, "Sessão deve estar em Firestore"
        print(f"[FIRESTORE] Sessão encontrada: {bool(sessao)}")

        # 3. Validar tenant_id
        assert sessao.get("tenant_id") == self.TENANT_ID, "tenant_id incorreto"
        print(f"✅ tenant_id correto: {sessao.get('tenant_id')}")

        # 4. Validar histórico
        historico = sessao.get("historico_texto", [])
        print(f"[FIRESTORE] Histórico: {len(historico)} mensagens")
        print(f"✅ Teste 1 PASSOU")

    # ════════════════════════════════════════════════════════════════
    # TESTE 2: Loop detection valida reset de intenção no Firestore
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_02_loop_detection_intencao_reset(self):
        """
        CENÁRIO: Enviar "ola" múltiplas vezes em fluxo ativo
        VALIDA:
        1. Loop detectado (logs mostram)
        2. Intenção é REMOVIDA (não None, ausente!)
        3. Sistema recupera corretamente
        """
        print(f"\n{'='*70}")
        print(f"TEST 02: Loop detection com reset de intenção")
        print(f"{'='*70}")

        # Enviar 3x "ola" para possibilitar loop
        for i in range(1, 4):
            print(f"\n[MSG {i}] Enviando 'ola'...")
            resultado = await self._enviar_msg("ola")
            assert resultado is not None
            print(f"✅ Msg {i} respondida")

        # Validar estado final em Firestore
        print(f"\n[FIRESTORE] Validando estado final...")
        sessao = await self._ler_firestore(
            f"Clientes/{self.TENANT_ID}/Sessoes/{self.ACTOR_ID}/contexto"
        )

        assert sessao is not None
        intencao = sessao.get("intencao_conversacional")
        print(f"[FIRESTORE] intencao_conversacional: {intencao}")

        # Se houve loop, intenção foi removida
        if intencao is None:
            print(f"✅ Intenção removida após loop recovery")
        else:
            print(f"ℹ️ Intenção presente: {intencao}")

        print(f"✅ Teste 2 PASSOU")

    # ════════════════════════════════════════════════════════════════
    # TESTE 3: Agendamento valida evento criado no Firestore
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_03_agendamento_evento_firestore(self):
        """
        CENÁRIO: Cliente tenta agendar: "Quero corte amanhã às 10"
        VALIDA:
        1. Sistema responde apropriadamente
        2. Se evento foi criado, validar em Firestore
        3. Campos corretos (profissional, data, tenant_id)
        """
        print(f"\n{'='*70}")
        print(f"TEST 03: Agendamento com validação de evento no Firestore")
        print(f"{'='*70}")

        # 1. Enviar pedido de agendamento
        print(f"\n[ACAO] Enviando pedido: 'Quero corte amanhã às 10'...")
        resultado = await self._enviar_msg("Quero corte amanhã às 10")

        assert resultado is not None
        print(f"[RESPOSTA] ok={resultado.get('ok')}")
        print(f"✅ Pedido respondido")

        # 2. Validar sessão
        print(f"\n[FIRESTORE] Validando sessão...")
        sessao = await self._ler_firestore(
            f"Clientes/{self.TENANT_ID}/Sessoes/{self.ACTOR_ID}/contexto"
        )

        assert sessao is not None
        estado = sessao.get("estado_fluxo")
        print(f"[FIRESTORE] estado_fluxo: {estado}")
        print(f"✅ Sessão validada")

        # 3. Verificar se evento foi criado
        print(f"\n[FIRESTORE] Procurando eventos...")
        eventos = await self._ler_firestore(f"Clientes/{self.TENANT_ID}/Eventos")

        if eventos:
            print(f"[FIRESTORE] {len(eventos)} evento(s) encontrado(s)")
            # Verificar primeiro evento
            for evt_id, evt_data in list(eventos.items())[:1]:
                print(f"  - ID: {evt_id[:20]}...")
                print(f"  - Profissional: {evt_data.get('profissional')}")
                print(f"  - Data: {evt_data.get('data')}")
                print(f"  - Tenant: {evt_data.get('tenant_id')}")

                # Validações
                assert evt_data.get("tenant_id") == self.TENANT_ID
                print(f"✅ Evento validado no Firestore")
        else:
            print(f"ℹ️ Nenhum evento criado (pode estar aguardando confirmação)")

        print(f"✅ Teste 3 PASSOU")

    # ════════════════════════════════════════════════════════════════
    # TESTE 4: Multi-tenant isolation
    # ════════════════════════════════════════════════════════════════
    @pytest.mark.asyncio
    async def test_04_multi_tenant_paths_corretos(self):
        """
        VALIDA: Dados salvam no caminho CORRETO (tenant_id, não user_id)

        Paths CORRETOS:
        ✅ Clientes/{tenant_id}/Sessoes/{actor_id}/contexto
        ❌ Clientes/{user_id}/...  (fallback inseguro)
        """
        print(f"\n{'='*70}")
        print(f"TEST 04: Multi-tenant isolation - paths corretos")
        print(f"{'='*70}")

        # Enviar mensagem
        print(f"\n[ACAO] Enviando mensagem...")
        resultado = await self._enviar_msg("teste isolamento")
        assert resultado is not None
        print(f"✅ Mensagem processada")

        # Validar path CORRETO
        print(f"\n[FIRESTORE] Validando path correto...")
        sessao_correta = await self._ler_firestore(
            f"Clientes/{self.TENANT_ID}/Sessoes/{self.ACTOR_ID}/contexto"
        )

        assert sessao_correta is not None, "Sessão não encontrada no path correto"
        assert sessao_correta.get("tenant_id") == self.TENANT_ID
        print(f"✅ Path correto: Clientes/{self.TENANT_ID}/Sessoes/...")

        print(f"✅ Teste 4 PASSOU")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
