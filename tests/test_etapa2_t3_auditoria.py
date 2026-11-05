"""
T3 AUDITORIA: Solo Hora - Rastrear Origen

Objetivo: Verificar que cuando usuario menciona solo hora ("às 15"),
el sistema reutiliza data anterior y marca hora_confirmada=True
de forma CORRECTA (la hora vino del usuario actual, la data es anterior).
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
class TestT3Auditoria:

    @pytest.mark.asyncio
    async def test_t3_auditoria_origen_hora(self):
        """
        T3 AUDITORIA: Usuario menciona solo hora en contexto con data anterior

        Rastrear:
        1. De dónde viene la data (contexto anterior)
        2. De dónde viene la hora (mensaje actual)
        3. Si hora_confirmada es True (hora vino del usuario en este mensaje)

        Escenario:
        - Primer mensaje: "quero agendar para amanhã às 15"
          → data_hora = "2026-11-05T15:00:00", hora_confirmada = True

        - Segundo mensaje: "às 16" (cambió de opinión sobre la hora)
          → Esperado: reutilizar data 2026-11-05, setear hora 16:00
          → hora_confirmada = True (hora fue mencionada en este mensaje)
        """
        print("\n" + "="*100)
        print("T3 AUDITORIA: Origen de la Hora")
        print("="*100)

        dono_id = "test_t3_auditoria"
        cliente_id = "test_cliente_t3"

        # Contexto del primer mensaje: data+hora
        ctx_primer_mensaje = {
            "estado_fluxo": "agendando",
            "data_hora": "2026-11-05T15:00:00",  # Data anterior + hora anterior
            "hora_confirmada": True,              # Fue confirmada en primer mensaje
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "corte feminino",
                "data_hora": "2026-11-05T15:00:00"
            },
        }

        # Segundo mensaje: solo hora (usuario cambió de opinión)
        texto_usuario = "às 16"  # Nova hora

        print(f"\n📋 AUDITORIA:")
        print(f"   Primer mensaje → data_hora=2026-11-05T15:00:00, hora_confirmada=True")
        print(f"   Segundo mensaje → '{texto_usuario}' (solo hora)")
        print(f"")
        print(f"   Esperado:")
        print(f"   - Reutilizar data: 2026-11-05 (del contexto)")
        print(f"   - Setear hora: 16:00 (del mensaje actual)")
        print(f"   - hora_confirmada = True (hora mencionada en este mensaje)")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }
            mock_salvar.return_value = None

            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_primer_mensaje,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n📤 RESULTADO:")
            data_hora = ctx_resultado.get("data_hora")
            print(f"   data_hora: {data_hora}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")

            # Auditoria 1: Data debe venir de contexto anterior
            print(f"\n📊 AUDITORIA 1: Origen de la Data")
            assert data_hora and "2026-11-05" in data_hora, \
                f"❌ Data debe ser 2026-11-05 (del contexto anterior), obtuvo {data_hora}"
            print(f"   ✅ Data = 2026-11-05 (reutilizada del contexto anterior)")

            # Auditoria 2: Hora debe venir del mensaje actual
            print(f"\n📊 AUDITORIA 2: Origen de la Hora")
            assert data_hora and "T16:" in data_hora, \
                f"❌ Hora debe ser 16:00 (del mensaje actual), obtuvo {data_hora}"
            print(f"   ✅ Hora = 16:00 (extraída del mensaje actual)")

            # Auditoria 3: Confirmación debe ser True
            print(f"\n📊 AUDITORIA 3: Confirmación")
            assert ctx_resultado.get("hora_confirmada") == True, \
                f"❌ hora_confirmada debe ser True (hora fue mencionada), obtuvo {ctx_resultado.get('hora_confirmada')}"
            print(f"   ✅ hora_confirmada = True (hora fue mencionada en este mensaje)")

            # Auditoria 4: Estado debe ser coherente
            print(f"\n📊 AUDITORIA 4: Estado del Flujo")
            assert ctx_resultado.get("estado_fluxo") == "agendando", \
                f"⚠️  estado_fluxo = {ctx_resultado.get('estado_fluxo')}"
            print(f"   ✅ estado_fluxo = agendando (coherente)")

            print(f"\n✅ T3 AUDITORIA: La hora vino del usuario actual, la data del contexto anterior")
            print(f"   REGLA DE CONTINUIDAD RESPETADA")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
