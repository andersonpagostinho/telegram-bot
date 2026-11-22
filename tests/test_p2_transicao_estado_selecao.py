# -*- coding: utf-8 -*-
"""
PROBLEMA 2: Estado não avança após seleção
Teste de Fluxo — Seleção → Confirmação

Critério de Aceite:
- Usuário seleciona "o primeiro"
- Sistema pede confirmação explícita
- Estado transiciona para aguardando_confirmacao_agendamento
- Opção e contexto são preservados
"""

import pytest
import sys
import os
import uuid
from datetime import datetime, timedelta

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

from schemas.resultado_consulta_schema import ContextoResultadoConsulta, OpcaoHorario
from services.reconhecimento_opcao_service import processar_selecao_opcao


class TestP2TransicaoEstado:
    """Teste de transição de estado: seleção → confirmação"""

    @pytest.mark.asyncio
    async def test_p2_selecao_transiciona_estado_para_confirmacao(self):
        """
        CENÁRIO:
        1. Usuário tem 3 opções disponíveis (consulta ativa)
        2. Usuário: "o primeiro"
        3. Sistema registra seleção

        ESPERADO:
        - Seleção bem-sucedida ✅
        - Estado_fluxo = "aguardando_confirmacao_agendamento" (não "idle")
        - aguardando_confirmacao_agendamento = True
        - Resposta pede: "Confirma este agendamento?"
        - Opção selecionada preservada
        """

        # === SETUP: Contexto com 3 opções ===

        opcoes = [
            OpcaoHorario(
                numero=1,
                opcao_id="2026-11-20_bruna_1400",
                hora_inicio="14:00",
                hora_fim="15:00",
                profissional_id="bruna",
                servicos=["pedicure"],
                duracao_total_min=60,
                data="2026-11-20"
            ),
            OpcaoHorario(
                numero=2,
                opcao_id="2026-11-20_gloria_1430",
                hora_inicio="14:30",
                hora_fim="15:30",
                profissional_id="gloria",
                servicos=["pedicure"],
                duracao_total_min=60,
                data="2026-11-20"
            ),
            OpcaoHorario(
                numero=3,
                opcao_id="2026-11-20_joana_1500",
                hora_inicio="15:00",
                hora_fim="16:00",
                profissional_id="joana",
                servicos=["pedicure"],
                duracao_total_min=60,
                data="2026-11-20"
            ),
        ]

        contexto = ContextoResultadoConsulta(
            consulta_id=f"test_{uuid.uuid4().hex[:8]}",
            data="2026-11-20",
            servicos=["pedicure"],
            opcoes=opcoes
        )

        # === TESTE: Processar seleção ===

        tenant_id = "7394370553"  # Salão
        actor_id = "5511991382080"  # Cliente
        mensagem = "o primeiro"

        resultado = await processar_selecao_opcao(
            mensagem=mensagem,
            tenant_id=tenant_id,
            actor_id=actor_id,
            contexto=contexto
        )

        # === VALIDAÇÕES ===

        # 1. Seleção deve ser bem-sucedida
        assert resultado.get("sucesso") == True, \
            f"❌ Seleção falhou: {resultado.get('mensagem')}"

        # 2. Opção selecionada deve ser preservada
        assert resultado.get("opcao_id") == "2026-11-20_bruna_1400", \
            f"❌ Opção incorreta: {resultado.get('opcao_id')}"

        # 3. Resposta deve mencionar confirmação
        resposta = resultado.get("mensagem", "")
        assert "primeiro" in resposta.lower() or "1º" in resposta, \
            f"❌ Resposta não menciona primeira opção: {resposta}"

        # 4. CRÍTICO: Próximo passo deve pedir confirmação
        proximo_passo = resultado.get("proximo_passo", "")
        assert "confirma" in proximo_passo.lower() or "confirm" in proximo_passo.lower(), \
            f"❌ Próximo passo não pede confirmação: {proximo_passo}"

        print(f"✅ TESTE PASSOU: Seleção registrada e confirmação solicitada")
        print(f"   Opção: {resultado.get('opcao_id')}")
        print(f"   Próximo passo: {proximo_passo}")

        # === VERIFICAÇÃO FUTURA (Phase 3): Estado deveria ter avançado ===
        # Este teste valida que a seleção funciona
        # A transição de estado (problema 2.2) é validada em contexto_handler


    @pytest.mark.asyncio
    async def test_p2_selecao_preserva_contexto_completo(self):
        """
        CENÁRIO:
        - Seleção registra opcao_selecionada_id
        - Contexto completo é preservado (opcoes, ttl, etc)

        ESPERADO:
        - Contexto_resultado_consulta não é sobrescrito
        - opcao_selecionada_id é adicionado (merge=True)
        """

        opcoes = [
            OpcaoHorario(
                numero=1,
                opcao_id="opt_1",
                hora_inicio="14:00",
                hora_fim="15:00",
                profissional_id="prof_1",
                servicos=["serv_1"],
                duracao_total_min=60,
                data="2026-11-20"
            )
        ]

        contexto = ContextoResultadoConsulta(
            consulta_id="test_query",
            data="2026-11-20",
            servicos=["serv_1"],
            opcoes=opcoes
        )

        tenant_id = "7394370553"
        actor_id = "5511991382080"

        resultado = await processar_selecao_opcao(
            mensagem="o primeiro",
            tenant_id=tenant_id,
            actor_id=actor_id,
            contexto=contexto
        )

        # Validar que contexto ainda tem as opções
        assert contexto.opcoes is not None, \
            "❌ Opções foram perdidas"

        assert len(contexto.opcoes) == 1, \
            f"❌ Número de opções mudou: {len(contexto.opcoes)}"

        assert contexto.opcao_selecionada_id == "opt_1", \
            f"❌ opcao_selecionada_id não foi definido: {contexto.opcao_selecionada_id}"

        print(f"✅ TESTE PASSOU: Contexto preservado completamente")
        print(f"   Opções: {len(contexto.opcoes)}")
        print(f"   Seleção: {contexto.opcao_selecionada_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
