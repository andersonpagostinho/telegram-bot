"""
TESTE ISOLADO: Rastreamento de data_hora

Objetivo: Capturar os 9 checkpoints de fluxo de data_hora
Cenário: "queria agendar corte com a bruna para amanha as 15"

Requisitos:
- READ-ONLY (sem modificações)
- Sem Firebase
- Sem GPT
- Sem efeitos colaterais
- Dependências mockadas
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Importar funções críticas
try:
    from router.principal_router import (
        extrair_slots_e_mesclar,
        tem_hora_real,
    )
    from utils.interpretador_datas import interpretar_data_e_hora
    IMPORTS_OK = True
except Exception as e:
    print(f"Import error: {e}")
    IMPORTS_OK = False


@pytest.mark.skipif(not IMPORTS_OK, reason="Failed to import router functions")
class TestCheckpointRastreamentoDataHora:
    """
    Captura valores reais em cada transição de data_hora.
    """

    @pytest.mark.asyncio
    async def test_rastreamento_completo_9_checkpoints(self):
        """
        Cenário: "queria agendar corte com a bruna para amanha as 15"
        """
        print("\n" + "="*100)
        print("TESTE ISOLADO: RASTREAMENTO DE data_hora")
        print("="*100)

        # =====================================================
        # SETUP ISOLADO
        # =====================================================
        dono_id = "test_isolado_rastreamento"
        cliente_id = "test_cliente_iso"
        texto_usuario = "queria agendar corte com a bruna para amanha as 15"

        amanha = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        data_esperada = amanha.strftime("%Y-%m-%d")
        hora_esperada = "15:00"
        valor_esperado = f"{data_esperada}T{hora_esperada}:00"

        print(f"\n📋 CENÁRIO:")
        print(f"   Texto: '{texto_usuario}'")
        print(f"   Data esperada: {data_esperada}")
        print(f"   Hora esperada: {hora_esperada}")
        print(f"   Valor esperado: {valor_esperado}")

        # Contexto inicial (estado vazio, novo agendamento)
        ctx_inicial = {
            "estado_fluxo": "idle",
            "intencao_conversacional": None,
            "draft_agendamento": {},
        }

        print(f"\n📥 Contexto inicial:")
        print(f"   {json.dumps(ctx_inicial, indent=2)}")

        # =====================================================
        # CHECKPOINT 1: Retorno de extrair_slots_e_mesclar()
        # =====================================================
        print(f"\n{'='*100}")
        print("CHECKPOINT 1: Retorno de extrair_slots_e_mesclar()")
        print("="*100)

        try:
            # Mock de dependências externas
            with patch('router.principal_router.buscar_subcolecao', new_callable=AsyncMock) as mock_buscar, \
                 patch('router.principal_router.validar_horario_funcionamento', new_callable=AsyncMock) as mock_validar, \
                 patch('router.principal_router.salvar_contexto_temporario_v2', new_callable=AsyncMock) as mock_salvar, \
                 patch('services.firebase_service_async.buscar_dado_em_path', new_callable=AsyncMock) as mock_buscar_path:

                # Mock: Profissionais (Bruna existe)
                mock_buscar.return_value = {
                    "prof_1": {
                        "nome": "Bruna",
                        "servicos": ["corte feminino", "escova", "coloracao"]
                    }
                }

                # Mock: Validação de expediente (aceita qualquer horário)
                mock_validar.return_value = {"permitido": True}

                # Mock: Salvar contexto (não faz nada)
                mock_salvar.return_value = None

                # Mock: Buscar dados (não encontra conflito)
                mock_buscar_path.return_value = None

                # EXECUTAR extrair_slots_e_mesclar()
                ctx_retornado = await extrair_slots_e_mesclar(
                    ctx_inicial,
                    texto_usuario,
                    dono_id,
                    cliente_id
                )

                print(f"\n✅ extrair_slots_e_mesclar() retornou com sucesso")

                # ========================================
                # CHECKPOINT 2: ctx["data_hora"]
                # ========================================
                data_hora_em_ctx = ctx_retornado.get("data_hora")
                print(f"\nCHECKPOINT 2: ctx['data_hora'] após extrair_slots_e_mesclar()")
                print(f"   Valor: {data_hora_em_ctx}")
                print(f"   Tipo: {type(data_hora_em_ctx)}")
                if data_hora_em_ctx:
                    print(f"   ✅ NÃO VAZIO")
                else:
                    print(f"   ❌ VAZIO OU NONE")

                # ========================================
                # CHECKPOINT 3: draft_agendamento["data_hora"]
                # ========================================
                draft = ctx_retornado.get("draft_agendamento") or {}
                data_hora_em_draft = draft.get("data_hora")
                print(f"\nCHECKPOINT 3: draft_agendamento['data_hora']")
                print(f"   Valor: {data_hora_em_draft}")
                print(f"   Tipo: {type(data_hora_em_draft)}")
                if data_hora_em_draft:
                    print(f"   ✅ NÃO VAZIO")
                else:
                    print(f"   ❌ VAZIO OU NONE")

                # ========================================
                # CHECKPOINT 4: slots_extraidos["data_hora"] (SIMULADO)
                # ========================================
                # Simular a lógica de centralização (linhas 13149-13162)
                slots_extraidos = {
                    "data_hora": ctx_retornado.get("data_hora") or draft.get("data_hora"),
                    "servico": ctx_retornado.get("servico") or draft.get("servico"),
                    "profissional": ctx_retornado.get("profissional_escolhido") or draft.get("profissional"),
                }

                # Fallback duplicado
                if not slots_extraidos["data_hora"]:
                    slots_extraidos["data_hora"] = draft.get("data_hora")

                data_hora_em_slots = slots_extraidos["data_hora"]
                print(f"\nCHECKPOINT 4: slots_extraidos['data_hora'] (centralização)")
                print(f"   Valor: {data_hora_em_slots}")
                print(f"   Tipo: {type(data_hora_em_slots)}")
                if data_hora_em_slots:
                    print(f"   ✅ NÃO VAZIO")
                else:
                    print(f"   ❌ VAZIO OU NONE")

                # ========================================
                # CHECKPOINT 5: Argumento para tem_hora_real()
                # ========================================
                argumento_para_funcao = slots_extraidos["data_hora"]
                print(f"\nCHECKPOINT 5: Argumento recebido por tem_hora_real()")
                print(f"   Valor: {argumento_para_funcao}")
                print(f"   Tipo: {type(argumento_para_funcao)}")

                # ========================================
                # CHECKPOINT 6: Retorno de tem_hora_real()
                # ========================================
                resultado_tem_hora = tem_hora_real(slots_extraidos["data_hora"])
                print(f"\nCHECKPOINT 6: Retorno de tem_hora_real()")
                print(f"   Valor: {resultado_tem_hora}")
                print(f"   Tipo: {type(resultado_tem_hora)}")
                if resultado_tem_hora:
                    print(f"   ✅ TRUE (hora é real)")
                else:
                    print(f"   ❌ FALSE (hora NÃO é real)")

                # ========================================
                # CHECKPOINT 7: campos_faltantes
                # ========================================
                campos_faltantes = []

                if not slots_extraidos["servico"]:
                    campos_faltantes.append("servico")

                if not slots_extraidos["profissional"]:
                    campos_faltantes.append("profissional")

                if not tem_hora_real(slots_extraidos["data_hora"]):
                    campos_faltantes.append("data_hora")

                print(f"\nCHECKPOINT 7: campos_faltantes")
                print(f"   Valor: {campos_faltantes}")
                if "data_hora" in campos_faltantes:
                    print(f"   ❌ 'data_hora' MARCADO COMO FALTANTE")
                else:
                    print(f"   ✅ 'data_hora' NÃO está faltante")

                # ========================================
                # CHECKPOINT 8: proximo_passo (simulado)
                # ========================================
                proximo_passo = None
                if campos_faltantes:
                    if campos_faltantes == ["servico"]:
                        proximo_passo = "perguntar_servico"
                    elif campos_faltantes == ["profissional"]:
                        proximo_passo = "perguntar_profissional"
                    elif campos_faltantes == ["data_hora"]:
                        proximo_passo = "perguntar_data_hora"
                    else:
                        proximo_passo = "coletar_dado_faltante"
                else:
                    proximo_passo = "confirmar_ou_executar"

                print(f"\nCHECKPOINT 8: proximo_passo")
                print(f"   Valor: {proximo_passo}")
                if proximo_passo == "perguntar_data_hora":
                    print(f"   ❌ REDIRECIONA PARA PERGUNTAR HORÁRIO")
                else:
                    print(f"   ✅ Não pede horário")

                # ========================================
                # CHECKPOINT 9: proximo_passo_real (simplificado)
                # ========================================
                # Simplificar: assumir que resolver_proximo_passo_real não muda o valor
                proximo_passo_real = proximo_passo

                print(f"\nCHECKPOINT 9: proximo_passo_real")
                print(f"   Valor: {proximo_passo_real}")
                if proximo_passo_real == "perguntar_somente_horario" or proximo_passo_real == "perguntar_data_hora":
                    print(f"   ❌ ENVIARÁ: 'Qual horário você prefere?'")
                else:
                    print(f"   ✅ Não enviará pergunta de horário")

                # =====================================================
                # ANÁLISE RESUMIDA
                # =====================================================
                print(f"\n{'='*100}")
                print("ANÁLISE RESUMIDA")
                print("="*100)

                print(f"\n📊 TABELA DE VALORES:")
                print(f"""
                | Checkpoint | Esperado | Observado | Status |
                |---|---|---|---|
                | 1. Retorno de extrair_slots_e_mesclar() | dict com data_hora | ✅ | OK |
                | 2. ctx["data_hora"] | {valor_esperado} | {data_hora_em_ctx} | {'✅' if data_hora_em_ctx == valor_esperado else '❌'} |
                | 3. draft["data_hora"] | {valor_esperado} | {data_hora_em_draft} | {'✅' if data_hora_em_draft == valor_esperado else '❌'} |
                | 4. slots_extraidos["data_hora"] | {valor_esperado} | {data_hora_em_slots} | {'✅' if data_hora_em_slots == valor_esperado else '❌'} |
                | 5. Argumento para tem_hora_real() | {valor_esperado} | {argumento_para_funcao} | {'✅' if argumento_para_funcao == valor_esperado else '❌'} |
                | 6. Retorno tem_hora_real() | True | {resultado_tem_hora} | {'✅' if resultado_tem_hora else '❌'} |
                | 7. campos_faltantes | [] | {campos_faltantes} | {'✅' if "data_hora" not in campos_faltantes else '❌'} |
                | 8. proximo_passo | confirmar_ou_executar | {proximo_passo} | {'✅' if proximo_passo != "perguntar_data_hora" else '❌'} |
                | 9. proximo_passo_real | (não pede hora) | {proximo_passo_real} | {'✅' if proximo_passo_real != "perguntar_data_hora" else '❌'} |
                """)

                # =====================================================
                # CONCLUSÃO
                # =====================================================
                print(f"\n{'='*100}")
                print("CONCLUSÃO")
                print("="*100)

                if data_hora_em_ctx == valor_esperado and resultado_tem_hora and "data_hora" not in campos_faltantes:
                    print(f"\n✅ FLUXO DE data_hora CORRETO ATÉ CHECKPOINT 7")
                    print(f"   Se o usuário recebe 'Qual horário?', o problema está ALÉM da linha 13172")
                    print(f"   Investigar: resolver_proximo_passo_real() ou montar_resposta_fallback()")
                else:
                    print(f"\n❌ DIVERGÊNCIA ENCONTRADA")
                    if not data_hora_em_ctx:
                        print(f"   → extrair_slots_e_mesclar() NÃO preencheu ctx['data_hora']")
                    elif not resultado_tem_hora:
                        print(f"   → tem_hora_real() retornou False (valor inválido)")
                    elif "data_hora" in campos_faltantes:
                        print(f"   → data_hora marcado como faltante")

                print(f"\n{'='*100}\n")

        except Exception as e:
            print(f"\n❌ ERRO NA EXECUÇÃO:")
            print(f"   {type(e).__name__}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise


if __name__ == "__main__":
    print("Teste de Rastreamento: data_hora")
    print("Execute com: pytest tests/test_checkpoint_rastreamento_data_hora.py -v -s")
