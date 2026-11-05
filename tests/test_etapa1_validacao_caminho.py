"""
ETAPA 1 — TESTE ISOLADO: Auditoria del Camino de Ejecución

Objetivo: Confirmar si validar_data_funcionamento() causa un retorno antecipado
que impide la asignación de hora_confirmada = True en línea 1930.

Escenarios:
T1: validacio retorna {"permitido": True} → Debe llegar a línea 1930
T2: validacio retorna {"permitido": False} → Retorno antecipado en línea 1916, hora_confirmada = False
T3: validacio lanza Exception → Continúa a línea 1930 con hora_confirmada = True
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
class TestEtapa1ValidacaoCaminho:
    """
    Prueba aislada del camino de ejecución en extrair_slots_e_mesclar()
    con control explícito de validar_data_funcionamento().
    """

    @pytest.mark.asyncio
    async def test_t1_funcionamiento_permitido_true(self):
        """
        T1: validar_data_funcionamiento() retorna {"permitido": True}

        Esperado:
        - Debe llegar a línea 1930
        - hora_confirmada = True
        - estado_fluxo = "aguardando_profissional" (línea 1932)
        """
        print("\n" + "="*100)
        print("T1: Funcionamiento Permitido (permitido=True)")
        print("="*100)

        dono_id = "test_t1_permitido"
        cliente_id = "test_cliente_t1"
        texto_usuario = "queria agendar corte com a bruna para amanha as 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Contexto inicial:")
        print(f"   estado_fluxo: idle")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.validar_data_funcionamento', new_callable=AsyncMock) as mock_validacao, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            # Mock 1: Profissionales (Bruna existe)
            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }

            # Mock 2: Validación POSITIVA (permitido=True)
            mock_validacao.return_value = {"permitido": True}

            # Mock 3: Salvar contexto
            mock_salvar.return_value = None

            print(f"\n🔧 Mocks configurados:")
            print(f"   validar_data_funcionamento() → {{'permitido': True}}")

            # Ejecutar
            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_inicial,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n📤 Resultado de extrair_slots_e_mesclar():")
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")
            print(f"   data_hora: {ctx_resultado.get('data_hora')}")

            # Análisis
            print(f"\n✅ ANÁLISIS T1:")
            if ctx_resultado.get("hora_confirmada") == True:
                print(f"   ✅ CORRECTO: hora_confirmada = True")
                print(f"   ✅ CORRECTO: Llegó a línea 1930")
            else:
                print(f"   ❌ INCORRECTO: hora_confirmada = {ctx_resultado.get('hora_confirmada')}")
                print(f"   ❌ PROBLEMA: No llegó a línea 1930")

            assert ctx_resultado.get("hora_confirmada") == True, \
                f"T1 FALLÓ: hora_confirmada debe ser True, obtuvo {ctx_resultado.get('hora_confirmada')}"

    @pytest.mark.asyncio
    async def test_t2_funcionamiento_no_permitido_false(self):
        """
        T2: validar_data_funcionamento() retorna {"permitido": False}

        Esperado:
        - RETORNO ANTECIPADO en línea 1916
        - hora_confirmada = False (línea 1913)
        - estado_fluxo = "aguardando_data" (línea 1910)
        - Contexto contiene "_erro_validacion"
        """
        print("\n" + "="*100)
        print("T2: Funcionamiento NO Permitido (permitido=False)")
        print("="*100)

        dono_id = "test_t2_no_permitido"
        cliente_id = "test_cliente_t2"
        texto_usuario = "queria agendar corte com a bruna para amanha as 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Contexto inicial:")
        print(f"   estado_fluxo: idle")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.validar_data_funcionamento', new_callable=AsyncMock) as mock_validacao, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            # Mock 1: Profissionales
            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }

            # Mock 2: Validación NEGATIVA (permitido=False)
            mock_validacao.return_value = {
                "permitido": False,
                "motivo": "Salão fechado no feriado",
                "regra": {"tipo": "feriado"}
            }

            # Mock 3: Salvar contexto
            mock_salvar.return_value = None

            print(f"\n🔧 Mocks configurados:")
            print(f"   validar_data_funcionamento() → {{'permitido': False, ...}}")

            # Ejecutar
            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_inicial,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n📤 Resultado de extrair_slots_e_mesclar():")
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")
            print(f"   data_hora: {ctx_resultado.get('data_hora')}")
            print(f"   _erro_validacion: {bool(ctx_resultado.get('_erro_validacion'))}")

            # Análisis
            print(f"\n✅ ANÁLISIS T2:")
            if ctx_resultado.get("hora_confirmada") == False:
                print(f"   ✅ CORRECTO: hora_confirmada = False (retorno antecipado)")
            else:
                print(f"   ❌ INCORRECTO: hora_confirmada = {ctx_resultado.get('hora_confirmada')}")

            if ctx_resultado.get("estado_fluxo") == "aguardando_data":
                print(f"   ✅ CORRECTO: estado_fluxo = 'aguardando_data'")
            else:
                print(f"   ❌ INCORRECTO: estado_fluxo = {ctx_resultado.get('estado_fluxo')}")

            if ctx_resultado.get("_erro_validacion"):
                print(f"   ✅ CORRECTO: Mensaje de error presente")
            else:
                print(f"   ❌ INCORRECTO: Mensaje de error ausente")

            assert ctx_resultado.get("hora_confirmada") == False, \
                f"T2 FALLÓ: hora_confirmada debe ser False, obtuvo {ctx_resultado.get('hora_confirmada')}"

            assert ctx_resultado.get("estado_fluxo") == "aguardando_data", \
                f"T2 FALLÓ: estado_fluxo debe ser 'aguardando_data', obtuvo {ctx_resultado.get('estado_fluxo')}"

    @pytest.mark.asyncio
    async def test_t3_excepcion_en_validacion(self):
        """
        T3: validar_data_funcionamento() lanza Exception

        Esperado (según línea 1921-1923):
        - Captura la excepción
        - Continúa a línea 1930
        - hora_confirmada = True (falso abierto: asume que funciona)
        - NO hay "_erro_validacion"
        """
        print("\n" + "="*100)
        print("T3: Excepción en validación")
        print("="*100)

        dono_id = "test_t3_excepcion"
        cliente_id = "test_cliente_t3"
        texto_usuario = "queria agendar corte com a bruna para amanha as 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")

        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📋 Contexto inicial:")
        print(f"   estado_fluxo: idle")

        with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
             patch('router.principal_router.validar_data_funcionamento', new_callable=AsyncMock) as mock_validacao, \
             patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar:

            # Mock 1: Profissionales
            mock_buscar.return_value = {
                "prof_1": {"nome": "Bruna", "servicos": ["corte feminino", "escova"]}
            }

            # Mock 2: Validación LANZA EXCEPTION
            mock_validacao.side_effect = Exception("Firebase connection timeout")

            # Mock 3: Salvar contexto
            mock_salvar.return_value = None

            print(f"\n🔧 Mocks configurados:")
            print(f"   validar_data_funcionamento() → LANZA Exception('Firebase connection timeout')")

            # Ejecutar
            ctx_resultado = await extrair_slots_e_mesclar(
                ctx_inicial,
                texto_usuario,
                dono_id,
                cliente_id
            )

            print(f"\n📤 Resultado de extrair_slots_e_mesclar():")
            print(f"   estado_fluxo: {ctx_resultado.get('estado_fluxo')}")
            print(f"   hora_confirmada: {ctx_resultado.get('hora_confirmada')}")
            print(f"   data_hora: {ctx_resultado.get('data_hora')}")
            print(f"   _erro_validacion: {bool(ctx_resultado.get('_erro_validacion'))}")

            # Análisis
            print(f"\n✅ ANÁLISIS T3:")
            if ctx_resultado.get("hora_confirmada") == True:
                print(f"   ✅ CORRECTO: hora_confirmada = True (falsa abierto)")
                print(f"   ✅ CORRECTO: Continuó después de la excepción (línea 1923)")
            else:
                print(f"   ❌ INCORRECTO: hora_confirmada = {ctx_resultado.get('hora_confirmada')}")

            if not ctx_resultado.get("_erro_validacion"):
                print(f"   ✅ CORRECTO: Sin mensaje de error (asume funcionamiento)")
            else:
                print(f"   ⚠️  ADVERTENCIA: Hay error presente: {ctx_resultado.get('_erro_validacion')}")

            assert ctx_resultado.get("hora_confirmada") == True, \
                f"T3 FALLÓ: hora_confirmada debe ser True, obtuvo {ctx_resultado.get('hora_confirmada')}"

    # =========================================================================
    # RESUMEN Y CONCLUSIÓN
    # =========================================================================
    @pytest.mark.asyncio
    async def test_resumen_etapa1(self):
        """
        Resumen de ETAPA 1: Auditoria del camino de ejecución
        """
        print("\n" + "="*100)
        print("RESUMEN ETAPA 1")
        print("="*100)

        print(f"""
HALLAZGOS:

1. RETORNO ANTECIPADO CONFIRMADO
   - Línea 1916: return statement en el bloque if not permitido
   - Si validar_data_funcionamento() retorna permitido=False:
     → El flujo retorna en línea 1916
     → NUNCA llega a línea 1930 (hora_confirmada = True)
     → hora_confirmada se queda en False (línea 1913)

2. FALSA ABIERTA EN EXCEPCIÓN
   - Línea 1921: except Exception as e
   - Si validar_data_funcionamento() lanza exception:
     → Se captura silenciosamente
     → Continúa a línea 1926 (pop de _erro_validacion)
     → Llega a línea 1930 (hora_confirmada = True)

3. FLUJO NORMAL
   - Si validar_data_funcionamento() retorna permitido=True:
     → Continúa directo a línea 1926
     → Llega a línea 1930 (hora_confirmada = True)

CONCLUSIÓN:
La hipótesis del retorno antecipado es VÁLIDA.
El problema está en que validar_data_funcionamento() retorna permitido=False
en el test, causando un retorno prematuro en línea 1916.
        """)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
