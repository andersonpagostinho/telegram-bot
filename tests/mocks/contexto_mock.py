# tests/mocks/contexto_mock.py
"""Mock para contexto temporário - armazena em memória"""

class ContextoMock:
    def __init__(self):
        self.storage = {}  # {user_id: ctx_dict}
        self.chamadas = {
            "carregar_contexto_temporario": [],
            "salvar_contexto_temporario": []
        }

    async def carregar_contexto_temporario(self, user_id: str):
        """Carrega contexto da memória - replica utils/contexto_temporario.py"""
        self.chamadas["carregar_contexto_temporario"].append({"user_id": user_id})
        data = self.storage.get(user_id)
        return data

    async def salvar_contexto_temporario(self, user_id: str, contexto: dict):
        """Salva contexto na memória com merge - replica utils/contexto_temporario.py"""
        self.chamadas["salvar_contexto_temporario"].append(
            {"user_id": user_id, "ctx_keys": list(contexto.keys()) if contexto else []}
        )

        if not contexto:
            return

        if user_id not in self.storage:
            self.storage[user_id] = {}

        # Merge raso: atualiza chaves existentes
        self.storage[user_id].update(contexto)

    def get_contexto_final(self, user_id: str):
        """Retorna contexto final armazenado"""
        return self.storage.get(user_id, {})

    def reset(self):
        """Limpa tudo para novo teste"""
        self.storage.clear()
        self.chamadas = {
            "carregar_contexto_temporario": [],
            "salvar_contexto_temporario": []
        }
