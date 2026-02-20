from pydub import AudioSegment

# Converter M4A para WAV
audio = AudioSegment.from_file("arquivo.m4a", format="m4a")
audio = audio.set_channels(1).set_frame_rate(16000)  # Mono e 16kHz
audio.export("teste.wav", format="wav")

print("✅ Conversão concluída: teste.wav")