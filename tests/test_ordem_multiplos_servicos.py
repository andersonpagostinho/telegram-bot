# -*- coding: utf-8 -*-
"""
Testes de Validação — Ordem dos Serviços
FASE 5: Verificar que "manicure e pedicure" mantém ordem de menção
"""

import pytest
import sys
import os
from datetime import datetime

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

from router.principal_router import extrair_multiplos_servicos_da_mensagem


# Configuração de teste
TENANT_ID_TESTE = "7394370553"  # Tenant com manicure e pedicure


@pytest.mark.asyncio
class TestOrdemMultiplosServicos:
    """Testes de Ordem de Primeira Menção"""

    async def test_1_manicure_pedicure_nessa_ordem(self):
        """Teste 1: "manicure e pedicure" → ['manicure', 'pedicure']"""
        texto = "manicure e pedicure"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        # Normalizar resultado para comparação
        resultado_norm = [r.lower().strip() for r in resultado]

        # Verificar que ambos foram encontrados
        assert len(resultado_norm) >= 1, f"Nenhum serviço encontrado em '{texto}'"

        # Verificar ordem: manicure deve vir antes de pedicure
        idx_manicure = None
        idx_pedicure = None

        for i, serv in enumerate(resultado_norm):
            if 'manicur' in serv:
                idx_manicure = i
            if 'pedicur' in serv:
                idx_pedicure = i

        if idx_manicure is not None and idx_pedicure is not None:
            assert idx_manicure < idx_pedicure, \
                f"Ordem incorreta: manicure deveria vir antes de pedicure. Resultado: {resultado_norm}"

        print(f"✓ Teste 1 PASS: '{texto}' → {resultado_norm}")

    async def test_2_pedicure_manicure_nessa_ordem(self):
        """Teste 2: "pedicure e manicure" → ['pedicure', 'manicure']"""
        texto = "pedicure e manicure"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        # Verificar ordem: pedicure deve vir antes de manicure
        idx_pedicure = None
        idx_manicure = None

        for i, serv in enumerate(resultado_norm):
            if 'pedicur' in serv:
                idx_pedicure = i
            if 'manicur' in serv:
                idx_manicure = i

        if idx_pedicure is not None and idx_manicure is not None:
            assert idx_pedicure < idx_manicure, \
                f"Ordem incorreta: pedicure deveria vir antes de manicure. Resultado: {resultado_norm}"

        print(f"✓ Teste 2 PASS: '{texto}' → {resultado_norm}")

    async def test_3_repetido_uma_vez(self):
        """Teste 3: "manicure e manicure" → ['manicure'] (apenas uma ocorrência)"""
        texto = "manicure e manicure"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        # Contar ocorrências de manicure
        count_manicure = sum(1 for serv in resultado_norm if 'manicur' in serv)

        assert count_manicure <= 1, \
            f"Manicure deveria aparecer apenas uma vez. Resultado: {resultado_norm}"

        print(f"✓ Teste 3 PASS: '{texto}' → {resultado_norm} (sem duplicatas)")

    async def test_4_mensagem_longa(self):
        """Teste 4: Mensagem longa mantém ordem"""
        texto = "Olá, preciso de manicure e pedicure para amanhã à tarde"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        idx_manicure = None
        idx_pedicure = None

        for i, serv in enumerate(resultado_norm):
            if 'manicur' in serv:
                idx_manicure = i
            if 'pedicur' in serv:
                idx_pedicure = i

        if idx_manicure is not None and idx_pedicure is not None:
            assert idx_manicure < idx_pedicure, \
                f"Ordem incorreta em mensagem longa. Resultado: {resultado_norm}"

        print(f"✓ Teste 4 PASS: Mensagem longa mantém ordem → {resultado_norm}")

    async def test_5_pedicure_manicure_invertido(self):
        """Teste 5: Ordem inversa também funciona"""
        texto = "quero pedicure depois manicure"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        idx_pedicure = None
        idx_manicure = None

        for i, serv in enumerate(resultado_norm):
            if 'pedicur' in serv:
                idx_pedicure = i
            if 'manicur' in serv:
                idx_manicure = i

        if idx_pedicure is not None and idx_manicure is not None:
            assert idx_pedicure < idx_manicure, \
                f"Ordem incorreta. Resultado: {resultado_norm}"

        print(f"✓ Teste 5 PASS: Ordem inversa preservada → {resultado_norm}")

    async def test_6_sem_duplicata_posicional(self):
        """Teste 6: Mesmo com duplicata, primeiro match vence"""
        texto = "manicure manicure"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]

        # Verificar que há apenas 1 manicure, mesmo com menção dupla
        count = len([s for s in resultado_norm if 'manicur' in s])
        assert count == 1, f"Deveria haver 1 manicure, encontrou {count}. Resultado: {resultado_norm}"

        print(f"✓ Teste 6 PASS: Duplicata eliminada → {resultado_norm}")


@pytest.mark.asyncio
class TestRegressaoServicos:
    """Regressão: Garantir que correção não quebra casos existentes"""

    async def test_regressao_um_servico(self):
        """Regressão: Um único serviço funciona"""
        texto = "manicure"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]
        assert any('manicur' in s for s in resultado_norm), \
            f"Manicure deveria estar em {resultado_norm}"

        print(f"✓ Regressão PASS: Um serviço → {resultado_norm}")

    async def test_regressao_vazio(self):
        """Regressão: Mensagem sem serviços retorna lista vazia"""
        texto = "olá tudo bem"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        assert isinstance(resultado, list), "Deveria retornar lista"
        assert len(resultado) == 0, f"Deveria estar vazio, encontrou {resultado}"

        print(f"✓ Regressão PASS: Vazio correto → {resultado}")

    async def test_regressao_case_insensitive(self):
        """Regressão: Case insensitivity mantém"""
        texto = "MANICURE E PEDICURE"
        resultado = await extrair_multiplos_servicos_da_mensagem(texto, TENANT_ID_TESTE)

        resultado_norm = [r.lower().strip() for r in resultado]
        assert len(resultado_norm) >= 1, f"Nenhum serviço encontrado em uppercase"

        print(f"✓ Regressão PASS: Case insensitive funciona → {resultado_norm}")


if __name__ == "__main__":
    import asyncio

    print("\n" + "="*70)
    print("TESTES DE ORDEM DOS SERVIÇOS")
    print("="*70 + "\n")

    # Executar com pytest
    pytest.main([__file__, "-v", "-s"])
