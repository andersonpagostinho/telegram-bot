import speech_recognition as sr

# Inicializa o reconhecedor de áudio
recognizer = sr.Recognizer()

# Caminho do arquivo de áudio (substitua pelo seu arquivo)
audio_path = "teste.wav"  # Use um arquivo WAV curto para testar

# Carregar e processar o áudio
with sr.AudioFile(audio_path) as source:
    print("🎙️ Processando áudio...")
    audio = recognizer.record(source)

# Tentar transcrever o áudio
try:
    text = recognizer.recognize_google(audio, language="pt-BR")
    print(f"✅ Transcrição: {text}")
except sr.UnknownValueError:
    print("❌ Não foi possível entender o áudio.")
except sr.RequestError as e:
    print(f"❌ Erro na requisição ao Google Speech-to-Text: {e}")