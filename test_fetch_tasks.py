from config.firebase_config import db

def buscar_tarefas():
    tarefas_ref = db.collection("Tarefas").stream()
    tarefas = [tarefa.to_dict() for tarefa in tarefas_ref]
    
    if tarefas:
        print("📌 Tarefas encontradas no Firestore:")
        for t in tarefas:
            print(f"- {t['descricao']} ({t.get('prioridade', 'baixa')})")
    else:
        print("📭 Nenhuma tarefa encontrada!")

# Teste manual
buscar_tarefas()
