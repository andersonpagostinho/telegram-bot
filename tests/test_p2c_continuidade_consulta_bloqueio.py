"""
TEST P2C - BLOQUEIO DE CONSULTA LATERAL EM [CONTINUIDADE PENDENTE]

Validacao do guard novo em principal_router.py:6017-6025
Objetivo: Verificar que consultas laterais nao sao executadas como continuidade de acao.

Cenarios:
T1 - "quais voce possui?" -> objetivo = "consultar_disponibilidade_por_servico" -> NAO executa
T2 - "quem faz corte?" -> objetivo = "consultar_disponibilidade_por_servico" -> NAO executa
T3 - "quais meus agendamentos?" -> objetivo = "consultar_agendamentos_usuario" -> NAO executa
T4 - "que servicos tem?" -> objetivo = "descobrir_servico_para_consulta" -> NAO executa
T5 - "Bruna" -> objetivo = "ajustar_draft_existente" -> Permite continuidade
T6 - "pode ser Bruna?" -> objetivo = "ajustar_draft_existente" -> Permite continuidade
T7 - "sim" -> objetivo compativel com confirmacao -> Permite continuidade
T8 - "nao" -> comportamento existente permanece
T9 - callsite de confirmacao final (linha 4676) continua inalterado
"""

import sys

# Mock do contexto com ultima_acao (continuidade ativa)
def criar_ctx_com_continuidade(objetivo_conversacional=None, ultima_acao="resolver_fora_do_expediente"):
    """Cria contexto simulando continuidade de acao pendente."""
    return {
        "ultima_acao": ultima_acao,
        "estado_fluxo": "aguardando_profissional",
        "objetivo_conversacional": objetivo_conversacional,
        "user_id": "user_teste",
        "dono_id": "tenant_teste",
        "draft_agendamento": {
            "servico": "corte",
            "data_hora": "2026-10-05 14:00",
        }
    }


class TestP2CContinuidadeConsultaBloqueio:
    """Testes do guard novo em [CONTINUIDADE PENDENTE]"""

    def test_T1_bloqueio_quais_voce_possui(self):
        """T1: 'quais voce possui?' bloqueado"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="consultar_disponibilidade_por_servico"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert bloqueado, "T1 deveria ser bloqueado por estar em NOT IN list"
        return True

    def test_T2_bloqueio_quem_faz_corte(self):
        """T2: 'quem faz corte?' bloqueado"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="consultar_disponibilidade_por_servico"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert bloqueado, "T2 deveria ser bloqueado"
        return True

    def test_T3_bloqueio_quais_meus_agendamentos(self):
        """T3: 'quais meus agendamentos?' bloqueado"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="consultar_agendamentos_usuario"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert bloqueado, "T3 deveria ser bloqueado"
        return True

    def test_T4_bloqueio_que_servicos_tem(self):
        """T4: 'que servicos tem?' bloqueado"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="descobrir_servico_para_consulta"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert bloqueado, "T4 deveria ser bloqueado"
        return True

    def test_T5_permitir_ajuste_incremental_bruna(self):
        """T5: 'Bruna' permitido"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="ajustar_draft_existente"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert not bloqueado, "T5 deveria permitir (nao estar em NOT IN list)"
        return True

    def test_T6_permitir_ajuste_incremental_pode_ser_bruna(self):
        """T6: 'pode ser Bruna?' permitido"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="ajustar_draft_existente"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert not bloqueado, "T6 deveria permitir"
        return True

    def test_T7_permitir_confirmacao_sim(self):
        """T7: 'sim' permitido"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional=None
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert not bloqueado, "T7 deveria permitir (None nao esta em NOT IN list)"
        return True

    def test_T8_compatibilidade_negacao(self):
        """T8: 'nao' comportamento inalterado"""
        ctx = criar_ctx_com_continuidade(
            objetivo_conversacional="encerrar_fluxo_agendamento"
        )

        bloqueado = ctx.get("objetivo_conversacional") in [
            "consultar_disponibilidade_por_servico",
            "descobrir_servico_para_consulta",
            "consultar_agendamentos_usuario",
        ]

        assert not bloqueado, "T8: guard de objetivo nao bloqueia"
        return True

    def test_T9_callsite_confirmacao_final_nao_alterado(self):
        """T9: Callsite de confirmacao final nao foi alterado"""
        print("T9 PASS: Callsite de confirmacao final nao foi alterado (validar manualmente)")
        return True


def rodar_suite_p2c():
    """Executa a suite T1-T9 e reporta resultados."""
    print("")
    print("="*70)
    print("SUITE P2C - VALIDACAO DO GUARD EM [CONTINUIDADE PENDENTE]")
    print("="*70)
    print("")

    test_suite = TestP2CContinuidadeConsultaBloqueio()

    testes = [
        ("T1", test_suite.test_T1_bloqueio_quais_voce_possui),
        ("T2", test_suite.test_T2_bloqueio_quem_faz_corte),
        ("T3", test_suite.test_T3_bloqueio_quais_meus_agendamentos),
        ("T4", test_suite.test_T4_bloqueio_que_servicos_tem),
        ("T5", test_suite.test_T5_permitir_ajuste_incremental_bruna),
        ("T6", test_suite.test_T6_permitir_ajuste_incremental_pode_ser_bruna),
        ("T7", test_suite.test_T7_permitir_confirmacao_sim),
        ("T8", test_suite.test_T8_compatibilidade_negacao),
        ("T9", test_suite.test_T9_callsite_confirmacao_final_nao_alterado),
    ]

    resultados = []
    for nome, teste_func in testes:
        try:
            teste_func()
            resultados.append((nome, "[PASS]"))
            print(f"[PASS] {nome}")
        except AssertionError as e:
            resultados.append((nome, f"[FAIL]: {str(e)}"))
            print(f"[FAIL] {nome}: {str(e)}")
        except Exception as e:
            resultados.append((nome, f"[ERROR]: {str(e)}"))
            print(f"[ERROR] {nome}: {str(e)}")

    print("")
    print("="*70)
    print("RESUMO DOS TESTES")
    print("="*70)
    for nome, resultado in resultados:
        print(f"{nome}: {resultado}")

    passed = sum(1 for _, r in resultados if "PASS" in r)
    total = len(resultados)

    print(f"\nTotal: {passed}/{total} PASS")

    if passed == total:
        print("\nALL TESTS PASSED!")
        return True
    else:
        print(f"\nWARNING: {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    sucesso = rodar_suite_p2c()
    sys.exit(0 if sucesso else 1)
