# Gerenciador centralizado de cliente Firestore
# Responsabilidade: Inicializar e reutilizar cliente Firebase de forma segura
# Evita duplicação de inicialização e centraliza configuração

import firebase_admin
from firebase_admin import firestore
import os


def get_db():
    """
    Obtém cliente Firestore, inicializando Firebase uma única vez se necessário.

    Esta função é thread-safe e pode ser chamada múltiplas vezes sem risco de
    dupla inicialização (firebase_admin valida automaticamente).

    Returns:
        firestore.client() - Cliente Firestore pronto para usar

    Raises:
        ValueError: Se Firebase não conseguir inicializar
    """
    try:
        # Verificar se app já está inicializado
        firebase_admin.get_app()
    except ValueError:
        # Firebase não inicializado, tentar inicializar
        _inicializar_firebase()

    return firestore.client()


def _inicializar_firebase():
    """
    Inicializa Firebase Admin SDK com credenciais.

    Tenta em ordem:
    1. firebaseConfig.json (local)
    2. GOOGLE_APPLICATION_CREDENTIALS (variável ambiente)
    3. Application Default Credentials (Cloud)

    Raises:
        ValueError: Se nenhuma estratégia de autenticação funcionou
    """
    import json

    # Estratégia 1: Arquivo local
    creds_paths = [
        os.path.join(os.path.dirname(__file__), "..", "firebaseConfig.json"),
        os.path.join(os.getcwd(), "firebaseConfig.json"),
    ]

    for creds_path in creds_paths:
        if os.path.exists(creds_path):
            try:
                cred = firestore.credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
                print(f"[OK] Firebase inicializado com credenciais locais: {creds_path}")
                return
            except Exception as e:
                print(f"[AVISO] Falha ao usar {creds_path}: {e}")

    # Estratégia 2: Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            firebase_admin.initialize_app()
            print("[OK] Firebase inicializado com GOOGLE_APPLICATION_CREDENTIALS")
            return
        except Exception as e:
            print(f"[AVISO] Falha com GOOGLE_APPLICATION_CREDENTIALS: {e}")

    # Estratégia 3: Application Default Credentials
    try:
        firebase_admin.initialize_app()
        print("[OK] Firebase inicializado com Application Default Credentials")
        return
    except Exception as e:
        print(f"[ERRO] Falha na inicialização Firebase: {e}")
        raise ValueError(f"Não foi possível inicializar Firebase: {e}")
