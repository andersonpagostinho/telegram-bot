# Gerenciador centralizado de cliente Firestore
# Responsabilidade: Inicializar e reutilizar cliente Firebase de forma segura
# Evita duplicação de inicialização e centraliza configuração

import firebase_admin
from firebase_admin import firestore
import os

# [INFRA-02 PATCH] Cache singleton do cliente Firestore
# Evita acúmulo de conexões gRPC ao reutilizar um único cliente
_firestore_client = None


def get_db():
    """
    Obtém cliente Firestore, inicializando Firebase uma única vez se necessário.

    [INFRA-02 PATCH] Agora reutiliza a mesma instância de cliente para evitar
    acúmulo de conexões gRPC que causam timeout no shutdown.

    Esta função é thread-safe e pode ser chamada múltiplas vezes sem risco de
    dupla inicialização (firebase_admin valida automaticamente).

    Returns:
        firestore.client() - Cliente Firestore pronto para usar (REUTILIZADO)

    Raises:
        ValueError: Se Firebase não conseguir inicializar
    """
    global _firestore_client

    try:
        # Verificar se app já está inicializado
        firebase_admin.get_app()
    except ValueError:
        # Firebase não inicializado, tentar inicializar
        _inicializar_firebase()

    # [INFRA-02] Retornar cliente em cache em vez de criar novo
    if _firestore_client is None:
        _firestore_client = firestore.client()

    return _firestore_client


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
                with open(creds_path, 'r') as f:
                    creds_dict = json.load(f)
                cred = firebase_admin.credentials.Certificate(creds_dict)
                firebase_admin.initialize_app(cred)
                print(f"[OK] Firebase inicializado com credenciais locais: {creds_path}")
                return
            except Exception as e:
                print(f"[AVISO] Falha ao usar {creds_path}: {e}")

    # Estratégia 2: Variável de ambiente FIREBASE_CREDENTIALS (JSON string)
    if os.environ.get("FIREBASE_CREDENTIALS"):
        try:
            import json
            creds_json = os.environ.get("FIREBASE_CREDENTIALS")
            if not creds_json or len(creds_json) < 10:
                raise ValueError("FIREBASE_CREDENTIALS está vazio ou muito curto (pode estar truncado)")

            creds_dict = json.loads(creds_json)
            if not isinstance(creds_dict, dict) or "type" not in creds_dict:
                raise ValueError("FIREBASE_CREDENTIALS não é um JSON de credenciais válido (falta campo 'type')")

            cred = firebase_admin.credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
            print("[OK] Firebase inicializado com FIREBASE_CREDENTIALS (env var)")
            return
        except json.JSONDecodeError as e:
            print(f"[ERRO] FIREBASE_CREDENTIALS JSON inválido: {e}")
            print("[DICA] Verificar se a variável está truncada. Use: $env:FIREBASE_CREDENTIALS='...' (PowerShell)")
        except ValueError as e:
            print(f"[ERRO] FIREBASE_CREDENTIALS inválido: {e}")
            print("[DICA] Usar GOOGLE_APPLICATION_CREDENTIALS ao invés, ou arquivo firebaseConfig.json")
        except Exception as e:
            print(f"[AVISO] Falha com FIREBASE_CREDENTIALS: {e}")

    # Estratégia 3: Variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            firebase_admin.initialize_app()
            print("[OK] Firebase inicializado com GOOGLE_APPLICATION_CREDENTIALS")
            return
        except Exception as e:
            print(f"[AVISO] Falha com GOOGLE_APPLICATION_CREDENTIALS: {e}")

    # Estratégia 4: Application Default Credentials
    try:
        firebase_admin.initialize_app()
        print("[OK] Firebase inicializado com Application Default Credentials")
        return
    except Exception as e:
        print(f"[ERRO] Falha na inicialização Firebase: {e}")
        raise ValueError(f"Não foi possível inicializar Firebase: {e}")
