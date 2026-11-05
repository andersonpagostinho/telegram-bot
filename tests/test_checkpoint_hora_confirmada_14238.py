"""
TESTE FINAL: Capturar hora_confirmada na linha 14238

Objetivo: Descobrir qual é o valor de contexto["hora_confirmada"]
quando montar_resposta_fallback() é chamada.

Cenário: "queria agendar corte com a bruna para amanha as 15"
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Monkey-patch montar_resposta_fallback para logar valores
original_montar_resposta = None

def hook_montar_resposta(proximo_passo_real, frase_data_legivel, contexto=None):
    """Hook para capturar valores de entrada"""
    contexto = contexto or {}

    print("\n" + "="*100)
    print("🎯 HOOK: montar_resposta_fallback() CHAMADA")
    print("="*100)
    print(f"\n📥 Parâmetros de entrada:")
    print(f"   proximo_passo_real: {proximo_passo_real!r}")
    print(f"   frase_data_legivel: {frase_data_legivel!r}")
    print(f"   contexto.hora_confirmada: {contexto.get('hora_confirmada')!r}")
    print(f"   contexto.servico: {contexto.get('servico')!r}")
    print(f"   contexto.profissional_escolhido: {contexto.get('profissional_escolhido')!r}")
    print(f"   contexto.data_hora: {contexto.get('data_hora')!r}")

    # Chamar função original
    resultado = original_montar_resposta(proximo_passo_real, frase_data_legivel, contexto)

    print(f"\n📤 Retorno:")
    print(f"   {resultado!r}")

    return resultado


try:
    from router.principal_router import montar_resposta_fallback
    IMPORTS_OK = True
except Exception as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


@pytest.mark.skipif(not IMPORTS_OK, reason="Failed to import")
class TestHoraConfirmadaCheckpoint:
    """
    Simula o fluxo até o ponto 14238.
    """

    @pytest.mark.asyncio
    async def test_capturar_hora_confirmada_no_ponto_14238(self):
        """
        Objetivo: Saber qual é contexto["hora_confirmada"]
        quando montar_resposta_fallback() é chamada.
        """
        global original_montar_resposta
        original_montar_resposta = montar_resposta_fallback

        print("\n" + "="*100)
        print("TESTE: Capturar hora_confirmada em linha 14238")
        print("="*100)

        # Simular contexto após extrair_slots_e_mesclar()
        # (conforme confirmado no teste anterior)
        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")

        # TESTE 1: Com hora_confirmada = True
        contexto_com_confirmada_true = {
            "estado_fluxo": "aguardando_profissional",
            "hora_confirmada": True,  # ← Conforme setado em linha 1930
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": f"{data_esperada}T15:00:00",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "corte feminino",
                "data_hora": f"{data_esperada}T15:00:00",
            }
        }

        # TESTE 2: Com hora_confirmada = False
        contexto_com_confirmada_false = {
            "estado_fluxo": "aguardando_profissional",
            "hora_confirmada": False,  # ← Se for reset para False em algum lugar
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "data_hora": f"{data_esperada}T15:00:00",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "corte feminino",
                "data_hora": f"{data_esperada}T15:00:00",
            }
        }

        contexto_simulado = contexto_com_confirmada_true

        print(f"\n📥 Contexto simulado (após extrair_slots_e_mesclar):")
        print(f"   estado_fluxo: {contexto_simulado['estado_fluxo']}")
        print(f"   hora_confirmada: {contexto_simulado['hora_confirmada']}")
        print(f"   servico: {contexto_simulado['servico']}")
        print(f"   profissional_escolhido: {contexto_simulado['profissional_escolhido']}")
        print(f"   data_hora: {contexto_simulado['data_hora']}")

        # Montar resposta como faria a linha 14238
        with patch('router.principal_router.montar_resposta_fallback',
                   side_effect=hook_montar_resposta):
            # Chamar com hook
            resposta = hook_montar_resposta(
                proximo_passo_real="confirmar_ou_executar",
                frase_data_legivel=f"para {data_esperada} às 15h",
                contexto=contexto_simulado
            )

        print("\n" + "="*100)
        print("ANÁLISE")
        print("="*100)
        print(f"\n✅ Contexto tinha:")
        print(f"   hora_confirmada = {contexto_simulado.get('hora_confirmada')}")
        print(f"\n📤 Resposta gerada:")
        print(f"   {resposta!r}")

        if "Qual horário" in resposta:
            print(f"\n❌ PROBLEMA ENCONTRADO:")
            print(f"   A resposta PEDIU horário, mas contexto.hora_confirmada = True")
            print(f"   Isso significa que montar_resposta_fallback() tem um BUG")
            print(f"   na linha 572-581: Ignora proximo_passo_real='confirmar_ou_executar'")
            print(f"   e volta para a condição antiga (que pede horário)")
        else:
            print(f"\n✅ Resposta CORRETA (não pediu horário)")


if __name__ == "__main__":
    print("Teste: Capturar hora_confirmada em linha 14238")
    print("Execute com: pytest tests/test_checkpoint_hora_confirmada_14238.py -v -s")
