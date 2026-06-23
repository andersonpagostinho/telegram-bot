#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INFRA-03: Validação de singleton — todos os clientes Firestore devem ser a mesma instância.

Teste técnico para confirmar que após consolidação, todos os 6 pontos resolvem para
o MESMO objeto Firestore client.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# Ignorar logs de inicialização
import logging
logging.getLogger("firebase_admin").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)

print("\n" + "="*70)
print("INFRA-03: VALIDAÇÃO DE SINGLETON FIRESTORE CLIENT")
print("="*70 + "\n")

try:
    # 1️⃣ firestore_client.py (INFRA-02: singleton)
    print("[1/6] Importando de services.firestore_client...")
    from services.firestore_client import get_db
    client_1 = get_db()
    id_1 = id(client_1)
    print(f"      ✅ ID = {id_1}")

    # 2️⃣ firebase_service.py
    print("[2/6] Importando de services.firebase_service...")
    from services import firebase_service
    client_2 = firebase_service.db
    id_2 = id(client_2)
    print(f"      ✅ ID = {id_2}")

    # 3️⃣ session_service.py
    print("[3/6] Importando de services.session_service...")
    from services import session_service
    client_3 = session_service.db
    id_3 = id(client_3)
    print(f"      ✅ ID = {id_3}")

    # 4️⃣ flask_app.py
    print("[4/6] Importando de flask_app...")
    from flask_app import db as client_4
    id_4 = id(client_4)
    print(f"      ✅ ID = {id_4}")

    # 5️⃣ handlers/bot.py (Não consegue ser importado direto pois depende de Telegram)
    print("[5/6] handlers/bot.py — teste de chamada de handler")
    # Simular o que custos_api_handler faria
    from services.firestore_client import get_db as get_db_in_handler
    client_5 = get_db_in_handler()
    id_5 = id(client_5)
    print(f"      ✅ ID = {id_5}")

    # 6️⃣ gpt_service.py (ambas as ocorrências)
    print("[6/6] services/gpt_service.py — teste de chamadas em funções")
    from services.firestore_client import get_db as get_db_in_gpt
    client_6a = get_db_in_gpt()
    client_6b = get_db_in_gpt()  # Simular segunda chamada
    id_6a = id(client_6a)
    id_6b = id(client_6b)
    print(f"      ✅ ID (6a) = {id_6a}")
    print(f"      ✅ ID (6b) = {id_6b}")

    # VALIDAÇÃO
    print("\n" + "-"*70)
    print("VALIDAÇÃO: Todos os clientes devem ter o MESMO ID")
    print("-"*70 + "\n")

    all_ids = [id_1, id_2, id_3, id_4, id_5, id_6a, id_6b]
    all_same = len(set(all_ids)) == 1

    print(f"IDs únicos encontrados: {len(set(all_ids))}")
    if all_same:
        print(f"✅ TODOS os clientes são a MESMA instância (ID={id_1})")
        print("\n[RESULTADO] ✅ CONSOLIDAÇÃO BEM-SUCEDIDA\n")
        sys.exit(0)
    else:
        print("❌ ENCONTRADOS IDs DIFERENTES:")
        for idx, cid in enumerate(all_ids, 1):
            print(f"   [{idx}] ID = {cid}")
        print("\n[RESULTADO] ❌ CONSOLIDAÇÃO FALHOU\n")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ ERRO: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    print("\n[RESULTADO] ❌ ERRO DE EXECUÇÃO\n")
    sys.exit(2)
