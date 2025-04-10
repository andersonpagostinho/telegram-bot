from openai import AsyncOpenAI

client = AsyncOpenAI()  # Ou configure com chave/env personalizada

INTENCOES_VALIDAS = [
    "start", "help", "meusdados", "meuestilo", "adicionar_tarefa",
    "listar_tarefas", "listar_prioridade", "limpar_tarefas",
    "adicionar_evento", "listar_eventos", "confirmar_reuniao",
    "confirmar_presenca", "debug_eventos", "conectar_email",
    "authcallback", "ler_emails", "emails_prioritarios", "enviar_email",
    "meu_email", "relatorio_diario", "relatorio_semanal",
    "enviar_relatorio_email", "definir_tipo_negocio", "definir_estilo",
    "definir_nome_negocio", "criar_followup", "concluir_followup",
    "meusfollowups", "configurar_avisos"
]

async def identificar_intencao_com_gpt(texto_usuario: str) -> str | None:
    prompt = f"""
Você é um classificador de comandos para uma assistente virtual com foco em secretariado executivo.

Dado o texto a seguir, identifique qual das intenções ele representa. 
Responda *somente* com uma das opções abaixo (sem explicações):

{INTENCOES_VALIDAS}

Texto:
\"\"\"{texto_usuario}\"\"\"
"""
    try:
        resposta = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )

        intencao = resposta.choices[0].message.content.strip().lower()

        if intencao in INTENCOES_VALIDAS:
            return intencao
        return None

    except Exception as e:
        print("[GPT] Erro ao identificar intenção:", e)
        return None
