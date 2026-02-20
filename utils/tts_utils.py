# utils/tts_utils.py

from gtts import gTTS
import os
from telegram import Update
from telegram.ext import ContextTypes
import uuid

# ✅ Converte texto em áudio e envia como resposta de voz
async def responder_em_audio(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    try:
        user_id = str(update.message.from_user.id)
        nome_arquivo = f"voz_{user_id}_{uuid.uuid4().hex}.mp3"

        # 🔊 Converte texto para áudio usando gTTS
        tts = gTTS(text=texto, lang="pt-br")
        tts.save(nome_arquivo)

        # 📤 Envia áudio como mensagem de voz (audio comum também funciona)
        with open(nome_arquivo, "rb") as audio:
            await update.message.reply_voice(voice=audio)

        # 🧹 Limpa o arquivo temporário
        os.remove(nome_arquivo)

    except Exception as e:
        await update.message.reply_text("❌ Erro ao gerar o áudio da resposta.")
        print(f"Erro em responder_em_audio: {e}")
