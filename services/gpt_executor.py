from telegram import Update
from telegram.ext import ContextTypes

from datetime import datetime
import json
from typing import Optional

from handlers.task_handler import add_task_por_gpt, gerar_texto_tarefas, remover_tarefa_por_descricao
from handlers.event_handler import add_evento_por_gpt
from utils.identidade_contexto import IdentidadeContexto
from handlers.email_handler import listar_emails_prioritarios, ler_emails_command
from handlers.followup_handler import configurar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.perfil_handler import meu_plano

from utils.plan_utils import verificar_pagamento, verificar_acesso_modulo
from utils.tts_utils import responder_em_audio
from utils.gpt_utils import estimar_duracao
from utils.formatters import formatar_eventos_telegram
from utils.contexto_temporario import (
    carregar_contexto_temporario,
    salvar_contexto_temporario,
    salvar_contexto_temporario_v2,
)

from services.firebase_service_async import buscar_subcolecao, obter_id_dono
from services.email_service import enviar_email_google
from services.event_service_async import (
    cancelar_evento_por_texto,
    buscar_eventos_por_termo_avancado,
    cancelar_evento,
    verificar_conflito_e_sugestoes_profissional,
    buscar_eventos_por_intervalo,
)
from services.agenda_service import (
    validar_horario_funcionamento,
    resolver_fora_do_expediente,
    obter_janela_funcionamento,
)
from services.profissional_service import buscar_profissionais_disponiveis_no_horario

# ✅ Executor de ações baseado no JSON retornado pelo GPT
from services.event_service_async import buscar_eventos_por_intervalo  # Importação necessária


# ═══════════════════════════════════════════════════════════════════════════════
# P0.3: CONTRATO RESULTADO AÇÃO — Separação Execução × Transporte
# ═══════════════════════════════════════════════════════════════════════════════

def resultado_acao(
    ok: bool,
    acao: str,
    resposta: str = None,
    resultado: any = None,
    erro: str = None,
    already_sent: bool = False,
    handled: bool = True
) -> dict:
    """
    Construtor do contrato ResultadoAcao (P0.3).

    Retorna dict estruturado que separar execução de transporte.

    Args:
        ok: True se ação foi executada com sucesso
        acao: Nome da ação executada
        resposta: Mensagem ao usuário
        resultado: Resultado específico da ação (evento criado, etc)
        erro: Mensagem de erro se houver
        already_sent: True APENAS se mensagem foi enviada pelo transporte
        handled: True se foi tratado (não deve processar mais)

    Returns:
        Dict com campos: ok, acao, resultado, resposta, erro, already_sent, handled
    """
    return {
        "ok": ok,
        "acao": acao,
        "resultado": resultado,
        "resposta": resposta,
        "erro": erro,
        "already_sent": already_sent,
        "handled": handled
    }


# 🔥 P0: Sanitizador de cancelamento_pendente — apenas dados serializáveis
def sanitizar_cancelamento_pendente(candidatos, cliente_id, evento_id=None):
    """
    Converte candidatos (lista de tuplas) em estrutura serializável para Firestore.

    Caso único: retorna dict com evento_id
    Caso múltiplo: retorna dict com resumo_eventos (lista)

    Proibido: tuplas, evento dict inteiro, datetime, DocumentSnapshot
    """
    if not candidatos:
        return None

    # Construir resumo_eventos a partir de candidatos
    resumo_eventos = []
    for item in candidatos:
        if isinstance(item, tuple):
            eid, ev = item
        else:
            eid, ev = item.get("evento_id"), item

        resumo_eventos.append({
            "evento_id": str(eid),
            "descricao": str(ev.get("descricao", "") if isinstance(ev, dict) else ""),
            "data": str(ev.get("data", "") if isinstance(ev, dict) else ""),
            "hora_inicio": str(ev.get("hora_inicio", "") if isinstance(ev, dict) else ""),
            "profissional": str(ev.get("profissional", "") if isinstance(ev, dict) else ""),
        })

    # Caso único
    if len(resumo_eventos) == 1:
        res = resumo_eventos[0]
        resultado = {
            "evento_id": res["evento_id"],
            "cliente_id": str(cliente_id),
            "resumo_evento": res
        }
    else:
        # Caso múltiplo
        resultado = {
            "cliente_id": str(cliente_id),
            "resumo_eventos": resumo_eventos
        }

    # Validar serializabilidade
    try:
        json.dumps(resultado, ensure_ascii=False)
        print(f"[SANITIZAR_CANCELAMENTO] OK - serializavel", flush=True)
        return resultado
    except TypeError as e:
        print(f"[SANITIZAR_CANCELAMENTO] ERRO - nao serializavel: {e}", flush=True)
        return None


def _obter_user_id(update, context) -> str:
    uid = None
    try:
        if getattr(update, "effective_user", None) and getattr(update.effective_user, "id", None):
            uid = update.effective_user.id
        elif getattr(update, "message", None) and getattr(update.message, "chat", None):
            uid = update.message.chat.id
    except Exception:
        pass

    if not uid:
        uid = (
            context.user_data.get("user_id")
            or context.chat_data.get("user_id")
            or context.bot_data.get("user_id")
        )

    return str(uid) if uid else ""


def _normalizar_nome(x: str) -> str:
    return (x or "").strip().lower()


def _extrair_servico_do_contexto(contexto: dict) -> str:
    """
    Tenta encontrar o serviço atual salvo no MemoriaTemporaria.
    Ajuste aqui se você salva o serviço em outra chave.
    """
    if not isinstance(contexto, dict):
        return ""

    # seus logs mostram: {'servico': 'escova', 'data_hora': ...}
    s = contexto.get("servico")
    if isinstance(s, str) and s.strip():
        return s.strip()

    # fallback caso você tenha estrutura aninhada em algum momento
    ag = contexto.get("agendamento") or {}
    if isinstance(ag, dict):
        s2 = ag.get("servico")
        if isinstance(s2, str) and s2.strip():
            return s2.strip()

    return ""


async def _listar_profissionais_validos_para_servico(dono_id: str, servico: str) -> list[str]:
    """
    Busca em Clientes/{dono_id}/Profissionais e filtra por quem contém 'servico' em 'servicos'.
    Retorna lista de NOMES (strings).
    """
    if not dono_id or not servico:
        return []

    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}
    servico_norm = _normalizar_nome(servico)

    validos = []
    for _, prof in profissionais_dict.items():
        if not isinstance(prof, dict):
            continue
        nome = prof.get("nome") or ""
        servicos = prof.get("servicos") or []
        if not nome or not isinstance(servicos, list):
            continue

        servicos_norm = [_normalizar_nome(x) for x in servicos if isinstance(x, str)]
        if servico_norm in servicos_norm:
            validos.append(str(nome).strip())

    # ordena pra ficar determinístico
    validos = sorted(set(validos), key=lambda x: x.lower())
    return validos


async def executar_acao_gpt_resultado(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str, dados: dict, identidade: Optional[IdentidadeContexto] = None):
    """
    Wrapper que normaliza o retorno de executar_acao_gpt para sempre ser dict.

    Contrato:
    - executar_acao_gpt retorna bool ou dict (histórico misto)
    - Este wrapper normaliza para dict sempre

    Retorno normalizado:
    {
        "ok": bool,           # True se sucesso, False se falha
        "acao": str,          # Nome da ação executada
        "resultado": any,     # Resultado específico da ação
        "erro": str | None,   # Mensagem de erro se houver
        "tipo_erro": str | None  # Tipo/classe do erro
    }
    """
    resultado = await executar_acao_gpt(update, context, acao, dados, identidade=identidade)

    # Se já é dict (exc block), garantir que tem chave "ok"
    if isinstance(resultado, dict):
        if "ok" not in resultado:
            resultado["ok"] = resultado.get("sucesso", True)
        return resultado

    # Se é bool, normalizar para dict
    if isinstance(resultado, bool):
        return {
            "ok": resultado,
            "acao": acao,
            "resultado": resultado,
            "erro": None if resultado else "executar_acao_gpt_retornou_false",
            "tipo_erro": None if resultado else "retorno_false"
        }

    # Fallback: algo inesperado
    return {
        "ok": False,
        "acao": acao,
        "resultado": resultado,
        "erro": f"tipo_retorno_inesperado: {type(resultado).__name__}",
        "tipo_erro": "tipo_retorno_desconhecido"
    }


async def executar_acao_gpt(
    update: Optional[Update] = None,
    context: Optional[ContextTypes.DEFAULT_TYPE] = None,
    acao: str = "",
    dados: dict = None,
    identidade: Optional[IdentidadeContexto] = None,
):
    """
    Executar ação determinística ou delegada ao GPT.

    P0.2: Aceita IdentidadeContexto para ser agnóstico de canal.

    Args:
        update: Telegram Update (opcional, para compatibilidade)
        context: Telegram Context (opcional, para compatibilidade)
        acao: Nome da ação a executar
        dados: Dados específicos da ação
        identidade: IdentidadeContexto normalizado (novo, opcional)

    Se identidade for passado, usar dele.
    Se não, tentar extrair de update (compatibilidade Telegram).
    """
    try:
        print(f"[DEBUG] Acao recebida: {repr(acao)}")

        if not acao or acao.strip() == "":
            return False

        # [P0.2] Obter identidade de forma agnóstica
        if identidade:
            # Usar identidade normalizada
            user_id = identidade.user_id
            tenant_id = identidade.tenant_id
            canal = identidade.canal
            print(f"[P0.2] Usando IdentidadeContexto: canal={canal}, user_id={user_id}, tenant_id={tenant_id}", flush=True)
        else:
            # Fallback para Telegram (compatibilidade)
            if not update or not update.message:
                print(f"[P0.2] ERRO: Nem identidade nem update fornecidos", flush=True)
                return False

            user_id = str(update.message.from_user.id)
            tenant_id = await obter_id_dono(user_id)
            canal = "telegram"
            print(f"[P0.2] Usando fallback Telegram: user_id={user_id}, tenant_id={tenant_id}", flush=True)

        print(f"[ACAO] Recebida: {acao}")
        print(f"[DADOS] Valores: {dados}")

        if acao == "criar_tarefa":
            await add_task_por_gpt(update, context, dados)
            return True

        elif acao == "buscar_tarefas_do_usuario":
            # [P0.3] Separar execução de transporte
            # Obter user_id de identidade ou fallback
            if identidade:
                user_id = identidade.user_id
            else:
                user_id = (update.message.from_user.id if update and update.message else None)
                if not user_id:
                    return resultado_acao(
                        ok=False,
                        acao=acao,
                        resposta="Não consegui identificar o usuário.",
                        erro="user_id_missing",
                        already_sent=False
                    )
                user_id = str(user_id)

            texto_tarefas = await gerar_texto_tarefas(user_id)
            resposta_texto = dados.get("resposta") or "📋 Aqui está sua lista de tarefas:\n"
            mensagem = f"{resposta_texto}\n\n{texto_tarefas}"

            # [P0.3] Se update é disponível, marcar como enviado pelo Telegram
            already_sent = bool(update and update.message)
            if already_sent:
                await update.message.reply_text(mensagem, parse_mode="Markdown")

            return resultado_acao(
                ok=True,
                acao=acao,
                resposta=mensagem,
                resultado={"tarefas": texto_tarefas},
                already_sent=already_sent
            )

        elif acao == "pre_confirmar_agendamento":

            # [P0.2] Obter user_id de identidade ou fallback
            if identidade:
                user_id = identidade.user_id
            else:
                user_id = _obter_user_id(update, context)

            if not user_id:
                # [P0.3] Retornar dict de erro em vez de reply_text
                msg = "⚠️ Não consegui identificar o usuário."
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg,
                    erro="user_id_not_identified",
                    already_sent=already_sent
                )

            prof = (dados or {}).get("profissional")
            servico = (dados or {}).get("servico")
            data_hora = (dados or {}).get("data_hora")

            if not (prof and servico and data_hora):
                # [P0.3] Retornar dict de erro
                msg = "Faltaram dados para confirmar o agendamento."
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg,
                    erro="missing_required_data",
                    already_sent=already_sent
                )

            # 🔥 VERIFICAR CONFLITO
            data = data_hora.split("T")[0]
            hora = data_hora.split("T")[1][:5]
            duracao = estimar_duracao(servico)

            # =========================================================
            # 🔒 VALIDAÇÃO DE EXPEDIENTE (FALTAVA AQUI)
            # =========================================================
            if identidade and identidade.tenant_id:
                id_dono = identidade.tenant_id
            else:
                id_dono = await obter_id_dono(user_id)

            validacao = await validar_horario_funcionamento(
                user_id=id_dono,
                data_iso=data,
                hora_inicio=hora,
                duracao_min=duracao,
                profissional=prof,
            )

            print(f"🧪 [P0 EXPEDIENTE] permitido={validacao.get('permitido')} | motivo={validacao.get('motivo')}", flush=True)

            if not validacao.get("permitido"):
                motivo = validacao.get("motivo")

                # 🔥 DIA FECHADO → NÃO tenta sugerir horário
                if motivo == "fechado_na_data":
                    regra = validacao.get("regra") or {}
                    origem = regra.get("origem")

                    if origem == "excecao_profissional":

                        data_obj = datetime.strptime(data, "%Y-%m-%d")

                        alternativas = await buscar_profissionais_disponiveis_no_horario(
                            user_id=id_dono,
                            data=data_obj,
                            hora=hora,
                            duracao=duracao,
                        ) or {}

                        nomes_validos = []

                        for nome_alt, dados_alt in alternativas.items():
                            if (nome_alt or "").strip().lower() == (prof or "").strip().lower():
                                continue

                            servicos_alt = [
                                str(s).strip().lower()
                                for s in (dados_alt.get("servicos") or [])
                            ]

                            if (servico or "").strip().lower() in servicos_alt:
                                nomes_validos.append(nome_alt)

                        if nomes_validos:
                            alternativo = nomes_validos[0]
                            nova_data_hora = f"{data}T{hora}:00"

                            contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}

                            contexto_tmp["alternativa_profissional"] = alternativo
                            contexto_tmp["profissional_escolhido"] = alternativo
                            contexto_tmp["servico"] = servico
                            contexto_tmp["data_hora"] = nova_data_hora

                            contexto_tmp["estado_fluxo"] = "agendando"
                            contexto_tmp["aguardando_confirmacao_agendamento"] = True

                            contexto_tmp["draft_agendamento"] = {
                                "profissional": alternativo,
                                "servico": servico,
                                "data_hora": nova_data_hora,
                                "modo_prechecagem": True,
                            }

                            contexto_tmp["dados_confirmacao_agendamento"] = {
                                "origem": "confirmacao_pendente",
                                "profissional": alternativo,
                                "servico": servico,
                                "data_hora": nova_data_hora,
                                "duracao": duracao,
                                "descricao": f"{servico.capitalize()} com {alternativo}",
                            }

                            await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)

                            # [P0.3] Retornar dict em vez de reply_text
                            msg = (
                                f"😕 A {prof} não estará atendendo nesse dia.\n\n"
                                f"Tenho *{alternativo}* disponível às *{hora}* para *{servico}*.\n"
                                "Posso agendar pra você? 😊"
                            )
                            already_sent = False
                            if update and update.message:
                                await update.message.reply_text(msg, parse_mode="Markdown")
                                already_sent = True
                            return resultado_acao(
                                ok=True,
                                acao=acao,
                                resposta=msg,
                                resultado={"alternativa": alternativo, "motivo": "profissional_indisponivel"},
                                already_sent=already_sent
                            )

                        # [P0.3] Sem alternativas
                        msg = (
                            f"😕 A {prof} não estará atendendo nesse dia.\n\n"
                            "Me diga outro dia ou outro profissional que eu verifico para você 😊"
                        )
                        already_sent = False
                        if update and update.message:
                            await update.message.reply_text(msg, parse_mode="Markdown")
                            already_sent = True
                        return resultado_acao(
                            ok=True,
                            acao=acao,
                            resposta=msg,
                            resultado={"alternativa": None, "motivo": "profissional_indisponivel_sem_alternativa"},
                            already_sent=already_sent
                        )

                    # [P0.3] Dia fechado
                    msg = (
                        "😕 Nesse dia não vamos atender.\n\n"
                        "Por favor, me informe outro dia que eu verifico para você 😊"
                    )
                    already_sent = False
                    if update and update.message:
                        await update.message.reply_text(msg, parse_mode="Markdown")
                        already_sent = True
                    return resultado_acao(
                        ok=True,
                        acao=acao,
                        resposta=msg,
                        resultado={"motivo": "dia_fechado"},
                        already_sent=already_sent
                    )

                if motivo == "fora_do_expediente":
                    tentativa = await resolver_fora_do_expediente(
                        user_id=id_dono,
                        data_iso=data,
                        hora_inicio=hora,
                        duracao_min=duracao,
                        servico=servico,
                        profissional=prof,
                    )

                    if tentativa.get("ok"):
                        horario = tentativa.get("horario")
                        nova_data_hora = tentativa.get("data_hora")

                        contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}

                        contexto_tmp["estado_fluxo"] = "agendando"
                        contexto_tmp["data_hora"] = nova_data_hora
                        contexto_tmp["profissional_escolhido"] = prof
                        contexto_tmp["servico"] = servico

                        contexto_tmp["draft_agendamento"] = {
                            "profissional": prof,
                            "servico": servico,
                            "data_hora": nova_data_hora,
                            "modo_prechecagem": True,
                        }

                        contexto_tmp["aguardando_confirmacao_agendamento"] = True
                        contexto_tmp["dados_confirmacao_agendamento"] = {
                            "origem": "confirmacao_pendente",
                            "profissional": prof,
                            "servico": servico,
                            "data_hora": nova_data_hora,
                            "duracao": duracao,
                            "descricao": f"{servico.capitalize()} com {prof}",
                        }

                        await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)

                        janela = await obter_janela_funcionamento(
                            user_id=id_dono,
                            data_str=data,
                            profissional=prof,
                        )

                        fim_janela = janela.get("fim") if janela.get("aberto") else None

                        texto_base = ""

                        if fim_janela:
                            texto_base = (
                                f"Esse horário não está disponível nesse dia, porque o salão atende só até {fim_janela}.\n\n"
                            )
                        else:
                            texto_base = (
                                "Esse horário não está disponível nesse dia.\n\n"
                            )

                        # [P0.3] Retornar dict
                        msg = (
                            texto_base
                            + f"O horário mais próximo com *{prof}* é às *{horario}*.\n"
                            + "Posso agendar pra você? 😊"
                        )
                        already_sent = False
                        if update and update.message:
                            await update.message.reply_text(msg, parse_mode="Markdown")
                            already_sent = True
                        return resultado_acao(
                            ok=True,
                            acao=acao,
                            resposta=msg,
                            resultado={"horario_sugerido": horario, "motivo": "fora_do_expediente_com_alternativa"},
                            already_sent=already_sent
                        )

                    # [P0.3] Sem mais horários disponíveis
                    msg = (
                        "😕 Esse horário não encaixa e hoje já não tenho mais horários próximos disponíveis.\n\n"
                        "Me fala outro dia e horário que eu vejo o melhor pra você 😊"
                    )
                    already_sent = False
                    if update and update.message:
                        await update.message.reply_text(msg, parse_mode="Markdown")
                        already_sent = True
                    return resultado_acao(
                        ok=True,
                        acao=acao,
                        resposta=msg,
                        resultado={"motivo": "fora_do_expediente_sem_alternativa"},
                        already_sent=already_sent
                    )

            resultado = await verificar_conflito_e_sugestoes_profissional(
                user_id=user_id,
                data=data,
                hora_inicio=hora,
                duracao_min=duracao,
                profissional=prof,
                servico=servico,
                tenant_id=tenant_id
            )

            # 🚨 CONFLITO
            if resultado.get("conflito"):

                sugestoes = resultado.get("sugestoes") or []
                sugestoes_formatadas = "\n".join(f"🔄 {s}" for s in sugestoes)

                # profissionais alternativos para o mesmo serviço
                alternativas = []

                try:
                    dono_id = await obter_id_dono(user_id)
                    profissionais_dict = await buscar_subcolecao(f"Clientes/{dono_id}/Profissionais") or {}

                    for _, p in profissionais_dict.items():
                        nome_alt = (p.get("nome") or "").strip()
                        if not nome_alt or nome_alt.lower() == (prof or "").strip().lower():
                            continue

                        servicos_alt = [str(s).strip().lower() for s in (p.get("servicos") or [])]
                        if (servico or "").strip().lower() not in servicos_alt:
                            continue

                        # checa se esse profissional está livre exatamente no mesmo horário
                        resultado_alt = await verificar_conflito_e_sugestoes_profissional(
                            user_id=user_id,
                            data=data,
                            hora_inicio=hora,
                            duracao_min=duracao,
                            profissional=nome_alt,
                            servico=servico,
                            tenant_id=tenant_id
                        )

                        if not resultado_alt.get("conflito"):
                            alternativas.append(nome_alt)

                except Exception as e:
                    print(f"⚠️ Falha ao montar alternativas no mesmo horário: {e}", flush=True)

                # =========================================================
                # 🔥 SALVA ESTADO DE ESCOLHA ANTES DE RESPONDER
                # =========================================================
                contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}

                horarios_formatados = []
                for s in sugestoes[:3]:
                    s_str = str(s).strip()
                    horarios_formatados.append(s_str)

                contexto_tmp["estado_fluxo"] = "aguardando_escolha_horario"
                contexto_tmp["modo_escolha_horario"] = True
                contexto_tmp["horarios_sugeridos"] = horarios_formatados
                contexto_tmp["alternativa_profissional"] = alternativas
                contexto_tmp["ultima_opcao_profissionais"] = [prof] + alternativas

                contexto_tmp["profissional_escolhido"] = prof
                contexto_tmp["servico"] = servico
                contexto_tmp["data_hora"] = data_hora
                contexto_tmp["ultima_acao"] = "criar_evento"

                contexto_tmp["aguardando_confirmacao_agendamento"] = False
                contexto_tmp.pop("dados_confirmacao_agendamento", None)

                draft_tmp = contexto_tmp.get("draft_agendamento") or {}
                draft_tmp["profissional"] = prof
                draft_tmp["servico"] = servico
                draft_tmp["data_hora"] = data_hora
                draft_tmp["modo_prechecagem"] = True
                contexto_tmp["draft_agendamento"] = draft_tmp

                await salvar_contexto_temporario(user_id, contexto_tmp, tenant_id=tenant_id)

                print(
                    f"🚨 [CTX SALVO PELO GPT_EXECUTOR] "
                    f"estado_fluxo={contexto_tmp.get('estado_fluxo')} | "
                    f"modo_escolha_horario={contexto_tmp.get('modo_escolha_horario')} | "
                    f"horarios_sugeridos={contexto_tmp.get('horarios_sugeridos')} | "
                    f"data_hora={contexto_tmp.get('data_hora')} | "
                    f"draft={contexto_tmp.get('draft_agendamento')}",
                    flush=True
                )

                alternativas_txt = ""
                if alternativas:
                    alternativas_txt = (
                        f"\n\n💡 Se você quiser manter *{hora}*, estas profissionais fazem *{servico}* "
                        f"e estão disponíveis: *{', '.join(alternativas)}*."
                    )

                mensagem = (
                    f"⛔ A *{prof}* já tem atendimento às *{hora}* nesse dia.\n\n"
                    f"✅ Estes horários estão livres com a *{prof}* no mesmo dia:\n"
                    f"{(sugestoes_formatadas or 'Sem sugestões disponíveis.')}"
                    f"{alternativas_txt}\n\n"
                    f"Deseja escolher outro horário com essa profissional ou prefere uma das alternativas?"
                )

                # [P0.3] Retornar dict
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(mensagem, parse_mode="Markdown")
                    already_sent = True

                return resultado_acao(
                    ok=True,
                    acao=acao,
                    resposta=mensagem,
                    resultado={
                        "motivo": "conflito_detectado",
                        "horarios_sugeridos": horarios_formatados,
                        "alternativas": alternativas
                    },
                    already_sent=already_sent
                )

            # ✅ SEM CONFLITO → SALVA CONTEXTO + CONFIRMAÇÃO
            contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=id_dono) or {}

            contexto_tmp["estado_fluxo"] = "agendando"
            contexto_tmp["draft_agendamento"] = {
                "profissional": prof,
                "servico": servico,
                "data_hora": data_hora,
                "modo_prechecagem": True,
            }
            contexto_tmp["aguardando_confirmacao_agendamento"] = True
            contexto_tmp["dados_confirmacao_agendamento"] = {
                "origem": "confirmacao_pendente",
                "profissional": prof,
                "servico": servico,
                "data_hora": data_hora,
                "duracao": duracao,
                "descricao": f"{servico.capitalize()} com {prof}",
            }
            contexto_tmp["profissional_escolhido"] = prof
            contexto_tmp["servico"] = servico
            contexto_tmp["data_hora"] = data_hora
            contexto_tmp["ultima_opcao_profissionais"] = [prof]
            contexto_tmp["ultima_acao"] = "criar_evento"

            actor_id = identidade.actor_id if identidade else f"telegram:{user_id}"
            await salvar_contexto_temporario_v2(id_dono, actor_id, contexto_tmp)

            try:
                data_fmt = datetime.fromisoformat(data_hora).strftime("%d/%m às %H:%M")
            except Exception:
                data_fmt = data_hora

            # [P0.3] Separar execução de transporte — sempre retornar ResultadoAcao com resposta
            mensagem = (
                f"✨ *{servico.capitalize()} com {prof}*\n"
                f"📆 {data_fmt}\n\n"
                f"Posso confirmar?"
            )

            already_sent = False
            if update and update.message:
                await update.message.reply_text(mensagem, parse_mode="Markdown")
                already_sent = True
            else:
                # [P0.3] WhatsApp: resposta será entregue pelo adapter — não enviar aqui
                print(f"[P0.3] Confirmação de agendamento preparada — resposta no dict, adapter entrega", flush=True)

            return resultado_acao(
                ok=True,
                acao=acao,
                resposta=mensagem,
                resultado={"servico": servico, "profissional": prof, "data_hora": data_hora},
                already_sent=already_sent
            )

        elif acao == "criar_evento":
            # ✅ GATE: valida profissional vs serviço antes de agendar
            # P0A: Reutilizar user_id já resolvido no início da função
            # Se identidade existe, user_id já foi obtido de identidade.user_id (linha 293)
            # Não chamar _obter_user_id(None, None) que quebra com context=None
            if not user_id:
                # Fallback: tentar extrair de dados se ainda não temos
                user_id = (dados or {}).get("user_id")

            # [TESTE_SURI] DADOS PARA EXECUTAR_ACAO_GPT
            print(f"[TESTE_SURI] DADOS_EXECUTAR_ACAO: user_id={repr(user_id)}", flush=True)
            print(f"[TESTE_SURI] DADOS_EXECUTAR_ACAO: acao={repr(acao)}", flush=True)
            print(f"[TESTE_SURI] DADOS_EXECUTAR_ACAO: dados_keys={list((dados or {}).keys())}", flush=True)
            if "cliente_nome" in (dados or {}):
                print(f"[TESTE_SURI] DADOS_EXECUTAR_ACAO: cliente_nome={repr(dados.get('cliente_nome'))}", flush=True)
            if "profissional" in (dados or {}):
                print(f"[TESTE_SURI] DADOS_EXECUTAR_ACAO: profissional={repr(dados.get('profissional'))}", flush=True)

            if not user_id:
                # [P0.3] Retornar dict de erro
                msg = "⚠️ Não consegui identificar o usuário para criar o evento."
                already_sent = False
                if update and hasattr(update, "message"):
                    await update.message.reply_text(msg)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg,
                    erro="user_id_not_identified",
                    already_sent=already_sent
                )

            dono_id = await obter_id_dono(user_id)
            # [WhatsApp] Se update=None e dono_id é None, usar tenant_id de dados_exec
            if not dono_id:
                dono_id = (dados or {}).get("tenant_id")

            # serviço: preferir contexto; se não existir, tenta inferir do texto/descrição
            contexto_tmp = await carregar_contexto_temporario(user_id, tenant_id=dono_id) or {}
            servico_ctx = _extrair_servico_do_contexto(contexto_tmp)

            # tentativa extra: se não achou no contexto, tenta tirar da descrição "escova com Bruna"
            if not servico_ctx:
                desc = (dados or {}).get("descricao") or ""
                desc_norm = _normalizar_nome(desc)
                # regra simples: pega primeira palavra (melhor é você salvar sempre o servico no contexto)
                if desc_norm:
                    servico_ctx = desc_norm.split(" ")[0].strip()

            prof_escolhido = (dados or {}).get("profissional") or ""
            prof_escolhido_norm = _normalizar_nome(prof_escolhido)

            if servico_ctx:
                validos = await _listar_profissionais_validos_para_servico(dono_id, servico_ctx)

                # se existe conjunto de válidos e a escolha não pertence, bloqueia
                if validos:
                    validos_norm = {_normalizar_nome(x) for x in validos}
                    if prof_escolhido_norm and prof_escolhido_norm not in validos_norm:
                        # [P0.3] Profissional inválido — retornar dict
                        lista_txt = ", ".join(validos)
                        msg = (
                            f"Para *{servico_ctx}*, eu tenho: {lista_txt}.\n"
                            f"Quem você prefere?"
                        )
                        already_sent = False
                        if update and hasattr(update, "message"):
                            await update.message.reply_text(msg, parse_mode="Markdown")
                            already_sent = True
                        return resultado_acao(
                            ok=True,
                            acao=acao,
                            resposta=msg,
                            resultado={"motivo": "profissional_invalido", "validos": validos},
                            already_sent=already_sent,
                            handled=True
                        )

            # ✅ passou no gate → executa normal
            print(
                f"[DIAG EXECUTOR] "
                f"update={update is None and 'None' or 'presente'} | "
                f"context={context is not None and 'presente' or 'None'} | "
                f"acao={acao!r} | "
                f"dados_keys={list((dados or {}).keys())} | "
                f"profissional={dados.get('profissional')!r} | "
                f"servico={dados.get('servico')!r} | "
                f"data_hora={dados.get('data_hora')!r} | "
                f"tenant_id={dados.get('tenant_id')!r}",
                flush=True
            )
            await add_evento_por_gpt(update, context, dados)
            return True  # ✅ sempre "handled": add_evento_por_gpt já responde (sucesso OU conflito)

        elif acao == "remover_tarefa":
            descricao = dados.get("descricao")
            if descricao:
                await remover_tarefa_por_descricao(update, context, descricao)
            return True

        elif acao == "cancelar_evento":
            # P0.1A: Cancelamento com confirmação obrigatória
            user_id = _obter_user_id(update, context)
            if not user_id:
                # [P0.3] Retornar dict
                msg = "⚠️ Não consegui identificar quem está solicitando o cancelamento."
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg,
                    erro="user_id_not_identified",
                    already_sent=already_sent
                )

            termo = (dados or {}).get("termo") or getattr(getattr(update, "message", None), "text", "") or ""

            # Usar nova função que NÃO cancela direto
            ok, msg, candidatos = await cancelar_evento_por_texto(user_id, termo)

            if not candidatos:
                # [P0.3] Nenhum encontrado — retornar dict
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg,
                    erro="no_events_found",
                    already_sent=already_sent
                )

            # Limpar estado anterior
            if context:
                context.user_data.pop("cancelamento_pendente", None)

            # 🔥 P0: Sanitizar cancelamento_pendente — APENAS dados serializáveis
            cancelamento_sanitizado = sanitizar_cancelamento_pendente(candidatos, user_id)

            if not cancelamento_sanitizado:
                # [P0.3] Erro de serialização — retornar dict
                msg_erro = "Não consegui preparar o cancelamento. Pode tentar novamente?"
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg_erro)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg_erro,
                    erro="serialization_error",
                    already_sent=already_sent
                )

            # Salvar contexto sanitizado
            if context:
                context.user_data["cancelamento_pendente"] = cancelamento_sanitizado
                context.user_data["estado_fluxo"] = "aguardando_confirmacao_cancelamento"

            # 🔥 P0: Limpar lixo de agendamento antes de entrar em cancelamento
            ctx = await carregar_contexto_temporario(user_id, tenant_id=tenant_id) or {}
            ctx.pop("motivo_estado", None)
            ctx.pop("profissional_rejeitado", None)
            ctx.pop("profissionais_validos", None)
            ctx.pop("aguardando_confirmacao_agendamento", None)
            ctx.pop("dados_confirmacao_agendamento", None)

            # Salvar em MemoriaTemporaria (persistência)
            ctx["cancelamento_pendente"] = cancelamento_sanitizado
            ctx["estado_fluxo"] = "aguardando_confirmacao_cancelamento"
            await salvar_contexto_temporario(user_id, ctx, tenant_id=tenant_id)

            # [P0.3] Retornar dict em vez de reply_text
            already_sent = False
            if update and update.message:
                await update.message.reply_text(msg)
                already_sent = True
            return resultado_acao(
                ok=True,
                acao=acao,
                resposta=msg,
                resultado={"cancelamento_pendente": cancelamento_sanitizado},
                already_sent=already_sent
            )

        elif acao == "enviar_email":
            destinatario = dados.get("destinatario")
            assunto = dados.get("assunto")
            corpo = dados.get("corpo")
            # ... mantenha seu código existente daqui pra baixo ...
            return True

        # ... mantenha seus outros elif acao == ... que existem no seu arquivo ...

        elif acao == "buscar_eventos_do_dia":
            user_id = _obter_user_id(update, context)
            if not user_id:
                # [P0.3] Retornar dict
                msg = "⚠️ Não consegui identificar o usuário para consultar a agenda."
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg)
                    already_sent = True
                return resultado_acao(
                    ok=False,
                    acao=acao,
                    resposta=msg,
                    erro="user_id_not_identified",
                    already_sent=already_sent
                )

            dias = int((dados or {}).get("dias", 0))
            eventos = await buscar_eventos_por_intervalo(user_id, dias=dias) or []

            if not eventos:
                prof = (dados or {}).get("profissional") or (dados or {}).get("profissional_escolhido")
                data_hora = (dados or {}).get("data_hora")

                def _fmt(dt_iso: str) -> str:
                    from datetime import datetime
                    try:
                        return datetime.fromisoformat(dt_iso).strftime("%d/%m/%Y às %H:%M")
                    except Exception:
                        return str(dt_iso)

                when = _fmt(data_hora) if data_hora else "nesse horário"

                if prof:
                    msg = f"✅ A agenda da *{prof}* está livre *{when}*. Quer que eu agende?"
                else:
                    msg = f"✅ Está livre em *{when}*. Quer que eu agende?"

                # [P0.3] Retornar dict
                already_sent = False
                if update and update.message:
                    await update.message.reply_text(msg, parse_mode="Markdown")
                    already_sent = True

                return resultado_acao(
                    ok=True,
                    acao=acao,
                    resposta=msg,
                    resultado={"eventos": [], "motivo": "sem_eventos"},
                    already_sent=already_sent
                )

            # Se você já tem formatador padronizado:
            try:
                texto = formatar_eventos_telegram(eventos)
            except Exception:
                # fallback simples
                linhas = []
                for ev in eventos:
                    linhas.append(
                        f"• {ev.get('descricao','(Sem título)')} — {ev.get('data','')} {ev.get('hora_inicio','')}-{ev.get('hora_fim','')}"
                    )
                texto = "📅 Eventos do dia:\n\n" + "\n".join(linhas)

            # [P0.3] Retornar dict
            already_sent = False
            if update and update.message:
                await update.message.reply_text(texto, parse_mode="Markdown")
                already_sent = True

            return resultado_acao(
                ok=True,
                acao=acao,
                resposta=texto,
                resultado={"eventos": eventos, "count": len(eventos)},
                already_sent=already_sent
            )

        # [P0.3] Ação não reconhecida — retornar dict em vez de False
        return resultado_acao(
            ok=False,
            acao=acao,
            resposta=None,
            erro="acao_nao_reconhecida",
            already_sent=False
        )

    except Exception as e:
        import traceback
        print("[ERRO] Detalhado em executar_acao_gpt:")
        traceback.print_exc()
        try:
            if getattr(update, "message", None):
                await update.message.reply_text(f"[ERRO] Interno: {e}")
        except Exception:
            pass
        return {
            "ok": False,
            "erro": str(e),
            "tipo_erro": "exception_executar_acao_gpt",
            "acao": acao,
            "resultado": None
        }
