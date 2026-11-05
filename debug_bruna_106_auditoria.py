"""
P0.27.5 — Debug: Por que Bruna 10:00 em 2026-11-06 não está entre os 434?

Os 4 locks existem:
- status: confirmado
- expira_em: 2026-10-21T22:00:00.119453 (expirado!)
- evento_id: whatsapp:5511991382080_bruna_2026-11-06_10:00

Mas não foram identificados pela função liberar_locks_orfaos_expirados()

Hipóteses:
1. Evento correspondente foi encontrado (falha na busca?)
2. Evento legado foi encontrado
3. Status não é "confirmado" (improvável)
4. Não estão expirados (improvável, confirmado como expirado)
5. evento_id é vazio (improvável, confirmado que existe)
"""

import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.firebase_service_async import buscar_dado_em_path

TENANT_ID = "7394370553"

# Evento_id dos locks de Bruna
EVENTO_ID = "whatsapp:5511991382080_bruna_2026-11-06_10:00"
EVENTO_ID_LEGADO = EVENTO_ID.rsplit("_", 1)[0]  # Remove última parte (hora)


async def debug():
    """Debug do processamento de Bruna 2026-11-06"""
    print("\n" + "="*80)
    print("P0.27.5 — DEBUG: POR QUE BRUNA NÃO FOI IDENTIFICADA?")
    print("="*80)

    print(f"\nDados do lock:")
    print(f"  evento_id: {EVENTO_ID}")
    print(f"  evento_id_legado: {EVENTO_ID_LEGADO}")

    # Teste 1: Buscar evento_id exato
    print(f"\n[TESTE 1] Buscar evento com ID EXATO")
    print(f"  Path: Clientes/{TENANT_ID}/Eventos/{EVENTO_ID}")

    evento_exato = await buscar_dado_em_path(
        f"Clientes/{TENANT_ID}/Eventos/{EVENTO_ID}"
    )

    if evento_exato:
        print(f"  ✓ ENCONTRADO (evento exato)")
        print(f"    Isso explica por que lock não foi identificado como órfão!")
        return True
    else:
        print(f"  ❌ Não encontrado (evento exato)")

    # Teste 2: Buscar evento_id legado
    print(f"\n[TESTE 2] Buscar evento com ID LEGADO")
    print(f"  Path: Clientes/{TENANT_ID}/Eventos/{EVENTO_ID_LEGADO}")

    evento_legado = await buscar_dado_em_path(
        f"Clientes/{TENANT_ID}/Eventos/{EVENTO_ID_LEGADO}"
    )

    if evento_legado:
        print(f"  ✓ ENCONTRADO (evento legado)")
        print(f"    Isso explica por que lock não foi identificado como órfão!")
        return True
    else:
        print(f"  ❌ Não encontrado (evento legado)")

    # Teste 3: Procurar variações
    print(f"\n[TESTE 3] Procurar variações de evento_id")

    variacoes = [
        ("Sem hora", "whatsapp:5511991382080_bruna_2026-11-06"),
        ("Data só", "bruna_2026-11-06"),
        ("Cliente+prof", "whatsapp:5511991382080_bruna"),
        ("Sem colon", "5511991382080_bruna_2026-11-06_10:00"),
    ]

    encontrado_alguma = False
    for nome, var_id in variacoes:
        try:
            evento = await buscar_dado_em_path(
                f"Clientes/{TENANT_ID}/Eventos/{var_id}"
            )
            if evento:
                print(f"  ✓ ENCONTRADO: {nome} → {var_id}")
                encontrado_alguma = True
            else:
                print(f"  ❌ {nome} → {var_id}")
        except:
            print(f"  ❌ {nome} → {var_id} (erro)")

    if encontrado_alguma:
        print(f"\n  ⚠️ Evento encontrado em variação! Isso explica o problema.")
        return True

    # Teste 4: Conclusão
    print(f"\n" + "="*80)
    print("CONCLUSÃO")
    print("="*80)

    print(f"\n❌ Nenhum evento encontrado (nem exato, nem legado, nem variações)")
    print(f"\nO lock deveria ter sido identificado como órfão!")
    print(f"Status: BUG na função liberar_locks_orfaos_expirados()")

    print(f"\n🔴 PROBLEMA: Os 4 locks de Bruna não estão entre os 434")
    print(f"   Possível motivo: Função não iterou sobre todos os locks do Firestore")
    print(f"   Verificar: buscar_subcolecao() retorna todos os documentos?")

    print(f"\n" + "="*80 + "\n")

    return False


if __name__ == "__main__":
    asyncio.run(debug())
