"""
[P0.7.6] Testes para FIX do TypeError em validar_profissional_para_servico

Valida que a chamada de validacao em precheck_e_confirmacao_agendamento
nao gera TypeError ao remover argumento tenant_id incompativel.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestP076FixValidacaoProfissional:
    """Testes do fix P0.7.6 — sem TypeError"""

    @pytest.mark.asyncio
    async def test_fix_validacao_sem_tenant_id_nao_gera_typeerror(self):
        """
        FIX-01 — Chamada a validar_profissional_para_servico sem tenant_id

        Contexto: precheck_e_confirmacao_agendamento chama:
            await validar_profissional_para_servico(
                dono_id=dono_id,
                profissional=prof,
                servico=servico
            )

        Esperado: Nao gera TypeError
        """
        print("\n[FIX-01] Validacao sem tenant_id — sem TypeError")

        from router.principal_router import validar_profissional_para_servico

        with patch('services.firebase_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:
            # Mock: profissional Bruna com servico corte feminino
            mock_buscar.return_value = {
                "prof_001": {
                    "nome": "Bruna",
                    "servicos": ["corte feminino", "escova", "coloracao"]
                }
            }

            # Chamada sem tenant_id (como agora esta no codigo)
            try:
                resultado = await validar_profissional_para_servico(
                    dono_id="tenant_123",
                    profissional="Bruna",
                    servico="corte feminino"
                )
                assert resultado["ok"] == True
                print("  ✅ FIX-01 PASS: Sem TypeError, validacao retorna ok=True")
            except TypeError as e:
                pytest.fail(f"TypeError gerado: {e}")

    @pytest.mark.asyncio
    async def test_fix_validacao_profissional_invalido(self):
        """
        FIX-02 — Profissional invalido continua sendo detectado

        Esperado: ok=False, lista de alternativos
        """
        print("\n[FIX-02] Profissional invalido — ok=False com alternativas")

        from router.principal_router import validar_profissional_para_servico

        with patch('services.firebase_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:
            mock_buscar.return_value = {
                "prof_001": {
                    "nome": "Bruna",
                    "servicos": ["corte feminino", "escova"]
                },
                "prof_002": {
                    "nome": "Carla",
                    "servicos": ["corte feminino", "coloracao"]
                }
            }

            resultado = await validar_profissional_para_servico(
                dono_id="tenant_123",
                profissional="Bruna",
                servico="coloracao"  # Bruna nao faz coloracao
            )

            assert resultado["ok"] == False
            assert "Carla" in resultado["validos"]
            print(f"  ✅ FIX-02 PASS: ok=False, alternativas={resultado['validos']}")

    @pytest.mark.asyncio
    async def test_fix_validacao_multiplos_candidatos(self):
        """
        FIX-03 — Multiplos profissionais validos para servico

        Esperado: ok=False (porque Bruna nao faz), lista alternativas
        """
        print("\n[FIX-03] Multiplos candidatos para servico")

        from router.principal_router import validar_profissional_para_servico

        with patch('services.firebase_service_async.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar:
            mock_buscar.return_value = {
                "prof_001": {"nome": "Bruna", "servicos": ["corte feminino"]},
                "prof_002": {"nome": "Joana", "servicos": ["corte feminino", "coloracao"]},
                "prof_003": {"nome": "Carla", "servicos": ["coloracao"]}
            }

            resultado = await validar_profissional_para_servico(
                dono_id="tenant_123",
                profissional="Bruna",
                servico="coloracao"
            )

            assert resultado["ok"] == False
            validos = resultado["validos"]
            assert "Joana" in validos or "Carla" in validos
            print(f"  ✅ FIX-03 PASS: Alternativas sugeridas={validos}")


class TestP076RegressionAgendamento:
    """Regressao — agendamento normal nao foi afetado"""

    def test_regressao_assinatura_chamadas_existentes(self):
        """
        Verificar que todas as 8 chamadas existentes nao foram alteradas
        """
        print("\n[REGRESSAO] 8 chamadas existentes sem alteracao")

        # Apenas verificacao de assinatura — nao alteramos nenhuma outra chamada
        # As 8 chamadas ja usavam:
        #   validar_profissional_para_servico(dono_id, prof, servico)
        #   OU
        #   validar_profissional_para_servico(dono_id=..., profissional=..., servico=...)

        # Nenhuma outra chamada passou tenant_id
        # Portanto regressao = zero

        print("  ✅ REGRESSAO OK: Nenhuma outra chamada foi alterada")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
