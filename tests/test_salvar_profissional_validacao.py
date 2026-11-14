#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE UNITÁRIO — Validação de persistência em salvar_profissional()

Objetivos:
1. Confirmar que salvar_profissional() lança exceção se persistência falhar
2. Confirmar que retorna payload se persistência suceder
3. Confirmar comportamento dos chamadores afetados
"""

import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.cadastro_inicial_service import salvar_profissional


class TestSalvarProfissionalValidacao:
    """Testes da validação de persistência."""

    @staticmethod
    async def test_persistencia_sucesso():
        """Teste 1: Persistência bem-sucedida retorna payload."""
        print("\n[TEST-1] Persistência bem-sucedida...")

        # Mock: salvar_dado_em_path retorna True (sucesso)
        with patch('services.cadastro_inicial_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = True

            payload = await salvar_profissional(
                user_id="test_tenant",
                nome="TestProf",
                servicos={"manicure": {"preco": 50, "duracao": 30}}
            )

            assert isinstance(payload, dict), f"Esperado dict, obteve {type(payload)}"
            assert payload.get("nome") == "Testprof", f"Nome não formatado corretamente"
            assert payload.get("duracoes", {}).get("manicure") == 30
            print("  [OK] PASS: Retornou payload em sucesso")

    @staticmethod
    async def test_persistencia_falha():
        """Teste 2: Persistência falhando lança exceção."""
        print("\n[TEST-2] Persistência falhando...")

        # Mock: salvar_dado_em_path retorna False (falha)
        with patch('services.cadastro_inicial_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = False

            try:
                await salvar_profissional(
                    user_id="test_tenant",
                    nome="TestProf",
                    servicos={"manicure": {"preco": 50, "duracao": 30}}
                )
                print("  [FAIL] FAIL: Deveria ter lançado exceção")
                return False
            except ValueError as e:
                assert "Falha ao persistir" in str(e), f"Mensagem incorreta: {e}"
                print(f"  [OK] PASS: Lançou ValueError com mensagem: {e}")
                return True

    @staticmethod
    async def test_persistencia_excecao():
        """Teste 3: Simular falha de Firestore (retorna False)."""
        print("\n[TEST-3] Falha de Firestore...")

        # Mock: salvar_dado_em_path retorna False (Firestore captura e retorna False)
        with patch('services.cadastro_inicial_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = False

            # salvar_dado_em_path captura a exceção e retorna False
            # Então salvar_profissional lança ValueError
            try:
                await salvar_profissional(
                    user_id="test_tenant",
                    nome="TestProf",
                    servicos={"manicure": {"preco": 50, "duracao": 30}}
                )
                print("  [FAIL] FAIL: Deveria ter lançado exceção")
                return False
            except ValueError as e:
                print(f"  [OK] PASS: Lançou ValueError: {e}")
                return True

    @staticmethod
    async def test_normalizacao_nome():
        """Teste 4: Nome é formatado como Title case."""
        print("\n[TEST-4] Normalização de nome...")

        with patch('services.cadastro_inicial_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = True

            payload = await salvar_profissional(
                user_id="test_tenant",
                nome="bruna silva",
                servicos={"manicure": {"preco": 50, "duracao": 30}}
            )

            assert payload.get("nome") == "Bruna Silva", f"Nome não é Title case: {payload.get('nome')}"
            print(f"  [OK] PASS: Nome formatado como '{payload.get('nome')}'")

    @staticmethod
    async def test_normalizacao_servicos():
        """Teste 5: Nomes de serviços são convertidos para lowercase."""
        print("\n[TEST-5] Normalização de serviços...")

        with patch('services.cadastro_inicial_service.salvar_dado_em_path', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = True

            payload = await salvar_profissional(
                user_id="test_tenant",
                nome="Bruna",
                servicos={
                    "Manicure": {"preco": 50, "duracao": 30},
                    "PEDICURE": {"preco": 40, "duracao": 30}
                }
            )

            servicos = payload.get("servicos", [])
            assert "manicure" in servicos, f"manicure não em lowercase: {servicos}"
            assert "pedicure" in servicos, f"pedicure não em lowercase: {servicos}"
            assert "Manicure" not in servicos, "Manicure deveria ser lowercase"
            print(f"  [OK] PASS: Serviços normalizados: {servicos}")


async def run_tests():
    """Executar todos os testes."""
    print("\n" + "="*70)
    print("TESTES UNITÁRIOS — VALIDAÇÃO DE PERSISTÊNCIA")
    print("="*70)

    tests = [
        TestSalvarProfissionalValidacao.test_persistencia_sucesso,
        TestSalvarProfissionalValidacao.test_persistencia_falha,
        TestSalvarProfissionalValidacao.test_persistencia_excecao,
        TestSalvarProfissionalValidacao.test_normalizacao_nome,
        TestSalvarProfissionalValidacao.test_normalizacao_servicos,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = await test()
            if result is False:
                failed += 1
            else:
                passed += 1
        except AssertionError as e:
            print(f"  [FAIL] FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] ERROR: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTADO: {passed} PASSOU, {failed} FALHOU")
    print("="*70 + "\n")

    return failed == 0


if __name__ == "__main__":
    resultado = asyncio.run(run_tests())
    sys.exit(0 if resultado else 1)
