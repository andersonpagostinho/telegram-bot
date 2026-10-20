#!/usr/bin/env python3
"""Debug da validacao de servico"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("FIREBASE_CREDENTIALS_B64", os.getenv("FIREBASE_CREDENTIALS_B64", ""))

async def debug():
    from services.profissional_service import listar_servicos_cadastrados
    import unidecode

    user_id = "5511991382080"
    servico_contexto = "corte feminino"

    print("\n" + "="*80)
    print("DEBUG VALIDACAO DE SERVICO")
    print("="*80)

    # Simular o que event_handler faz
    print(f"\nContexto recebido:")
    print(f"  user_id: {user_id}")
    print(f"  servico: {servico_contexto}")

    # 1. Listar servicos cadastrados
    servicos_cadastrados = await listar_servicos_cadastrados(user_id)
    print(f"\nServicos cadastrados (de Profissionais):")
    print(f"  {servicos_cadastrados}")

    # 2. Normalizar
    def norm(x):
        return unidecode.unidecode(str(x).strip().lower())

    servicos_norm = [norm(s) for s in servicos_cadastrados]
    print(f"\nServicos normalizados:")
    print(f"  {servicos_norm}")

    servico_norm = norm(servico_contexto)
    print(f"\nServico do contexto normalizado:")
    print(f"  '{servico_contexto}' → '{servico_norm}'")

    # 3. Comparar
    encontrado = servico_norm in servicos_norm
    print(f"\nValidacao:")
    print(f"  '{servico_norm}' in {servicos_norm}")
    print(f"  Resultado: {encontrado}")

    if not encontrado:
        print(f"\n  [ERRO] Servico inexistente!")
    else:
        print(f"\n  [OK] Servico valido!")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(debug())
