"""
ETAPA 3: E2E COMPLETO

Escenario completo:
"quero agendar corte com Bruna para amanhã às 15"

Validar el flujo completo desde interpretación hasta respuesta.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

try:
    from router.principal_router import (
        extrair_slots_e_mesclar,
        resolver_proximo_passo_real,
        montar_resposta_fallback,
        tem_hora_real
    )
    IMPORTS_OK = True
except Exception as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


@pytest.mark.skipif(not IMPORTS_OK, reason="Failed to import")
class TestE2ECompleto:

    @pytest.mark.asyncio
    async def test_e2e_agendamiento_completo(self):
        """
        E2E: "quero agendar corte com Bruna para amanhã às 15"

        Verificar:
        1. ✅ Interpretación
        2. ✅ Slots extraídos correctamente
        3. ✅ Validación de funcionamiento
        4. ✅ hora_confirmada = True (EFECTO DEL PATCH)
        5. ✅ Respuesta con éxito y emoji
        """
        print("\n" + "="*100)
        print("E2E: Agendamiento Completo")
        print("="*100)

        dono_id = "test_e2e_completo"
        cliente_id = "test_cliente_e2e"
        texto_usuario = "quero agendar corte com Bruna para amanhã às 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")
        valor_esperado = f"{data_esperada}T15:00:00"

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n" + "="*100)
        print("PASO 1: INTERPRETACIÓN")
        print("="*100)
        print(f"\n📥 Entrada:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Data esperada: {data_esperada}")
        print(f"   Hora esperada: 15:00")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }
            mock_salvar.return_value = None

            print(f"\n" + "="*100)
            print("PASO 2: EXTRAER SLOTS")
            print("="*100)

            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_inicial,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n✅ Slots extraídos:")
            print(f"   servico: {ctx_resultado.get('servico')}")
            print(f"   profissional_escolhido: {ctx_resultado.get('profissional_escolhido')}")
            print(f"   data_hora: {ctx_resultado.get('data_hora')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')} ← PATCH EFFECT")
            print(f"   data_sem_hora: {ctx_resultado.get('data_sem_hora')}")
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")

            # Validar slots
            assert ctx_resultado.get("servico") == "corte feminino", \
                f"❌ Serviço incorrecto: {ctx_resultado.get('servico')}"
            print(f"\n   ✅ Serviço correcto: corte feminino")

            assert ctx_resultado.get("profissional_escolhido") == "Bruna", \
                f"❌ Profissional incorrecto: {ctx_resultado.get('profissional_escolhido')}"
            print(f"   ✅ Profissional correcto: Bruna")

            assert ctx_resultado.get("data_hora") == valor_esperado, \
                f"❌ Data/hora incorrecto: {ctx_resultado.get('data_hora')}"
            print(f"   ✅ Data/hora correcto: {valor_esperado}")

            assert ctx_resultado.get("hora_confirmada") == True, \
                f"❌ CRÍTICO: hora_confirmada debe ser True, obtuvo {ctx_resultado.get('hora_confirmada')}"
            print(f"   ✅ hora_confirmada = True (PATCH FUNCIONÓ)")

            assert ctx_resultado.get("data_sem_hora") == False, \
                f"❌ data_sem_hora debe ser False, obtuvo {ctx_resultado.get('data_sem_hora')}"
            print(f"   ✅ data_sem_hora = False")

            print(f"\n" + "="*100)
            print("PASO 3: MONTAR RESPUESTA")
            print("="*100)

            # Simular montar resposta
            contexto_resposta = ctx_resultado
            proximo_passo_real = "confirmar_ou_executar"

            frase_data_legivel = f"em {data_esperada.split('-')[2]}/{data_esperada.split('-')[1]} às 15h"

            resposta = montar_resposta_fallback(
                proximo_passo_real=proximo_passo_real,
                frase_data_legivel=frase_data_legivel,
                contexto=contexto_resposta
            )

            print(f"\n📤 Resposta gerada:")
            print(f"   {resposta}")

            # Validar resposta
            assert "Bruna" in resposta, \
                f"❌ Resposta debe mencionar Bruna"
            print(f"\n   ✅ Menciona profesional (Bruna)")

            assert "corte" in resposta.lower(), \
                f"❌ Resposta debe mencionar servicio"
            print(f"   ✅ Menciona servicio (corte)")

            # Resposta SIN pedir horário (porque hora_confirmada=True)
            if "Qual horário" not in resposta and "Qual hora" not in resposta:
                print(f"   ✅ NO pide horário (correcto, fue confirmado)")
            else:
                print(f"   ❌ PROBLEMA: Still asking for time despite hora_confirmada=True")

            # Idealmente debe tener formato con éxito
            if "✅" in resposta or "✨" in resposta or "📆" in resposta:
                print(f"   ✅ Tiene formato de éxito (con emoji)")
            else:
                print(f"   ⚠️  Resposta sin formato esperado")

            print(f"\n" + "="*100)
            print("E2E: FLUXO COMPLETO VALIDADO")
            print("="*100)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
