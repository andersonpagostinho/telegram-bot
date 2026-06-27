#!/usr/bin/env python3
"""
Verifica se documento especifico existe e lista suas subcoleções
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore

def init_firestore():
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not os.path.exists(cred_path):
        raise Exception("Credenciais nao encontradas")

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"projectId": "projeto-agente-inteligente"})
    except ValueError:
        pass

    return firestore.client()

def main():
    print("=" * 80)
    print("VERIFICANDO: Clientes/dono_teste_f6d12d49_02")
    print("=" * 80 + "\n")

    db = init_firestore()

    ref = db.document("Clientes/dono_teste_f6d12d49_02")

    print("Verificando se documento existe...")
    exists = ref.get().exists
    print(f"ref.get().exists = {exists}\n")

    print("Listando subcoleções...")
    try:
        subcols = [c.id for c in ref.collections()]
        print(f"Subcoleções: {subcols}")
        print(f"Total de subcoleções: {len(subcols)}\n")

        if subcols:
            print("Detalhes das subcoleções:")
            for col_name in subcols:
                doc_count = len(list(ref.collection(col_name).stream()))
                print(f"  - {col_name}: {doc_count} documentos")
    except Exception as e:
        print(f"ERRO ao listar subcoleções: {e}\n")

    print("=" * 80)
    print("RESULTADO:")
    print("=" * 80)

    if exists:
        print(f"[ENCONTRADO] Clientes/dono_teste_f6d12d49_02 EXISTE")
        doc_data = ref.get().to_dict()
        print(f"Dados: {doc_data}")
    else:
        print(f"[NAO EXISTE] Clientes/dono_teste_f6d12d49_02 eh um documento fantasma/orfao")
        print("(Aparece na visualizacao, mas nao tem conteudo real)")

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
