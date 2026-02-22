# handlers/event_handler.py 

import logging
import dateparser
import re
import io
import unidecode  # no topo, junto dos imports
from openpyxl import Workbook
from telegram import InputFile
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from utils.tts_utils import responder_em_audio
from utils.formatters import formatar_horario_atual, gerar_sugestoes_de_horario, adaptar_genero
from services.excel_service import gerar_excel_agenda
from services.notificacao_service import criar_notificacao_agendada
from services.profissional_service import obter_profissional_para_evento, buscar_profissionais_por_servico, buscar_profissionais_disponiveis_no_horario
from utils.intencao_utils import identificar_intencao, deve_ativar_fluxo_manual
from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario

from services.firebase_service_async import (
    salvar_cliente,
    buscar_cliente,
    buscar_dados,
    salvar_dado_em_path,
    buscar_subcolecao,
    salvar_dados,
    atualizar_dado_em_path,
    buscar_dado_em_path,
    obter_id_dono,
)
from services.event_service_async import salvar_evento, buscar_eventos_por_intervalo, cancelar_evento_por_texto
from utils.plan_utils import verificar_acesso_modulo, verificar_pagamento 

logger = logging.getLogger(__name__)

def _precisa_profissional(contexto: dict, descricao: str) -> bool:
    """
    Só exige 'profissional' quando for recepção de salão (atendimento_cliente).
    Reuniões/agenda pessoal não precisam.
    """
    contexto = contexto or {}
    usuario = (contexto.get("usuario") or {})
    modo_uso = contexto.get("modo_uso") or usuario.get("modo_uso") or "interno"
    tipo_negocio = (contexto.get("tipoNegocio") or contexto.get("tipo_negocio") or "")
    desc = unidecode.unidecode((descricao or "").lower())

    eh_reuniao = "reuni" in desc  # pega 'reunião'/'reuniao'
    return (modo_uso == "atendimento_cliente" and "sala" in unidecode.unidecode(tipo_negocio.lower()) and not eh_reuniao)

async def add_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    if len(context.args) < 4:
        await update.message.reply_text(
            "⚠️ Uso correto: /agenda <Descrição> <AAAA-MM-DD> <HH:MM início> <HH:MM fim>\n"
            "Exemplo: /agenda Reunião 2025-03-25 14:00 15:00"
        )
        return

    descricao = context.args[0]
    data = context.args[1]
    hora_inicio = context.args[2]
    hora_fim = context.args[3]
    user_id = str(update.message.from_user.id)

    try:
        inicio = datetime.fromisoformat(f"{data}T{hora_inicio}")
        fim = datetime.fromisoformat(f"{data}T{hora_fim}")
        duracao = fim - inicio
        duracao_minutos = int(duracao.total_seconds() / 60)
    except Exception:
        await update.message.reply_text("⚠️ Data ou hora em formato inválido. Use o formato 2025-03-25 14:00.")
        return

    # 🔍 Buscar eventos do dia
    eventos_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=inicio.date())

    # 🔄 Verificar conflitos com base nos horários
    conflitos = []
    for ev in eventos_dia:
        try:
            ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
            ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
        except Exception:
            # fallback: ignora eventos mal formatados
            continue

        if inicio < ev_fim and fim > ev_inicio:
            conflitos.append((ev_inicio, ev_fim))

    if conflitos:
        sugestoes = []
        atual = datetime.combine(inicio.date(), time(8, 0))
        limite = datetime.combine(inicio.date(), time(18, 0))

        while atual + duracao <= limite:
            livre = all(not (atual < f and atual + duracao > i) for i, f in conflitos)
            if livre:
                sugestoes.append(f"{atual.strftime('%H:%M')} - {(atual + duracao).strftime('%H:%M')}")
                if len(sugestoes) >= 3:
                    break
            atual += timedelta(minutes=15)

        resposta = "⚠️ Já existe um evento nesse horário.\n"
        resposta += "\n".join(f"🔄 Alternativa: {s}" for s in sugestoes) if sugestoes else "❌ Nenhum horário alternativo disponível."
        await update.message.reply_text(resposta)
        return

    # ✅ Salvar evento no Firebase
    evento = {
        "descricao": descricao,
        "data": data,
        "hora_inicio": hora_inicio,
        "hora_fim": hora_fim,
        "duracao": duracao_minutos,
        "confirmado": False,
        "link": ""
    }

    print("📦 Salvando evento com os dados:", evento)
    sucesso = await salvar_evento(user_id, evento)
    if sucesso:
        await update.message.reply_text(
            f"📅 Evento criado com sucesso!\n🗓️ {data} ⏰ {hora_inicio} às {hora_fim}",
            parse_mode="Markdown"
        )

        from services.notificacao_service import criar_notificacao_agendada

        await criar_notificacao_agendada(
            user_id=user_id,
            descricao=descricao,
            data=data,
            hora_inicio=hora_inicio,
            canal="telegram",
            minutos_antes=30,
            destinatario_user_id=user_id,  # dono recebe o aviso
            alvo_evento={"data": data, "hora_inicio": hora_inicio}
        )
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao tentar salvar o evento.")

async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    hoje = datetime.now().date()

    eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=hoje)

    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado para hoje.")
        return

    resposta = "📅 Eventos de hoje:\n" + "\n".join(f"- {ev}" for ev in eventos)
    await update.message.reply_text(resposta)

async def confirmar_reuniao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    descricao = ' '.join(context.args)
    if not descricao:
        await update.message.reply_text("⚠️ Informe a descrição do evento para confirmar.")
        return

    user_id = str(update.message.from_user.id)
    dono_id = await obter_id_dono(user_id)   # 👈 garante que busca no dono

    eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos")

    for event_id, evento in eventos.items():
        texto_evento = f"{evento.get('descricao', '')} {evento.get('data', '')} {evento.get('hora_inicio', '')} {evento.get('hora_fim', '')}".lower()
        if descricao.lower() in texto_evento:
            evento["confirmado"] = True
            await salvar_dado_em_path(f"Clientes/{dono_id}/Eventos/{event_id}", evento)
            await responder_em_audio(update, context, f"✅ Reunião confirmada: {evento['descricao']}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")

async def confirmar_presenca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    descricao = ' '.join(context.args).lower()
    if not descricao:
        await update.message.reply_text("⚠️ Informe o nome do evento para confirmar presença.")
        return

    user_id = str(update.message.from_user.id)
    dono_id = await obter_id_dono(user_id)  # 👈 aqui

    eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos")

    for event_id, evento in eventos.items():
        if descricao in evento.get("descricao", "").lower():
            evento["confirmado"] = True
            await salvar_dado_em_path(f"Clientes/{dono_id}/Eventos/{event_id}", evento)
            await responder_em_audio(update, context, f"✅ Presença confirmada para: {evento['descricao']}")
            return

    await update.message.reply_text("❌ Evento não encontrado.")


async def debug_eventos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)
    dono_id = await obter_id_dono(user_id)  # 👈 aqui

    event_id = "evento_debug"
    evento_data = {
        "descricao": "Evento de Teste via Bot",
        "data": "2025-03-30",
        "hora_inicio": "12:00",
        "hora_fim": "13:00",
        "confirmado": False,
        "link": "https://exemplo.com/evento-debug"
    }

    if await salvar_dado_em_path(f"Clientes/{dono_id}/Eventos/{event_id}", evento_data):
        await responder_em_audio(update, context, "✅ Evento de teste salvo com sucesso.")
    else:
        await update.message.reply_text("❌ Erro ao salvar evento de teste.")

    eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos")
    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado.")
        return

    resposta = "📂 Eventos salvos:\n"
    for eid, ev in eventos.items():
        resposta += f"\n📌 {eid}: {ev.get('descricao')} ({ev.get('data')} {ev.get('hora_inicio')} - {ev.get('hora_fim')})"

    await responder_em_audio(update, context, resposta)

async def add_evento_por_voz(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context): return

    if context.chat_data.get("evento_via_gpt"):
        return  # evitar duplicação

    try:
        texto = texto.lower().replace("marcar reunião", "").replace("agendar reunião", "").replace("às", "as").strip()
        data_hora = dateparser.parse(texto, languages=["pt"])
        if not data_hora:
            await update.message.reply_text("❌ Não entendi a data e hora. Pode tentar de outra forma?")
            return

        user_id = str(update.message.from_user.id)
        start_time = data_hora
        end_time = start_time + timedelta(hours=1)
        duracao = 60
        titulo = "Reunião agendada por voz"

        # 🧠 Recupera contexto e profissional alternativo
        contexto = await carregar_contexto_temporario(user_id) or {}
        profissional = contexto.get("profissional")  # vem do contexto anterior
        alternativa = contexto.get("alternativa_profissional")

        # 🔍 Só exige profissional se o tipo de evento precisar
        if _precisa_profissional(contexto, titulo) and not profissional:
            await update.message.reply_text(
                "❌ Não consegui identificar a profissional. Pode repetir dizendo quem irá atender?"
            )
            return

        # 🔍 Verifica conflitos
        eventos = await buscar_eventos_por_intervalo(user_id, dia_especifico=start_time.date())
        ocupados = []

        for ev in eventos:
            try:
                ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
                ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
                ocupados.append((ev_inicio, ev_fim))
            except:
                continue

        print("🧪 TESTE - checando conflito...")
        conflito = any(not (end_time <= inicio or start_time >= fim) for inicio, fim in ocupados if fim > inicio)

        if conflito:
            sugestoes = gerar_sugestoes_de_horario(
                start_time,
                ocupados,
                duracao_evento_minutos=duracao_minutos,
                max_sugestoes=3
            )
            sugestoes_formatadas = "\n".join([f"🔄 {s}" for s in sugestoes]) if sugestoes else "❌ Nenhum horário alternativo disponível."

            alternativa = contexto.get("alternativa_profissional")

            # ✅ Persistir agendamento pendente (data ORIGINAL) para não perder o dia
            #    (isso é o que permite o usuário mandar só "15:20" depois)
            try:
                servico_ctx = None

                # tenta derivar do texto "descricao" (ex: "escova com Joana" -> "escova")
                if isinstance(descricao, str) and descricao.strip():
                    desc_lower = descricao.strip().lower()
                    servico_ctx = desc_lower.split(" com ")[0].strip()

                # fallback: se já existe algo no contexto
                servico_final = servico_ctx or contexto.get("servico")

                # profissional: salva o atual ou preserva o que já existe
                prof_final = profissional or contexto.get("profissional_escolhido") or contexto.get("profissional")

                contexto["ultima_acao"] = "criar_evento"
                contexto["aguardando_horario"] = True
                contexto["data_hora"] = start_time.replace(second=0, microsecond=0).isoformat()

                if prof_final:
                    contexto["profissional_escolhido"] = prof_final

                contexto["duracao"] = duracao_minutos
                contexto["sugestoes"] = sugestoes
                contexto["alternativa_profissional"] = alternativa

                if servico_final:
                    contexto["servico"] = servico_final

                # ✅ SEMPRE salvar dados_anteriores (não condicionar ao serviço)
                contexto["dados_anteriores"] = {
                    "profissional": prof_final,
                    "servico": servico_final,
                    "data_hora": start_time.replace(second=0, microsecond=0).isoformat(),
                    "duracao": duracao_minutos,
                }

                await salvar_contexto_temporario(user_id, contexto)
                print("💾 Contexto pendente salvo (conflito).")

            except Exception as e:
                print(f"⚠️ Falha ao salvar contexto pendente no conflito: {e}")

            mensagem_sugestao = (
                f"⛔ A *{profissional}* já tem atendimento às *{start_time.strftime('%H:%M')}* nesse dia."
                f"\n\n✅ Estes horários estão livres com a *{profissional}* no mesmo dia:\n{sugestoes_formatadas}"
                f"{alternativa_txt}"
                "\n\nDeseja escolher outro horário com essa profissional ou prefere agendar com a alternativa?"
            )

            print(f"[DEBUG mensagem enviada]: {mensagem_sugestao}")
            await update.message.reply_text(mensagem_sugestao, parse_mode="Markdown")
            return False  # ⛔️ Não agenda nesse momento

        # ✅ Salva o evento no Firebase
        evento_data = {
            "descricao": titulo,
            "data": start_time.strftime("%Y-%m-%d"),
            "hora_inicio": start_time.strftime("%H:%M"),
            "hora_fim": end_time.strftime("%H:%M"),
            "duracao": duracao,
            "confirmado": False,
            "link": "",
        }
        if profissional:
            evento_data["profissional"] = profissional  # ✅ só se tiver

        print(f"👤 Profissional detectado: {profissional}") 
        sucesso = await salvar_evento(user_id, evento_data)
        if sucesso:
            msg = f"✅ Reunião marcada para {start_time.strftime('%d/%m/%Y')} às {start_time.strftime('%H:%M')}."
            await responder_em_audio(update, context, msg)

            # 🔔 Lembretes para o DONO (quem executou o comando / a conta que está usando o bot)
            from services.notificacao_service import criar_notificacao_agendada
            try:
                # 30 min antes
                await criar_notificacao_agendada(
                    user_id=user_id,
                    descricao=titulo,
                    data=start_time.strftime("%Y-%m-%d"),
                    hora_inicio=start_time.strftime("%H:%M"),
                    canal="telegram",
                    minutos_antes=30,
                    destinatario_user_id=user_id,  # dono recebe
                    alvo_evento={"data": start_time.strftime("%Y-%m-%d"), "hora_inicio": start_time.strftime("%H:%M")}
                )
                
            except Exception as e:
                print(f"⚠️ Falha ao agendar lembretes (voz): {e}")
        else:
            await update.message.reply_text("❌ Não foi possível salvar o evento.")

    except Exception as e:
        print(f"❌ Erro ao agendar por voz: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao tentar agendar a reunião.")

    finally:
        context.chat_data.pop("evento_via_gpt", None)

async def cancelar_evento_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    termo = " ".join(context.args) if context.args else ""
    if not termo:
        await update.message.reply_text(
            "Uso: /cancelar <parte do título/data/hora>\nEx.: /cancelar reunião 15:00 ou /cancelar 2025-10-12"
        )
        return

    ok, msg = await cancelar_evento_por_texto(user_id, termo)

    # ✅ Se vieram múltiplos candidatos, salva estado para o atalho numérico do bot.py finalizar
    if (not ok) and candidatos:
        context.user_data["cancelamento_pendente"] = {
            "user_id": str(user_id),
            "candidatos": [(eid, ev) for (eid, ev) in candidatos],  # lista de tuples
        }
    await update.message.reply_text(msg)
    return

# ✅ definição de duração de eventos
async def detectar_e_definir_duracao(update: Update, context: ContextTypes.DEFAULT_TYPE, mensagem: str):
    match = re.search(r'(\d{1,3})\s*(min|minuto|minutos)', mensagem.lower())

    if match:
        minutos = int(match.group(1))

        if 15 <= minutos <= 180:
            user_id = str(update.message.from_user.id)
            dono_id = await obter_id_dono(user_id)  # 👈 salva na config do dono
            await atualizar_dado_em_path(f"Clientes/{dono_id}/configuracoes", {"duracao_padrao_evento": minutos})

            await update.message.reply_text(f"✅ Duração dos eventos ajustada para {minutos} minutos.")
            return True

        else:
            await update.message.reply_text("⚠️ Por favor, escolha uma duração entre 15 e 180 minutos.")
            return True

    return False

# ✅ Criar evento via GPT com verificação de conflito
async def add_evento_por_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE, dados: dict):
    print("⚙️ Executando add_evento_por_gpt")
    if not await verificar_pagamento(update, context): return False
    if not await verificar_acesso_modulo(update, context, "secretaria"): return False

    if context.chat_data.get("evento_via_gpt"):
        return False  # evitar duplicação
    context.chat_data["evento_via_gpt"] = True

    try:
        descricao = dados.get("descricao", "Evento sem título")
        profissional = dados.get("profissional")
        data_hora_str = dados.get("data_hora")  # ISO string
        duracao_minutos = dados.get("duracao", 60)
        user_id = str(update.message.from_user.id)

        # ✅ Carrega contexto UMA vez no início (evita UnboundLocalError)
        contexto = await carregar_contexto_temporario(user_id) or {}

        # 🚫 BLOQUEIO: impedir agendamento sem confirmação explícita
        texto_usuario = (
            (getattr(getattr(update, "message", None), "text", None) or dados.get("texto_usuario") or "")
            .lower()
            .strip()
        )

        def eh_confirmacao(txt: str) -> bool:
            gatilhos = [
                "confirmar", "confirma", "pode agendar", "pode marcar",
                "agende", "marque", "fechar", "ok", "confirmado"
            ]
            return any(g in txt for g in gatilhos)

        # 🧠 Se não há confirmação explícita, NÃO agenda
        # ✅ CONTROLE DE CONFIRMAÇÃO (modo híbrido)
        origem = (dados or {}).get("origem")

        if origem == "auto":
            print("⚙️ Modo automático: pulando confirmação", flush=True)
        else:
            if not eh_confirmacao(texto_usuario):
                await update.message.reply_text(
                f"📅 Consulta de disponibilidade:\n"
                f"{descricao} em {data_hora_str}\n\n"
                f"👉 Deseja confirmar esse agendamento? Responda *confirmar*.",
                parse_mode="Markdown"
            )
            return {"acao": None, "handled": True}

        # 🧠 Trata profissional alternativo (contexto já carregado acima)
        resposta_usuario = (
            (getattr(getattr(update, "message", None), "text", None) or "")
            .lower()
            .strip()
        )

        alternativa = contexto.get("alternativa_profissional")

        if alternativa:
            if alternativa.lower() in resposta_usuario:
                profissional = alternativa.capitalize()
                dados["profissional"] = profissional
                print(f"🔁 Profissional substituído com sucesso: {profissional}")
            else:
                # ❌ Usuário não confirmou a alternativa → limpa
                contexto.pop("alternativa_profissional", None)
                contexto.pop("sugestoes", None)
                await salvar_contexto_temporario(user_id, contexto)
        
        if not profissional:
            # Só tenta descobrir/exigir profissional se realmente precisar
            if _precisa_profissional(contexto, descricao):
                profissional = await obter_profissional_para_evento(user_id, descricao)
                if not profissional:
                    await update.message.reply_text("❌ Não consegui identificar a profissional para esse agendamento. Pode repetir mencionando quem irá atender?")
                    return False
            else:
                profissional = None  # reunião/agenda pessoal não precisa

        if not descricao or not data_hora_str:
            await update.message.reply_text("❌ Dados insuficientes para criar o evento.")
            return False

        try:
            start_time = datetime.fromisoformat(data_hora_str)
        except ValueError:
            await update.message.reply_text("❌ Formato de data/hora inválido.")
            return False

        end_time = start_time + timedelta(minutes=duracao_minutos)

        eventos_do_dia = await buscar_eventos_por_intervalo(user_id, dia_especifico=start_time.date()) or []
        ocupados = []
        for ev in eventos_do_dia:
            # Se houver profissional, filtra por ele; se não, considera todos
            if profissional:
                if ev.get("profissional", "").lower() != profissional.lower():
                    continue
            try:
                ev_inicio = datetime.strptime(f"{ev['data']} {ev['hora_inicio']}", "%Y-%m-%d %H:%M")
                ev_fim = datetime.strptime(f"{ev['data']} {ev['hora_fim']}", "%Y-%m-%d %H:%M")
                ocupados.append((ev_inicio, ev_fim))
            except Exception as e:
                print(f"⚠️ Erro ao processar evento: {e}")
                continue

        # 📌 DEBUG dos horários ocupados e do novo agendamento
        print(f"📌 Novo agendamento solicitado: {start_time} → {end_time}")
        for i, (ini, fim) in enumerate(ocupados):
            print(f"❗ Evento ocupado {i}: {ini} → {fim} | Conflita? {not (end_time <= ini or start_time >= fim)}")

        print("🔍 Entrando no bloco de verificação de conflitos...")
        # Verifica se há conflito real com esse horário
        conflito = any(not (end_time <= inicio or start_time >= fim) for inicio, fim in ocupados if fim > inicio)

        if conflito:
            # ⚠️ Aqui sim faz sentido sugerir horários alternativos com base no horário solicitado
            sugestoes = gerar_sugestoes_de_horario(
                start_time,
                ocupados,
                duracao_evento_minutos=duracao_minutos,
                max_sugestoes=3
            )

            alternativa = contexto.get("alternativa_profissional")
            sugestoes_formatadas = '\n'.join([f"🔄 {s}" for s in sugestoes]) if sugestoes else "❌ Nenhum horário alternativo disponível."

            id_dono = user_id
            try:
                cliente_tmp = await buscar_cliente(user_id) or {}
                id_dono = str(cliente_tmp.get("id_negocio") or cliente_tmp.get("id_dono") or user_id)
            except Exception as e:
                print(f"⚠️ Falha ao obter id_negocio: {e}", flush=True)

            # ✅ Persistir agendamento pendente (data ORIGINAL) para não perder o dia
            try:
                # tenta derivar serviço do texto (ex: "escova com Joana" -> "escova")
                servico_ctx = None
                if isinstance(descricao, str) and descricao.strip():
                    servico_ctx = descricao.strip().lower().split(" com ")[0].strip()

                servico_final = servico_ctx or contexto.get("servico")
                prof_final = profissional or contexto.get("profissional_escolhido")

                contexto["ultima_acao"] = "criar_evento"
                contexto["aguardando_horario"] = True
                contexto["data_hora"] = start_time.replace(second=0, microsecond=0).isoformat()

                if prof_final:
                    contexto["profissional_escolhido"] = prof_final

                # ✅ sempre salvar
                contexto["duracao"] = duracao_minutos
                contexto["sugestoes"] = sugestoes
                contexto["alternativa_profissional"] = alternativa

                if servico_final:
                    contexto["servico"] = servico_final

                # ✅ sempre salvar dados_anteriores (para o gpt_service retomar com "15:20")
                contexto["dados_anteriores"] = {
                    "profissional": prof_final,
                    "servico": servico_final,
                    "data_hora": start_time.replace(second=0, microsecond=0).isoformat(),
                    "duracao": duracao_minutos,
                }

                await salvar_contexto_temporario(user_id, contexto)
                print("💾 Contexto pendente salvo (conflito).")

            except Exception as e:
                print(f"⚠️ Falha ao salvar contexto pendente no conflito: {e}")

            alternativa_txt = (
                f"\n\n💡 Porém, *{alternativa}* está disponível exatamente às *{start_time.strftime('%H:%M')}*."
                if alternativa else ""
            )

            # --- Alternativas no MESMO horário (mesmo serviço) ---
            alternativas_txt = ""
            try:
                # blindagem: se por algum motivo servico_final não existir aqui
                servico_final = servico_final or contexto.get("servico")

                if servico_final:
                    data_ref = start_time.date()
                    hora_ref = start_time.strftime("%H:%M")

                    # quem faz o serviço (no NEGÓCIO/DONO)
                    aptas = await buscar_profissionais_por_servico([servico_final], id_dono)  # dict {nome: dados}

                    # quem está livre no horário (no NEGÓCIO/DONO)
                    livres = await buscar_profissionais_disponiveis_no_horario(
                        user_id=id_dono,
                        data=data_ref,
                        hora=hora_ref,
                        duracao=duracao_minutos
                    )  # dict {nome: dados}

                    # normaliza para interseção robusta
                    def norm_nome(n: str) -> str:
                        return unidecode.unidecode(str(n).strip().lower())

                    aptas_norm = {norm_nome(n): n for n in aptas.keys()}
                    livres_norm = {norm_nome(n): n for n in livres.keys()}
                    prof_ocupada_norm = norm_nome(profissional)

                    # interseção: faz o serviço E está livre, removendo a profissional ocupada
                    nomes_alternativos = []
                    for k in livres_norm.keys():
                        if k == prof_ocupada_norm:
                            continue
                        if k in aptas_norm:
                            nomes_alternativos.append(livres_norm[k])

                    print(
                        f"🧪 alternativas debug | servico={servico_final} | "
                        f"aptas={list(aptas.keys())} | livres={list(livres.keys())} | alts={nomes_alternativos}",
                        flush=True
                    )

                    if nomes_alternativos:
                        alternativas_txt = (
                            f"\n\n💡 Se você quiser manter *{hora_ref}*, estas profissionais fazem *{servico_final}* "
                            f"e estão disponíveis: *{', '.join(nomes_alternativos)}*."
                        )

            except Exception as e:
                print(f"⚠️ Falha ao montar alternativas no mesmo horário: {e}", flush=True)

            mensagem_sugestao = (
                f"⛔ A *{profissional}* já tem atendimento às *{start_time.strftime('%H:%M')}* nesse dia."
                f"\n\n✅ Estes horários estão livres com a *{profissional}* no mesmo dia:\n{sugestoes_formatadas}"
                f"{alternativas_txt or alternativa_txt}"
                "\n\nDeseja escolher outro horário com essa profissional ou prefere uma das alternativas?"
            )

            print(f"[DEBUG mensagem enviada]: {mensagem_sugestao}")
            await update.message.reply_text(mensagem_sugestao, parse_mode="Markdown")
            return False  # ⛔️ Não agenda nesse momento

        evento_data = {
            "descricao": descricao,
            "data": start_time.strftime("%Y-%m-%d"),
            "hora_inicio": start_time.strftime("%H:%M"),
            "hora_fim": end_time.strftime("%H:%M"),
            "duracao": duracao_minutos,
            "confirmado": False,
            "link": "",
        }
        if profissional:
            evento_data["profissional"] = profissional

        print("📦 Disparando salvar_evento com:", evento_data)
        await salvar_evento(user_id, evento_data)
        print("✅ Evento salvo")

        # 🔔 Lembretes (60 e 10 min antes)
        from services.notificacao_service import criar_notificacao_agendada
        try:
            # Decide quem recebe o lembrete:
            # - se veio cliente_user_id (atendimento ao cliente) -> notifica o cliente
            # - senão -> notifica o dono (quem está usando o bot)
            cliente_user_id = dados.get("cliente_user_id") if isinstance(dados, dict) else None
            destinatario = cliente_user_id or user_id

            # 30 min antes
            await criar_notificacao_agendada(
                user_id=user_id,
                descricao=descricao,
                data=start_time.strftime("%Y-%m-%d"),
                hora_inicio=start_time.strftime("%H:%M"),
                canal="telegram",
                minutos_antes=30,
                destinatario_user_id=destinatario,
                alvo_evento={"data": start_time.strftime("%Y-%m-%d"), "hora_inicio": start_time.strftime("%H:%M")}
            )

        except Exception as e:
            print(f"⚠️ Falha ao agendar lembretes do evento: {e}")

        mensagem_confirmacao = (
            f"📝 {descricao.capitalize()}\n"
            f"📅 {start_time.strftime('%d/%m/%Y')} às {start_time.strftime('%H:%M')}"
        )

        if context.user_data.get("origem_email_detectado"):
            mensagem_confirmacao = (
                "📬 Um novo evento foi criado com base em um e-mail importante:\n\n"
                + mensagem_confirmacao
            )
        context.user_data.pop("origem_email_detectado", None)

        try:
            from main import application
            await application.bot.send_message(chat_id=user_id, text=mensagem_confirmacao)
        except Exception as e:
            print(f"❌ Erro ao enviar notificação Telegram: {e}")

        try:
            from utils.whatsapp_utils import enviar_mensagem_whatsapp
            await enviar_mensagem_whatsapp(user_id, mensagem_confirmacao)
        except Exception as e:
            print(f"❌ Erro ao enviar WhatsApp: {e}")

        mensagem_gpt = f"{descricao.capitalize()} marcada com sucesso para {start_time.strftime('%d/%m/%Y')} às {start_time.strftime('%H:%M')}."
        mensagem_gpt_limpa = re.sub(r"[^\w\s,.:áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]", "", mensagem_gpt)

        await responder_em_audio(update, context, mensagem_gpt_limpa)
        await update.message.reply_text(mensagem_gpt)
        await update.message.reply_text("😄 Agendamento concluído! Se precisar de mais alguma coisa, é só me chamar.")

        # 🧼 Limpa o restante do contexto (exceto histórico)
        for chave in ["alternativa_profissional", "sugestoes", "profissional_escolhido", "dados_anteriores", "ultima_acao", "evento_criado", "servico"]:
            contexto.pop(chave, None)
        await salvar_contexto_temporario(user_id, contexto)

        return True

    except Exception as e:
        import traceback
        print(f"❌ Erro inesperado em add_evento_por_gpt: {e}")
        traceback.print_exc()
        await update.message.reply_text("❌ Ocorreu um erro ao tentar criar o evento.")
        return False

    finally:
        context.chat_data.pop("evento_via_gpt", None)

async def enviar_agenda_excel(update: Update, context: ContextTypes.DEFAULT_TYPE, intervalo: str = "hoje"):
    if not await verificar_pagamento(update, context): return
    if not await verificar_acesso_modulo(update, context, "secretaria"): return

    user_id = str(update.message.from_user.id)

    if intervalo == "hoje":
        eventos = await buscar_eventos_por_intervalo(user_id, dias=0)
    elif intervalo == "amanha":
        eventos = await buscar_eventos_por_intervalo(user_id, dias=1)
    elif intervalo == "semana":
        eventos = await buscar_eventos_por_intervalo(user_id, semana=True)
    else:
        eventos = await buscar_eventos_por_intervalo(user_id, dias=-365)

    if not eventos:
        await update.message.reply_text("📭 Nenhum evento encontrado para gerar a agenda.")
        await responder_em_audio(update, context, "Nenhum evento disponível para gerar a agenda.")
        return

    # 🧾 Gera planilha em memória
    excel_stream = await gerar_excel_agenda(user_id, eventos)

    await update.message.reply_document(
        document=InputFile(excel_stream, filename="agenda_neoagenda.xlsx"),
        caption="📎 Aqui está sua agenda exportada com sucesso."
    )

    await responder_em_audio(update, context, "Sua agenda em Excel foi gerada e enviada.")  