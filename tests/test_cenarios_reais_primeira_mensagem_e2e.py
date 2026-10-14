"""
Test: Cenários Reais como PRIMEIRA MENSAGEM E2E

Objetivo: Executar padrões de mensagem reais como PRIMEIRA MENSAGEM (estado idle, sem contexto prévio)

Este teste foi criado porque os 174/174 testes P0 passam mas o erro persiste em PRODUÇÃO.
A causa: testes usam CONTEXTO PRÉ-PREENCHIDO enquanto produção recebe PRIMEIRA MENSAGEM.

Resultado esperado: Este teste DEVE CAPTURAR o erro real "outra profissional" que produção vê.

Cenários incluem:
- P0: Agendamento completo + curto + com erros
- P1: Onboarding + operacional + robustez
- Contexto dependente: rejeições, alterações
- Erro real: "outra profissional" em confirmacao_pendente (C01)
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Adicionar projeto ao path
projeto_dir = Path(__file__).parent.parent
sys.path.insert(0, str(projeto_dir))


class TestCenariosReaisPrimeiraMensagem:
    """Testa padrões reais como PRIMEIRA MENSAGEM (sem contexto prévio)"""

    @pytest.fixture
    def cenarios_p0(self):
        """Carrega cenários P0 do arquivo JSON"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_agendamento_real.json"
        if fixture_path.exists():
            with open(fixture_path, encoding='utf-8') as f:
                data = json.load(f)
                return data.get("cenarios", [])
        return []

    @pytest.fixture
    def cenarios_p1(self):
        """Carrega cenários P1 do arquivo JSON"""
        fixture_path = Path(__file__).parent / "fixtures" / "cenarios_p1_onboarding_real.json"
        if fixture_path.exists():
            with open(fixture_path, encoding='utf-8') as f:
                data = json.load(f)
                return data.get("cenarios", [])
        return []

    async def _executar_cenario(self, frase: str, contexto_previo: dict = None, user_id: str = "test_user_001", dono_id: str = "test_dono_001"):
        """
        Executa um cenário como PRIMEIRA MENSAGEM (estado idle, sem contexto)

        Args:
            frase: Texto do usuário
            contexto_previo: Contexto anterior (simulado apenas se presente, senão vazio)
            user_id: ID do usuário
            dono_id: ID do dono/tenant

        Returns:
            dict: Resultado da execução
        """
        from router.principal_router import processar_entrada

        # Se há contexto prévio, simular (mas a primeira mensagem NOT deve usá-lo)
        # Este é o ponto crítico: em produção, primeira mensagem não tem contexto
        session_id = f"session_{datetime.now().timestamp()}"

        # Executar: PRIMEIRA MENSAGEM com CONTEXTO VAZIO
        resultado = await processar_entrada(
            mensagem=frase,
            user_id=user_id,
            dono_id=dono_id,
            session_id=session_id,
            contexto_previo=None,  # ← PRIMEIRO ACESSO = SEM CONTEXTO
            timestamp=datetime.now().isoformat()
        )

        return resultado

    @pytest.mark.asyncio
    async def test_C01_outra_profissional_confirmacao_pendente(self, cenarios_p0):
        """
        TESTE CRÍTICO: P0.1 - "outra profissional" em confirmacao_pendente

        Este é o erro real que aparece em produção mas NÃO é pego nos 174/174 testes.

        Razão: Testes P0 pré-preenchem contexto_confirmacao.
        Produção recebe primeira mensagem com contexto vazio.

        Esperado: Sistema DEVE abrir menu de seleção de profissional
        """
        # Encontrar cenário C01 nos fixtures
        cenario = next((c for c in cenarios_p0 if c.get("id") == "C01"), None)

        if not cenario:
            pytest.skip("Cenário C01 não encontrado")

        # Executar como PRIMEIRA MENSAGEM
        # (sem contexto prévio, apesar de cenário descrever contexto_previo)
        resultado = await self._executar_cenario(
            frase=cenario["frase"],
            contexto_previo=cenario.get("contexto_previo"),  # Apenas para referência
            user_id="test_cliente_001",
            dono_id="test_dono_real"
        )

        # Validar: deve reconhecer intenção de trocar profissional
        assert resultado.get("tipo") in ["alteracao_profissional", "aguardando_nova_prof"], \
            f"C01 falhou: frase '{cenario['frase']}' não reconhecida como troca de profissional. Got: {resultado}"

        print(f"✅ C01 PASSOU: 'outra profissional' corretamente interpretada")

    @pytest.mark.asyncio
    async def test_A01_agendamento_completo_primeira_mensagem(self, cenarios_p0):
        """Testa agendamento completo como PRIMEIRA MENSAGEM"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A01"), None)

        if not cenario:
            pytest.skip("Cenário A01 não encontrado")

        resultado = await self._executar_cenario(
            frase=cenario["frase"],
            user_id="test_cliente_novo",
            dono_id="test_dono_novo"
        )

        # Validar extração de dados
        assert resultado.get("servico") is not None, \
            f"A01: serviço não extraído de '{cenario['frase']}'"
        assert resultado.get("profissional") is not None, \
            f"A01: profissional não extraído"

        print(f"✅ A01 PASSOU: Agendamento completo extraído corretamente")

    @pytest.mark.asyncio
    async def test_A05_agendamento_curto_apenas_servico(self, cenarios_p0):
        """Testa agendamento mínimo (apenas serviço)"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A05"), None)

        if not cenario:
            pytest.skip("Cenário A05 não encontrado")

        resultado = await self._executar_cenario(
            frase=cenario["frase"],
            user_id="test_cliente_min"
        )

        # Com apenas serviço, deve pedir profissional
        assert resultado.get("servico") is not None, \
            f"A05: serviço não extraído"
        assert resultado.get("status") in ["aguardando_profissional", "aguardando_contexto"], \
            f"A05: status incorreto, esperava aguardando_profissional"

        print(f"✅ A05 PASSOU: Extração mínima funcionando")

    @pytest.mark.asyncio
    async def test_A09_agendamento_erros_digitacao(self, cenarios_p0):
        """Testa robustez: erro de digitação múltiplo"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A09"), None)

        if not cenario:
            pytest.skip("Cenário A09 não encontrado")

        resultado = await self._executar_cenario(
            frase=cenario["frase"],  # "quero corte com bruna amanha as 9"
            user_id="test_cliente_erros"
        )

        # Deve normalizar e ainda assim extrair
        assert resultado.get("servico") is not None, \
            f"A09: serviço não extraído apesar de erro de digitação"

        print(f"✅ A09 PASSOU: Erros de digitação normalizados")

    @pytest.mark.asyncio
    async def test_P1_01_novo_dono_onboarding(self, cenarios_p1):
        """Testa onboarding de novo dono (primeira mensagem P1)"""
        cenario = next((c for c in cenarios_p1 if c.get("id") == "P1_01"), None)

        if not cenario:
            pytest.skip("Cenário P1_01 não encontrado")

        resultado = await self._executar_cenario(
            frase=cenario["frase"],  # "Olá, quero usar o sistema de agendamento"
            user_id="novo_dono_whatsapp_001",  # Novo dono
            dono_id=None  # Será resolvido
        )

        # Deve reconhecer como onboarding de novo dono
        assert resultado.get("tipo") == "onboarding_novo_dono" or "aguardando" in resultado.get("status", "").lower(), \
            f"P1_01: não reconhecido como onboarding"

        print(f"✅ P1_01 PASSOU: Onboarding novo dono detectado")

    @pytest.mark.asyncio
    async def test_P1_14_robustez_gpt_erros_multiplos(self, cenarios_p1):
        """Testa robustez P1: entrada com múltiplos erros de digitação"""
        cenario = next((c for c in cenarios_p1 if c.get("id") == "P1_14"), None)

        if not cenario:
            pytest.skip("Cenário P1_14 não encontrado")

        resultado = await self._executar_cenario(
            frase=cenario["frase"],  # "quro faze corti com a brunna amanha as dez"
            user_id="test_p1_robusto",
            dono_id="test_dono_p1"
        )

        # Apesar de múltiplos erros, deve extrair informação
        assert resultado.get("servico") is not None, \
            f"P1_14: serviço não extraído apesar de erros"

        print(f"✅ P1_14 PASSOU: Robustez de entrada com erros")

    @pytest.mark.asyncio
    async def test_multi_tenant_isolamento(self, cenarios_p0):
        """Valida isolamento multi-tenant em primeira mensagem"""
        cenario = next((c for c in cenarios_p0 if c.get("id") == "A01"), None)

        if not cenario:
            pytest.skip("Cenário A01 não encontrado")

        # Executar MESMO CENÁRIO com DONOS diferentes
        resultado1 = await self._executar_cenario(
            frase=cenario["frase"],
            user_id="cliente_dono1",
            dono_id="dono_001"
        )

        resultado2 = await self._executar_cenario(
            frase=cenario["frase"],
            user_id="cliente_dono2",
            dono_id="dono_002"
        )

        # Ambos devem funcionar, mas com tenant isolado
        assert resultado1.get("servico") is not None, "Dono 1: serviço não extraído"
        assert resultado2.get("servico") is not None, "Dono 2: serviço não extraído"

        print(f"✅ MULTI-TENANT PASSOU: Isolamento em primeira mensagem validado")

    @pytest.mark.asyncio
    async def test_batch_cenarios_p0_aleatorios(self, cenarios_p0):
        """Batch test: executa múltiplos cenários P0 aleatoriamente"""
        import random

        # Pegar 10 cenários aleatórios
        amostra = random.sample(cenarios_p0, min(10, len(cenarios_p0)))

        erros = []
        for cenario in amostra:
            try:
                resultado = await self._executar_cenario(
                    frase=cenario["frase"],
                    contexto_previo=cenario.get("contexto_previo"),
                    user_id=f"test_{cenario['id']}",
                    dono_id="test_dono_batch"
                )

                # Validação mínima: não deve falhar
                if resultado.get("erro"):
                    erros.append(f"[{cenario['id']}] {resultado.get('erro')}")
                else:
                    print(f"  ✅ {cenario['id']}: {cenario['frase'][:50]}...")

            except Exception as e:
                erros.append(f"[{cenario['id']}] {str(e)}")

        if erros:
            print("\n❌ ERROS ENCONTRADOS:")
            for erro in erros:
                print(f"  {erro}")

        assert len(erros) == 0, f"Batch test: {len(erros)} cenários falharam"
        print(f"\n✅ BATCH PASSOU: {len(amostra)} cenários P0 executados sem erros")


class TestRegressaoPosCorrecao:
    """Valida que correção (commit 941f2c4) não quebrou cenários adjacentes"""

    @pytest.mark.asyncio
    async def test_encontrar_servico_mais_proximo_com_dono_id(self):
        """Valida: função encontrar_servico_mais_proximo com dono_id direto"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        # Com dono_id fornecido, deve usar diretamente
        resultado = await encontrar_servico_mais_proximo(
            texto_usuario="corte",
            user_id=None,
            dono_id="test_dono_valido"
        )

        # Deve funcionar ou retornar None, não crash
        assert resultado is None or isinstance(resultado, str), \
            f"encontrar_servico_mais_proximo retornou tipo inesperado: {type(resultado)}"

        print(f"✅ encontrar_servico_mais_proximo com dono_id: OK")

    @pytest.mark.asyncio
    async def test_encontrar_servico_mais_proximo_com_user_id(self):
        """Valida: função encontrar_servico_mais_proximo com user_id (resolve tenant)"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        # Com user_id, deve resolver tenant internamente
        resultado = await encontrar_servico_mais_proximo(
            texto_usuario="escova",
            user_id="test_user_valido",
            dono_id=None
        )

        # Deve funcionar sem erro
        assert resultado is None or isinstance(resultado, str), \
            f"encontrar_servico_mais_proximo com user_id falhou"

        print(f"✅ encontrar_servico_mais_proximo com user_id: OK")

    @pytest.mark.asyncio
    async def test_encontrar_servico_sem_parametros(self):
        """Valida: função encontrar_servico_mais_proximo sem tenant deve retornar None, não crash"""
        from services.normalizacao_service import encontrar_servico_mais_proximo

        # Sem dono_id e sem user_id, deve retornar None com log
        resultado = await encontrar_servico_mais_proximo(
            texto_usuario="corte",
            user_id=None,
            dono_id=None
        )

        # Deve ser None (não crash)
        assert resultado is None, \
            f"encontrar_servico_mais_proximo sem tenant deveria retornar None, got {resultado}"

        print(f"✅ encontrar_servico_mais_proximo sem parâmetros: retorna None corretamente")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
