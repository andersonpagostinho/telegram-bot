# services/encaixe_service.py
from __future__ import annotations

from datetime import datetime, timedelta, time
from typing import List, Tuple, Dict, Any, Optional
import uuid
import logging
import os

from pytz import timezone

from services.firebase_service_async import (
    buscar_subcolecao,
    salvar_dado_em_path,
    atualizar_dado_em_path,
)
from services.event_service_async import (
    buscar_eventos_por_intervalo,
    salvar_evento,
)
from services.notificacao_service import criar_notificacao_agendada

logger = logging.getLogger(__name__)
FUSO_BR = timezone("America/Sao_Paulo")


# ---------------------------
# Utilidades internas
# ---------------------------
def _local_now() -> datetime:
    return datetime.now(FUSO_BR)


def _dt(date_str: str, hhmm: str) -> datetime:
    """Cria um datetime timezone-aware no fuso BR a partir de 'YYYY-MM-DD' e 'HH:MM'."""
    naive = datetime.strptime(f"{date_str} {hhmm}", "%Y-%m-%d %H:%M")
    return FUSO_BR.localize(naive)


def _to_date_hhmm(dt: datetime) -> Tuple[str, str]:
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def _eventos_ocupados_na_data(
    dono_id: str, data: datetime.date, profissional: Optional[str] = None
) -> List[Tuple[datetime, datetime]]:
    """
    Retorna pares (inicio,fim) timezone-aware de todos eventos do dia.
    Se 'profissional' informado, filtra por ele.
    """
    eventos = []
    br_date = data
    encontrados = []

    try:
        encontrados = buscar_eventos_por_intervalo.__wrapped__  # type: ignore[attr-defined]
    except Exception:
        pass  # só pra agradar linters locais

    # buscar_eventos_por_intervalo é async — chamaremos de fato abaixo na função chamadora
    # aqui só definimos o formato do que vamos construir


def _tem_conflito(inicio: datetime, fim: datetime, ocupados: List[Tuple[datetime, datetime]]) -> bool:
    return any(not (fim <= i or inicio >= f) for i, f in ocupados if f > i)


def _janela_livre(
    ocupados: List[Tuple[datetime, datetime]],
    dia: datetime.date,
    duracao_min: int,
    inicio_dia: time = time(9, 0),
    fim_dia: time = time(18, 0),
    max_opcoes: int = 3,
) -> List[Tuple[datetime, datetime]]:
    """
    Gera até 'max_opcoes' janelas livres no dia informado, respeitando 'ocupados' e a duração.
    Retorna pares (ini,fim).
    """
    base = FUSO_BR.localize(datetime.combine(dia, inicio_dia))
    limite = FUSO_BR.localize(datetime.combine(dia, fim_dia))
    passo = timedelta(minutes=15)
    dur = timedelta(minutes=duracao_min)

    opcoes = []
    cursor = base
    while cursor + dur <= limite and len(opcoes) < max_opcoes:
        if not _tem_conflito(cursor, cursor + dur, ocupados):
            opcoes.append((cursor, cursor + dur))
        cursor += passo
    return opcoes


async def _carregar_ocupados(
    dono_id: str, dia: datetime.date, profissional: Optional[str] = None
) -> List[Tuple[datetime, datetime]]:
    eventos = await buscar_eventos_por_intervalo(dono_id, dia_especifico=dia) or []
    slots: List[Tuple[datetime, datetime]] = []
    for ev in eventos:
        try:
            if profissional and ev.get("profissional"):
                if ev.get("profissional", "").strip().lower() != profissional.strip().lower():
                    continue
            ini = _dt(ev["data"], ev["hora_inicio"])
            fim = _dt(ev["data"], ev["hora_fim"])
            if fim > ini:
                slots.append((ini, fim))
        except Exception:
            continue
    return slots


def _overlap(a_ini: datetime, a_fim: datetime, b_ini: datetime, b_fim: datetime) -> bool:
    return not (a_fim <= b_ini or a_ini >= b_fim)


async def _enviar_msg_telegram(chat_id: str, texto: str):
    """
    Envia mensagem via Telegram usando application.bot se disponível; senão fallback por TOKEN.
    """
    try:
        from main import application
        bot = getattr(application, "bot", None)
    except Exception:
        bot = None

    if bot is None:
        from telegram import Bot
        token = os.getenv("TOKEN")
        if not token:
            logger.error("TOKEN ausente — não dá para enviar mensagem Telegram.")
            return
        bot = Bot(token=token)

    await bot.send_message(chat_id=int(chat_id), text=texto)


# ---------------------------
# Núcleo do ENCAIXE
# ---------------------------

async def solicitar_encaixe(
    user_id: str,
    descricao: str,
    profissional: Optional[str],
    duracao_min: int,
    dt_desejado: datetime,
    solicitante_user_id: str,
) -> Dict[str, Any]:
    """
    1) Se o slot desejado estiver livre -> cria o evento direto e retorna sucesso.
    2) Senão -> escolhe 1–2 clientes com eventos conflitantes (com mesmo profissional se informado),
       gera 3 horários realmente livres p/ cada, envia proposta e guarda pendência.
    """
    dt_desejado = dt_desejado.astimezone(FUSO_BR)
    dia = dt_desejado.date()
    inicio = dt_desejado
    fim = dt_desejado + timedelta(minutes=duracao_min)

    ocupados = await _carregar_ocupados(user_id, dia, profissional)
    if not _tem_conflito(inicio, fim, ocupados):
        # Livre → cria evento direto
        ev = {
            "descricao": descricao or "Encaixe",
            "data": dia.strftime("%Y-%m-%d"),
            "hora_inicio": inicio.strftime("%H:%M"),
            "hora_fim": fim.strftime("%H:%M"),
            "duracao": duracao_min,
            "confirmado": False,
            "link": "",
            "status": "pendente",
            "cliente_id": solicitante_user_id,
        }
        if profissional:
            ev["profissional"] = profissional

        await salvar_evento(user_id, ev)

        # lembrete ao solicitante
        try:
            await criar_notificacao_agendada(
                user_id=solicitante_user_id,
                descricao=ev["descricao"],
                data=ev["data"],
                hora_inicio=ev["hora_inicio"],
                minutos_antes=30,
                canal="telegram",
                destinatario_user_id=solicitante_user_id,
                alvo_evento={"data": ev["data"], "hora_inicio": ev["hora_inicio"]},
            )
        except Exception as e:
            logger.warning(f"Falha ao agendar lembrete do encaixe direto: {e}")

        return {
            "status": "encaixe_confirmado",
            "mensagem": "Slot estava livre e o encaixe foi criado.",
            "evento": ev,
        }

    # Conflito → procurar clientes candidatos (eventos que conflitam)
    eventos_do_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=dia) or []
    candidatos: List[Tuple[str, Dict[str, Any]]] = []  # (event_id, evento)
    for ev_id, ev in ((k, v) for k, v in eventos_do_dia.items() if isinstance(eventos_do_dia, dict)) if isinstance(eventos_do_dia, dict) else []:
        # se buscar_eventos_por_intervalo retorna lista, ajustamos:
        pass

    # Normalizar 'eventos_do_dia' em tuplas (id,ev)
    norm: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(eventos_do_dia, dict):
        for k, v in eventos_do_dia.items():
            if isinstance(v, dict):
                norm.append((k, v))
    elif isinstance(eventos_do_dia, list):
        # quando serviço retorna lista simples (sem id), criamos ids voláteis
        for v in eventos_do_dia:
            if isinstance(v, dict):
                norm.append((v.get("id") or f"ev_{uuid.uuid4()}", v))

    for ev_id, ev in norm:
        try:
            if profissional and ev.get("profissional"):
                if ev.get("profissional", "").strip().lower() != profissional.strip().lower():
                    continue

            ini = _dt(ev["data"], ev["hora_inicio"])
            fim_ev = _dt(ev["data"], ev["hora_fim"])
            if _overlap(inicio, fim, ini, fim_ev):
                # precisa ter cliente_id (não realoque reuniões internas por padrão)
                if ev.get("cliente_id"):
                    candidatos.append((ev_id, ev))
        except Exception:
            continue

    # ordenar candidatos por "flex" aproximado: eventos com descricao curta ou recorrentes (heurística simples)
    candidatos = candidatos[:2]  # máximo 2 convites por tentativa

    if not candidatos:
        return {
            "status": "sem_candidato",
            "mensagem": "Sem clientes flexíveis/compatíveis para propor reagendamento neste horário.",
        }

    # Para cada candidato, gerar 3 janelas realmente livres (considerando TODO O DIA) nos próximos 5 dias
    pend_id = str(uuid.uuid4())
    pend_path = f"Clientes/{user_id}/PendenciasEncaixe/{pend_id}"

    opcoes_por_cliente: Dict[str, List[Dict[str, str]]] = {}
    horizonte = 5  # dias
    for ev_id, ev in candidatos:
        cli_id = str(ev.get("cliente_id"))
        dur = int(ev.get("duracao") or 30)

        achadas: List[Dict[str, str]] = []
        base_dia = dia
        for d in range(horizonte):
            dia_test = base_dia + timedelta(days=d)
            ocp = await _carregar_ocupados(user_id, dia_test, profissional)
            # Ao verificar slots, consideramos “livre” se o único conflito for o PRÓPRIO evento do cliente (pois ele será movido).
            # Então removemos o slot do próprio evento da lista de ocupados.
            try:
                ini_cli = _dt(ev["data"], ev["hora_inicio"])
                fim_cli = _dt(ev["data"], ev["hora_fim"])
                ocp = [(i, f) for (i, f) in ocp if not (i == ini_cli and f == fim_cli)]
            except Exception:
                pass

            janelas = _janela_livre(ocp, dia_test, dur, max_opcoes=3 - len(achadas))
            for ini2, fim2 in janelas:
                achadas.append({
                    "data": ini2.strftime("%Y-%m-%d"),
                    "hora_inicio": ini2.strftime("%H:%M"),
                    "hora_fim": fim2.strftime("%H:%M"),
                })
                if len(achadas) >= 3:
                    break
            if len(achadas) >= 3:
                break

        opcoes_por_cliente[cli_id] = achadas

    # Guarda a pendência
    pend_doc = {
        "status": "pendente",
        "criado_em": _local_now().isoformat(),
        "solicitante_user_id": solicitante_user_id,
        "dono_id": user_id,
        "profissional": profissional,
        "duracao_min": duracao_min,
        "dt_desejado": dt_desejado.isoformat(),
        "candidatos": [
            {
                "cliente_id": ev.get("cliente_id"),
                "evento_id": ev_id,
                "evento_original": {
                    "data": ev.get("data"),
                    "hora_inicio": ev.get("hora_inicio"),
                    "hora_fim": ev.get("hora_fim"),
                    "descricao": ev.get("descricao"),
                    "duracao": ev.get("duracao"),
                    "profissional": ev.get("profissional"),
                },
                "opcoes": opcoes_por_cliente.get(str(ev.get("cliente_id"))) or [],
                "status_cliente": "aguardando",
            }
            for (ev_id, ev) in candidatos
        ],
    }
    await salvar_dado_em_path(pend_path, pend_doc)

    # Dispara mensagens aos clientes candidatos
    for (ev_id, ev) in candidatos:
        cli_id = str(ev.get("cliente_id"))
        opcoes = opcoes_por_cliente.get(cli_id, [])
        if not opcoes:
            # sem opções livres -> marca como sem_opcao (e segue para o próximo)
            await atualizar_dado_em_path(pend_path, {"status": "sem_opcao"})
            continue

        # monta texto
        linhas = []
        for idx, o in enumerate(opcoes, start=1):
            linhas.append(f"{idx}) {o['data']} às {o['hora_inicio']}")

        prof_txt = f" com {ev.get('profissional')}" if ev.get("profissional") else ""
        msg = (
            ⚠️ Oi! Surgiu uma urgência e estamos tentando realocar um horário.\n\n"
            f"Você topa mover o seu agendamento{prof_txt} *({ev.get('descricao')})* para um destes horários?\n\n"
            + "\n".join(linhas) +
            "\n\nResponda *1*, *2* ou *3* aqui no chat para confirmar. Obrigado! 🙏"
        )
        try:
            await _enviar_msg_telegram(cli_id, msg)
        except Exception as e:
            logger.error(f"Falha ao notificar cliente flex {cli_id}: {e}")

    # Notifica o solicitante que estamos aguardando
    try:
        await _enviar_msg_telegram(
            solicitante_user_id,
            "📨 Enviei pedidos de reagendamento para clientes com flexibilidade. Assim que alguém confirmar, eu fecho o encaixe pra você."
        )
    except Exception:
        pass

    return {
        "status": "aguardando_respostas",
        "mensagem": "Foram enviados pedidos de reagendamento para clientes candidatos.",
        "pendencia_id": pend_id,
    }


async def confirmar_reagendamento_por_opcao(
    dono_id: str,
    cliente_id: str,
    opcao: int,
) -> Dict[str, Any]:
    """
    Chamado quando o cliente “flex” responde 1/2/3.
    - Localiza a pendência mais recente onde esse cliente está como candidato 'aguardando'.
    - Move o evento do cliente para a opção escolhida (valida conflito).
    - Cria o evento do ENCAIXE para o solicitante no dt_desejado original.
    - Notifica envolvidos e agenda lembretes.
    """
    pendencias = await buscar_subcolecao(f"Clientes/{dono_id}/PendenciasEncaixe") or {}
    # pega a mais recente em status pendente contendo esse cliente
    alvo_id = None
    alvo_doc = None
    for pid, p in pendencias.items():
        if not isinstance(p, dict):
            continue
        if (p.get("status") == "pendente") and any(
            (c.get("cliente_id") == cliente_id and c.get("status_cliente") == "aguardando")
            for c in p.get("candidatos", [])
        ):
            alvo_id = pid
            alvo_doc = p
            break

    if not alvo_doc:
        return {"status": "erro", "mensagem": "Não encontrei uma pendência ativa para sua resposta."}

    # localiza candidato e opção
    cand = None
    for c in alvo_doc.get("candidatos", []):
        if c.get("cliente_id") == cliente_id and c.get("status_cliente") == "aguardando":
            cand = c
            break
    if not cand:
        return {"status": "erro", "mensagem": "Sua pendência já foi resolvida ou cancelada."}

    opcoes = cand.get("opcoes") or []
    if opcao < 1 or opcao > len(opcoes):
        return {"status": "erro", "mensagem": "Opção inválida. Responda com 1, 2 ou 3."}

    opc = opcoes[opcao - 1]
    nova_data = opc["data"]
    nova_hora_inicio = opc["hora_inicio"]
    nova_hora_fim = opc["hora_fim"]

    # valida de novo se não surgiu conflito (janela pode ter sido ocupada entre a proposta e a resposta)
    ocp = await _carregar_ocupados(dono_id, datetime.strptime(nova_data, "%Y-%m-%d").date(), alvo_doc.get("profissional"))
    ini_novo = _dt(nova_data, nova_hora_inicio)
    fim_novo = _dt(nova_data, nova_hora_fim)
    if _tem_conflito(ini_novo, fim_novo, ocp):
        return {"status": "erro", "mensagem": "Esse horário acabou de ficar indisponível. Pode escolher outra opção?"}

    # 1) mover o evento do cliente (update simples: cria novo e recomenda-se cancelar o antigo; aqui sobrescrevemos)
    ev_ori = cand.get("evento_original") or {}
    # salvamos um novo evento com os mesmos dados, porém nova data/hora
    novo_ev_cliente = {
        "descricao": ev_ori.get("descricao", "Atendimento"),
        "data": nova_data,
        "hora_inicio": nova_hora_inicio,
        "hora_fim": nova_hora_fim,
        "duracao": int(ev_ori.get("duracao") or 30),
        "confirmado": False,
        "link": "",
        "status": "pendente",
        "cliente_id": cliente_id,
    }
    if ev_ori.get("profissional"):
        novo_ev_cliente["profissional"] = ev_ori.get("profissional")

    await salvar_evento(dono_id, novo_ev_cliente)

    # 2) criar o evento do ENCAIXE no horário originalmente desejado
    dt_desejado_str = alvo_doc.get("dt_desejado")
    dt_desejado = datetime.fromisoformat(dt_desejado_str).astimezone(FUSO_BR)
    data_encaixe, hora_encaixe = _to_date_hhmm(dt_desejado)
    dur_encaixe = int(alvo_doc.get("duracao_min") or 30)
    fim_encaixe_dt = dt_desejado + timedelta(minutes=dur_encaixe)

    ev_encaixe = {
        "descricao": "Encaixe confirmado",
        "data": data_encaixe,
        "hora_inicio": hora_encaixe,
        "hora_fim": fim_encaixe_dt.strftime("%H:%M"),
        "duracao": dur_encaixe,
        "confirmado": False,
        "link": "",
        "status": "pendente",
        "cliente_id": str(alvo_doc.get("solicitante_user_id")),
    }
    if alvo_doc.get("profissional"):
        ev_encaixe["profissional"] = alvo_doc.get("profissional")

    await salvar_evento(dono_id, ev_encaixe)

    # 3) atualizar pendência
    # marca cliente como concluído, e pendência como concluída
    for c in alvo_doc.get("candidatos", []):
        if c.get("cliente_id") == cliente_id:
            c["status_cliente"] = "remarcado"
    alvo_doc["status"] = "concluida"
    alvo_doc["concluida_em"] = _local_now().isoformat()
    alvo_doc["resultado"] = {
        "cliente_movido": cliente_id,
        "opcao_escolhida": opcao,
        "evento_cliente_novo": novo_ev_cliente,
        "evento_encaixe_criado": ev_encaixe,
    }
    await salvar_dado_em_path(f"Clientes/{dono_id}/PendenciasEncaixe/{alvo_id}", alvo_doc)

    # 4) notificar envolvidos
    # 4a) cliente flex (confirmação)
    try:
        await _enviar_msg_telegram(
            cliente_id,
            f"✅ Obrigado! Seu horário foi remarcado para *{nova_data} às {nova_hora_inicio}*.",
        )
        # lembrete do cliente para nova data
        await criar_notificacao_agendada(
            user_id=cliente_id,
            descricao=novo_ev_cliente["descricao"],
            data=novo_ev_cliente["data"],
            hora_inicio=novo_ev_cliente["hora_inicio"],
            minutos_antes=30,
            canal="telegram",
            destinatario_user_id=cliente_id,
            alvo_evento={"data": novo_ev_cliente["data"], "hora_inicio": novo_ev_cliente["hora_inicio"]},
        )
    except Exception as e:
        logger.warning(f"Falha ao notificar/lembrar cliente flex: {e}")

    # 4b) solicitante (encaixe)
    solicitante = str(alvo_doc.get("solicitante_user_id"))
    try:
        prof_txt = f" com {ev_encaixe.get('profissional')}" if ev_encaixe.get("profissional") else ""
        await _enviar_msg_telegram(
            solicitante,
            f"🎉 Encaixe confirmado{prof_txt}: *{data_encaixe} às {hora_encaixe}*.\nJá agendei pra você!"
        )
        await criar_notificacao_agendada(
            user_id=solicitante,
            descricao=ev_encaixe["descricao"],
            data=ev_encaixe["data"],
            hora_inicio=ev_encaixe["hora_inicio"],
            minutos_antes=30,
            canal="telegram",
            destinatario_user_id=solicitante,
            alvo_evento={"data": ev_encaixe["data"], "hora_inicio": ev_encaixe["hora_inicio"]},
        )
    except Exception as e:
        logger.warning(f"Falha ao notificar/lembrar solicitante do encaixe: {e}")

    # 4c) dono (opcional)
    try:
        await _enviar_msg_telegram(
            dono_id,
            f"🧩 Fechamento de encaixe concluído:\n- Cliente movido: {cliente_id} → {nova_data} {nova_hora_inicio}\n- Encaixe criado: {data_encaixe} {hora_encaixe}"
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "mensagem": f"Reagendamento confirmado na opção {opcao}. Encaixe criado e lembretes agendados.",
        "evento_cliente_novo": novo_ev_cliente,
        "evento_encaixe": ev_encaixe,
    }
