from services.firestore_client import get_db

def salvar_tarefa(descricao):
    db = get_db()
    doc_ref = db.collection("Tarefas").document()
    doc_ref.set({"descricao": descricao, "prioridade": "baixa"})
    print(f"✅ Tarefa '{descricao}' salva no Firestore!")

# Teste manual
salvar_tarefa("Testando salvar tarefa no Firestore")
