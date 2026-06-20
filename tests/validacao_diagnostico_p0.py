#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACAO OBJETIVA - 3 Diagnosticos P0

Executa testes minimos contra Firestore REAL para validar:
1. normalizar_hora() - entrada/saida
2. obter_id_dono() - resolve tenant corretamente?
3. DELETE_FIELD - limpa dados corretamente?

NAO modifica producao. Apenas le e valida.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
    obter_id_dono,
)
from services.agenda_lock_service import normalizar_hora

# ============================================================================
# TESTE 1: normalizar_hora()
# ============================================================================

async def teste_1_normalizar_hora():
    """Validar que normalizar_hora retorna strings validas"""
    print("\n" + "="*80)
    print("TESTE 1: normalizar_hora()")
    print("="*80)

    testes = [
        ("10:00", "string simples"),
        ("10:00:00", "string com segundos"),
        ("09:30", "horario diferente"),
        ("", "string vazia"),
        (None, "None"),
    ]

    resultado_teste_1 = {
        "teste": "normalizar_hora()",
        "status": "EXECUTADO",
        "casos": []
    }

    for entrada, descricao in testes:
        try:
            saida = normalizar_hora(entrada)
            tipo_saida = type(saida).__name__

            # Validacao
            valido = (
                isinstance(saida, str) and
                len(saida) > 0 and
                saida not in [None, False, ""]
            )

            caso = {
                "entrada": entrada,
                "descricao": descricao,
                "saida": saida,
                "tipo_saida": tipo_saida,
                "valido": valido,
                "status": "[OK]" if valido else "[FALHA]"
            }

            resultado_teste_1["casos"].append(caso)

            print(f"\n[TESTE 1.{len(resultado_teste_1['casos'])}] {descricao}")
            print(f"  Entrada: {entrada} (tipo: {type(entrada).__name__})")
            print(f"  Saida: {saida} (tipo: {tipo_saida})")
            print(f"  Valido: {valido}")
            print(f"  Status: {caso['status']}")

        except Exception as e:
            caso = {
                "entrada": entrada,
                "descricao": descricao,
                "erro": str(e),
                "status": "[EXCECAO]"
            }
            resultado_teste_1["casos"].append(caso)
            print(f"\n[TESTE 1.{len(resultado_teste_1['casos'])}] {descricao} - ERRO")
            print(f"  Entrada: {entrada}")
            print(f"  Erro: {e}")

    # Resumo
    validos = sum(1 for c in resultado_teste_1["casos"] if c.get("valido") is True)
    resultado_teste_1["resumo"] = {
        "total": len(resultado_teste_1["casos"]),
        "validos": validos,
        "falhas": len(resultado_teste_1["casos"]) - validos,
        "problematico": validos < 2  # Se < 2 horarios validos, problema
    }

    print(f"\n[RESUMO TESTE 1]")
    print(f"   Validos: {validos}/{len(resultado_teste_1['casos'])}")
    print(f"   Problematico: {resultado_teste_1['resumo']['problematico']}")

    return resultado_teste_1


# ============================================================================
# TESTE 2: obter_id_dono() - tenant resolution
# ============================================================================

async def teste_2_obter_id_dono():
    """Validar que obter_id_dono resolve tenant corretamente"""
    print("\n" + "="*80)
    print("TESTE 2: obter_id_dono() - tenant resolution")
    print("="*80)

    actor_id = "bateria_p0_user_teste_001"
    esperado_tenant = "bateria_p0_dono_teste"

    resultado_teste_2 = {
        "teste": "obter_id_dono()",
        "actor_id": actor_id,
        "esperado_tenant": esperado_tenant,
        "pasos": []
    }

    # Passo 1: Chamar obter_id_dono
    print(f"\n[PASSO 1] Chamar obter_id_dono('{actor_id}')...")
    try:
        tenant_retornado = await obter_id_dono(actor_id)

        passo_1 = {
            "acao": "obter_id_dono()",
            "entrada": actor_id,
            "saida": tenant_retornado,
            "correto": tenant_retornado == esperado_tenant,
            "status": "[OK]" if tenant_retornado == esperado_tenant else "[FALHA]"
        }

        resultado_teste_2["pasos"].append(passo_1)

        print(f"  Entrada: {actor_id}")
        print(f"  Saida: {tenant_retornado}")
        print(f"  Esperado: {esperado_tenant}")
        print(f"  Correto: {passo_1['correto']}")
        print(f"  Status: {passo_1['status']}")

    except Exception as e:
        passo_1 = {
            "acao": "obter_id_dono()",
            "entrada": actor_id,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_2["pasos"].append(passo_1)
        print(f"  ERRO: {e}")
        return resultado_teste_2

    # Passo 2: Verificar cliente em Firestore
    print(f"\n[PASSO 2] Verificar se cliente existe em Firestore...")
    cliente_path = f"Clientes/{actor_id}"
    try:
        cliente = await buscar_dado_em_path(cliente_path)

        passo_2 = {
            "acao": "buscar_dado_em_path()",
            "path": cliente_path,
            "existe": cliente is not None and len(cliente) > 0,
            "id_negocio": cliente.get("id_negocio") if cliente else None,
            "status": "[EXISTE]" if cliente else "[NAO_EXISTE]"
        }

        resultado_teste_2["pasos"].append(passo_2)

        print(f"  Path: {cliente_path}")
        print(f"  Existe: {passo_2['existe']}")
        if cliente:
            print(f"  Dados: {json.dumps({k: v for k, v in cliente.items() if not k.startswith('_')}, indent=2, default=str)}")
            print(f"  id_negocio: {passo_2['id_negocio']}")
        print(f"  Status: {passo_2['status']}")

    except Exception as e:
        passo_2 = {
            "acao": "buscar_dado_em_path()",
            "path": cliente_path,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_2["pasos"].append(passo_2)
        print(f"  ERRO: {e}")

    # Passo 3: Validacao geral
    print(f"\n[PASSO 3] Validacao geral...")

    tenant_ok = passo_1.get("correto", False)
    cliente_ok = resultado_teste_2["pasos"][-1].get("existe", False) if len(resultado_teste_2["pasos"]) > 1 else False
    id_negocio_ok = resultado_teste_2["pasos"][-1].get("id_negocio") == esperado_tenant if len(resultado_teste_2["pasos"]) > 1 else False

    resultado_teste_2["diagnostico"] = {
        "tenant_resolvido_corretamente": tenant_ok,
        "cliente_existe": cliente_ok,
        "id_negocio_correto": id_negocio_ok,
        "problema": not tenant_ok or not cliente_ok
    }

    print(f"  Tenant resolvido corretamente: {tenant_ok}")
    print(f"  Cliente existe em Firestore: {cliente_ok}")
    print(f"  id_negocio esta correto: {id_negocio_ok}")
    print(f"  PROBLEMA DETECTADO: {resultado_teste_2['diagnostico']['problema']}")

    return resultado_teste_2


# ============================================================================
# TESTE 3: DELETE_FIELD - ciclo save/clean/load
# ============================================================================

async def teste_3_delete_field():
    """Validar que DELETE_FIELD funciona em atualizar_dado_em_path()"""
    print("\n" + "="*80)
    print("TESTE 3: DELETE_FIELD - ciclo save/clean/load")
    print("="*80)

    tenant_id = "bateria_p0_dono_teste"
    actor_id = "bateria_p0_user_teste_001"
    path_v2 = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    path_v1 = f"Clientes/{actor_id}/MemoriaTemporaria/contexto"

    resultado_teste_3 = {
        "teste": "DELETE_FIELD",
        "path_v2": path_v2,
        "path_v1": path_v1,
        "pasos": []
    }

    # Passo 1: Criar documento com dados de teste
    print(f"\n[PASSO 1] Criar documento em {path_v2}...")
    try:
        dados_iniciais = {
            "estado_fluxo": "agendando",
            "draft_agendamento": {
                "profissional": "Bruna",
                "horario": "10:00"
            },
            "dados_confirmacao_agendamento": {
                "usuario_confirmou": False
            },
            "outras_dados": "valor",
            "_criado_em": datetime.now().isoformat()
        }

        resultado_salvar = await atualizar_dado_em_path(path_v2, dados_iniciais)

        passo_1 = {
            "acao": "criar documento",
            "path": path_v2,
            "campos_criados": list(dados_iniciais.keys()),
            "resultado": resultado_salvar,
            "status": "[OK]" if resultado_salvar else "[FALHA]"
        }

        resultado_teste_3["pasos"].append(passo_1)

        print(f"  Path: {path_v2}")
        print(f"  Campos criados: {list(dados_iniciais.keys())}")
        print(f"  Resultado: {resultado_salvar}")
        print(f"  Status: {passo_1['status']}")

    except Exception as e:
        passo_1 = {
            "acao": "criar documento",
            "path": path_v2,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_3["pasos"].append(passo_1)
        print(f"  ERRO: {e}")
        return resultado_teste_3

    # Passo 2: Ler antes de limpar
    print(f"\n[PASSO 2] Ler documento antes de limpar...")
    try:
        doc_antes = await buscar_dado_em_path(path_v2)

        passo_2 = {
            "acao": "ler antes",
            "path": path_v2,
            "campos_presentes": list(doc_antes.keys()) if doc_antes else [],
            "tem_draft": "draft_agendamento" in (doc_antes or {}),
            "tem_confirmacao": "dados_confirmacao_agendamento" in (doc_antes or {})
        }

        resultado_teste_3["pasos"].append(passo_2)

        print(f"  Path: {path_v2}")
        print(f"  Campos presentes: {passo_2['campos_presentes']}")
        print(f"  Tem draft_agendamento: {passo_2['tem_draft']}")
        print(f"  Tem dados_confirmacao_agendamento: {passo_2['tem_confirmacao']}")

    except Exception as e:
        passo_2 = {
            "acao": "ler antes",
            "path": path_v2,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_3["pasos"].append(passo_2)
        print(f"  ERRO: {e}")
        return resultado_teste_3

    # Passo 3: Limpar com DELETE_FIELD
    print(f"\n[PASSO 3] Limpar com DELETE_FIELD...")
    try:
        dados_limpeza = {
            "estado_fluxo": "idle",
            "draft_agendamento": firestore.DELETE_FIELD,
            "dados_confirmacao_agendamento": firestore.DELETE_FIELD,
            "_updated_at": datetime.now().isoformat()
        }

        resultado_limpeza = await atualizar_dado_em_path(path_v2, dados_limpeza)

        passo_3 = {
            "acao": "limpar com DELETE_FIELD",
            "path": path_v2,
            "campos_marcados_delete": [
                "draft_agendamento",
                "dados_confirmacao_agendamento"
            ],
            "resultado": resultado_limpeza,
            "status": "[OK]" if resultado_limpeza else "[FALHA]"
        }

        resultado_teste_3["pasos"].append(passo_3)

        print(f"  Path: {path_v2}")
        print(f"  Campos marcados para DELETE: {passo_3['campos_marcados_delete']}")
        print(f"  Resultado: {resultado_limpeza}")
        print(f"  Status: {passo_3['status']}")

    except Exception as e:
        passo_3 = {
            "acao": "limpar com DELETE_FIELD",
            "path": path_v2,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_3["pasos"].append(passo_3)
        print(f"  ERRO: {e}")
        return resultado_teste_3

    # Passo 4: Ler depois de limpar (path v2)
    print(f"\n[PASSO 4] Ler documento depois de limpar (path v2)...")
    try:
        doc_depois_v2 = await buscar_dado_em_path(path_v2)

        passo_4 = {
            "acao": "ler depois (v2)",
            "path": path_v2,
            "campos_presentes": list(doc_depois_v2.keys()) if doc_depois_v2 else [],
            "tem_draft": "draft_agendamento" in (doc_depois_v2 or {}),
            "tem_confirmacao": "dados_confirmacao_agendamento" in (doc_depois_v2 or {}),
            "delete_funcionou": (
                "draft_agendamento" not in (doc_depois_v2 or {}) and
                "dados_confirmacao_agendamento" not in (doc_depois_v2 or {})
            )
        }

        resultado_teste_3["pasos"].append(passo_4)

        print(f"  Path: {path_v2}")
        print(f"  Campos presentes agora: {passo_4['campos_presentes']}")
        print(f"  Tem draft_agendamento: {passo_4['tem_draft']} (deveria ser False)")
        print(f"  Tem dados_confirmacao_agendamento: {passo_4['tem_confirmacao']} (deveria ser False)")
        print(f"  DELETE_FIELD funcionou: {passo_4['delete_funcionou']}")

    except Exception as e:
        passo_4 = {
            "acao": "ler depois (v2)",
            "path": path_v2,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_3["pasos"].append(passo_4)
        print(f"  ERRO: {e}")

    # Passo 5: Ler path v1 (verificar se contexto tambem esta la)
    print(f"\n[PASSO 5] Ler path v1 legado (para comparacao)...")
    try:
        doc_v1 = await buscar_dado_em_path(path_v1)

        passo_5 = {
            "acao": "ler path v1 legado",
            "path": path_v1,
            "existe": doc_v1 is not None and len(doc_v1) > 0,
            "campos_presentes": list(doc_v1.keys()) if doc_v1 else [],
        }

        resultado_teste_3["pasos"].append(passo_5)

        print(f"  Path: {path_v1}")
        print(f"  Existe: {passo_5['existe']}")
        print(f"  Campos: {passo_5['campos_presentes']}")

    except Exception as e:
        passo_5 = {
            "acao": "ler path v1 legado",
            "path": path_v1,
            "erro": str(e),
            "status": "[EXCECAO]"
        }
        resultado_teste_3["pasos"].append(passo_5)
        print(f"  ERRO: {e}")

    # Passo 6: Diagnostico final
    print(f"\n[PASSO 6] Diagnostico final...")

    delete_funcionou = resultado_teste_3["pasos"][-2].get("delete_funcionou", False) if len(resultado_teste_3["pasos"]) > 3 else False

    resultado_teste_3["diagnostico"] = {
        "delete_field_funcionou": delete_funcionou,
        "problema_detectado": not delete_funcionou,
        "conclusao": "[OK] DELETE_FIELD funciona" if delete_funcionou else "[PROBLEMA] DELETE_FIELD nao esta funcionando"
    }

    print(f"  DELETE_FIELD funcionou: {delete_funcionou}")
    print(f"  Conclusao: {resultado_teste_3['diagnostico']['conclusao']}")

    return resultado_teste_3


# ============================================================================
# MAIN - Executar todos os testes e salvar resultado
# ============================================================================

async def main():
    print("\n" + "="*80)
    print("VALIDACAO OBJETIVA - 3 Diagnosticos P0")
    print("="*80)

    resultado_geral = {
        "timestamp": datetime.now().isoformat(),
        "testes": {}
    }

    # Teste 1
    print("\n[EXECUTANDO TESTE 1]")
    resultado_geral["testes"]["teste_1_normalizar_hora"] = await teste_1_normalizar_hora()

    # Teste 2
    print("\n[EXECUTANDO TESTE 2]")
    resultado_geral["testes"]["teste_2_obter_id_dono"] = await teste_2_obter_id_dono()

    # Teste 3
    print("\n[EXECUTANDO TESTE 3]")
    resultado_geral["testes"]["teste_3_delete_field"] = await teste_3_delete_field()

    # Salvar resultado
    print("\n" + "="*80)
    print("SALVANDO RESULTADO")
    print("="*80)

    resultado_arquivo = Path(__file__).parent / "resultado_validacao_diagnostico_p0.json"
    with open(resultado_arquivo, "w", encoding="utf-8") as f:
        json.dump(resultado_geral, f, indent=2, default=str)

    print(f"[OK] Resultado salvo em: {resultado_arquivo}")

    # Resumo final
    print("\n" + "="*80)
    print("RESUMO FINAL")
    print("="*80)

    print("\n[TESTE 1 - normalizar_hora]")
    t1 = resultado_geral["testes"]["teste_1_normalizar_hora"]
    status_1 = "[PROBLEMA]" if t1['resumo']['problematico'] else "[OK]"
    print(f"   Status: {status_1}")
    print(f"   Validos: {t1['resumo']['validos']}/{t1['resumo']['total']}")

    print("\n[TESTE 2 - obter_id_dono]")
    t2 = resultado_geral["testes"]["teste_2_obter_id_dono"]
    status_2 = "[PROBLEMA]" if t2['diagnostico']['problema'] else "[OK]"
    print(f"   Status: {status_2}")
    print(f"   Tenant resolvido: {t2['diagnostico']['tenant_resolvido_corretamente']}")
    print(f"   Cliente existe: {t2['diagnostico']['cliente_existe']}")

    print("\n[TESTE 3 - DELETE_FIELD]")
    t3 = resultado_geral["testes"]["teste_3_delete_field"]
    print(f"   Status: {t3['diagnostico']['conclusao']}")
    print(f"   DELETE_FIELD funcionou: {t3['diagnostico']['delete_field_funcionou']}")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
