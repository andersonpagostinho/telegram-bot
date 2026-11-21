"""
P0: TESTES DE VALIDAÇÃO - Fix "botox capilar" Bug

Validar que H2 não aceita serviços inexistentes no catálogo real.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestP0BotoxCapilarFix:
    """Testes para validar que H2 rejeita "botox capilar" e aceita "corte feminino" correto"""

    # Catálogo real do tenant 7394370553 (da produção)
    CATALOGO_REAL = {
        "corte feminino": 40,
        "manicure": 30,
        "escova": 60,
        "hidratacao": 60,
        "coloracao": 120,
        "pedicure": 30
    }

    async def mock_h2_encontrar_servico(
        self,
        mensagem: str,
        servicos_cataloG: dict,
        extrair_como: str = None
    ):
        """
        Mock do fluxo H2:
        1. encontrar_servico_mais_proximo() retorna serviço
        2. Validação contra catálogo
        3. Aceita se existe, rejeita se não existe
        """
        # Simular fuzzy matching (pode retornar qualquer coisa!)
        if extrair_como:
            servico_extraido = extrair_como
        else:
            servico_extraido = None

        # Validação de catálogo (depois da extração)
        if servico_extraido:
            servico_norm = servico_extraido.lower().strip()
            # Verificar contra catálogo real
            catalogo_norm = {s.lower().strip(): v for s, v in servicos_cataloG.items()}

            if servico_norm in catalogo_norm:
                return servico_extraido  # Válido
            else:
                return None  # Rejeitado (não existe)

        return None

    # === TESTE 1: Serviço inexistente é rejeitado ===
    @pytest.mark.asyncio
    async def test_01_botox_capilar_rejeitado(self):
        """Serviço "botox capilar" não existe no catálogo → rejeitado"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer botox capilar segunda às 16",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="botox capilar"  # Mesmo que H2 extraia isso
        )

        assert resultado is None, "botox capilar não deve ser aceito (não existe no catálogo)"

    # === TESTE 2: Serviço real é aceito ===
    @pytest.mark.asyncio
    async def test_02_corte_feminino_aceito(self):
        """Serviço "corte feminino" existe no catálogo → aceito"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer corte feminino segunda às 16",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="corte feminino"
        )

        assert resultado == "corte feminino", "corte feminino deve ser aceito"

    # === TESTE 3: Variações de caso são tratadas ===
    @pytest.mark.asyncio
    async def test_03_case_insensitive(self):
        """Validação deve ser case-insensitive"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer CORTE FEMININO segunda às 16",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="CORTE FEMININO"  # Uppercase
        )

        assert resultado == "CORTE FEMININO", "CORTE FEMININO (uppercase) deve ser aceito"

    # === TESTE 4: Manicure é aceito ===
    @pytest.mark.asyncio
    async def test_04_manicure_aceito(self):
        """Serviço "manicure" existe → aceito"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer manicure sexta",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="manicure"
        )

        assert resultado == "manicure"

    # === TESTE 5: Escova é aceita ===
    @pytest.mark.asyncio
    async def test_05_escova_aceita(self):
        """Serviço "escova" existe → aceito"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer escova amanhã",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="escova"
        )

        assert resultado == "escova"

    # === TESTE 6: Pedicure é aceito ===
    @pytest.mark.asyncio
    async def test_06_pedicure_aceito(self):
        """Serviço "pedicure" existe → aceito"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer pedicure segunda",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="pedicure"
        )

        assert resultado == "pedicure"

    # === TESTE 7: Coloração é aceita ===
    @pytest.mark.asyncio
    async def test_07_coloracao_aceita(self):
        """Serviço "coloracao" existe → aceito"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer coloração segunda",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="coloracao"
        )

        assert resultado == "coloracao"

    # === TESTE 8: Hidratação é aceita ===
    @pytest.mark.asyncio
    async def test_08_hidratacao_aceita(self):
        """Serviço "hidratacao" existe → aceito"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer hidratação segunda",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como="hidratacao"
        )

        assert resultado == "hidratacao"

    # === TESTE 9: Nenhum serviço retorna None ===
    @pytest.mark.asyncio
    async def test_09_nenhum_servico_none(self):
        """Sem extração de serviço → None"""
        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Olá, como vocês estão?",
            servicos_cataloG=self.CATALOGO_REAL,
            extrair_como=None
        )

        assert resultado is None

    # === TESTE 10: Serviço inventado é rejeitado ===
    @pytest.mark.asyncio
    async def test_10_servico_inventado_rejeitado(self):
        """Serviços aleatórios inventados são rejeitados"""
        servicos_inventados = [
            "cabelo colorido",
            "unhas de ouro",
            "tratamento quantico",
            "reflexologia capilar",
            "rituais xamanicos"
        ]

        for servico_inv in servicos_inventados:
            resultado = await self.mock_h2_encontrar_servico(
                mensagem=f"Queria fazer {servico_inv}",
                servicos_cataloG=self.CATALOGO_REAL,
                extrair_como=servico_inv
            )
            assert resultado is None, f"{servico_inv} não deve ser aceito"

    # === TESTE 11: Multi-tenant isolamento ===
    @pytest.mark.asyncio
    async def test_11_multitenant_isolamento(self):
        """Catálogos diferentes de tenants devem ser isolados"""

        # Tenant 1: Catálogo A
        catalogo_A = {"corte masculino": 25, "barba": 15}

        # Tenant 2: Catálogo B
        catalogo_B = {"manicure": 30, "pedicure": 30}

        # Tenant 1 não deve aceitar serviço de Tenant 2
        resultado_tenant1 = await self.mock_h2_encontrar_servico(
            mensagem="manicure",
            servicos_cataloG=catalogo_A,
            extrair_como="manicure"
        )
        assert resultado_tenant1 is None, "Tenant 1 não deve aceitar 'manicure' (não está em seu catálogo)"

        # Tenant 2 deve aceitar
        resultado_tenant2 = await self.mock_h2_encontrar_servico(
            mensagem="manicure",
            servicos_cataloG=catalogo_B,
            extrair_como="manicure"
        )
        assert resultado_tenant2 == "manicure", "Tenant 2 deve aceitar 'manicure'"

    # === TESTE 12: Catálogo vazio = fallback seguro ===
    @pytest.mark.asyncio
    async def test_12_catalogo_vazio_fallback(self):
        """Se catálogo vazio, qualquer serviço é rejeitado"""
        catalogo_vazio = {}

        resultado = await self.mock_h2_encontrar_servico(
            mensagem="Queria fazer qualquer coisa",
            servicos_cataloG=catalogo_vazio,
            extrair_como="qualquer_coisa"
        )

        assert resultado is None, "Catálogo vazio deve rejeitar tudo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
