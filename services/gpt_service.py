import os
import json
import re
from openai import AsyncOpenAI
from datetime import datetime, timedelta
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario
from utils.custos_gpt import registrar_custo_gpt
from firebase_admin import firestore
from utils.interpretador_datas import interpretar_data_e_hora
import unidecode

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ GPT simples para respostas diretas (sem contexto)
async def processar_com_gpt(texto_usuario, user_id="desconhecido"):
    try:
        resposta = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            messages=[
                {"role": "system", "content": INSTRUCAO_SECRETARIA},
                {"role": "user", "content": texto_usuario}
            ]
        )
        # 🔍 Registrar custo da chamada
        firestore_client = firestore.client()
        await registrar_custo_gpt(resposta, "gpt-4o", user_id, firestore_client)

        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Erro no GPT:", e)
        return "❌ Houve um erro ao processar com a IA."

# ✅ GPT com contexto e resposta estruturada em JSON (ação + dados)
async def processar_com_gpt_com_acao(texto_usuario, contexto, instrucao):
    user_id = str(contexto.get('usuario', {}).get('user_id', 'desconhecido'))
    contexto_salvo = await carregar_contexto_temporario(user_id)

    # 🔍 Detecta e salva data/hora direto do texto (ex: "corte amanhã às 10")
    from utils.interpretador_datas import interpretar_data_e_hora

    data_hora_detectada = interpretar_data_e_hora(texto_usuario)
    if data_hora_detectada:
        data_hora_iso = data_hora_detectada.replace(second=0, microsecond=0).isoformat()
        await salvar_contexto_temporario(user_id, {"data_hora": data_hora_iso})
        contexto_salvo = await carregar_contexto_temporario(user_id)  # 🔄 Atualiza com nova info

    # ⚡ Reconhecer respostas curtas de confirmação
    resposta_direta = texto_usuario.strip().lower()
    palavras_confirmacao = [
        "confirmar", "pode ser", "pode marcar", "fechar",
        "tá bom", "tudo certo", "ok", "isso", "agendar", "sim", "beleza", "claro"
    ]
    resposta_curta = (
        any(p in resposta_direta for p in palavras_confirmacao)
        and len(resposta_direta.split()) <= 4  # ✅ Evita pegar frases longas
    )

    if resposta_curta and contexto_salvo:
        from services.gpt_service import executar_confirmacao_generica

        # ✅ Verifica se a última mensagem do BOT foi uma sugestão ou pergunta
        historico = contexto_salvo.get("historico", [])
        if historico:
            ultima_interacao = historico[-1]
            ultima_mensagem_bot = ultima_interacao.get("bot", "").lower()

            if any(p in ultima_mensagem_bot for p in [
                "deseja", "prefere", "posso", "quer que", "confirmar", "gostaria", "agendar", "?"
            ]):
                return await executar_confirmacao_generica(user_id, contexto_salvo)

        # ⛔️ Se não houver sugestão recente, ignora confirmação genérica
        return {
            "resposta": "Preciso de mais detalhes para confirmar. Poderia especificar melhor?",
            "acao": None,
            "dados": {}
        }

    if contexto_salvo is None:
        contexto_salvo = {}  # 🔧 Garante que temos ao menos um dicionário vazio

    profissionais = contexto.get("profissionais", [])
    # ✅ Garante que o contexto existe como dicionário
    contexto = contexto or {}

    # 🔧 Carrega todos os profissionais do Firebase
    profissionais = contexto.get("profissionais", [])

    # 🔍 Detecta se o usuário quer ver a lista completa
    texto_normalizado = unidecode.unidecode(texto_usuario.lower())
    intencao_listagem_ampla = any(p in texto_normalizado for p in [
        "todos os profissionais", "quem trabalha", "quantas profissionais",
        "quais são as profissionais", "todas as profissionais", "todo mundo que trabalha"
    ])

    # 🔎 Detecta serviço mencionado com base nos serviços disponíveis
    servicos_disponiveis = [s.lower() for p in profissionais for s in p.get("servicos", [])]
    servico_mencionado = None
    for s in servicos_disponiveis:
        if re.search(rf"\b{s.lower()}\b", texto_normalizado):
            servico_mencionado = s.lower()
            break

    # 🧠 Decide se filtra ou mantém todos
    if servico_mencionado and not intencao_listagem_ampla:
        profissionais_filtrados = [
            p for p in profissionais
            if servico_mencionado in [s.lower() for s in p.get("servicos", [])]
        ]
    else:
        profissionais_filtrados = profissionais  # Usa todos

    # 💾 Atualiza o contexto que será enviado ao GPT
    contexto["profissionais"] = profissionais_filtrados

    # 🧠 Salva também o serviço mencionado (se houver) para uso posterior
    if servico_mencionado:
        await salvar_contexto_temporario(user_id, {"servico": servico_mencionado})

    nomes_profissionais = [p["nome"].lower() for p in profissionais_filtrados]
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
                    "descricao": formatar_descricao_evento(servico, profissional),
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

                # ⚠️ Verifica se já foi criado recentemente para não duplicar
                if contexto_salvo.get("evento_criado"):
                    return {
                        "resposta": "✅ O agendamento já foi registrado anteriormente.",
                        "acao": None,
                        "dados": {}
                    }

                # 🔄 VERIFICAR se pode agendar agora
                profissional = contexto_salvo.get("profissional_escolhido")
                servico = contexto_salvo.get("servico")
                data_hora = contexto_salvo.get("data_hora")

                if profissional and servico and data_hora:
                    duracao = estimar_duracao(servico)

                    await salvar_contexto_temporario(user_id, {"evento_criado": True})  # 🚫 Marcar como já criado

                    return {
                        "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                        "acao": "criar_evento",
                        "dados": {
                            "data_hora": data_hora,
                            "descricao": formatar_descricao_evento(servico, profissional),
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
        firestore_client = firestore.client()
        await registrar_custo_gpt(resposta, "gpt-3.5-turbo", user_id, firestore_client)
        conteudo = resposta.choices[0].message.content.strip()


        resultado = json.loads(conteudo)

        # 🛡️ Protege contra acionamento incorreto de "consultar_preco_servico"
        texto_normalizado = unidecode.unidecode(texto_usuario.lower())
        menciona_preco = any(p in texto_normalizado for p in ["preco", "preço", "valor", "quanto", "custa"])

        # ⚠️ Corrige interpretação automática mal feita
        if resultado.get("acao") == "consultar_preco_servico" and not menciona_preco:
            resultado["acao"] = None
            resultado["dados"] = {}

        # ✅ Se não veio ação mas mencionou um serviço e a intenção foi clara de preço, força como consulta
        elif resultado.get("acao") is None and servico_mencionado and menciona_preco:
            resultado["acao"] = "consultar_preco_servico"
            resultado["dados"] = {"servico": servico_mencionado}

        memoria_nova = {}

        # 🧩 Correção automática se o GPT ignorar profissionais do contexto
        intencao_listagem_ampla = any(p in texto_usuario.lower() for p in [
            "todos os profissionais", "quem trabalha", "quantas profissionais",
            "quais são as profissionais", "todas as profissionais", "todo mundo que trabalha"
        ])

        if (
            intencao_listagem_ampla and contexto.get("profissionais")
        ):
            profissionais_formatados = [
                f"- {p['nome']}: {', '.join(p['servicos'])}" for p in contexto["profissionais"]
            ]
            resultado["resposta"] = "Aqui estão as profissionais cadastradas:\n" + "\n".join(profissionais_formatados)
            resultado["acao"] = None
            resultado["dados"] = {}

        if "profissional" in resultado.get("dados", {}):
            memoria_nova["profissional_escolhido"] = resultado["dados"]["profissional"]

        if "data_hora" in resultado.get("dados", {}):
            memoria_nova["data_hora"] = resultado["dados"]["data_hora"]

        # Verificar se a resposta contém algum nome de profissional
        nomes_validos = [p["nome"] for p in contexto.get("profissionais", [])]
        nomes_mencionados = []
        if "resposta" in resultado:
            nomes_mencionados = [nome for nome in nomes_validos if nome.lower() in resultado["resposta"].lower()]

        # Detectar intenção de listagem ampla (não salvar profissional nesse caso)
        intencao_listagem_ampla = any(p in texto_usuario.lower() for p in [
            "todos os profissionais", "quem trabalha", "quantas profissionais",
            "quais são as profissionais", "todas as profissionais", "todo mundo que trabalha"
        ])

        # Salvar profissional escolhido se:
        # 1. Só um nome foi mencionado E
        # 2. Não é uma listagem ampla
        # OU
        # 3. O nome mencionado estava na última listagem (continuidade de atendimento)
        if (
            len(nomes_mencionados) == 1 and not intencao_listagem_ampla
        ) or (
            len(nomes_mencionados) == 1
            and "ultima_opcao_profissionais" in contexto
            and nomes_mencionados[0] in contexto["ultima_opcao_profissionais"]
        ):
            memoria_nova["ultima_opcao_profissionais"] = [nomes_mencionados[0]]
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
            start_dt = datetime.fromisoformat(data_hora)
            data = start_dt.strftime("%Y-%m-%d")
            hora = start_dt.strftime("%H:%M")

            from services.event_service_async import verificar_conflito_e_sugestoes_profissional
            conflito_info = await verificar_conflito_e_sugestoes_profissional(
                user_id=user_id,
                data=data,
                hora_inicio=hora,
                duracao_min=duracao,
                profissional=profissional,
                servico=servico
            )

            if conflito_info["conflito"]:
                sugestoes_txt = "\n".join([f"🔄 {h}" for h in conflito_info["sugestoes"]]) if conflito_info["sugestoes"] else ""
                alternativa_txt = f"\n💡 Porém, {conflito_info['profissional_alternativo']} está disponível nesse mesmo horário." if conflito_info["profissional_alternativo"] else ""

                await salvar_contexto_temporario(user_id, {
                    "profissional_escolhido": profissional,
                    "servico": servico,
                    "data_hora": data_hora,
                    "sugestoes": conflito_info["sugestoes"],
                    "alternativa_profissional": conflito_info["profissional_alternativo"]
                })

                sugestao_formatada = f"\n{sugestoes_txt}" if sugestoes_txt else ""
                alternativa_formatada = alternativa_txt

                resultado = {
                    "resposta": (
                        f"⚠️ {profissional} está ocupado nesse horário."
                        f"{sugestao_formatada}"
                        f"{alternativa_formatada}"
                        f"\n\nDeseja escolher outro horário ou prefere agendar com {conflito_info['profissional_alternativo']}?"
                    ),
                    "acao": None,
                    "dados": {}
                }
            else:
                resultado["acao"] = "criar_evento"
                resultado["dados"] = {
                    "data_hora": data_hora,
                    "descricao": formatar_descricao_evento(servico, profissional),
                    "duracao": duracao
                }

        # ✅ Salvar tudo junto
        if memoria_nova:
            await salvar_contexto_temporario(user_id, memoria_nova)

        # 🔧 Adiciona sugestão de profissionais compatíveis com o serviço, se for o caso
        if (
            servico_mencionado
            and resultado.get("acao") != "criar_evento"
            and not resultado.get("resposta", "").lower().startswith("aqui estão as profissionais")
        ):
            profissionais_compativeis = []
            for p in contexto["profissionais"]:
                servicos = [s.lower() for s in p.get("servicos", []) if isinstance(s, str)]
                if servico_mencionado in servicos:
                    profissionais_compativeis.append(p["nome"])

            if profissionais_compativeis:
                profissionais_compativeis = list(set(profissionais_compativeis))  # ✅ remove duplicados
                nomes_formatados = ", ".join(profissionais_compativeis)
                resposta_atual = resultado.get("resposta", "").lower()

                # ✅ Se os nomes já estão todos mencionados, não adiciona nada
                nomes_ja_mencionados = all(nome.lower() in resposta_atual for nome in profissionais_compativeis)

                if not nomes_ja_mencionados:
                    resposta_base = resultado.get("resposta", "").strip()

                    # Remove frase final padrão do GPT se houver
                    if "deseja ser atendido por" in resposta_base.lower():
                        resposta_base = re.sub(r"deseja ser atendido por.*$", "", resposta_base, flags=re.IGNORECASE).strip()

                    nova_resposta = f"{resposta_base} Deseja ser atendido por {nomes_formatados}?"
                    resultado["resposta"] = nova_resposta

        if resultado.get("acao") and resultado.get("dados"):
            await salvar_contexto_temporario(user_id, {
                "ultima_acao": resultado["acao"],
                "dados_anteriores": resultado["dados"],
                "ultima_intencao": resultado.get("acao")  # 👈 mesma ação por padrão
            })

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

def formatar_descricao_evento(servico: str, profissional: str) -> str:
    """
    Remove duplicações do nome da profissional no serviço, se já estiver embutido,
    e garante capitalização adequada.
    """
    # retira "com Profissional" repetido dentro de servico
    servico_limpo = re.sub(
        rf"\bcom\s+{re.escape(profissional)}\b",
        "",
        servico,
        flags=re.IGNORECASE
    ).strip()
    # capitaliza a primeira letra e adiciona o "com Profissional"
    return f"{servico_limpo.capitalize()} com {profissional}"

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

def limpar_nome_duplicado(resposta, nomes):
    for nome in nomes:
        padrao = rf"(\b{re.escape(nome)}\b[,\s]*)+"
        resposta = re.sub(padrao, f"{nome}, ", resposta, flags=re.IGNORECASE)
    # Remove vírgulas duplicadas e espaços extras
    return re.sub(r',\s*,', ',', resposta).strip(", ").strip()

async def executar_confirmacao_generica(user_id, contexto_salvo):
    """
    Reutiliza a última intenção e dados anteriores para repetir a ação confirmada.
    """
    ultima_acao = contexto_salvo.get("ultima_acao")
    ultima_intencao = contexto_salvo.get("ultima_intencao")
    dados_anteriores = contexto_salvo.get("dados_anteriores")

    if ultima_acao and dados_anteriores:
        if ultima_acao == "criar_evento":
            profissional = contexto_salvo.get("profissional_escolhido")
            servico = contexto_salvo.get("servico")
            data_hora = dados_anteriores.get("data_hora")

            if profissional and servico and data_hora:
                from .gpt_service import formatar_data, estimar_duracao, formatar_descricao_evento
                duracao = estimar_duracao(servico)
                return {
                    "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                    "acao": "criar_evento",
                    "dados": {
                        "data_hora": data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao,
                        "profissional": profissional
                    }
                }
        else:
            return {
                "resposta": f"✅ Ação confirmada: {ultima_intencao.replace('_', ' ').capitalize()}!",
                "acao": ultima_acao,
                "dados": dados_anteriores
            }

    return {
        "resposta": "⚠️ Não encontrei nenhuma ação recente para confirmar.",
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
