# tests/mocks/agenda_mock.py
"""Mock para agenda/validação de horário - validação mínima"""

class AgendaMock:
    def __init__(self):
        self.chamadas = {
            "validar_horario_funcionamento": []
        }

    async def validar_horario_funcionamento(
        self,
        user_id: str,
        data_iso: str,
        hora_inicio: str,
        duracao_min: int,
        profissional: str = None
    ):
        """Valida se horário está dentro do expediente (8h-18h)"""
        self.chamadas["validar_horario_funcionamento"].append({
            "user_id": user_id,
            "data_iso": data_iso,
            "hora_inicio": hora_inicio,
            "duracao_min": duracao_min,
            "profissional": profissional
        })

        # Validação mínima: expediente 8h-18h
        try:
            hora = int(hora_inicio.split(":")[0])
            if hora < 8 or hora >= 18:
                return {
                    "permitido": False,
                    "motivo": "fora_expediente"
                }
        except Exception:
            return {
                "permitido": False,
                "motivo": "horario_invalido"
            }

        return {
            "permitido": True,
            "motivo": "horario_disponivel"
        }

    def reset(self):
        """Limpa chamadas para novo teste"""
        self.chamadas = {
            "validar_horario_funcionamento": []
        }
