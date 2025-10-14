# handlers/reagendamento_handler.py
import re
from telegram import Update
from telegram.ext import ContextTypes

from services.firebase_service_async import buscar_subcolecao
from services.encaixe_service import confirmar_reagendamento_por_opcao

async def _descobrir_dono_por_cliente(cliente_id: str) -> str | None:
    """
    Procura em todos os 'Clientes/*/Eventos' algum evento cujo cliente_id == cliente_id.
    Retorna o user_id do dono (coleção raiz) se achar.
    Obs.: simples e suficiente para bases pequenas; se crescer, indexe isso.
    """
    donos = await buscar_subcolecao("Clientes") or {}
    for dono_id in donos.keys():
        eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}
        for _, ev in eventos.items():
            if isinstance(ev, dict) and ev.get("cliente_id") == cliente_id:
                return dono_id
    return None

def _texto_eh_apenas_opcao(txt: str) -> int | None:
    """
    Reconhece '1', '2', '3' (com tolerância a espaços).
    """
    m = re.fullmatch(r"\s*([1-3])\s*", txt)
    return int(m.group(1)) if m else None

async def handle_resposta_reagendamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Cliente "flex" responde com 1/2/3 — confirmamos o reagendamento dele.
    - Descobrimos o dono (negócio) associado por busca nos eventos.
    - Chamamos confirmar_reagendamento_por_opcao.
    """
    if not update.message or not update.message.text:
        return

    txt = update.message.text.strip()
    opcao = _texto_eh_apenas_opcao(txt)
    if not opcao:
        return  # não é resposta de 1-3; deixe outros handlers seguirem

    cliente_id = str(update.message.from_user.id)
    dono_id = await _descobrir_dono_por_cliente(cliente_id)
    if not dono_id:
        await update.message.reply_text("❌ Não encontrei seu agendamento para mover. Pode tentar novamente mais tarde?")
        return

    out = await confirmar_reagendamento_por_opcao(dono_id, cliente_id, opcao)
    if out.get("status") == "ok":
        await update.message.reply_text(f"✅ {out.get('mensagem')}")
        # Aqui você pode notificar o dono sobre o sucesso do reagendamento, se quiser
        # (ex.: via NotificacoesAgendadas)
    else:
        await update.message.reply_text(f"❌ {out.get('mensagem')}")
