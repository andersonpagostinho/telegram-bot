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
    obter_id_dono,              # 👈 acrescentado
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
    # 👇 garante que sempre trabalhamos no negócio do dono
    dono_id = await obter_id_dono(user_id)

    dt_desejado = dt_desejado.astimezone(FUSO_BR)
    dia = dt_desejado.date()
    # --- MODO / LIMITE POR BURACO (anti-spam) ---
    agora = datetime.now(FUSO_BR)
    horas_restantes = (dt_desejado - agora).total_seconds() / 3600

    if horas_restantes <= 4:
        modo = "urgente"
        max_tentativas = 10
    elif horas_restantes <= 24:
        modo = "moderado"
        max_tentativas = 6
    else:
        modo = "estrategico"
        max_tentativas = 3
    inicio = dt_desejado
    fim = dt_desejado + timedelta(minutes=duracao_min)

    # ocupação sempre do dono
    ocupados = await _carregar_ocupados(dono_id, dia, profissional)
    if not _tem_conflito(inicio, fim, ocupados):
        # Livre → cria evento direto no dono
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

        # 👇 salva no dono
        await salvar_evento(dono_id, ev)
        print(f"💰 ENCAIXE DIRETO CONFIRMADO | dono={dono_id} | data={ev['data']} | hora={ev['hora_inicio']} | duracao={ev['duracao']}", flush=True)

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
    eventos_do_dia = await buscar_eventos_por_intervalo(dono_id, dia_especifico=dia) or []
    candidatos: List[Tuple[str, Dict[str, Any]]] = []

    # Normalizar 'eventos_do_dia' em tuplas (id,ev)
    norm: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(eventos_do_dia, dict):
        for k, v in eventos_do_dia.items():
            if isinstance(v, dict):
                norm.append((k, v))
    elif isinstance(eventos_do_dia, list):
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
                if ev.get("cliente_id"):
                    candidatos.append((ev_id, ev))
        except Exception:
            continue

    candidatos = candidatos[:2]  # máximo 2 convites por tentativa

    if not candidatos:
        return {
            "status": "sem_candidato",
            "mensagem": "Sem clientes flexíveis/compatíveis para propor reagendamento neste horário.",
        }

    # --- ID determinístico do BURACO (slot) para contar tentativas ---
    data_slot, hora_slot = _to_date_hhmm(dt_desejado)
    prof_key = (profissional or "sem_prof").strip().lower().replace(" ", "_")
    slot_key = f"{data_slot}_{hora_slot}_{int(duracao_min)}_{prof_key}"

    pend_id = slot_key  # ✅ sempre o mesmo para o mesmo buraco
    pend_path = f"Clientes/{dono_id}/PendenciasEncaixe/{pend_id}"

    # Carrega pendência existente (se já tentou antes)
    pend_existente = await buscar_dado_em_path(pend_path) or {}

    tentativas_atual = int(pend_existente.get("tentativas") or 0)
    max_tentativas_slot = int(pend_existente.get("max_tentativas") or max_tentativas)
    status_atual = pend_existente.get("status") or "pendente"

    # Se já foi resolvido/encerrado, não dispara de novo
    if status_atual in ("preenchido", "concluida", "encerrado"):
        return {
            "status": "encerrado",
            "mensagem": "Este buraco já foi encerrado ou preenchido anteriormente.",
            "pendencia_id": pend_id,
        }

    # ✅ Limite por buraco
    if tentativas_atual >= max_tentativas_slot:
        await atualizar_dado_em_path(pend_path, {
            "status": "encerrado",
            "encerrado_em": datetime.now(FUSO_BR).isoformat(),
        })
        return {
            "status": "encerrado_por_limite",
            "mensagem": "Atingi o limite de tentativas para preencher esse horário.",
            "pendencia_id": pend_id,
        }

    # incrementa tentativa (uma “rodada” de disparos)
    tentativas_nova = tentativas_atual + 1

    # ✅ Salva/atualiza pendência do buraco (necessário para confirmar 1/2/3 depois)
    pend_doc = {
        "status": "pendente",
        "criado_em": datetime.now(FUSO_BR).isoformat(),
        "ultima_tentativa_em": datetime.now(FUSO_BR).isoformat(),
        "slot_key": slot_key,
        "modo": modo,
        "tentativas": tentativas_nova,
        "max_tentativas": max_tentativas_slot,
        "solicitante_user_id": solicitante_user_id,
        "dono_id": dono_id,
        "profissional": profissional,
        "duracao_min": int(duracao_min),
        "dt_desejado": dt_desejado.isoformat(),
        "candidatos": [],
    }

    # guarda, por candidato, o evento original e as opções
    for (ev_id, ev) in candidatos:
        cli_id = str(ev.get("cliente_id"))
        opcoes = opcoes_por_cliente.get(cli_id, []) or []
        pend_doc["candidatos"].append({
            "cliente_id": cli_id,
            "evento_id": ev_id,
            "evento_original": {
                "data": ev.get("data"),
                "hora_inicio": ev.get("hora_inicio"),
                "hora_fim": ev.get("hora_fim"),
                "descricao": ev.get("descricao"),
                "duracao": ev.get("duracao"),
                "profissional": ev.get("profissional"),
            },
            "opcoes": opcoes,
            "status_cliente": "aguardando",
        })

    await salvar_dado_em_path(pend_path, pend_doc)


    # Dispara mensagens aos clientes candidatos
    for (ev_id, ev) in candidatos:
        cli_id = str(ev.get("cliente_id"))
        opcoes = opcoes_por_cliente.get(cli_id, [])
        if not opcoes:
            continue

        linhas = []
        for idx, o in enumerate(opcoes, start=1):
            linhas.append(f"{idx}) {o['data']} às {o['hora_inicio']}")

        prof_txt = f" com {ev.get('profissional')}" if ev.get("profissional") else ""
        msg = (
            "⚠️ Oi! Surgiu uma urgência e estamos tentando realocar um horário.\n\n"
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
    """
    pendencias = await buscar_subcolecao(f"Clientes/{dono_id}/PendenciasEncaixe") or {}
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

    # valida de novo se não surgiu conflito
    ocp = await _carregar_ocupados(dono_id, datetime.strptime(nova_data, "%Y-%m-%d").date(), alvo_doc.get("profissional"))
    ini_novo = _dt(nova_data, nova_hora_inicio)
    fim_novo = _dt(nova_data, nova_hora_fim)
    if _tem_conflito(ini_novo, fim_novo, ocp):
        return {"status": "erro", "mensagem": "Esse horário acabou de ficar indisponível. Pode escolher outra opção?"}

    ev_ori = cand.get("evento_original") or {}
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
    print(
    f"💰 ENCAIXE VIA REMARCAÇÃO | dono={dono_id} | data={ev_encaixe['data']} | "
    f"hora={ev_encaixe['hora_inicio']} | cliente_movido={cliente_id}",
    flush=True
)

    # atualizar pendência
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

    # notificações
    try:
        await _enviar_msg_telegram(
            cliente_id,
            f"✅ Obrigado! Seu horário foi remarcado para *{nova_data} às {nova_hora_inicio}*.",
        )
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
