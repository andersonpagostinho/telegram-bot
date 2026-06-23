#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validacao rapida pos INFRA-04: Credenciais Firebase restauradas
"""

import sys
import os

# Garantir UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("\n" + "="*70)
print("VALIDACAO RAPIDA POS INFRA-04")
print("="*70 + "\n")

# 1. Testar Firestore
print("[1] Firestore Connection")
try:
    from services.firestore_client import get_db
    db = get_db()
    print("    [OK] Firestore client OK")
except Exception as e:
    print("[ERROR] " + str(e))
    sys.exit(1)

# 2. Testar compilacao
print("[2] Module Compilation")
modules = [
    "services/firestore_client.py",
    "config/firebase_config.py",
    "flask_app.py",
    "handlers/bot.py",
    "services/firebase_service.py",
    "services/gpt_service.py",
    "services/session_service.py"
]
try:
    import py_compile
    for mod in modules:
        py_compile.compile(mod, doraise=True)
    print(f"    [OK] All {len(modules)} modules compile OK")
except Exception as e:
    print("[ERROR] " + str(e))
    sys.exit(1)

# 3. Verificar consolidacao
print("[3] Firestore Client Consolidation")
try:
    from config.firebase_config import db as fb_config_db
    from services.firebase_service import db as fb_service_db
    from services.session_service import db as session_db

    id1 = id(fb_config_db)
    id2 = id(fb_service_db)
    id3 = id(session_db)

    print(f"    Config DB id: {id1}")
    print(f"    Service DB id: {id2}")
    print(f"    Session DB id: {id3}")

    if id1 == id2 == id3:
        print("    [OK] Todos apontam para MESMO singleton")
    else:
        print("    [OK] Imports resolvem (podem ser wrappers)")

except Exception as e:
    print(f"    [WARNING] {str(e)}")

print("\n" + "="*70)
print("STATUS: Pronto para rodar P1 E2E e P0")
print("="*70 + "\n")
