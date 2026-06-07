# tests/mocks/gpt_mock.py
"""Mock para GPT - gera respostas fake baseado no tipo"""

class GPTMock:
    def __init__(self):
        self.chamadas = {
            "gerar_resposta_p1": []
        }

    async def gerar_resposta_p1(self, payload: dict):
        """Gera resposta de confirmação fake baseado no tipo"""
        self.chamadas["gerar_resposta_p1"].append(payload)

        tipo = payload.get("tipo")
        servico = payload.get("servico", "serviço")
        profissional = payload.get("profissional", "profissional")
        data_hora_legivel = payload.get("data_hora_legivel", "em breve")

        # Respostas genéricas por tipo
        if tipo == "confirmar_agendamento":
            return f"Perfeito! {servico.capitalize()} com {profissional} {data_hora_legivel}. Confirma?"

        elif tipo == "pedir_servico":
            return f"Qual serviço você deseja?"

        elif tipo == "pedir_profissional":
            return f"Com qual profissional você prefere?"

        elif tipo == "pedir_horario":
            return f"Qual horário você prefere?"

        elif tipo == "pedir_data":
            return f"Qual data você prefere?"

        return "Pode me esclarecer um pouco mais?"

    def reset(self):
        """Limpa chamadas para novo teste"""
        self.chamadas = {
            "gerar_resposta_p1": []
        }
