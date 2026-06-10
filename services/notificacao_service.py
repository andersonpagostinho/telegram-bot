# services/notificacao_service.py
from datetime import datetime, timedelta
from services.firebase_service_async import salvar_dado_em_path, buscar_subcolecao, buscar_dado_em_path
import uuid
import logging

logger = logging.getLogger(__name__)

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


async def _notificacao_ja_existe(
    tenant_id: str,
    destinatario_user_id: str,
    evento_id: str,
    tipo: str = "lembrete_evento"
) -> bool:
    """
    Verifica se já existe notificação para mesmo evento + destinatario + tipo.
    Evita duplicação.
    """
    try:
        notificacoes = await buscar_subcolecao(f"Clientes/{tenant_id}/NotificacoesAgendadas") or {}
        for notif_id, notif in notificacoes.items():
            if isinstance(notif, dict):
                if (notif.get("evento_id") == evento_id and
                    notif.get("destinatario_user_id") == destinatario_user_id and
                    notif.get("tipo") == tipo and
                    notif.get("avisado") == False):
                    return True
        return False
    except Exception as e:
        logger.warning(f"Erro ao verificar duplicação de notificação: {e}")
        return False


async def criar_notificacoes_evento_cliente_e_profissional(
    tenant_id: str,
    evento_id: str,
    cliente_id: str,
    cliente_nome: str,
    profissional_nome: str,
    profissional_user_id: str | None,
    data: str,
    hora_inicio: str,
    canal_cliente: str = "telegram",
    canal_profissional: str = "telegram",
    minutos_antes: int = 30,
    descricao: str = "lembrete_evento",
) -> dict:
    """
    Cria notificações de lembrete para CLIENTE e PROFISSIONAL.

    Retorna dict com status de cada notificação.
    Exemplo:
    {
        "cliente": {"sucesso": True, "notif_id": "uuid"},
        "profissional": {"sucesso": False, "motivo": "profissional_sem_id"}
    }

    Requisitos:
    - Não duplica se já existe para mesmo evento + destinatario + tipo
    - Se profissional sem ID, apenas loga aviso e continua
    - Mantém path tenant: Clientes/{tenant_id}/NotificacoesAgendadas/{notif_id}
    """
    resultado = {
        "cliente": {"sucesso": False, "notif_id": None},
        "profissional": {"sucesso": False, "motivo": None}
    }

    try:
        data_evento = datetime.fromisoformat(f"{data}T{hora_inicio}")
        horario_notificacao = data_evento - timedelta(minutes=minutos_antes)

        # Dados comuns da notificação
        notificacao_base = {
            "descricao": descricao,
            "mensagem": None,
            "data_hora": horario_notificacao.isoformat(),
            "avisado": False,
            "processada": False,
            "status": "pendente",
            "criado_em": datetime.now().isoformat(),
            "alvo_evento": {
                "data": data,
                "hora_inicio": hora_inicio,
                "cliente_nome": cliente_nome,
                "profissional": profissional_nome,
            },
            "minutos_antes": minutos_antes,
            "tipo": "lembrete_evento",
            "tenant_id": tenant_id,
            "evento_id": evento_id,
        }

        # ================================================================
        # 1. CRIAR NOTIFICAÇÃO PARA CLIENTE
        # ================================================================
        if not await _notificacao_ja_existe(tenant_id, cliente_id, evento_id, "lembrete_evento"):
            try:
                notificacao_cliente = {
                    **notificacao_base,
                    "destinatario_user_id": cliente_id,
                    "papel_destinatario": "cliente",
                    "canal": canal_cliente,
                }

                id_notif_cliente = str(uuid.uuid4())
                await salvar_dado_em_path(
                    f"Clientes/{tenant_id}/NotificacoesAgendadas/{id_notif_cliente}",
                    notificacao_cliente
                )

                resultado["cliente"]["sucesso"] = True
                resultado["cliente"]["notif_id"] = id_notif_cliente
                logger.info(f"✅ Notificação cliente criada: evento={evento_id} cliente={cliente_id}")

            except Exception as e:
                resultado["cliente"]["sucesso"] = False
                resultado["cliente"]["motivo"] = str(e)
                logger.error(f"❌ Erro ao criar notificação cliente: {e}")
        else:
            resultado["cliente"]["sucesso"] = False
            resultado["cliente"]["motivo"] = "duplicada"
            logger.info(f"⏭️ Notificação cliente já existe: evento={evento_id} cliente={cliente_id}")

        # ================================================================
        # 2. CRIAR NOTIFICAÇÃO PARA PROFISSIONAL (se houver ID)
        # ================================================================
        if profissional_user_id:
            if not await _notificacao_ja_existe(tenant_id, profissional_user_id, evento_id, "lembrete_evento"):
                try:
                    notificacao_profissional = {
                        **notificacao_base,
                        "destinatario_user_id": profissional_user_id,
                        "papel_destinatario": "profissional",
                        "canal": canal_profissional,
                    }

                    id_notif_prof = str(uuid.uuid4())
                    await salvar_dado_em_path(
                        f"Clientes/{tenant_id}/NotificacoesAgendadas/{id_notif_prof}",
                        notificacao_profissional
                    )

                    resultado["profissional"]["sucesso"] = True
                    resultado["profissional"]["notif_id"] = id_notif_prof
                    logger.info(f"✅ Notificação profissional criada: evento={evento_id} prof={profissional_nome}")

                except Exception as e:
                    resultado["profissional"]["sucesso"] = False
                    resultado["profissional"]["motivo"] = str(e)
                    logger.error(f"❌ Erro ao criar notificação profissional: {e}")
            else:
                resultado["profissional"]["sucesso"] = False
                resultado["profissional"]["motivo"] = "duplicada"
                logger.info(f"⏭️ Notificação profissional já existe: evento={evento_id} prof={profissional_user_id}")
        else:
            resultado["profissional"]["sucesso"] = False
            resultado["profissional"]["motivo"] = "profissional_sem_id"
            logger.warning(f"⚠️ Profissional sem ID: {profissional_nome} evento={evento_id}")

        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao criar notificações evento/cliente/profissional: {e}")
        return resultado
