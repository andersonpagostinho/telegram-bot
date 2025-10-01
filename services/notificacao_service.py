# services/notificacao_service.py
from datetime import datetime, timedelta
from services.firebase_service_async import salvar_dado_em_path
import uuid

async def criar_notificacao_agendada(
    user_id: str,
    descricao: str,
    data: str,                 # "YYYY-MM-DD"
    hora_inicio: str,          # "HH:MM"
    canal: str = "telegram",
    minutos_antes: int = 30,
    destinatario_user_id: str | None = None,  # 👈 quem vai receber o aviso (se None, usa user_id)
    alvo_evento: dict | None = None,          # 👈 dados extras p/ construir a mensagem no worker
) -> bool:
    """
    Cria uma notificação agendada para disparar X minutos antes do evento.

    Compatível com o uso antigo (sem destinatario_user_id) e pronto para o scheduler novo.

    - user_id: quem está operando (dono/atendente)
    - destinatario_user_id: (opcional) quem receberá a notificação. Se não informado, notifica o próprio user_id.
    - alvo_evento: (opcional) dict com dados do evento (ex: {"data": "...", "hora_inicio": "...", "profissional": "..."}).
    """
    try:
        # destino real do aviso (cliente ou dono). Se não vier, mantém o comportamento antigo.
        destino = destinatario_user_id or user_id

        # horário do evento e horário da notificação (X minutos antes)
        data_evento = datetime.fromisoformat(f"{data}T{hora_inicio}")
        horario_notificacao = data_evento - timedelta(minutes=minutos_antes)

        notificacao = {
            # esses campos são usados pelo worker/scheduler
            "descricao": descricao,
            "mensagem": None,  # deixa None para o worker montar fallback amigável
            "canal": canal,    # "telegram" | "whatsapp" | etc.
            "data_hora": horario_notificacao.isoformat(),
            "avisado": False,
            "status": "pendente",
            "criado_em": datetime.now().isoformat(),

            # ajuda a compor a mensagem no disparo
            "alvo_evento": alvo_evento or {"data": data, "hora_inicio": hora_inicio},
            "minutos_antes": minutos_antes,

            # metadados úteis para debug/auditoria
            "destinatario": destino,
            "origem_user": user_id,
        }

        id_notificacao = str(uuid.uuid4())
        await salvar_dado_em_path(
            f"Clientes/{destino}/NotificacoesAgendadas/{id_notificacao}",
            notificacao
        )

        # Mantemos o retorno booleano para não quebrar chamadas existentes
        return True

    except Exception as e:
        print(f"❌ Erro ao criar notificação agendada: {e}")
        return False
