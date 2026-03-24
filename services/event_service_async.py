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
        # ✅ Verifica conflitos antes de salvar
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

        # ✅ ID idempotente por slot (evita duplicar ao confirmar/retentar)
        if not event_id:
            base_id = f"{evento.get('cliente_id')}_{evento.get('profissional')}_{evento.get('data')}_{evento.get('hora_inicio')}"
            event_id = base_id.replace(" ", "_").lower()

        evento.setdefault("criado_em", datetime.now().isoformat())
        evento.setdefault("link", "")
        evento.setdefault("cliente_id", user_id)  # 👈 garante que sabemos quem é o cliente

        # ✅ status/confirmado coerentes: se vier confirmado=True, nasce confirmado
        confirmado_flag = bool(evento.get("confirmado") is True)
        if confirmado_flag:
            evento["confirmado"] = True
            evento["status"] = "confirmado"
            evento.setdefault("confirmado_em", datetime.now(FUSO_BR).isoformat())
        else:
            evento.setdefault("confirmado", False)
            evento.setdefault("status", "pendente")

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
        cliente_id = (evento.get("cliente_id") or "").strip()
        data_ev = evento.get("data")
        hora_ev = evento.get("hora_inicio")
        descricao_ev = evento.get("descricao", "Compromisso")

        origem_user = user_id_efetivo

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
async def buscar_eventos_por_intervalo(
    user_id: str,
    dias: int = 0,
    semana: bool = False,
    dia_especifico: date | None = None
):
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

        # ✅ Preserva o event_id no retorno (essencial para updates/idempotência)
        for event_id, evento in eventos.items():
            if not isinstance(evento, dict):
                continue

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
                ev_out = dict(evento)
                ev_out["event_id"] = event_id
                resultado.append(ev_out)

        return resultado

    except Exception as e:
        print(f"❌ Erro ao buscar eventos: {e}")
        return []


async def cancelar_evento(user_id: str, event_id: str) -> bool:
    """
    Marca um evento como cancelado (soft delete).
    Resolve user_id efetivo (dono) quando a chamada vier do cliente.
    Após cancelar, aciona o motor de encaixe para preencher o buraco.
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

        # 1) buscar dados do evento ANTES de cancelar (para saber qual buraco abriu)
        ev = await buscar_dado_em_path(path) or {}
        data = ev.get("data")
        hora = ev.get("hora_inicio")
        duracao = ev.get("duracao") or 60
        # opcional: se você tiver esses campos
        servico = ev.get("servico") or ev.get("descricao")
        profissional = ev.get("profissional")

        # 2) cancelar
        payload = {
            "status": "cancelado",
            "cancelado_em": datetime.now(FUSO_BR).isoformat()
        }
        await atualizar_dado_em_path(path, payload)

        # ✅ HOTFIX: cancelar deve apenas marcar status e liberar horário
        # (motor de encaixe volta depois, mas sem criar evento automaticamente)
        return True

        # 3) acionar motor de encaixe (sem quebrar o cancelamento se encaixe falhar)
        try:
            from services.encaixe_service import solicitar_encaixe

            if data and hora:
                # montar datetime completo no fuso
                dt_desejado = FUSO_BR.localize(
                    datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
                )

                # ✅ decide pelo modo do DONO/NEGÓCIO (user_id_efetivo)
                dados_dono = await buscar_dado_em_path(f"Clientes/{user_id_efetivo}") or {}
                modo_dono = (dados_dono.get("modo_uso") or "").strip().lower()

                # ✅ flag explícita (você pode trocar por config depois)
                if modo_dono == "auto_encaixe_ativo":
                    await solicitar_encaixe(
                        user_id=user_id_efetivo,              # dono/negócio
                        descricao=servico or ev.get("descricao") or "Encaixe",
                        profissional=profissional,
                        duracao_min=int(duracao),
                        dt_desejado=dt_desejado,
                        solicitante_user_id=user_id,          # quem solicitou (cliente que cancelou)
                    )
                else:
                    print(f"ℹ️ auto_encaixe desativado (modo_uso={modo_dono})", flush=True)

        except Exception as e:
            print(f"⚠️ motor de encaixe falhou após cancelamento: {e}", flush=True)

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

    # ❌ Nenhum encontrado
    if not candidatos:
        return False, "❌ Não encontrei nenhum evento correspondente ao que você quer cancelar.", []

    # ✅ Apenas 1 → cancela direto
    if len(candidatos) == 1:
        eid, ev = candidatos[0]

        ok = await cancelar_evento(user_id, eid)
        if not ok:
            return False, "❌ Tive um problema ao cancelar no sistema.", []

        desc = ev.get("descricao", "Evento")
        data = ev.get("data", "")
        hora = ev.get("hora_inicio", "")

        return True, f"✅ {desc} em {data} às {hora} foi cancelado e liberou o horário.", []

    # ⚠️ Vários candidatos → precisa escolher
    linhas = []
    for i, (eid, ev) in enumerate(candidatos, start=1):
        linhas.append(
            f"{i}) {ev.get('descricao','(sem título)')} — {ev.get('data','????-??-??')} às {ev.get('hora_inicio','??:??')}"
        )

    msg = "Encontrei mais de um. Envie o número da opção para cancelar:\n" + "\n".join(linhas)

    # ✅ RETORNA também candidatos (ESSENCIAL)
    return False, msg, candidatos


# 🔍 Verificar conflito de horário para um novo evento
async def verificar_conflito(
    user_id: str,
    data: str,
    hora_inicio: str,
    duracao_min: int = 60,
    profissional: str = "",
    cliente_id: str = "",
    event_id: str | None = None,
) -> list:
    try:
        dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
        user_id_efetivo = user_id

        tipo = (dados_usuario.get("tipo_usuario") or "cliente").strip().lower()
        modo = (dados_usuario.get("modo_uso") or "").strip().lower()

        if tipo == "cliente" or modo == "atendimento_cliente":
            user_id_efetivo = await obter_id_dono(user_id)

        eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
        inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
        fim_novo = inicio_novo + timedelta(minutes=duracao_min)

        conflitos = []

        cliente_novo = (str(cliente_id or "")).strip()
        prof_novo = (profissional or "").strip().lower()

        for eid, ev in (eventos or {}).items():
            # ❗ Ignora cancelados
            status = (ev.get("status") or "").strip().lower()
            if status == "cancelado":
                continue

            # ✅ ignorar o próprio evento (quando event_id conhecido)
            if event_id and eid == event_id:
                continue

            # ✅ idempotência: mesmo cliente + mesmo slot não é conflito
            if (
                cliente_novo
                and str(ev.get("cliente_id") or "").strip() == cliente_novo
                and (ev.get("profissional") or "").strip().lower() == prof_novo
                and ev.get("data") == data
                and ev.get("hora_inicio") == hora_inicio
            ):
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
        status = (ev.get("status") or "").strip().lower()
        if status == "cancelado":
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


async def tentar_split_simples(
    user_id: str,
    data: str,
    hora_inicio: str,
    servicos: list,
    profissional_preferido: str,
    event_id: str = None,
    grade_min: int = 10,
    buffer_inicio_min: int = 5,
    buffer_fim_min: int = 5,
    espera_max_min: int = 20
):
    """
    Split simples para 2 serviços, em sequência, com até 2 profissionais.
    Regras:
      - manter horário pedido (início do serviço 1 fixo em data+hora_inicio)
      - depois prioriza profissional_preferido no serviço 1 (se fizer)
      - serviço 2 começa no máximo espera_max_min após terminar o serviço 1
      - grade de 10 min para início do serviço 2
      - buffer do pacote: +5 no começo (antes do serv1) e +5 no fim (depois do serv2)
    Retorna dict plano ou None.
    """
    from datetime import datetime, timedelta
    from unidecode import unidecode

    if not isinstance(servicos, list) or len(servicos) != 2:
        return None

    s1 = str(servicos[0]).strip()
    s2 = str(servicos[1]).strip()
    if not s1 or not s2:
        return None

    # --- helpers ---
    def ceil_grade(dt: datetime, g: int) -> datetime:
        dt = dt.replace(second=0, microsecond=0)
        r = dt.minute % g
        if r == 0:
            return dt
        return dt + timedelta(minutes=(g - r))

    def conflita(inicio: datetime, fim: datetime, ocupados: list[tuple[datetime, datetime]]) -> bool:
        return any(inicio < ev_fim and fim > ev_inicio for ev_inicio, ev_fim in ocupados)

    def duracao_servico_min(servico_nome: str, prof_data: dict) -> int:
        # 1) tenta buscar no doc do profissional se existir
        # Ex.: {"duracoes": {"corte": 60, "hidratação": 45}} (você pode padronizar isso depois)
        serv_norm = unidecode(servico_nome.strip().lower())
        for key in ("duracoes", "duracao_servicos", "duracao_por_servico"):
            dmap = prof_data.get(key)
            if isinstance(dmap, dict):
                for k, v in dmap.items():
                    if unidecode(str(k).strip().lower()) == serv_norm:
                        try:
                            return int(v)
                        except Exception:
                            pass

        # 2) fallback padrão (AJUSTE depois com seus dados reais)
        base = {
            "escova": 30,
            "hidratação": 45,
            "hidratacao": 45,
            "corte": 60,
            "coloração": 90,
            "coloracao": 90,
            "luzes": 120,
            "botox capilar": 120,
            "manicure": 30,
            "pedicure": 30,
            "unha gel": 60,
        }
        return int(base.get(serv_norm, 60))

    # --- modo híbrido (dono efetivo) ---
    dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}")
    user_id_efetivo = await obter_id_dono(user_id) if dados_usuario else user_id

    # --- carregar dados ---
    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
    profissionais = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Profissionais") or {}

    # --- parser de intervalos (reusa o padrão robusto) ---
    from datetime import datetime as _dt, timedelta as _td

    def _parse_event_interval(ev: dict):
        try:
            hi = ev.get("hora_inicio")
            hf = ev.get("hora_fim")

            # ISO
            if isinstance(hi, str) and "T" in hi:
                ini = _dt.fromisoformat(hi)
                if isinstance(hf, str) and "T" in hf:
                    fim = _dt.fromisoformat(hf)
                else:
                    dur = ev.get("duracao") or ev.get("duracao_min") or 0
                    fim = ini + _td(minutes=int(dur) if dur else 0)
                return ini, fim

            # data + HH:MM
            d = ev.get("data")
            if d and hi and hf:
                ini = _dt.strptime(f"{d} {hi}", "%Y-%m-%d %H:%M")
                fim = _dt.strptime(f"{d} {hf}", "%Y-%m-%d %H:%M")
                return ini, fim

            return None, None
        except Exception:
            return None, None

    # --- construir ocupados por profissional (somente do dia) ---
    dia_dt = datetime.fromisoformat(f"{data}T00:00:00").date()
    ocupados_por_prof = {}

    for eid, ev in eventos.items():
        if event_id and eid == event_id:
            continue

        ev_prof = unidecode(str(ev.get("profissional", "")).strip().lower())
        if not ev_prof:
            continue

        ev_ini, ev_fim = _parse_event_interval(ev)
        if not ev_ini or not ev_fim:
            continue
        if ev_ini.date() != dia_dt:
            continue

        ocupados_por_prof.setdefault(ev_prof, []).append((ev_ini, ev_fim))

    # --- candidatos por serviço ---
    def profs_que_fazem(servico_nome: str) -> list[dict]:
        sn = unidecode(servico_nome.strip().lower())
        out = []
        for p in profissionais.values():
            nome = (p.get("nome") or "").strip()
            if not nome:
                continue
            servs = p.get("servicos") or []
            servs_norm = [unidecode(str(s).strip().lower()) for s in servs]
            if sn in servs_norm:
                out.append(p)
        return out

    cand1 = profs_que_fazem(s1)
    cand2 = profs_que_fazem(s2)
    if not cand1 or not cand2:
        return None

    pref_norm = unidecode((profissional_preferido or "").strip().lower())

    # ordena candidatos do serviço 1: preferido primeiro, depois demais
    cand1_sorted = sorted(
        cand1,
        key=lambda p: 0 if unidecode((p.get("nome") or "").strip().lower()) == pref_norm else 1
    )

    inicio1_serv = datetime.fromisoformat(f"{data}T{hora_inicio}")

    for prof1_data in cand1_sorted:
        prof1_nome = (prof1_data.get("nome") or "").strip()
        if not prof1_nome:
            continue
        prof1_norm = unidecode(prof1_nome.lower())

        d1 = duracao_servico_min(s1, prof1_data)

        # buffer do pacote: +5 antes do primeiro serviço (entra na checagem)
        inicio1_chk = inicio1_serv - timedelta(minutes=buffer_inicio_min)
        fim1_serv = inicio1_serv + timedelta(minutes=d1)

        if conflita(inicio1_chk, fim1_serv, ocupados_por_prof.get(prof1_norm, [])):
            continue

        # serviço 2 começa após fim1_serv, alinhado na grade, com espera <= 20
        base2 = ceil_grade(fim1_serv, grade_min)
        inicios2 = [base2 + timedelta(minutes=grade_min * i) for i in range(0, (espera_max_min // grade_min) + 1)]

        # candidatos do serviço 2: se preferido faz s2, prioriza; senão qualquer
        cand2_sorted = sorted(
            cand2,
            key=lambda p: 0 if unidecode((p.get("nome") or "").strip().lower()) == pref_norm else 1
        )

        for prof2_data in cand2_sorted:
            prof2_nome = (prof2_data.get("nome") or "").strip()
            if not prof2_nome:
                continue
            prof2_norm = unidecode(prof2_nome.lower())

            d2 = duracao_servico_min(s2, prof2_data)

            for inicio2_serv in inicios2:
                # buffer do pacote: +5 depois do último serviço (entra na checagem)
                fim2_chk = inicio2_serv + timedelta(minutes=d2 + buffer_fim_min)

                if conflita(inicio2_serv, fim2_chk, ocupados_por_prof.get(prof2_norm, [])):
                    continue

                # achou split válido
                return {
                    "servicos": [s1, s2],
                    "eventos": [
                        {
                            "servico": s1,
                            "profissional": prof1_nome,
                            "data": data,
                            "hora_inicio": inicio1_serv.strftime("%H:%M"),
                            "duracao_min": d1,
                        },
                        {
                            "servico": s2,
                            "profissional": prof2_nome,
                            "data": data,
                            "hora_inicio": inicio2_serv.strftime("%H:%M"),
                            "duracao_min": d2,
                        }
                    ],
                    "espera_min": int((inicio2_serv - fim1_serv).total_seconds() / 60),
                }

    return None


async def verificar_conflito_e_sugestoes_profissional(
    user_id: str,
    data: str,
    hora_inicio: str,
    duracao_min: int,
    profissional: str,
    servico,
    event_id: str = None
) -> dict:
    from datetime import datetime, timedelta
    from unidecode import unidecode
    import json

    # -------------------------
    # helpers (aceita HH:MM + ISO)
    # -------------------------
    def _parse_event_interval(ev: dict):
        try:
            hi = ev.get("hora_inicio")
            hf = ev.get("hora_fim")

            # ISO completo
            if isinstance(hi, str) and "T" in hi:
                ini = datetime.fromisoformat(hi)
                if isinstance(hf, str) and "T" in hf:
                    fim = datetime.fromisoformat(hf)
                else:
                    dur = ev.get("duracao") or ev.get("duracao_min") or 0
                    fim = ini + timedelta(minutes=int(dur) if dur else 0)
                return ini, fim

            # data + HH:MM
            d = ev.get("data")
            hi2 = ev.get("hora_inicio")
            hf2 = ev.get("hora_fim")
            if d and hi2 and hf2:
                ini = datetime.strptime(f"{d} {hi2}", "%Y-%m-%d %H:%M")
                fim = datetime.strptime(f"{d} {hf2}", "%Y-%m-%d %H:%M")
                return ini, fim

            return None, None
        except Exception:
            return None, None

    # 1) Converte a hora nova para datetime
    inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
    fim_novo = inicio_novo + timedelta(minutes=duracao_min)

    # 2) Ajusta para modo híbrido de forma segura
    dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
    user_id_efetivo = user_id

    tipo = (dados_usuario.get("tipo_usuario") or "cliente").strip().lower()
    modo = (dados_usuario.get("modo_uso") or "").strip().lower()

    if tipo == "cliente" or modo == "atendimento_cliente":
        user_id_efetivo = await obter_id_dono(user_id)

    # 3) Busca eventos e profissionais
    eventos = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Eventos") or {}
    profissionais = await buscar_subcolecao(f"Clientes/{user_id_efetivo}/Profissionais") or {}

    print(
        f"🧪 Dados recebidos: user_id={user_id}, data={data}, hora_inicio={hora_inicio}, "
        f"duracao_min={duracao_min}, profissional={profissional}, servico={servico}",
        flush=True
    )
    print(f"📦 Eventos existentes:\n{json.dumps(eventos, indent=2, default=str)}", flush=True)

    prof_norm = unidecode((profissional or "").strip().lower())

    # 4) Ocupados do profissional (do dia todo)
    ocupados = []
    for eid, ev in eventos.items():
        if event_id and eid == event_id:
            continue

        status = (ev.get("status") or "").strip().lower()
        if status == "cancelado":
            continue

        ev_prof = unidecode(str(ev.get("profissional", "")).strip().lower())
        if not ev_prof or ev_prof != prof_norm:
            continue

        ev_ini, ev_fim = _parse_event_interval(ev)
        if not ev_ini or not ev_fim:
            continue

        if ev_ini.date() != inicio_novo.date():
            continue

        ocupados.append((ev_ini, ev_fim))

    conflito = any(inicio_novo < f and fim_novo > i for i, f in ocupados)

    # 🔥 SPLIT: somente se houver conflito e servico vier como lista com 2 itens
    if conflito and isinstance(servico, list) and len(servico) == 2:
        plano = await tentar_split_simples(
            user_id=user_id,
            data=data,
            hora_inicio=hora_inicio,
            servicos=servico,
            profissional_preferido=profissional,
            event_id=event_id,
        )
        if plano:
            return {
                "conflito": True,
                "tipo": "split",
                "plano": plano,
                "sugestoes": [],
                "profissional_alternativo": None,
            }

    # 5) Sugestões (fallback normal)
    sugestoes = gerar_sugestoes_de_horario(inicio_novo, ocupados, duracao_min)

    # 6) Profissional alternativo (apenas quando servico é string)
    alternativo = None
    if isinstance(servico, str) and servico.strip():
        servico_norm = (servico or "").strip().lower()

        for p in profissionais.values():
            nome_alt = p.get("nome", "")
            nome_alt_norm = unidecode(str(nome_alt).strip().lower())

            if not nome_alt_norm or nome_alt_norm == prof_norm:
                continue

            servs_alt = [str(s).strip().lower() for s in (p.get("servicos") or [])]
            if servico_norm and servico_norm not in servs_alt:
                continue

            conflitos_alt = False
            for eid, ev in eventos.items():
                if event_id and eid == event_id:
                    continue

                status = (ev.get("status") or "").strip().lower()
                if status == "cancelado":
                    continue

            ev_prof = unidecode(str(ev.get("profissional", "")).strip().lower())
            if ev_prof != nome_alt_norm:
                continue

            ev_ini, ev_fim = _parse_event_interval(ev)
            if not ev_ini or not ev_fim:
                continue
            if ev_ini.date() != inicio_novo.date():
                continue

            if inicio_novo < ev_fim and fim_novo > ev_ini:
                conflitos_alt = True
                break

    print(
        f"✅ Resultado: conflito={conflito}, sugestões={sugestoes}, alternativo={alternativo}",
        flush=True
    )

    return {
        "conflito": bool(conflito),
        "sugestoes": sugestoes,
        "profissional_alternativo": alternativo
    }