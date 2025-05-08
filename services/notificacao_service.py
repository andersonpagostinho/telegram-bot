from datetime import datetime, timedelta
from services.firebase_service_async import salvar_dado_em_path
import uuid

async def criar_notificacao_agendada(user_id: str, descricao: str, data: str, hora_inicio: str, canal="telegram", minutos_antes=30):
    """
    Cria uma notificação agendada para um evento, a ser disparada X minutos antes.

    Args:
        user_id (str): ID do usuário no Firebase
        descricao (str): Descrição do evento
        data (str): Data do evento no formato YYYY-MM-DD
        hora_inicio (str): Hora de início do evento (HH:MM)
        canal (str): Canal preferido (telegram, whatsapp, email)
        minutos_antes (int): Quantos minutos antes avisar (default: 30)

    Returns:
        bool: True se salvou com sucesso, False caso contrário
    """
    try:
        data_evento = datetime.fromisoformat(f"{data}T{hora_inicio}")
        horario_notificacao = data_evento - timedelta(minutes=minutos_antes)

        notificacao = {
            "mensagem": f"⏰ Lembrete: {descricao} às {hora_inicio}.",
            "data_hora": horario_notificacao.isoformat(),
            "tipo": "evento",
            "canal": canal,
            "avisado": False
        }

        id_notificacao = str(uuid.uuid4())
        await salvar_dado_em_path(f"Clientes/{user_id}/NotificacoesAgendadas/{id_notificacao}", notificacao)

        return True
    except Exception as e:
        print(f"❌ Erro ao criar notificação agendada: {e}")
        return False
