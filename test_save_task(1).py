from config.firebase_config import db

def salvar_tarefa(descricao):
    doc_ref = db.collection("Tarefas").document()
    doc_ref.set({"descricao": descricao, "prioridade": "baixa"})
    print(f"✅ Tarefa '{descricao}' salva no Firestore!")

# Teste manual
salvar_tarefa("Testando salvar tarefa no Firestore")
