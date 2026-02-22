from telegram import Update
from telegram.ext import ContextTypes

from datetime import datetime

# Handlers importados
from handlers.task_handler import add_task_por_gpt, gerar_texto_tarefas, remover_tarefa_por_descricao
from handlers.event_handler import add_evento_por_gpt
from handlers.email_handler import listar_emails_prioritarios, ler_emails_command
from handlers.followup_handler import configurar_avisos
from handlers.report_handler import relatorio_diario, relatorio_semanal, enviar_relatorio_email
from handlers.perfil_handler import meu_plano

from utils.plan_utils import verificar_pagamento, verificar_acesso_modulo
from utils.tts_utils import responder_em_audio
from utils.context_manager import carregar_contexto_temporario  # ✅ necessário para ler MemoriaTemporaria

from services.firebase_service_async import buscar_subcolecao, obter_id_dono  # ✅ obter_id_dono para pegar dono
from services.email_service import enviar_email_google
from services.event_service_async import (
    cancelar_evento_por_texto,
    buscar_eventos_por_termo_avancado,
    cancelar_evento,
)
from utils.formatters import formatar_eventos_telegram

# ✅ Executor de ações baseado no JSON retornado pelo GPT
from services.event_service_async import buscar_eventos_por_intervalo  # Importação necessária


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


async def executar_acao_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, acao: str, dados: dict):
    try:
        print(f"🪵 Ação recebida: {repr(acao)}")  # DEBUG extra

        if not acao or acao.strip() == "":
            return False

        print(f"🔁 Ação recebida: {acao}")
        print(f"📦 Dados: {dados}")

        if acao == "criar_tarefa":
            await add_task_por_gpt(update, context, dados)
            return True

        elif acao == "buscar_tarefas_do_usuario":
            user_id = str(update.message.from_user.id)
            texto_tarefas = await gerar_texto_tarefas(user_id)
            resposta = dados.get("resposta") or "📋 Aqui está sua lista de tarefas:\n"
            await update.message.reply_text(f"{resposta}\n\n{texto_tarefas}", parse_mode="Markdown")
            return True

        elif acao == "criar_evento":
            # ✅ GATE: valida profissional vs serviço antes de agendar
            user_id = _obter_user_id(update, context)
            if not user_id:
                await update.message.reply_text("⚠️ Não consegui identificar o usuário para criar o evento.")
                return True

            dono_id = await obter_id_dono(user_id)

            # serviço: preferir contexto; se não existir, tenta inferir do texto/descrição
            contexto_tmp = await carregar_contexto_temporario(user_id) or {}
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
                        # ❌ não agenda
                        lista_txt = ", ".join(validos)
                        await update.message.reply_text(
                            f"Para *{servico_ctx}*, eu tenho: {lista_txt}.\n"
                            f"Quem você prefere?",
                            parse_mode="Markdown"
                        )
                        return True  # handled

            # ✅ passou no gate → executa normal
            await add_evento_por_gpt(update, context, dados)
            return True  # ✅ sempre "handled": add_evento_por_gpt já responde (sucesso OU conflito)

        elif acao == "remover_tarefa":
            descricao = dados.get("descricao")
            if descricao:
                await remover_tarefa_por_descricao(update, context, descricao)
            return True

        elif acao == "cancelar_evento":
            user_id = _obter_user_id(update, context)
            if not user_id:
                await update.message.reply_text("⚠️ Não consegui identificar quem está solicitando o cancelamento.")
                return True

            termo = (dados or {}).get("termo") or getattr(getattr(update, "message", None), "text", "") or ""

            try:
                candidatos = await buscar_eventos_por_termo_avancado(user_id, termo)
            except Exception as e:
                candidatos = []
                print(f"buscar_eventos_por_termo_avancado falhou: {e}")

            if not candidatos:
                await update.message.reply_text("❌ Não encontrei nenhum evento correspondente ao que você quer cancelar.")
                return True

            context.user_data.pop("cancelamento_pendente", None)

            if len(candidatos) == 1:
                eid, ev = candidatos[0]
                ok = await cancelar_evento(user_id, eid)
                if ok:
                    await update.message.reply_text(
                        f"✅ Cancelei: {ev.get('descricao','Evento')} em {ev.get('data','')} às  {ev.get('hora_inicio','')}."
                    )
                else:
                    await update.message.reply_text("❌ Tive um problema ao cancelar. Pode tentar novamente?")
                return True

            linhas = []
            for i, (eid, ev) in enumerate(candidatos, start=1):
                linhas.append(
                    f"{i}) {ev.get('descricao','(Sem título)')} — {ev.get('data','')} às {ev.get('hora_inicio','')} "
                    f"(prof: {ev.get('profissional','-')})"
                )

            txt = (
                "Encontrei mais de um. Qual você deseja cancelar?\n\n"
                + "\n".join(linhas)
                + "\n\nResponda com o número da opção."
            )

            context.user_data["cancelamento_pendente"] = {
                "user_id": user_id,
                "candidatos": [eid for eid, _ in candidatos],
                "criado_em": datetime.now().isoformat()
            }
            await update.message.reply_text(txt)
            return True

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
                await update.message.reply_text("⚠️ Não consegui identificar o usuário para consultar a agenda.")
                return True

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
                    await update.message.reply_text(
                        f"✅ A agenda da *{prof}* está livre em *{when}*. Quer que eu agende?",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Está livre em *{when}*. Quer que eu agende?",
                        parse_mode="Markdown"
                    )

                return True

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

            await update.message.reply_text(texto, parse_mode="Markdown")
            return True

        return False

    except Exception as e:
        print(f"❌ Erro em executar_acao_gpt: {e}")
        try:
            if getattr(update, "message", None):
                await update.message.reply_text("❌ Ocorreu um erro ao executar a ação.")
        except Exception:
            pass
        return True
