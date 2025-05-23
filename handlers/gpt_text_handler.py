from services.gpt_service import processar_com_gpt_com_acao
from services.firebase_service_async import buscar_cliente, buscar_subcolecao, salvar_dado_em_path, buscar_dado_em_path, obter_id_dono
from services.gpt_executor import executar_acao_gpt
from utils.formatters import formatar_horario_atual, formatar_lista_emails
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA, EXTRACAO_DADOS_EMAIL
from services.session_service import criar_ou_atualizar_sessao
from telegram import Update
from telegram.ext import ContextTypes
from handlers.acao_handler import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario
print("🔍 IMPORT de tratar_mensagem_usuario feito a partir do gpt_service")
from datetime import datetime, timedelta
from services.event_service_async import buscar_eventos_por_intervalo
from handlers.email_handler import enviar_email_natural
from utils.context_manager import carregar_contexto_temporario, atualizar_contexto, limpar_contexto
from services.email_service import ler_emails_google, filtrar_emails_por_nome
from unidecode import unidecode
from services.notificacao_service import criar_notificacao_agendada
from utils.context_manager import salvar_contexto_temporario, limpar_contexto, carregar_contexto_temporario
from utils.interpretador_datas import interpretar_intervalo_de_datas
from utils.intencao_utils import identificar_intencao, deve_ativar_fluxo_manual
import json
import pprint
import re
import sys

def extrair_data_de_texto(ev_texto):
    """
    Extrai a primeira data no formato dd/mm/aaaa de um texto.
    Retorna datetime.date, ou datetime.min.date() se nada for encontrado.
    """
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", ev_texto)
    if match:
        d, m, y = map(int, match.groups())
        return datetime(y, m, d).date()
    return datetime.min.date()

async def processar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🚀 Entrou no processar_texto()")
    texto = update.message.text
    user_id = str(update.message.from_user.id)

    # 🔎 Verificação sobre status da importação de profissionais
    if texto.lower() in ["importou?", "deu certo a importação?", "deu certo?", "funcionou?"]:
        status_importacao = context.user_data.get("ultima_importacao_profissionais")

        if status_importacao == "sucesso":
            await update.message.reply_text("✅ Sim, os profissionais foram importados com sucesso!")
        elif status_importacao == "erro":
            await update.message.reply_text("❌ Houve um problema na importação da planilha. Você pode tentar novamente.")
        else:
            await update.message.reply_text("🤔 Ainda não recebi nenhuma planilha recente para importar.")
        return  # 🔒 Para o fluxo aqui

    # 📧 Verifica se há e-mail pendente a ser finalizado
    if "email_em_espera" in context.user_data:
        await enviar_email_natural(update, context, texto)
        return  # 🔒 Garante que finalize esse fluxo antes de continuar com outros

    # ✅ Carregar contexto no início
    contexto_memoria = await carregar_contexto_temporario(user_id)
    print("🧠 Contexto carregado:", contexto_memoria)

    # 🧹 Limpeza seletiva se intenção for listar todos os profissionais
    intencao_listar_profissionais = any(p in texto.lower() for p in [
        "todos os profissionais", "todas as profissionais",
        "quem trabalha aí", "quais são as profissionais", "todo mundo que trabalha"
    ])

    if intencao_listar_profissionais:
        if contexto_memoria:
            for chave in ["profissional_escolhido", "servico", "data_hora"]:
                contexto_memoria.pop(chave, None)
            await salvar_dado_em_path(f"Clientes/{user_id}/MemoriaTemporaria/contexto", contexto_memoria)

    # 🔍 Verificação rápida para perguntas diretas sobre eventos
    texto_baixo = texto.lower()

    if any(p in texto_baixo for p in ["eventos de hoje", "tenho evento hoje", "qual evento hoje", "compromissos de hoje"]):
        eventos = await buscar_eventos_por_intervalo(user_id, dias=0)
    elif any(p in texto_baixo for p in ["amanhã", "tenho amanhã", "eventos amanhã"]):
        eventos = await buscar_eventos_por_intervalo(user_id, dias=1)
    # 🔍 Verificação inteligente para semana, intervalo ou datas flexíveis
    elif "semana" in texto_baixo or "entre os dias" in texto_baixo or "semana do" in texto_baixo or "próxima semana" in texto_baixo or "proxima semana" in texto_baixo:
        data_inicio, data_fim = interpretar_intervalo_de_datas(texto_baixo)
        eventos_todos = await buscar_eventos_por_intervalo(user_id, semana=True)
        eventos = [
            ev for ev in eventos_todos
            if data_inicio <= extrair_data_de_texto(ev) <= data_fim
        ]
    else:
        eventos = None  # Não foi uma pergunta óbvia → deixa pro GPT

    # 🎯 Se detectou eventos direto, responde e encerra
    if eventos is not None:
        if eventos:
            resposta = "📅 Seus eventos:\n" + "\n".join(f"- {e}" for e in eventos)
        else:
            resposta = "📭 Nenhum evento encontrado para o período solicitado."
        await update.message.reply_text(resposta)
        
        # Atualiza contexto após resposta
        await atualizar_contexto(user_id, {"usuario": texto, "bot": resposta})
        return  # Não segue pro GPT

    # ⚡ Etapa 1: Verifica se está no meio de um fluxo de agendamento
    sessao = pegar_sessao(user_id)
    if sessao and sessao.get("estado") != "completo":
        resposta_fluxo = await tratar_mensagem_usuario(user_id, texto)
        print("🚦 Vai chamar tratar_mensagem_usuario agora")
        await update.message.reply_text(resposta_fluxo)

        # Atualiza contexto após fluxo
        await atualizar_contexto(user_id, {"usuario": texto, "bot": resposta_fluxo})
        return

    # 🛡️ Verifica se o cliente está cadastrado
    dados_usuario = await buscar_cliente(user_id)
    print("📇 Dados do usuário:", dados_usuario)

    if not dados_usuario:
        resposta = (
            "👋 Olá! Eu sou a *NeoEve*, sua secretária virtual inteligente.\n"
            "Se você está me conhecendo agora, digite o comando `/start` para ativar sua assistente personalizada e começar a organizar sua rotina! 🚀"
        )
        await update.message.reply_text(resposta, parse_mode="Markdown")
        await criar_ou_atualizar_sessao(user_id, {"estado": "cadastro_nome"})
        await atualizar_contexto(user_id, {"usuario": texto, "bot": resposta})
        return  # <-- Para o fluxo aqui!

    # 👥 Identifica o cliente
    nome_usuario = update.message.from_user.full_name
    cliente_dados = await identificar_ou_cadastrar_cliente(user_id, nome_usuario)

    # (Opcional) Pode usar nome do cliente em respostas
    nome_cliente = cliente_dados.get("nome", "Cliente")

    id_dono = await obter_id_dono(user_id)  # 🧠 garante que pega o ID do dono mesmo se for cliente

    # 🔍 Buscar tarefas e eventos ainda são do usuário atual
    tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
    eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

    # ✅ PROFISSIONAIS devem ser buscados pelo ID DO DONO
    id_negocio = await obter_id_dono(user_id)
    profissionais_dict = await buscar_subcolecao(f"Clientes/{id_negocio}/Profissionais")
    print("📂 profissionais_dict recebido:", profissionais_dict)

    tarefas = [t["descricao"] for t in tarefas_dict.values() if isinstance(t, dict) and "descricao" in t]
    eventos = [e["descricao"] for e in eventos_dict.values() if isinstance(e, dict) and "descricao" in e]

    profissionais = []
    if isinstance(profissionais_dict, dict):
        for p in profissionais_dict.values():
            if isinstance(p, dict):
                nome = p.get("nome")
                servicos = p.get("servicos")
                if nome and isinstance(servicos, list):
                    profissionais.append({"nome": nome, "servicos": servicos})
    print("👥 Profissionais encontrados:", profissionais)

    # 🔍 Detectar serviço mencionado
    servicos_disponiveis = {s.lower() for p in profissionais for s in p.get("servicos", [])}
    servico_mencionado = None
    texto_baixo = unidecode(texto.lower())

    # 🎯 Detecção de serviço mencionando e adaptação por tipo de negócio
    for s in servicos_disponiveis:
        if re.search(rf'\b{s.lower()}\b', texto_baixo):
            servico_mencionado = s.lower()
            break

    # 💡 Correção semântica baseada no tipo de negócio
    tipo_negocio = contexto.get("usuario", {}).get("tipo_negocio", "").lower()

    # Exemplo: se for um salão e digitar "corte", entender que é "corte de cabelo"
    if tipo_negocio in ["salao", "salão", "estetica", "estética"] and "corte" in texto_baixo and not servico_mencionado:
        # Verifica se "corte" está entre os serviços
        for s in servicos_disponiveis:
            if "corte" in s:
                servico_mencionado = s
                break

    # 🔍 Verificação inteligente: exportar agenda
    if any(p in texto_baixo for p in [
        "agenda em excel", "me envia a agenda", "enviar agenda",
        "baixar minha agenda", "exportar agenda", "planilha de agenda"
    ]):
        from handlers.event_handler import enviar_agenda_excel

        # Detecta intervalo sugerido
        if "semana" in texto_baixo:
            intervalo = "semana"
        elif "amanhã" in texto_baixo:
            intervalo = "amanha"
        elif "hoje" in texto_baixo:
            intervalo = "hoje"
        else:
            intervalo = "completo"  # padrão se não tiver pista

        await enviar_agenda_excel(update, context, intervalo=intervalo)
        return

    # ✅ Garante que 'contexto' existe
    if "contexto" not in locals():
        contexto = {}

    # 💡 Detecta intenção de listar todos os profissionais explicitamente
    intencao_listagem_ampla = any(palavra in texto.lower() for palavra in [
        "todos os profissionais", "todas as profissionais",
        "quem trabalha aí", "quais são as profissionais", "todo mundo que trabalha"
    ])

    # 🧠 Decide se filtra por serviço ou mostra todos
    if intencao_listagem_ampla:
        profissionais_filtrados = profissionais  # ✅ Força a exibição de todos
    elif servico_mencionado:
        profissionais_filtrados = [
            p for p in profissionais
            if servico_mencionado in [s.lower() for s in p.get("servicos", [])]
        ]
    else:
        profissionais_filtrados = profissionais
       
    print("🎯 profissionais_filtrados:", profissionais_filtrados)
    # 🔧 Atualiza o contexto com a lista correta
    contexto["profissionais"] = profissionais_filtrados

    # 💾 SALVAR MEMÓRIA INICIAL SE SERVIÇO E DATA/HORA FOREM DETECTADOS
    
    memoria_inicial = {}

    if servico_mencionado:
        memoria_inicial["servico"] = servico_mencionado

    # Capturar data e hora se mencionadas no texto
    data_match = re.search(r'dia (\d{1,2})', texto.lower())
    hora_match = re.search(r'(\d{1,2})[:h](\d{2})?', texto.lower())

    if data_match and hora_match:
        dia = int(data_match.group(1))
        hora = int(hora_match.group(1))
        minuto = int(hora_match.group(2) or 0)

        agora = datetime.now()
        try:
            data_completa = agora.replace(day=dia, hour=hora, minute=minuto, second=0, microsecond=0)
            memoria_inicial["data_hora"] = data_completa.isoformat()
        except ValueError:
            pass  # Caso a data seja inválida

    # 💾 Salva somente se NÃO for intenção de listar todos os profissionais
    if memoria_inicial and not intencao_listar_profissionais:
        print(f"💾 Salvando memória inicial: {memoria_inicial}")
        await salvar_dado_em_path(f"Clientes/{user_id}/MemoriaTemporaria/contexto", memoria_inicial)

    usuario = {
        "user_id": user_id,  # <-- ESSENCIAL AQUI
        "nome": dados_usuario.get("nome", ""),
        "email": dados_usuario.get("email", ""),
        "tipo_usuario": dados_usuario.get("tipo_usuario", "cliente"),
        "modo_uso": dados_usuario.get("modo_uso", ""),
        "tipo_negocio": dados_usuario.get("tipo_negocio", ""),
        "nome_negocio": dados_usuario.get("nome_negocio", ""),
        "estilo": dados_usuario.get("estilo_mensagem", ""),
        "pagamentoAtivo": dados_usuario.get("pagamentoAtivo", False),
        "planosAtivos": dados_usuario.get("planosAtivos", [])
    }

    # 🔍 Aumenta profundidade se usuário buscar remetente específico
    pesquisa_especifica = any(p in texto.lower() for p in ["email do", "mensagem do", "tem algum email de", "recebi de", "email da", "mensagem da", "recebi da"])
    limite_emails = 15 if pesquisa_especifica else 5
    emails_raw = await ler_emails_google(user_id=user_id, num_emails=limite_emails)
    emails = [{
        "remetente": e.get("remetente", ""),
        "assunto": e.get("assunto", ""),
        "corpo": e.get("corpo", "")[:200],
        "prioridade": e.get("prioridade", ""),
        "link": e.get("link", "")
    } for e in emails_raw if isinstance(e, dict)]

    # 🔎 Inicializa variáveis para evitar erros
    emails_filtrados = []
    nome_mencionado = None

    # 🎯 Filtro por nome no texto (ex: "recebi algum e-mail do itau?")
    emails_filtrados, nome_mencionado = filtrar_emails_por_nome(texto, emails)

    # ✅ Responde diretamente se encontrou nome
    if nome_mencionado:
        if emails_filtrados:
            lista_formatada = formatar_lista_emails(emails_filtrados)
            resposta = f"Aqui estão os e-mails recebidos de {nome_mencionado.capitalize()}:\n{lista_formatada}"
        else:
            resposta = f"❌ Nenhum e-mail encontrado de {nome_mencionado.capitalize()}."
    
        await update.message.reply_text(resposta)
        await atualizar_contexto(user_id, {"usuario": texto, "bot": resposta})
        return  # ⛔️ Encerra aqui — evita GPT

    # Atualiza o contexto final
    contexto = {
        "usuario": usuario,
        "tarefas": tarefas,
        "eventos": eventos,
        "emails": emails,
        "profissionais": profissionais_filtrados
    }
    print("📦 Contexto final montado:", contexto)

    # 👤 Se já há um profissional escolhido salvo na memória, injeta no contexto
    profissional_escolhido = contexto_memoria.get("profissional_escolhido")
    if profissional_escolhido:
        print(f"🧠 Profissional já escolhido: {profissional_escolhido}")
        contexto["profissional_escolhido"] = profissional_escolhido

    # 🧠 Processar com GPT
    resultado_raw = await processar_com_gpt_com_acao(texto, contexto, INSTRUCAO_SECRETARIA)
    print("🔍 Resultado bruto do GPT:", resultado_raw)

    if isinstance(resultado_raw, dict) and resultado_raw.get("acao") == "criar_evento":
        await executar_acao_gpt(update, context, resultado_raw["acao"], resultado_raw["dados"])
        context.chat_data["evento_via_gpt"] = True

        # 🔄 Limpa a flag após uso
        context.user_data.pop("origem_email_detectado", None)

        # 🐞 Opcional: debug
        payload_debug = {
            "texto": texto,
            "contexto": contexto,
            "instrucoes": INSTRUCAO_SECRETARIA[:500] + "..."
        }
        print(json.dumps(payload_debug, indent=2))

        contexto_atual = await carregar_contexto_temporario(user_id) or {}
        contexto_atual["evento_criado"] = False
        await salvar_contexto_temporario(user_id, contexto_atual)
        await atualizar_contexto(user_id, {"usuario": texto, "bot": resultado_raw["resposta"]})
        return

    try:
        resultado = json.loads(resultado_raw) if isinstance(resultado_raw, str) else resultado_raw
        print("📦 Resultado processado:", resultado)
        
        # 💾 Salva profissional escolhido se detectado
        prof_detectado = resultado.get("dados", {}).get("profissional")
        if prof_detectado:
            await salvar_dado_em_path(
                f"Clientes/{user_id}/MemoriaTemporaria/contexto",
                {"profissional_escolhido": prof_detectado}
            )
            print(f"💾 Profissional detectado salvo: {prof_detectado}")

        # 👥 Fallback inteligente para exibir profissionais, se a IA esquecer
        tipo_negocio = contexto.get("usuario", {}).get("tipo_negocio", "").lower()

        negocios_com_profissionais = [
            "salao", "salão", "clinica", "clínica", "consultorio", "consultório", "escritorio", "escritório",
            "estetica", "estética", "agencia", "agência", "studio", "atendimento", "terapias"
        ]

        resposta_bot = resultado.get("resposta", "").strip().lower()

        frases_indicativas = [
            "aqui estão os profissionais cadastrados",
            "aqui estão os profissionais disponíveis",
            "segue a lista de profissionais",
            "temos os seguintes profissionais disponíveis"
        ]
        print("🔍 Verificando fallback de profissionais...")
        print("📌 tipo_negocio:", tipo_negocio)
        print("📌 profissionais no contexto:", contexto.get("profissionais"))
        print("📌 resposta do GPT:", resposta_bot)
        print("📌 Frase detectada?", any(frase in resposta_bot for frase in frases_indicativas))

        cond_fallback_profissionais = (
            tipo_negocio in negocios_com_profissionais
            and "profissionais" in contexto
            and contexto["profissionais"]
            and any(frase in resposta_bot for frase in frases_indicativas)
        )

        if cond_fallback_profissionais:
            print("⚙️ Ativando fallback de profissionais com base no tipo_negocio e resposta do GPT.")
            profissionais_formatados = [
                f"- {p['nome']}: {', '.join(p['servicos'])}" for p in contexto["profissionais"]
            ]
            resultado["resposta"] += "\n" + "\n".join(profissionais_formatados)
            resultado["acao"] = None
            resultado["dados"] = {}

        # 🛡️ Fallback: se o GPT ignorar os dados dos e-mails, monta a resposta manualmente
        if "leia meus emails" in texto.lower() and not resultado.get("dados", {}).get("emails") and emails:
            linhas = [
                f"- {e['remetente']}: {e['assunto']} (prioridade: {e['prioridade']})\n  🔗 {e['link'] or 'Sem link'}"
                for e in emails
            ]
            resultado["resposta"] = "Aqui estão os e-mails recebidos:\n" + "\n".join(linhas)
            resultado["acao"] = None
            resultado["dados"] = {}

        # 📦 Correção automática se o GPT não incluiu a lista de e-mails na resposta
        if (
            resultado.get("resposta", "").strip().lower() == "aqui estão seus e-mails:"
            and isinstance(resultado.get("dados", {}).get("emails"), list)
        ):
            emails = resultado["dados"]["emails"]
            linhas = [
                f"- {e.get('remetente')}: {e.get('assunto')} (prioridade: {e.get('prioridade', 'baixa')})\n  🔗 {e.get('link')}"
                for e in emails
            ]
            resultado["resposta"] = "Aqui estão os e-mails recebidos:\n" + "\n".join(linhas)
            resultado["dados"] = {}
            resultado["acao"] = None

    except Exception as e:
        print("❌ Erro ao decodificar JSON:", e)
        resultado = {
            "resposta": "❌ Ocorreu um erro ao interpretar a resposta da IA.",
            "acao": None,
            "dados": {}
        }
 
    # 🔧 Correções com base nos eventos reais
    dados = resultado.get("dados", {})
    if dados.get("agenda"):
        eventos_gpt = dados["agenda"]
        datas_gpt = [datetime.fromisoformat(e["data_hora"]).date() for e in eventos_gpt if "data_hora" in e]
        if datas_gpt:
            dia_especifico = datas_gpt[0]
            eventos_reais = await buscar_eventos_por_intervalo(user_id, dia_especifico=dia_especifico)
            if len(eventos_gpt) < len(eventos_reais):
                resposta = f"📅 Sua agenda completa para {dia_especifico.strftime('%d/%m/%Y')}:\n" + "\n".join(f"- {e}" for e in eventos_reais)
                await update.message.reply_text(resposta)
                return

    # 🔧 Correções automáticas com base no contexto
    if (
        "profissionais" in contexto and
        contexto["profissionais"] and
        (
            resultado.get("resposta", "").strip().lower() in [
                "aqui estão os profissionais cadastrados:",
                "aqui estão os profissionais disponíveis:",
                "segue a lista de profissionais:",
            ]
            or (
                resultado.get("resposta", "").strip().lower().startswith("temos os seguintes profissionais disponíveis")
            )
        )
    ):
        profissionais_formatados = [
            f"- {p['nome']}: {', '.join(p['servicos'])}" for p in contexto["profissionais"]
        ]
        resultado["resposta"] += "\n" + "\n".join(profissionais_formatados)
        resultado["acao"] = None
        resultado["dados"] = {}

    # ✅ Garantir variáveis sempre definidas
    acao = resultado.get("acao")
    dados = resultado.get("dados", {})
    resposta = resultado.get("resposta", "✅ Comando processado.")

    # 📂 Aguardar planilha para importar profissionais
    if acao == "aguardar_arquivo_importacao":
        context.user_data["esperando_planilha"] = True
        await update.message.reply_text(resposta)
        return

    # ⚙️ Aqui detecta se é um pedido de e-mail natural
    if acao == "enviar_email_natural" or any(p in texto.lower() for p in ["mande um email", "envie um email", "enviar e-mail", "dizer para"]):
        await enviar_email_natural(update, context, texto)
        return  # Já tratou, não precisa continuar

    # ⚙️ Executar ação (caso necessário)
    if acao == "criar_followup":
        from handlers.followup_handler import criar_followup_por_gpt
        await criar_followup_por_gpt(update, context, dados)
        await verificar_fim_fluxo_e_limpar(user_id, resultado)
        return

    elif acao:
        sucesso = await executar_acao_gpt(update, context, acao, dados)
        if not sucesso and resposta:
            await update.message.reply_text(resposta)
        return

    # 🔔 Se for tarefa, agenda notificação (opcional: com hora definida no futuro)
    if acao == "criar_tarefa" and "descricao" in dados:
        descricao_tarefa = dados["descricao"]
        horario = datetime.now() + timedelta(minutes=60)

        await criar_notificacao_agendada(
            user_id=user_id,
            descricao=descricao_tarefa,
            data=horario.strftime("%Y-%m-%d"),
            hora_inicio=horario.strftime("%H:%M"),
            canal="telegram",  # pode ser adaptado para "whatsapp"
            minutos_antes=0  # notifica no horário exato
        )

    # 💬 Responder usuário
    print(f"📤 Resposta final: {resposta}")
    try:
        await update.message.reply_text(resposta, parse_mode=None)
    except Exception as e:
        print(f"❌ Erro ao enviar resposta: {e}")

    # 🧠 Atualiza o contexto após a resposta
    await atualizar_contexto(user_id, {"usuario": texto, "bot": resposta})

    # 🧹 Verifica se deve limpar o contexto ao final
    await verificar_fim_fluxo_e_limpar(user_id, resultado)

    print("✅ Saiu do processar_texto()")

async def verificar_fim_fluxo_e_limpar(user_id: str, resultado: dict):
    acao = resultado.get("acao")
    
    if acao in ["criar_evento", "criar_tarefa", "enviar_email_natural", "criar_followup"]:
        await limpar_contexto(user_id)

    # 🧹 Limpeza também ao detectar fim natural da conversa
    resposta_usuario = resultado.get("resposta", "").lower()
    frases_fim = ["obrigado", "obrigada", "valeu", "tudo certo", "não, obrigado", "nao, obrigado", "de nada"]
    if any(p in resposta_usuario for p in frases_fim):
        await limpar_contexto(user_id)

async def identificar_ou_cadastrar_cliente(user_id, nome_usuario):
    """
    Verifica se o cliente já está cadastrado. Se não estiver, cadastra automaticamente.
    """
    path_cliente = f"Clientes/{user_id}"
    cliente_existente = await buscar_dado_em_path(path_cliente)

    if cliente_existente:
        print(f"👤 Cliente já cadastrado: {cliente_existente.get('nome', 'Desconhecido')}")
        return cliente_existente  # Já cadastrado, retorna os dados

    # 🆕 Cadastrar novo cliente
    novo_cliente = {
        "nome": nome_usuario,
        "data_cadastro": datetime.now().isoformat(),
        "historico_servicos": [],  # 🗂️ Lista para armazenar os serviços anteriores
    }

    await salvar_dado_em_path(path_cliente, novo_cliente)
    print(f"✅ Novo cliente cadastrado: {nome_usuario}")
    return novo_cliente
