import re
from unidecode import unidecode
from datetime import datetime, timedelta, date
from pytz import timezone
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_subcolecao,
    deletar_dado_em_path,
    obter_id_dono,
    buscar_dado_em_path,
    atualizar_dado_em_path,   # ✅ necessário para cancelar_evento
)
from services.notificacao_service import criar_notificacao_agendada
from utils.formatters import gerar_sugestoes_de_horario

FUSO_BR = timezone("America/Sao_Paulo")

# 🔁 Salvar ou atualizar um evento
async def salvar_evento(user_id: str, evento: dict, event_id: str = None) -> bool:
    try:
        # ✅ Verifica conflitos antes de salvar (chama direto, sem import interno)
        conflitos = await verificar_conflito(
            user_id=user_id,
            data=evento["data"],
            hora_inicio=evento["hora_inicio"],
            duracao_min=evento.get("duracao", 60),
            profissional=evento.get("profissional", "")
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
        from services.notificacao_service import criar_notificacao_agendada

        cliente_id = (evento.get("cliente_id") or "").strip()
        data_ev = evento.get("data")
        hora_ev = evento.get("hora_inicio")
        descricao_ev = evento.get("descricao", "Compromisso")

        # user_id_efetivo = quem está criando/operando (dono/atendente)
        # garanta que essa variável exista no escopo; se não existir, use user_id
        origem_user = user_id_efetivo if "user_id_efetivo" in locals() else user_id

        if cliente_id and cliente_id != origem_user and data_ev and hora_ev:
            try:
                await criar_notificacao_agendada(
                    user_id=origem_user,              # quem originou a criação
                    descricao=descricao_ev,
                    data=data_ev,
                    hora_inicio=hora_ev,
                    canal="telegram",
                    minutos_antes=30,
                    destinatario_user_id=cliente_id,  # 🔑 notifica o CLIENTE
                    alvo_evento={"data": data_ev, "hora_inicio": hora_ev, "descricao": descricao_ev}
                )
            except Exception as e:
                print(f"⚠️ Erro ao agendar notificação para cliente {cliente_id}: {e}")

        return True
    except Exception as e:
        print(f"❌ Erro ao salvar evento: {e}")
        return False

# 🔎 Buscar eventos por data (hoje, amanhã, etc.)
async def buscar_eventos_por_intervalo(user_id: str, dias: int = 0, semana: bool = False, dia_especifico: date | None = None):
    from services.firebase_service_async import buscar_dado_em_path, obter_id_dono

    try:
        # 🧠 Ajuste híbrido de ID se for cliente
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
        user_id_efetivo = user_id

        if dados_usuario:
            tipo = dados_usuario.get("tipo_usuario", "cliente")
            modo = dados_usuario.get("modo_uso", "")
            if tipo == "cliente" or modo == "atendimento_cliente":
                user_id_efetivo = await obter_id_dono(user_id)

        eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
        hoje = datetime.now().date()

        # 📆 Define intervalo de busca
        if dia_especifico:
            data_inicio = data_fim = dia_especifico
        elif semana:
            proxima_semana = hoje + timedelta(days=(7 - hoje.weekday()))
            data_inicio = proxima_semana
            data_fim = proxima_semana + timedelta(days=6)
        else:
            data_inicio = hoje + timedelta(days=dias)
            data_fim = data_inicio

        resultado = []

        for evento in eventos.values():
            # ❗ Ignora cancelados
            if (evento.get("status") or "").lower() == "cancelado":
                continue

            data_str = evento.get("data")
            if not data_str:
                continue

            try:
                data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if data_inicio <= data_evento <= data_fim:
                resultado.append(evento)

        return resultado

    except Exception as e:
        print(f"❌ Erro ao buscar eventos: {e}")
        return []

async def cancelar_evento(user_id: str, event_id: str) -> bool:
    """
    Marca um evento como cancelado (soft delete).
    Resolve user_id efetivo (dono) quando a chamada vier do cliente.
    """
    try:
        # resolve o id efetivo como nos outros métodos
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
        user_id_efetivo = user_id
        if dados_usuario:
            tipo = dados_usuario.get("tipo_usuario", "cliente")
            modo = dados_usuario.get("modo_uso", "")
            if tipo == "cliente" or modo == "atendimento_cliente":
                user_id_efetivo = await obter_id_dono(user_id)

        path = f"Clientes/{user_id_efetivo}/Eventos/{event_id}"
        payload = {
            "status": "cancelado",
            "cancelado_em": datetime.now(FUSO_BR).isoformat()
        }
        await atualizar_dado_em_path(path, payload)
        return True
    except Exception as e:
        print(f"❌ cancelar_evento: {e}")
        return False

async def cancelar_evento_por_texto(user_id: str, termo: str):
    """
    Encontra por texto e cancela.
    Se houver 1 candidato -> cancela direto.
    Se houver vários -> retorna lista para confirmação (quem guarda estado é o handler).
    """
    candidatos = await buscar_eventos_por_termo_avancado(user_id, termo)

    if not candidatos:
        return False, "❌ Não encontrei nenhum evento correspondente ao que você quer cancelar."

    if len(candidatos) == 1:
        eid, ev = candidatos[0]
        ok = await cancelar_evento(user_id, eid)
        if not ok:
            return False, "❌ Tive um problema ao cancelar no sistema."
        desc = ev.get("descricao", "Evento")
        data = ev.get("data", "")
        hora = ev.get("hora_inicio", "")
        return True, f"✅ {desc} em {data} às {hora} foi cancelado e liberou o horário."

    # Vários candidatos — deixe o handler listar e pedir número
    linhas = []
    for i, (eid, ev) in enumerate(candidatos, start=1):
        linhas.append(f"{i}) {ev.get('descricao','(sem título)')} — {ev.get('data','????-??-??')} às {ev.get('hora_inicio','??:??')}")

    return False, "Encontrei mais de um. Envie o número da opção para cancelar:\n" + "\n".join(linhas)


# 🔍 Verificar conflito de horário para um novo evento
async def verificar_conflito(user_id: str, data: str, hora_inicio: str, duracao_min: int = 60, profissional: str = "") -> list:
    from datetime import datetime, timedelta

    try:
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
        user_id_efetivo = await obter_id_dono(user_id) if dados_usuario else user_id

        eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
        inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
        fim_novo = inicio_novo + timedelta(minutes=duracao_min)

        conflitos = []
        for ev in eventos.values():
             # ❗ Ignora cancelados
            if (ev.get("status") or "").lower() == "cancelado":
                continue

            try:
                data_evento = datetime.strptime(ev.get("data", ""), "%Y-%m-%d").date()
            except:
                continue

            if data_evento != inicio_novo.date():
                continue
            if not ev.get("profissional"):
                continue
            if ev.get("profissional", "").lower() != profissional.lower():
                continue
            try:
                ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
                ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
                if inicio_novo < ev_fim and fim_novo > ev_inicio:

                    print(f"⛔ Conflito detectado com evento existente: {ev}")
                    print(f"📅 Horário novo: {inicio_novo} até {fim_novo}")
                    print(f"📅 Evento conflitante: {ev_inicio} até {ev_fim}")

                    conflitos.append((ev_inicio, ev_fim))
            except Exception as e:
                print(f"⚠️ Erro ao interpretar evento existente: {ev} — {e}")
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

def _normaliza_txt(s: str) -> str:
    return unidecode((s or "").strip().lower())

def _interpreta_data_relativa(termo: str, hoje: datetime.date):
    """
    Retorna (data_inicial, data_final) se houver termo relativo (hoje/amanhã).
    Caso contrário, (None, None).
    """
    t = unidecode((termo or "").strip().lower())
    if "hoje" in t:
        return hoje, hoje
    if "amanha" in t:  # já normalizado sem acento
        d = hoje + timedelta(days=1)
        return d, d
    return None, None

def _extrai_data_explicita(termo: str):
    t = (termo or "")
    padroes = [
        r"\b(\d{2})[/-](\d{2})[/-](\d{4})\b",   # DD/MM/YYYY
        r"\b(\d{4})-(\d{2})-(\d{2})\b",         # YYYY-MM-DD
        r"\b(\d{2})[/-](\d{2})\b"               # DD/MM (assume ano atual)
    ]
    for p in padroes:
        m = re.search(p, t)
        if m:
            try:
                if len(m.groups()) == 3 and p.startswith(r"\b(\d{2})"):
                    d, mth, y = map(int, m.groups())
                    return datetime(y, mth, d).date()
                if len(m.groups()) == 3 and p.startswith(r"\b(\d{4})"):
                    y, mth, d = map(int, m.groups())
                    return datetime(y, mth, d).date()
                if len(m.groups()) == 2:
                    d, mth = map(int, m.groups())
                    y = datetime.now().year
                    return datetime(y, mth, d).date()
            except Exception:
                return None
    return None

async def buscar_eventos_por_termo_avancado(user_id: str, termo: str):
    """
    Retorna lista [(event_id, evento)] que combinem com:
      - palavras úteis do texto (ex.: 'corte', 'unha', 'reuniao', 'carla')
      - data relativa ('hoje', 'amanha') ou explícita (20/10, 2025-10-21)
    Ignora eventos cancelados.
    """
    termo_norm = unidecode((termo or "").strip().lower())
    if not termo_norm:
        return []

    # resolve id efetivo (dono)
    dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
    user_id_efetivo = user_id
    if dados_usuario:
        tipo = dados_usuario.get("tipo_usuario", "cliente")
        modo = dados_usuario.get("modo_uso", "")
        if tipo == "cliente" or modo == "atendimento_cliente":
            user_id_efetivo = await obter_id_dono(user_id)

    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
    hoje = datetime.now().date()

    # datas
    d1, d2 = _interpreta_data_relativa(termo_norm, hoje)
    data_exp = _extrai_data_explicita(termo)
    if data_exp:
        d1 = d2 = data_exp

    # stopwords + verbos de intenção + palavras de data que NÃO devem pesar no match textual
    STOP = {"o","a","os","as","um","uma","de","do","da","dos","das","com","no","na","nos","nas","para","pro","pra"}
    INTENCOES = {"cancelar","cancela","cancele","remover","excluir","apagar","tirar","tira"}
    DATAS = {"hoje","amanha"}  # já sem acento

    tokens_util = [p for p in re.split(r"\s+", termo_norm)
                   if p and p not in STOP and p not in INTENCOES and p not in DATAS]

    def _match(ev: dict) -> bool:
        if (ev.get("status") or "").lower() == "cancelado":
            return False

        blob = unidecode((" ".join([
            str(ev.get("descricao","")),
            str(ev.get("profissional","")),
            str(ev.get("data","")),
            str(ev.get("hora_inicio","")),
            str(ev.get("hora_fim","")),
        ])).strip().lower())

        # precisa conter TODAS as tokens úteis (se tiverem sobrado)
        if tokens_util:
            for p in tokens_util:
                # ignore tokens muito curtos (<=2) para não falsear
                if len(p) <= 2:
                    continue
                if p not in blob:
                    return False

        # data bate?
        if d1 and d2:
            try:
                data_ev = datetime.strptime(ev.get("data",""), "%Y-%m-%d").date()
                if not (d1 <= data_ev <= d2):
                    return False
            except Exception:
                return False

        return True

    candidatos = []
    for eid, ev in eventos.items():
        if not isinstance(ev, dict):
            continue
        if _match(ev):
            candidatos.append((eid, ev))

    # ordenar por data/hora (mais próximo primeiro)
    def _key(item):
        _, e = item
        try:
            return datetime.fromisoformat(f"{e['data']}T{e['hora_inicio']}:00")
        except Exception:
            return datetime.max

    candidatos.sort(key=_key)
    return candidatos


# 🧾 Formatador para exibição
def formatar_evento(evento: dict) -> str:
    data = evento.get("data", "???")
    inicio = evento.get("hora_inicio", "??:??")
    fim = evento.get("hora_fim", "??:??")
    desc = evento.get("descricao", "Sem título")
    return f"📝 {desc} – {data} das {inicio} às {fim}"

async def verificar_conflito_e_sugestoes_profissional(
    user_id: str,
    data: str,
    hora_inicio: str,
    duracao_min: int,
    profissional: str,
    servico: str,
    event_id: str = None
) -> dict:
    from datetime import datetime, timedelta
    from unidecode import unidecode

    # 1. Converte a hora para datetime
    inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
    fim_novo = inicio_novo + timedelta(minutes=duracao_min)

    # 2. Ajusta para modo híbrido
    dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
    user_id_efetivo = await obter_id_dono(user_id) if dados_usuario else user_id

    # 3. Busca eventos e profissionais
    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
    profissionais = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Profissionais") or {}

    # 🧪 Diagnóstico
    import json
    print(f"🧪 Dados recebidos: user_id={user_id}, data={data}, hora_inicio={hora_inicio}, duracao_min={duracao_min},        profissional={profissional}, servico={servico}")
    print(f"📦 Eventos existentes:\n{json.dumps(eventos, indent=2, default=str)}")

    # 🔄 Normaliza o nome do profissional para evitar conflitos por acento, espaço ou maiúscula
    prof_norm = unidecode(profissional.strip().lower())

    # 4. Verifica conflitos para o profissional
    ocupados = []
    for eid, ev in eventos.items():
        if eid == event_id:
            continue

        try:
            data_evento = datetime.strptime(ev.get("data", ""), "%Y-%m-%d").date()
            if data_evento != inicio_novo.date():
                continue
        except:
            continue

        ev_prof = unidecode(ev.get("profissional", "").strip().lower())
        if ev_prof != prof_norm:
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
        if unidecode(p.get("nome", "").strip().lower()) == prof_norm:
            continue
        if servico.lower() in [s.lower() for s in p.get("servicos", [])]:
            conflitos = []
            for eid, ev in eventos.items():
                if eid == event_id:
                    continue
                try:
                    data_evento = datetime.strptime(ev.get("data", ""), "%Y-%m-%d").date()
                    if data_evento != inicio_novo.date():
                        continue
                except:
                    continue

                ev_prof_alt = unidecode(ev.get("profissional", "").strip().lower())
                if ev_prof_alt != unidecode(p.get("nome", "").strip().lower()):
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
    print(f"✅ Resultado: conflito={bool(ocupados)}, sugestões={sugestoes}, alternativo={alternativo}")
    return {
        "conflito": bool(ocupados),
        "sugestoes": sugestoes,
        "profissional_alternativo": alternativo
    }
