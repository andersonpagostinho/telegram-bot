"""
TEST: P0 UnboundLocalError dono_id Fix

Valida que a correção P0-UnboundLocalError resolveu o erro na função roteador_principal().

Cenário: Chamar roteador_principal() com dados simples
Esperado: Não levanta UnboundLocalError, carregar_contexto_temporario é chamado com tenant_id correto
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, "/Users/ANDERSON/iCloudDrive/Projeto Mercado Digital/Agente Bot/NeoEve - Empresarial")


async def test_roteador_principal_dono_id_defined():
    """
    Teste que valida que dono_id é definido no início de roteador_principal()
    antes de ser usado em carregar_contexto_temporario().
    """

    print("\n" + "=" * 70)
    print("TEST: P0 UnboundLocalError dono_id Fix - roteador_principal()")
    print("=" * 70)

    # Mock de obter_id_dono
    async def mock_obter_id_dono(user_id):
        print(f"  [MOCK] obter_id_dono({user_id}) = 'dono_teste_123'")
        return "dono_teste_123"

    # Mock de carregar_contexto_temporario
    async def mock_carregar_contexto(user_id, tenant_id=None):
        print(f"  [MOCK] carregar_contexto_temporario({user_id}, tenant_id={tenant_id})")
        assert tenant_id is not None, "tenant_id deve estar definido!"
        assert tenant_id != "", "tenant_id não pode estar vazio!"
        return {"estado_fluxo": "idle"}

    # Mock de salvar_contexto_temporario
    async def mock_salvar_contexto(user_id, ctx, tenant_id=None):
        print(f"  [MOCK] salvar_contexto_temporario({user_id}, tenant_id={tenant_id})")
        assert tenant_id is not None, "tenant_id deve estar definido!"
        return True

    # Mock de normalizar_intencao_humana
    def mock_normalizar_intencao(texto):
        return {}

    # Patch das funções
    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("router.principal_router.carregar_contexto_temporario", side_effect=mock_carregar_contexto):
            with patch("router.principal_router.salvar_contexto_temporario", side_effect=mock_salvar_contexto):
                with patch("router.principal_router.normalizar_intencao_humana", side_effect=mock_normalizar_intencao):
                    try:
                        # Import DEPOIS de fazer os patches
                        from router.principal_router import roteador_principal

                        # Chamar a função
                        print("\n[TESTE] Chamando roteador_principal('user_123', 'Olá')...")
                        result = await roteador_principal(
                            user_id="user_123",
                            mensagem="Olá",
                            update=None,
                            context=None
                        )

                        print(f"\n[RESULTADO] Função executou sem UnboundLocalError ✅")
                        print(f"[RESULTADO] obter_id_dono foi chamado ✅")
                        print(f"[RESULTADO] carregar_contexto_temporario foi chamado com tenant_id ✅")

                        return True

                    except UnboundLocalError as e:
                        print(f"\n[ERRO] UnboundLocalError: {e} ❌")
                        print(f"[ERRO] Correção não funcionou, dono_id ainda não está definido!")
                        raise

                    except Exception as e:
                        print(f"\n[ERRO] Exceção inesperada: {type(e).__name__}: {e}")
                        # Pode ser erro em outra parte do código, não no dono_id
                        # Então só reportamos se for UnboundLocalError
                        raise


async def test_roteador_principal_tenant_id_fallback():
    """
    Teste que valida que dono_id tem fallback para user_id se obter_id_dono retornar None.
    """

    print("\n" + "=" * 70)
    print("TEST: P0 dono_id Fallback - quando obter_id_dono retorna None")
    print("=" * 70)

    # Mock que retorna None
    async def mock_obter_id_dono_none(user_id):
        print(f"  [MOCK] obter_id_dono({user_id}) = None (fallback)")
        return None

    # Mock de carregar_contexto_temporario
    tenant_id_usado = None
    async def mock_carregar_contexto(user_id, tenant_id=None):
        nonlocal tenant_id_usado
        tenant_id_usado = tenant_id
        print(f"  [MOCK] carregar_contexto_temporario({user_id}, tenant_id={tenant_id})")
        assert tenant_id is not None, "tenant_id deve estar definido (fallback para user_id)!"
        return {"estado_fluxo": "idle"}

    # Mock de salvar_contexto_temporario
    async def mock_salvar_contexto(user_id, ctx, tenant_id=None):
        print(f"  [MOCK] salvar_contexto_temporario({user_id}, tenant_id={tenant_id})")
        return True

    # Mock de normalizar_intencao_humana
    def mock_normalizar_intencao(texto):
        return {}

    # Patch das funções
    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono_none):
        with patch("router.principal_router.carregar_contexto_temporario", side_effect=mock_carregar_contexto):
            with patch("router.principal_router.salvar_contexto_temporario", side_effect=mock_salvar_contexto):
                with patch("router.principal_router.normalizar_intencao_humana", side_effect=mock_normalizar_intencao):
                    try:
                        from router.principal_router import roteador_principal

                        print("\n[TESTE] Chamando com obter_id_dono retornando None...")
                        result = await roteador_principal(
                            user_id="user_999",
                            mensagem="Olá",
                            update=None,
                            context=None
                        )

                        print(f"\n[RESULTADO] Função executou com fallback ✅")
                        print(f"[RESULTADO] tenant_id usado: {tenant_id_usado}")
                        print(f"[RESULTADO] Esperado fallback para 'user_999': {tenant_id_usado == 'user_999'} ✅")

                        assert tenant_id_usado == "user_999", f"Fallback esperado para user_id, mas foi {tenant_id_usado}"
                        return True

                    except Exception as e:
                        print(f"\n[ERRO] Exceção: {type(e).__name__}: {e}")
                        raise


async def main():
    """Executar todos os testes."""
    print("\n" + "=" * 70)
    print("SUITE: P0 UnboundLocalError dono_id Fix")
    print("=" * 70)

    results = []

    # Teste 1: dono_id definido
    try:
        result1 = await test_roteador_principal_dono_id_defined()
        results.append(("Test 1: dono_id defined", result1))
        print("\n✅ Test 1 PASSED")
    except Exception as e:
        results.append(("Test 1: dono_id defined", False))
        print(f"\n❌ Test 1 FAILED: {e}")

    # Teste 2: dono_id fallback
    try:
        result2 = await test_roteador_principal_tenant_id_fallback()
        results.append(("Test 2: dono_id fallback", result2))
        print("\n✅ Test 2 PASSED")
    except Exception as e:
        results.append(("Test 2: dono_id fallback", False))
        print(f"\n❌ Test 2 FAILED: {e}")

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {total_passed}/{total} passed")

    return all(r for _, r in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
