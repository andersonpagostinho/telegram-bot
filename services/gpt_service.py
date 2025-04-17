import os
import json
from openai import AsyncOpenAI
from datetime import datetime, timedelta
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ GPT simples para respostas diretas (sem contexto)
async def processar_com_gpt(texto_usuario):
    try:
        resposta = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.4,
            messages=[
                {"role": "system", "content": INSTRUCAO_SECRETARIA},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Erro no GPT:", e)
        return "❌ Houve um erro ao processar com a IA."


# ✅ GPT com contexto e resposta estruturada em JSON (ação + dados)
async def processar_com_gpt_com_acao(texto_usuario, contexto, instrucao):
    prompt = f"""
{instrucao}

--- CONTEXTO DO USUÁRIO ---
📅 Data atual: {datetime.now().strftime('%Y-%m-%d')}
👤 Nome: {contexto['usuario'].get('nome', 'Desconhecido')}
📌 Plano ativo: {contexto['usuario'].get('pagamentoAtivo', False)}
🔐 Módulos: {', '.join(contexto['usuario'].get('planosAtivos', []))}

📋 Tarefas:
{chr(10).join(f"- {t}" for t in contexto['tarefas']) or 'Nenhuma'}

📆 Eventos:
{chr(10).join(f"- {e}" for e in contexto['eventos']) or 'Nenhum'}

📧 E-mails:
{chr(10).join(f"- {e}" for e in contexto['emails']) or 'Nenhum'}

--- PEDIDO DO USUÁRIO ---
🗣️ "{texto_usuario}"

Lembre-se: responda SEMPRE em JSON com os campos 'resposta', 'acao' e 'dados'.
"""

    try:
        resposta = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.5,
            messages=[
                {"role": "system", "content": instrucao},
                {"role": "user", "content": prompt}
            ]
        )

        conteudo = resposta.choices[0].message.content.strip()

        print("📦 [DEBUG GPT] Conteúdo bruto retornado:\n", conteudo)

        try:
            resultado = json.loads(conteudo)

            print("✅ [DEBUG GPT] JSON interpretado com sucesso:", resultado)

            return resultado  # ✅ Aqui: retorna o dict, não use await em quem chama isso
        except json.JSONDecodeError:
            print(f"❌ Erro ao interpretar JSON:\n{conteudo}")
            return {
                "resposta": "❌ A IA respondeu fora do formato esperado.",
                "acao": None,
                "dados": {}
            }

    except Exception as e:
        print(f"❌ Erro ao processar com GPT:", e)
        return {
            "resposta": "❌ Ocorreu um erro ao processar sua solicitação.",
            "acao": None,
            "dados": {}
        }


# ✅ Organização da semana (sem JSON, apenas plano formatado)
async def organizar_semana_com_gpt(tarefas: list, eventos: list, dia_inicio: str = "hoje"):
    try:
        hoje = datetime.now().date()

        dias_formatados = [
            (hoje + timedelta(days=i)).strftime("%A (%d/%m)") for i in range(5)
        ]

        prompt = f"""
Você é uma assistente virtual especializada em produtividade e organização semanal.

Ajude o usuário a planejar os próximos 5 dias, a partir de hoje: *{hoje.strftime("%A (%d/%m)")}.*  
Use os dias reais a seguir:

{chr(10).join(f"- {dia}" for dia in dias_formatados)}

Com base nas tarefas e eventos abaixo, distribua as atividades de forma inteligente e priorize o que é mais importante primeiro.

- Use título com o dia da semana e data. Ex: 📅 Sexta-feira (11/04)
- Organize os itens como: tarefas primeiro, eventos depois.
- Use emojis para dar destaque.
- Seja objetiva e evite texto explicativo.

Tarefas:
{chr(10).join(f"- {t}" for t in tarefas)}

Eventos:
{chr(10).join(f"- {e}" for e in eventos)}

Responda apenas com o plano formatado.
"""

        resposta = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.5,
            messages=[
                {"role": "system", "content": INSTRUCAO_SECRETARIA},
                {"role": "user", "content": prompt}
            ]
        )

        return resposta.choices[0].message.content.strip()

    except Exception as e:
        print(f"[GPT] Erro ao organizar semana: {e}")
        return "❌ Houve um erro ao tentar planejar sua semana."

