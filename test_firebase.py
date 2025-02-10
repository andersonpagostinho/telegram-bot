import firebase_admin
from firebase_admin import credentials, firestore

# Caminho para o arquivo JSON da chave do Firebase
cred = credentials.Certificate("chave_firebase.json")

# Inicializa o Firebase
firebase_admin.initialize_app(cred)

# Conectar ao Firestore
db = firestore.client()

# Testar criando um documento no Firestore
doc_ref = db.collection("testes").document("primeiro_teste")
doc_ref.set({"mensagem": "Conexão bem-sucedida!"})

print("✅ Firebase conectado e dados enviados com sucesso!")