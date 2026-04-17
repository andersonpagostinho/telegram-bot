# router/principal_router.py

from services.session_service import pegar_sessao
from services.gpt_service import tratar_mensagem_usuario as tratar_mensagem_gpt
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario
from utils.context_manager import atualizar_contexto  # apenas histórico user/bot
from services.gpt_executor import executar_acao_gpt
from services.firebase_service_async import obter_id_dono, buscar_subcolecao
from services.event_service_async import verificar_conflito_e_sugestoes_profissional
from services.gpt_service import processar_com_gpt_com_acao as chamar_gpt_com_contexto
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA

from datetime import datetime, timedelta
from utils.interpretador_datas import interpretar_data_e_hora
from utils.gpt_utils import estimar_duracao, formatar_descricao_evento

from services.agenda_service import (
    validar_data_funcionamento,
    validar_horario_funcionamento,
    resolver_fora_do_expediente,
)

import pytz
import re
from unidecode import unidecode
from telegram.ext import ApplicationHandlerStop
from handlers.acao_router_handler import executar_acao_por_nome
from calendar import monthrange

# ----------------------------
# Helpers de saída (anti-duplicidade)
# ----------------------------

async def _send_and_stop(context, user_id: str, text: str, parse_mode: str = "Markdown"):
    """
    Envia mensagem UMA vez e sinaliza para o bot.py não reenviar.
    """
    if context is not None:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
    return {"handled": True, "already_sent": True}

async def _send_and_stop_ctx(context, user_id, mensagem, ctx, texto_usuario):
    try:
        await salvar_contexto_temporario(user_id, ctx)
    except Exception as e:
        print(f"⚠️ erro ao salvar contexto: {e}", flush=True)

    return await _send_and_stop(context, user_id, mensagem)


# ----------------------------
# Helpers de NLP simples
# ----------------------------

def normalizar(texto: str) -> str:
    return unidecode((texto or "").strip().lower())


def formatar_data_hora_br(dt_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_iso)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(dt_iso)

def montar_frase_data_legivel(data_hora_iso: str | None) -> str:
    if not data_hora_iso:
        return ""

    try:
        dt = datetime.fromisoformat(data_hora_iso)
        hoje = datetime.now().date()

        if dt.date() == hoje:
            return "para hoje"
        elif dt.date() == (hoje + timedelta(days=1)):
            return "para amanhã"
        else:
            return f"para {dt.strftime('%d/%m')}"
    except Exception:
        return ""

def resolver_proximo_passo_real(
    proximo_passo: str | None,
    slots_extraidos: dict,
    contexto: dict | None = None
) -> str | None:

    contexto = contexto or {}

    # 🔥 Se está em escolha de horário, só pode confirmar se já houver base mínima
    if contexto.get("estado_fluxo") == "aguardando_escolha_horario":
        tem_servico_ctx = bool(slots_extraidos.get("servico") or contexto.get("servico"))
        tem_profissional_ctx = bool(
            slots_extraidos.get("profissional") or contexto.get("profissional_escolhido")
        )

        # só confirma se já souber serviço e profissional
        if tem_servico_ctx and tem_profissional_ctx:
            return "confirmar_ou_executar"


    def tem_hora_real_local():
        if "hora_confirmada" in contexto:
            return contexto.get("hora_confirmada") is True

        dt_iso = slots_extraidos.get("data_hora") or contexto.get("data_hora")
        if not dt_iso:
            return False

        try:
            dt = datetime.fromisoformat(dt_iso)
            return not (dt.hour == 0 and dt.minute == 0)
        except Exception:
            return False

    def tem_data():
        return bool(slots_extraidos.get("data_hora") or contexto.get("data_hora"))

    tem_servico = bool(slots_extraidos.get("servico") or contexto.get("servico"))
    tem_profissional = bool(slots_extraidos.get("profissional") or contexto.get("profissional_escolhido"))
    tem_data_valor = tem_data()
    tem_hora = tem_hora_real_local()
    horarios_candidatos = contexto.get("horarios_sugeridos") or []

    # 🔥 NOVA LÓGICA CENTRAL (IGNORA proximo_passo antigo)

    # 1. Se já existem horários candidatos capturados, não pergunte horário de novo.
    # Primeiro complete os campos principais do agendamento.
    if horarios_candidatos and not tem_hora:
        if not tem_servico:
            return "perguntar_servico"
        if not tem_profissional:
            return "perguntar_profissional"
        return "perguntar_somente_horario"

    # 2. Não tem data nenhuma → pedir data + hora
    if not tem_data_valor:
        return "perguntar_data_hora"

    # 3. Falta profissional
    if not tem_servico:
        return "perguntar_servico"

    # 4. Falta serviço
    if not tem_profissional:
        return "perguntar_profissional"

    # 5. Tudo completo
    return "confirmar_ou_executar"

def tem_hora_real(dt_iso: str | None) -> bool:
    if not dt_iso:
        return False
    try:
        dt = datetime.fromisoformat(dt_iso)
        return not (dt.hour == 0 and dt.minute == 0)
    except Exception:
        return False

def montar_resposta_fallback(
    proximo_passo_real: str | None,
    frase_data_legivel: str,
    contexto: dict | None = None
) -> str:
    contexto = contexto or {}

    servico = contexto.get("servico")
    profissional = contexto.get("profissional_escolhido")
    data_hora = contexto.get("data_hora")

    servicos_permitidos = contexto.get("servicos_permitidos") or []
    profissionais_permitidos = contexto.get("profissionais_permitidos") or []

    comp = f" {frase_data_legivel}" if frase_data_legivel else ""

    # =========================================================
    # 🔹 PERGUNTAR SERVIÇO
    # =========================================================
    if proximo_passo_real == "perguntar_servico":
        horarios_candidatos = contexto.get("horarios_sugeridos") or []

        # 👉 se só existe 1 serviço → assume
        if len(servicos_permitidos) == 1:
            unico = servicos_permitidos[0]

            partes = []

            if profissional:
                partes.append(f"com {profissional}")

            if frase_data_legivel:
                partes.append(frase_data_legivel.strip())

            if horarios_candidatos:
                partes.append(f"por volta de {' ou '.join(horarios_candidatos)}")

            contexto_str = " ".join(partes)

            if contexto_str:
                return f"Perfeito — {unico} {contexto_str}. Posso confirmar?"
            else:
                return f"Perfeito — {unico}. Posso confirmar?"

        # 👉 se precisa perguntar
        partes = []

        if profissional:
            partes.append(f"com {profissional}")

        if frase_data_legivel:
            partes.append(frase_data_legivel.strip())

        contexto_str = " ".join(partes)

        if contexto_str:

            if horarios_candidatos:
                horarios_txt = " ou ".join(horarios_candidatos)

                return (
                    f"Perfeito — {contexto_str} por volta de {horarios_txt} 😊\n\n"
                    "Qual serviço você deseja?"
                )

            return (
                f"Perfeito — {contexto_str} 😊\n\n"
                "Qual serviço você deseja?"
            )

        return "Perfeito 😊\n\nQual serviço você deseja?"

    # =========================================================
    # 🔹 PERGUNTAR PROFISSIONAL
    # =========================================================
    if proximo_passo_real == "perguntar_profissional":

        # 👉 se só existe 1 profissional → assume
        if len(profissionais_permitidos) == 1:
            unico = profissionais_permitidos[0]

            partes = []

            if servico:
                partes.append(servico)

            if frase_data_legivel:
                partes.append(frase_data_legivel.strip())

            contexto_str = " ".join(partes)

            if contexto_str:
                return f"Perfeito — {contexto_str} com {unico}. Posso confirmar?"
            else:
                return f"Perfeito — com {unico}. Posso confirmar?"

        # 👉 se precisa perguntar
        partes = []

        if servico:
            partes.append(servico)

        if frase_data_legivel:
            partes.append(frase_data_legivel.strip())

        contexto_str = " ".join(partes)

        if contexto_str:
            return f"Perfeito — {contexto_str}. Qual profissional você prefere?"

        return "Perfeito. Qual profissional você prefere?"

    # =========================================================
    # 🔹 PERGUNTAR SOMENTE HORÁRIO
    # =========================================================
    if proximo_passo_real == "perguntar_somente_horario":

        partes = []

        if servico:
            partes.append(servico)

        if profissional:
            partes.append(f"com {profissional}")

        contexto_str = " ".join(partes)

        if contexto_str:
            return f"Perfeito — {contexto_str}{comp}. Qual horário você prefere?"

        return f"Perfeito{comp}. Qual horário você prefere?" if comp else "Perfeito. Qual horário você prefere?"

    # =========================================================
    # 🔹 PERGUNTAR DATA + HORÁRIO
    # =========================================================
    if proximo_passo_real == "perguntar_data_hora":

        partes = []

        if servico:
            partes.append(servico)

        if profissional:
            partes.append(f"com {profissional}")

        contexto_str = " ".join(partes)

        if contexto_str:
            return f"Perfeito — {contexto_str}. Qual dia e horário você prefere?"

        return f"Perfeito{comp}. Qual dia e horário você prefere?" if comp else "Perfeito. Qual dia e horário você prefere?"

    # =========================================================
    # 🔹 TEM TUDO, FALTA CONFIRMAR HORÁRIO
    # =========================================================
    if (
        servico
        and profissional
        and data_hora
        and not contexto.get("hora_confirmada")
    ):
        return (
            f"Perfeito — {servico} com {profissional} "
            f"{frase_data_legivel}. Agora me diga o horário que você prefere."
        )

    # =========================================================
    # 🔹 FALLBACK FINAL
    # =========================================================
    return "Perfeito. Me diga como você prefere agendar."        

def eh_consulta(txt: str) -> bool:
    """
    Detecta consulta pura.
    Só retorna True quando há forte evidência de pergunta/informação
    e NÃO houver sinais típicos de agendamento/continuidade.
    """
    t = normalizar(txt or "")
    if not t:
        return False

    # ❌ Mensagens curtas/neutras não devem ser tratadas como consulta
    curtas_neutras = {
        "sim", "nao", "não", "ok", "pode", "pode ser", "fechado",
        "esse", "esse ai", "esse aí", "entao", "então",
        "mais tarde", "mais cedo", "outro horario", "outro horário",
        "esse horario", "esse horário", "esse outro",
        "com ela", "com ele", "com a", "com o"
    }
    if t in curtas_neutras:
        return False

    # ❌ Se há indício de horário, tende a ser continuidade/agendamento
    if _tem_indicio_de_hora(t):
        return False

    # ❌ Se há verbos de ação de agendamento, não é consulta
    gatilhos_agendamento = [
        "agendar", "marcar", "confirmar", "confirma", "confirme", "confirmo",
        "pode agendar", "pode marcar", "agenda pra", "agenda para",
        "marca pra", "marca para", "entao marca", "então marca",
        "quero agendar", "quero marcar", "fechar horario", "fechar horário",
        "agenda esse", "marca esse", "entao esse", "então esse"
    ]
    if any(g in t for g in gatilhos_agendamento):
        return False

    # ❌ Frases de continuidade/reação também não são consulta pura
    gatilhos_continuacao = [
        "outro horario", "outro horário",
        "esse horario", "esse horário",
        "mais tarde", "mais cedo",
        "esse outro", "entao esse", "então esse",
        "mas com a", "mas com o", "com ela", "com ele",
        "que pena", "nossa", "serio", "sério",
        "ela nao consegue", "ela não consegue",
        "nao consegue", "não consegue",
        "nao tem jeito", "não tem jeito",
        "que horario tem", "que horário tem"
    ]
    if any(g in t for g in gatilhos_continuacao):
        return False

    # ✅ Consultas claras
    gatilhos_consulta = [
        "quanto custa", "qual o preco", "qual o preço", "valor", "preco", "preço",
        "tem horario", "tem horário", "tem vaga", "tem espaco", "tem espaço",
        "quais horarios", "quais horários", "que horas",
        "agenda da", "como esta a agenda", "como está a agenda",
        "disponivel", "disponível",
        "quais servicos", "quais serviços", "que servicos", "que serviços",
        "quem faz", "quem atende", "faz escova", "faz corte",
        "qual o endereco", "qual o endereço", "onde fica", "localizacao", "localização",
        "qual o telefone", "whatsapp", "zap",
        "funciona hoje", "abre hoje", "fecha hoje", "que horas abre", "que horas fecha",
        "tem promocao", "tem promoção", "promoção", "promocao"
    ]

    # ✅ Pergunta explícita só é consulta se também tiver cara de consulta
    if "?" in txt:
        gatilhos_pergunta_consulta = [
            "quanto", "qual", "quais", "quem", "onde", "como", "valor", "preco", "preço",
            "horario", "horário", "vaga", "espaco", "espaço",
            "servico", "serviço", "endereco", "endereço", "telefone", "whatsapp",
            "funciona", "abre", "fecha", "promocao", "promoção"
        ]
        if any(g in t for g in gatilhos_pergunta_consulta):
            return True

    return any(g in t for g in gatilhos_consulta)

def eh_gatilho_agendar(txt: str) -> bool:
    """
    Gatilho explícito de agendar (decisão final do usuário).
    """
    t = (txt or "").strip().lower()
    gatilhos = ["pode agendar", "pode marcar", "agende", "marque"]
    return any(g in t for g in gatilhos)

def detectar_bloqueio_agenda_salao(texto: str) -> dict | None:
    texto_lower = (texto or "").lower().strip()

    sinais_fechamento = [
        "não abriremos", "nao abriremos",
        "não vai abrir", "nao vai abrir",
        "não vamos abrir", "nao vamos abrir",
        "fechado", "fechada", "fechar",
        "bloquear agenda", "bloquear",
        "não atender", "nao atender",
        "indisponivel", "indisponível",
    ]

    sinais_janela = [
        "até", "ate",
        "só até", "so ate",
        "atender só", "atender so",
        "vamos atender", "iremos atender",
        "a partir das", "a partir de", "depois das",
        "das", "de",  # intervalo será validado por regex
        "só de manhã", "so de manha", "somente de manhã", "somente de manha",
        "só à tarde", "so a tarde", "só de tarde", "so de tarde",
        "somente à tarde", "somente a tarde",
        "meio período", "meio periodo",
    ]

    eh_fechamento = any(s in texto_lower for s in sinais_fechamento)
    eh_janela = any(s in texto_lower for s in sinais_janela)

    # se não for bloqueio nem janela especial, ignora
    if not eh_fechamento and not eh_janela:
        return None

    hoje = datetime.now()
    datas = []

    def ajustar_data_futura(dia: int) -> datetime | None:
        if not (1 <= dia <= 31):
            return None

        try:
            d = datetime(hoje.year, hoje.month, dia)

            if d.date() < hoje.date():
                mes = hoje.month + 1
                ano = hoje.year
                if mes > 12:
                    mes = 1
                    ano += 1

                ultimo_dia = monthrange(ano, mes)[1]
                dia_aj = min(dia, ultimo_dia)
                d = datetime(ano, mes, dia_aj)

            return d
        except Exception:
            return None

    # =========================================================
    # 1. intervalo de dias: "de 20 até 23"
    # =========================================================
    m_intervalo_dias = re.search(
        r"\bde\s+(\d{1,2})\s+(?:ate|até|a)\s+(\d{1,2})\b",
        texto_lower
    )

    if m_intervalo_dias:
        try:
            dia_inicio = int(m_intervalo_dias.group(1))
            dia_fim = int(m_intervalo_dias.group(2))

            data_inicio = ajustar_data_futura(dia_inicio)
            data_fim = ajustar_data_futura(dia_fim)

            if data_inicio and data_fim:
                if data_fim < data_inicio:
                    data_inicio, data_fim = data_fim, data_inicio

                atual = data_inicio
                while atual <= data_fim:
                    datas.append(atual.strftime("%Y-%m-%d"))
                    atual += timedelta(days=1)
        except Exception:
            pass

    # =========================================================
    # 2. múltiplos dias: "20, 21 e 22"
    # evita capturar números de hora quando já houver janela horária
    # =========================================================
    possui_janela_horaria = any([
        re.search(r"(?:até|ate)\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*h?\b", texto_lower),
        re.search(r"(?:a\s+partir\s+das?|depois\s+das?)\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*h?\b", texto_lower),
        re.search(r"\bdas?\s+([01]?\d|2[0-3])(?::([0-5]\d))?\s*(?:h)?\s*(?:às|as|ate|até|a)\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*h?\b", texto_lower),
    ])

    if not datas and not possui_janela_horaria:
        nums = re.findall(r"\b(\d{1,2})\b", texto_lower)
        for n in nums:
            try:
                d = ajustar_data_futura(int(n))
                if d:
                    datas.append(d.strftime("%Y-%m-%d"))
            except Exception:
                pass

    # =========================================================
    # 3. fallback parser padrão: hoje, amanhã, etc.
    # =========================================================
    if not datas:
        try:
            dt = interpretar_data_e_hora(texto)
            if dt:
                datas.append(dt.strftime("%Y-%m-%d"))
        except Exception:
            pass

    datas = sorted(set(datas))

    if not datas:
        return None

    # =========================================================
    # 4. BLOQUEIO TOTAL sempre prevalece
    # =========================================================
    if eh_fechamento:
        return {
            "acao": "bloquear_agenda_salao",
            "dados": {
                "datas": datas,
                "motivo": "fechado"
            }
        }

    # =========================================================
    # 5. intervalos completos: "das 10 às 15"
    # =========================================================
    m_intervalo_horas = re.search(
        r"\bdas?\s+([01]?\d|2[0-3])(?::([0-5]\d))?\s*(?:h)?\s*(?:às|as|ate|até|a)\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*h?\b",
        texto_lower
    )
    if m_intervalo_horas:
        h1 = int(m_intervalo_horas.group(1))
        m1 = int(m_intervalo_horas.group(2) or 0)
        h2 = int(m_intervalo_horas.group(3))
        m2 = int(m_intervalo_horas.group(4) or 0)

        inicio = f"{h1:02d}:{m1:02d}"
        fim = f"{h2:02d}:{m2:02d}"

        if inicio < fim:
            return {
                "acao": "definir_meio_periodo_salao",
                "dados": {
                    "datas": datas,
                    "inicio": inicio,
                    "fim": fim,
                    "motivo": "janela_especial"
                }
            }

    # =========================================================
    # 6. até X horas: "até 12h"
    # =========================================================
    m_ate = re.search(
        r"(?:até|ate)\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*h?\b",
        texto_lower
    )
    if m_ate:
        hora = int(m_ate.group(1))
        minuto = int(m_ate.group(2) or 0)

        return {
            "acao": "definir_meio_periodo_salao",
            "dados": {
                "datas": datas,
                "inicio": "08:00",
                "fim": f"{hora:02d}:{minuto:02d}",
                "motivo": "expediente_reduzido"
            }
        }

    # =========================================================
    # 7. a partir de X horas: "a partir das 13h"
    # =========================================================
    m_apartir = re.search(
        r"(?:a\s+partir\s+das?|depois\s+das?)\s*([01]?\d|2[0-3])(?::([0-5]\d))?\s*h?\b",
        texto_lower
    )
    if m_apartir:
        hora = int(m_apartir.group(1))
        minuto = int(m_apartir.group(2) or 0)

        return {
            "acao": "definir_meio_periodo_salao",
            "dados": {
                "datas": datas,
                "inicio": f"{hora:02d}:{minuto:02d}",
                "fim": "18:00",
                "motivo": "abertura_parcial"
            }
        }

    # =========================================================
    # 8. manhã / tarde
    # =========================================================
    sinais_manha = [
        "só de manhã", "so de manha",
        "somente de manhã", "somente de manha",
        "apenas de manhã", "apenas de manha",
        "só pela manhã", "so pela manha",
    ]
    if any(s in texto_lower for s in sinais_manha):
        return {
            "acao": "definir_meio_periodo_salao",
            "dados": {
                "datas": datas,
                "inicio": "08:00",
                "fim": "12:00",
                "motivo": "turno_manha"
            }
        }

    sinais_tarde = [
        "só à tarde", "so a tarde",
        "só de tarde", "so de tarde",
        "somente à tarde", "somente a tarde",
        "apenas à tarde", "apenas a tarde",
        "só pela tarde", "so pela tarde",
    ]
    if any(s in texto_lower for s in sinais_tarde):
        return {
            "acao": "definir_meio_periodo_salao",
            "dados": {
                "datas": datas,
                "inicio": "13:00",
                "fim": "18:00",
                "motivo": "turno_tarde"
            }
        }

    return None

def eh_confirmacao(txt: str) -> bool:
    """
    Confirmação genérica (sem depender de comando).
    """
    t = (txt or "").strip().lower()
    if "nao" in t or "não" in t:
        return False
    gatilhos = [
        "confirmar", "confirma", "confirme", "confirmo",   
        "pode agendar", "pode marcar", "agende", "marque",
        "fechar", "ok", "confirmado",
        "sim", "pode", "pode ser", "pode sim", "pode ir", "manda ver"
    ]
    return any(g in t for g in gatilhos)

def eh_desistencia_fluxo(txt: str) -> bool:
    t = normalizar(txt or "")

    sinais_fortes = [
        "cancelar",
        "cancela",
        "nao quero",
        "deixa pra la",
        "melhor nao",
        "nao precisa",
        "desisto",
    ]

    sinais_contexto = [
        "nao vou conseguir",
        "nao consigo",
        "tenho compromisso",
        "tenho reuniao",
        "nesse horario nao da",
        "depois vejo",
        "vou falar depois",
        "volto a falar",
        "deixar para depois",
    ]

    score = 0

    for s in sinais_fortes:
        if s in t:
            score += 2

    for s in sinais_contexto:
        if s in t:
            score += 1

    return score >= 2

def _tem_indicio_de_hora(txt: str) -> bool:
    """
    Evita que interpretar_data_e_hora chute 'amanhã' sem hora.
    Só tenta extrair dt quando houver indício de horário.
    """
    t = (txt or "").lower()
    return bool(
        re.search(r"\b\d{1,2}(:\d{2})?\b", t)
        or re.search(r"\b\d{1,2}\s*h\b", t)
        or "às" in t
        or " as " in t
    )


def extrair_servico_do_texto(texto_usuario: str, servicos_disponiveis: list) -> str | None:
    """
    Tenta mapear o texto do usuário para um serviço existente (lista).
    """
    if not servicos_disponiveis:
        return None
    txt = normalizar(texto_usuario)
    if not txt:
        return None

    for s in servicos_disponiveis:
        s_norm = normalizar(str(s))
        if s_norm and s_norm in txt:
            return str(s).strip()

    if len(txt.split()) <= 2:
        for s in servicos_disponiveis:
            if normalizar(str(s)) == txt:
                return str(s).strip()

    return None


async def validar_profissional_para_servico(dono_id: str, profissional: str | None, servico: str | None):
    """
    Valida se o profissional executa o serviço.
    Retorna:
      {
        "ok": bool,
        "validos": [nomes]
      }
    """
    if not profissional or not servico:
        return {"ok": False, "validos": []}

    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    # serviços do profissional escolhido
    servicos_prof = []
    for p in profs_dict.values():
        nomep = (p.get("nome") or "").strip()
        if normalizar(nomep) == normalizar(profissional):
            servicos_prof = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
            break

    if any(normalizar(servico) == normalizar(s) for s in servicos_prof):
        return {"ok": True, "validos": []}

    # lista de profissionais válidos para o serviço
    validos = []
    for p in profs_dict.values():
        nomep = (p.get("nome") or "").strip()
        servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
        if nomep and any(normalizar(servico) == normalizar(s) for s in servs):
            validos.append(nomep)

    return {"ok": False, "validos": validos}

# ----------------------------
# auditoria
# ----------------------------

def _audit_confirmacao(tag: str, ctx: dict, texto_usuario: str = ""):
    try:
        draft = ctx.get("draft_agendamento") or {}
        dados_conf = ctx.get("dados_confirmacao_agendamento") or {}

        print(
            f"🧪 [AUDIT-CONF:{tag}] "
            f"texto={texto_usuario!r} | "
            f"estado_fluxo={ctx.get('estado_fluxo')} | "
            f"aguardando_confirmacao_agendamento={ctx.get('aguardando_confirmacao_agendamento')} | "
            f"profissional_escolhido={ctx.get('profissional_escolhido')} | "
            f"servico={ctx.get('servico')} | "
            f"data_hora={ctx.get('data_hora')} | "
            f"ultima_opcao_profissionais={ctx.get('ultima_opcao_profissionais')}",
            flush=True
        )

        print(
            f"🧪 [AUDIT-CONF:{tag}:DRAFT] "
            f"profissional={draft.get('profissional')} | "
            f"servico={draft.get('servico')} | "
            f"data_hora={draft.get('data_hora')} | "
            f"modo_prechecagem={draft.get('modo_prechecagem')}",
            flush=True
        )

        print(
            f"🧪 [AUDIT-CONF:{tag}:DADOS_CONF] "
            f"profissional={dados_conf.get('profissional')} | "
            f"servico={dados_conf.get('servico')} | "
            f"data_hora={dados_conf.get('data_hora')} | "
            f"duracao={dados_conf.get('duracao')} | "
            f"descricao={dados_conf.get('descricao')}",
            flush=True
        )

    except Exception as e:
        print(f"⚠️ Falha em _audit_confirmacao({tag}): {e}", flush=True)


# ----------------------------
# Slots always-on
# ----------------------------

async def extrair_slots_e_mesclar(ctx: dict, texto_usuario: str, dono_id: str) -> dict:

    """
    Sempre-on: extrai slots em ctx + draft_agendamento.

    Regra principal:
    - se o usuário informou explicitamente profissional, serviço ou data/hora
      na mensagem atual, esse valor SOBRESCREVE o anterior.
    - não herda profissional/serviço/data_hora antigos quando a mensagem nova
      já trouxe novos slots claros.
    """
    # 🔥 blindagem obrigatória
    if not isinstance(ctx, dict):
        print(f"⚠️ [extrair_slots_e_mesclar] ctx inválido recebido: {ctx}", flush=True)

        if not isinstance(ctx, dict):
            print(f"⚠️ ctx inválido — mantendo anterior", flush=True)
            return ctx if isinstance(ctx, dict) else {}
    
    texto = (texto_usuario or "").strip()
    tnorm = normalizar(texto)
    draft = ctx.get("draft_agendamento") or {}

    # ---------------- profissionais ----------------
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]

    prof_detectado = None
    for nome in nomes_profs:
        if normalizar(nome) in tnorm:
            prof_detectado = nome
            break

    # ---------------- serviço ----------------
    servico_detectado = None

    def _match_servico(lista_servs):
        nonlocal servico_detectado
        for s in lista_servs or []:
            s_norm = normalizar(str(s))
            if s_norm and s_norm in tnorm:
                servico_detectado = str(s).strip()
                return True
        return False

    # 1) serviços do profissional detectado
    if prof_detectado:
        for p in profs_dict.values():
            if normalizar(p.get("nome", "")) == normalizar(prof_detectado):
                _match_servico(p.get("servicos") or [])
                break

    # 2) catálogo global
    if not servico_detectado:
        todos = []
        for p in profs_dict.values():
            todos.extend(p.get("servicos") or [])
        vistos = set()
        uniq = []
        for s in todos:
            s2 = str(s).strip()
            if s2 and s2 not in vistos:
                vistos.add(s2)
                uniq.append(s2)
        _match_servico(uniq)

    # ---------------- persistir slots textuais explícitos ----------------
    if prof_detectado:
        ctx["profissional_escolhido"] = prof_detectado
        draft["profissional"] = prof_detectado

    if servico_detectado:
        ctx["servico"] = servico_detectado
        draft["servico"] = servico_detectado

    # ---------------- data/hora ----------------
    dt_detectado = interpretar_data_e_hora(texto)

    print("🧪 [MESCLAR] texto=", texto, flush=True)
    print("🧪 [MESCLAR] dt_detectado=", dt_detectado, flush=True)

    tem_hora_explicita = bool(
        re.search(r"\b\d{1,2}:\d{2}\b", texto.lower())
        or re.search(r"\b\d{1,2}\s*h\b", texto.lower())
        or re.search(r"\b\d{1,2}h\d{2}\b", texto.lower())
        or " às " in f" {texto.lower()} "
        or " as " in f" {texto.lower()} "
    )

    # =========================================================
    # 🔥 extrai somente HORÁRIOS reais, não números soltos como dia 17
    # =========================================================
    hora_matches = []

    # 1) HH:MM  -> 10:00
    for h, m in re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", texto.lower()):
        hora_matches.append((h, m))

    # 2) às 10 / as 10 / 10h / 10 horas
    for h in re.findall(r"(?:\b(?:as|às)\s*([01]?\d|2[0-3])\b|\b([01]?\d|2[0-3])h\b|\b([01]?\d|2[0-3])\s*horas?\b)", texto.lower()):
        hora = next((x for x in h if x), None)
        if hora is not None:
            hora_matches.append((hora, "00"))

    # remove duplicados preservando ordem
    hora_matches = list(dict.fromkeys((str(int(h)), str(int(m)).zfill(2)) for h, m in hora_matches))

    if dt_detectado:

        # 🔥 NÃO limpar se está aguardando escolha de horário
        if (
            ctx.get("estado_fluxo") != "aguardando_escolha_horario"
            and not ctx.get("modo_escolha_horario")
        ):
            ctx["estado_fluxo"] = "agendando"

        # =========================================================
        # 🔥 CASO 1 — 1 horário → segue normal
        # =========================================================
        if len(hora_matches) == 1:
            hora = int(hora_matches[0][0])
            minuto = int(hora_matches[0][1] or 0)

            dt_final = dt_detectado.replace(
                hour=hora,
                minute=minuto,
                second=0,
                microsecond=0
            )

            iso = dt_final.isoformat()

            ctx["data_hora"] = iso
            draft["data_hora"] = iso

            # 🔥 limpa estado especial
            if ctx.get("modo_escolha_horario") or ctx.get("estado_fluxo") == "aguardando_escolha_horario":
                pass
            else:
                ctx["estado_fluxo"] = "agendando"

        # =========================================================
        # 🔥 CASO 2 — múltiplos horários → NÃO DECIDE
        # =========================================================
        elif len(hora_matches) > 1:

            dt_final = dt_detectado.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
           )

            iso = dt_final.isoformat()

            ctx["data_hora"] = iso
            draft["data_hora"] = iso

            # preserva slots já detectados
            if prof_detectado:
                ctx["profissional_escolhido"] = prof_detectado
                draft["profissional"] = prof_detectado

            if servico_detectado:
                ctx["servico"] = servico_detectado
                draft["servico"] = servico_detectado

            # 🔥 normaliza e remove duplicados
            horarios = sorted(
                set(f"{int(h[0]):02d}:{int(h[1] or 0):02d}" for h in hora_matches)
            )

            ctx["horarios_sugeridos"] = horarios
            ctx["estado_fluxo"] = "aguardando_escolha_horario"

        # =========================================================
        # 🔥 CASO 3 — sem hora → normal
        # =========================================================
        else:
            dt_final = dt_detectado.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

            iso = dt_final.isoformat()

            ctx["data_hora"] = iso
            draft["data_hora"] = iso

        # =========================================================
        # 🔥 salvar ultima consulta
        # =========================================================
        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}

        ctx["ultima_consulta"]["data_hora"] = iso

    # 🔥 persistir draft no contexto
    if draft:
        ctx["draft_agendamento"] = draft

    return ctx

def _tem_referencia_profissional_indireta(tnorm: str) -> bool:
    gat = [
        "ela", "ele", "dela", "dele", "dessa", "desse", "essa", "esse",
        "essa profissional", "esse profissional", "a moça", "o rapaz",
        "com ela", "com ele", "pra ela", "pra ele", "para ela", "para ele",
        "da última", "do último", "da ultima", "do ultimo",
        "dessa ai", "desse ai", "dessa aí", "desse aí",
        "dela aí", "dele aí", "dela ai", "dele ai"
    ]
    return any(g in tnorm for g in gat)


def resolver_profissional_referenciado(tnorm: str, profs_dict: dict, ctx: dict) -> str | None:
    """
    Resolve qual profissional o usuário está referenciando, com prioridade:
    1) nome explícito no texto
    2) profissional do fluxo (draft/profissional_escolhido)
    3) referência indireta (ela/dela/etc.) -> ultima_consulta/profissional_escolhido
    """
    # 1) nome explícito no texto
    for p in (profs_dict or {}).values():
        nomep = (p.get("nome") or "").strip()
        if nomep and normalizar(nomep) in tnorm:
            return nomep

    # 2) profissional do fluxo
    draft = (ctx or {}).get("draft_agendamento") or {}
    prof_fluxo = draft.get("profissional") or (ctx or {}).get("profissional_escolhido")
    if prof_fluxo:
        return prof_fluxo

    # 3) referência indireta -> última consulta / escolhido
    if _tem_referencia_profissional_indireta(tnorm):
        ult_prof = ((ctx or {}).get("ultima_consulta") or {}).get("profissional")
        if ult_prof:
            return ult_prof
        prof_ctx = (ctx or {}).get("profissional_escolhido")
        if prof_ctx:
            return prof_ctx

    return None


def extrair_servico_alvo_binario(tnorm: str, catalogo_servicos: list[str]) -> str | None:
    """
    Pega o 'X' em frases tipo:
    - "ela faz X?"
    - "tem X?"
    - "trabalha com X?"
    E tenta mapear para um serviço do catálogo.
    """
    if not catalogo_servicos:
        return None

    # tira pontuação básica
    t = re.sub(r"[?!.,;:]", " ", tnorm).strip()

    # padrões simples
    padroes = [
        r"\bfaz\s+(.+)$",
        r"\btem\s+(.+)$",
        r"\btrabalha\s+com\s+(.+)$",
        r"\boferece\s+(.+)$",
        r"\batende\s+(.+)$",
    ]

    alvo = None
    for pat in padroes:
        m = re.search(pat, t)
        if m:
            alvo = m.group(1).strip()
            break

    if not alvo:
        return None

    # normaliza alvo e tenta casar com catálogo
    alvo_n = normalizar(alvo)
    if not alvo_n:
        return None

    # match forte: catálogo contido no alvo (ou alvo contido no catálogo)
    for s in catalogo_servicos:
        sn = normalizar(s)
        if not sn:
            continue
        if sn in alvo_n or alvo_n in sn:
            return s

    return None

def tem_contexto_agendamento_ativo(ctx: dict) -> bool:
    ctx = ctx or {}
    draft = ctx.get("draft_agendamento") or {}
    ultima = ctx.get("ultima_consulta") or {}

    return bool(
        ctx.get("aguardando_confirmacao_agendamento")
        or ctx.get("servico")
        or ctx.get("profissional_escolhido")
        or ctx.get("data_hora")
        or draft.get("servico")
        or draft.get("profissional")
        or draft.get("data_hora")
        or ultima.get("profissional")
        or ultima.get("data_hora")
    )


def eh_confirmacao_pendente_ativa(ctx: dict) -> bool:
    ctx = ctx or {}
    return bool(ctx.get("aguardando_confirmacao_agendamento"))


def eh_reacao_a_sugestao(txt: str, ctx: dict) -> bool:
    """
    Reações/dúvidas do usuário quando já existe um fluxo de agendamento.
    Ex.: 'nossa sério que ela não consegue nesse horário?'
    """
    t = normalizar(txt or "")
    if not t:
        return False

    if not tem_contexto_agendamento_ativo(ctx):
        return False

    gatilhos = [
        "nossa", "que pena", "serio", "sério",
        "ela nao consegue", "ela não consegue",
        "nao consegue", "não consegue",
        "nao tem jeito", "não tem jeito",
        "lotado", "cheia", "cheio",
        "mesmo", "de verdade"
    ]
    return any(g in t for g in gatilhos)


def eh_escolha_de_alternativa(txt: str, ctx: dict) -> bool:
    """
    Detecta aceitação/troca de opção dentro de um fluxo já ativo.
    Ex.: '14:40', 'outro horário às 14:40', 'então marca esse'
    """
    t = normalizar(txt or "")
    if not t:
        return False

    if not tem_contexto_agendamento_ativo(ctx):
        return False

    if _tem_indicio_de_hora(t):
        return True

    gatilhos = [
        "outro horario", "outro horário",
        "esse horario", "esse horário",
        "esse", "esse outro",
        "entao marca esse", "então marca esse",
        "entao esse", "então esse",
        "mais tarde", "mais cedo",
        "com ela", "com ele", "com a", "com o",
        "pode ser", "fechado"
    ]
    return any(g in t for g in gatilhos)


def eh_continuacao_de_agendamento(txt: str, ctx: dict) -> bool:
    """
    Guarda-chuva para qualquer continuidade legítima de um fluxo já ativo.
    """
    if not tem_contexto_agendamento_ativo(ctx):
        return False

    t = normalizar(txt or "")
    if not t:
        return False

    if eh_confirmacao(t):
        return True

    if eh_escolha_de_alternativa(t, ctx):
        return True

    if eh_reacao_a_sugestao(t, ctx):
        return True

    # frases como "então marca", "vamos nessa", etc.
    gatilhos_fluxo = [
        "marca", "agenda", "entao", "então", "vamos", "segue", "faz assim"
    ]
    if any(g in t for g in gatilhos_fluxo):
        return True

    return False


# ----------------------------
# Router principal
# ----------------------------

async def roteador_principal(user_id: str, mensagem: str, update=None, context=None):
    print("🚨 [principal_router] Arquivo carregado")

    texto_usuario = (mensagem or "").strip()
    texto_lower = texto_usuario.lower().strip()
    tnorm = normalizar(texto_usuario)

    ctx = await carregar_contexto_temporario(user_id) or {}

    historico = ctx.get("historico_texto") or []
    if texto_usuario:
        historico.append(texto_usuario)

    ctx["historico_texto"] = historico[-2:]
    await salvar_contexto_temporario(user_id, {"historico_texto": ctx["historico_texto"]})

    estado_fluxo = (ctx.get("estado_fluxo") or "idle").strip().lower()
    draft = ctx.get("draft_agendamento") or {}

    # 🔥 BLOQUEIO DE SAUDAÇÃO (ANTES DE QUALQUER FLUXO OU GPT)
    saudacoes_usuario = [
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
        "e ai", "e aí", "eai", "opa", "oie"
    ]

    if estado_fluxo == "idle" and texto_lower in saudacoes_usuario:
        return await _send_and_stop(
            context,
            user_id,
            "👋 Olá! Como posso te ajudar hoje?"
        )

    # ✅ 0) Consulta informativa só quando está IDLE (não atrapalha o fluxo de agendamento)
    if estado_fluxo == "idle":
        from services.informacao_service import responder_consulta_informativa
        resposta_informativa = await responder_consulta_informativa(mensagem, user_id)
        if resposta_informativa:
            print("🔍 Consulta informativa detectada (idle). Respondendo diretamente.")
            return await _send_and_stop(context, user_id, resposta_informativa)

    # 🔐 dono do negócio
    dono_id = await obter_id_dono(user_id)

    # ✅ Guard: perguntas de catálogo/menu NÃO podem cair no fluxo legado (evita GPT alucinar lista)
    intencao_catalogo = any(x in tnorm for x in [
        # lista por profissional (A1)
        "cada profissional", "servicos de cada", "serviços de cada",
        "todos os profissionais", "todos profissionais", "todas as profissionais", "todas profissionais",
        "separado por nome", "separados por nome", "por profissional",

        # menus (A)
        "quais profissionais", "lista de profissionais", "me diz os profissionais",
        "quais servicos", "quais serviços", "lista de servicos", "lista de serviços",
        "quais voce tem", "quais você tem", "quem voce tem", "quem você tem",

        # binários/busca (A0)
        "quem faz", "quem atende", "ela faz", "ele faz", "dela", "dele"
    ])

    # ✅ Se existe sessão ativa do fluxo legado, só respeita se NÃO for intenção de catálogo
    sessao = await pegar_sessao(user_id)

    # ✅ Só deixa a sessão legada assumir quando NÃO estamos no fluxo novo de agendamento
    if (not intencao_catalogo) and sessao and sessao.get("estado") and estado_fluxo != "agendando":
        print(f"🔁 Sessão ativa: {sessao['estado']}")
        resposta_fluxo = await tratar_mensagem_gpt(user_id, mensagem)
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_fluxo})
        return resposta_fluxo

    FUSO_BR = pytz.timezone("America/Sao_Paulo")

    def _agora_br_naive():
        return datetime.now(FUSO_BR).replace(tzinfo=None)

    def _dt_from_iso_naive(iso_str: str):
        try:
            return datetime.fromisoformat(iso_str)
        except Exception:
            return None

    async def _perguntar_amanha_mesmo_horario_e_bloquear(data_hora_iso: str):
        """
        Produto:
        - Se o horário passou e o usuário não informou serviço/profissional,
          primeiro coletar 1 dos dois (serviço OU profissional), com texto humano.
        - Só depois oferecer 'amanhã mesmo horário'.
        """
        draft_local = ctx.get("draft_agendamento") or {}
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft_local.get("servico") or ctx.get("servico")

        # prepara bloqueio de amanhã
        ctx["estado_fluxo"] = "aguardando_data"
        ctx["pergunta_amanha_mesmo_horario"] = True
        ctx["data_hora_pendente"] = data_hora_iso
        ctx["data_hora"] = None

        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["data_hora"] = None

        await salvar_contexto_temporario(user_id, ctx)

        # ✅ primeiro coletar mínimo (serviço OU profissional)
        if not (prof or servico):
            return await _send_and_stop(
                context,
                user_id,
                (
                    f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou.\n"
                    "Só me diz rapidinho: *qual serviço* você quer fazer (ou *com qual profissional* prefere), "
                    "pra eu conferir a agenda certinho."
                )
            )

        # ✅ já tem mínimo → agora sim oferecer amanhã mesmo horário
        return await _send_and_stop(
            context,
            user_id,
            (
                f"Esse horário (*{formatar_data_hora_br(data_hora_iso)}*) já passou.\n"
                "Quer *amanhã no mesmo horário* ou prefere outro horário?"
            )
        )

    # =========================================================
    # PRIORIDADE MÁXIMA — CONFIRMAÇÃO FINAL DE AGENDAMENTO
    # =========================================================
    if eh_confirmacao_pendente_ativa(ctx) and eh_confirmacao(texto_lower):

        _audit_confirmacao("BLOCO_PENDENTE_ENTRADA", ctx, texto_usuario)

        dados_confirmacao = ctx.get("dados_confirmacao_agendamento") or {}
        draft = ctx.get("draft_agendamento") or {}

        profissional = (
            dados_confirmacao.get("profissional")
            or draft.get("profissional")
            or ctx.get("profissional_escolhido")
        )

        servico = (
            dados_confirmacao.get("servico")
            or draft.get("servico")
            or ctx.get("servico")
        )

        data_hora = (
            dados_confirmacao.get("data_hora")
            or draft.get("data_hora")
            or ctx.get("data_hora")
        )

        duracao = dados_confirmacao.get("duracao")
        if not duracao and servico:
            duracao = estimar_duracao(servico)

        if profissional and servico and data_hora:
            dados_exec = {
                "profissional": profissional,
                "servico": servico,
                "data_hora": data_hora,
                "duracao": duracao,
                "descricao": formatar_descricao_evento(servico, profissional),
            }

            ctx["aguardando_confirmacao_agendamento"] = False
            ctx.pop("dados_confirmacao_agendamento", None)
            ctx.pop("ultima_opcao_profissionais", None)
            await salvar_contexto_temporario(user_id, ctx)

            print("🧪 [AUDIT-CONF:BLOCO_PENDENTE] EXECUTANDO criar_evento direto", flush=True)
            return await executar_acao_gpt(update, context, "criar_evento", dados_exec)

        print("🧪 [AUDIT-CONF:BLOCO_PENDENTE] DADOS_INSUFICIENTES -> REABRINDO FLUXO", flush=True)
        return await _send_and_stop(
            context,
            user_id,
            "Perdi parte dos dados da confirmação. Me diga novamente o profissional, serviço e horário para eu concluir."
        )

    # =========================================================
    # ✅ (A0) Intercept binário: "ela faz X?" / "quem faz X?"
    # =========================================================
    profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

    # catálogo global (união)
    catalogo_global = []
    for p in profs_dict.values():
        for s in (p.get("servicos") or []):
            s = str(s).strip()
            if s:
                catalogo_global.append(s)
    catalogo_global = sorted(set(catalogo_global), key=lambda x: normalizar(x))

    # 1) "quem faz X?" -> retorna profissionais que fazem
    if "quem faz" in tnorm or "quem atende" in tnorm:
        serv_alvo = extrair_servico_alvo_binario(tnorm, catalogo_global)
        if serv_alvo:
            fazem = []
            for p in profs_dict.values():
                nomep = (p.get("nome") or "").strip()
                servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                if nomep and any(normalizar(serv_alvo) == normalizar(x) for x in servs):
                    fazem.append(nomep)

            if fazem:
                txt = f"*Quem faz {serv_alvo}:*\n- " + "\n- ".join(sorted(set(fazem)))
                # se estiver em fluxo, puxa para seleção
                if estado_fluxo in ("aguardando_profissional", "aguardando_servico", "aguardando serviço", "aguardando_serviço"):
                    txt += "\n\nCom quem você prefere?"
                return await _send_and_stop(context, user_id, txt)
            else:
                return await _send_and_stop(context, user_id, f"Aqui eu não encontrei ninguém cadastrado para *{serv_alvo}*.")

    # 2) "ela faz X?" / "tem X?" -> responde sim/não (com base no profissional referenciado)
    # Só roda se houver pista de binário
    if any(x in tnorm for x in ["faz ", "tem ", "trabalha com", "oferece ", "atende "]):
        prof_ref = resolver_profissional_referenciado(tnorm, profs_dict, ctx)
        if prof_ref:
            # catálogo do profissional
            servs_prof = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof_ref):
                    servs_prof = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                    break

            serv_alvo = extrair_servico_alvo_binario(tnorm, servs_prof or catalogo_global)
            if serv_alvo:
                tem = any(normalizar(serv_alvo) == normalizar(x) for x in (servs_prof or []))
                if tem:
                    return await _send_and_stop(context, user_id, f"Sim — *{prof_ref}* faz *{serv_alvo}* ✅")
                else:
                    # sugere quem faz (se existir)
                    fazem = []
                    for p in profs_dict.values():
                        nomep = (p.get("nome") or "").strip()
                        servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                        if nomep and any(normalizar(serv_alvo) == normalizar(x) for x in servs):
                            fazem.append(nomep)
                    if fazem:
                        return await _send_and_stop(
                            context,
                            user_id,
                            f"*{prof_ref}* não faz *{serv_alvo}*.\nQuem faz: " + ", ".join(sorted(set(fazem))) + "."
                        )
                    return await _send_and_stop(context, user_id, f"*{prof_ref}* não faz *{serv_alvo}*.")

    # =========================================================
    # ✅ (A1) Intercept: serviços de TODOS os profissionais (por nome)
    # =========================================================
    gatilhos_a1 = [
        "cada profissional",
        "servicos de cada", "serviços de cada",
        "servicos de todas", "serviços de todas",
        "todos profissionais", "todos os profissionais",
        "todas profissionais", "todas as profissionais",
        "separado por nome", "separados por nome",
        "por profissional",
        "lista de servicos", "lista de serviços"
    ]

    if any(x in tnorm for x in gatilhos_a1):
        if not profs_dict:
            return await _send_and_stop(context, user_id, "Ainda não há profissionais cadastrados.")

        linhas = []
        for p in profs_dict.values():
            nome = (p.get("nome") or "").strip()

            raw_servs = p.get("servicos")
            if isinstance(raw_servs, str):
                servs = [s.strip() for s in raw_servs.split(",") if s.strip()]
            elif isinstance(raw_servs, dict):
                servs = [str(k).strip() for k in raw_servs.keys() if str(k).strip()]
            else:
                servs = [str(s).strip() for s in (raw_servs or []) if str(s).strip()]

            if nome:
                if servs:
                    linhas.append(f"- *{nome}:* " + ", ".join(sorted(set(servs), key=lambda x: normalizar(x))))
                else:
                    linhas.append(f"- *{nome}:* (sem serviços cadastrados)")

        txt = "*Serviços por profissional:*\n" + "\n".join(linhas)
        return await _send_and_stop(context, user_id, txt)

    # =========================================================
    # ✅ (A) Intercept contextual: listar profissionais/serviços SOMENTE quando o usuário pede menu
    # =========================================================

    # intenção explícita de menu
    quer_menu_prof = any(x in tnorm for x in [
        "quais profissionais", "quais profissional", "quem atende", "quem voce tem", "quem você tem", "quem tem",
        "me diz os profissionais", "lista de profissionais", "opcoes de profissionais", "opções de profissionais"
    ])

    quer_menu_serv = any(x in tnorm for x in [
        "quais servicos", "quais serviços", "quais voce tem", "quais você tem",
        "me diz os servicos", "me diz os serviços", "lista de servicos", "lista de serviços",
        "opcoes de servicos", "opções de serviços", "quais são os serviços", "quais sao os servicos"
    ])

    # "quem faz" (genérico)
    quem_faz_generico = ("quem faz" in tnorm)

    # em fluxo, só abre menu se usuário pediu menu (não por estar aguardando)
    if estado_fluxo == "aguardando_profissional":
        quer_profissionais = bool(quer_menu_prof or tnorm in ("quais", "quem"))
        quer_servicos = False
    elif estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        quer_servicos = bool(quer_menu_serv or tnorm == "quais")
        quer_profissionais = False
    else:
        quer_profissionais = bool(quer_menu_prof or quem_faz_generico)
        quer_servicos = bool(quer_menu_serv and not quer_profissionais)

    if quer_profissionais or quer_servicos or (quem_faz_generico and estado_fluxo == "idle"):
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        if not profs_dict:
            return await _send_and_stop(context, user_id, "Ainda não há profissionais cadastrados.")

        nomes = []
        servicos = set()
        for p in profs_dict.values():
            nome = (p.get("nome") or "").strip()
            if nome:
                nomes.append(nome)
            for s in (p.get("servicos") or []):
                s = str(s).strip()
                if s:
                    servicos.add(s)

        # 🔎 Resolve profissional (nome explícito OU pronome "ela/dela" via contexto)
        prof_citado = resolver_profissional_referenciado(tnorm, profs_dict, ctx)

        if quer_servicos and not quer_profissionais:
            if prof_citado:
                # ✅ Serviços somente do profissional citado
                servs_prof = []
                for p in profs_dict.values():
                    if normalizar(p.get("nome", "")) == normalizar(prof_citado):
                        servs_prof = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                        break

                if servs_prof:
                    txt = f"*Serviços da {prof_citado}:*\n- " + "\n- ".join(sorted(set(servs_prof)))
                else:
                    txt = f"Não encontrei serviços cadastrados para *{prof_citado}*."
            else:
                # ✅ Serviços gerais do salão (união de todos)
                txt = "*Serviços do salão:*\n- " + "\n- ".join(sorted(servicos)) if servicos else "Ainda não há serviços cadastrados."
        else:
            txt = "*Profissionais:*\n- " + "\n- ".join(sorted(set(nomes)))

        # ✅ Só faz pergunta de coleta se o menu foi pedido DURANTE o fluxo
        menu_dentro_do_fluxo = (estado_fluxo in ("aguardando_profissional", "aguardando_servico", "aguardando serviço", "aguardando_serviço"))

        if menu_dentro_do_fluxo:
            if estado_fluxo == "aguardando_profissional":
                txt += "\n\nQual você prefere?"
            elif estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
                # se o usuário perguntou serviços de um profissional específico, pode perguntar qual vai ser
                # mas só se isso fizer sentido dentro do fluxo (aqui faz)
                txt += "\n\nQual serviço vai ser?"

        return await _send_and_stop(context, user_id, txt)
    # =========================================================
    # ✅ (B) SEMPRE-ON: extrair e mesclar slots (prof/serv/dt)
    # =========================================================
    try:
        print(
            f"🧪 [B-INICIO] texto={texto_usuario} | "
            f"estado_fluxo={ctx.get('estado_fluxo')} | "
            f"modo_escolha_horario={ctx.get('modo_escolha_horario')} | "
            f"horarios_sugeridos={ctx.get('horarios_sugeridos')} | "
            f"data_hora={ctx.get('data_hora')} | "
            f"draft={ctx.get('draft_agendamento')}",
            flush=True
        )

        print(
            f"🧪 [ANTES IF ESCOLHA] cond1={ctx.get('modo_escolha_horario')} | "
            f"cond2={(ctx.get('estado_fluxo') or '').strip().lower() == 'aguardando_escolha_horario'} | "
            f"estado_fluxo_raw={ctx.get('estado_fluxo')}",
            flush=True
        )

        # =========================================================
        # 🔥 PRIORIDADE ABSOLUTA — ESCOLHA DE HORÁRIO SUGERIDO
        # PRECISA vir antes do extrair_slots_e_mesclar
        # =========================================================
        if (
            ctx.get("modo_escolha_horario")
            or (ctx.get("estado_fluxo") or "").strip().lower() == "aguardando_escolha_horario"
        ):
            print(
                f"🧪 [ESCOLHA PRIORIDADE TOTAL] texto={texto_usuario} | "
                f"estado_fluxo={ctx.get('estado_fluxo')} | "
                f"modo_escolha_horario={ctx.get('modo_escolha_horario')} | "
                f"horarios_sugeridos={ctx.get('horarios_sugeridos')} | "
                f"data_hora={ctx.get('data_hora')} | "
                f"draft={ctx.get('draft_agendamento')}",
                flush=True
            )

            texto_norm = (texto_usuario or "").strip().lower().replace("às", "as")
            horarios_sugeridos = ctx.get("horarios_sugeridos") or []
            opcoes_hora_profissional = ctx.get("opcoes_hora_profissional") or []
            melhor_sugestao = ctx.get("melhor_sugestao") or {}
            matches = re.findall(r"\b(?:as\s*)?(\d{1,2})(?::(\d{2}))?\b", texto_norm)

            print(f"🧪 [TESTE-DESISTENCIA] texto_usuario={texto_usuario}", flush=True)
            print(f"🧪 [TESTE-DESISTENCIA] texto_normalizado={normalizar(texto_usuario)}", flush=True)
            print(f"🧪 [TESTE-DESISTENCIA] retorno={eh_desistencia_fluxo(texto_usuario)}", flush=True)

            # 🔥 INTERCEPTAÇÃO DE DESISTÊNCIA DENTRO DA ESCOLHA
            if eh_desistencia_fluxo(texto_usuario):
                print("🧪 [DESISTENCIA DETECTADA] Encerrando fluxo...", flush=True)

                await limpar_contexto_agendamento(user_id)

                ctx.clear()
                ctx["estado_fluxo"] = "idle"

                await _send_and_stop(
                    context,
                    user_id,
                    "Perfeito. Não vou agendar nada então. Quando quiser, é só me chamar."
                )

                raise ApplicationHandlerStop

            def _extrair_profissional_citado(texto: str, nomes_validos: list[str]) -> str | None:
                txt = normalizar(texto or "")
                for nome in nomes_validos:
                    if normalizar(nome) in txt:
                        return nome
                return None

            async def _resolver_escolha_para_confirmacao(
                hora_escolhida: str,
                profissional: str,
                user_id: str,
                servico: str | None,
            ):
                data_base = ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora")
                if not data_base:
                    return None

                try:
                    base = datetime.fromisoformat(data_base)
                    hh, mm = map(int, hora_escolhida.split(":"))
                except Exception:
                    return None

                nova_data_hora = base.replace(
                    hour=hh,
                    minute=mm,
                    second=0,
                    microsecond=0
                ).isoformat()

                draft = ctx.get("draft_agendamento") or {}
                servico = (
                    ctx.get("servico")
                    or draft.get("servico")
                    or (ctx.get("dados_anteriores") or {}).get("servico")
                )

                data_ref = nova_data_hora.split("T")[0]
                hora_ref = nova_data_hora.split("T")[1][:5]

                validacao_horario = await validar_horario_funcionamento(
                    user_id=id_dono,
                    data_iso=data_ref,
                    hora_inicio=hora_ref,
                    duracao_min=estimar_duracao(servico) if servico else 0,
                )

                if not validacao_horario.get("permitido"):
                    return {
                        "erro": "fora_do_expediente",
                        "nova_data_hora": nova_data_hora,
                    }

                draft["data_hora"] = nova_data_hora
                if profissional:
                    draft["profissional"] = profissional
                if servico:
                    draft["servico"] = servico

                ctx["data_hora"] = nova_data_hora
                ctx["hora_confirmada"] = True
                ctx["draft_agendamento"] = draft

                if profissional:
                    ctx["profissional_escolhido"] = profissional

                ctx.pop("modo_escolha_horario", None)
                ctx.pop("horarios_sugeridos", None)
                ctx["aguardando_confirmacao_agendamento"] = False
                ctx.pop("dados_confirmacao_agendamento", None)

                ctx["dados_anteriores"] = {
                    "profissional": profissional,
                    "servico": servico,
                    "data_hora": nova_data_hora
                }

                if servico and profissional:
                    ctx["estado_fluxo"] = "agendando"
                    ctx["aguardando_confirmacao_agendamento"] = True
                    ctx["ultima_acao"] = "criar_evento"
                    ctx["dados_confirmacao_agendamento"] = {
                        "profissional": profissional,
                        "servico": servico,
                        "data_hora": nova_data_hora,
                        "duracao": estimar_duracao(servico),
                        "descricao": formatar_descricao_evento(servico, profissional),
                    }
                else:
                    if servico and not profissional:
                        ctx["estado_fluxo"] = "aguardando_profissional"
                    elif profissional and not servico:
                        ctx["estado_fluxo"] = "aguardando_servico"
                    else:
                        ctx["estado_fluxo"] = "idle"

                    ctx["aguardando_confirmacao_agendamento"] = False
                    ctx["ultima_acao"] = None
                    ctx["dados_confirmacao_agendamento"] = None

                return {
                    "nova_data_hora": nova_data_hora,
                    "servico": servico,
                    "profissional": profissional
                }

            # ---------------------------------------------------------
            # NOVO: confirmação curta usa a melhor sugestão
            # Ex.: "pode sim", "fechado", "ok", "confirmar"
            # ---------------------------------------------------------
            if eh_confirmacao(texto_norm) and melhor_sugestao:
                hora_escolhida = str(melhor_sugestao.get("hora") or "").strip()
                prof_escolhido = str(melhor_sugestao.get("profissional") or "").strip()

                if hora_escolhida and prof_escolhido:
                    resolvido = await _resolver_escolha_para_confirmacao(
                        hora_escolhida,
                        prof_escolhido,
                        user_id,
                        servico,
                    )

                    if resolvido and resolvido.get("erro") == "fora_do_expediente":

                        tentativa = await resolver_fora_do_expediente(
                        user_id=user_id,
                        data_iso=data_ref,
                        hora_inicio=hora_ref,
                        duracao_min=estimar_duracao(servico),
                        servico=servico,
                        profissional=profissional,
                    )

                    if tentativa.get("ok"):
                        horario = tentativa.get("horario")
                        nova_data_hora = tentativa.get("data_hora")

                        if nova_data_hora:
                            ctx["data_hora"] = nova_data_hora

                            draft = ctx.get("draft_agendamento") or {}
                            draft["data_hora"] = nova_data_hora
                            ctx["draft_agendamento"] = draft

                            await salvar_contexto_temporario(user_id, ctx)

                        return await _send_and_stop_ctx(
                            context,
                            user_id,
                            "Infelizmente esse horário fica fora do nosso expediente 😕\n\n"
                            f"O horário mais próximo que tenho disponível é às *{horario}*.\n"
                            "Posso agendar pra você? 😊",
                            ctx,
                            texto_usuario,
                        )

                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        "❌ Não consegui encaixar esse horário. Me diga outro que eu verifico pra você.",
                        ctx,
                        texto_usuario,
                    )

                    if resolvido:
                        nova_data_hora = resolvido["nova_data_hora"]
                        servico = resolvido["servico"]
                        profissional = resolvido["profissional"]

                        print(
                            f"🔥 [ESCOLHA_HORARIO_CONFIRMACAO_CURTA] nova_data_hora={nova_data_hora} | "
                            f"estado_fluxo={ctx.get('estado_fluxo')} | "
                            f"profissional={profissional} | "
                            f"servico={servico}",
                            flush=True
                        )

                        await salvar_contexto_temporario(user_id, ctx)

                        if servico and profissional:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — *{servico}* com *{profissional}* "
                                f"em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Posso confirmar esse horário?"
                            )

                        if servico and not profissional:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — *{servico}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Qual profissional você prefere?"
                            )

                        if profissional and not servico:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — com *{profissional}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Qual serviço você quer fazer?"
                            )

                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Perfeito — *{formatar_data_hora_br(nova_data_hora)}*.\n"
                            "Agora me diga o serviço e o profissional."
                        )

            # ---------------------------------------------------------
            # NOVO: tenta interpretar hora + profissional juntos
            # Ex.: "15 com a Carla", "Carla às 16"
            # ---------------------------------------------------------
            hora_escolhida = None
            prof_escolhido = None

            if len(matches) >= 1:
                hora = int(matches[0][0])
                minuto = int(matches[0][1] or 0)
                hora_escolhida = f"{hora:02d}:{minuto:02d}"

            nomes_validos = sorted(
                {str(o.get("profissional") or "").strip() for o in opcoes_hora_profissional if o.get("profissional")}
            )
            prof_escolhido = _extrair_profissional_citado(texto_usuario, nomes_validos)

            # se falou só hora, pega o melhor profissional daquela hora
            if hora_escolhida and not prof_escolhido and opcoes_hora_profissional:
                candidatos = [o for o in opcoes_hora_profissional if str(o.get("hora")) == hora_escolhida]
                if candidatos:
                    if (
                        melhor_sugestao
                        and str(melhor_sugestao.get("hora") or "").strip() == hora_escolhida
                        and str(melhor_sugestao.get("profissional") or "").strip()
                    ):
                        prof_escolhido = str(melhor_sugestao.get("profissional")).strip()
                    else:
                        prof_escolhido = str(candidatos[0].get("profissional") or "").strip()

            # se falou só profissional, pega o melhor horário daquele profissional
            if prof_escolhido and not hora_escolhida and opcoes_hora_profissional:
                candidatos = [o for o in opcoes_hora_profissional if str(o.get("profissional") or "").strip() == prof_escolhido]
                if candidatos:
                    if (
                        melhor_sugestao
                        and str(melhor_sugestao.get("profissional") or "").strip() == prof_escolhido
                        and str(melhor_sugestao.get("hora") or "").strip()
                    ):
                        hora_escolhida = str(melhor_sugestao.get("hora")).strip()
                    else:
                        hora_escolhida = str(candidatos[0].get("hora") or "").strip()

            # valida se o par hora + profissional realmente existe nas opções
            if hora_escolhida and prof_escolhido and opcoes_hora_profissional:
                par_valido = None
                for op in opcoes_hora_profissional:
                    if (
                        str(op.get("hora") or "").strip() == hora_escolhida
                        and str(op.get("profissional") or "").strip() == prof_escolhido
                    ):
                        par_valido = op
                        break

                if par_valido:
                    resolvido = await _resolver_escolha_para_confirmacao(
                        hora_escolhida,
                        prof_escolhido,
                        user_id,
                        servico,
                    )

                    if resolvido and resolvido.get("erro") == "fora_do_expediente":
                        return await _send_and_stop_ctx(
                            context,
                            user_id,
                            "Esse horário está fora do expediente desse dia. Me diga outro horário que eu verifico para você.",
                            ctx,
                            texto_usuario,
                        )

                    if resolvido:
                        nova_data_hora = resolvido["nova_data_hora"]
                        servico = resolvido["servico"]
                        profissional = resolvido["profissional"]

                        print(
                            f"🔥 [ESCOLHA_HORARIO_PAR_VALIDO] nova_data_hora={nova_data_hora} | "
                            f"estado_fluxo={ctx.get('estado_fluxo')} | "
                            f"profissional={profissional} | "
                            f"servico={servico}",
                            flush=True
                        )

                        await salvar_contexto_temporario(user_id, ctx)

                        if servico and profissional:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — *{servico}* com *{profissional}* "
                                f"em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Posso confirmar esse horário?"
                            )

                        if servico and not profissional:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — *{servico}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Qual profissional você prefere?"
                            )

                        if profissional and not servico:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — com *{profissional}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Qual serviço você quer fazer?"
                            )

                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Perfeito — *{formatar_data_hora_br(nova_data_hora)}*.\n"
                            "Agora me diga o serviço e o profissional."
                        )

            # ---------------------------------------------------------
            # LEGADO: continua aceitando hora explícita das sugestões
            # ---------------------------------------------------------
            if len(matches) == 1:
                hora = int(matches[0][0])
                minuto = int(matches[0][1] or 0)
                hora_escolhida = f"{hora:02d}:{minuto:02d}"

                horario_match = None
                for faixa in horarios_sugeridos:
                    inicio = faixa.split(" - ")[0].strip()
                    if inicio == hora_escolhida:
                        horario_match = faixa
                        break

                if horario_match:
                    data_base = ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora")

                    if data_base:
                        base = datetime.fromisoformat(data_base)

                        nova_data_hora = base.replace(
                            hour=hora,
                            minute=minuto,
                            second=0,
                            microsecond=0
                        ).isoformat()

                        ctx["data_hora"] = nova_data_hora
                        ctx["hora_confirmada"] = True

                        draft = ctx.get("draft_agendamento") or {}
                        draft["data_hora"] = nova_data_hora
                        ctx["draft_agendamento"] = draft

                        ctx.pop("modo_escolha_horario", None)
                        ctx.pop("horarios_sugeridos", None)
                        ctx["aguardando_confirmacao_agendamento"] = False
                        ctx.pop("dados_confirmacao_agendamento", None)

                        servico = (
                            ctx.get("servico")
                            or draft.get("servico")
                            or (ctx.get("dados_anteriores") or {}).get("servico")
                        )
                        profissional = (
                            ctx.get("profissional_escolhido")
                            or draft.get("profissional")
                            or (ctx.get("dados_anteriores") or {}).get("profissional")
                        )

                        ctx["dados_anteriores"] = {
                            "profissional": profissional,
                            "servico": servico,
                            "data_hora": nova_data_hora
                        }

                        if servico and profissional:
                            ctx["estado_fluxo"] = "agendando"
                            ctx["aguardando_confirmacao_agendamento"] = True
                            ctx["ultima_acao"] = "criar_evento"
                            ctx["dados_confirmacao_agendamento"] = {
                                "profissional": profissional,
                                "servico": servico,
                                "data_hora": nova_data_hora,
                                "duracao": estimar_duracao(servico),
                                "descricao": formatar_descricao_evento(servico, profissional),
                            }
                        else:
                            if servico and not profissional:
                                ctx["estado_fluxo"] = "aguardando_profissional"
                            elif profissional and not servico:
                                ctx["estado_fluxo"] = "aguardando_servico"
                            else:
                                ctx["estado_fluxo"] = "idle"

                            ctx["aguardando_confirmacao_agendamento"] = False
                            ctx["ultima_acao"] = None
                            ctx["dados_confirmacao_agendamento"] = None

                        print(
                            f"🔥 [ESCOLHA_HORARIO] nova_data_hora={nova_data_hora} | "
                            f"estado_fluxo={ctx.get('estado_fluxo')} | "
                            f"ctx_data_hora={ctx.get('data_hora')} | "
                            f"draft_data_hora={(ctx.get('draft_agendamento') or {}).get('data_hora')} | "
                            f"dados_confirmacao={ctx.get('dados_confirmacao_agendamento')}",
                            flush=True
                        )

                        await salvar_contexto_temporario(user_id, ctx)

                        if servico and profissional:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — *{servico}* com *{profissional}* "
                                f"em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Posso confirmar esse horário?"
                            )

                        if servico and not profissional:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — *{servico}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Qual profissional você prefere?"
                            )

                        if profissional and not servico:
                            return await _send_and_stop(
                                context,
                                user_id,
                                f"Perfeito — com *{profissional}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                                "Qual serviço você quer fazer?"
                            )

                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Perfeito — *{formatar_data_hora_br(nova_data_hora)}*.\n"
                            "Agora me diga o serviço e o profissional."
                        )

            # fallback: usuário respondeu errado ou fora das opções
            if horarios_sugeridos:
                opcoes = " ou ".join(
                    h.split(" - ")[0].strip() if " - " in str(h) else str(h).strip()
                    for h in horarios_sugeridos
                )

                if melhor_sugestao:
                    hora_melhor = str(melhor_sugestao.get("hora") or "").strip()
                    prof_melhor = str(melhor_sugestao.get("profissional") or "").strip()

                    if hora_melhor and prof_melhor:
                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Você pode me dizer um dos horários sugeridos, como {opcoes}, "
                            f"ou simplesmente confirmar a melhor opção: *{hora_melhor} com {prof_melhor}*."
                        )

                return await _send_and_stop(
                    context,
                    user_id,
                    f"Me diga um dos horários sugeridos, por exemplo: {opcoes}."
                )

            return await _send_and_stop(
                context,
                user_id,
                "Me diga o horário que você prefere."
            )

        # novo pedido de agendamento não deve herdar resíduos de conflito/confirmação anterior
        if eh_gatilho_agendar(texto_lower):
            tnorm_msg = normalizar(texto_usuario)

            profs_dict_tmp = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            nomes_tmp = [str(p.get("nome", "")).strip() for p in profs_dict_tmp.values() if p.get("nome")]

            tem_profissional_expresso = any(normalizar(nome) in tnorm_msg for nome in nomes_tmp)
            tem_data_explicitada = _tem_indicio_de_hora(texto_usuario)

            servicos_tmp = []
            for p in profs_dict_tmp.values():
                servicos_tmp.extend(
                    [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
                )

            servicos_tmp = list(dict.fromkeys(servicos_tmp))
            tem_servico_explicito = any(normalizar(s) in tnorm_msg for s in servicos_tmp)

            ctx.pop("sugestoes", None)
            ctx.pop("alternativa_profissional", None)
            ctx.pop("dados_confirmacao_agendamento", None)
            ctx["aguardando_confirmacao_agendamento"] = False
            ctx["ultima_opcao_profissionais"] = []

            if tem_profissional_expresso and not tem_servico_explicito:
                ctx.pop("servico", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("servico", None)

            if tem_profissional_expresso and not tem_data_explicitada:
                ctx.pop("data_hora", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("data_hora", None)

            if tem_servico_explicito and not tem_profissional_expresso:
                ctx.pop("profissional_escolhido", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("profissional", None)

            if tem_servico_explicito and not tem_data_explicitada:
                ctx.pop("data_hora", None)
                if isinstance(ctx.get("draft_agendamento"), dict):
                    ctx["draft_agendamento"].pop("data_hora", None)

            if isinstance(ctx.get("ultima_consulta"), dict):
                if not tem_data_explicitada:
                    ctx["ultima_consulta"].pop("data_hora", None)
                if not tem_profissional_expresso:
                    ctx["ultima_consulta"].pop("profissional", None)

        ctx = await extrair_slots_e_mesclar(ctx, texto_usuario, dono_id)
        # =========================================================
        # 🔥 PROTEÇÃO — não fixar serviço cedo demais em aguardando_servico
        # quando o usuário mandar múltiplos serviços candidatos
        # =========================================================
        estado_fluxo_tmp = (ctx.get("estado_fluxo") or "").strip().lower()

        if estado_fluxo_tmp in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
            texto_norm_tmp = normalizar(texto_usuario or "")
            partes_tmp = re.split(r"\bou\b|,|/", texto_norm_tmp)

            profs_dict_tmp = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

            todos_tmp = []
            for p in profs_dict_tmp.values():
                todos_tmp.extend(p.get("servicos") or [])

            catalogo_tmp = list(dict.fromkeys([str(s).strip() for s in todos_tmp if s]))
            candidatos_tmp = []

            for parte in partes_tmp:
                parte = parte.strip()
                for s in catalogo_tmp:
                    if normalizar(s) in parte:
                        candidatos_tmp.append(s)

            candidatos_tmp = list(dict.fromkeys(candidatos_tmp))

            if len(candidatos_tmp) > 1:
                ctx.pop("servico", None)

                draft_tmp = ctx.get("draft_agendamento") or {}
                draft_tmp.pop("servico", None)
                ctx["draft_agendamento"] = draft_tmp

        await salvar_contexto_temporario(user_id, ctx)
        estado_fluxo = (ctx.get("estado_fluxo") or estado_fluxo or "idle").strip().lower()
        draft = ctx.get("draft_agendamento") or {}

    except ApplicationHandlerStop:
        raise

    except Exception as e:
        print("⚠️ [slots] Falha ao extrair/mesclar slots:", e, flush=True)

    # =========================================================
    # ✅ (C) Bloqueio de data no passado -> pergunta amanhã mesmo horário
    # =========================================================
    if ctx.get("data_hora"):
        dt_naive_existente = _dt_from_iso_naive(ctx["data_hora"])
        if dt_naive_existente and dt_naive_existente <= _agora_br_naive():
            return await _perguntar_amanha_mesmo_horario_e_bloquear(ctx["data_hora"])

    # =========================================================
    # ✅ (D) Capturar "sim/amanhã então" (amanhã mesmo horário)
    # =========================================================
    if ctx.get("pergunta_amanha_mesmo_horario") and (
        eh_confirmacao(texto_lower) or "amanha" in texto_lower or "amanhã" in texto_lower
    ):
        base_iso = ctx.get("data_hora_pendente") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        if not base_iso:
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["pergunta_amanha_mesmo_horario"] = False
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Certo — qual dia e horário você prefere?")

        base_dt = _dt_from_iso_naive(base_iso)
        if not base_dt:
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["pergunta_amanha_mesmo_horario"] = False
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Me manda o dia e horário de novo, por favor.")

        nova_dt = base_dt + timedelta(days=1)
        nova_iso = nova_dt.replace(second=0, microsecond=0).isoformat()

        draft_local = ctx.get("draft_agendamento") or {}
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft_local.get("servico") or ctx.get("servico")

        if not (prof or servico):
            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["pergunta_amanha_mesmo_horario"] = False
            ctx["data_hora"] = nova_iso
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": nova_iso, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(
                context,
                user_id,
                f"Fechado — *{formatar_data_hora_br(nova_iso)}*. Só me diz: qual serviço você quer fazer? (ou com qual profissional prefere)"
            )

        # Atualiza contexto
        ctx["data_hora"] = nova_iso
        ctx["data_hora_pendente"] = None
        ctx["pergunta_amanha_mesmo_horario"] = False
        if not isinstance(ctx.get("ultima_consulta"), dict):
            ctx["ultima_consulta"] = {}
        ctx["ultima_consulta"]["data_hora"] = nova_iso

        # Define próximo passo correto
        if not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["draft_agendamento"] = {"profissional": None, "data_hora": nova_iso, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Perfeito. Qual profissional você prefere?")

        if not servico:
            sugestao = ""
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": nova_iso, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(
                context,
                user_id,
                f"Fechado — *{formatar_data_hora_br(nova_iso)}* com *{prof}*. Qual serviço vai ser?{sugestao}"
            )

        # ✅ valida profissional x serviço ANTES de confirmar
        validacao = await validar_profissional_para_servico(dono_id, prof, servico)
        if not validacao["ok"]:
            nomes_validos = validacao["validos"]

            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["profissional_escolhido"] = None
            ctx["ultima_opcao_profissionais"] = nomes_validos
 
            ctx["aguardando_confirmacao_agendamento"] = False
            ctx.pop("dados_confirmacao_agendamento", None)

            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": nova_iso,
                "servico": servico,
                "modo_prechecagem": True
            }
            await salvar_contexto_temporario(user_id, ctx)

            lista = ", ".join(nomes_validos) if nomes_validos else "ninguém cadastrado"
            return await _send_and_stop(
                context,
                user_id,
                f"{prof} não faz *{servico}*.\n\n"
                f"Para *{servico}* eu tenho: {lista}.\n"
                "Qual você prefere?"
            )

        # tudo completo -> salva draft e deixa o fluxo principal concluir depois
        ctx["estado_fluxo"] = "agendando"
        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": nova_iso,
            "servico": servico,
            "modo_prechecagem": True
        }
        ctx["aguardando_confirmacao_agendamento"] = True
        ctx["dados_confirmacao_agendamento"] = {
            "profissional": prof,
            "servico": servico,
            "data_hora": nova_iso,
            "duracao": estimar_duracao(servico),
            "descricao": formatar_descricao_evento(servico, prof),
        }
        ctx["ultima_opcao_profissionais"] = [prof]
        ctx["pergunta_amanha_mesmo_horario"] = False
        ctx["data_hora_pendente"] = None

        await salvar_contexto_temporario(user_id, ctx)
        print(
            "🧪 [SAVE-CONF]",
            {
                "estado_fluxo": ctx.get("estado_fluxo"),
                "aguardando_confirmacao_agendamento": ctx.get("aguardando_confirmacao_agendamento"),
                "dados_confirmacao_agendamento": ctx.get("dados_confirmacao_agendamento"),
                "draft_agendamento": ctx.get("draft_agendamento"),
            },
            flush=True,
        )

        return await _send_and_stop(
            context,
            user_id,
            (
                f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(nova_iso)}*.\n"
                f"Responda *sim* para confirmar."
            )
        )

    # =========================================================
    # ✅ (E) Consulta com horário específico = pré-checagem
    # =========================================================
    if eh_consulta(texto_lower) and estado_fluxo == "idle":
        data_hora = ctx.get("data_hora")
        draft_local = ctx.get("draft_agendamento") or {}
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido")
        servico = draft_local.get("servico") or ctx.get("servico")

        ctx["estado_fluxo"] = "consultando"

        if data_hora or prof:
            ctx["ultima_consulta"] = {"data_hora": data_hora, "profissional": prof}

        # 🔥 só pergunta profissional se tiver hora REAL
        if data_hora and not prof and tem_hora_real(data_hora):
            ctx["estado_fluxo"] = "aguardando_profissional"

            if not isinstance(ctx.get("ultima_consulta"), dict):
                ctx["ultima_consulta"] = {}

            ctx["ultima_consulta"]["data_hora"] = data_hora

            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": data_hora,
                "servico": None,
                "modo_prechecagem": True
            }

            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Para *{formatar_data_hora_br(data_hora)}*, qual profissional você prefere?"
            )

        # 🔥 só pergunta serviço se tiver hora REAL
        if data_hora and prof and not servico and tem_hora_real(data_hora):
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []

            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break

            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"

            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": None,
                "modo_prechecagem": True
            }

            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Pra eu confirmar se cabe em *{formatar_data_hora_br(data_hora)}*, qual serviço vai ser?{sugestao}"
            )

        await salvar_contexto_temporario(user_id, ctx)
    
    # =========================================================
    # ✅ (F) Estado aguardando_servico: captura serviço e fecha automático se completo
    # =========================================================
    if estado_fluxo in ("aguardando_servico", "aguardando serviço", "aguardando_serviço"):
        draft_local = ctx.get("draft_agendamento") or {}
        print(f"🔥 [AG_SERVICO] entrou no bloco | texto={texto_usuario} | estado={estado_fluxo}", flush=True)

        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        nomes_profs = [str(p.get("nome", "")).strip() for p in profs_dict.values() if p.get("nome")]

        prof_detectado = None
        for nome in nomes_profs:
            if normalizar(nome) in tnorm:
                prof_detectado = nome
                break

        if prof_detectado and " com " in tnorm:
            draft_local["profissional"] = prof_detectado
            ctx["profissional_escolhido"] = prof_detectado
            tnorm_limpo = re.sub(r"\bcom\s+(a|o)\s+" + re.escape(normalizar(prof_detectado)) + r"\b", "", tnorm).strip()
        else:
            tnorm_limpo = tnorm

        servico_in = (tnorm_limpo or "").strip()

        # 🔥 limpeza de prefixos
        for prefixo in ["somente ", "só ", "so ", "apenas "]:
            if servico_in.startswith(prefixo):
                servico_in = servico_in[len(prefixo):].strip()

        # 🔥 tenta casar com catálogo (agora aceita múltiplos candidatos)
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

        todos = []
        for p in profs_dict.values():
            todos.extend(p.get("servicos") or [])

        vistos = set()
        catalogo = []
        for s in todos:
            s2 = str(s).strip()
            if s2 and s2 not in vistos:
                vistos.add(s2)
                catalogo.append(s2)

        servico_norm = normalizar(servico_in)
        servicos_candidatos = []

        for s in catalogo:
            s_norm = normalizar(s)
            if servico_norm == s_norm or s_norm in servico_norm:
                servicos_candidatos.append(s)

        # remove duplicados preservando ordem
        servicos_candidatos = list(dict.fromkeys(servicos_candidatos))

        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or  {}).get("profissional")
        data_hora = draft_local.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        servico = draft_local.get("servico") or ctx.get("servico")
        print(f"🔥 [AG_SERVICO] prof={prof} | data_hora={data_hora} | servico={servico}", flush=True)

        # 🔥 múltiplos serviços candidatos
        if len(servicos_candidatos) > 1:
            ctx["servicos_candidatos"] = servicos_candidatos

            texto_atual = normalizar(texto_usuario or "")

            contexto_base = ""

            try:
                ultima_consulta = ctx.get("ultima_consulta") or {}
                data_ref = ultima_consulta.get("data_hora") or ""

                # usa também texto anterior se tiver salvo
                texto_anterior = ctx.get("ultimo_texto_usuario") or ""

                contexto_base = normalizar(texto_anterior)

            except:
                contexto_base = ""

            texto = f"{contexto_base} {texto_atual}".strip()

            # ---------------------------------------------------------
            # 🔥 DECISÃO GENÉRICA DE SERVIÇO PRINCIPAL (sem hardcode)
            # ---------------------------------------------------------

            historico = ctx.get("historico_texto") or []
            texto_completo = " ".join(historico)
            texto = normalizar(texto_completo)
            candidatos = list(dict.fromkeys(servicos_candidatos or []))  # dedupe

            print(f"🧪 [TEXTO_SCORE_SERVICOS] {texto}", flush=True)

            def score_servico(servico: str, texto: str) -> int:
                s = normalizar(servico)
                score = 0

                # eixo: resultado imediato / finalização rápida
                if any(x in texto for x in [
                    "urgente", "encaixe", "hoje", "amanha", "amanhã",
                    "preciso", "dar um jeito", "evento", "meu cabelo", "horrivel", "horrível"
                ]):
                    if any(k in s for k in ["escova", "finalizacao", "finalização", "penteado"]):
                        score += 3
                    else:
                        score += 1

                # eixo: compromisso / sair pronta
                if any(x in texto for x in [
                    "sair", "mais tarde", "compromisso", "reuniao", "reunião", "evento"
                ]):
                    if any(k in s for k in ["escova", "penteado", "finalizacao", "finalização"]):
                        score += 2

                # eixo: tratamento
                if any(x in texto for x in [
                    "ressecado", "quebrado", "danificado", "tratar", "hidratar", "cuidar"
                ]):
                    if any(k in s for k in ["hidrat", "nutri", "reconstr", "botox"]):
                        score += 3

                # eixo: transformação mais pesada
                if any(x in texto for x in [
                    "mudar", "transformar", "cor", "clarear"
                ]):
                    if any(k in s for k in ["luz", "mecha", "descolor", "colora"]):
                        score += 2

                return score


            scores = {s: score_servico(s, texto) for s in candidatos}
            servico_escolhido = max(scores, key=scores.get) if scores else None

            print(f"🧪 [SCORE_SERVICOS] {scores} | escolhido={servico_escolhido}", flush=True)

            # threshold leve: só decide automático se houver sinal suficiente
            if servico_escolhido and scores.get(servico_escolhido, 0) >= 2:
                ctx["servico"] = servico_escolhido

                draft = ctx.get("draft_agendamento") or {}
                draft["servico"] = servico_escolhido
                ctx["draft_agendamento"] = draft

                ctx["servico_principal_recomendado"] = servico_escolhido

                await salvar_contexto_temporario(user_id, ctx)

                print(f"🔥 [SERVICO_DECIDIDO_AUTOMATICO] servico={servico_escolhido}", flush=True)

                # segue fluxo normal (pré-check vai assumir daqui)

            else:
                # fallback (mantém seu comportamento atual)
                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    f"Para eu seguir certinho: você quer *{candidatos[0]}* ou *{candidatos[1]}*?",
                    ctx,
                    texto_usuario,
                )

        # 🔥 só salva se bateu com 1 serviço
        if len(servicos_candidatos) == 1:
            servico_detectado = servicos_candidatos[0]
            draft_local["servico"] = servico_detectado
            ctx["servico"] = servico_detectado
            ctx.pop("servicos_candidatos", None)
            print(f"🔥 [AG_SERVICO] servico_detectado={servico_detectado}", flush=True)
            ctx["draft_agendamento"] = draft_local

        # 🔥 recarrega variáveis depois de possível atualização
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        data_hora = draft_local.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        servico = draft_local.get("servico") or ctx.get("servico")

        if not data_hora:
            print("🛑 [AG_SERVICO] saiu por falta de data_hora", flush=True)
            ctx["estado_fluxo"] = "aguardando_data"
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual dia e horário você prefere?")

        # =========================================================
        # 🔒 VALIDAÇÃO DE FUNCIONAMENTO DA DATA
        # =========================================================
        if data_hora:
            data_ref = data_hora.split("T")[0]

            validacao_data = await validar_data_funcionamento(user_id, data_ref)

            if not validacao_data.get("permitido"):
                return await _send_and_stop(
                    context,
                    user_id,
                    "Nesse dia a agenda está fechada. Me diga outro dia que eu verifico para você."
                )

        # =========================================================
        # 🔥 PRÉ-CHECAGEM ANTECIPADA COM HORÁRIOS CANDIDATOS
        # reutiliza o mesmo motor de conflito já existente
        # =========================================================
        horarios = ctx.get("horarios_sugeridos") or []

        if horarios and data_hora and servico and not prof:
            print("🔥 [PRE-CHECK ANTECIPADO] serviço + horários candidatos, sem profissional", flush=True)

            # =========================================================
            # 🔒 FILTRO DE EXPEDIENTE (AQUI)
            # =========================================================
            data_ref = data_hora.split("T")[0]
            duracao_servico = estimar_duracao(servico)

            horarios_validos_expediente = []

            for h in horarios:
                validacao_horario = await validar_horario_funcionamento(
                    user_id=user_id,
                    data_iso=data_ref,
                    hora_inicio=h,
                    duracao_min=duracao_servico,
                )

                if validacao_horario.get("permitido"):
                    horarios_validos_expediente.append(h)

            # 🔥 substitui lista original
            horarios = horarios_validos_expediente

            # 🔥 mantém contexto consistente
            ctx["horarios_sugeridos"] = horarios

            # 🔥 trava se nada sobrou
            if not horarios:
                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    "Nesse dia eu não tenho horário dentro do expediente configurado. Me diga outro dia que eu verifico para você.",
                    ctx,
                    texto_usuario,
                )

            # profissionais aptos ao serviço
            profs_aptos = []
            for p in profs_dict.values():
                nome_p = str(p.get("nome") or "").strip()
                servs_p = [str(s).strip().lower() for s in (p.get("servicos") or [])]

                if nome_p and (servico or "").strip().lower() in servs_p:
                    profs_aptos.append(nome_p)

            dt_base = datetime.fromisoformat(data_hora)
            horarios_livres = []
            disponibilidade_por_horario = {}  # {"15:00": ["Bruna", "Carla"], ...}

            for h in horarios:
                try:
                    hora, minuto = map(int, h.split(":"))
                    dt_teste = dt_base.replace(
                        hour=hora,
                        minute=minuto,
                        second=0,
                        microsecond=0
                    )

                    profissionais_livres = []

                    for nome_prof in profs_aptos:
                        conflito = await verificar_conflito_e_sugestoes_profissional(
                            user_id=user_id,
                            data=dt_teste.strftime("%Y-%m-%d"),
                            hora_inicio=dt_teste.strftime("%H:%M"),
                            duracao_min=estimar_duracao(servico),
                            profissional=nome_prof,
                            servico=servico
                        )

                        if not conflito.get("conflito"):
                            profissionais_livres.append(nome_prof)

                    if profissionais_livres:
                        horarios_livres.append(h)
                        disponibilidade_por_horario[h] = profissionais_livres

                except Exception as e:
                    print(f"⚠️ [PRE-CHECK ANTECIPADO] erro ao testar {h}: {e}", flush=True)

            # profissionais livres no geral
            ctx["ultima_opcao_profissionais"] = sorted(
                list({p for lista in disponibilidade_por_horario.values() for p in lista})
            )

            # ---------------------------------------------------------
            # CASO 1: dois horários livres
            # ---------------------------------------------------------
            if len(horarios_livres) == 2:
                h1 = horarios_livres[0]
                h2 = horarios_livres[1]

                ctx["estado_fluxo"] = "aguardando_escolha_horario"
                ctx.pop("servicos_candidatos", None)
                ctx["servico"] = servico
                ctx["horarios_sugeridos"] = horarios_livres

                # guarda quem está livre em cada horário
                ctx["disponibilidade_por_horario"] = disponibilidade_por_horario

                draft_local["servico"] = servico
                draft_local["data_hora"] = data_hora  # continua só como data-base
                ctx["draft_agendamento"] = draft_local

                def _normalizar_lista_profissionais(lista):
                    if not lista:
                        return []

                    saida = []
                    vistos = set()

                    for item in lista:
                        if isinstance(item, dict):
                            nome = (
                                item.get("profissional")
                                or item.get("nome")
                                or item.get("nome_profissional")
                                or ""
                            ).strip()
                        else:
                            nome = str(item).strip()

                        if not nome:
                            continue

                        chave = nome.lower()
                        if chave not in vistos:
                            vistos.add(chave)
                            saida.append(nome)

                    return saida

                def _formatar_profissionais(lista):
                    lista = _normalizar_lista_profissionais(lista)

                    if not lista:
                        return ""

                    if len(lista) == 1:
                        return lista[0]

                    if len(lista) == 2:
                        return f"{lista[0]} ou {lista[1]}"

                    return ", ".join(lista[:-1]) + f" ou {lista[-1]}"

                profs_h1 = _normalizar_lista_profissionais(
                    disponibilidade_por_horario.get(h1) or []
                )
                profs_h2 = _normalizar_lista_profissionais(
                    disponibilidade_por_horario.get(h2) or []
                )

                # salva opções enriquecidas para o próximo passo
                opcoes_hora_profissional = []
                for prof_nome in profs_h1:
                    opcoes_hora_profissional.append({
                        "hora": h1,
                        "profissional": prof_nome
                    })

                for prof_nome in profs_h2:
                    opcoes_hora_profissional.append({
                        "hora": h2,
                        "profissional": prof_nome
                    })

                ctx["opcoes_hora_profissional"] = opcoes_hora_profissional

                # melhor sugestão inicial:
                # prioriza o primeiro horário retornado e o primeiro profissional disponível nele
                melhor_sugestao = None
                if profs_h1:
                    melhor_sugestao = {
                        "hora": h1,
                        "profissional": profs_h1[0]
                    }
                elif profs_h2:
                    melhor_sugestao = {
                        "hora": h2,
                        "profissional": profs_h2[0]
                    }

                ctx["melhor_sugestao"] = melhor_sugestao

                await salvar_contexto_temporario(user_id, ctx)

                frase_data = montar_frase_data_legivel(data_hora)
                msg = f"Perfeito — encontrei estas opções {frase_data} 😊\n\n"

                if profs_h1:
                    msg += f"🕒 *{h1}* com *{_formatar_profissionais(profs_h1)}*\n"
                else:
                    msg += f"🕒 *{h1}*\n"

                if profs_h2:
                    msg += f"🕒 *{h2}* com *{_formatar_profissionais(profs_h2)}*\n"
                else:
                    msg += f"🕒 *{h2}*\n"

                if melhor_sugestao:
                    msg += (
                        f"\n💡 Para você, o melhor encaixe é "
                        f"*{servico} às {melhor_sugestao['hora']} com {melhor_sugestao['profissional']}*.\n"
                        f"Posso agendar?"
                    )
                else:
                    msg += "\nQual opção você prefere?"

                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    msg,
                    ctx,
                    texto_usuario,
                )

            # ---------------------------------------------------------
            # CASO 2: só um horário livre
            # ---------------------------------------------------------
            if len(horarios_livres) == 1:
                h = horarios_livres[0]
                profs = disponibilidade_por_horario.get(h, [])

                if not profs:
                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        f"Encontrei *{h}*, mas tive um problema ao verificar as profissionais.\nPosso tentar outro horário?",
                        ctx,
                        texto_usuario,
                    )

                # 2A: só 1 profissional livre → fecha direto
                if len(profs) == 1:
                    prof = profs[0]

                    ctx["estado_fluxo"] = "aguardando_confirmacao_agendamento"
                    ctx["ultima_acao"] = "criar_evento"
                    ctx.pop("servicos_candidatos", None)
                    ctx["servico"] = servico

                    draft_local["profissional"] = prof
                    draft_local["servico"] = servico
                    draft_local["data_hora"] = datetime.fromisoformat(data_hora).replace(
                        hour=int(h.split(":")[0]),
                        minute=int(h.split(":")[1]),
                        second=0,
                        microsecond=0
                    ).isoformat()

                    ctx["draft_agendamento"] = draft_local

                    await salvar_contexto_temporario(user_id, ctx)
                    frase_data = montar_frase_data_legivel(draft_local.get("data_hora") or data_hora)

                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        f"Perfeito — tenho *{h} com a {prof}* {frase_data} 😊\nPosso reservar para você?",
                        ctx,
                        texto_usuario,
                    )

                # 2B: mais de 1 profissional livre → cliente escolhe
                lista = " ou ".join(profs)

                ctx["estado_fluxo"] = "aguardando_profissional"
                ctx.pop("servicos_candidatos", None)
                ctx["servico"] = servico
  
                draft_local["data_hora"] = datetime.fromisoformat(data_hora).replace(
                    hour=int(h.split(":")[0]),
                    minute=int(h.split(":")[1]),
                    second=0,
                    microsecond=0
                ).isoformat()
                draft_local["servico"] = servico
                ctx["draft_agendamento"] = draft_local
                ctx["ultima_opcao_profissionais"] = profs

                await salvar_contexto_temporario(user_id, ctx)
                frase_data = montar_frase_data_legivel(draft_local.get("data_hora") or data_hora)

                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    f"Perfeito — tenho *{h} com {lista}* {frase_data} 😊\nQual você prefere?",
                    ctx,
                    texto_usuario,
                )

            # ---------------------------------------------------------
            # CASO 3: nenhum horário livre
            # ---------------------------------------------------------
            frase_data = montar_frase_data_legivel(data_hora)
            return await _send_and_stop_ctx(
                context,
                user_id,
                f"Para *{servico}*, esses horários não estão livres {frase_data} 😕\n\nPosso te sugerir os horários mais próximos?",
                ctx,
                texto_usuario,
            )

        if not prof:
            print("🛑 [AG_SERVICO] saiu por falta de profissional", flush=True)
            ctx["estado_fluxo"] = "aguardando_profissional"
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual profissional você prefere?")

        if not servico:
            print("🛑 [AG_SERVICO] saiu por falta de serviço", flush=True)
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual serviço vai ser?")

        # =========================================================
        # 🔥 USAR HORÁRIOS SUGERIDOS COM SERVIÇO DEFINIDO
        # =========================================================
        horarios = ctx.get("horarios_sugeridos") or []

        if horarios and data_hora and servico and prof:
            print("🔥 [CHECK HORARIOS_CANDIDATOS COM SERVIÇO]", flush=True)

            # =========================================================
            # 🔒 FILTRO DE EXPEDIENTE (AQUI)
            # =========================================================
            data_ref = data_hora.split("T")[0]
            duracao_servico = estimar_duracao(servico)

            horarios_validos_expediente = []

            for h in horarios:
                validacao_horario = await validar_horario_funcionamento(
                    user_id=user_id,
                    data_iso=data_ref,
                    hora_inicio=h,
                    duracao_min=duracao_servico,
                )

                if validacao_horario.get("permitido"):
                    horarios_validos_expediente.append(h)

            horarios = horarios_validos_expediente
            ctx["horarios_sugeridos"] = horarios

            if not horarios:
                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    f"Para *{servico}*, não encontrei horário dentro do expediente desse dia. Me diga outro dia ou outro horário.",
                    ctx,
                    texto_usuario,
                )

            dt_base = datetime.fromisoformat(data_hora)
            disponiveis = []

            for h in horarios:
                try:
                    hora, minuto = map(int, h.split(":"))

                    dt_teste = dt_base.replace(
                        hour=hora,
                        minute=minuto,
                        second=0,
                        microsecond=0
                    )

                    conflito = await verificar_conflito_e_sugestoes_profissional(
                        user_id=user_id,
                        data=dt_teste.strftime("%Y-%m-%d"),
                        hora_inicio=dt_teste.strftime("%H:%M"),
                        duracao_min=estimar_duracao(servico),
                        profissional=prof,
                        servico=servico
                    )

                    if not conflito.get("conflito"):
                        disponiveis.append(h)

                except Exception as e:
                    print(f"⚠️ erro ao testar horário {h}: {e}", flush=True)

            if len(disponiveis) == 2:
                return await _send_and_stop(
                    context,
                    user_id,
                    f"Perfeito — para *{servico}*, tenho *{disponiveis[0]}* e *{disponiveis[1]}* amanhã. Qual você prefere?"
                )

            if len(disponiveis) == 1:
                ocupados = [h for h in horarios if h not in disponiveis]
                ocupado_txt = ocupados[0] if ocupados else "esse horário"

                return await _send_and_stop(
                    context,
                    user_id,
                    f"Perfeito — para *{servico}*, *{ocupado_txt}* já está ocupado. Tenho *{disponiveis[0]}* disponível amanhã. Quer esse?"

                )

            return await _send_and_stop(
                context,
                user_id,
                f"Para *{servico}*, esse horário não está livre amanhã.\nPosso te sugerir outros horários?"

            )

        dt_naive = _dt_from_iso_naive(data_hora)
        if dt_naive and dt_naive <= _agora_br_naive():
            return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        # ✅ valida profissional x serviço ANTES de confirmar
        validacao = await validar_profissional_para_servico(dono_id, prof, servico)
        if not validacao["ok"]:
            nomes_validos = validacao["validos"]

            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["profissional_escolhido"] = None
            ctx["ultima_opcao_profissionais"] = nomes_validos

            ctx["aguardando_confirmacao_agendamento"] = False
            ctx.pop("dados_confirmacao_agendamento", None)

            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": data_hora,
                "servico": servico,
                "modo_prechecagem": bool(draft_local.get("modo_prechecagem"))
            }
            await salvar_contexto_temporario(user_id, ctx)

            lista = ", ".join(nomes_validos) if nomes_validos else "ninguém cadastrado"
            return await _send_and_stop(
                context,
                user_id,
                f"{prof} não faz *{servico}*.\n\n"
                f"Para *{servico}* eu tenho: {lista}.\n"
                "Qual você prefere?"
            )

        # 🔥 PRE-CHECAGEM DE CONFLITO (ANTES DE CONFIRMAR)
        print("🔥 [PRE-CHECK] Executando verificação de conflito...", flush=True)
        dt_obj = datetime.fromisoformat(data_hora)

        conflito_info = await verificar_conflito_e_sugestoes_profissional(
            user_id=user_id,
            data=dt_obj.strftime("%Y-%m-%d"),
            hora_inicio=dt_obj.strftime("%H:%M"),
            duracao_min=estimar_duracao(servico),
            profissional=prof,
            servico=servico
        )
        print("🔥 [PRE-CHECK RESULTADO]:", conflito_info, flush=True)

        # =========================================================
        # ❌ TEM CONFLITO
        # =========================================================
        if conflito_info.get("conflito"):

            sugestoes = conflito_info.get("sugestoes") or []
            alternativo = conflito_info.get("profissional_alternativo")

            # 🔥 salva estado de escolha ANTES de responder
            ctx["estado_fluxo"] = "aguardando_escolha_horario"
            ctx["servico"] = servico
            ctx["profissional_escolhido"] = prof
            ctx["data_hora"] = data_hora
            ctx["ultima_acao"] = "criar_evento"
            ctx["aguardando_confirmacao_agendamento"] = False
            ctx["dados_confirmacao_agendamento"] = None

            ctx["draft_agendamento"] = {
                "profissional": prof,
                "data_hora": data_hora,
                "servico": servico,
                "modo_prechecagem": True
            }

            # 🔥 mantém as sugestões exatamente no formato que o bloco 2338 espera
            horarios_formatados = []
            for h in sugestoes[:3]:
                if hasattr(h, "strftime"):
                    horarios_formatados.append(h.strftime("%H:%M"))
                else:
                    h_str = str(h).strip()
                    if " - " in h_str:
                        horarios_formatados.append(h_str)
                    else:
                        horarios_formatados.append(h_str)

            ctx["horarios_sugeridos"] = horarios_formatados
            ctx["alternativa_profissional"] = alternativo
            ctx["ultima_opcao_profissionais"] = [prof] + ([alternativo] if alternativo else [])
            ctx["modo_escolha_horario"] = True

            await salvar_contexto_temporario(user_id, ctx)

            print(
                f"🧪 [POS-SAVE CONFLITO] estado_fluxo={ctx.get('estado_fluxo')} | "
                f"modo_escolha_horario={ctx.get('modo_escolha_horario')} | "
                f"horarios_sugeridos={ctx.get('horarios_sugeridos')} | "
                f"data_hora={ctx.get('data_hora')} | "
                f"draft={ctx.get('draft_agendamento')}",
                flush=True
            )

            # 🔥 horário original
            hora_original = datetime.fromisoformat(data_hora).strftime("%H:%M")

            msg = f"⛔ A *{prof}* já tem atendimento às *{hora_original}*.\n"

            # 🔥 horários alternativos
            if sugestoes:
                msg += f"\n✅ Estes horários estão livres com *{prof}*:\n"
                for h in sugestoes[:3]:
                    if hasattr(h, "strftime"):
                        h = h.strftime("%H:%M")
                    msg += f"🔄 {h}\n"

            # 🔥 profissional alternativo
            if alternativo:
                msg += f"\n💡 Se quiser manter *{hora_original}*, posso te encaixar com *{alternativo}*.\n"

            msg += "\nVocê prefere outro horário ou manter o horário com outro profissional?"

            return await _send_and_stop(context, user_id, msg)

        # =========================================================
        # ✅ SEM CONFLITO → AGORA SIM CONFIRMA
        # =========================================================

        ctx["estado_fluxo"] = "agendando"

        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico,
            "modo_prechecagem": True
        }

        ctx["aguardando_confirmacao_agendamento"] = True

        ctx["dados_confirmacao_agendamento"] = {
            "profissional": prof,
            "servico": servico,
            "data_hora": data_hora,
            "duracao": estimar_duracao(servico),
            "descricao": formatar_descricao_evento(servico, prof),
        }

        ctx["ultima_opcao_profissionais"] = [prof]

        await salvar_contexto_temporario(user_id, ctx)

        return await _send_and_stop(
            context,
            user_id,
            (
                f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(data_hora)}*.\n"
                f"Responda *sim* para confirmar."
            )
        )

    # =========================================================
    # ✅ (G) Gatilho explícito "pode agendar/pode marcar"
    # =========================================================
    if eh_gatilho_agendar(texto_lower) or (estado_fluxo == "consultando" and eh_confirmacao(texto_lower)):
        draft_local = ctx.get("draft_agendamento") or {}
        data_hora = draft_local.get("data_hora") or ctx.get("data_hora") or (ctx.get("ultima_consulta") or {}).get("data_hora")
        prof = draft_local.get("profissional") or ctx.get("profissional_escolhido") or (ctx.get("ultima_consulta") or {}).get("profissional")
        servico = draft_local.get("servico") or ctx.get("servico")

        if data_hora:
            dt_naive = _dt_from_iso_naive(data_hora)
            if dt_naive and dt_naive <= _agora_br_naive():
                return await _perguntar_amanha_mesmo_horario_e_bloquear(data_hora)

        if not prof and not servico:
            ctx.pop("modo_escolha_horario", None)
            ctx.pop("horarios_sugeridos", None)
            ctx["estado_fluxo"] = "aguardando_servico"
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(
                context,
                user_id,
                "Pra eu reservar certinho: qual serviço vai ser e com qual profissional você prefere?"
            )

        if data_hora and prof and not servico:
            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
            servs = []
            for p in profs_dict.values():
                if normalizar(p.get("nome", "")) == normalizar(prof):
                    servs = p.get("servicos") or []
                    break

            sugestao = ""
            if servs:
                sugestao = "\n\nServiços disponíveis:\n- " + "\n- ".join([str(x) for x in servs])

            ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": data_hora, "servico": None, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Fechado — com *{prof}* em *{formatar_data_hora_br(data_hora)}*. Qual serviço vai ser?{sugestao}"
            )

        # =========================================================
        # 🔒 VALIDAÇÃO DE EXPEDIENTE ANTES DE PERGUNTAR PROFISSIONAL
        # =========================================================
        if data_hora and servico and not prof:

            data_ref = data_hora.split("T")[0]
            hora_ref = data_hora.split("T")[1][:5]

            id_dono = await obter_id_dono(user_id)

            validacao = await validar_horario_funcionamento(
                user_id=id_dono,
                data_iso=data_ref,
                hora_inicio=hora_ref,
                duracao_min=estimar_duracao(servico),
            )

            if not validacao.get("permitido"):

                motivo = validacao.get("motivo")

                if motivo == "fechado_na_data":
                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        "Nesse dia a agenda está fechada 😕",
                        ctx,
                        texto_usuario,
                    )

                if motivo == "fora_do_expediente":
                    tentativa = await resolver_fora_do_expediente(
                        user_id=id_dono,
                        data_iso=data_ref,
                        hora_inicio=hora_ref,
                        duracao_min=estimar_duracao(servico),
                        servico=servico,
                        profissional=None,
                    )

                    if tentativa.get("ok"):
                        horario = tentativa.get("horario")
                        nova_data_hora = tentativa.get("data_hora")

                        if nova_data_hora:
                            ctx["data_hora"] = nova_data_hora

                            draft = ctx.get("draft_agendamento") or {}
                            draft["data_hora"] = nova_data_hora
                            ctx["draft_agendamento"] = draft

                            await salvar_contexto_temporario(user_id, ctx)

                        return await _send_and_stop_ctx(
                            context,
                            user_id,
                            "Infelizmente esse horário fica fora do nosso expediente 😕\n\n"
                            f"O horário mais próximo que tenho disponível é às *{horario}*.\n"
                            "Posso agendar pra você? 😊",
                            ctx,
                            texto_usuario,
                        )

                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        "Esse horário ficará fora do nosso atendimento comercial 😕",
                        ctx,
                        texto_usuario,
                    )

        if data_hora and servico and not prof:
            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["draft_agendamento"] = {"profissional": None, "data_hora": data_hora, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Perfeito. Qual profissional você prefere?")

        if not data_hora:
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["draft_agendamento"] = {"profissional": prof, "data_hora": None, "servico": servico, "modo_prechecagem": True}
            await salvar_contexto_temporario(user_id, ctx)
            return await _send_and_stop(context, user_id, "Qual dia e horário você prefere?")

        # ✅ valida profissional x serviço ANTES de confirmar
        validacao = await validar_profissional_para_servico(dono_id, prof, servico)
        if not validacao["ok"]:
            nomes_validos = validacao["validos"]

            ctx["estado_fluxo"] = "aguardando_profissional"
            ctx["profissional_escolhido"] = None
            ctx["ultima_opcao_profissionais"] = nomes_validos

            ctx["aguardando_confirmacao_agendamento"] = False
            ctx.pop("dados_confirmacao_agendamento", None)

            ctx["draft_agendamento"] = {
                "profissional": None,
                "data_hora": data_hora,
                "servico": servico,
                "modo_prechecagem": True
            }
            await salvar_contexto_temporario(user_id, ctx)

            lista = ", ".join(nomes_validos) if nomes_validos else "ninguém cadastrado"
            return await _send_and_stop(
                context,
                user_id,
                f"{prof} não faz *{servico}*.\n\n"
                f"Para *{servico}* eu tenho: {lista}.\n"
                "Qual você prefere?"
            )

        ctx["estado_fluxo"] = "agendando"

        ctx["draft_agendamento"] = {
            "profissional": prof,
            "data_hora": data_hora,
            "servico": servico,
            "modo_prechecagem": True
        }

        ctx["aguardando_confirmacao_agendamento"] = True

        ctx["dados_confirmacao_agendamento"] = {
            "profissional": prof,
            "servico": servico,
            "data_hora": data_hora,
            "duracao": estimar_duracao(servico),
            "descricao": formatar_descricao_evento(servico, prof),
        }

        ctx["ultima_opcao_profissionais"] = [prof]

        await salvar_contexto_temporario(user_id, ctx)

        return await _send_and_stop(
            context,
            user_id,
            (
                f"Confirmando: *{servico}* com *{prof}* em *{formatar_data_hora_br(data_hora)}*.\n"
                f"Responda *sim* para confirmar."
            )
        )

    # =========================================================
    # ESCOLHA DIRETA DE PROFISSIONAL A PARTIR DA ÚLTIMA LISTA
    # =========================================================
    opcoes = ctx.get("ultima_opcao_profissionais") or []

    def _norm_nome(s: str) -> str:
        return normalizar(s or "")

    def _limpar_escolha(txt: str) -> str:
        t = _norm_nome(txt)
        prefixos = [
            "a ", "o ",
            "com a ", "com o ",
            "quero a ", "quero o ",
            "pode ser a ", "pode ser o ",
        ]
        for p in prefixos:
            if t.startswith(p):
                return t[len(p):].strip()
        return t

    escolha_prof = None
    texto_escolha = _limpar_escolha(texto_lower)
    texto_norm = _norm_nome(texto_lower)

    for nome in opcoes:
        nome_norm = _norm_nome(nome)

        # match exato OU palavra isolada
        if (
            texto_escolha == nome_norm
            or re.search(rf"\b{re.escape(nome_norm)}\b", texto_norm)
        ):
            escolha_prof = nome
            break

    if escolha_prof:

        _audit_confirmacao("ESCOLHA_DIRETA_PROFISSIONAL", ctx, texto_usuario)
        servico = ctx.get("servico") or (ctx.get("draft_agendamento") or {}).get("servico")
        data_hora = ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora")

        if servico and data_hora:
            ctx["profissional_escolhido"] = escolha_prof
            ctx["estado_fluxo"] = "agendando"
            ctx["aguardando_confirmacao_agendamento"] = True
            ctx["dados_confirmacao_agendamento"] = {
                "profissional": escolha_prof,
                "servico": servico,
                "data_hora": data_hora,
                "duracao": estimar_duracao(servico),
                "descricao": formatar_descricao_evento(servico, escolha_prof),
            }
            ctx["draft_agendamento"] = {
                "profissional": escolha_prof,
                "servico": servico,
                "data_hora": data_hora,
                "modo_prechecagem": True
            }
            ctx["ultima_opcao_profissionais"] = [escolha_prof]
            await salvar_contexto_temporario(user_id, ctx)

            print("🧪 [AUDIT-CONF:ESCOLHA_DIRETA_PROFISSIONAL] MONTANDO CONFIRMACAO", flush=True)

            return await _send_and_stop(
                context,
                user_id,
                (
                    f"Confirmando: *{servico}* com *{escolha_prof}* "
                    f"em *{formatar_data_hora_br(data_hora)}*.\n"
                    f"Responda *sim* para confirmar."
                )
            )

        # ✅ FALTA APENAS DATA/HORA
        if servico and not data_hora:
            ctx["profissional_escolhido"] = escolha_prof
            ctx["estado_fluxo"] = "aguardando_data"
            ctx["draft_agendamento"] = {
                "profissional": escolha_prof,
                "servico": servico,
                "data_hora": None,
                "modo_prechecagem": True
            }
            ctx["ultima_opcao_profissionais"] = [escolha_prof]

            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Perfeito — *{servico}* com *{escolha_prof}*. Qual dia e horário você prefere?"
            )

        if not servico:
            ctx["profissional_escolhido"] = escolha_prof
            if ctx.get("estado_fluxo") not in ["aguardando_confirmacao_agendamento", "agendando"]:
                ctx["estado_fluxo"] = "aguardando_servico"
            ctx["draft_agendamento"] = {
                "profissional": escolha_prof,
                "servico": None,
                "data_hora": data_hora,
                "modo_prechecagem": True
            }
            ctx["ultima_opcao_profissionais"] = [escolha_prof]

            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                f"Perfeito — com *{escolha_prof}*. Qual serviço você quer fazer?"
            )

    # =========================================================
    # BLOQUEIO: usuário escolheu nome fora da última lista oferecida
    # =========================================================
    if opcoes and texto_escolha:
        profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
        nomes_cadastrados = []

        for p in profs_dict.values():
            nomep = (p.get("nome") or "").strip()
            if nomep:
                nomes_cadastrados.append(nomep)

        nome_real_digitado = None
        for nomep in nomes_cadastrados:
            if texto_escolha == _norm_nome(nomep):
                nome_real_digitado = nomep
                break

        # se digitou um profissional real, mas fora da lista permitida
        if nome_real_digitado:
            servico = ctx.get("servico") or (ctx.get("draft_agendamento") or {}).get("servico")
            lista = ", ".join(opcoes)

            return await _send_and_stop(
                context,
                user_id,
                (
                    f"*{nome_real_digitado}* não atende *{servico}*.\n\n"
                    f"Para *{servico}*, eu tenho: {lista}.\n"
                    f"Qual você prefere?"
                )
            )
  
    # =========================================================
    # ✅ (H) Chamada normal ao GPT (com contexto do dono)
    # =========================================================
    contexto = await carregar_contexto_temporario(user_id) or {}
    contexto["usuario"] = {"user_id": user_id, "id_negocio": dono_id}

    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    contexto["profissionais"] = list(profissionais_dict.values())

    # =========================================================
    # ⛔ INTERCEPTAÇÃO: usuário digitou só hora sem data definida
    # =========================================================
    if estado_fluxo == "aguardando_data":
        draft = ctx.get("draft_agendamento") or {}
        data_hora_ctx = draft.get("data_hora") or ctx.get("data_hora")

        texto_norm = normalizar(texto_usuario or "")
        so_hora = bool(re.match(r"^(?:as\s*)?\d{1,2}(?::\d{2})?$", texto_norm))

        if so_hora and not data_hora_ctx:
            ctx["hora_pendente"] = texto_usuario
            await salvar_contexto_temporario(user_id, ctx)

            return await _send_and_stop(
                context,
                user_id,
                "Perfeito — falta só o dia. Você quer para quando?"
            )

        # =========================================================
        # ⛔ INTERCEPTAÇÃO: usuário digitou só data sem hora definida
        # =========================================================
        data_detectada = interpretar_data_e_hora(texto_usuario)

        if (data_detectada or eh_dia_semana or eh_dia_numero) and not data_hora_ctx:
            hora_pendente = (ctx.get("hora_pendente") or "").strip().lower()
            hora_match = re.match(
                r"^(?:as\s*)?(\d{1,2})(?::(\d{2}))?$",
                normalizar(hora_pendente)
            )

            # =========================================================
            # 1) Se existe hora pendente, combina com a data detectada
            # =========================================================
            if hora_match and data_detectada:
                hora = int(hora_match.group(1))
                minuto = int(hora_match.group(2) or 0)

                data_final = data_detectada.replace(
                    hour=hora,
                    minute=minuto,
                    second=0,
                    microsecond=0
                ).isoformat()

                ctx["data_hora"] = data_final
                ctx["hora_pendente"] = None
                ctx["estado_fluxo"] = "agendando"

                draft = ctx.get("draft_agendamento") or {}
                draft["data_hora"] = data_final
                ctx["draft_agendamento"] = draft

                servico = ctx.get("servico") or draft.get("servico")
                profissional = ctx.get("profissional_escolhido") or draft.get("profissional")

                if servico and profissional:
                    ctx["aguardando_confirmacao_agendamento"] = True
                    ctx["dados_confirmacao_agendamento"] = {
                        "profissional": profissional,
                        "servico": servico,
                        "data_hora": data_final,
                        "duracao": estimar_duracao(servico),
                        "descricao": formatar_descricao_evento(servico, profissional),
                    }

                await salvar_contexto_temporario(user_id, ctx)

                if servico and profissional:
                    return await _send_and_stop(
                        context,
                        user_id,
                        (
                            f"Confirmando: *{servico}* com *{profissional}* "
                            f"em *{formatar_data_hora_br(data_final)}*.\n"
                            f"Responda *sim* para confirmar."
                        )
                    )

            # =========================================================
            # 2) Se NÃO existe hora pendente, mas a própria frase já
            #    trouxe data+hora ("sexta feira as 11"), usa direto
            # =========================================================
            if data_detectada and (data_detectada.hour != 0 or data_detectada.minute != 0):
                data_final = data_detectada.replace(
                    second=0,
                    microsecond=0
                ).isoformat()

                ctx["data_hora"] = data_final
                ctx["hora_pendente"] = None
                ctx["estado_fluxo"] = "agendando"

                draft = ctx.get("draft_agendamento") or {}
                draft["data_hora"] = data_final
                ctx["draft_agendamento"] = draft

                servico = ctx.get("servico") or draft.get("servico")
                profissional = ctx.get("profissional_escolhido") or draft.get("profissional")

                if servico and profissional:

                    data_ref = data_final.split("T")[0]
                    hora_ref = data_final.split("T")[1][:5]

                    id_dono = await obter_id_dono(user_id)

                    validacao = await validar_horario_funcionamento(
                        user_id=id_dono,
                        data_iso=data_ref,
                        hora_inicio=hora_ref,
                        duracao_min=estimar_duracao(servico),
                    )

                    if not validacao.get("permitido"):
                        print("🚫 [BLOQUEIO] confirmação impedida por horário inválido", flush=True)
                    else:
                        ctx["aguardando_confirmacao_agendamento"] = True
                        ctx["dados_confirmacao_agendamento"] = {
                        "profissional": profissional,
                        "servico": servico,
                        "data_hora": data_final,
                        "duracao": estimar_duracao(servico),
                        "descricao": formatar_descricao_evento(servico, profissional),
                    }

                    await salvar_contexto_temporario(user_id, ctx)

                    return await _send_and_stop(
                        context,
                        user_id,
                        (
                            f"Confirmando: *{servico}* com *{profissional}* "
                            f"em *{formatar_data_hora_br(data_final)}*.\n"
                            f"Responda *sim* para confirmar."
                        )
                    )

                await salvar_contexto_temporario(user_id, ctx)

                # =========================================================
                # 🔒 VALIDAÇÃO DE EXPEDIENTE (BLOCO DATA COMPLEXA)
                # =========================================================
                data_ref = data_final.split("T")[0]
                hora_ref = data_final.split("T")[1][:5]

                id_dono = await obter_id_dono(user_id)

                validacao = await validar_horario_funcionamento(
                    user_id=id_dono,
                    data_iso=data_ref,
                    hora_inicio=hora_ref,
                    duracao_min=estimar_duracao(servico),
                )

                print(f"🧪 [EXPEDIENTE] permitido={validacao.get('permitido')} | motivo={validacao.get('motivo')}", flush=True)

                if not validacao.get("permitido"):

                    tentativa = await resolver_fora_do_expediente(
                        user_id=id_dono,
                        data_iso=data_ref,
                        hora_inicio=hora_ref,
                        duracao_min=estimar_duracao(servico),
                        servico=servico,
                        profissional=None,
                    ) 

                    if tentativa.get("ok"):
                        horario = tentativa.get("horario")
                        nova_data_hora = tentativa.get("data_hora")

                        if nova_data_hora:
                            ctx["data_hora"] = nova_data_hora

                            draft = ctx.get("draft_agendamento") or {}
                            draft["data_hora"] = nova_data_hora
                            ctx["draft_agendamento"] = draft

                            await salvar_contexto_temporario(user_id, ctx)

                        return await _send_and_stop_ctx(
                            context,
                            user_id,
                            "Infelizmente esse horário fica fora do nosso expediente 😕\n\n"
                            f"O horário mais próximo que tenho disponível é às *{horario}*.\n"
                            "Posso agendar pra você? 😊",
                            ctx,
                            texto_usuario,
                        )

                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        "❌ Esse horário não cabe no expediente desse dia. Me diga outro horário.",
                        ctx,
                        texto_usuario,
                    )

                if servico and not profissional and tem_hora_real(data_final):
                    return await _send_and_stop(
                        context,
                        user_id,
                        f"Perfeito — *{servico}* em *{formatar_data_hora_br(data_final)}*. Qual profissional você prefere?"
                    )

                if profissional and not servico and tem_hora_real(data_final):
                    return await _send_and_stop(
                        context,
                        user_id,
                        f"Perfeito — com *{profissional}* em *{formatar_data_hora_br(data_final)}*. Qual serviço você quer fazer?"
                    )

            # =========================================================
            # 3) Se chegou até aqui, temos só a data -> falta horário
            # =========================================================
            if data_detectada:
                data_base = data_detectada.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).isoformat()

                ctx["data_hora"] = data_base
                ctx["estado_fluxo"] = "aguardando_data"

                draft = ctx.get("draft_agendamento") or {}
                draft["data_hora"] = data_base
                ctx["draft_agendamento"] = draft

                await salvar_contexto_temporario(user_id, ctx)

                data_legivel = formatar_data_hora_br(data_base).split(" às ")[0]

                return await _send_and_stop(
                    context,
                    user_id,
                    f"Perfeito — agora falta só o horário para *{data_legivel}*. Qual horário você prefere?"
                )

    print("🔥🔥🔥 BLOCO DATA COMPLEXA EXECUTOU 🔥🔥🔥", flush=True)

    # =========================================================
    # PRÉ-GPT — usa a extração central do projeto
    # =========================================================
    
    ctx = await extrair_slots_e_mesclar(ctx, texto_usuario, dono_id)

    # 🔥 PROTEÇÃO CRÍTICA
    if not isinstance(ctx, dict):
        print(f"🚨 ctx inválido — abortando sobrescrita", flush=True)
        ctx = await carregar_contexto_temporario(user_id) or {}

    print("🧪 [SLOTS CENTRALIZADOS] ctx=", ctx, flush=True)

    draft_tmp = ctx.get("draft_agendamento") or {}

    slots_extraidos = {
        "data_hora": ctx.get("data_hora") or draft_tmp.get("data_hora"),
        "servico": ctx.get("servico") or draft_tmp.get("servico"),
        "profissional": ctx.get("profissional_escolhido") or draft_tmp.get("profissional"),
    }

    if not slots_extraidos["data_hora"]:
        slots_extraidos["data_hora"] = draft_tmp.get("data_hora")

    if not slots_extraidos["servico"]:
        slots_extraidos["servico"] = draft_tmp.get("servico")

    if not slots_extraidos["profissional"]:
        slots_extraidos["profissional"] = draft_tmp.get("profissional")

    campos_faltantes = []

    if not slots_extraidos["servico"]:
        campos_faltantes.append("servico")

    if not slots_extraidos["profissional"]:
        campos_faltantes.append("profissional")

    if not tem_hora_real(slots_extraidos["data_hora"]):
        campos_faltantes.append("data_hora")

    proximo_passo = None

    if campos_faltantes:
        if campos_faltantes == ["servico"]:
            proximo_passo = "perguntar_servico"
        elif campos_faltantes == ["profissional"]:
            proximo_passo = "perguntar_profissional"
        elif campos_faltantes == ["data_hora"]:
            proximo_passo = "perguntar_data_hora"
        else:
            proximo_passo = "coletar_dado_faltante"

    else:
        data_hora_final = slots_extraidos.get("data_hora") or ctx.get("data_hora")

        if tem_hora_real(data_hora_final):
            proximo_passo = "confirmar_ou_executar"
        else:
            proximo_passo = "coletar_dado_faltante"

    # 🔥 GARANTIA FINAL
    if not proximo_passo:
        proximo_passo = "coletar_dado_faltante"

    proximo_passo_real = resolver_proximo_passo_real(
        proximo_passo,
        slots_extraidos,
        ctx
    )

    frase_data_legivel = montar_frase_data_legivel(slots_extraidos.get("data_hora"))

    payload_resposta = { 
        "slots_extraidos": slots_extraidos, 
        "campos_faltantes": campos_faltantes, 
        "proximo_passo": proximo_passo, 
        "proximo_passo_real": proximo_passo_real, 
        "frase_data_legivel": frase_data_legivel, 
        "nao_inventar_catalogo": True, 
        "nao_prometer_disponibilidade_sem_validar": True, 
        "servicos_permitidos": [], 
        "profissionais_permitidos": [], 
    }

    # só lista profissionais quando o serviço já existe
    if slots_extraidos.get("servico"):
        profissionais_validos = []
        for p in profissionais_dict.values():
            nomep = (p.get("nome") or "").strip()
            servs = [str(s).strip() for s in (p.get("servicos") or []) if str(s).strip()]
            if nomep and any(normalizar(slots_extraidos["servico"]) == normalizar(s) for s in servs):
                profissionais_validos.append(nomep)
        payload_resposta["profissionais_permitidos"] = profissionais_validos

    contexto["payload_resposta"] = payload_resposta

    # =========================================================
    # 🔒 VALIDAÇÃO GLOBAL DE EXPEDIENTE ANTES DE PERGUNTAR PROFISSIONAL
    # =========================================================
    data_hora_validacao = (
        slots_extraidos.get("data_hora")
        or ctx.get("data_hora")
        or (ctx.get("draft_agendamento") or {}).get("data_hora")
    )
    servico_validacao = (
        slots_extraidos.get("servico")
        or ctx.get("servico")
        or (ctx.get("draft_agendamento") or {}).get("servico")
    )
    profissional_validacao = (
        slots_extraidos.get("profissional")
        or ctx.get("profissional_escolhido")
        or (ctx.get("draft_agendamento") or {}).get("profissional")
    )

    if (
        proximo_passo_real == "perguntar_profissional"
        and data_hora_validacao
        and servico_validacao
        and not profissional_validacao
    ):
        data_ref = data_hora_validacao.split("T")[0]
        hora_ref = data_hora_validacao.split("T")[1][:5]

        id_dono = await obter_id_dono(user_id)

        validacao = await validar_horario_funcionamento(
            user_id=id_dono,
            data_iso=data_ref,
            hora_inicio=hora_ref,
            duracao_min=estimar_duracao(servico_validacao),
            profissional=profissional_validacao,
        )

        if not validacao.get("permitido"):
            motivo = validacao.get("motivo")

            if motivo == "fechado_na_data":
                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    "Nesse dia não teremos expediente.\n\n",
                    "Por favor, me informe outro dia que eu verifico para você 😊",
                    ctx,
                    texto_usuario,
                )

            if motivo == "fora_do_expediente":

                tentativa = await resolver_fora_do_expediente(
                    user_id=id_dono,
                    data_iso=data_ref,
                    hora_inicio=hora_ref,
                    duracao_min=estimar_duracao(servico_validacao),
                    servico=servico_validacao,
                    profissional=None,  # aqui ainda não tem profissional
                )

                if tentativa.get("ok"):
                    horario = tentativa.get("horario")
                    nova_data_hora = tentativa.get("data_hora")

                    if nova_data_hora:
                        ctx["data_hora"] = nova_data_hora

                        draft = ctx.get("draft_agendamento") or {}
                        draft["data_hora"] = nova_data_hora
                        ctx["draft_agendamento"] = draft

                        await salvar_contexto_temporario(user_id, ctx)

                    return await _send_and_stop_ctx(
                        context,
                        user_id,
                        "Infelizmente esse horário fica fora do nosso expediente 😕\n\n"
                        f"O horário mais próximo que tenho disponível é às *{horario}*.\n"
                        "Posso agendar pra você? 😊",
                        ctx,
                        texto_usuario,
                    )

                return await _send_and_stop_ctx(
                    context,
                    user_id,
                    "❌ Não consegui encaixar esse horário. Me diga outro que eu verifico pra você.",
                    ctx,
                    texto_usuario,
                )

    print("🧪 [ANTES GPT] proximo_passo=", proximo_passo, flush=True)
    print("🧪 [ANTES GPT] proximo_passo_real=", proximo_passo_real, flush=True)
    print("🧪 [ANTES GPT] slots_extraidos=", slots_extraidos, flush=True)

    # =========================================================
    # 🔥 P0 — PRÉ-CHECAGEM (SEM GPT)
    # só executa se o horário estiver válido no expediente
    # =========================================================
    data_hora_check = slots_extraidos.get("data_hora")
    servico_check = slots_extraidos.get("servico")
    prof_check = slots_extraidos.get("profissional")

    pode_executar_p0 = False

    if data_hora_check and servico_check and prof_check:
        data_ref = data_hora_check.split("T")[0]
        hora_ref = data_hora_check.split("T")[1][:5]

        id_dono = await obter_id_dono(user_id)

        validacao_p0 = await validar_horario_funcionamento(
            user_id=id_dono,
            data_iso=data_ref,
            hora_inicio=hora_ref,
            duracao_min=estimar_duracao(servico_check),
        )

        print(
            f"🧪 [P0 CHECK] permitido={validacao_p0.get('permitido')} | motivo={validacao_p0.get('motivo')}",
            flush=True
        )

        if validacao_p0.get("permitido"):
            pode_executar_p0 = True

    if pode_executar_p0:
        print("🔥 [P0] PRÉ-CHECAGEM — SEM GPT", flush=True)

        return await executar_acao_gpt(
            update,
            context,
            "pre_confirmar_agendamento",
            {
                "data_hora": data_hora_check,
                "servico": servico_check,
                "profissional": prof_check
            }
        )

    print("🔥🔥🔥 ANTES DO CHAMAR_GPT_COM_CONTEXTO 🔥🔥🔥", flush=True)

    # =========================================================
    # 🔒 GARANTE QUE FLUXO SEMPRE RESPONDE ANTES DO GPT
    # =========================================================
    estado_fluxo = ctx.get("estado_fluxo")

    interceptar_flow_guard = estado_fluxo in [
        "aguardando_servico",
        "aguardando_profissional",
        "aguardando_data",
        "aguardando_horario",
        "agendando"
    ]

    if interceptar_flow_guard:
        data_hora_guard = ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora")
        servico_guard = ctx.get("servico") or (ctx.get("draft_agendamento") or {}).get("servico")
        profissional_guard = ctx.get("profissional_escolhido") or (ctx.get("draft_agendamento") or {}).get("profissional")

        # não intercepta quando já existe agendamento completo;
        # deixa seguir para a validação de expediente/conflito
        if estado_fluxo == "agendando" and data_hora_guard and servico_guard and profissional_guard:
            interceptar_flow_guard = False

    if interceptar_flow_guard:
        print("🧪 [FLOW GUARD] interceptando mensagem no fluxo:", texto_usuario, flush=True)

        # =========================================================
        # 🔒 BLOQUEIO DE AGENDA DO SALÃO (DONO)
        # precisa entrar antes de qualquer reaproveitamento do fluxo
        # =========================================================
        payload_bloqueio = detectar_bloqueio_agenda_salao(texto_usuario)

        if payload_bloqueio:
            print(f"🔒 [BLOQUEIO_AGENDA_SALAO/FLOW_GUARD] payload={payload_bloqueio}", flush=True)
            return await executar_acao_por_nome(
                update,
                context,
                payload_bloqueio["acao"],
                payload_bloqueio["dados"]
            )

        # 🔥 BLOCO DE CAPTURA DE "SÓ HORA"
        if ctx.get("estado_fluxo") == "aguardando_horario":

            print(
                f"🚨 [AGUARDANDO_HORARIO] entrou | "
                f"texto={texto_usuario} | "
                f"estado_fluxo={ctx.get('estado_fluxo')} | "
                f"ctx_data_hora={ctx.get('data_hora')} | "
                f"draft_data_hora={(ctx.get('draft_agendamento') or {}).get('data_hora')} | "
                f"dados_confirmacao={ctx.get('dados_confirmacao_agendamento')}",
                flush=True
            )

            texto_norm = (texto_usuario or "").strip().lower().replace("às", "as")

            m = re.search(r"\b(?:as\s*)?(\d{1,2})(?::(\d{2}))?\b", texto_norm)

            if m:
                hora = int(m.group(1))
                minuto = int(m.group(2) or 0)

                data_base = ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora")

                if data_base:
                    base = datetime.fromisoformat(data_base)

                    nova_data_hora = base.replace(
                        hour=hora,
                        minute=minuto,
                        second=0,
                        microsecond=0
                    ).isoformat()

                    ctx["data_hora"] = nova_data_hora
                    ctx["hora_confirmada"] = True

                    draft = ctx.get("draft_agendamento") or {}
                    draft["data_hora"] = nova_data_hora
                    ctx["draft_agendamento"] = draft

                    servico = ctx.get("servico")
                    profissional = ctx.get("profissional_escolhido")

                    ctx["dados_anteriores"] = {
                        "profissional": profissional,
                        "servico": servico,
                        "data_hora": nova_data_hora
                    }

                    if servico and profissional:
                        ctx["estado_fluxo"] = "agendando"
                        ctx["aguardando_confirmacao_agendamento"] = True
                        ctx["ultima_acao"] = "criar_evento"
                        ctx["dados_confirmacao_agendamento"] = {
                            "profissional": profissional,
                            "servico": servico,
                            "data_hora": nova_data_hora,
                            "duracao": estimar_duracao(servico),
                            "descricao": formatar_descricao_evento(servico, profissional),
                        }

                    else:
                        if servico and not profissional:
                            ctx["estado_fluxo"] = "aguardando_profissional"
                        elif profissional and not servico:
                            ctx["estado_fluxo"] = "aguardando_servico"
                        else:
                            ctx["estado_fluxo"] = "idle"

                        ctx["aguardando_confirmacao_agendamento"] = False
                        ctx["ultima_acao"] = None
                        ctx["dados_confirmacao_agendamento"] = None

                    await salvar_contexto_temporario(user_id, ctx)

                    if servico and profissional:
                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Perfeito — *{servico}* com *{profissional}* "
                            f"em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                            "Posso confirmar esse horário?"
                        )

                    if servico and not profissional:
                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Perfeito — *{servico}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                            "Qual profissional você prefere?"
                        )
   
                    if profissional and not servico:
                        return await _send_and_stop(
                            context,
                            user_id,
                            f"Perfeito — com *{profissional}* em *{formatar_data_hora_br(nova_data_hora)}*.\n"
                            "Qual serviço você quer fazer?"
                        )
 
        # 🔥 BLOCO ESPECÍFICO — AGUARDANDO SERVIÇO
        if ctx.get("estado_fluxo") == "aguardando_servico":
            texto_norm = normalizar(texto_usuario or "")
            partes = re.split(r"\bou\b|,|/", texto_norm)

            profs_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

            todos = []
            for p in profs_dict.values():
                todos.extend(p.get("servicos") or [])

            catalogo = list(dict.fromkeys([str(s).strip() for s in todos if s]))
            servicos_candidatos = []

            for parte in partes:
                parte = parte.strip()
                for s in catalogo:
                    if normalizar(s) in parte:
                        servicos_candidatos.append(s)

        # primeiro tenta responder algo determinístico já existente no fluxo
        if estado_fluxo == "aguardando_profissional":
            tnorm_guard = normalizar(texto_usuario or "")
            if tnorm_guard in ["quais", "quais voce tem", "quais você tem", "quem", "quem tem", "opcoes", "opções"]:
                if payload_resposta.get("profissionais_permitidos"):
                    lista = ", ".join(payload_resposta["profissionais_permitidos"])
                    return await _send_and_stop(
                        context,
                        user_id,
                        f"Para *{slots_extraidos.get('servico')}*, eu tenho: {lista}.\n\nQual profissional você prefere?"
                    )

        resposta_texto = montar_resposta_fallback(
            proximo_passo_real,
            frase_data_legivel,
            ctx
        )

        # NÃO responder aqui se ainda está coletando serviço.
        # Deixa o bloco específico de aguardando_servico tratar antes do GPT.
        if ctx.get("estado_fluxo") != "aguardando_servico":
            return await _send_and_stop(context, user_id, resposta_texto)

    # =========================================================
    # 🔥 BLOQUEIO DE GPT — só quando ainda NÃO tem serviço
    # =========================================================
    if (
        ctx.get("data_hora")
        and ctx.get("horarios_sugeridos")
        and not ctx.get("servico")
    ):
        print("🛑 [BLOQUEIO GPT] já tenho data + horários (sem serviço)", flush=True)

        ctx["estado_fluxo"] = "aguardando_servico"
        await salvar_contexto_temporario(user_id, ctx)

        horarios = ctx.get("horarios_sugeridos") or []
        horarios_txt = " ou ".join(horarios)
        base = montar_frase_data_legivel(ctx.get("data_hora"))

        return await _send_and_stop(
            context,
            user_id,
            f"Perfeito — {base} por volta de {horarios_txt} 😊\n\nQual serviço você deseja?"
        )

    # =========================================================
    # 🔒 BLOQUEIO DE AGENDA DO SALÃO — ANTES DO GPT (GLOBAL)
    # =========================================================
    payload_bloqueio = detectar_bloqueio_agenda_salao(texto_usuario)

    if payload_bloqueio:
        print(f"🔒 [BLOQUEIO_AGENDA_SALAO/ANTES_GPT] payload={payload_bloqueio}", flush=True)
        return await executar_acao_por_nome(
            update,
            context,
            payload_bloqueio["acao"],
            payload_bloqueio["dados"]
        )

    # =========================================================
    # 🔥 BLOQUEIO DE GPT — quando já temos dados suficientes
    # =========================================================
    if (
        ctx.get("data_hora")
        and (
            (ctx.get("servico") and ctx.get("profissional_escolhido"))
            or (
                (ctx.get("draft_agendamento") or {}).get("servico")
                and (ctx.get("draft_agendamento") or {}).get("profissional")
            )
        )
    ):
        print("🚫 [BLOCK GPT] já tenho dados completos — fluxo determinístico", flush=True)

        return await executar_acao_gpt(
            update,
            context,
            "pre_confirmar_agendamento",
            {
                "data_hora": ctx.get("data_hora") or (ctx.get("draft_agendamento") or {}).get("data_hora"),
                "servico": ctx.get("servico") or (ctx.get("draft_agendamento") or {}).get("servico"),
                "profissional": ctx.get("profissional_escolhido") or (ctx.get("draft_agendamento") or {}).get("profissional"),
            }
        )
 
    resposta_gpt = await chamar_gpt_com_contexto(mensagem, contexto, INSTRUCAO_SECRETARIA)

    # 🔥 BLOQUEIO: se GPT respondeu algo direto, NÃO entra no fluxo
    if resposta_gpt and resposta_gpt.get("resposta") and not resposta_gpt.get("acao"):

        texto_resp = (resposta_gpt["resposta"] or "").lower()
        txt_user = (texto_usuario or "").strip().lower()

        saudacoes_usuario = [
            "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
            "e ai", "e aí", "eai", "opa", "oie"
        ]

        if txt_user in saudacoes_usuario and any(
            s in texto_resp for s in [
                "olá", "ola", "oi", "posso te ajudar", "como posso te ajudar", "como posso ajudar"
            ]
        ):
            return await _send_and_stop(
                context,
                user_id,
                resposta_gpt["resposta"]
            )

    resposta_texto = resposta_gpt.get("resposta")
    acao = resposta_gpt.get("acao")
    dados = resposta_gpt.get("dados", {}) or {}

    print("🧪 [OVERRIDE] acao=", acao, "proximo_passo=", proximo_passo, flush=True)

    # =========================================================
    # OVERRIDE FORÇADO — caso complexo guiado pelo sistema
    # =========================================================
    if not acao:
        resposta_texto = montar_resposta_fallback(proximo_passo_real, frase_data_legivel, ctx)

    print("🧪 [OVERRIDE] acao=", acao, "proximo_passo=", proximo_passo, "proximo_passo_real=", proximo_passo_real, flush=True)

    # =========================================================
    # PATCH — escrita ruidosa / interpretação incerta
    # GPT pode sugerir entendimento, mas não autoriza efeito colateral
    # =========================================================
    if acao == "criar_evento":
        prof = dados.get("profissional")
        servico = dados.get("servico")
        data_hora = dados.get("data_hora")
        descricao = dados.get("descricao") or ""

        # fallback: tenta derivar serviço da descrição, se o GPT não enviou
        if not servico and descricao and " com " in descricao.lower():
            servico = descricao.split(" com ")[0].strip().lower()

        # heurística de baixa confiança:
        # - texto original muito diferente do texto "limpo"
        # - serviço/profissional vieram, mas o usuário escreveu curto/ruidoso
        # - ou faltou algum campo essencial
        texto_norm = normalizar(texto_usuario)
        texto_curto = len(texto_norm.split()) <= 5

        sinais_ruido = 0
        if texto_curto:
            sinais_ruido += 1
        if "?" in texto_usuario:
            sinais_ruido += 1
        if not servico or not prof or not data_hora:
            sinais_ruido += 2

        # sinais de escrita ruidosa comuns sem depender de lista fixa
        palavras = texto_norm.split()
        palavras_muito_curta = sum(1 for p in palavras if len(p) <= 3)
        if palavras and (palavras_muito_curta / max(len(palavras), 1)) >= 0.4:
            sinais_ruido += 1

        # se o GPT devolveu descrição muito mais "arrumada" do que o texto do usuário,
        # exige confirmação em vez de executar direto
        descricao_norm = normalizar(descricao)
        if descricao_norm and texto_norm and descricao_norm not in texto_norm:
            sinais_ruido += 1

        exigir_confirmacao = sinais_ruido >= 2

        if exigir_confirmacao:
            if prof and servico and data_hora:
                data_ref = data_hora.split("T")[0]
                hora_ref = data_hora.split("T")[1][:5]

                id_dono = await obter_id_dono(user_id)

                validacao = await validar_horario_funcionamento(
                    user_id=id_dono,
                    data_iso=data_ref,
                    hora_inicio=hora_ref,
                    duracao_min=dados.get("duracao") or estimar_duracao(servico),
                )

                if not validacao.get("permitido"):
                    tentativa = await resolver_fora_do_expediente(
                        user_id=id_dono,
                        data_iso=data_ref,
                        hora_inicio=hora_ref,
                        duracao_min=dados.get("duracao") or estimar_duracao(servico),
                        servico=servico,
                        profissional=prof,
                    )

                    if tentativa.get("ok"):
                        horario = tentativa.get("horario")
                        nova_data_hora = tentativa.get("data_hora")

                        if nova_data_hora:
                            ctx["data_hora"] = nova_data_hora

                            draft = ctx.get("draft_agendamento") or {}
                            draft["profissional"] = prof
                            draft["servico"] = servico
                            draft["data_hora"] = nova_data_hora
                            draft["modo_prechecagem"] = True
                            ctx["draft_agendamento"] = draft

                            await salvar_contexto_temporario(user_id, ctx)

                        return await _send_and_stop(
                            context,
                            user_id,
                            (
                                "Infelizmente esse horário fica fora do nosso expediente 😕\n\n"
                                f"O horário mais próximo com *{prof}* é às *{horario}*.\n"
                                "Posso agendar pra você? 😊"
                            )
                        )

                    return await _send_and_stop(
                        context,
                        user_id,
                        "❌ Não consegui encaixar esse horário. Me diga outro que eu verifico pra você."
                    )

                ctx["estado_fluxo"] = "agendando"
                ctx["draft_agendamento"] = {
                    "profissional": prof,
                    "servico": servico,
                    "data_hora": data_hora,
                    "modo_prechecagem": True,
                }
                ctx["aguardando_confirmacao_agendamento"] = True
                ctx["dados_confirmacao_agendamento"] = {
                    "profissional": prof,
                    "servico": servico,
                    "data_hora": data_hora,
                    "duracao": dados.get("duracao") or estimar_duracao(servico),
                    "descricao": formatar_descricao_evento(servico, prof),
                }
                ctx["ultima_opcao_profissionais"] = [prof]

                await salvar_contexto_temporario(user_id, ctx)

                return await _send_and_stop(
                    context,
                    user_id,
                    (
                        f"Só confirmando rapidinho:\n\n"
                        f"✨ *{servico.capitalize()} com {prof}*\n"
                        f"📆 {formatar_data_hora_br(data_hora)}\n\n"
                        f"Posso confirmar?"
                    )
                )

            return await _send_and_stop(
                context,
                user_id,
                "Entendi parte do agendamento, mas faltaram dados. Me diga novamente profissional, serviço e horário."
            )

    if (
        slots_extraidos.get("data_hora")
        and slots_extraidos.get("servico")
        and slots_extraidos.get("profissional")
    ):
        print("🔥 [P0] PRÉ-CHECAGEM — SEM GPT", flush=True)

        return await executar_acao_gpt(
            update,
            context,
            "pre_confirmar_agendamento",
            {
                "data_hora": slots_extraidos["data_hora"],
                "servico": slots_extraidos["servico"],
                "profissional": slots_extraidos["profissional"]
            }
        )

    # ✅ REGRA DE OURO FINAL:
    # Só permite ação mutável quando houver:
    # - continuidade real de agendamento
    # - confirmação pendente
    # Fora disso, consulta pura / desvio bloqueiam criar_evento e cancelar_evento.

    fluxo_agendamento_ativo = tem_contexto_agendamento_ativo(contexto)
    continuando_agendamento = eh_continuacao_de_agendamento(texto_lower, contexto)
    confirmacao_pendente = bool(contexto.get("aguardando_confirmacao_agendamento"))

    consulta_pura = eh_consulta(texto_lower)
    esta_em_modo_consulta = (estado_fluxo == "consultando")

    # ✅ novo: intenção explícita de agendar, mesmo que ainda falte horário
    gatilhos_agendar = [
        "quero", "agendar", "agenda", "marcar", "marca", "pode marcar",
        "pode agendar", "quero agendar", "quero marcar"
    ]
    quer_agendar_expresso = any(g in texto_lower for g in gatilhos_agendar)

    profissional_no_texto = bool((dados or {}).get("profissional")) or any(
        normalizar(str(p.get("nome", ""))) in normalizar(texto_lower)
        for p in profissionais_dict.values()
    )

    servico_no_texto = bool((dados or {}).get("servico")) or any(
        normalizar(str(s)) in normalizar(texto_lower)
        for p in profissionais_dict.values()
        for s in (p.get("servicos") or [])
    )

    # aceita data vaga também (amanhã / hoje / sexta / dia 10 etc.)
    tem_data_ou_hora = bool((dados or {}).get("data_hora")) or (
        _tem_indicio_de_hora(texto_usuario)
        or any(x in normalizar(texto_lower) for x in ["amanha", "amanhã", "hoje", "sexta", "sabado", "sábado", "domingo"])
    )

    novo_agendamento_expresso = (
        quer_agendar_expresso and (profissional_no_texto or servico_no_texto or tem_data_ou_hora)
    )

    bloquear_acao_mutavel = False

    if acao in ("criar_evento", "cancelar_evento"):

        # 1) Continuidade real sempre libera
        if continuando_agendamento or confirmacao_pendente:
            bloquear_acao_mutavel = False

        # 2) Novo pedido explícito de agendamento também libera
        elif novo_agendamento_expresso:
            bloquear_acao_mutavel = False

        # 3) Consulta pura, sem continuidade nem intenção explícita, bloqueia
        elif consulta_pura:
            bloquear_acao_mutavel = True

        # 4) Em modo consulta, só bloqueia se não for continuação nem agendamento novo
        elif esta_em_modo_consulta and not novo_agendamento_expresso:
            bloquear_acao_mutavel = True

        # 5) Fluxo ativo com desvio real bloqueia
        elif fluxo_agendamento_ativo and not continuando_agendamento and not novo_agendamento_expresso:
            bloquear_acao_mutavel = True

    if bloquear_acao_mutavel:
        print(f"🛑 [estado_fluxo] Bloqueado '{acao}' pois mensagem é consulta/desvio: '{texto_lower}'", flush=True)

        faltando = []
        if not profissional_no_texto and not contexto.get("profissional_escolhido"):
            faltando.append("profissional")
        if not servico_no_texto and not contexto.get("servico"):
            faltando.append("serviço")
        if not tem_data_ou_hora and not contexto.get("data_hora"):
            faltando.append("dia/horário")

        if faltando:
            return await _send_and_stop(
                context,
                user_id,
                f"Perfeito — para agendar, só falta informar: {', '.join(faltando)}."
            )

        return await _send_and_stop(
            context,
            user_id,
            "Entendi. Me diga só o horário que você prefere."
        )

    ACOES_SUPORTADAS = {
        "consultar_preco_servico",
        "criar_evento",
        "buscar_eventos_da_semana",
        "criar_tarefa",
        "remover_tarefa",
        "cancelar_evento",
        "listar_followups",
        "cadastrar_profissional",
        "aguardar_arquivo_importacao",
        "enviar_email",
        "organizar_semana",
        "buscar_tarefas_do_usuario",
        "buscar_emails",
        "verificar_pagamento",
        "verificar_acesso_modulo",
        "responder_audio",
        "criar_followup",
        "buscar_eventos_do_dia",
        "buscar_eventos_do_dia",
    }

    handled = False

    if acao:
        if acao not in ACOES_SUPORTADAS:
            print(f"⚠️ Ação '{acao}' não suportada. Ignorando...", flush=True)
            acao = None
            dados = {}
        else:
            # 🔒 Não deixa criar evento se a hora não foi explicitamente dita pelo usuário
            if acao == "criar_evento":
                tem_hora_no_texto = _tem_indicio_de_hora(mensagem)

                if not tem_hora_no_texto:
                    print("🛑 Bloqueado criar_evento: sem hora explícita no texto", flush=True)

                    servico_ctx = (
                        (dados or {}).get("servico")
                        or contexto.get("servico")
                        or (contexto.get("draft_agendamento") or {}).get("servico")
                    )
                    profissional_ctx = (
                        (dados or {}).get("profissional")
                        or contexto.get("profissional_escolhido")
                        or (contexto.get("draft_agendamento") or {}).get("profissional")
                    )

                    data_hora_ctx = (
                        (dados or {}).get("data_hora")
                        or contexto.get("data_hora")
                        or (contexto.get("draft_agendamento") or {}).get("data_hora")
                    )

                    if data_hora_ctx:
                        try:
                            dt_base = _dt_from_iso_naive(data_hora_ctx)
                            if dt_base:
                                data_base_iso = dt_base.replace(
                                    hour=0, minute=0, second=0, microsecond=0
                                ).isoformat()
                            else:
                                data_base_iso = data_hora_ctx
                        except Exception:
                            data_base_iso = data_hora_ctx
                    else:
                        data_base_iso = None

                    estado_fluxo_atual = contexto.get("estado_fluxo")

                    contexto_update = {
                        "estado_fluxo": (
                        "aguardando_escolha_horario"
                        if estado_fluxo_atual == "aguardando_escolha_horario"
                            else "aguardando_horario"
                        ),
                        "servico": servico_ctx,
                        "profissional_escolhido": profissional_ctx,
                        "ultima_acao": "criar_evento",
                        "draft_agendamento": {
                            "servico": servico_ctx,
                            "profissional": profissional_ctx,
                            "data_hora": data_base_iso,
                        },
                    }

                    if estado_fluxo_atual == "aguardando_escolha_horario":
                        contexto_update["horarios_sugeridos"] = contexto.get("horarios_sugeridos") or []

                    if data_base_iso:
                        contexto_update["data_hora"] = data_base_iso

                    ctx_atual = await carregar_contexto_temporario(user_id) or {}

                    # 🔥 NÃO deixar perder estado de escolha de horário
                    if ctx_atual.get("estado_fluxo") == "aguardando_escolha_horario":
                        contexto_update["estado_fluxo"] = "aguardando_escolha_horario"
                        contexto_update["horarios_sugeridos"] = ctx_atual.get("horarios_sugeridos") or []

                    # 🔥 merge em vez de sobrescrever
                    ctx_atual.update(contexto_update)

                    await salvar_contexto_temporario(user_id, ctx_atual)

                    partes = []
                    if servico_ctx:
                        partes.append(str(servico_ctx))
                    if profissional_ctx:
                        partes.append(f"com {profissional_ctx}")

                    resumo = " ".join(partes).strip()

                    data_legivel = "esse dia"
                    if data_base_iso:
                        try:
                            dt_msg = _dt_from_iso_naive(data_base_iso)
                            hoje = _agora_br_naive().date()
                            if dt_msg:
                                if dt_msg.date() == hoje:
                                    data_legivel = "hoje"
                                elif dt_msg.date() == (hoje + timedelta(days=1)):
                                    data_legivel = "amanhã"
                                else:
                                    data_legivel = dt_msg.strftime("%d/%m")
                        except Exception:
                            pass

                    if resumo:
                        msg = f"Perfeito — {resumo} para {data_legivel}.\nAgora me diga o horário que você prefere."
                    else:
                        msg = f"Perfeito — agora me diga o horário que você prefere para {data_legivel}."

                    return await _send_and_stop(context, user_id, msg)

            handled = await executar_acao_gpt(update, context, acao, dados)

            if acao == "criar_evento":
                return {"acao": "criar_evento", "handled": True}

    # =========================================================
    # SE GPT SÓ RESPONDEU TEXTO EM CASO COMPLEXO,
    # CONVERTE ISSO EM ESTADO OPERACIONAL REAL
    # =========================================================

    contexto = contexto or {}

    if not acao and proximo_passo_real:

        if proximo_passo_real == "perguntar_servico":
            if (
                not ctx.get("servico")
                and ctx.get("estado_fluxo") not in ["aguardando_confirmacao_agendamento", "agendando"]
            ):
                ctx["estado_fluxo"] = "aguardando_servico"

        elif proximo_passo_real == "perguntar_profissional":
            ctx["estado_fluxo"] = "aguardando_profissional"

        elif proximo_passo_real == "perguntar_somente_horario":
            ctx["estado_fluxo"] = "aguardando_horario"

        elif proximo_passo_real == "perguntar_data_hora":
            ctx["estado_fluxo"] = "aguardando_data"

        if slots_extraidos.get("servico"):
            ctx["servico"] = slots_extraidos["servico"]
        if slots_extraidos.get("profissional"):
            ctx["profissional_escolhido"] = slots_extraidos["profissional"]
        if slots_extraidos.get("data_hora"):
            ctx["data_hora"] = slots_extraidos["data_hora"]

        draft = ctx.get("draft_agendamento") or {}
        if slots_extraidos.get("servico"):
            draft["servico"] = slots_extraidos["servico"]
        if slots_extraidos.get("profissional"):
            draft["profissional"] = slots_extraidos["profissional"]
        if slots_extraidos.get("data_hora"):
            draft["data_hora"] = slots_extraidos["data_hora"]

        ctx["draft_agendamento"] = draft

        print("🧪 [SALVANDO ESTADO COMPLEXO] ctx=", ctx, flush=True)
        await salvar_contexto_temporario(user_id, ctx)


    if (not acao) and resposta_texto:
        await atualizar_contexto(user_id, {"usuario": mensagem, "bot": resposta_texto})
        return await _send_and_stop(context, user_id, resposta_texto)

    if acao:
        return {"acao": acao, "handled": bool(handled)}

    return {"resposta": "❌ Não consegui interpretar sua mensagem."}