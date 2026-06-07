# tests/mocks/firebase_mock.py
"""Mock para Firebase - retorna dados fake"""

class FirebaseMock:
    def __init__(self):
        self.chamadas = {
            "obter_id_dono": [],
            "buscar_subcolecao": []
        }

    async def obter_id_dono(self, user_id: str):
        """Retorna ID do dono (fake)"""
        self.chamadas["obter_id_dono"].append({"user_id": user_id})
        return "dono_teste_001"

    async def buscar_subcolecao(self, path: str):
        """Retorna dados baseado na path"""
        self.chamadas["buscar_subcolecao"].append({"path": path})

        if "Profissionais" in path:
            return {
                "prof_1": {
                    "nome": "Carla",
                    "servicos": ["corte", "escova", "hidratação"]
                },
                "prof_2": {
                    "nome": "Bruna",
                    "servicos": ["corte", "escova", "coloração"]
                },
                "prof_3": {
                    "nome": "Joana",
                    "servicos": ["escova", "hidratação"]
                }
            }

        elif "Servicos" in path:
            return {
                "srv_1": {
                    "nome": "corte",
                    "duracao": 30,
                    "preco": 50
                },
                "srv_2": {
                    "nome": "escova",
                    "duracao": 45,
                    "preco": 60
                },
                "srv_3": {
                    "nome": "hidratação",
                    "duracao": 60,
                    "preco": 80
                },
                "srv_4": {
                    "nome": "coloração",
                    "duracao": 90,
                    "preco": 120
                }
            }

        elif "Agenda" in path:
            # Sem eventos = sem conflitos
            return {}

        return {}

    async def verificar_conflito_e_sugestoes_profissional(
        self,
        user_id: str,
        data: str,
        hora_inicio: str,
        duracao_min: int,
        profissional: str = None,
        servico: str = None,
        event_id: str = None
    ):
        """Retorna resultado de conflito - replica services/event_service_async.py"""
        self.chamadas["verificar_conflito_e_sugestoes_profissional"] = {
            "user_id": user_id,
            "data": data,
            "hora_inicio": hora_inicio,
            "duracao_min": duracao_min,
            "profissional": profissional,
            "servico": servico,
            "event_id": event_id
        }

        # Simular: sem conflito (sempre)
        return {
            "conflito": False,
            "sugestoes": [],
            "profissional_alternativo": None
        }

    def reset(self):
        """Limpa chamadas para novo teste"""
        self.chamadas = {
            "obter_id_dono": [],
            "buscar_subcolecao": []
        }
