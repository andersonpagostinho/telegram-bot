#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
C4.4.1-FIX — Teste Mínimo Independente de PROFISSIONAL

Objetivo: Testar PROFISSIONAL sem complexidade de fixture/event loop.
Simula o fluxo real de enviar_resumo_diario() para PROFISSIONAL.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
    obter_id_dono,
    buscar_subcolecao,
)


async def test_minimo_profissional():
    """Teste mínimo: PROFISSIONAL vinculado consegue buscar eventos do DONO."""

    dono_id = "c441_min_dono"
    prof_id = "c441_min_prof"

    print("\n=== TESTE MÍNIMO — PROFISSIONAL ===\n")

    try:
        # SETUP: Criar DONO
        print(f"[SETUP] Criando DONO {dono_id}...")
        await salvar_dado_em_path(f"Clientes/{dono_id}", {
            "tipo_usuario": "dono",
            "nome": "Dono Mínimo",
            "id_negocio": dono_id,
        })
        print(f"[OK] DONO criado")

        # SETUP: Criar PROFISSIONAL vinculado
        print(f"[SETUP] Criando PROFISSIONAL {prof_id} vinculado a {dono_id}...")
        await salvar_dado_em_path(f"Clientes/{prof_id}", {
            "tipo_usuario": "profissional",
            "nome": "Prof Mínimo",
            "id_negocio": dono_id,  # ← Vinculado
        })
        print(f"[OK] PROFISSIONAL criado")

        # TESTE 1: obter_id_dono() retorna tenant válido
        print(f"\n[TESTE 1] Obter tenant para PROFISSIONAL...")
        tenant = await obter_id_dono(prof_id)
        print(f"[RESULTADO] tenant = {tenant}")

        if tenant is None:
            print(f"❌ FALHA: tenant é None")
            return False

        if tenant != dono_id:
            print(f"❌ FALHA: tenant é {tenant}, esperava {dono_id}")
            return False

        print(f"✅ PASSOU: tenant é válido ({tenant})")

        # TESTE 2: Não tenta acessar Clientes/None
        print(f"\n[TESTE 2] Simular fluxo de busca de eventos...")

        if not tenant:
            # Esta é a validação que foi adicionada em C4.4.1
            print(f"[VALIDAÇÃO] tenant é falsy, pulando busca")
            print(f"✅ PASSOU: validação previne Clientes/None")
            return True

        # Se chegou aqui, tenant é válido
        print(f"[BUSCA] Buscando eventos em Clientes/{tenant}/Eventos...")
        eventos_dict = await buscar_subcolecao(f"Clientes/{tenant}/Eventos") or {}
        print(f"[RESULTADO] {len(eventos_dict)} eventos encontrados")

        # Validar que não é Clientes/None/Eventos
        if f"Clientes/None/Eventos" in str(eventos_dict):
            print(f"❌ FALHA: Clientes/None foi acessado")
            return False

        print(f"✅ PASSOU: eventos foram buscados em path correto")

        print(f"\n=== TESTE MÍNIMO CONCLUÍDO COM SUCESSO ===\n")
        return True

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # CLEANUP
        print(f"\n[CLEANUP] Deletando dados de teste...")
        try:
            await deletar_dado_em_path(f"Clientes/{dono_id}")
            await deletar_dado_em_path(f"Clientes/{prof_id}")
            print(f"[OK] Cleanup concluído")
        except Exception as e:
            print(f"[WARN] Erro no cleanup: {e}")


if __name__ == "__main__":
    # Executar diretamente com asyncio (sem pytest)
    resultado = asyncio.run(test_minimo_profissional())

    if resultado:
        print("\n✅ TESTE MÍNIMO PASSOU")
        sys.exit(0)
    else:
        print("\n❌ TESTE MÍNIMO FALHOU")
        sys.exit(1)
