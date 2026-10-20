#!/usr/bin/env python3
"""Investiga estrutura de ServicosNegocio no Firestore"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("FIREBASE_CREDENTIALS_B64", os.getenv("FIREBASE_CREDENTIALS_B64", ""))

async def investigar():
    from firebase_admin import firestore
    import firebase_admin
    from google.cloud.firestore import AsyncClient

    # Inicializar Firebase
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    db = firestore.client()

    tenant = "7394370553"

    print("\n" + "="*80)
    print("INVESTIGACAO DE ServicosNegocio")
    print("="*80)

    # 1. Verificar coleção ServicosNegocio
    print(f"\n[1] Buscando colecao: Clientes/{tenant}/ServicosNegocio")
    try:
        docs = db.collection(f"Clientes/{tenant}/ServicosNegocio").stream()
        servicos = []
        for doc in docs:
            data = doc.to_dict()
            servicos.append({
                'id': doc.id,
                'nome': data.get('nome'),
                'tipo': type(data.get('nome')).__name__,
                'keys': list(data.keys())
            })
            print(f"  - {doc.id}: nome='{data.get('nome')}'")
            print(f"    chaves: {list(data.keys())}")
            print(f"    dados completos: {data}")

        if not servicos:
            print("  [VAZIO] Nenhum servico encontrado em ServicosNegocio")
        else:
            print(f"\n  Total: {len(servicos)} servicos")
    except Exception as e:
        print(f"  [ERRO] {e}")

    # 2. Verificar Profissionais e seus servicos
    print(f"\n[2] Buscando servicos em Profissionais:")
    try:
        prof_docs = db.collection(f"Clientes/{tenant}/Profissionais").stream()
        for prof_doc in prof_docs:
            prof_data = prof_doc.to_dict()
            servicos_prof = prof_data.get('servicos', [])
            print(f"  - {prof_doc.id} ({prof_data.get('nome')}):")
            print(f"    servicos: {servicos_prof}")
    except Exception as e:
        print(f"  [ERRO] {e}")

    # 3. Procurar por "corte feminino" em diferentes formatos
    print(f"\n[3] Procurando 'corte feminino' em diferentes formatos:")
    try:
        # Tentar variações
        variations = [
            "corte feminino",
            "corte_feminino",
            "Corte Feminino",
            "corte feminino".lower(),
        ]

        for var in variations:
            doc = db.collection(f"Clientes/{tenant}/ServicosNegocio").document(var).get()
            if doc.exists:
                print(f"  ENCONTRADO com chave '{var}':")
                print(f"    {doc.to_dict()}")
            else:
                print(f"  Nao encontrado com chave '{var}'")
    except Exception as e:
        print(f"  [ERRO] {e}")

    # 4. Ver estrutura de um servico existente (se houver)
    print(f"\n[4] Estrutura de servicos encontrados:")
    try:
        docs = db.collection(f"Clientes/{tenant}/ServicosNegocio").limit(1).stream()
        for doc in docs:
            print(f"  Exemplo: {doc.id}")
            print(f"  Estrutura completa:")
            data = doc.to_dict()
            for key, value in data.items():
                print(f"    {key}: {type(value).__name__} = {value}")
    except Exception as e:
        print(f"  [ERRO] {e}")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(investigar())
