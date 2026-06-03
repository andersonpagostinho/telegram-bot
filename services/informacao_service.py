from unidecode import unidecode
from services.profissional_service import (
    buscar_profissionais_por_servico,
    buscar_profissionais_disponiveis_no_horario,
    encontrar_servico_mais_proximo
)
from services.firebase_service_async import buscar_subcolecao, obter_id_dono
from utils.interpretador_datas import interpretar_data_e_hora
from datetime import datetime, date, timedelta
import re
import string

def formatar_nomes_humanos(profs: list[str]) -> str:
    """Formata lista de profissionais com linguagem natural.
    ["Bruna"] → "Bruna"
    ["Bruna", "Gloria"] → "Bruna ou Gloria"
    ["Bruna", "Gloria", "Joana"] → "Bruna, Gloria ou Joana"
    """
    if not profs:
        return ""
    if len(profs) == 1:
        return profs[0]
    if len(profs) == 2:
        return f"{profs[0]} ou {profs[1]}"
    return ", ".join(profs[:-1]) + f" ou {profs[-1]}"

def formatar_resposta_disponibilidade(
    servico: str,
    data_str: str,
    periodo_str: str,
    profissionais_disponiveis: list[str],
    com_horario: bool = False,
    horario: str = None
) -> str:
    """
    Formatador padrão para respostas de disponibilidade.
    Garante cliente e dono recebem o mesmo formato.

    Args:
        servico: Nome do serviço (ex: "corte", "escova")
        data_str: Data formatada (ex: "03/06", "amanhã")
        periodo_str: Período (ex: "de manhã", "à tarde", ou "" se com horário)
        profissionais_disponiveis: Lista de nomes de profissionais (max 3)
        com_horario: Se True, usa o horário específico no formato
        horario: Horário específico (ex: "8h", "09:00")

    Returns:
        Mensagem formatada padronizada
    """
    if not profissionais_disponiveis:
        return f"😕 Desculpe, nenhum profissional de {servico} está disponível {periodo_str} em {data_str}."

    # Limitar a máximo 3 profissionais
    profs = profissionais_disponiveis[:3]
    nomes_formatados = formatar_nomes_humanos(profs)

    # Formatar conforme o número de opções (NÃO assume horário quando apenas período foi informado)
    if len(profs) == 1:
        # 1 profissional: pergunta direta
        if com_horario and horario:
            return f"Tenho sim. Para {servico} {data_str} às {horario}, posso te atender com {nomes_formatados}.\n\nPosso deixar com ela?"
        else:
            return f"Tenho sim. Para {servico} {periodo_str} em {data_str}, posso te atender com {nomes_formatados}.\n\nPosso deixar com ela?"
    else:
        # 2+ profissionais: oferece opções
        if com_horario and horario:
            return f"Tenho sim. Para {servico} {data_str} às {horario}, posso te atender com {nomes_formatados}.\n\nPrefere alguma delas?"
        else:
            return f"Tenho sim. Para {servico} {periodo_str} em {data_str}, posso te atender com {nomes_formatados}.\n\nPrefere alguma delas?"

async def responder_consulta_informativa(mensagem: str, user_id: str) -> str | None:
    mensagem_normalizada = unidecode(re.sub(r"[^\w\s]", " ", mensagem.lower())).strip()
    mensagem_normalizada = re.sub(r"\s+", " ", mensagem_normalizada)

    try:
        dono_id = await obter_id_dono(user_id)
    except Exception:
        dono_id = user_id

    # 📌 Listar todos os serviços disponíveis
    if "servi" in mensagem_normalizada and ("oferec" in mensagem_normalizada or "tem" in mensagem_normalizada):
        profissionais = (await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")) or {}
        servicos_set = set()
        for p in profissionais.values():
            for serv in p.get("servicos", []):
                servicos_set.add(serv.lower().strip())
        if servicos_set:
            lista = "\n".join([f"• {s.capitalize()}" for s in sorted(servicos_set)])
            return f"✨ Serviços oferecidos atualmente:\n\n{lista}"
        return "❌ Nenhum serviço foi encontrado no sistema."

    # 👥 Quem faz determinado serviço
    if "quem faz" in mensagem_normalizada or "qual profissional" in mensagem_normalizada:
        termo_busca = mensagem_normalizada

        # remove gatilhos da pergunta
        termo_busca = re.sub(r"\bquem faz\b", "", termo_busca).strip()
        termo_busca = re.sub(r"\bqual profissional\b", "", termo_busca).strip()
        termo_busca = re.sub(r"\bfaz\b", "", termo_busca).strip()
        termo_busca = re.sub(r"\s+", " ", termo_busca).strip()

        servico_normalizado = await encontrar_servico_mais_proximo(termo_busca, user_id)

        if servico_normalizado:
            profissionais = await buscar_profissionais_por_servico([servico_normalizado], user_id)
            if profissionais:
                nomes = "\n".join([f"• {p}" for p in profissionais])
                return f"👥 Profissionais que fazem *{servico_normalizado}*:\n\n{nomes}"
            return f"❌ Nenhum profissional encontrado para o serviço *{servico_normalizado}*."

        return "❌ Não consegui identificar o serviço que você quer consultar."

    # 💰 Preço de determinado serviço ou tabela completa
    palavras_chave_preco = [
        "quanto custa", "qual o valor", "qual é o valor", "qual é o preço", "preço",
        "valor", "quanto", "cobra", "custa", "quero saber o valor de", "quero saber o valor da",
        "quero saber quanto custa", "valores", "todos os valores", "tabela de preços", 
        "preços dos serviços", "valores dos serviços", "me traga todos os valores"
    ]

    if any(p in mensagem_normalizada for p in palavras_chave_preco):
        profissionais = (await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais")) or {}
        profissionais = profissionais.values()

        # Verifica se o usuário pediu TODOS OS VALORES
        if "todos os valores" in mensagem_normalizada or "me traga todos os valores" in mensagem_normalizada \
            or "tabela de preços" in mensagem_normalizada or "valores dos serviços" in mensagem_normalizada \
            or "preços dos serviços" in mensagem_normalizada or (mensagem_normalizada.strip() == "valores"):
            
            respostas = []
            for p in profissionais:
                nome = p.get("nome", "Profissional")
                precos = p.get("precos", {})
                for servico, preco in precos.items():
                    respostas.append(f"• {servico.capitalize()} com {nome}: R$ {preco}")
            if respostas:
                return f"💰 Tabela completa de valores:\n\n" + "\n".join(respostas)
            else:
                return "❌ Não encontrei preços cadastrados para nenhum serviço."

        # Caso seja pergunta por serviço específico
        padrao = r"(?:quanto custa|qual o valor|qual é o valor|qual é o preço|preço|valor|quanto|cobra|custa|quero saber o valor de|quero saber o valor da|quero saber quanto custa)?\s*(?:o|a|uma|um)?\s*(.*)"
        match = re.search(padrao, mensagem_normalizada)
        termo = match.group(1).strip() if match else ""

        # Limpa pontuações
        termo = termo.translate(str.maketrans('', '', string.punctuation)).strip()

        # Remove artigos finais se ainda houver
        termo = re.sub(r"^(o|a|uma|um)\s+", "", termo).strip()

        # Tokenização do termo para comparação inteligente
        termo_tokens = set(unidecode(termo.lower()).split())

        respostas = []
        for p in profissionais:
            nome = p.get("nome", "Profissional")
            precos = p.get("precos", {})
            for servico, preco in precos.items():
                servico_tokens = set(unidecode(servico.lower()).split())
                if termo_tokens & servico_tokens:  # se houver interseção de palavras
                    respostas.append(f"• {servico.capitalize()} com {nome}: R$ {preco}")

        if respostas:
            return f"💰 Valores encontrados:\n\n" + "\n".join(respostas)
        return "❌ Não encontrei preços para esse serviço."

    # 📅 Quem tem disponível em data/período
    palavras_chave_disponibilidade = [
        "quem tem disponivel", "quem tem disponível",
        "quem voce tem disponivel", "quem você tem disponível",
        "tem disponivel", "tem disponível",
        "quem esta disponivel", "quem está disponível"
    ]

    if any(p in mensagem_normalizada for p in palavras_chave_disponibilidade):
        # Extrair serviço
        servico = await encontrar_servico_mais_proximo(mensagem, user_id)
        if not servico:
            return "❌ Qual serviço você quer? (corte, escova, manicure...?)"

        # Extrair data
        dt = interpretar_data_e_hora(mensagem)
        if not dt:
            return "❌ Qual dia você quer? (hoje, amanhã, segunda...?)"

        # Extrair período → converter em janela horária
        periodo_str = ""
        if "manha" in mensagem_normalizada or "cedo" in mensagem_normalizada:
            hora_inicio, hora_fim = 8, 12
            periodo_str = "de manhã"
        elif "tarde" in mensagem_normalizada or "fim_tarde" in mensagem_normalizada:
            hora_inicio, hora_fim = 13, 18
            periodo_str = "à tarde"
        elif "noite" in mensagem_normalizada:
            hora_inicio, hora_fim = 18, 21
            periodo_str = "à noite"
        else:
            hora_inicio, hora_fim = 8, 21
            periodo_str = ""

        # Buscar profissionais que fazem o serviço
        profs_servico = await buscar_profissionais_por_servico([servico], user_id)
        if not profs_servico:
            return f"❌ Nenhum profissional encontrado para {servico}."

        # Determinar duração do serviço
        duracao = 30  # fallback seguro
        duracao_map = {
            "corte": 30,
            "escova": 40,
            "hidratacao": 40,
            "hidratação": 40,
            "coloracao": 90,
            "coloração": 90,
            "manicure": 30,
            "pedicure": 30,
            "unha gel": 60,
            "unhasegel": 60,
            "gel": 60
        }
        servico_norm = unidecode(servico.lower().strip())
        if servico_norm in duracao_map:
            duracao = duracao_map[servico_norm]
        else:
            # Tentar buscar em ServicosNegocio/{servico}
            try:
                servicos_negocio = (await buscar_subcolecao(f"Clientes/{dono_id}/ServicosNegocio")) or {}
                for serv_id, serv_dados in servicos_negocio.items():
                    serv_nome = unidecode((serv_dados.get("nome") or "").lower().strip())
                    if serv_nome == servico_norm:
                        duracao = serv_dados.get("duracao_minutos", 30)
                        break
            except Exception:
                pass

        # Iterar janela horária com passo de 30 minutos
        data_obj = dt.date()
        horarios_disponiveis = {}

        for hora_num in range(hora_inicio, hora_fim + 1):
            for minuto in [0, 30]:  # passo de 30 minutos
                if hora_num == hora_fim and minuto == 30:
                    continue  # não testar além do fim do período

                hora_str = f"{hora_num:02d}:{minuto:02d}"

                # Chamar motor determinístico
                disponiveis = await buscar_profissionais_disponiveis_no_horario(
                    user_id=user_id,
                    data=data_obj,
                    hora=hora_str,
                    duracao=duracao
                )

                # Filtrar apenas profissionais que fazem o serviço
                disponiveis_servico = {
                    nome: info for nome, info in disponiveis.items()
                    if nome in profs_servico
                }

                if disponiveis_servico:
                    horarios_disponiveis[hora_str] = disponiveis_servico

        # Usar formatador único padronizado
        if horarios_disponiveis:
            data_str = data_obj.strftime("%d/%m")
            # Extrair profissionais da primeira opção de horário
            primeira_hora, primeira_profs = next(iter(horarios_disponiveis.items()))
            profs_disponiveis = list(primeira_profs.keys())

            # Usar formatador padronizado
            return formatar_resposta_disponibilidade(
                servico=servico,
                data_str=data_str,
                periodo_str=periodo_str,
                profissionais_disponiveis=profs_disponiveis,
                com_horario=True,
                horario=primeira_hora
            )
        else:
            data_str = data_obj.strftime("%d/%m")
            return formatar_resposta_disponibilidade(
                servico=servico,
                data_str=data_str,
                periodo_str=periodo_str,
                profissionais_disponiveis=[]
            )

    return None  # Se não for uma intenção informativa
