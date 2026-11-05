"""
ETAPA 2 — TESTES DE VALIDACIÓN: Patch de 2 líneas en CASO 1

Objetivo: Confirmar que el patch de `hora_confirmada=True` + `data_sem_hora=False`
funciona correctamente sin romper CASO 2 o CASO 3.

Testes:
T1: Data + hora explícitas → hora_confirmada=True, data_sem_hora=False
T2: Solo data → data_sem_hora=True, NO hora_confirmada=True
T3: Solo hora en contexto → reutiliza data anterior
T4: Múltiples horarios → NO confirma arbitrariamente
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
class TestEtapa2ValidacaoPatch:
    """
    Validación post-patch del CASO 1.
    """

    @pytest.mark.asyncio
    async def test_t1_data_hora_explicitas(self):
        """
        T1: Usuario menciona data + hora explícita
        Texto: "quero agendar corte com Bruna amanhã às 15"

        Esperado:
        - data_hora correcto
        - hora_confirmada = True ✅ (EFECTO DEL PATCH)
        - data_sem_hora = False ✅ (EFECTO DEL PATCH)
        - estado_fluxo = "agendando"
        """
        print("\n" + "="*100)
        print("T1: Data + Hora Explícitas")
        print("="*100)

        dono_id = "test_t1_data_hora"
        cliente_id = "test_cliente_t1"
        texto_usuario = "quero agendar corte com Bruna amanhã às 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")
        valor_esperado = f"{data_esperada}T15:00:00"

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Cenário:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Data esperada: {data_esperada}")
        print(f"   Hora esperada: 15:00")

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

            # Validaciones
            assert ctx_resultado.get("data_hora") == valor_esperado, \
                f"❌ data_hora incorrecto: {ctx_resultado.get('data_hora')} != {valor_esperado}"
            print(f"   ✅ data_hora correcto")

            assert ctx_resultado.get("hora_confirmada") == True, \
                f"❌ hora_confirmada debe ser True, obtuvo {ctx_resultado.get('hora_confirmada')}"
            print(f"   ✅ hora_confirmada = True")

            assert ctx_resultado.get("data_sem_hora") == False, \
                f"❌ data_sem_hora debe ser False, obtuvo {ctx_resultado.get('data_sem_hora')}"
            print(f"   ✅ data_sem_hora = False")

            assert ctx_resultado.get("estado_fluxo") == "agendando", \
                f"❌ estado_fluxo incorrecto: {ctx_resultado.get('estado_fluxo')}"
            print(f"   ✅ estado_fluxo = agendando")

            print(f"\n✅ T1 PASÓ")

    @pytest.mark.asyncio
    async def test_t2_solo_data(self):
        """
        T2: Usuario menciona solo data (sin hora)
        Texto: "quero agendar corte amanhã"

        Esperado:
        - data_sem_hora = True (usuario NO mencionó hora)
        - hora_confirmada NO debe ser True (¡NO inventar!)
        - estado_fluxo = "aguardando_horario" o similar
        """
        print("\n" + "="*100)
        print("T2: Solo Data (sin Hora)")
        print("="*100)

        dono_id = "test_t2_solo_data"
        cliente_id = "test_cliente_t2"
        texto_usuario = "quero agendar corte amanhã"  # SIN "às 15"

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Cenário:")
        print(f"   Texto: '{texto_usuario}'")
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

            # El usuario NO mencionó hora, entonces data_sem_hora debería ser True
            # y hora_confirmada NO debería ser True (no inventar hora)
            assert ctx_resultado.get("data_sem_hora") == True, \
                f"❌ data_sem_hora debe ser True (usuario no mencionó hora), obtuvo {ctx_resultado.get('data_sem_hora')}"
            print(f"   ✅ data_sem_hora = True")

            assert ctx_resultado.get("hora_confirmada") != True, \
                f"❌ NO inventar hora_confirmada=True cuando usuario no mencionó hora"
            print(f"   ✅ hora_confirmada NO es True (correcto)")

            print(f"\n✅ T2 PASÓ")

    @pytest.mark.asyncio
    async def test_t3_solo_hora_con_contexto(self):
        """
        T3: Usuario menciona solo hora en contexto con data anterior
        Escenario: Primer mensaje estableció data, segundo mensaje es solo hora

        Texto: "às 15"
        Contexto anterior: data_hora = "2026-11-05T00:00:00"

        Esperado:
        - reutilizar data anterior (2026-11-05)
        - setear hora (15:00)
        - hora_confirmada = True
        - data_sem_hora = False
        """
        print("\n" + "="*100)
        print("T3: Solo Hora con Data Anterior en Contexto")
        print("="*100)

        dono_id = "test_t3_solo_hora"
        cliente_id = "test_cliente_t3"
        texto_usuario = "às 15"  # Solo hora

        # Contexto que ya tiene data anterior
        ctx_anterior = {
            "estado_fluxo": "aguardando_horario",
            "data_hora": "2026-11-05T00:00:00",  # Data anterior sin hora específica
            "servico": "corte feminino",
            "profissional_escolhido": "Bruna",
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "corte feminino",
                "data_hora": "2026-11-05T00:00:00"
            },
        }

        print(f"\n📋 Cenário:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Data anterior en contexto: 2026-11-05T00:00:00")
        print(f"   Esperado: reutilizar 2026-11-05 con hora 15:00")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }
            mock_salvar.return_value = None

            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_anterior,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n📤 Resultado:")
            print(f"   data_hora: {ctx_resultado.get('data_hora')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")
            print(f"   data_sem_hora: {ctx_resultado.get('data_sem_hora')}")

            # Debe reutilizar la data anterior (2026-11-05) con la hora nueva (15:00)
            data_hora = ctx_resultado.get("data_hora")
            assert data_hora and "2026-11-05T15:" in data_hora, \
                f"❌ Debe reutilizar data anterior con hora nueva, obtuvo {data_hora}"
            print(f"   ✅ Reutilizó data anterior con hora nueva")

            assert ctx_resultado.get("hora_confirmada") == True, \
                f"❌ hora_confirmada debe ser True, obtuvo {ctx_resultado.get('hora_confirmada')}"
            print(f"   ✅ hora_confirmada = True")

            assert ctx_resultado.get("data_sem_hora") == False, \
                f"❌ data_sem_hora debe ser False, obtuvo {ctx_resultado.get('data_sem_hora')}"
            print(f"   ✅ data_sem_hora = False")

            print(f"\n✅ T3 PASÓ")

    @pytest.mark.asyncio
    async def test_t4_multiplos_horarios(self):
        """
        T4: Usuario menciona múltiples horarios (CASO 2)
        Texto: "amanhã às 15 ou 16"

        Esperado:
        - NO confirmar arbitrariamente un horario
        - estado_fluxo = "aguardando_escolha_horario"
        - horarios_sugeridos = ["15:00", "16:00"]
        - NO setear hora_confirmada=True (esperar que usuario elija)
        """
        print("\n" + "="*100)
        print("T4: Múltiples Horarios (CASO 2)")
        print("="*100)

        dono_id = "test_t4_multiplos"
        cliente_id = "test_cliente_t4"
        texto_usuario = "amanhã às 15 ou 16"  # Múltiples horarios

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Cenário:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Múltiples horarios mencionados")

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
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")
            print(f"   horarios_sugeridos: {ctx_resultado.get('horarios_sugeridos')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")

            # CASO 2: Múltiples horarios → debe pedir que el usuario elija
            assert ctx_resultado.get("estado_fluxo") == "aguardando_escolha_horario", \
                f"❌ estado_fluxo debe ser 'aguardando_escolha_horario', obtuvo {ctx_resultado.get('estado_fluxo')}"
            print(f"   ✅ estado_fluxo = aguardando_escolha_horario")

            horarios = ctx_resultado.get("horarios_sugeridos") or []
            assert len(horarios) == 2, \
                f"❌ Debe haber 2 horarios sugeridos, obtuvo {len(horarios)}: {horarios}"
            print(f"   ✅ horarios_sugeridos = {horarios}")

            # NO debe confirmara arbitrariamente cuando hay múltiples opciones
            assert ctx_resultado.get("hora_confirmada") != True, \
                f"❌ NO confirmar hora arbitrariamente cuando hay múltiples opciones"
            print(f"   ✅ NO confirma hora arbitrariamente")

            print(f"\n✅ T4 PASÓ")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
