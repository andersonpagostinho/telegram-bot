from config.firebase_config import db

# Criar um documento de teste no Firestore
doc_ref = db.collection("testes").document("primeiro_teste")
doc_ref.set({"mensagem": "Conexão bem-sucedida!"})

# Buscar o documento salvo
doc = doc_ref.get()
if doc.exists:
    print(f"✅ Firebase conectado e dados enviados com sucesso! Mensagem: {doc.to_dict()}")
else:
    print("❌ Erro: O documento não foi salvo corretamente!")
