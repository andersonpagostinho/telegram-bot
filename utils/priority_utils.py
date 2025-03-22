import os
import json
import logging
from datetime import datetime, timezone
from services.firebase_service import db

logger = logging.getLogger(__name__)

# 🔸 Palavras-chave padrão
PALAVRAS_CHAVE = {
    "alta": ["urgente", "pagar", "vencimento", "prazo", "importante", "multa", "conta", "reunião"],
    "media": ["enviar", "revisar", "responder", "agendar"],
    "baixa": ["newsletter", "promoção", "marketing", "atualizações", "lembrar", "verificar", "pensar", "considerar"]
}

# 🔸 Remetentes padrão considerados importantes (via env)
REMETENTES_PRIORITARIOS = json.loads(os.getenv("REMETENTES_PRIORITARIOS", "[]"))

# 🔸 Horário comercial usado para ajustar prioridade
HORARIO_COMERCIAL = (9, 18)


def obter_config_prioridade_usuario(user_id: str):
    """Busca regras personalizadas de prioridade do usuário."""
    try:
        doc_ref = db.collection("UserPrioritySettings").document(str(user_id))
        doc = doc_ref.get()
        return doc.to_dict() or {"remetentes": {}, "palavras": {}}
    except Exception as e:
        logger.error(f"❌ Erro ao buscar configurações de prioridade do usuário {user_id}: {e}")
        return {"remetentes": {}, "palavras": {}}


def classificar_prioridade_email(email_data: dict, user_id: str = "") -> str:
    """
    Classifica um e-mail por prioridade com base em:
    - Regras personalizadas do usuário
    - Palavras-chave
    - Horário de recebimento
    """
    try:
        remetente = email_data.get('de', '').lower()
        assunto = email_data.get('assunto', '').lower()
        corpo = email_data.get('corpo', '').lower()

        # 🔹 Configuração personalizada do usuário
        user_config = obter_config_prioridade_usuario(user_id)

        # 🔸 Verifica remetente personalizado
        for r, p in user_config.get("remetentes", {}).items():
            if r in remetente:
                return p

        # 🔸 Verifica palavras-chave personalizadas
        for palavra, p in user_config.get("palavras", {}).items():
            if palavra in assunto or palavra in corpo:
                return p

        # 🔸 Verifica palavras-chave padrão
        for prioridade, palavras in PALAVRAS_CHAVE.items():
            if any(p in assunto or p in corpo for p in palavras):
                return prioridade

        # 🔸 Verifica se é de remetente prioritário global
        if any(rem in remetente for rem in REMETENTES_PRIORITARIOS):
            return "alta"

        # 🔸 Ajusta para "média" se fora do horário comercial
        hora_atual = datetime.now(timezone.utc).hour
        if not (HORARIO_COMERCIAL[0] <= hora_atual < HORARIO_COMERCIAL[1]):
            return "media"

        return "baixa"

    except Exception as e:
        logger.error(f"❌ Erro ao classificar prioridade do e-mail: {e}")
        return "baixa"


def detectar_prioridade_tarefa(descricao: str, user_id: str = "") -> str:
    """
    Detecta a prioridade de uma tarefa com base na descrição e regras do usuário.
    """
    try:
        descricao_lower = descricao.lower()
        user_config = obter_config_prioridade_usuario(user_id)

        for palavra, prioridade in user_config.get("palavras", {}).items():
            if palavra in descricao_lower:
                return prioridade

        for prioridade, palavras in PALAVRAS_CHAVE.items():
            if any(p in descricao_lower for p in palavras):
                return prioridade

        return "baixa"
    except Exception as e:
        logger.error(f"❌ Erro ao detectar prioridade da tarefa: {e}")
        return "baixa"
