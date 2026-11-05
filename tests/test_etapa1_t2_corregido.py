"""
T2 CORREGIDO: Solo Data con Fecha Permitida

Objetivo: Validar que el patch NO setea hora_confirmada=True
cuando el usuario solo menciona data sin hora.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

try:
    from router.principal_router import extrair_slots_e_mesclar
    IMPORTS_OK = True
except Exception as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


@pytest.mark.skipif(not IMPORTS_OK, reason="Failed to import")
class TestT2Corregido:

    @pytest.mark.asyncio
    async def test_t2_solo_data_viernes(self):
        """
        T2: Usuario menciona solo data (sin hora) en fecha permitida
        Texto: "quero agendar corte para sexta-feira"
        Fecha: 2026-11-06 (viernes, típicamente abierto)

        Esperado:
        - hora_confirmada ≠ True (NO inventar hora)
        - Usuario menciona solo data → el sistema debe pedir hora después
        """
        print("\n" + "="*100)
        print("T2 CORREGIDO: Solo Data (Viernes)")
        print("="*100)

        dono_id = "test_t2_viernes"
        cliente_id = "test_cliente_t2"
        # Viernes próximo
        viernes = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if viernes.weekday() != 4:  # Si no es viernes
            viernes = viernes + timedelta(days=(4 - viernes.weekday()))

        data_viernes = viernes.strftime("%Y-%m-%d")

        # Texto con fecha relativa
        texto_usuario = "quero agendar corte para sexta-feira"

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Cenário:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Data extraída esperada: {data_viernes}")
        print(f"   Hora: NO mencionada")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }
            mock_salvar.return_value = None

            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_inicial,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n📤 Resultado:")
            print(f"   data_hora: {ctx_resultado.get('data_hora')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")
            print(f"   data_sem_hora: {ctx_resultado.get('data_sem_hora')}")
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")

            # Validación crítica: NO inventar hora_confirmada
            assert ctx_resultado.get("hora_confirmada") != True, \
                f"❌ CRÍTICO: NO debe setear hora_confirmada=True cuando usuario menciona solo data"
            print(f"   ✅ hora_confirmada ≠ True (correcto, no inventó hora)")

            # Si hay data_hora, no debe tener hora específica (debe ser 00:00 o None)
            data_hora = ctx_resultado.get("data_hora")
            if data_hora:
                assert "T00:00" in data_hora or data_hora.endswith("T00:00:00"), \
                    f"⚠️  Data sin hora debe tener 00:00, obtuvo {data_hora}"
                print(f"   ✅ data_hora no tiene hora específica (tiene 00:00)")

            print(f"\n✅ T2 CORREGIDO PASÓ")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
