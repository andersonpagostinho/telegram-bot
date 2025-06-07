from datetime import datetime
import math

# 💰 Preços por mil tokens (em dólares)
PRECOS = {
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
}

async def registrar_custo_gpt(resposta, modelo, user_id, firestore_client=None):
    try:
        usage = resposta.usage
        tokens_in = usage.prompt_tokens
        tokens_out = usage.completion_tokens
        preco = PRECOS.get(modelo, {"input": 0.01, "output": 0.03})  # fallback

        custo = round((tokens_in * preco["input"] + tokens_out * preco["output"]) / 1000, 6)

        log = {
            "user_id": user_id,
            "modelo": modelo,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "custo_usd": custo,
            "data": datetime.now().isoformat()
        }

        if firestore_client:
            firestore_client.collection("custos_usuarios").add(log)

        print("📊 Custo registrado:", log)
        return log

    except Exception as e:
        print("❌ Erro ao registrar custo GPT:", e)
        return None
