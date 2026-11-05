"""
TESTE DE VALIDAÇÃO: Confirmar causa raiz de dupla chamada

Objetivo: Validar que a segunda chamada a extrair_slots_e_mesclar()
realmente executa CASO 3 e reseta hora_confirmada.

Cenário: "queria agendar corte com a bruna para amanha as 15"
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

try:
    from router.principal_router import extrair_slots_e_mesclar
    IMPORTS_OK = True
except Exception as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


@pytest.mark.skipif(not IMPORTS_OK, reason="Failed to import")
class TestValidacaoDuplaChamada:

    @pytest.mark.asyncio
    async def test_confirmar_reset_em_segunda_chamada(self):
        """
        Simular:
        1. PRIMEIRA chamada a extrair_slots_e_mesclar() com estado inicial
        2. SEGUNDA chamada com estado "aguardando_profissional" (resultado da primeira)

        Validar se a segunda reseta hora_confirmada.
        """
        print("\n" + "="*100)
        print("TESTE DE VALIDAÇÃO: Dupla Chamada a extrair_slots_e_mesclar()")
        print("="*100)

        dono_id = "test_dupla_chamada"
        cliente_id = "test_cliente_dupla"
        texto_usuario = "queria agendar corte com a bruna para amanha as 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")

        # =====================================================
        # PRIMEIRA CHAMADA
        # =====================================================
        print("\n📋 PRIMEIRA CHAMADA:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Estado: idle")

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }
            mock_salvar.return_value = None

            ctx_apos_primeira = await extrair_slots_e_mesclar(
                ctx_inicial,
                texto_usuario,
                dono_id,
                cliente_id
            )

        print(f"\n   Resultado PRIMEIRA chamada:")
        print(f"   - estado_fluxo: {ctx_apos_primeira.get('estado_fluxo')}")
        print(f"   - hora_confirmada: {ctx_apos_primeira.get('hora_confirmada')}")
        print(f"   - data_hora: {ctx_apos_primeira.get('data_hora')}")
        print(f"   - servico: {ctx_apos_primeira.get('servico')}")
        print(f"   - profissional_escolhido: {ctx_apos_primeira.get('profissional_escolhido')}")

        assert ctx_apos_primeira.get("hora_confirmada") == True, \
            "FALHA: Primeira chamada deveria settar hora_confirmada=True"

        valor_primeira = ctx_apos_primeira.get("hora_confirmada")
        print(f"\n   ✅ Primeira chamada setou hora_confirmada = {valor_primeira}")

        # =====================================================
        # SEGUNDA CHAMADA (com estado após primeira)
        # =====================================================
        print("\n📋 SEGUNDA CHAMADA:")
        print(f"   Texto: '{texto_usuario}' (MESMA mensagem)")
        print(f"   Estado inicial: aguardando_profissional (resultado da primeira)")
        print(f"   Contexto: resultado da primeira chamada")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }
            mock_salvar.return_value = None

            ctx_apos_segunda = await extrair_slots_e_mesclar(
                ctx_apos_primeira,  # Passa o resultado da primeira
                texto_usuario,       # Mesma mensagem
                dono_id,
                cliente_id
            )

        print(f"\n   Resultado SEGUNDA chamada:")
        print(f"   - estado_fluxo: {ctx_apos_segunda.get('estado_fluxo')}")
        print(f"   - hora_confirmada: {ctx_apos_segunda.get('hora_confirmada')}")
        print(f"   - data_hora: {ctx_apos_segunda.get('data_hora')}")
        print(f"   - data_sem_hora: {ctx_apos_segunda.get('data_sem_hora')}")

        valor_segunda = ctx_apos_segunda.get("hora_confirmada")

        # =====================================================
        # ANÁLISE
        # =====================================================
        print("\n" + "="*100)
        print("ANÁLISE")
        print("="*100)

        print(f"\nComparação:")
        print(f"  Primeira:  hora_confirmada = {valor_primeira}")
        print(f"  Segunda:   hora_confirmada = {valor_segunda}")

        if valor_primeira == True and valor_segunda == False:
            print(f"\n🔴 PROBLEMA CONFIRMADO:")
            print(f"   Segunda chamada RESETS hora_confirmada de True para False!")
            print(f"   Estado da segunda: {ctx_apos_segunda.get('estado_fluxo')}")
            print(f"   Data sem hora: {ctx_apos_segunda.get('data_sem_hora')}")
            print(f"\n   CAUSA PROVÁVEL: Está em CASO 3 com data_sem_hora=True")

            if ctx_apos_segunda.get('data_sem_hora') == True:
                print(f"   ✅ CONFIRMADO: data_sem_hora foi setada na segunda chamada")
                print(f"   Isso ativa a lógica de pedir horário separadamente")
        elif valor_primeira == True and valor_segunda == True:
            print(f"\n✅ NÃO HÁ PROBLEMA:")
            print(f"   Segunda chamada preservou hora_confirmada=True")
        else:
            print(f"\n❓ RESULTADO INESPERADO:")
            print(f"   Primeira retornou: {valor_primeira}")
            print(f"   Segunda retornou: {valor_segunda}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
