# services/profissional_service.py

from services.firebase_service_async import buscar_subcolecao, obter_id_dono
from datetime import datetime, timedelta
import difflib
import unidecode
import re


async def buscar_profissionais_por_servico(servicos: list[str], user_id: str) -> dict:
    """
    Retorna um dicionário com os profissionais que oferecem TODOS os serviços listados.
    Resolve o dono primeiro, para suportar clientes falando com o bot.
    """
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    print(f"\n📥 Serviços solicitados: {servicos}")
    print(f"👥 Profissionais cadastrados: {list(profissionais.keys())}")

    profissionais_filtrados = {}

    for nome, dados in profissionais.items():
        prof_servicos = dados.get("servicos", [])
        if all(servico.lower() in [s.lower() for s in prof_servicos] for servico in servicos):
            profissionais_filtrados[nome] = dados

    return profissionais_filtrados


async def buscar_profissionais_disponiveis_no_horario(
    user_id: str,
    data: datetime.date,
    hora: str,
    duracao: int = 60
) -> dict:
    """
    Retorna os profissionais que estão disponíveis no horário e duração informados.
    Resolve o dono primeiro.
    """
    dono_id = await obter_id_dono(user_id)

    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}

    data_str = data.strftime("%Y-%m-%d")
    hora_inicio = datetime.strptime(f"{data_str} {hora}", "%Y-%m-%d %H:%M")
    hora_fim = hora_inicio + timedelta(minutes=duracao)

    profissionais_ocupados = set()

    print(f"\n📅 Verificando disponibilidade em {data.strftime('%d/%m/%Y')} às {hora}")
    print(f"📋 Eventos encontrados: {len(eventos)}")

    for evento in eventos.values():
        if evento.get("data") != data_str:
            continue

        print(f"  ⏰ Evento: {evento.get('descricao')} com {evento.get('profissional')}")
        print(f"     Início: {evento.get('hora_inicio')} | Fim: {evento.get('hora_fim')}")

        prof_evento = (evento.get("profissional") or "").lower()
        inicio_str = evento.get("hora_inicio")
        fim_str = evento.get("hora_fim")

        if not prof_evento or not inicio_str or not fim_str:
            continue

        # aqui no original você fazia fromisoformat só da hora, o que quebra — vamos montar com a data:
        inicio_evento = datetime.strptime(f"{data_str} {inicio_str}", "%Y-%m-%d %H:%M")
        fim_evento = datetime.strptime(f"{data_str} {fim_str}", "%Y-%m-%d %H:%M")

        conflito = not (hora_fim <= inicio_evento or hora_inicio >= fim_evento)
        print(f"     → Conflito? {conflito}")
        if conflito:
            profissionais_ocupados.add(prof_evento)

        print(f"❌ Ocupados: {profissionais_ocupados}")
        print(f"✅ Disponíveis: {[nome for nome in profissionais if nome.lower() not in profissionais_ocupados]}")

    disponiveis = {
        nome: dados for nome, dados in profissionais.items()
        if nome.lower() not in profissionais_ocupados
    }

    return disponiveis


async def obter_profissional_para_evento(user_id: str, descricao_evento: str) -> str | None:
    """
    Tenta identificar automaticamente um único profissional compatível com os serviços da descrição.
    Retorna o nome se houver apenas um compatível.
    """
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    descricao_lower = descricao_evento.lower()

    compativeis = []

    for nome, dados in profissionais.items():
        servicos = dados.get("servicos", [])
        if any(servico.lower() in descricao_lower for servico in servicos):
            compativeis.append(nome)

    if len(compativeis) == 1:
        return compativeis[0]
    else:
        return None


def gerar_mensagem_profissionais_disponiveis(
    servico: str,
    data: datetime.date,
    hora: str,
    disponiveis: dict,
    todos: dict
) -> str:
    data_str = data.strftime("%d/%m")
    print(f"\n📨 Gerando mensagem para o serviço '{servico}' em {data_str} às {hora}")
    print(f"   Profissionais disponíveis: {list(disponiveis.keys())}")
    print(f"   Todos cadastrados: {list(todos.keys())}")
    if disponiveis:
        lista = "\n".join([f"- {nome}: {', '.join(info.get('servicos', []))}" for nome, info in disponiveis.items()])
        return f"✅ Segue a lista de profissionais disponíveis para *{servico}* no dia *{data_str}* às *{hora}*:\n{lista}"
    else:
        if todos:
            lista = "\n".join([f"- {nome}: {', '.join(info.get('servicos', []))}" for nome, info in todos.items()])
            return (
                f"😕 No momento, ninguém está com horário disponível para *{servico}* no dia *{data_str}* às *{hora}*.\n\n"
                f"Mas estas profissionais realizam esse serviço — podemos tentar outro horário com elas:\n{lista}"
            )
        else:
            return "❌ Nenhum profissional cadastrado até o momento."


async def listar_servicos_cadastrados(user_id: str) -> list[str]:
    """Retorna a lista de todos os serviços oferecidos pelas profissionais."""
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    servicos = set()
    for dados in profissionais.values():
        for servico in dados.get("servicos", []):
            if isinstance(servico, str):
                servicos.add(servico)

    return sorted(servicos)


async def obter_precos_servico(user_id: str, servico: str, profissional: str | None = None):
    """Retorna o preço do ``servico`` para cada profissional ou para um profissional específico."""
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    servico_lower = servico.lower()

    def _buscar_preco(dados: dict) -> float | str | None:
        precos = dados.get("precos", {})
        for nome_serv, valor in precos.items():
            if isinstance(nome_serv, str) and nome_serv.lower() == servico_lower:
                return valor

        nomes_cadastrados = [n.lower() for n in precos.keys() if isinstance(n, str)]
        match = difflib.get_close_matches(servico_lower, nomes_cadastrados, n=1, cutoff=0.6)
        if match:
            nome_correspondente = match[0]
            for nome_serv, valor in precos.items():
                if isinstance(nome_serv, str) and nome_serv.lower() == nome_correspondente:
                    return valor

        return None

    if profissional:
        dados = profissionais.get(profissional)
        if dados:
            return _buscar_preco(dados)
        return None

    precos = {}
    for nome, dados in profissionais.items():
        preco = _buscar_preco(dados)
        if preco is not None:
            precos[nome] = preco

    return precos if precos else None


async def encontrar_servico_mais_proximo(texto_usuario: str, user_id: str = None) -> str | None:
    """
    Tenta encontrar o serviço mais próximo com base nas palavras do usuário.
    Se user_id for passado, busca serviços reais do banco. Caso contrário, usa um exemplo fixo.
    """
    texto = unidecode.unidecode(re.sub(r"[^\w\s]", " ", texto_usuario.lower()))

    servicos_disponiveis = set()

    if user_id:
        dono_id = await obter_id_dono(user_id)
        profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        for p in profissionais.values():
            for s in p.get("servicos", []):
                servicos_disponiveis.add(unidecode.unidecode(s.lower().strip()))
    else:
        servicos_disponiveis = {"corte", "escova", "manicure", "pedicure", "luzes", "botox capilar"}

    for servico in servicos_disponiveis:
        if servico in texto:
            return servico

    for palavra in texto.split():
        palavra = palavra.strip()
        for servico in servicos_disponiveis:
            if palavra in servico or servico in palavra:
                return servico

    return None


async def consultar_todos_precos(user_id: str) -> str:
    dono_id = await obter_id_dono(user_id)
    profissionais = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    resposta = "📋 *Lista completa de preços:*\n"

    for dados in profissionais.values():
        nome_prof = dados.get("nome", "Desconhecido")
        precos = dados.get("precos", {})
        if precos:
            resposta += f"\n*{nome_prof}*:\n"
            for servico, preco in precos.items():
                resposta += f"- {servico.capitalize()}: R$ {float(preco):.2f}\n"

    return resposta
