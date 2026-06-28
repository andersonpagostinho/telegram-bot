"""
SEG-05B — MEC-03: Override Manual por Contato

Responsável por:
- Processar comandos /pausar e /retomar
- Validar autorização (whitelist A-01 a A-06)
- Bloquear desconhecidos
- Persistir em Firestore via governanca_service

NÃO faz:
- Decidir resposta (apenas persiste governança)
- Bloquear mensagens (feito em bot.py antes do GPT)
- Alterar agenda, conflito, sugestão, criação ou histórico
"""

from typing import Tuple, Dict, Any
from services.governanca_service import salvar_governanca, carregar_governanca
from services.whitelist_service import classificar_com_whitelist
from services.firestore_client import get_db


WHITELIST_AUTORIZ = {"A-01", "A-02", "A-03", "A-04", "A-05", "A-06"}


async def processar_comando_pausar(
    actor_id: str,
    tenant_id: str,
    user_id: str = None
) -> Tuple[bool, str]:
    """
    Processa comando /pausar (desativa respostas automáticas).

    Args:
        actor_id: ID do ator executando comando (user_id)
        tenant_id: ID do tenant (dono_id para isolamento)
        user_id: Mesmo que actor_id (compatibilidade)

    Returns:
        (sucesso: bool, mensagem: str)
        - (True, "✅ NeoEve pausada...") se autorizado
        - (False, "❌ Você não...") se bloqueado
    """
    actor_id = actor_id or user_id
    tenant_id = tenant_id or actor_id

    if not actor_id or not tenant_id:
        return False, "❌ Erro: actor_id ou tenant_id ausente"

    try:
        # 1️⃣ Validar que o contato está cadastrado (não desconhecido)
        db = get_db()
        contato_doc = db.collection("Clientes").document(tenant_id).collection("Contatos").document(actor_id).get()

        if not contato_doc.exists:
            return False, "❌ Você não está cadastrado neste sistema."

        # 2️⃣ Validar autorização (whitelist A-01 a A-06)
        # Classificar o comando /pausar na whitelist
        esta_na_whitelist, categoria, nome_categoria = classificar_com_whitelist("/pausar", actor_id)

        if not esta_na_whitelist or categoria not in WHITELIST_AUTORIZ:
            # /pausar não está em categoria autorizada
            return False, (
                "❌ Você não está autorizado para pausar respostas automáticas.\n\n"
                "Apenas contatos administrativos (categorias A-01 a A-06) podem usar este comando."
            )

        # 3️⃣ Salvar governança com responder_automaticamente=False
        await salvar_governanca(
            actor_id=actor_id,
            tenant_id=tenant_id,
            responder_automaticamente=False,
            motivo="/pausar",
            executor_id=actor_id
        )

        return True, (
            "⏸️ *NeoEve pausada para você.*\n\n"
            "Suas mensagens não receberão respostas automáticas.\n"
            "Use `/retomar` para voltar ao atendimento normal."
        )

    except Exception as e:
        print(f"[ERRO] processar_comando_pausar: {str(e)}", flush=True)
        return False, f"❌ Erro ao processar comando: {str(e)[:100]}"


async def processar_comando_retomar(
    actor_id: str,
    tenant_id: str,
    user_id: str = None
) -> Tuple[bool, str]:
    """
    Processa comando /retomar (reativa respostas automáticas).

    Args:
        actor_id: ID do ator executando comando (user_id)
        tenant_id: ID do tenant (dono_id para isolamento)
        user_id: Mesmo que actor_id (compatibilidade)

    Returns:
        (sucesso: bool, mensagem: str)
        - (True, "✅ NeoEve retomada...") se autorizado
        - (False, "❌ Você não...") se bloqueado
    """
    actor_id = actor_id or user_id
    tenant_id = tenant_id or actor_id

    if not actor_id or not tenant_id:
        return False, "❌ Erro: actor_id ou tenant_id ausente"

    try:
        # 1️⃣ Validar que o contato está cadastrado (não desconhecido)
        db = get_db()
        contato_doc = db.collection("Clientes").document(tenant_id).collection("Contatos").document(actor_id).get()

        if not contato_doc.exists:
            return False, "❌ Você não está cadastrado neste sistema."

        # 2️⃣ Validar autorização (whitelist A-01 a A-06)
        # Classificar o comando /retomar na whitelist
        esta_na_whitelist, categoria, nome_categoria = classificar_com_whitelist("/retomar", actor_id)

        if not esta_na_whitelist or categoria not in WHITELIST_AUTORIZ:
            # /retomar não está em categoria autorizada
            return False, (
                "❌ Você não está autorizado para retomar respostas automáticas.\n\n"
                "Apenas contatos administrativos (categorias A-01 a A-06) podem usar este comando."
            )

        # 3️⃣ Salvar governança com responder_automaticamente=True
        await salvar_governanca(
            actor_id=actor_id,
            tenant_id=tenant_id,
            responder_automaticamente=True,
            motivo="/retomar",
            executor_id=actor_id
        )

        return True, (
            "▶️ *NeoEve retomada para você.*\n\n"
            "Suas mensagens voltarão a receber respostas automáticas.\n"
            "Estou aqui para ajudar! 🚀"
        )

    except Exception as e:
        print(f"[ERRO] processar_comando_retomar: {str(e)}", flush=True)
        return False, f"❌ Erro ao processar comando: {str(e)[:100]}"
