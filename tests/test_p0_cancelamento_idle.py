"""
TEST: P0 Cancelamento em Contexto Idle

Valida que cancelamento é detectado e processado mesmo sem fluxo ativo.

Cenários:
1. "Quero cancelar com a Bruna amanhã" → entra em aguardando_confirmacao_cancelamento
2. "Olá" → saudação normal, não entra em cancelamento
3. "Cancelar" → inicia fluxo de cancelamento
"""

import asyncio
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, "/Users/ANDERSON/iCloudDrive/Projeto Mercado Digital/Agente Bot/NeoEve - Empresarial")


async def test_cancelamento_idle_detectado():
    """Teste que cancelamento em idle é detectado e não ignorado."""

    print("\n" + "=" * 70)
    print("TEST 1: Cancelamento em contexto idle é detectado")
    print("=" * 70)

    # Mock de funções
    async def mock_obter_id_dono(user_id):
        return "dono_teste"

    async def mock_carregar_contexto(user_id, tenant_id=None):
        return {"estado_fluxo": "idle"}  # Contexto vazio, sem fluxo

    async def mock_salvar_contexto(user_id, ctx, tenant_id=None):
        assert ctx.get("estado_fluxo") == "aguardando_confirmacao_cancelamento", \
            f"Estado deveria ser 'aguardando_confirmacao_cancelamento', mas foi {ctx.get('estado_fluxo')}"
        assert ctx.get("cancelamento_pendente") is not None, \
            "cancelamento_pendente deveria estar no contexto"
        print(f"  ✅ Contexto salvo corretamente com estado: {ctx.get('estado_fluxo')}")
        return True

    def mock_normalizar(txt):
        return txt.lower().strip()

    def mock_normalizar_intencao(txt):
        return {}

    # Patches
    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("router.principal_router.carregar_contexto_temporario", side_effect=mock_carregar_contexto):
            with patch("router.principal_router.salvar_contexto_temporario", side_effect=mock_salvar_contexto):
                with patch("router.principal_router.normalizar", side_effect=mock_normalizar):
                    with patch("router.principal_router.normalizar_intencao_humana", side_effect=mock_normalizar_intencao):
                        try:
                            from router.principal_router import roteador_principal

                            # Teste: mensagem com cancelamento em idle
                            print("\n[TESTE] Chamando roteador_principal com 'Quero cancelar com a Bruna amanhã'...")
                            result = await roteador_principal(
                                user_id="user_123",
                                mensagem="Quero cancelar com a Bruna amanhã",
                                update=None,
                                context=None
                            )

                            # Validar resultado
                            assert result.get("handled") == True, "Resultado deveria ter handled=True"
                            resposta = result.get("resposta", "")
                            assert "cancelar" in resposta.lower(), f"Resposta deveria mencionar cancelamento: {resposta}"
                            assert "acao" not in result or result.get("acao") != "ignorar", \
                                "Resultado NÃO deveria ter acao='ignorar'"

                            print(f"\n✅ TEST 1 PASSED")
                            print(f"   - Cancelamento foi detectado ✅")
                            print(f"   - Não ignorou a mensagem ✅")
                            print(f"   - Estado foi atualizado para aguardando_confirmacao_cancelamento ✅")
                            return True

                        except Exception as e:
                            print(f"\n❌ TEST 1 FAILED: {e}")
                            import traceback
                            traceback.print_exc()
                            return False


async def test_saudacao_continua_normal():
    """Teste que saudação simples continua sendo tratada como saudação."""

    print("\n" + "=" * 70)
    print("TEST 2: Saudação normal não entra em cancelamento")
    print("=" * 70)

    async def mock_obter_id_dono(user_id):
        return "dono_teste"

    async def mock_carregar_contexto(user_id, tenant_id=None):
        return {"estado_fluxo": "idle"}

    async def mock_salvar_contexto(user_id, ctx, tenant_id=None):
        # Saudação não deveria alterar estado para cancelamento
        assert ctx.get("estado_fluxo") != "aguardando_confirmacao_cancelamento", \
            "Saudação não deveria iniciar fluxo de cancelamento"
        return True

    def mock_normalizar(txt):
        return txt.lower().strip()

    def mock_normalizar_intencao(txt):
        return {}

    with patch("router.principal_router.obter_id_dono", side_effect=mock_obter_id_dono):
        with patch("router.principal_router.carregar_contexto_temporario", side_effect=mock_carregar_contexto):
            with patch("router.principal_router.salvar_contexto_temporario", side_effect=mock_salvar_contexto):
                with patch("router.principal_router.normalizar", side_effect=mock_normalizar):
                    with patch("router.principal_router.normalizar_intencao_humana", side_effect=mock_normalizar_intencao):
                        try:
                            from router.principal_router import roteador_principal

                            print("\n[TESTE] Chamando roteador_principal com 'Olá'...")
                            result = await roteador_principal(
                                user_id="user_123",
                                mensagem="Olá",
                                update=None,
                                context=None
                            )

                            # Resultado deveria ser saudação, não cancelamento
                            assert result.get("handled") == True, "Resultado deveria ter handled=True"

                            print(f"\n✅ TEST 2 PASSED")
                            print(f"   - Saudação foi tratada corretamente ✅")
                            print(f"   - Não inicializou fluxo de cancelamento ✅")
                            return True

                        except Exception as e:
                            print(f"\n❌ TEST 2 FAILED: {e}")
                            import traceback
                            traceback.print_exc()
                            return False


async def main():
    """Executar testes."""
    print("\n" + "=" * 70)
    print("SUITE: P0 Cancelamento em Contexto Idle")
    print("=" * 70)

    results = []

    # Teste 1
    try:
        r1 = await test_cancelamento_idle_detectado()
        results.append(("Test 1: Cancelamento em idle", r1))
    except Exception as e:
        results.append(("Test 1: Cancelamento em idle", False))
        print(f"❌ Erro: {e}")

    # Teste 2
    try:
        r2 = await test_saudacao_continua_normal()
        results.append(("Test 2: Saudação normal", r2))
    except Exception as e:
        results.append(("Test 2: Saudação normal", False))
        print(f"❌ Erro: {e}")

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")

    total = sum(1 for _, r in results if r)
    print(f"\nTotal: {total}/{len(results)} passed")

    return all(r for _, r in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
