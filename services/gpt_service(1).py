import os
import json
import re
from openai import AsyncOpenAI
from datetime import datetime, timedelta
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario
import re
import unidecode

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
    user_id = str(contexto.get('usuario', {}).get('user_id', 'desconhecido'))
    contexto_salvo = await carregar_contexto_temporario(user_id)

    if contexto_salvo is None:
        contexto_salvo = {}  # 🔧 Corrige o problema ao garantir que seja um dicionário vazio

    profissionais = contexto.get("profissionais", [])
    nomes_profissionais = [p["nome"].lower() for p in profissionais]
    resposta_direta = texto_usuario.strip().lower()

    # ⏰ Novo trecho: captura horário direto se já tem profissional e serviço
    hora_encontrada = re.search(r'\b(\d{1,2})(?:[:h](\d{2}))?\b', resposta_direta)
    if hora_encontrada:
        hora = int(hora_encontrada.group(1))
        minuto = int(hora_encontrada.group(2) or 0)

        profissional = contexto_salvo.get("profissional_escolhido")
        servico = contexto_salvo.get("servico")
        data_hora_antiga = contexto_salvo.get("data_hora")

        if profissional and servico:
            if data_hora_antiga:
                data_original = datetime.fromisoformat(data_hora_antiga)
            else:
                data_original = datetime.now()

            nova_data_hora = data_original.replace(hour=hora, minute=minuto, second=0, microsecond=0).isoformat()
            duracao = estimar_duracao(servico)

            await salvar_contexto_temporario(user_id, {
                "profissional_escolhido": profissional,
                "servico": servico,
                "data_hora": nova_data_hora
            })

            return {
                "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(nova_data_hora)}. ✂️",
                "acao": "criar_evento",
                "dados": {
                    "data_hora": nova_data_hora,
                    "descricao": f"{servico} com {profissional}",
                    "duracao": duracao
                }
            }

    # Verifica se a resposta menciona diretamente um profissional

    texto_normalizado = unidecode.unidecode(resposta_direta.lower())

    for prof in nomes_profissionais:
        prof_normalizado = unidecode.unidecode(prof.lower())
        padrao = rf"\b{prof_normalizado}\b"  # Garante que a palavra esteja isolada, ex: 'gloria' e não 'gloriamaria'

        if re.search(padrao, texto_normalizado):
            opcoes_disponiveis = contexto_salvo.get("ultima_opcao_profissionais", [])
            servico = contexto_salvo.get("servico")
            data_hora = contexto_salvo.get("data_hora")

            print(f"🔍 Verificação de dados: profissional={prof.capitalize()}, servico={servico}, data_hora={data_hora}, opções={opcoes_disponiveis}")

            if prof.capitalize() in opcoes_disponiveis and servico and data_hora:
                duracao = estimar_duracao(servico)
                await salvar_contexto_temporario(user_id, {
                    "profissional_escolhido": prof.capitalize(),
                    "servico": servico,
                    "data_hora": data_hora
                })
                return {
                    "resposta": f"{servico.capitalize()} agendado com {prof.capitalize()} para {formatar_data(data_hora)}. ✂️",
                    "acao": "criar_evento",
                    "dados": {
                        "data_hora": data_hora,
                        "descricao": f"{servico} com {prof.capitalize()}",
                        "duracao": estimar_duracao(servico)
                    }
                }
            else:
                await salvar_contexto_temporario(user_id, {"profissional_escolhido": prof.capitalize()})
                contexto_salvo = await carregar_contexto_temporario(user_id)

                # 🔄 VERIFICAR se pode agendar agora
                profissional = contexto_salvo.get("profissional_escolhido")
                servico = contexto_salvo.get("servico")
                data_hora = contexto_salvo.get("data_hora")

                if profissional and servico and data_hora:
                    duracao = estimar_duracao(servico)
                    return {
                        "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                        "acao": "criar_evento",
                        "dados": {
                            "data_hora": data_hora,
                            "descricao": f"{servico} com {profissional}",
                            "duracao": duracao
                        }
                    }

    # Gera prompt com contexto se ainda não for possível agendar
    contexto_salvo = await carregar_contexto_temporario(user_id)
    prompt = f"""
{instrucao}

--- CONTEXTO DO USUÁRIO ---
📅 Data atual: {datetime.now().strftime('%Y-%m-%d')}
👤 Nome: {contexto['usuario'].get('nome', 'Desconhecido')}
📌 Plano ativo: {contexto['usuario'].get('pagamentoAtivo', False)}
🔐 Módulos: {', '.join(contexto['usuario'].get('planosAtivos', []))}
🏢 Tipo de negócio: {contexto['usuario'].get('tipo_negocio', contexto['usuario'].get('tipoNegocio', 'não informado'))}

📋 Tarefas:
{chr(10).join(f"- {t}" for t in contexto['tarefas']) or 'Nenhuma'}

📆 Eventos:
{chr(10).join(f"- {e}" for e in contexto['eventos']) or 'Nenhum'}

📧 E-mails:
{chr(10).join(f"- {e}" for e in contexto['emails']) or 'Nenhum'}

--- CONTEXTO TEMPORÁRIO ---
{json.dumps(contexto_salvo or {}, ensure_ascii=False, indent=2)}

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

        resultado = json.loads(conteudo)
        memoria_nova = {}

        if "profissional" in resultado.get("dados", {}):
            memoria_nova["profissional_escolhido"] = resultado["dados"]["profissional"]

        if "descricao" in resultado.get("dados", {}):
            memoria_nova["servico"] = resultado["dados"]["descricao"]

        if "data_hora" in resultado.get("dados", {}):
            memoria_nova["data_hora"] = resultado["dados"]["data_hora"]

        if "resposta" in resultado:
            nomes_validos = [p["nome"] for p in contexto.get("profissionais", [])]
            nomes_mencionados = [nome for nome in nomes_validos if nome.lower() in resultado["resposta"].lower()]

            if len(nomes_mencionados) >= 1:
                memoria_nova["ultima_opcao_profissionais"] = nomes_mencionados
                memoria_nova["profissional_escolhido"] = nomes_mencionados[0]
 
        # 🟡 Salve também o serviço e a data_hora se existirem, mesmo que estejam fora de 'dados'
        if "descricao" in resultado.get("dados", {}):
            memoria_nova["servico"] = resultado["dados"]["descricao"]

        if "data_hora" in resultado.get("dados", {}):
            memoria_nova["data_hora"] = resultado["dados"]["data_hora"]


        # ✅ Antes de salvar, verifique se já dá para agendar
        profissional = memoria_nova.get("profissional_escolhido")
        servico = memoria_nova.get("servico")
        data_hora = memoria_nova.get("data_hora")

        if profissional and servico and data_hora:
            duracao = estimar_duracao(servico)
            return {
                "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                "acao": "criar_evento",
                "dados": {
                    "data_hora": data_hora,
                    "descricao": f"{servico} com {profissional}",
                    "duracao": duracao
                }
            }

        # ✅ Salvar tudo junto
        if memoria_nova:
            print(f"💾 Salvando memória: {memoria_nova}")  # 🔍 Debug opcional
            await salvar_contexto_temporario(user_id, memoria_nova)

        return resultado

    except json.JSONDecodeError:
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

# 👇 Funções auxiliares
def estimar_duracao(servico):
    mapa = {
        "corte": 30,
        "escova": 40,
        "coloração": 90
    }
    return mapa.get(servico.lower(), 60)

def formatar_data(data_iso):
    try:
        dt = datetime.fromisoformat(data_iso)
        return dt.strftime("dia %d/%m às %H:%Mh")
    except:
        return data_iso

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
