#gpt Service
import os
import json
import re
import traceback
import importlib
import inspect
import unidecode
from datetime import datetime, timedelta
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario
from utils.custos_gpt import registrar_custo_gpt
from firebase_admin import firestore
from utils.interpretador_datas import interpretar_data_e_hora
from services.session_service import pegar_sessao, resetar_sessao
from utils.context_manager import atualizar_contexto, limpar_contexto
from services.profissional_service import listar_servicos_cadastrados, obter_precos_servico, encontrar_servico_mais_proximo
from services.gpt_client import client
from utils.gpt_utils import (
    montar_prompt_com_contexto,
    formatar_descricao_evento,
    estimar_duracao,
    formatar_data,
)
from services.gpt_intent import classificar_intencao_usuario
from services.gpt_actions import (
    executar_acao_gpt_por_confirmacao,
    executar_confirmacao_generica,
)

from services.firebase_service_async import buscar_cliente

# ✅ GPT simples para respostas diretas (com plano e módulos no prompt)
async def processar_com_gpt(texto_usuario, user_id="desconhecido"):
    try:
        # 🔍 Busca os dados do cliente
        cliente = await buscar_cliente(user_id)
        pagamento_ativo = cliente.get("pagamentoAtivo", False) if cliente else False
        planos_ativos = cliente.get("planosAtivos", []) if cliente else []

        # 🧠 Monta prompt com os dados de plano
        prompt_completo = f"""
📌 Plano ativo: {pagamento_ativo}
🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}

🗣️ Mensagem do usuário:
\"{texto_usuario}\"
"""

        resposta = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            messages=[
                {"role": "system", "content": INSTRUCAO_SECRETARIA},
                {"role": "user", "content": prompt_completo}
            ]
        )

        # 🔍 Registrar custo da chamada
        firestore_client = firestore.client()
        await registrar_custo_gpt(resposta, "gpt-4o", user_id, firestore_client)

        # ✅ Extrai conteúdo de forma segura
        try:
            conteudo = resposta.choices[0].message.content
            if conteudo:
                return conteudo.strip()
            else:
                raise ValueError("Conteúdo da resposta do GPT veio vazio.")
        except Exception as e:
            print("❌ Erro ao extrair resposta do GPT:", e)
            print("🧾 Objeto resposta:", resposta.model_dump_json(indent=2, ensure_ascii=False))
            return "❌ A IA não conseguiu entender seu pedido. Pode reformular?"

    except Exception as e:
        print(f"❌ Erro no GPT:", e)
        return "❌ Houve um erro ao processar com a IA."

async def tratar_mensagem_usuario(user_id, mensagem):
    print("🔥 [gpt_service] Entrou no tratar_mensagem_usuario via importlib")

    # 👇 Essa linha mostra de onde a função está sendo chamada
    print("📍 Stack de chamada:")
    for frame in inspect.stack()[1:5]:  # mostra os 4 níveis anteriores
        print(f" - Arquivo: {frame.filename}, Linha: {frame.lineno}, Função: {frame.function}")

    # Carrega a função original dinamicamente
    acao_handler = importlib.import_module("handlers.acao_handler")
    return await acao_handler.tratar_mensagem_usuario(user_id, mensagem)

# ✅ GPT com contexto e resposta estruturada em JSON (ação + dados)
async def processar_com_gpt_com_acao(texto_usuario, contexto, instrucao):
    print("🚨 [gpt_service] Arquivo carregado")
    try:
        user_id = str(contexto.get('usuario', {}).get('user_id', 'desconhecido'))
        texto_normalizado = unidecode.unidecode(texto_usuario.lower().strip())


        # 📍 Detecta intenção do usuário
        intencao = await classificar_intencao_usuario(texto_usuario)
        print(f"🎯 Intenção detectada: {intencao}")

        contexto_salvo = await carregar_contexto_temporario(user_id) or {}

        # 🛡️ Evita resposta repetitiva com 'None' após conversa concluída
        SAUDACOES_INICIAIS = [
            "oi", "ola", "olá", "opa", "e aí", "eaí", "bom dia", "boa tarde", "boa noite",
            "tudo bem", "como vai", "beleza", "salve", "fala aí", "fala", "oiê", "oi oi"
        ]

        if texto_normalizado in SAUDACOES_INICIAIS:
            try:
                # 👋 Oi depois de agendamento concluído → limpar contexto
                if contexto_salvo.get("evento_criado") and contexto_salvo.get("ultima_acao") == "criar_evento":
                    await limpar_contexto(user_id)
                    return {
                        "resposta": "👋 Olá! Em que mais posso te ajudar hoje?",
                        "acao": None,
                        "dados": {}
                    }

                # 😎 Oi durante um fluxo incompleto → retomar de onde parou
                elif any(contexto_salvo.get(k) for k in ["servico", "data_hora", "profissional_escolhido"]):
                    partes = []
                    if contexto_salvo.get("servico"):
                        partes.append(f"{contexto_salvo['servico']}")
                    if contexto_salvo.get("profissional_escolhido"):
                        partes.append(f"com {contexto_salvo['profissional_escolhido']}")
                    if contexto_salvo.get("data_hora"):
                        partes.append(f"para {formatar_data(contexto_salvo['data_hora'])}")

                    resumo = " ".join(partes)

                    return {
                        "resposta": f"Estamos no meio de um agendamento de {resumo}. Deseja confirmar, alterar ou cancelar?",
                        "acao": None,
                        "dados": {}
                    }

                # 👋 Oi fora de qualquer fluxo → início normal
                else:
                    return {
                        "resposta": "👋 Olá! Como posso te ajudar hoje?",
                        "acao": None,
                        "dados": {}
                    }

            except Exception as e:
                print(f"⚠️ Erro ao tratar saudação com contexto: {e}")
                return {
                    "resposta": "👋 Olá! Como posso te ajudar hoje?",
                    "acao": None,
                    "dados": {}
                }

        # 🧼 Se a intenção mudou e temos contexto salvo de agendamento, limpa tudo
        if intencao not in ["AGENDAR", "DESCONHECIDO"] and any(
            contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]
        ):
            print("🔄 Mudança de intenção detectada. Limpando contexto antigo.")
            await limpar_contexto(user_id)
            await resetar_sessao(user_id)
            contexto_salvo = {}

        # 🚫 Detecta intenção de cancelamento explícita
        texto_lower = texto_usuario.strip().lower()
        palavras_cancelamento = [
            "cancela", "cancelar", "não quero", "nao quero", "esquece", "deixa pra lá", "deixa pra la",
            "parei", "sai", "não desejo mais", "desisto"
        ]
        if any(p in texto_lower for p in palavras_cancelamento):
            print("🛑 Cancelamento detectado. Limpando contexto.")
            await limpar_contexto(user_id)
            await resetar_sessao(user_id)
            return {
                "resposta": "✅ Tudo bem, cancelei o agendamento em andamento. Se precisar de algo, estou aqui!",
                "acao": None,
                "dados": {}
            }

        contexto_salvo = await carregar_contexto_temporario(user_id) or {}
        if contexto_salvo.get("profissional_escolhido"):
            contexto_salvo.pop("ultima_opcao_profissionais", None)

        if not contexto_salvo.get("data_hora"):
            data_inteligente = interpretar_data_e_hora(texto_usuario)
            if data_inteligente:
                contexto_salvo["data_hora"] = data_inteligente.replace(second=0, microsecond=0).isoformat()
                print(f"🧠 Data/hora interpretada e salva de forma inteligente: {contexto_salvo['data_hora']}")
                await salvar_contexto_temporario(user_id, contexto_salvo)


        # 🧠 Extração antecipada
        texto_normalizado = unidecode.unidecode(texto_usuario.lower())
        data_hora_detectada = interpretar_data_e_hora(texto_usuario)
        servico_mencionado = None

        for p in contexto.get("profissionais", []):
            for s in p.get("servicos", []):
                if s.lower() in texto_normalizado:
                    servico_mencionado = s.lower()
                    break

        profissional_mencionado = None
        for p in contexto.get("profissionais", []):
            if p["nome"].lower() in texto_normalizado:
                profissional_mencionado = p["nome"]
                break

        # Atualiza contexto
        if profissional_mencionado and not contexto_salvo.get("profissional_escolhido"):
            contexto_salvo["profissional_escolhido"] = profissional_mencionado
        if servico_mencionado and not contexto_salvo.get("servico"):
            contexto_salvo["servico"] = servico_mencionado
        if data_hora_detectada and not contexto_salvo.get("data_hora"):
            contexto_salvo["data_hora"] = data_hora_detectada.replace(second=0, microsecond=0).isoformat()

        await salvar_contexto_temporario(user_id, contexto_salvo)

        # 💰 Consulta de preço tratada localmente (sem chamar o GPT)
        print("⚪ Verificando se menciona preço...")
        menciona_preco = any(
            chave in texto_normalizado for chave in ["preco", "preço", "valor", "custa", "quanto custa"]
        )
        print(f"🟡 menciona_preco: {menciona_preco}")
        print(f"🟡 servico_mencionado antes da normalização: {servico_mencionado}")

        if menciona_preco:
            from services.profissional_service import obter_precos_servico
            from services.normalizacao_service import encontrar_servico_mais_proximo

            if not servico_mencionado:
                servico_mencionado = await encontrar_servico_mais_proximo(texto_usuario, user_id)
                print(f"🔍 Serviço mencionado após normalização: {servico_mencionado}")

            if servico_mencionado:
                if profissional_mencionado:
                    preco = await obter_precos_servico(
                        user_id, servico_mencionado, profissional_mencionado
                    )
                    if preco is not None:
                        try:
                            valor_formatado = f"{float(preco):.2f}"
                        except Exception:
                            valor_formatado = str(preco)
                        resposta = (
                            f"O preço de *{servico_mencionado}* com *{profissional_mencionado}* é R$ {valor_formatado}"
                        )
                    else:
                        resposta = (
                            f"Infelizmente não temos o preço de {servico_mencionado} com {profissional_mencionado} ainda."
                        )
                else:
                    precos = await obter_precos_servico(user_id, servico_mencionado)
                    if not precos:
                        # tenta normalizar o serviço se não encontrou nenhum preço
                        servico_sugerido = await encontrar_servico_mais_proximo(texto_usuario, user_id)
                        if servico_sugerido and servico_sugerido != servico_mencionado:
                            servico_mencionado = servico_sugerido
                            precos = await obter_precos_servico(user_id, servico_mencionado)

                    if precos:
                        resposta = f"Valores de *{servico_mencionado}*:\n"
                        for nome, preco_val in precos.items():
                            try:
                                valor_formatado = f"{float(preco_val):.2f}"
                            except Exception:
                                valor_formatado = str(preco_val)
                            resposta += f"- *{nome}*: R$ {valor_formatado}\n"
                    else:
                        resposta = "Infelizmente não temos esse preço ainda."
            else:
                resposta = "❌ Não consegui identificar o serviço para informar o preço. Você pode tentar reformular a pergunta?"

            await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta})

            return {
                "resposta": resposta,
                "acao": None,
                "dados": {}
            }

        # ⚡ Reconhecer respostas curtas de confirmação
        resposta_direta = texto_usuario.strip().lower()
        palavras_confirmacao = [
            "confirmar", "pode ser", "pode marcar", "fechar",
            "tá bom", "tudo certo", "ok", "isso", "agendar", "sim", "beleza", "claro",
            "desejo continuar", "quero continuar", "continuar", "vamos continuar"
        ]
        resposta_curta = (
            any(p in resposta_direta for p in palavras_confirmacao)
            and len(resposta_direta.split()) <= 6  # aumentei de 4 para 6 para pegar variações como "desejo continuar agora"
        )

        if resposta_curta and contexto_salvo.get("ultima_acao"):
            from services.gpt_service import executar_confirmacao_generica
            print("✅ Detectada confirmação de continuidade.")

            # ✅ Verifica se a última mensagem do BOT foi uma sugestão ou pergunta
            historico = contexto_salvo.get("historico", [])
            if historico:
                ultima_interacao = historico[-1]
                ultima_mensagem_bot = ultima_interacao.get("bot", "").lower()

                print("🧪 [DEBUG] Última mensagem do bot:", ultima_mensagem_bot)

                if any(p in ultima_mensagem_bot for p in [
                    "deseja", "prefere", "posso", "quer que", "confirmar", "gostaria", "agendar", "continuar", "seguir", "fechar", "?", "vamos", "pode"
                ]):
                    print("🧠 Última mensagem do bot indica ação pendente.")
                    print("➡️ Executando ação confirmada:", contexto_salvo.get("ultima_acao"))
                    return await executar_confirmacao_generica(user_id, contexto_salvo)
                else:
                    print("🚫 Última mensagem do bot não parece ser uma sugestão de ação.")
            else:
                print("🚫 Sem histórico suficiente para validar confirmação.")

            # ⛔️ Caso não seja uma resposta a uma sugestão, não executa ação
            await update.message.reply_text("❌ Não entendi o que deseja continuar. Pode repetir o pedido?")
            return
            return {
                "resposta": "❌ Não entendi o que deseja continuar. Pode repetir o pedido?",
                "acao": None,
                "dados": {}
            }

        # ✅ Verifica se há novos dados antes de seguir
        tem_novos_dados = profissional_mencionado or servico_mencionado or data_hora_detectada

        # Se o usuário não trouxe novos dados, e já temos um contexto anterior incompleto
        if not tem_novos_dados:
            if all(contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]):
                return {
                    "resposta": (
                        f"Você mencionou um {contexto_salvo['servico']} com "
                        f"{contexto_salvo['profissional_escolhido']} para "
                        f"{formatar_data(contexto_salvo['data_hora'])}. "
                        "Deseja confirmar, alterar ou cancelar?"
                    ),
                    "acao": None,
                    "dados": {}
                }
            elif any(contexto_salvo.get(k) for k in ["servico", "data_hora", "profissional_escolhido"]):
                partes = []
                if contexto_salvo.get("servico"):
                    partes.append(f"um {contexto_salvo['servico']}")
                if contexto_salvo.get("profissional_escolhido"):
                    partes.append(f"com {contexto_salvo['profissional_escolhido']}")
                if contexto_salvo.get("data_hora"):
                    partes.append(f"para {formatar_data(contexto_salvo['data_hora'])}")

                resumo = " ".join(partes) if partes else "um agendamento"

                # 🧠 Salva a intenção pendente no contexto
                contexto_salvo["ultima_acao"] = "criar_evento"
                contexto_salvo["ultima_intencao"] = "criar_evento"
                contexto_salvo["dados_anteriores"] = {
                    "profissional": contexto_salvo.get("profissional_escolhido"),
                    "servico": contexto_salvo.get("servico"),
                    "data_hora": contexto_salvo.get("data_hora"),
                    "duracao": estimar_duracao(contexto_salvo.get("servico", ""))
                }
                await salvar_contexto_temporario(user_id, contexto_salvo)

                return {
                    "resposta": (
                        f"Você estava iniciando {resumo}. "
                        "Deseja continuar ou começar algo novo?"
                    ),
                    "acao": None,
                    "dados": {}
                }

        #🔒Verifica se há sessão pendente (ex: aguardando_profissional)
        sessao = await pegar_sessao(user_id)
        if sessao and sessao.get("estado") in ["aguardando_profissional", "aguardando_nome_cliente"]:
            resposta = await tratar_mensagem_usuario(user_id, texto_usuario)
            return {
                "resposta": resposta,
                "acao": None,
                "dados": {}
            }

        contexto = contexto or {}  # <- esta linha precisa vir ANTES do .get
        profissionais = contexto.get("profissionais", [])
        texto_normalizado = unidecode.unidecode(texto_usuario.lower())

        # 📋 Verifica se o usuário quer apenas a lista de serviços disponíveis
        intencao_listar_servicos = any(
            chave in texto_normalizado
            for chave in [
                "quais servicos",
                "quais serviços",
                "servicos voce tem",
                "serviços você tem",
                "lista de servicos",
                "lista de serviços",
                "que servicos",
                "que serviços",
            ]
        )
        if intencao_listar_servicos:
            servicos = await listar_servicos_cadastrados(user_id)
            if servicos:
                resposta = "Aqui estão os serviços disponíveis:\n- " + "\n- ".join(servicos)
            else:
                resposta = "Não há serviços cadastrados no momento."
            await atualizar_contexto(
                user_id,
                {"usuario": texto_usuario, "bot": resposta},
            )
            return {"resposta": resposta, "acao": None, "dados": {}}

        # ✅ Tenta agendar diretamente se contexto completo
        if all(contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]):
            try:
                profissional = contexto_salvo["profissional_escolhido"]
                servico = contexto_salvo["servico"]
                data_hora = contexto_salvo["data_hora"]

                duracao = estimar_duracao(servico)
                from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                data = datetime.fromisoformat(data_hora).strftime("%Y-%m-%d")
                hora = datetime.fromisoformat(data_hora).strftime("%H:%M")

                conflito = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id, data=data, hora_inicio=hora,
                    duracao_min=duracao, profissional=profissional, servico=servico
                )

                if not conflito["conflito"]:
                    contexto_salvo.update({
                        "evento_criado": True,
                        "ultima_acao": "criar_evento",
                        "dados_anteriores": {
                            "data_hora": data_hora,
                            "descricao": formatar_descricao_evento(servico, profissional),
                            "duracao": duracao,
                            "profissional": profissional
                        }
                    })
                    await salvar_contexto_temporario(user_id, contexto_salvo)

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

            except Exception as e:
                print(f"⚠️ Erro ao tratar fluxo de agendamento automático: {e}")
                return {
                    "resposta": "👋 Como posso te ajudar hoje?",
                    "acao": None,
                    "dados": {}
                }

        # 🔄 Caso esteja no meio de um agendamento, ignora o "oi"
        #else:
        #    return {
        #        "resposta": "🔄 Estamos no meio de um agendamento. Por favor, diga o nome da profissional, a data ou o horário desejado para continuar.",
        #        "acao": None,
        #        "dados": {}
        #    }

        # 🔍 Detecta intenção de listar todos os profissionais
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

        data_hora_detectada = interpretar_data_e_hora(texto_usuario)

        # ✅ Aqui: Salva contexto atualizado antes de filtrar profissionais
        memoria_nova = {}

        if servico_mencionado:
            memoria_nova["servico"] = servico_mencionado

        if data_hora_detectada:
            data_hora_iso = data_hora_detectada.replace(second=0, microsecond=0).isoformat()
            if data_hora_iso != contexto_salvo.get("data_hora"):
                memoria_nova["data_hora"] = data_hora_iso

        
        if memoria_nova:
            contexto_salvo.update(memoria_nova)
            await salvar_contexto_temporario(user_id, contexto_salvo)
            contexto_salvo = await carregar_contexto_temporario(user_id) or {}
            if contexto_salvo.get("profissional_escolhido"):
                contexto_salvo.pop("ultima_opcao_profissionais", None)

            if not contexto_salvo.get("data_hora"):
                data_inteligente = interpretar_data_e_hora(texto_usuario)
                if data_inteligente:
                    contexto_salvo["data_hora"] = data_inteligente.replace(second=0, microsecond=0).isoformat()
                    print(f"🧠 Data/hora interpretada e salva de forma inteligente: {contexto_salvo['data_hora']}")
                    await salvar_contexto_temporario(user_id, contexto_salvo)


        if contexto_salvo is None:
            contexto_salvo = {}  # 🔧 Garante que temos ao menos um dicionário vazio

        # ✅ Garante que o contexto existe como dicionário
        contexto = contexto or {}

        # 🧠 Decide se filtra ou mantém todos
        if servico_mencionado and not intencao_listagem_ampla:
            profissionais_filtrados = [
                p for p in profissionais
                if servico_mencionado in [s.lower() for s in p.get("servicos", [])]
            ]
        else:
            profissionais_filtrados = profissionais  # Usa todos

        # Se houver um horário detectado, filtre apenas os disponíveis nesse horário
        if contexto_salvo.get("data_hora"):
            from services.event_service_async import verificar_conflito_e_sugestoes_profissional
            data = datetime.fromisoformat(contexto_salvo["data_hora"])
            data_str = data.strftime("%Y-%m-%d")
            hora_str = data.strftime("%H:%M")
            duracao = estimar_duracao(servico_mencionado) if servico_mencionado else 60

            profissionais_disponiveis = []
            for prof in profissionais_filtrados:
                conflito = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id,
                    data=data_str,
                    hora_inicio=hora_str,
                    duracao_min=duracao,
                    profissional=prof["nome"],
                    servico=servico_mencionado or ""
                )
                if not conflito["conflito"]:
                    profissionais_disponiveis.append(prof)

            contexto["profissionais"] = profissionais_disponiveis
        else:
            profissionais_disponiveis = profissionais_filtrados
            contexto["profissionais"] = profissionais_disponiveis

        # ✅ Listagem direta de profissionais
        if intencao_listagem_ampla and profissionais_disponiveis:
            profissionais_formatados = [
                f"- {p['nome']}: {', '.join(p['servicos'])}" for p in profissionais_disponiveis
            ]
            await atualizar_contexto(user_id, {
                "usuario": texto_usuario,
                "bot": "Aqui estão as profissionais cadastradas:\n" + "\n".join(profissionais_formatados)
            })
            return {
                "resposta": "Aqui estão as profissionais cadastradas:\n" + "\n".join(profissionais_formatados),
                "acao": None,
                "dados": {}
            }

        # ✅ Novo: se temos profissionais disponíveis, mas ainda não há um escolhido, sugerimos nomes
        if profissionais_disponiveis and not contexto_salvo.get("profissional_escolhido"):
            servico_para_frase = servico_mencionado or contexto_salvo.get("servico")
    
            if not servico_para_frase:
                return {
                    "resposta": "Para te mostrar os profissionais corretos, qual serviço você deseja?",
                    "acao": "aguardar_servico",
                    "dados": {}
                }

            # 🧠 Atualiza nome do serviço se novo
            if servico_mencionado and contexto_salvo.get("servico") != servico_mencionado:
                contexto_salvo["servico"] = servico_mencionado

            nomes = [p["nome"] for p in profissionais_disponiveis]
            contexto_salvo["ultima_opcao_profissionais"] = nomes

            servico_para_frase = (
                servico_mencionado or contexto_salvo.get("servico")
            ).strip()

            data_hora_str = contexto_salvo.get("data_hora")
            data_formatada = formatar_data(data_hora_str) if data_hora_str else "em breve"

            resposta = f"Temos disponibilidade para {servico_para_frase} {data_formatada}. Deseja ser atendido por {' ou '.join(nomes)}?"

            await atualizar_contexto(user_id, {
                "usuario": texto_usuario,
                "bot": resposta
            })

            await salvar_contexto_temporario(user_id, contexto_salvo)

            return {
                "resposta": resposta,
                "acao": None,
                "dados": {}
            }

        # 🧠 Salva também o serviço mencionado (se houver) para uso posterior
        if servico_mencionado:
            contexto_salvo = await carregar_contexto_temporario(user_id) or {}
            if contexto_salvo.get("profissional_escolhido"):
                contexto_salvo.pop("ultima_opcao_profissionais", None)

            if not contexto_salvo.get("data_hora"):
                data_inteligente = interpretar_data_e_hora(texto_usuario)
                if data_inteligente:
                    contexto_salvo["data_hora"] = data_inteligente.replace(second=0, microsecond=0).isoformat()
                    print(f"🧠 Data/hora interpretada e salva de forma inteligente: {contexto_salvo['data_hora']}")
                    await salvar_contexto_temporario(user_id, contexto_salvo)


        nomes_profissionais = [p["nome"].lower() for p in contexto["profissionais"]]
        resposta_direta = texto_usuario.strip().lower()

        contexto_salvo = await carregar_contexto_temporario(user_id)
        print("📥 Contexto salvo atual:", contexto_salvo)  # 👈 Coloque aqui

        # ✅ Novo: o usuário respondeu diretamente com um nome da última sugestão?
        resposta_direta = texto_usuario.strip().title()
        opcoes_anteriores = contexto_salvo.get("ultima_opcao_profissionais", [])

        if any(resposta_direta.lower() in nome.lower() for nome in opcoes_anteriores):
            profissional = next((n for n in opcoes_anteriores if resposta_direta.lower() in n.lower()), resposta_direta)
            servico = contexto_salvo.get("servico")
            data_hora = contexto_salvo.get("data_hora")

            if servico and data_hora:
                duracao = estimar_duracao(servico)
                await salvar_contexto_temporario(user_id, {
                    "profissional_escolhido": profissional,
                    "servico": servico,
                    "data_hora": data_hora,
                    "evento_criado": True,
                    "ultima_acao": "criar_evento",
                    "ultima_intencao": "criar_evento",
                    "dados_anteriores": {
                        "profissional": profissional,
                        "servico": servico,
                        "data_hora": data_hora,
                        "duracao": duracao
                    }
                })

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
                # salva apenas o nome, continua a coleta
                await salvar_contexto_temporario(user_id, {
                    "profissional_escolhido": profissional
                })
                return {
                    "resposta": f"Perfeito! {profissional} foi selecionada. Agora diga a data e o horário que você prefere.",
                    "acao": None,
                    "dados": {}
                }

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
                    "data_hora": nova_data_hora,
                    "evento_criado": True
                })

                return {
                    "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(nova_data_hora)}. ✂️",
                    "acao": "criar_evento",
                    "dados": {
                        "data_hora": nova_data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao,
                        "profissional": profissional
                    }
                }

        # 🎯 Verifica se a resposta menciona diretamente um profissional
        texto_normalizado = unidecode.unidecode(resposta_direta.lower())

        for prof in nomes_profissionais:
            prof_normalizado = unidecode.unidecode(prof.lower())
        
            # Permite detectar frases como "pela Carla", "com a Carla", "Carla"
            if re.search(rf"\b(pela|com|com a|a|para|por)?\s*{prof_normalizado}\b", texto_normalizado):
                opcoes_disponiveis = contexto_salvo.get("ultima_opcao_profissionais", [])
                servico = contexto_salvo.get("servico")
                data_hora = contexto_salvo.get("data_hora")

                print(f"🔍 Verificação de dados: profissional={prof.capitalize()}, servico={servico}, data_hora={data_hora}, opções={opcoes_disponiveis}")

                if prof.capitalize() in opcoes_disponiveis and servico and data_hora:
                    duracao = estimar_duracao(servico)
                    await salvar_contexto_temporario(user_id, {
                        "profissional_escolhido": prof.capitalize(),
                        "servico": servico,
                        "data_hora": data_hora,
                        "evento_criado": True
                    })
                    return {
                        "resposta": f"{servico.capitalize()} agendado com {prof.capitalize()} para {formatar_data(data_hora)}. ✂️",
                        "acao": "criar_evento",
                        "dados": {
                            "data_hora": data_hora,
                            "descricao": f"{servico} com {prof.capitalize()}",
                            "duracao": duracao
                        }
                    }
                else:
                    # 🧠 Salva o profissional escolhido e tenta completar depois
                    await salvar_contexto_temporario(user_id, {"profissional_escolhido": prof.capitalize()})
                    contexto_salvo = await carregar_contexto_temporario(user_id)
                

                    if contexto_salvo.get("evento_criado"):
                        return {
                            "resposta": "✅ O agendamento já foi registrado anteriormente.",
                            "acao": None,
                            "dados": {}
                        }
 
                    profissional = contexto_salvo.get("profissional_escolhido")
                    servico = contexto_salvo.get("servico")
                    data_hora = contexto_salvo.get("data_hora")

                    if profissional and servico and data_hora:
                        duracao = estimar_duracao(servico)

                        await salvar_contexto_temporario(user_id, {"evento_criado": True})

                        return {
                            "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                            "acao": "criar_evento",
                            "dados": {
                                "data_hora": data_hora,
                                "descricao": formatar_descricao_evento(servico, profissional),
                                "duracao": duracao
                            }
                        }

            # 🔍 Garante que os dados do cliente estejam no contexto
            cliente = await buscar_cliente(user_id)
            if cliente:
                contexto["usuario"] = cliente
                contexto["pagamentoAtivo"] = cliente.get("pagamentoAtivo", False)
                contexto["planosAtivos"] = cliente.get("planosAtivos", [])


            messages = montar_prompt_com_contexto(INSTRUCAO_SECRETARIA, contexto, contexto_salvo, texto_usuario)

            resposta = await client.chat.completions.create(
                model="gpt-4o",
                temperature=0.4,
                messages=messages
            )
            firestore_client = firestore.client()
            await registrar_custo_gpt(resposta, "gpt-4o", user_id, firestore_client)
 
            try:
                conteudo = resposta.choices[0].message.content
                if conteudo:
                    conteudo = conteudo.strip()
                else:
                    raise ValueError("Conteúdo da resposta do GPT veio vazio.")

                print("📨 Conteúdo bruto do GPT:\n", conteudo)

                if "{" in conteudo and "}" in conteudo:
                    inicio = conteudo.index("{")
                    fim = conteudo.rindex("}")
                    json_puro = conteudo[inicio:fim + 1]
                else:
                    raise ValueError("JSON mal formado: delimitadores '{' ou '}' ausentes.")

                resultado = json.loads(json_puro)

            except Exception as e:
                print("🛑 Erro ao interpretar resposta do GPT:")
                print(f"❗ Tipo de erro: {type(e).__name__}")
                print(f"❗ Erro: {e}")
                print("📦 Objeto de resposta bruto:")
                print(resposta.model_dump_json(indent=2, ensure_ascii=False))

                return {
                    "resposta": "❌ A IA respondeu fora do formato esperado. Pode reformular a pergunta?",
                    "acao": None,
                    "dados": {}
                }

            # 🟡 Salve também o serviço e a data_hora se existirem, mesmo que estejam fora de 'dados'
            if "descricao" in resultado.get("dados", {}):
                descricao = resultado["dados"]["descricao"].lower()
                if "com" in descricao:
                    servico_detectado = descricao.split("com")[0].strip()
                    memoria_nova["servico"] = servico_detectado
                else:
                    memoria_nova["servico"] = descricao

            if "data_hora" in resultado.get("dados", {}):
                memoria_nova["data_hora"] = resultado["dados"]["data_hora"]

            # ✅ Verifica se já temos os 3 elementos e agenda diretamente
            profissional = memoria_nova.get("profissional_escolhido") or contexto_salvo.get("profissional_escolhido")
            servico = memoria_nova.get("servico") or contexto_salvo.get("servico")
            data_hora = memoria_nova.get("data_hora") or contexto_salvo.get("data_hora")

            if profissional and servico and data_hora:
                duracao = estimar_duracao(servico)

                await salvar_contexto_temporario(user_id, {
                    "evento_criado": True,
                    "ultima_acao": "criar_evento",
                    "ultima_intencao": "criar_evento",
                    "dados_anteriores": {
                        "data_hora": data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao,
                        "profissional": profissional
                    }
                })

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
                intencao_listagem_ampla
                and contexto.get("profissionais")
                and not resultado.get("acao")
                and not resultado.get("resposta")
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
                descricao = resultado["dados"]["descricao"]
                memoria_nova["servico"] = descricao.split(" com ")[0].strip().lower()

            if "data_hora" in resultado.get("dados", {}):
                memoria_nova["data_hora"] = resultado["dados"]["data_hora"]


            # ✅ Antes de salvar, verifique se já dá para agendar
            profissional = memoria_nova.get("profissional_escolhido") or contexto_salvo.get("profissional_escolhido")
            servico = memoria_nova.get("servico") or contexto_salvo.get("servico")
            data_hora = memoria_nova.get("data_hora") or contexto_salvo.get("data_hora")


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
                contexto_salvo = await carregar_contexto_temporario(user_id) or {}
                if contexto_salvo.get("profissional_escolhido"):
                    contexto_salvo.pop("ultima_opcao_profissionais", None)

                if not contexto_salvo.get("data_hora"):
                    data_inteligente = interpretar_data_e_hora(texto_usuario)
                    if data_inteligente:
                        contexto_salvo["data_hora"] = data_inteligente.replace(second=0, microsecond=0).isoformat()
                        print(f"🧠 Data/hora interpretada e salva de forma inteligente: {contexto_salvo['data_hora']}")
                        await salvar_contexto_temporario(user_id, contexto_salvo)

                contexto_salvo.update(memoria_nova)
                await salvar_contexto_temporario(user_id, contexto_salvo)

            # 🔧 Adiciona sugestão de profissionais compatíveis com o serviço, se for o caso
            if (
                servico_mencionado
                and resultado.get("acao") not in ["criar_evento", "consultar_preco_servico"]
                and resultado.get("resposta")
                and contexto.get("profissionais")
            ):
                profissionais_compativeis = []
                for p in contexto["profissionais"]:
                    servicos = [s.lower() for s in p.get("servicos", []) if isinstance(s, str)]
                    if servico_mencionado in servicos:
                        profissionais_compativeis.append(p["nome"])

                if profissionais_compativeis:
                    profissionais_compativeis = list(set(profissionais_compativeis))  # remove duplicados
                    nomes_formatados = ", ".join(profissionais_compativeis)

                    resposta_atual = resultado["resposta"].strip().lower()

                    # ✅ Evita repetir se nomes já estiverem mencionados
                    nomes_ja_mencionados = all(
                        nome.lower() in resposta_atual for nome in profissionais_compativeis
                    )

                    if not nomes_ja_mencionados:
                        resposta_base = resultado["resposta"].strip()

                        # Remove final padrão do GPT se existir
                        resposta_base = re.sub(
                            r"deseja ser atendido por.*?$", "", resposta_base, flags=re.IGNORECASE
                        ).strip()

                        nova_resposta = f"{resposta_base} Deseja ser atendido por {nomes_formatados}?"
                        resultado["resposta"] = nova_resposta

                    if (
                        servico_mencionado
                        and data_hora_detectada
                        and contexto["profissionais"]  # se houver sugestões reais
                    ):
                        await salvar_contexto_temporario(user_id, {
                            "servico": servico_mencionado,
                            "data_hora": data_hora_detectada.isoformat(),
                            "ultima_acao": "criar_evento",
                            "ultima_intencao": "criar_evento",
                            "dados_anteriores": {
                                "data_hora": data_hora_detectada.isoformat(),
                                "duracao": estimar_duracao(servico_mencionado),
                                "descricao": f"{servico_mencionado.capitalize()} com ...",  # incompleto
                                "profissional": None  # aguarda o usuário escolher
                            },
                            "ultima_opcao_profissionais": [p["nome"] for p in contexto["profissionais"]]
                        })


            if resultado.get("acao") and resultado.get("dados"):
                await salvar_contexto_temporario(user_id, {
                    "ultima_acao": resultado["acao"],
                    "dados_anteriores": resultado["dados"],
                    "ultima_intencao": resultado.get("acao")  # 👈 mesma ação por padrão
                })

            # 🧠 Se houver intenção nova e não estiver em meio a execução de ação, pode limpar contexto
            if resultado.get("acao") is None and intencao not in ["AGENDAR", "DESCONHECIDO"]:
                if any(contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]):
                    print("🧹 Mudança de assunto detectada sem ação pendente. Limpando contexto.")
                    await limpar_contexto(user_id)
                    await resetar_sessao(user_id)
                    contexto_salvo = {}

             # ✅ Verificações finais após processar toda a lógica principal
            if contexto_salvo.get("evento_criado") and not contexto_salvo.get("ultima_acao"):
                for chave in [
                    "evento_criado", "data_hora", "servico", "profissional_escolhido",
                    "ultima_opcao_profissionais", "ultima_acao", "dados_anteriores", "ultima_intencao"
                ]:
                    contexto_salvo.pop(chave, None)

                await salvar_contexto_temporario(user_id, contexto_salvo)

                return {
                    "resposta": "👋 Olá! Em que mais posso te ajudar hoje?",
                    "acao": None,
                    "dados": {}
                }
            elif any(contexto_salvo.get(k) for k in ["servico", "data_hora", "profissional_escolhido"]):
                return {
                    "resposta": "😊 Podemos continuar de onde paramos. Deseja confirmar o profissional ou horário?",
                    "acao": None,
                    "dados": {}
                }

            return resultado

    except json.JSONDecodeError:
        return {
            "resposta": "❌ A IA respondeu fora do formato esperado.",
            "acao": None,
            "dados": {}
        }
    except Exception as e:
        print(f"❌ Erro em processar_com_gpt_com_acao: {e}")
        traceback.print_exc()
        return {
            "resposta": "❌ Ocorreu um erro ao tentar entender seu pedido.",
            "acao": None,
            "dados": {}
        }

from services.firebase_service_async import buscar_cliente

# ✅ Organização da semana (com dados de plano no prompt)
async def organizar_semana_com_gpt(tarefas: list, eventos: list, user_id: str, dia_inicio: str = "hoje"):
    try:
        hoje = datetime.now().date()

        dias_formatados = [
            (hoje + timedelta(days=i)).strftime("%A (%d/%m)") for i in range(5)
        ]

        # 🔍 Busca dados do cliente
        cliente = await buscar_cliente(user_id)
        pagamento_ativo = cliente.get("pagamentoAtivo", False) if cliente else False
        planos_ativos = cliente.get("planosAtivos", []) if cliente else []

        # 🧠 Prompt completo com contexto
        prompt = f"""
📌 Plano ativo: {pagamento_ativo}
🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}

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
{chr(10).join(f"- {t}" for t in tarefas) or 'Nenhuma'}

Eventos:
{chr(10).join(f"- {e}" for e in eventos) or 'Nenhum'}

Responda apenas com o plano formatado.
"""

        resposta = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            messages=[
                {"role": "system", "content": INSTRUCAO_SECRETARIA},
                {"role": "user", "content": prompt}
            ]
        )

        return resposta.choices[0].message.content.strip()

    except Exception as e:
        print(f"[GPT] Erro ao organizar semana: {e}")
        return "❌ Houve um erro ao tentar planejar sua semana."