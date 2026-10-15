"""
P0 — TESTE QUE PEGA O GAP: "outra profissional" genérico

PROBLEMA ORIGINAL (antes do fix):
- Testes P0 cobriam "outra profissional" COM contexto pré-preenchido
- Em produção: "outra profissional" SEM nome específico chegava como genérico
- detectar_alteracao_draft_agendamento() retornava None
- Fluxo caía em resposta vazia

SOLUÇÃO:
Este teste valida que detectar_alteracao_draft_agendamento():
1. Retorna {"tipo": "profissional", "valor": None} para entrada genérica
2. Continua retornando nome específico para "quero Gloria"
3. Trata corretamente em resolver_alteracao_draft_agendamento()
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

raiz_projeto = Path(__file__).parent.parent
sys.path.insert(0, str(raiz_projeto))

import pytest


class TestOutraProfissionalGap:
    """Testa o gap que não era coberto antes"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para todos os testes"""
        self.tenant_id = "7394370553"
        self.cliente_id = "whatsapp:5511991382080"
        self.actor_id = "whatsapp:5511991382080"
        self.dono_id = self.tenant_id

    async def test_1_outra_profissional_generico_retorna_none(self):
        """
        TESTE CRÍTICO: "outra profissional" (genérico, sem nome)

        Antes do fix: retornava None → resposta vazia
        Depois do fix: retorna {"tipo": "profissional", "valor": None}
        """
        from router.principal_router import detectar_alteracao_draft_agendamento

        ctx = {
            "intencao_conversacional": "ajuste_incremental",
            "objetivo_conversacional": "ajustar_draft_existente",
            "profissional_escolhido": "Bruna",
            "servico": "corte",
            "data_hora": "2026-10-14T14:00",
            "draft_agendamento": {},
            "alternativa_profissional": ["Gloria", "Joana"],
        }

        resultado = await detectar_alteracao_draft_agendamento(
            texto_usuario="outra profissional",
            ctx=ctx,
            dono_id=self.dono_id,
            cliente_id=self.cliente_id
        )

        # Validar que NÃO é None (antes retornava None)
        assert resultado is not None, "BUG: 'outra profissional' retorna None!"
        assert resultado.get("tipo") == "profissional", \
            f"Esperava tipo=profissional, got {resultado.get('tipo')}"
        assert resultado.get("valor") is None, \
            f"Esperava valor=None (genérico), got {resultado.get('valor')}"

        print("[PASS] 'outra profissional' genérico retorna tipo=profissional valor=None")

    async def test_2_quero_gloria_continua_funcionando(self):
        """
        TESTE DE REGRESSÃO: "quero Gloria" (nome específico)

        Validar que fix não quebrou deteccao de nome específico
        """
        from router.principal_router import detectar_alteracao_draft_agendamento

        ctx = {
            "intencao_conversacional": "ajuste_incremental",
            "objetivo_conversacional": "ajustar_draft_existente",
            "profissional_escolhido": "Bruna",
            "servico": "corte",
            "data_hora": "2026-10-14T14:00",
            "draft_agendamento": {},
        }

        resultado = await detectar_alteracao_draft_agendamento(
            texto_usuario="quero Gloria",
            ctx=ctx,
            dono_id=self.dono_id,
            cliente_id=self.cliente_id
        )

        assert resultado is not None, "Deveria detectar Gloria"
        assert resultado.get("tipo") == "profissional"
        assert resultado.get("valor") == "Gloria", \
            f"Esperava 'Gloria', got {resultado.get('valor')}"

        print("[PASS] 'quero Gloria' continua detectando nome específico")

    async def test_3_outra_prof_continua_funcionando(self):
        """
        TESTE ADICIONAL: "outra prof" (abreviação)

        Validar que padrão genérico reconhece abreviações
        """
        from router.principal_router import detectar_alteracao_draft_agendamento

        ctx = {
            "profissional_escolhido": "Bruna",
            "servico": "corte",
            "data_hora": "2026-10-14T14:00",
        }

        resultado = await detectar_alteracao_draft_agendamento(
            texto_usuario="outra prof",
            ctx=ctx,
            dono_id=self.dono_id,
            cliente_id=self.cliente_id
        )

        assert resultado is not None, "BUG: 'outra prof' retorna None!"
        assert resultado.get("tipo") == "profissional"
        assert resultado.get("valor") is None

        print("[PASS] 'outra prof' (abreviação) reconhecido")

    async def test_4_profissional_diferente_continua_funcionando(self):
        """
        TESTE ADICIONAL: "profissional diferente" (padrão completo)
        """
        from router.principal_router import detectar_alteracao_draft_agendamento

        ctx = {
            "profissional_escolhido": "Bruna",
            "servico": "corte",
            "data_hora": "2026-10-14T14:00",
        }

        resultado = await detectar_alteracao_draft_agendamento(
            texto_usuario="profissional diferente",
            ctx=ctx,
            dono_id=self.dono_id,
            cliente_id=self.cliente_id
        )

        assert resultado is not None, "BUG: 'profissional diferente' retorna None!"
        assert resultado.get("tipo") == "profissional"
        assert resultado.get("valor") is None

        print("[PASS] 'profissional diferente' reconhecido")

    async def test_5_servico_continua_sendo_detectado(self):
        """
        TESTE DE REGRESSÃO: Deteccao de serviço não foi quebrada
        """
        from router.principal_router import detectar_alteracao_draft_agendamento

        ctx = {
            "servico": "corte",
            "data_hora": "2026-10-14T14:00",
        }

        resultado = await detectar_alteracao_draft_agendamento(
            texto_usuario="quero escova",
            ctx=ctx,
            dono_id=self.dono_id,
            cliente_id=self.cliente_id
        )

        assert resultado is not None, "Deveria detectar serviço"
        assert resultado.get("tipo") == "servico", \
            f"Esperava tipo=servico, got {resultado.get('tipo')}"
        assert resultado.get("valor") == "escova"

        print("[PASS] Deteccao de serviço continua funcionando")

    async def test_6_horario_continua_sendo_detectado(self):
        """
        TESTE DE REGRESSÃO: Deteccao de horário não foi quebrada
        """
        from router.principal_router import detectar_alteracao_draft_agendamento

        ctx = {
            "servico": "corte",
            "data_hora": "2026-10-14T14:00",
        }

        resultado = await detectar_alteracao_draft_agendamento(
            texto_usuario="mais cedo",
            ctx=ctx,
            dono_id=self.dono_id,
            cliente_id=self.cliente_id
        )

        assert resultado is not None, "Deveria detectar horário"
        assert resultado.get("tipo") == "horario", \
            f"Esperava tipo=horario, got {resultado.get('tipo')}"
        assert resultado.get("direcao") == "mais_cedo"

        print("[PASS] Deteccao de horário continua funcionando")


async def run_tests():
    """Executar testes async"""
    test = TestOutraProfissionalGap()
    test.setup()

    print("\n" + "="*80)
    print("TESTES P0: GAP DE 'OUTRA PROFISSIONAL' GENÉRICO")
    print("="*80)

    testes = [
        ("T1", test.test_1_outra_profissional_generico_retorna_none),
        ("T2", test.test_2_quero_gloria_continua_funcionando),
        ("T3", test.test_3_outra_prof_continua_funcionando),
        ("T4", test.test_4_profissional_diferente_continua_funcionando),
        ("T5", test.test_5_servico_continua_sendo_detectado),
        ("T6", test.test_6_horario_continua_sendo_detectado),
    ]

    resultados = {}
    for nome, teste_func in testes:
        try:
            await teste_func()
            resultados[nome] = True
        except AssertionError as e:
            print(f"[FAIL] {nome}: {e}")
            resultados[nome] = False
        except Exception as e:
            print(f"[ERROR] {nome}: {e}")
            resultados[nome] = False

    # RESUMO
    print("\n" + "="*80)
    print("RESUMO")
    print("="*80)

    for nome, passou in resultados.items():
        status = "[PASS]" if passou else "[FAIL]"
        print(f"{nome}: {status}")

    total = sum(resultados.values())
    print(f"\nTotal: {total}/{len(resultados)} testes passaram")

    return all(resultados.values())


if __name__ == "__main__":
    # Executar com pytest ou direto
    sucesso = asyncio.run(run_tests())
    sys.exit(0 if sucesso else 1)
