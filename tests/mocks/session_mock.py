# tests/mocks/session_mock.py
"""Mock para session_service - previne acesso a Firebase"""


class SessionMock:
    def __init__(self):
        self.chamadas = {
            "pegar_sessao": [],
            "resetar_sessao": [],
        }

    async def pegar_sessao(self, user_id: str):
        """Retorna None (sem sessão ativa) para novo usuário"""
        self.chamadas["pegar_sessao"].append({"user_id": user_id})
        return None

    async def resetar_sessao(self, user_id: str):
        """Registra tentativa de resetar sessão (no mock, não faz nada)"""
        self.chamadas["resetar_sessao"].append({"user_id": user_id})
        return None

    def reset(self):
        """Limpa chamadas para novo teste"""
        self.chamadas = {
            "pegar_sessao": [],
            "resetar_sessao": [],
        }
