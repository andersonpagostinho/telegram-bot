# handlers/voice_handler.py
import os
from telegram import Update
from telegram.ext import ContextTypes
from utils.audio_utils import converter_audio_para_wav, transcrever_audio
from handlers.voice_command_handler import processar_comando_voz  # 👈 IMPORTA AQUI

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ogg_path = "temp_audio.ogg"
    wav_path = "temp_audio.wav"

    try:
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(ogg_path)

        if not converter_audio_para_wav(ogg_path, wav_path):
            await update.message.reply_text("❌ Erro ao converter o áudio.")
            return

        texto = transcrever_audio(wav_path)
        if not texto:
            await update.message.reply_text("❌ Não entendi o áudio. Pode repetir?")
            return

        await update.message.reply_text(f"🎤 Você disse: {texto}")

        # ✅ Agora executa o comando de verdade
        await processar_comando_voz(update, context, texto)

    except Exception as e:
        await update.message.reply_text(f"❌ Ocorreu um erro ao processar o áudio:\n{e}")
    finally:
        # Limpa arquivos temporários
        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)