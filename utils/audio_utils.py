# utils/audio_utils.py
import subprocess
import speech_recognition as sr
import logging

logger = logging.getLogger(__name__)

def converter_audio_para_wav(entrada_path, saida_path):
    try:
        comando = [
            "ffmpeg", "-i", entrada_path,
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            saida_path
        ]
        subprocess.run(comando, check=True)
        logger.info(f"✅ Áudio convertido: {saida_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erro ao converter áudio: {e}")
        return False

def transcrever_audio(wav_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
        try:
            texto = recognizer.recognize_google(audio, language="pt-BR")
            logger.info(f"✅ Transcrição: {texto}")
            return texto
        except sr.UnknownValueError:
            logger.warning("🤷‍♂️ Áudio não foi entendido.")
            return None
        except sr.RequestError as e:
            logger.error(f"❌ Erro ao acessar Google Speech-to-Text: {e}")
            return None

