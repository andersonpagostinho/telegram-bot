# -*- coding: utf-8 -*-
# tests/test_p01_identidade_contexto.py

"""
Testes P0.1: IdentidadeContexto multicanal

Comprovar que a estrutura de identidade normalizada funciona
para Telegram e WhatsApp, preservando semantics existentes.
"""

import pytest
from utils.identidade_contexto import (
    IdentidadeContexto,
    criar_identidade_whatsapp,
    criar_identidade_telegram,
    validar_identidade_whatsapp,
)


class TestT1_WhatsApp_Identidade:
    """T1: Verificar construção de identidade WhatsApp."""

    def test_whatsapp_factory_basico(self):
        """Criar identidade WhatsApp com dados básicos."""
        wa_id = "5511991382080"
        phone_number_id = "1350170954840548"
        tenant_id = "7394370553"

        identidade = criar_identidade_whatsapp(
            wa_id=wa_id,
            phone_number_id=phone_number_id,
            tenant_id=tenant_id,
        )

        # Validação de resultado esperado
        assert identidade.user_id == "5511991382080"
        assert identidade.tenant_id == "7394370553"
        assert identidade.actor_id == "whatsapp:5511991382080"
        assert identidade.canal == "whatsapp"
        assert identidade.actor_tipo is None
        assert identidade.actor_nome is None

    def test_whatsapp_actor_id_canonico(self):
        """Verificar que actor_id é canônico (whatsapp:wa_id)."""
        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        assert identidade.actor_id == "whatsapp:5511991382080"
        assert identidade.actor_id.startswith("whatsapp:")

    def test_whatsapp_tenant_id_nao_eh_wa_id(self):
        """Verificar que tenant_id é DIFERENTE de wa_id."""
        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        # Regra P0: tenant_id NUNCA deve ser wa_id
        assert identidade.tenant_id != identidade.user_id
        assert identidade.tenant_id == "7394370553"
        assert identidade.user_id == "5511991382080"

    def test_whatsapp_validacao_identidade_correta(self):
        """Verificar que validação passa para identidade correta."""
        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        assert validar_identidade_whatsapp(identidade) is True

    def test_whatsapp_validacao_fallback_incorreto(self):
        """Verificar que validação falha se tenant_id == wa_id (fallback)."""
        # Simular fallback incorreto (tenant_id virou wa_id)
        identidade = IdentidadeContexto(
            user_id="5511991382080",
            tenant_id="5511991382080",  # FALLBACK INCORRETO
            actor_id="whatsapp:5511991382080",
            canal="whatsapp",
        )

        # Validação deve FALHAR
        assert validar_identidade_whatsapp(identidade) is False


class TestT2_Telegram_Identidade:
    """T2: Verificar que Telegram preserva identidade existente."""

    def test_telegram_factory_basico(self):
        """Criar identidade Telegram com dados básicos."""
        telegram_id = "123456789"

        identidade = criar_identidade_telegram(telegram_id=telegram_id)

        # Validação de resultado esperado
        assert identidade.user_id == "123456789"
        assert identidade.actor_id == "tg:123456789"
        assert identidade.canal == "telegram"
        # tenant_id para Telegram pode ser resolvido depois
        assert identidade.tenant_id is not None

    def test_telegram_actor_id_canonico(self):
        """Verificar que actor_id é canônico (tg:telegram_id)."""
        identidade = criar_identidade_telegram(telegram_id="123456789")

        assert identidade.actor_id == "tg:123456789"
        assert identidade.actor_id.startswith("tg:")

    def test_telegram_user_id_preservado(self):
        """Verificar que user_id é preservado exatamente (sem reinterpretação)."""
        telegram_id = "123456789"
        identidade = criar_identidade_telegram(telegram_id=telegram_id)

        # user_id deve ser EXATAMENTE o telegram_id original
        assert identidade.user_id == telegram_id
        # Não deve ser reinterpretado como algo diferente
        assert identidade.user_id == "123456789"

    def test_telegram_com_tenant_id_explícito(self):
        """Verificar que tenant_id pode ser passado explicitamente."""
        telegram_id = "123456789"
        tenant_id = "999"

        identidade = criar_identidade_telegram(
            telegram_id=telegram_id,
            canal_tenant_id=tenant_id,
        )

        assert identidade.tenant_id == "999"


class TestT3_Isolamento_Tenant:
    """T3: Verificar isolamento entre diferentes tenants."""

    def test_dois_phone_number_id_diferentes_mesmo_wa_id(self):
        """
        Dois phone_number_id diferentes podem ter o mesmo wa_id
        mas DEVEM ter tenant_id diferentes.
        """
        wa_id = "5511991382080"  # Mesmo número de telefone

        # Endpoint A
        identidade_a = criar_identidade_whatsapp(
            wa_id=wa_id,
            phone_number_id="1350170954840548",  # Endpoint A
            tenant_id="7394370553",               # Tenant A
        )

        # Endpoint B
        identidade_b = criar_identidade_whatsapp(
            wa_id=wa_id,
            phone_number_id="987654321",         # Endpoint B (diferente)
            tenant_id="9876543210",              # Tenant B (diferente)
        )

        # Isolamento: mesmo wa_id, tenants diferentes
        assert identidade_a.user_id == identidade_b.user_id
        assert identidade_a.tenant_id != identidade_b.tenant_id

        # actor_id continua igual (baseado em wa_id)
        assert identidade_a.actor_id == identidade_b.actor_id

    def test_dois_wa_id_diferentes_mesmo_tenant(self):
        """
        Dois wa_id diferentes podem ter o mesmo tenant
        mas DEVEM ter actor_id diferentes.
        """
        phone_number_id = "1350170954840548"
        tenant_id = "7394370553"

        # Ator A
        identidade_a = criar_identidade_whatsapp(
            wa_id="5511991382080",  # Ator A
            phone_number_id=phone_number_id,
            tenant_id=tenant_id,
        )

        # Ator B
        identidade_b = criar_identidade_whatsapp(
            wa_id="5521987654321",  # Ator B (diferente)
            phone_number_id=phone_number_id,
            tenant_id=tenant_id,
        )

        # Isolamento: mesmo tenant, atores diferentes
        assert identidade_a.tenant_id == identidade_b.tenant_id
        assert identidade_a.user_id != identidade_b.user_id
        assert identidade_a.actor_id != identidade_b.actor_id


class TestT4_Campos_Obrigatórios:
    """T4: Verificar comportamento quando faltam campos obrigatórios."""

    def test_identidade_sem_user_id(self):
        """Falhar explicitamente se user_id está vazio."""
        with pytest.raises(ValueError, match="user_id é obrigatório"):
            IdentidadeContexto(
                user_id="",  # VAZIO
                tenant_id="123",
                actor_id="test:123",
                canal="whatsapp",
            )

    def test_identidade_sem_tenant_id(self):
        """Falhar explicitamente se tenant_id está vazio."""
        with pytest.raises(ValueError, match="tenant_id é obrigatório"):
            IdentidadeContexto(
                user_id="123",
                tenant_id="",  # VAZIO
                actor_id="test:123",
                canal="whatsapp",
            )

    def test_identidade_sem_actor_id(self):
        """Falhar explicitamente se actor_id está vazio."""
        with pytest.raises(ValueError, match="actor_id é obrigatório"):
            IdentidadeContexto(
                user_id="123",
                tenant_id="456",
                actor_id="",  # VAZIO
                canal="whatsapp",
            )

    def test_identidade_canal_invalido(self):
        """Falhar explicitamente se canal não é válido."""
        with pytest.raises(ValueError, match="canal deve ser"):
            IdentidadeContexto(
                user_id="123",
                tenant_id="456",
                actor_id="test:123",
                canal="discord",  # INVÁLIDO
            )

    def test_whatsapp_factory_sem_wa_id(self):
        """Falhar se factory WhatsApp recebe wa_id vazio."""
        with pytest.raises(ValueError, match="wa_id é obrigatório"):
            criar_identidade_whatsapp(
                wa_id="",  # VAZIO
                phone_number_id="1350170954840548",
                tenant_id="7394370553",
            )

    def test_whatsapp_factory_sem_tenant_id(self):
        """Falhar se factory WhatsApp recebe tenant_id vazio."""
        with pytest.raises(ValueError, match="tenant_id é obrigatório"):
            criar_identidade_whatsapp(
                wa_id="5511991382080",
                phone_number_id="1350170954840548",
                tenant_id="",  # VAZIO
            )

    def test_telegram_factory_sem_telegram_id(self):
        """Falhar se factory Telegram recebe telegram_id vazio."""
        with pytest.raises(ValueError, match="telegram_id é obrigatório"):
            criar_identidade_telegram(telegram_id="")  # VAZIO


class TestIntegracaoBasica:
    """Testes de integração básica."""

    def test_repr_identidade(self):
        """Verificar que __repr__ funciona."""
        identidade = criar_identidade_whatsapp(
            wa_id="5511991382080",
            phone_number_id="1350170954840548",
            tenant_id="7394370553",
        )

        repr_str = repr(identidade)
        assert "IdentidadeContexto" in repr_str
        assert "whatsapp" in repr_str
        assert "5511991382080" in repr_str

    def test_identidade_com_campos_opcionais(self):
        """Verificar que campos opcionais podem ser definidos."""
        identidade = IdentidadeContexto(
            user_id="5511991382080",
            tenant_id="7394370553",
            actor_id="whatsapp:5511991382080",
            canal="whatsapp",
            actor_tipo="cliente",
            actor_nome="João Silva",
            tenant_nome="Barbearia Central",
        )

        assert identidade.actor_tipo == "cliente"
        assert identidade.actor_nome == "João Silva"
        assert identidade.tenant_nome == "Barbearia Central"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
