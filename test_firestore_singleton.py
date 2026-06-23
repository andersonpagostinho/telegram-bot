#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste: Validar que Firestore client é reutilizado (singleton)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from services.firestore_client import get_db

print("\nTestando Firestore client singleton...\n")

# Chamar 10 vezes
clients = []
ids = []

print("[1] Obtendo cliente Firestore 10 vezes...")
for i in range(10):
    client = get_db()
    clients.append(client)
    client_id = id(client)
    ids.append(client_id)
    print(f"    [{i+1}] id={client_id}")

# Validar que todos são o mesmo objeto
print(f"\n[2] Validando reutilizacao...")
first_id = ids[0]
all_same = all(cid == first_id for cid in ids)

if all_same:
    print(f"    [PASS] Todos os 10 clientes tem o MESMO id: {first_id}")
    print(f"    Cliente esta sendo REUTILIZADO (singleton funciona)")
    sys.exit(0)
else:
    different_ids = set(ids)
    print(f"    [FAIL] Encontrados {len(different_ids)} ids diferentes:")
    for uid in different_ids:
        count = ids.count(uid)
        print(f"           id={uid} (apareceu {count}x)")
    print(f"    Cliente NAO esta sendo reutilizado!")
    sys.exit(1)
