import os
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INTENCOES_VALIDAS = [
    "start", "help", "meusdados", "meuestilo", "adicionar_tarefa",
    "listar_tarefas", "listar_prioridade", "limpar_tarefas",
    "adicionar_evento", "listar_eventos", "confirmar_reuniao",
    "confirmar_presenca", "debug_eventos", "conectar_email",
    "authcallback", "ler_emails", "emails_prioritarios", "enviar_email",
    "meu_email", "relatorio_diario", "relatorio_semanal",
    "enviar_relatorio_email", "definir_tipo_negocio", "definir_estilo",
    "definir_nome_negocio", "criar_followup", "concluir_followup",
    "meusfollowups", "configurar_avisos", "organizar_semana"
]

async def identificar_intencao_com_gpt(texto_usuario: str) -> str | None:
    prompt = f"""
Você é um classificador de comandos para uma secretária executiva virtual.

Dado o texto a seguir, identifique a intenção dele com base na lista abaixo. 
Retorne somente o nome da intenção, sem explicações. Se for algo como "organizar semana" ou "me ajuda com meu dia", a intenção é "organizar_semana".

{INTENCOES_VALIDAS}

Texto:
\"\"\"{texto_usuario}\"\"\"
"""
    try:
        resposta = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0
        )

        intencao = resposta.choices[0].message.content.strip().lower()

        if intencao in INTENCOES_VALIDAS:
            # Verificação extra para não classificar frase genérica como tarefa
            if intencao == "adicionar_tarefa" and "tarefa" not in texto_usuario.lower():
                return None

            return intencao
        else:
            print(f"[GPT] Intenção inválida recebida: {intencao}")
            return None

    except Exception as e:
        print("[GPT] Erro ao identificar intenção:", e)
        return None
