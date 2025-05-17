from datetime import datetime, timedelta
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_subcolecao,
    deletar_dado_em_path,
    obter_id_dono,
    buscar_dado_em_path
)
from services.notificacao_service import criar_notificacao_agendada
from utils.formatters import gerar_sugestoes_de_horario

# 🔁 Salvar ou atualizar um evento
async def salvar_evento(user_id: str, evento: dict, event_id: str = None) -> bool:
    try:
        # ✅ Verifica conflitos antes de salvar
        from .event_service_async import verificar_conflito
        conflitos = await verificar_conflito(
            user_id=user_id,
            data=evento["data"],
            hora_inicio=evento["hora_inicio"],
            duracao_min=evento.get("duracao", 60)
        )
        if conflitos:
            print("⛔ Conflito de horário detectado. Evento não será salvo.")
            return False

        if not event_id:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            nome_base = evento.get("descricao", "evento").replace(" ", "_").lower()
            event_id = f"{timestamp}_{nome_base}"

        evento.setdefault("criado_em", datetime.now().isoformat())
        evento.setdefault("confirmado", False)
        evento.setdefault("link", "")
        evento.setdefault("status", "pendente")
        evento.setdefault("cliente_id", user_id)  # 👈 garante que sabemos quem é o cliente

        # 🧠 Decide onde salvar (pessoal ou empresa)
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
        user_id_efetivo = user_id

        if dados_usuario:
            tipo = dados_usuario.get("tipo_usuario", "cliente")
            modo = dados_usuario.get("modo_uso", "")
            if tipo == "cliente" or modo == "atendimento_cliente":
                user_id_efetivo = await obter_id_dono(user_id)

        path = f"Clientes/{user_id_efetivo}/Eventos/{event_id}"
        await salvar_dado_em_path(path, evento)

        print(f"✅ Evento salvo para {user_id_efetivo} com ID {event_id}: {evento}")

        # 🔔 Enviar notificação só para o cliente (e não para o dono)
        cliente_id = evento.get("cliente_id")
        if cliente_id and cliente_id != user_id_efetivo:
            try:
                await criar_notificacao_agendada(
                    user_id=cliente_id,
                    descricao=evento.get("descricao", "Compromisso"),
                    data=evento.get("data"),
                    hora_inicio=evento.get("hora_inicio"),
                    canal="telegram",
                    minutos_antes=30
                )
            except Exception as e:
                print(f"⚠️ Erro ao agendar notificação: {e}")

        return True
    except Exception as e:
        print(f"❌ Erro ao salvar evento: {e}")
        return False

# 🔎 Buscar eventos por data (hoje, amanhã, etc.)
async def buscar_eventos_por_intervalo(user_id: str, dias: int = 0, semana: bool = False, dia_especifico: datetime.date = None):
    from services.firebase_service_async import buscar_dado_em_path, obter_id_dono

    try:
        # 🧠 Ajuste híbrido de ID se for cliente
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
        user_id_efetivo = user_id
        filtrar_por_cliente = False

        if dados_usuario:
            tipo = dados_usuario.get("tipo_usuario", "cliente")
            modo = dados_usuario.get("modo_uso", "")
            if tipo == "cliente" or modo == "atendimento_cliente":
                user_id_efetivo = await obter_id_dono(user_id)
                filtrar_por_cliente = True

        eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
        hoje = datetime.now().date()

        if dia_especifico:
            data_inicio = dia_especifico
            data_fim = dia_especifico
        elif semana:
            # Avança para o início da próxima semana (segunda-feira que vem)
            proxima_semana = hoje + timedelta(days=(7 - hoje.weekday()))  # próxima segunda
            data_inicio = proxima_semana
            data_fim = proxima_semana + timedelta(days=6)  # domingo
        else:
            data_inicio = hoje + timedelta(days=dias)
            data_fim = data_inicio

        resultado = []

        for evento in eventos.values():
            data_str = evento.get("data")
            if not data_str:
                continue

            try:
                data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            # 🧠 Filtra por cliente se for o caso
            #if filtrar_por_cliente and evento.get("cliente_id") != user_id:
            #    continue

            if semana:
                if data_inicio <= data_evento <= data_fim:
                    resultado.append(formatar_evento(evento))
            else:
                if data_evento == data_alvo:
                    resultado.append(formatar_evento(evento))

        return resultado
    except Exception as e:
        print(f"❌ Erro ao buscar eventos: {e}")
        return []

# 🔍 Verificar conflito de horário para um novo evento
async def verificar_conflito(user_id: str, data: str, hora_inicio: str, duracao_min: int = 60) -> list:
    from datetime import datetime, timedelta

    try:
        # Ajusta para modo híbrido
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
        user_id_efetivo = user_id
        if dados_usuario:
            tipo = dados_usuario.get("tipo_usuario", "cliente")
            modo = dados_usuario.get("modo_uso", "")
            if tipo == "cliente" or modo == "atendimento_cliente":
                user_id_efetivo = await obter_id_dono(user_id)

        # Pega os eventos do dia
        eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
        inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
        fim_novo = inicio_novo + timedelta(minutes=duracao_min)

        conflitos = []
        for ev in eventos.values():
            if ev.get("data") != data:
                continue
            try:
                ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
                ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
                if inicio_novo < ev_fim and fim_novo > ev_inicio:
                    conflitos.append((ev_inicio, ev_fim))
            except:
                continue

        return conflitos
    except Exception as e:
        print(f"❌ Erro ao verificar conflitos: {e}")
        return []

# 🧹 Deletar um evento (opcional)
async def deletar_evento(user_id: str, event_id: str) -> bool:
    from services.firebase_service_async import buscar_dado_em_path, obter_id_dono

    try:
        # 🧠 Ajuste híbrido de ID se for cliente
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
        if dados_usuario:
            tipo = dados_usuario.get("tipo_usuario", "cliente")
            modo = dados_usuario.get("modo_uso", "")
            if tipo == "cliente" or modo == "atendimento_cliente":
                user_id = await obter_id_dono(user_id)

        await deletar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}")
        return True
    except Exception as e:
        print(f"❌ Erro ao deletar evento: {e}")
        return False

# 🧾 Formatador para exibição
def formatar_evento(evento: dict) -> str:
    data = evento.get("data", "???")
    inicio = evento.get("hora_inicio", "??:??")
    fim = evento.get("hora_fim", "??:??")
    desc = evento.get("descricao", "Sem título")
    return f"📝 {desc} – {data} das {inicio} às {fim}"

async def verificar_conflito_e_sugestoes_profissional(user_id: str, data: str, hora_inicio: str, duracao_min: int, profissional: str, servico: str) -> dict:
    from datetime import datetime, timedelta

    # 1. Converte a hora para datetime
    inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
    fim_novo = inicio_novo + timedelta(minutes=duracao_min)

    # 2. Ajusta para modo híbrido
    dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
    user_id_efetivo = await obter_id_dono(user_id) if dados_usuario else user_id

    # 3. Busca eventos e profissionais
    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
    profissionais = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Profissionais") or {}

    # 4. Verifica conflitos para o profissional
    ocupados = []
    for ev in eventos.values():
        if ev.get("data") != data:
            continue
        if profissional.lower() not in ev.get("descricao", "").lower():
            continue
        try:
            ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
            ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
            if inicio_novo < ev_fim and fim_novo > ev_inicio:
                ocupados.append((ev_inicio, ev_fim))
        except:
            continue

    # 5. Gera sugestões
    sugestoes = gerar_sugestoes_de_horario(inicio_novo, ocupados, duracao_min)

    # 6. Verifica outro profissional compatível
    alternativo = None
    for p in profissionais.values():
        if p.get("nome", "").lower() == profissional.lower():
            continue
        if servico.lower() in [s.lower() for s in p.get("servicos", [])]:
            # verifica agenda dele
            conflitos = []
            for ev in eventos.values():
                if ev.get("data") != data:
                    continue
                if p.get("nome", "").lower() not in ev.get("descricao", "").lower():
                    continue
                try:
                    ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
                    ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
                    if inicio_novo < ev_fim and fim_novo > ev_inicio:
                        conflitos.append((ev_inicio, ev_fim))
                except:
                    continue
            if not conflitos:
                alternativo = p.get("nome")
                break

    return {
        "conflito": bool(ocupados),
        "sugestoes": sugestoes,
        "profissional_alternativo": alternativo
    }

