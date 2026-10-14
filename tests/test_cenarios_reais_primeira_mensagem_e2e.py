"""
Teste E2E: Executar cenarios COMO PRIMEIRA MENSAGEM

Objetivo: Capturar o erro real que producao ve mas testes nao pegam

Problema: 174/174 testes passam porque usam contexto PRE-PREENCHIDO
Solucao: Testar como PRIMEIRA MENSAGEM (ctx={}, estado=idle)

Este teste executa cada cenario P0+P1 como se fosse a primeira interacao
do usuario, sem nenhum contexto anterior carregado.
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime

# Adicionar projeto ao path
projeto_dir = Path(__file__).parent.parent
sys.path.insert(0, str(projeto_dir))


class TestCenariosComoMensagemPrimeira:
    """Testa cenarios reais como PRIMEIRA MENSAGEM (sem contexto previo)"""

    @pytest.fixture
    def cenarios_p0(self):
        """Carrega cenarios P0 do arquivo JSON"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_agendamento_real.json"
        if fixture_path.exists():
            with open(fixture_path, encoding='utf-8') as f:
                data = json.load(f)
                return data.get("cenarios", [])
        return []

    @pytest.fixture
    def cenarios_p1(self):
        """Carrega cenarios P1 do arquivo JSON"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_p1_onboarding_real.json"
        if fixture_path.exists():
            with open(fixture_path, encoding='utf-8') as f:
                data = json.load(f)
                return data.get("cenarios", [])
        return []

    async def _executar_como_primeira_mensagem(
        self,
        frase: str,
        user_id: str = "test_user_001",
        tenant_id: str = "7394370553"
    ):
        """
        Executa mensagem como PRIMEIRA MENSAGEM (contexto vazio)

        Replica EXATAMENTE o cenario de producao:
        - Nenhum contexto anterior
        - Estado idle
        - Primeira interacao
        """
        from router.principal_router import roteador_principal

        # Executar como primeira mensagem
        resultado = await roteador_principal(
            user_id=user_id,
            mensagem=frase,
            tenant_id=tenant_id,
            phone_number_id=None,
            update=None,
            context=None
        )

        return resultado

    @pytest.mark.asyncio
    async def test_C01_outra_profissional_primeira_mensagem(self, cenarios_p0):
        """
        TESTE CRITICO: P0.1 - "outra profissional" como PRIMEIRA MENSAGEM

        Este cenario NAO funciona nos testes P0 porque:
        - Testes pre-carregam contexto_confirmacao
        - Producao recebe primeira mensagem com contexto vazio

        Se falhar aqui, captura o erro real!
        """
        cenario = next((c for c in cenarios_p0 if c.get("id") == "C01"), None)

        if not cenario:
            pytest.skip("Cenario C01 nao encontrado")

        # Executar como PRIMEIRA MENSAGEM (sem contexto anterior)
        resultado = await self._executar_como_primeira_mensagem(
            frase=cenario["frase"],  # "outra profissional"
            user_id="test_cliente_c01",
            tenant_id="7394370553"
        )

        # Validar
        assert resultado is not None, "Resultado nao pode ser None"
        print(f"[C01 RESULTADO] {resultado}")

    @pytest.mark.asyncio
    async def test_A01_agendamento_completo_primeira_mensagem(self, cenarios_p0):
        """Testa agendamento completo como primeira mensagem"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A01"), None)

        if not cenario:
            pytest.skip("Cenario A01 nao encontrado")

        resultado = await self._executar_como_primeira_mensagem(
            frase=cenario["frase"],
            user_id="test_a01",
            tenant_id="7394370553"
        )

        assert resultado is not None
        print(f"[A01 RESULTADO] {resultado}")

    @pytest.mark.asyncio
    async def test_A05_agendamento_curto_primeira_mensagem(self, cenarios_p0):
        """Testa agendamento minimo (apenas servico)"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A05"), None)

        if not cenario:
            pytest.skip("Cenario A05 nao encontrado")

        resultado = await self._executar_como_primeira_mensagem(
            frase=cenario["frase"],
            user_id="test_a05",
            tenant_id="7394370553"
        )

        assert resultado is not None
        print(f"[A05 RESULTADO] {resultado}")

    @pytest.mark.asyncio
    async def test_A09_erros_digitacao_primeira_mensagem(self, cenarios_p0):
        """Testa robustez: erro de digitacao multiplo"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A09"), None)

        if not cenario:
            pytest.skip("Cenario A09 nao encontrado")

        resultado = await self._executar_como_primeira_mensagem(
            frase=cenario["frase"],
            user_id="test_a09",
            tenant_id="7394370553"
        )

        assert resultado is not None
        print(f"[A09 RESULTADO] {resultado}")

    @pytest.mark.asyncio
    async def test_P1_01_onboarding_novo_dono(self, cenarios_p1):
        """Testa onboarding de novo dono"""
        cenario = next((c for c in cenarios_p1 if c.get("id") == "P1_01"), None)

        if not cenario:
            pytest.skip("Cenario P1_01 nao encontrado")

        resultado = await self._executar_como_primeira_mensagem(
            frase=cenario["frase"],
            user_id="novo_dono_001",
            tenant_id=None  # Novo dono pode nao ter tenant_id
        )

        assert resultado is not None
        print(f"[P1_01 RESULTADO] {resultado}")

    @pytest.mark.asyncio
    async def test_P1_14_robustez_erros_multiplos(self, cenarios_p1):
        """Testa robustez P1 com multiplos erros"""
        cenario = next((c for c in cenarios_p1 if c.get("id") == "P1_14"), None)

        if not cenario:
            pytest.skip("Cenario P1_14 nao encontrado")

        resultado = await self._executar_como_primeira_mensagem(
            frase=cenario["frase"],
            user_id="test_p1_14",
            tenant_id="7394370553"
        )

        assert resultado is not None
        print(f"[P1_14 RESULTADO] {resultado}")

    @pytest.mark.asyncio
    async def test_batch_cenarios_aleatorios(self, cenarios_p0):
        """Batch: executa 5 cenarios aleatorios como primeira mensagem"""
        import random

        amostra = random.sample(cenarios_p0, min(5, len(cenarios_p0)))

        erros = []
        for i, cenario in enumerate(amostra):
            try:
                resultado = await self._executar_como_primeira_mensagem(
                    frase=cenario["frase"],
                    user_id=f"test_batch_{i}",
                    tenant_id="7394370553"
                )

                if resultado:
                    print(f"[{cenario['id']}] OK")
                else:
                    erros.append(f"[{cenario['id']}] Resultado vazio")

            except Exception as e:
                erros.append(f"[{cenario['id']}] {str(e)}")

        if erros:
            print("\nERROS:")
            for erro in erros:
                print(f"  {erro}")

        assert len(erros) == 0, f"{len(erros)} cenarios falharam"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
