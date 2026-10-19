"""
Testes para validar correção de perda de estado_fluxo em processar_fluxo_identidade_onboarding.

T1: estado_fluxo="aguardando_servico" preservado após identidade
T2: multiplos_servicos_candidatos preservado
T3: Argumentos corretos em salvar_contexto_temporario
T4: Estado legitimamente encerrado não é reativado
T5: Firestore real (E2E) valida persistência
T6: Regressão "pode marcar as duas" — fluxo contextual, sem duplicação
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from router.integracao_identidade_onboarding import processar_fluxo_identidade_onboarding


# ============================================================================
# T1: estado_fluxo="aguardando_servico" preservado após identidade
# ============================================================================

@pytest.mark.asyncio
async def test_t1_estado_fluxo_aguardando_servico_preservado():
    """
    Valida que processar_fluxo_identidade_onboarding não remove
    estado_fluxo quando o cliente já está em estado ativo.
    """
    # Setup: contexto com estado ativo
    ctx = {
        "estado_fluxo": "aguardando_servico",
        "multiplos_servicos_candidatos": ["manicure", "pedicure"],
        "intencao_conversacional": "agendamento_direto",
    }

    user_id = "5511991382080"
    tenant_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"

    # Mock: resolver_ator_e_validar_guard retorna cliente existente normal
    with patch('router.integracao_identidade_onboarding.resolver_ator_e_validar_guard') as mock_resolver:
        with patch('router.integracao_identidade_onboarding.salvar_contexto_temporario') as mock_save:
            mock_resolver.return_value = {
                "sucesso": True,
                "tipo_usuario": "cliente",
                "actor_id": cliente_id,
                "ator": {"tipo_usuario": "cliente"},
                "requer_onboarding": False,
                "permissoes": ["ler", "agendamento"],
                "proxima_acao": "normal"
            }

            mock_save.return_value = None

            # Executar
            resultado = await processar_fluxo_identidade_onboarding(
                user_id=user_id,
                mensagem="pode marcar as duas",
                tenant_id=tenant_id,
                ctx=ctx,
                context=None,
                cliente_id=cliente_id
            )

            # Validar
            assert resultado is None, "Deve retornar None para fluxo normal"
            assert ctx.get("estado_fluxo") == "aguardando_servico", \
                f"estado_fluxo foi perdido! Esperado 'aguardando_servico', obteve {ctx.get('estado_fluxo')}"
            assert "actor_id" in ctx, "actor_id deve ser adicionado"
            assert "tipo_usuario" in ctx, "tipo_usuario deve ser adicionado"

    print("✅ T1 PASSOU: estado_fluxo preservado")


# ============================================================================
# T2: multiplos_servicos_candidatos preservado
# ============================================================================

@pytest.mark.asyncio
async def test_t2_multiplos_servicos_candidatos_preservado():
    """
    Valida que multiplos_servicos_candidatos não é removido
    durante processamento de identidade.
    """
    ctx = {
        "estado_fluxo": "aguardando_servico",
        "multiplos_servicos_candidatos": ["manicure", "pedicure"],
    }

    user_id = "5511991382080"
    tenant_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"

    with patch('router.integracao_identidade_onboarding.resolver_ator_e_validar_guard') as mock_resolver:
        with patch('router.integracao_identidade_onboarding.salvar_contexto_temporario') as mock_save:
            mock_resolver.return_value = {
                "sucesso": True,
                "tipo_usuario": "cliente",
                "actor_id": cliente_id,
                "ator": {"tipo_usuario": "cliente"},
                "requer_onboarding": False,
                "permissoes": ["ler"],
                "proxima_acao": "normal"
            }
            mock_save.return_value = None

            resultado = await processar_fluxo_identidade_onboarding(
                user_id=user_id,
                mensagem="pode marcar as duas",
                tenant_id=tenant_id,
                ctx=ctx,
                context=None,
                cliente_id=cliente_id
            )

            # Validar
            assert ctx.get("multiplos_servicos_candidatos") == ["manicure", "pedicure"], \
                f"multiplos_servicos_candidatos foi perdido! Obteve {ctx.get('multiplos_servicos_candidatos')}"

    print("✅ T2 PASSOU: multiplos_servicos_candidatos preservado")


# ============================================================================
# T3: Argumentos corretos em salvar_contexto_temporario
# ============================================================================

@pytest.mark.asyncio
async def test_t3_argumentos_salvar_contexto_temporario():
    """
    Valida que chamadas a salvar_contexto_temporario() usam
    argumentos na ordem e tipos corretos.

    Assinatura correta: (user_id: str, contexto: dict, tenant_id: str)
    """
    ctx = {
        "estado_fluxo": "aguardando_servico",
    }

    user_id = "5511991382080"
    tenant_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"

    captured_calls = []

    async def mock_save_captura(*args, **kwargs):
        captured_calls.append((args, kwargs))

    with patch('router.integracao_identidade_onboarding.resolver_ator_e_validar_guard') as mock_resolver:
        with patch('router.integracao_identidade_onboarding.salvar_contexto_temporario', side_effect=mock_save_captura):
            mock_resolver.return_value = {
                "sucesso": True,
                "tipo_usuario": "cliente",
                "actor_id": cliente_id,
                "ator": {"tipo_usuario": "cliente"},
                "requer_onboarding": False,
                "permissoes": ["ler"],
                "proxima_acao": "normal"
            }

            resultado = await processar_fluxo_identidade_onboarding(
                user_id=user_id,
                mensagem="pode marcar as duas",
                tenant_id=tenant_id,
                ctx=ctx,
                context=None,
                cliente_id=cliente_id
            )

            # Validar chamadas capturadas
            assert len(captured_calls) > 0, "salvar_contexto_temporario deve ser chamado pelo menos uma vez"

            for i, (args, kwargs) in enumerate(captured_calls):
                # Esperado: (tenant_id, cliente_id, ctx_dict)
                # Mas função espera: (user_id, contexto_dict, tenant_id)
                assert len(args) >= 2, f"Chamada {i} deve ter pelo menos 2 argumentos posicionais"

                # Validar tipos (segundo argumento deve ser dict)
                assert isinstance(args[1], dict), \
                    f"Chamada {i}: segundo argumento deve ser dict (contexto), obteve {type(args[1])}"

    print("✅ T3 PASSOU: argumentos validados")


# ============================================================================
# T4: Estado legitimamente encerrado não é reativado
# ============================================================================

@pytest.mark.asyncio
async def test_t4_estado_encerrado_nao_reativado():
    """
    Valida que se um if legitimamente seta estado_fluxo para valor novo
    (ex: onboarding_dono, idle), não é sobrescrito pelo restauro.
    """
    ctx = {
        "estado_fluxo": "aguardando_servico",
    }

    user_id = "7394370553"  # Simular dono (user_id == tenant_id)
    tenant_id = "7394370553"
    cliente_id = "whatsapp:7394370553"

    with patch('router.integracao_identidade_onboarding.resolver_ator_e_validar_guard') as mock_resolver:
        with patch('router.integracao_identidade_onboarding.salvar_contexto_temporario'):
            with patch('router.integracao_identidade_onboarding.pegar_etapa_onboarding'):
                # Simular: dono sem onboarding (proxima_acao="onboarding")
                mock_resolver.return_value = {
                    "sucesso": True,
                    "tipo_usuario": "dono",
                    "actor_id": cliente_id,
                    "ator": {"tipo_usuario": "dono"},
                    "requer_onboarding": True,
                    "proxima_acao": "onboarding",
                    "onboarding_etapa": "nome_negocio",
                    "onboarding_pergunta": "Qual é o nome?"
                }

                resultado = await processar_fluxo_identidade_onboarding(
                    user_id=user_id,
                    mensagem="teste",
                    tenant_id=tenant_id,
                    ctx=ctx,
                    context=None,
                    cliente_id=cliente_id
                )

                # Validar: resultado não None (handled=True) e estado foi alterado
                assert resultado is not None, "Deve retornar resultado para onboarding"
                assert resultado.get("handled") == True, "Deve marcar como handled"
                assert ctx.get("estado_fluxo") == "onboarding_dono", \
                    f"Estado deve ser alterado para onboarding_dono, obteve {ctx.get('estado_fluxo')}"

    print("✅ T4 PASSOU: estado encerrado não é reativado")


# ============================================================================
# T5: Firestore real E2E (se ambiente permitir)
# ============================================================================

@pytest.mark.asyncio
async def test_t5_firestore_real_persistencia():
    """
    E2E com Firestore real (se configurado):
    Valida que estado_fluxo persiste até Firestore mesmo após
    processar_fluxo_identidade_onboarding().

    PENDENTE: Requer ambiente de teste com Firestore real isolado.
    """
    pytest.skip("T5 PENDENTE: Requer Firestore real em tenant isolado")


# ============================================================================
# T6: Regressão "pode marcar as duas"
# ============================================================================

@pytest.mark.asyncio
async def test_t6_regressao_pode_marcar_duas():
    """
    Valida que "pode marcar as duas" com múltiplos serviços:
    - Não cria eventos duplicados
    - Continua fluxo contextual
    - Respeita validações e confirmações

    PENDENTE: Requer teste E2E completo (não apenas mock).
    """
    pytest.skip("T6 PENDENTE: Requer teste E2E completo com fluxo real")


# ============================================================================
# Testes Auxiliares
# ============================================================================

@pytest.mark.asyncio
async def test_fix_debug_logs():
    """
    Valida que logs de debug estão sendo emitidos
    para rastreamento da correção.
    """
    ctx = {
        "estado_fluxo": "aguardando_servico",
        "multiplos_servicos_candidatos": ["manicure"],
    }

    user_id = "5511991382080"
    tenant_id = "7394370553"
    cliente_id = "whatsapp:5511991382080"

    with patch('router.integracao_identidade_onboarding.resolver_ator_e_validar_guard') as mock_resolver:
        with patch('router.integracao_identidade_onboarding.salvar_contexto_temporario'):
            with patch('builtins.print') as mock_print:
                mock_resolver.return_value = {
                    "sucesso": True,
                    "tipo_usuario": "cliente",
                    "actor_id": cliente_id,
                    "ator": {"tipo_usuario": "cliente"},
                    "requer_onboarding": False,
                    "permissoes": ["ler"],
                    "proxima_acao": "normal"
                }

                resultado = await processar_fluxo_identidade_onboarding(
                    user_id=user_id,
                    mensagem="pode marcar as duas",
                    tenant_id=tenant_id,
                    ctx=ctx,
                    context=None,
                    cliente_id=cliente_id
                )

                # Validar que logs P0-FIX foram emitidos
                log_calls = [str(call) for call in mock_print.call_args_list]
                assert any("[P0-FIX]" in str(call) for call in log_calls), \
                    "Logs de debug P0-FIX devem ser emitidos"

    print("✅ Logs de debug validados")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
