import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# 🔹 Forçar o Firebase a usar o arquivo local
firebase_credentials_path = "firebase_credentials.json"

# 🔹 Remove a variável de ambiente para evitar conflitos
if "FIREBASE_CREDENTIALS" in os.environ:
    del os.environ["FIREBASE_CREDENTIALS"]

# 🔹 Carregar credenciais do arquivo JSON
with open(firebase_credentials_path) as f:
    cred_info = json.load(f)

# 🔹 Inicializar Firebase apenas se ainda não estiver rodando
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_info)
    firebase_admin.initialize_app(cred)

# 🔹 Conectar ao Firestore
db = firestore.client()

# 🔹 Agora, importar firebase_service SEM QUE ELE INICIALIZE O FIREBASE NOVAMENTE
import importlib.util

firebase_service_path = os.path.join(os.getcwd(), "services", "firebase_service.py")
spec = importlib.util.spec_from_file_location("firebase_service", firebase_service_path)
firebase_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firebase_service)

user_id = "7394370553"
calendar_id = "andersonpagostinho@gmail.com"

print("\n🔹 Testando salvamento de dados no Firebase...")
sucesso = firebase_service.salvar_cliente(user_id, {"calendar_id": calendar_id})

if sucesso:
    print("✅ Dados salvos com sucesso!")
else:
    print("❌ Falha ao salvar os dados!")

print("\n🔹 Testando busca de dados no Firebase...")
dados = firebase_service.buscar_cliente(user_id)

if dados:
    print(f"✅ Dados encontrados: {dados}")
else:
    print("❌ Nenhum dado encontrado no Firebase!")
