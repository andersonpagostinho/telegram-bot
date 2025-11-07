# handlers/encaixe_handler.py
import re
import dateparser
from datetime import timedelta
from pytz import timezone
from telegram import Update
from telegram.ext import ContextTypes

from services.encaixe_service import solicitar_encaixe
from services.firebase_service_async import obter_id_dono  # 👈 adiciona

FUSO_BR = timezone("America/Sao_Paulo")

def _extrair_profissional(txt: str) -> str | None:
    m = re.search(r"\bcom\s+(a|o)?\s*([A-Za-zÀ-ÿ][\wÀ-ÿ]+)", txt, flags=re.IGNORECASE)
    if m:
        return m.group(2).strip().capitalize()
    m2 = re.search(r"\b([A-Za-zÀ-ÿ][\wÀ-ÿ]+)$", txt.strip())
    return m2.group(1).capitalize() if m2 else None

def _extrair_duracao(txt: str, padrao_min: int = 30) -> int:
    m = re.search(r"(\d{1,3})\s*(min|minuto|minutos)", txt, flags=re.IGNORECASE)
    if m:
        return max(10, min(240, int(m.group(1))))
    return padrao_min

def _extrair_datahora(txt: str):
    dt = dateparser.parse(
        txt,
        languages=["pt"],
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "America/Sao_Paulo",
            "RETURN_AS_TIMEZONE_AWARE": False
        },
    )
    return FUSO_BR.localize(dt) if dt else None

async def handle_pedido_encaixe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Detecta intenção de 'encaixe' e tenta executar.
    Ex.: "tem encaixe hoje às 16:00 com a Carla? 30min"
    """
    if not update.message or not update.message.text:
        return

    texto = update.message.text.lower()

    if not any(k in texto for k in ["encaixe", "encaixa", "en-caixe", "tem agenda hoje", "cabem hoje", "urgência"]):
        return

    user_id = str(update.message.from_user.id)  # quem pediu
    dono_id = await obter_id_dono(user_id)      # 👈 agora resolve o dono de verdade

    dt_desejado = _extrair_datahora(texto)
    if not dt_desejado:
        await update.message.reply_text(
            "❌ Não entendi a data/hora do encaixe. Pode dizer, por exemplo: *hoje às 16:00*?",
            parse_mode="Markdown"
        )
        return

    prof = _extrair_profissional(texto)
    dur = _extrair_duracao(texto, padrao_min=30)

    agora = FUSO_BR.localize(dateparser.parse("agora"))
    if dt_desejado < agora:
        dt_desejado = agora + timedelta(minutes=10)

    await update.message.reply_text("🔎 Vou checar e tentar encaixar…")

    resp = await solicitar_encaixe(
        user_id=dono_id,                 # 👈 encaixe sempre no negócio
        descricao="Encaixe solicitado",
        profissional=prof,
        duracao_min=dur,
        dt_desejado=dt_desejado,
        solicitante_user_id=user_id      # 👈 quem pediu continua sendo o cliente
    )

    status = resp.get("status")
    msg = resp.get("mensagem", "")

    if status == "encaixe_confirmado":
        ev = resp.get("evento", {})
        quando = f"{ev.get('data')} às {ev.get('hora_inicio')}"
        prof_txt = f" com {ev.get('profissional')}" if ev.get("profissional") else ""
        await update.message.reply_text(f"✅ Encaixe confirmado{prof_txt}: *{quando}*.", parse_mode="Markdown")
    elif status == "aguardando_respostas":
        await update.message.reply_text("📨 Enviei pedido(s) de reagendamento para clientes com perfil flexível. Te aviso ao receber resposta.")
    else:
        await update.message.reply_text(f"❌ Não consegui encaixar agora. {msg}")
