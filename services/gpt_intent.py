#gpt intent
from services.gpt_client import client

CLASSIFICADOR_INTENCAO = (
    "Você é uma IA que detecta a intenção de comandos de agendamento. "
    "Responda apenas com uma das palavras: AGENDAR, CONSULTAR, CANCELAR ou DESCONHECIDO."
)


async def classificar_intencao_usuario(texto: str) -> str:
    """Classifica a intenção da frase informada usando o modelo GPT."""
    prompt = (
        "Analise a intenção do usuário com base na frase abaixo.\n"
        "Responda apenas com uma palavra entre: AGENDAR, CONSULTAR, CANCELAR, DESCONHECIDO.\n\n"
        f"Frase: \"{texto}\"\nIntenção:"
    )
    resposta = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        messages=[
            {"role": "system", "content": CLASSIFICADOR_INTENCAO},
            {"role": "user", "content": prompt},
        ],
    )
    return resposta.choices[0].message.content.strip().upper()