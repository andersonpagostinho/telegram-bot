# services/profissional_service.py

from services.firebase_service_async import buscar_subcolecao
from datetime import datetime, timedelta

async def buscar_profissionais_por_servico(servicos: list[str], user_id: str) -> dict:
    """
    Retorna um dicionário com os profissionais que oferecem TODOS os serviços listados.
    """
    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

    print(f"\n📥 Serviços solicitados: {servicos}")
    print(f"👥 Profissionais cadastrados: {list(profissionais.keys())}")

    profissionais_filtrados = {}

    for nome, dados in profissionais.items():
        prof_servicos = dados.get("servicos", [])
        if all(servico.lower() in [s.lower() for s in prof_servicos] for servico in servicos):
            profissionais_filtrados[nome] = dados

    return profissionais_filtrados

async def buscar_profissionais_disponiveis_no_horario(user_id: str, data: datetime.date, hora: str, duracao: int = 60) -> dict:
    """
    Retorna os profissionais que estão disponíveis no horário e duração informados.
    """
    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}

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

        prof_evento = evento.get("profissional", "").lower()
        inicio_str = evento.get("hora_inicio")
        fim_str = evento.get("hora_fim")

        if not prof_evento or not inicio_str or not fim_str:
            continue

        inicio_evento = datetime.fromisoformat(inicio_str)
        fim_evento = datetime.fromisoformat(fim_str)

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
    profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais") or {}
    descricao_lower = descricao_evento.lower()

    compativeis = []

    for nome, dados in profissionais.items():
        servicos = dados.get("servicos", [])
        if any(servico.lower() in descricao_lower for servico in servicos):
            compativeis.append(nome)

    if len(compativeis) == 1:
        return compativeis[0]  # 👍 único profissional compatível
    else:
        return None  # 🤷‍♂️ mais de um ou nenhum → precisa confirmar com o usuário

def gerar_mensagem_profissionais_disponiveis(servico: str, data: datetime.date, hora: str, disponiveis: dict, todos: dict) -> str:
    data_str = data.strftime("%d/%m")
    print(f"\n📨 Gerando mensagem para o serviço '{servico}' em {data_str} às {hora}")
    print(f"   Profissionais disponíveis: {list(disponiveis.keys())}")
    print(f"   Todos cadastrados: {list(todos.keys())}")
    data_str = data.strftime("%d/%m")
    if disponiveis:
        lista = "\n".join([f"- {nome}: {', '.join(info.get('servicos', []))}" for nome, info in disponiveis.items()])
        return f"✅ Segue a lista de profissionais disponíveis para *{servico}* no dia *{data_str}* às *{hora}*:\n{lista}"
    else:
        # Se nenhum disponível no horário, mas houver cadastrados, informe
        if todos:
            lista = "\n".join([f"- {nome}: {', '.join(info.get('servicos', []))}" for nome, info in todos.items()])
            return (
                f"😕 No momento, ninguém está com horário disponível para *{servico}* no dia *{data_str}* às *{hora}*.\n\n"
                f"Mas estas profissionais realizam esse serviço — podemos tentar outro horário com elas:\n{lista}"
            )
        else:
            return "❌ Nenhum profissional cadastrado até o momento."