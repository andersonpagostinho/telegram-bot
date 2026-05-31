# handlers/acao_router_handler.py
import inspect
from datetime import datetime
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path
from services.profissional_service import obter_precos_servico, encontrar_servico_mais_proximo
from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario


async def executar_acao_por_nome(update, context, acao, dados):
    user_id = str(update.message.from_user.id)

    # 🔤 Normaliza nomes de ação vindos do LLM (sinônimos/variações)
    def normalizar_acao(nome: str | None) -> str | None:
        if not nome:
            return None
        mapa = {
            "listar_tarefas": "buscar_tarefas_do_usuario",
            "ver_tarefas": "buscar_tarefas_do_usuario",
            "mostrar_tarefas": "buscar_tarefas_do_usuario",
            "minhas_tarefas": "buscar_tarefas_do_usuario",
            # extras relacionadas a tarefas
            "listar_prioridade": "listar_tarefas_por_prioridade",
            "limpar_tarefas": "limpar_tarefas_do_usuario",
            "adicionar_tarefa": "criar_tarefa",
        }
        return mapa.get(nome, nome)

    acao = normalizar_acao(acao)

    async def executar_se_coroutine(func, *args):
        print(f"⚙️ Função chamada: {func.__name__}")
        resultado = func(*args)
        print(f"🔁 Tipo do resultado: {type(resultado)}")
        if inspect.isawaitable(resultado):
            print("⏳ Resultado é awaitable, aguardando...")
            return await resultado
        print("🚫 Resultado não é awaitable.")
        return resultado

    try:
        print(f"\n➡️ Executando ação: {acao}")
        print(f"📦 Dados recebidos do GPT: {dados}")

        if acao in ["adicionar_tarefa", "criar_tarefa"]:
            from .task_handler import add_task_por_gpt
            await executar_se_coroutine(add_task_por_gpt, update, context, dados)

        elif acao == "buscar_tarefas_do_usuario":
            from .task_handler import gerar_texto_tarefas
            user_id = str(update.message.from_user.id)
            texto = await gerar_texto_tarefas(user_id)
            resposta = dados.get("resposta") or "Aqui estão suas tarefas:"
            await update.message.reply_text(f"{resposta}\n\n{texto}", parse_mode="Markdown")
            return {
                "resposta": f"{resposta}\n\n{texto}",
                "acao": "buscar_tarefas_do_usuario",
                "dados": {"tarefas": texto}
            }

        # 🆕 Listar tarefas por prioridade
        elif acao == "listar_tarefas_por_prioridade":
            from .task_handler import list_tasks_by_priority
            await executar_se_coroutine(list_tasks_by_priority, update, context, {})
            return {
                "resposta": "Listando tarefas por prioridade…",
                "acao": "listar_tarefas_por_prioridade",
                "dados": {}
            }

        # 🧹 Limpar todas as tarefas
        elif acao == "limpar_tarefas_do_usuario":
            from .task_handler import clear_tasks
            await executar_se_coroutine(clear_tasks, update, context, {})
            return {
                "resposta": "Limpando tarefas do usuário…",
                "acao": "limpar_tarefas_do_usuario",
                "dados": {}
            }

        elif acao == "criar_evento":
            user_id = str(update.message.from_user.id)
            contexto = await carregar_contexto_temporario(user_id)
            resposta_usuario = update.message.text.lower()
            alternativa = (contexto.get("alternativa_profissional") or "").lower()

            if alternativa and alternativa in resposta_usuario:
                print(f"🔁 Substituindo profissional original '{dados.get('profissional')}' pela alternativa '{alternativa}'")
                dados["profissional"] = alternativa.capitalize()

            from .event_handler import add_evento_por_gpt
            print("🟢 Chamando add_evento_por_gpt com dados:", dados)
            await executar_se_coroutine(add_evento_por_gpt, update, context, dados)

        elif acao == "enviar_email":
            from .email_handler import enviar_email_por_gpt
            await executar_se_coroutine(enviar_email_por_gpt, update, context, dados)

        elif acao == "ler_email":
            from .email_handler import ler_email_por_gpt
            await executar_se_coroutine(ler_email_por_gpt, update, context, dados)

        elif acao == "organizar_semana":
            from services.firebase_service_async import buscar_subcolecao
            from services.gpt_service import organizar_semana_com_gpt

            tarefas_dict = await buscar_subcolecao(f"Clientes/{user_id}/Tarefas")
            eventos_dict = await buscar_subcolecao(f"Clientes/{user_id}/Eventos")

            tarefas = [t["descricao"] for t in tarefas_dict.values() if "descricao" in t]
            eventos = [e["descricao"] for e in eventos_dict.values() if "descricao" in e]

            resposta = await organizar_semana_com_gpt(tarefas, eventos)
            await update.message.reply_text(resposta, parse_mode="Markdown")
            return {
                "resposta": resposta,
                "acao": "organizar_semana",
                "dados": {"tarefas": tarefas, "eventos": eventos}
            }

        elif acao == "criar_followup":
            from .followup_handler import criar_followup_por_gpt
            await executar_se_coroutine(criar_followup_por_gpt, update, context, dados)

        elif acao == "concluir_followup":
            from .followup_handler import concluir_followup_por_gpt
            await executar_se_coroutine(concluir_followup_por_gpt, update, context, dados)

        elif acao == "cadastrar_profissional":
            from services.cadastro_inicial_service import salvar_profissional
            from services.firebase_service_async import obter_id_dono

            nome = (dados.get("nome") or "").strip()

            # Aceita dois formatos:
            # 1. servicos_dict: {"corte": {"preco": 50, "duracao": 30}, ...}
            #    → vindo da camada admin (estruturado, com preço e duração)
            # 2. servicos: ["Corte", "Escova"]
            #    → vindo do GPT (legado, lista simples sem preço/duração)
            servicos_dict = dados.get("servicos_dict") or {}

            if not servicos_dict:
                # Fallback legado: converte lista de nomes para dict vazio por serviço
                servicos_lista = dados.get("servicos") or []
                if isinstance(servicos_lista, list):
                    servicos_dict = {
                        s.strip().lower(): {} for s in servicos_lista if s.strip()
                    }

            if not nome or not servicos_dict:
                await update.message.reply_text(
                    "⚠️ Dados incompletos para cadastrar profissional.\n"
                    "Informe nome e ao menos um serviço."
                )
                return

            # Salva sempre no tenant do dono, nunca no cliente
            dono_id = await obter_id_dono(user_id)

            print(
                f"📌 [cadastrar_profissional] tenant={dono_id} | "
                f"nome={nome} | servicos={servicos_dict}",
                flush=True,
            )

            try:
                payload = await salvar_profissional(dono_id, nome, servicos_dict)
            except Exception as e:
                print(f"❌ [cadastrar_profissional] erro ao salvar: {e}", flush=True)
                await update.message.reply_text(
                    "❌ Erro ao salvar a profissional. Tente novamente."
                )
                return

            servicos_fmt = ", ".join(payload.get("servicos") or [])
            nome_fmt = payload.get("nome") or nome

            await update.message.reply_text(
                f"✅ Profissional *{nome_fmt}* cadastrada com: *{servicos_fmt}*",
                parse_mode="Markdown",
            )

        elif acao == "adicionar_servico_profissional":
            from services.firebase_service_async import (
                obter_id_dono, buscar_dado_em_path, salvar_dado_em_path
            )

            nome = (dados.get("nome") or "").strip()
            servicos_dict = dados.get("servicos_dict") or {}

            if not nome or not servicos_dict:
                await update.message.reply_text(
                    "⚠️ Dados incompletos para adicionar serviço à profissional."
                )
                return

            nome_fmt = nome.strip().title()
            dono_id = await obter_id_dono(user_id)
            path = f"Clientes/{dono_id}/Profissionais/{nome_fmt}"

            print(
                f"📌 [adicionar_servico_profissional] tenant={dono_id} | "
                f"nome={nome_fmt} | novos={servicos_dict}",
                flush=True,
            )

            try:
                prof_atual = await buscar_dado_em_path(path) or {}

                # Merge: preserva serviços existentes e adiciona os novos
                servicos_lista = list(prof_atual.get("servicos") or [])
                precos    = dict(prof_atual.get("precos") or {})
                duracoes  = dict(prof_atual.get("duracoes") or {})
                detalhe   = dict(prof_atual.get("servicos_detalhe") or {})

                for chave, info in servicos_dict.items():
                    # Padronização: serviços sempre em minúsculas
                    chave_norm = chave.strip().lower()
                    if chave_norm not in servicos_lista:
                        servicos_lista.append(chave_norm)
                    if info.get("preco") is not None:
                        precos[chave_norm] = float(info["preco"])
                    if info.get("duracao") is not None:
                        duracoes[chave_norm] = int(info["duracao"])
                    detalhe[chave_norm] = info

                servicos_lista = sorted(set(servicos_lista))

                payload_merged = {
                    "nome": nome_fmt,
                    "servicos": servicos_lista,
                    "precos": precos,
                    "duracoes": duracoes,
                    "servicos_detalhe": detalhe,
                }
                await salvar_dado_em_path(path, payload_merged)

            except Exception as e:
                print(f"❌ [adicionar_servico_profissional] erro: {e}", flush=True)
                await update.message.reply_text("❌ Erro ao adicionar o serviço. Tente novamente.")
                return

            servico_nome = list(servicos_dict.keys())[0].strip().title()
            await update.message.reply_text(
                f"✅ *{servico_nome}* adicionado à agenda de *{nome_fmt}* com sucesso.",
                parse_mode="Markdown",
            )

        elif acao == "excluir_profissional":
            from services.firebase_service_async import (
                obter_id_dono, deletar_dado_em_path
            )

            nome = (dados.get("nome") or "").strip()
            if not nome:
                await update.message.reply_text("⚠️ Nome da profissional não informado.")
                return

            nome_fmt = nome.strip().title()
            dono_id = await obter_id_dono(user_id)
            path = f"Clientes/{dono_id}/Profissionais/{nome_fmt}"

            print(
                f"🗑️ [excluir_profissional] tenant={dono_id} | nome={nome_fmt}",
                flush=True,
            )

            try:
                ok = await deletar_dado_em_path(path)
            except Exception as e:
                print(f"❌ [excluir_profissional] erro: {e}", flush=True)
                await update.message.reply_text("❌ Erro ao excluir a profissional. Tente novamente.")
                return

            if ok:
                await update.message.reply_text(
                    f"✅ Profissional *{nome_fmt}* removida com sucesso.",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text(
                    f"❌ Não encontrei *{nome_fmt}* no cadastro.",
                    parse_mode="Markdown",
                )

        elif acao == "consultar_agenda_salao":
            from services.firebase_service_async import buscar_subcolecao, obter_id_dono
            from datetime import datetime

            data_iso = (dados.get("data") or "").strip()
            if not data_iso:
                await update.message.reply_text("⚠️ Data não informada para consulta de agenda.")
                return

            dono_id = await obter_id_dono(user_id)
            eventos_raw = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}

            status_cancelados = {
                "cancelado", "cancelada", "removido", "removida", "excluido", "excluído"
            }

            # Filtra por data e status
            eventos_do_dia = []
            for ev in eventos_raw.values():
                if not isinstance(ev, dict):
                    continue
                if ev.get("data") != data_iso:
                    continue
                status = (ev.get("status") or "").strip().lower()
                if status in status_cancelados:
                    continue
                hora_inicio = ev.get("hora_inicio") or ""
                if not hora_inicio:
                    continue
                eventos_do_dia.append(ev)

            # Ordena por hora_inicio
            eventos_do_dia.sort(key=lambda e: e.get("hora_inicio", ""))

            # Formata data legível
            try:
                data_fmt = datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                data_fmt = data_iso

            print(
                f"📅 [consultar_agenda_salao] tenant={dono_id} | "
                f"data={data_iso} | eventos={len(eventos_do_dia)}",
                flush=True,
            )

            if not eventos_do_dia:
                await update.message.reply_text(
                    f"📅 *Agenda do salão — {data_fmt}*\n\nNenhum atendimento agendado.",
                    parse_mode="Markdown",
                )
                return

            import re as _re

            linhas = [f"📅 *Agenda do salão — {data_fmt}*"]
            for ev in eventos_do_dia:
                hora = ev.get("hora_inicio", "??:??")
                prof = (ev.get("profissional") or "—").strip()

                # Prefere campo servico (limpo); se não existir, limpa descricao
                servico = (ev.get("servico") or "").strip()
                if not servico:
                    desc_raw = (ev.get("descricao") or "Atendimento").strip()
                    # Remove " com {profissional}" do fim, se presente
                    servico = _re.sub(
                        rf"\s+com\s+{_re.escape(prof)}\s*$",
                        "",
                        desc_raw,
                        flags=_re.IGNORECASE,
                    ).strip() or desc_raw

                # Cliente: tenta vários campos possíveis
                cliente = (
                    ev.get("cliente_nome")
                    or ev.get("nome_cliente")
                    or ev.get("cliente")
                    or ""
                ).strip()

                linhas.append("")                                    # linha em branco
                linhas.append(f"*{hora}* — {prof} — {servico}")
                if cliente:
                    linhas.append(f"Cliente: {cliente}")

            linhas.append("")
            linhas.append(f"_Total de atendimentos: {len(eventos_do_dia)}_")

            await update.message.reply_text(
                "\n".join(linhas),
                parse_mode="Markdown",
            )

        elif acao == "listar_profissionais":
            from services.firebase_service_async import buscar_subcolecao

            profissionais = await buscar_subcolecao(f"Clientes/{user_id}/Profissionais")

            if not profissionais:
                await update.message.reply_text("📬 Nenhum profissional cadastrado ainda.")
                return

            mensagem = "👥 *Profissionais cadastrados:*\n\n"
            for nome, dados in profissionais.items():
                servicos = ", ".join(dados.get("servicos", []))
                mensagem += f"• *{nome}* – {servicos}\n"

            await update.message.reply_text(mensagem, parse_mode="Markdown")
            return {
                "resposta": mensagem,
                "acao": "listar_profissionais",
                "dados": profissionais
            }

        elif acao == "bloquear_agenda_salao":
            from services.agenda_service import bloquear_datas_agenda_salao, normalizar_lista_datas

            datas = (dados or {}).get("datas") or []
            motivo = (dados or {}).get("motivo") or "fechado"

            datas = normalizar_lista_datas(datas)

            if not datas:
                msg = "⚠️ Não consegui identificar as datas para bloquear a agenda."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_salao",
                    "dados": {}
                }

            sucesso = await bloquear_datas_agenda_salao(
                user_id=user_id,
                datas=datas,
                motivo=motivo
            )

            if not sucesso:
                msg = "❌ Não consegui salvar o bloqueio da agenda."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_salao",
                    "dados": {"datas": datas, "motivo": motivo}
                }

            # 🧹 limpa contexto de agendamento
            ctx = await carregar_contexto_temporario(user_id) or {}
            ctx["estado_fluxo"] = "idle"
            ctx.pop("draft_agendamento", None)
            ctx.pop("data_hora", None)

            # opcional, mas eu recomendo fortemente já limpar também:
            ctx.pop("servico", None)
            ctx.pop("profissional_escolhido", None)
            ctx.pop("ultima_consulta", None)
            ctx.pop("aguardando_confirmacao_agendamento", None)
            ctx.pop("dados_confirmacao_agendamento", None)

            await salvar_contexto_temporario(user_id, ctx)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                "Perfeito 😊\n"
                "Fechei a agenda destes dias:\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)
            return {
                "resposta": resposta,
                "acao": "bloquear_agenda_salao",
                "dados": {
                    "datas": datas,
                    "motivo": motivo
                }
            }

        elif acao == "definir_meio_periodo_salao":
            from services.agenda_service import definir_janela_especial_agenda_salao, normalizar_lista_datas
            from utils.context_manager import limpar_contexto_agendamento
            
            datas = (dados or {}).get("datas") or []
            inicio = (dados or {}).get("inicio")
            fim = (dados or {}).get("fim")
            motivo = (dados or {}).get("motivo") or "expediente_reduzido"
  
            datas = normalizar_lista_datas(datas)

            if not datas or not inicio or not fim:
                msg = "⚠️ Não consegui identificar corretamente o período de atendimento."
                await update.message.reply_text(msg)
                return

            sucesso = await definir_janela_especial_agenda_salao(
                user_id=user_id,
                datas=datas,
                inicio=inicio,
                fim=fim,
                motivo=motivo
            )

            if not sucesso:
                msg = "❌ Não consegui salvar o horário especial."
                await update.message.reply_text(msg)
                return

            # 🧹 limpa contexto de agendamento
            await limpar_contexto_agendamento(user_id)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                "Perfeito 😊\n"
                f"Ajustei o atendimento destes dias para:\n"
                f"{inicio} às {fim}\n\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)

            return {
                "resposta": resposta,
                "acao": "definir_meio_periodo_salao",
                "dados": dados
            }  

        elif acao == "bloquear_agenda_profissional":
            from services.agenda_service import bloquear_agenda_profissional, normalizar_lista_datas
            from utils.context_manager import limpar_contexto_agendamento

            profissional = (dados or {}).get("profissional")
            datas = (dados or {}).get("datas") or []
            motivo = (dados or {}).get("motivo") or "indisponivel"

            profissional = (profissional or "").strip()
            datas = normalizar_lista_datas(datas)

            if not profissional or not datas:
                msg = "⚠️ Não consegui identificar corretamente o profissional ou as datas do bloqueio."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_profissional",
                    "dados": {}
                }

            sucesso = await bloquear_agenda_profissional(
                user_id=user_id,
                profissional=profissional,
                datas=datas,
                motivo=motivo
            )

            if not sucesso:
                msg = f"❌ Não consegui salvar o bloqueio da agenda de {profissional}."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_bloquear_agenda_profissional",
                    "dados": dados
                }

            await limpar_contexto_agendamento(user_id)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                f"Perfeito 😊\n"
                f"Bloqueei a agenda de {profissional} nestes dias:\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)
            return {
                "resposta": resposta,
                "acao": "bloquear_agenda_profissional",
                "dados": {
                    "profissional": profissional,
                    "datas": datas,
                    "motivo": motivo
                }
            }

        elif acao == "definir_meio_periodo_profissional":
            from services.agenda_service import definir_janela_especial_profissional, normalizar_lista_datas
            from utils.context_manager import limpar_contexto_agendamento

            profissional = (dados or {}).get("profissional")
            datas = (dados or {}).get("datas") or []
            inicio = (dados or {}).get("inicio")
            fim = (dados or {}).get("fim")
            motivo = (dados or {}).get("motivo") or "expediente_reduzido"

            profissional = (profissional or "").strip()
            datas = normalizar_lista_datas(datas)

            if not profissional or not datas or not inicio or not fim:
                msg = "⚠️ Não consegui identificar corretamente o profissional ou o período especial."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_definir_meio_periodo_profissional",
                    "dados": {}
                }

            sucesso = await definir_janela_especial_profissional(
                user_id=user_id,
                profissional=profissional,
                datas=datas,
                inicio=inicio,
                fim=fim,
                motivo=motivo
            )

            if not sucesso:
                msg = f"❌ Não consegui salvar o horário especial de {profissional}."
                await update.message.reply_text(msg)
                return {
                    "resposta": msg,
                    "acao": "erro_definir_meio_periodo_profissional",
                    "dados": dados
                }

            await limpar_contexto_agendamento(user_id)

            datas_formatadas = "\n".join(
                f"• {datetime.fromisoformat(d).strftime('%d/%m/%Y')}"
                for d in datas
            )

            resposta = (
                f"Perfeito 😊\n"
                f"Ajustei o atendimento de {profissional} para:\n"
                f"{inicio} às {fim}\n\n"
                f"{datas_formatadas}"
            )

            await update.message.reply_text(resposta)
            return {
                "resposta": resposta,
                "acao": "definir_meio_periodo_profissional",
                "dados": {
                    "profissional": profissional,
                    "datas": datas,
                    "inicio": inicio,
                    "fim": fim,
                    "motivo": motivo
                }
            }

        elif acao == "verificar_disponibilidade_profissional":
            from services.profissional_service import buscar_profissionais_por_servico
            from .acao_handler import verificar_disponibilidade_profissional

            servicos = dados.get("servicos", [])
            profissionais_filtrados = await buscar_profissionais_por_servico(servicos, user_id)

            if not profissionais_filtrados:
                await update.message.reply_text("😕 Nenhum profissional oferece todos esses serviços.")
                return

            resultado = await verificar_disponibilidade_profissional({
                "data_hora": dados["data_hora"],
                "duracao": dados["duracao"],
                "profissionais": list(profissionais_filtrados.keys())
            }, user_id)

            await update.message.reply_text(resultado["resposta"], parse_mode="Markdown")
            return {
                "resposta": resultado["resposta"],
                "acao": "verificar_disponibilidade_profissional",
                "dados": resultado
            }

        elif acao == "consultar_preco_servico":
             return await consultar_preco_servico(update, context, dados)

        else:
            await update.message.reply_text(f"⚠️ Ação desconhecida: {acao}")

    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao executar ação '{acao}': {e}")
        print(f"❌ Erro em executar_acao_por_nome: {e}")

async def consultar_preco_servico(update, context, dados):
    user_id = str(update.message.from_user.id)
    servico = dados.get("servico", "").lower()
    profissional_nome = dados.get("profissional")

    if not servico:
        msg = "❌ Não consegui identificar o serviço."
        await update.message.reply_text(msg)
        return {
            "resposta": msg,
            "acao": "erro_consulta_preco",
            "dados": {}
        }

    if profissional_nome:
        preco = await obter_precos_servico(user_id, servico, profissional_nome)
        if preco is not None:
            try:
                valor_formatado = f"{float(preco):.2f}"
            except Exception:
                valor_formatado = str(preco)
            resposta = (
                f"O preço de *{servico}* com *{profissional_nome}* é R$ {valor_formatado}"
            )
        else:
            resposta = (
                f"Infelizmente não temos o preço de {servico} com {profissional_nome} ainda."
            )
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return {
            "resposta": resposta,
            "acao": "resposta_preco",
            "dados": {"servico": servico, "profissional": profissional_nome}
        }

    precos = await obter_precos_servico(user_id, servico)

    if precos:
        resposta = f"Valores de *{servico}*:\n"
        for nome, preco in precos.items():
            try:
                valor_formatado = f"{float(preco):.2f}"
            except Exception:
                valor_formatado = str(preco)
            resposta += f"- *{nome}*: R$ {valor_formatado}\n"
    else:
        resposta = f"Infelizmente não temos esse preço ainda."

    await update.message.reply_text(resposta, parse_mode="Markdown")
    return {
        "resposta": resposta,
        "acao": "resposta_preco",
        "dados": {"servico": servico}
    }

async def consultar_tabela_geral_de_precos(update, user_id):
    precos = await obter_precos_servico(user_id)
    if not precos:
        await update.message.reply_text("Ainda não temos uma tabela de preços cadastrada.")
        return

    resposta = "*Tabela de Preços:*\n"
    for servico, precos_por_prof in precos.items():
        resposta += f"\n*{servico.title()}*\n"
        for prof, valor in precos_por_prof.items():
            resposta += f"- {prof}: R$ {valor:.2f}\n"

    await update.message.reply_text(resposta, parse_mode="Markdown")
    return {
        "resposta": resposta,
        "acao": "tabela_geral_precos",
        "dados": precos
    }
