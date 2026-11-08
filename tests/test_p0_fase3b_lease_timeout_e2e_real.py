#!/usr/bin/env python3
"""
P0 FASE 3.B - Testes E2E com Firestore REAL para OperacaoEmAndamento.
T1-T10: Validacao de lease/timeout com persistencia real em Firestore.
Reutiliza padrao de test_p0_19_e2e_firestore_real.py.
Sem AsyncMock. Firestore real.
"""

import asyncio
import pytest
import uuid
import sys
import os
from datetime import datetime, timedelta

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

from firebase_admin import firestore
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)
from utils.operacao_service import (
    gerar_proprietario_id,
    criar_operacao_em_andamento,
    adquirir_lease_operacao,
    atualizar_operacao_status,
    recuperar_operacao_em_andamento,
)

TEST_TENANT_ID = f"test_p0_fase3b_{uuid.uuid4().hex[:8]}"
TEST_ACTOR_ID = f"test_actor_{uuid.uuid4().hex[:8]}"


async def test_t1_aquisicao_lease_expirado():
    """T1: Propriedade antiga expirada pode ser transferida."""
    print("\n=== T1 AQUISICAO LEASE EXPIRADO ===")

    operacao_id = f"test_t1_{uuid.uuid4().hex[:8]}"
    prop_a = gerar_proprietario_id()
    prop_b = gerar_proprietario_id()

    try:
        await criar_operacao_em_andamento(
            tenant_id=TEST_TENANT_ID,
            operacao_id=operacao_id,
            actor_id=TEST_ACTOR_ID,
            tipo="agendamento",
            dados_confirmados={"draft": "test"},
            proprietario_id=prop_a,
            lease_ttl_minutos=0
        )

        doc_antes = await buscar_dado_em_path(
            f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
        )
        print(f"Antes: proprietario={doc_antes.get('proprietario_id')[:16]}...")

        resultado = await adquirir_lease_operacao(
            tenant_id=TEST_TENANT_ID,
            operacao_id=operacao_id,
            proprietario_id=prop_b
        )

        doc_depois = await buscar_dado_em_path(
            f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
        )
        print(f"Depois: proprietario={doc_depois.get('proprietario_id')[:16]}...")

        if doc_depois.get("proprietario_id") == prop_b:
            print("PASS T1: propriedade transferida com sucesso")
            return True
        else:
            print(f"FAIL T1: proprietario nao mudou")
            return False

    except Exception as e:
        print(f"FAIL T1: {type(e).__name__}")
        return False
    finally:
        try:
            await deletar_dado_em_path(
                f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
            )
        except:
            pass


async def test_t3_concorrencia():
    """T3: Concorrencia - 10 rodadas."""
    print("\n=== T3 CONCORRENCIA (10 RODADAS) ===")

    passed = 0

    for rodada in range(10):
        operacao_id = f"test_t3_rodada_{rodada}_{uuid.uuid4().hex[:8]}"
        prop_a = gerar_proprietario_id()
        prop_b = gerar_proprietario_id()

        try:
            await criar_operacao_em_andamento(
                tenant_id=TEST_TENANT_ID,
                operacao_id=operacao_id,
                actor_id=TEST_ACTOR_ID,
                tipo="agendamento",
                dados_confirmados={"draft": "test"},
                proprietario_id="inicial",
                lease_ttl_minutos=0
            )

            resultados = await asyncio.gather(
                adquirir_lease_operacao(TEST_TENANT_ID, operacao_id, prop_a),
                adquirir_lease_operacao(TEST_TENANT_ID, operacao_id, prop_b),
                return_exceptions=True
            )

            doc_final = await buscar_dado_em_path(
                f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
            )
            proprietario_final = doc_final.get("proprietario_id")

            if proprietario_final in (prop_a, prop_b):
                print(f"  Rodada {rodada+1}/10: PASS")
                passed += 1
            else:
                print(f"  Rodada {rodada+1}/10: FAIL (proprietario inesperado)")

        except Exception as e:
            print(f"  Rodada {rodada+1}/10: FAIL ({type(e).__name__})")
        finally:
            try:
                await deletar_dado_em_path(
                    f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
                )
            except:
                pass

    if passed == 10:
        print(f"PASS T3: {passed}/10 rodadas")
        return True
    else:
        print(f"FAIL T3: apenas {passed}/10 rodadas")
        return False


async def test_t5_bloqueio_proprietario_antigo():
    """T5: Proprietario antigo nao consegue atualizar."""
    print("\n=== T5 BLOQUEIO PROPRIETARIO ANTIGO ===")

    operacao_id = f"test_t5_{uuid.uuid4().hex[:8]}"
    prop_a = gerar_proprietario_id()
    prop_b = gerar_proprietario_id()

    try:
        await criar_operacao_em_andamento(
            tenant_id=TEST_TENANT_ID,
            operacao_id=operacao_id,
            actor_id=TEST_ACTOR_ID,
            tipo="agendamento",
            dados_confirmados={"draft": "test"},
            proprietario_id=prop_a,
            lease_ttl_minutos=5
        )

        await adquirir_lease_operacao(
            TEST_TENANT_ID, operacao_id, prop_b, lease_ttl_minutos=1
        )

        try:
            await atualizar_operacao_status(
                tenant_id=TEST_TENANT_ID,
                operacao_id=operacao_id,
                novo_status="concluida",
                proprietario_id=prop_a
            )
            print("FAIL T5: prop_a conseguiu atualizar (nao deveria)")
            return False
        except:
            print("PASS T5: prop_a bloqueado corretamente")
            return True

    except Exception as e:
        print(f"FAIL T5: {type(e).__name__}")
        return False
    finally:
        try:
            await deletar_dado_em_path(
                f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
            )
        except:
            pass


async def test_t9_recuperacao():
    """T9: Recuperacao apos reinicializacao."""
    print("\n=== T9 RECUPERACAO POS REINICIALIZACAO ===")

    operacao_id = f"test_t9_{uuid.uuid4().hex[:8]}"
    prop_a = gerar_proprietario_id()
    dados_confirmados = {"draft": "test_data", "servico": "corte"}

    try:
        await criar_operacao_em_andamento(
            tenant_id=TEST_TENANT_ID,
            operacao_id=operacao_id,
            actor_id=TEST_ACTOR_ID,
            tipo="agendamento",
            dados_confirmados=dados_confirmados,
            proprietario_id=prop_a,
            lease_ttl_minutos=5
        )

        doc_recuperado = await recuperar_operacao_em_andamento(
            TEST_TENANT_ID, operacao_id
        )

        if not doc_recuperado:
            print("FAIL T9: documento nao recuperado")
            return False

        if (doc_recuperado.get("operacao_id") == operacao_id and
            doc_recuperado.get("proprietario_id") == prop_a and
            doc_recuperado.get("status") == "em_andamento"):
            print("PASS T9: todos campos recuperados")
            return True
        else:
            print("FAIL T9: campos incorretos")
            return False

    except Exception as e:
        print(f"FAIL T9: {type(e).__name__}")
        return False
    finally:
        try:
            await deletar_dado_em_path(
                f"Clientes/{TEST_TENANT_ID}/OperacoesEmAndamento/{operacao_id}"
            )
        except:
            pass


async def main():
    """Executar T1, T3, T5, T9 (criticos)."""
    print("\n" + "="*60)
    print("P0 FASE 3.B - TESTES E2E COM FIRESTORE REAL")
    print("="*60)
    print(f"Tenant: {TEST_TENANT_ID}")
    print(f"Actor: {TEST_ACTOR_ID}")

    resultados = {
        "T1": await test_t1_aquisicao_lease_expirado(),
        "T3": await test_t3_concorrencia(),
        "T5": await test_t5_bloqueio_proprietario_antigo(),
        "T9": await test_t9_recuperacao(),
    }

    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    for teste, resultado in resultados.items():
        status = "PASS" if resultado else "FAIL"
        print(f"{teste}: {status}")

    if all(resultados.values()):
        print("\nCLASSIFICACAO: APROVADO PARA FASE 4")
    else:
        print("\nCLASSIFICACAO: BLOQUEADOR CRITICO")

    return resultados


if __name__ == "__main__":
    resultados = asyncio.run(main())
