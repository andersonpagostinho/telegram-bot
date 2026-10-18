"""
TESTES P0-FIX: Validação de Expediente e Cancelamento de Draft

FIX 1: Validar funcionamento quando data não tem horário (domingo fechado)
FIX 2: Abandonar draft sem cancelar evento existente
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pytz


class TestFix1Expediente:
    """FIX 1: Validação de funcionamento para datas sem horário"""

    @pytest.mark.asyncio
    async def test_domingo_fechado_rejeitado(self):
        """
        Quando usuário diz 'quero agendar para domingo' sem hora
        E domingo está configurado como fechado (aberto: false)
        Então: data deve ser rejeitada com mensagem apropriada
        """
        from router.principal_router import extrair_slots_e_mesclar

        # Data é domingo (18/10/2026 = Domingo)
        ctx = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": None
            }
        }

        # Simulando: "quero agendar para hoje" em domingo
        resultado = await extrair_slots_e_mesclar(
            ctx=ctx,
            texto_usuario="quero agendar um corte para hoje",  # 18/10/2026 = domingo
            dono_id="7394370553",
            cliente_id="whatsapp:5511991382080"
        )

        # Verificar se foi rejeitado
        assert resultado.get("_erro_validacao") is not None, \
            f"Domingo deveria ser rejeitado, mas resultado foi: {resultado}"

        assert "não abre" in resultado.get("_erro_validacao", "").lower(), \
            "Mensagem de erro deveria mencionar que não abre"

        assert resultado.get("data_hora") is None, \
            "data_hora não deveria ser atribuído se dia está fechado"

    @pytest.mark.asyncio
    async def test_dia_valido_sem_hora_aceito(self):
        """
        Quando usuário diz 'quero agendar para amanhã' sem hora
        E amanhã é um dia que o salão funciona
        Então: data deve ser aceita com data_sem_hora=True
        """
        from router.principal_router import extrair_slots_e_mesclar

        # Amanhã (19/10/2026 = segunda-feira)
        ctx = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "aguardando_data",
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": None
            }
        }

        resultado = await extrair_slots_e_mesclar(
            ctx=ctx,
            texto_usuario="quero agendar um corte para amanhã",  # 19/10/2026 = segunda
            dono_id="7394370553",
            cliente_id="whatsapp:5511991382080"
        )

        # Não deveria ter erro de expediente
        assert resultado.get("_erro_validacao") is None, \
            f"Dia válido não deveria ser rejeitado: {resultado.get('_erro_validacao')}"

        # Deveria ter data mas sem hora
        assert resultado.get("data_sem_hora") == True, \
            "data_sem_hora deveria ser True quando sem horário"


class TestFix2Cancelamento:
    """FIX 2: Abandonar draft sem cancelar evento existente"""

    @pytest.mark.asyncio
    async def test_cancelar_draft_ativo(self):
        """
        Quando usuário está em agendamento ativo (estado_fluxo='agendando')
        E diz 'cancelar'
        Então: draft deve ser abandonado, NÃO procurar eventos existentes
        """
        from router.principal_router import roteador_principal
        from services.firebase_service_async import atualizar_dado_em_path
        import uuid

        tenant_id = "test_" + uuid.uuid4().hex[:8]
        actor_id = "whatsapp:test_5511991382080"

        # Setup: criar sessão com draft ativo
        ctx_ativo = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "agendando",  # ← ESTADO ATIVO
            "draft_agendamento": {
                "servico": "corte feminino",
                "profissional": "Bruna",
                "data_hora": "2026-10-19T14:00:00"
            },
            "tenant_id": tenant_id,
            "_tenant_id_guard": tenant_id,
            "actor_id": actor_id
        }

        # Salvar contexto com draft ativo
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados=ctx_ativo
        )

        try:
            # Usuário diz "cancelar"
            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="cancelar",
                tenant_id=tenant_id
            )

            # Verificar resposta é de abandono de draft, NÃO erro de "evento não encontrado"
            resposta = resultado.get("resposta", "").lower()

            assert "não encontrei" not in resposta, \
                f"Não deveria procurar eventos quando há draft ativo. Resposta: {resposta}"

            assert "cancelei o agendamento" in resposta or "tudo bem" in resposta, \
                f"Deveria confirmar abandono do draft. Resposta: {resposta}"

        finally:
            # Cleanup
            pass

    @pytest.mark.asyncio
    async def test_cancelar_sem_draft_procura_eventos(self):
        """
        Quando usuário NÃO está em agendamento (estado_fluxo=None ou 'idle')
        E diz 'cancelar'
        Então: deve procurar por eventos existentes para cancelar
        """
        from router.principal_router import roteador_principal
        from services.firebase_service_async import atualizar_dado_em_path
        import uuid

        tenant_id = "test_" + uuid.uuid4().hex[:8]
        actor_id = "whatsapp:test_5511991382080"

        # Setup: criar sessão SEM draft ativo
        ctx_vazio = {
            "tipo_usuario": "cliente",
            "estado_fluxo": "idle",  # ← NÃO EM AGENDAMENTO
            "draft_agendamento": None,
            "tenant_id": tenant_id,
            "_tenant_id_guard": tenant_id,
            "actor_id": actor_id
        }

        # Salvar contexto sem draft
        await atualizar_dado_em_path(
            path=f"Clientes/{tenant_id}/Sessoes/{actor_id}",
            dados=ctx_vazio
        )

        try:
            # Usuário diz "cancelar"
            resultado = await roteador_principal(
                user_id=actor_id,
                mensagem="cancelar",
                tenant_id=tenant_id
            )

            resposta = resultado.get("resposta", "").lower()

            # Sem draft ativo, deveria procurar eventos
            # (resultado será "não encontrei" porque não há eventos reais)
            assert "não encontrei nenhum evento" in resposta or "nenhum agendamento" in resposta.lower(), \
                f"Sem draft ativo, deveria procurar eventos. Resposta: {resposta}"

        finally:
            # Cleanup
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
