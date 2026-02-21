# gpt Service
import os
import json
import re
import traceback
print("⚠️ Falha no filtro/auditoria CTX->GPT:", flush=True)
print(traceback.format_exc(), flush=True)
import importlib
import inspect
import unidecode  # se preferir, troque por: from unidecode import unidecode
from datetime import datetime, timedelta
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario
from utils.custos_gpt import registrar_custo_gpt
from firebase_admin import firestore
from utils.formatters import adaptar_genero
from utils.interpretador_datas import interpretar_data_e_hora
from services.session_service import pegar_sessao, resetar_sessao
from utils.context_manager import atualizar_contexto, limpar_contexto, limpar_contexto_agendamento
from services.profissional_service import (
    listar_servicos_cadastrados, obter_precos_servico,
    encontrar_servico_mais_proximo, consultar_todos_precos
)
from services.gpt_client import client
from utils.gpt_utils import (
    montar_prompt_com_contexto,
    formatar_descricao_evento,
    estimar_duracao,
    formatar_data,
)
from services.gpt_actions import (
    executar_acao_gpt_por_confirmacao,
    executar_confirmacao_generica,
)

from services.firebase_service_async import buscar_cliente, buscar_subcolecao

# ✅ GPT simples para respostas diretas (com plano e módulos no prompt)
async def processar_com_gpt(texto_usuario, user_id="desconhecido"):
    try:
        # 🔍 Busca os dados do cliente
        cliente = await buscar_cliente(user_id)
        pagamento_ativo = cliente.get("pagamentoAtivo", False) if cliente else False
        planos_ativos = cliente.get("planosAtivos", []) if cliente else []

        # 🧠 Monta prompt com os dados de plano
        prompt_completo = f"""
📌 Plano ativo: {pagamento_ativo}
🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}

🗣️ Mensagem do usuário:
\"{texto_usuario}\"
"""
        # 🔀 NÃO chama mais o GPT aqui. Encaminha para o fluxo único.
        print(
            f"🔀 [REDIRECT] processar_com_gpt -> processar_com_gpt_com_acao "
            f"user_id={user_id} pagamentoAtivo={pagamento_ativo} planosAtivos={planos_ativos} "
            f"texto={texto_usuario!r}",
            flush=True
        )

        # ⚠️ Ajuste obrigatório: sua assinatura exige contexto e instrucao
        # Se aqui você não tiver "contexto" disponível, passe {} e deixe o fluxo único carregar/ajustar.
        resultado = await processar_com_gpt_com_acao(
            texto_usuario=texto_usuario,
            contexto={},
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
        )

        # Normaliza retorno (dict ou string)
        if isinstance(resultado, dict):
            return resultado.get("resposta") or ""
        return str(resultado)

    except Exception as e:
        print(f"❌ Erro no processar_com_gpt (redirect): {type(e).__name__}: {e}", flush=True)
        return "❌ Houve um erro ao processar com a IA."


async def tratar_mensagem_usuario(user_id, mensagem):
    print("🔥 [gpt_service] Entrou no tratar_mensagem_usuario via importlib")

    # 👇 Essa linha mostra de onde a função está sendo chamada
    print("📍 Stack de chamada:")
    for frame in inspect.stack()[1:5]:  # mostra os 4 níveis anteriores
        print(f" - Arquivo: {frame.filename}, Linha: {frame.lineno}, Função: {frame.function}")

    # Carrega a função original dinamicamente
    acao_handler = importlib.import_module("handlers.acao_handler")
    return await acao_handler.tratar_mensagem_usuario(user_id, mensagem)

# ✅ GPT com contexto e resposta estruturada em JSON (ação + dados)
async def processar_com_gpt_com_acao(
    texto_usuario: str,
    contexto: dict,
    instrucao: str,
    user_id: str | None = None,
):
    print("🚨 [gpt_service] Arquivo carregado", flush=True)
    try:
        # --- 1) user_id robusto ---
        uid = (
            user_id
            or str((contexto.get("usuario") or {}).get("id") or "")
            or str((contexto.get("usuario") or {}).get("user_id") or "")
            or str(contexto.get("user_id") or "")
            or str(contexto.get("cliente_id") or "")
        ).strip() or "desconhecido"

        texto_usuario = (texto_usuario or "").strip()
        # 👇 ajuste do unidecode (opção 1: usando o módulo)
        texto_normalizado = unidecode.unidecode(texto_usuario.lower().strip())
        # (opção 2 seria: from unidecode import unidecode; e então texto_normalizado = unidecode(...))

        # --- 2) Contexto temporário salvo (sempre por UID correto) ---
        try:
            contexto_salvo = await carregar_contexto_temporario(uid) if uid != "desconhecido" else {}
            print("🧪 DEBUG uid:", uid, flush=True)
            print("🧪 DEBUG texto_usuario:", texto_usuario, flush=True)
            print("🧪 DEBUG contexto_salvo (chaves):", sorted(list((contexto_salvo or {}).keys())), flush=True)
            print("🧪 DEBUG contexto_salvo (servico/data_hora/prof/evento_criado):", {
                "servico": (contexto_salvo or {}).get("servico"),
                "data_hora": (contexto_salvo or {}).get("data_hora"),
                "profissional_escolhido": (contexto_salvo or {}).get("profissional_escolhido"),
                "evento_criado": (contexto_salvo or {}).get("evento_criado"),
                "ultima_acao": (contexto_salvo or {}).get("ultima_acao"),
            }, flush=True)

        except Exception as _e:
            print(f"⚠️ Falha ao carregar contexto temporário: {_e}", flush=True)
            contexto_salvo = {}

        if contexto_salvo.get("profissional_escolhido"):
            contexto_salvo.pop("ultima_opcao_profissionais", None)

        # --- 2.1) Curto-circuito: usuário digitou nome de profissional (antes do GPT) ---
        # Funciona mesmo se ainda faltar serviço/data_hora.
        try:
            if uid != "desconhecido":
                # Descobre id_dono (se tiver id_negocio)
                id_dono = uid
                try:
                    cliente_tmp = await buscar_cliente(uid) or {}
                    id_dono = str(cliente_tmp.get("id_negocio") or uid)
                except Exception:
                    id_dono = uid

                # Só trata se for uma mensagem curta (ex: "bruna")
                msg_norm = texto_normalizado
                if msg_norm and len(msg_norm.split()) <= 2:
                    profissionais_dict = await buscar_subcolecao(f"Clientes/{id_dono}/Profissionais") or {}

                    prof_match = None
                    for p in profissionais_dict.values():
                        nome = (p or {}).get("nome")
                        if not nome:
                            continue
                        if msg_norm == unidecode.unidecode(str(nome).lower().strip()):
                            prof_match = str(nome).strip()
                            break

                    if prof_match:
                        # 🔒 Se houve lista oferecida, só aceita dentro dela
                        opcoes = (contexto_salvo or {}).get("ultima_opcao_profissionais") or []
                        if opcoes:
                            opcoes_norm = {unidecode.unidecode(str(x).lower().strip()) for x in opcoes}
                            if unidecode.unidecode(prof_match.lower().strip()) not in opcoes_norm:
                                lista = ", ".join(opcoes)
                                return {
                                    "resposta": f"Para {contexto_salvo.get('servico','esse serviço')}, eu tenho disponível: {lista}. Qual deles você prefere?",
                                    "acao": None,
                                    "dados": {}
                                }

                        # Salva profissional (merge)
                        await salvar_contexto_temporario(uid, {"profissional_escolhido": prof_match})

                        # Recarrega o contexto (estado mais recente)
                        contexto_salvo = await carregar_contexto_temporario(uid) or {}

                        servico = contexto_salvo.get("servico")
                        data_hora = contexto_salvo.get("data_hora")

                        # Se falta serviço:
                        if not servico:
                            return {
                                "resposta": f"Perfeito — com {prof_match}. Qual serviço você quer agendar?",
                                "acao": None,
                                "dados": {}
                            }

                        # Se falta data/hora:
                        if not data_hora:
                            return {
                                "resposta": f"Perfeito — {servico} com {prof_match}. Para qual dia e horário?",
                                "acao": None,
                                "dados": {}
                            }

                        # Se tem tudo: cria evento
                        return {
                            "resposta": f"Perfeito. Vou agendar {servico} com {prof_match} para {formatar_data(data_hora)}.",
                            "acao": "criar_evento",
                            "dados": {
                                "data_hora": data_hora,
                                "descricao": f"{servico} com {prof_match}",
                                "duracao": estimar_duracao(servico),
                                "profissional": prof_match
                            }
                        }
        except Exception as e:
            print(f"⚠️ Curto-circuito profissional falhou: {e}", flush=True)

        # --- 3.0) Persistir servico e data_hora (antes do GPT) ---
        try:
            if uid != "desconhecido":
                dados_update = {}

                # 1) tentar detectar serviço por aproximação simples
                try:
                    id_dono = uid
                    cliente_tmp = await buscar_cliente(uid) or {}
                    id_dono = str(cliente_tmp.get("id_negocio") or uid)

                    servicos_disponiveis = await listar_servicos_cadastrados(id_dono) or []
                    txt = texto_normalizado

                    for s in servicos_disponiveis:
                        s_norm = unidecode.unidecode(str(s).lower().strip())
                        if s_norm and s_norm in txt:
                            dados_update["servico"] = str(s).strip()
                            break

                except Exception as e:
                    print(f"⚠️ Falha ao detectar serviço automaticamente: {e}", flush=True)

                # 2) interpretar data/hora
                try:
                    texto_hora_only = (texto_usuario or "").strip().lower()

                    # Detecta "só horário"
                    # Aceita: "16:40" | "as 16:40" | "às 16:40" | "16h40" | "16h" | "16"
                    m = re.match(r"^(?:às|as)?\s*(\d{1,2})(?:[:h]\s*(\d{2}))?\s*$", texto_hora_only)

                    data_hora_ctx = (contexto_salvo or {}).get("data_hora")

                    if m and data_hora_ctx:
                        hora = int(m.group(1))
                        minuto = int(m.group(2) or 0)

                        base = datetime.fromisoformat(str(data_hora_ctx))
                        dt = base.replace(hour=hora, minute=minuto, second=0, microsecond=0)
                    else:
                        dt = interpretar_data_e_hora(texto_usuario)

                    if dt:
                        try:
                            dados_update["data_hora"] = dt.replace(second=0, microsecond=0).isoformat()
                        except Exception:
                            dados_update["data_hora"] = str(dt)

                # 2.1) detectar profissional pelo texto (para continuidade do "pode agendar então")
                try:
                    txt_prof = unidecode.unidecode((texto_usuario or "").lower().strip())

                    # pega nomes do próprio contexto (mais robusto do que hardcode)
                    nomes_ctx = []
                    try:
                        for p in (contexto.get("profissionais") or []):
                            n = (p.get("nome") or "").strip()
                            if n:
                                nomes_ctx.append(n)
                    except Exception:
                        pass

                    # fallback: nomes conhecidos (se contexto não tiver lista)
                    if not nomes_ctx:
                        nomes_ctx = ["Amanda", "Bruna", "Carla", "Gloria", "Joana", "Larissa"]

                    nome_detectado = None
                    for n in nomes_ctx:
                        n_norm = unidecode.unidecode(str(n).lower().strip())
                        if n_norm and n_norm in txt_prof:
                            nome_detectado = str(n).strip()
                            break

                    if nome_detectado:
                        dados_update["profissional_escolhido"] = nome_detectado
                        # opcional: ajuda a retomar fluxos de consulta→agendamento
                        if "data_hora" in dados_update:
                            dados_update["ultima_consulta"] = {
                            "profissional": nome_detectado,
                            "data_hora": dados_update["data_hora"],
                        }

                except Exception as e:
                print(f"⚠️ Falha ao detectar profissional automaticamente: {e}", flush=True)

                except Exception as e:
                    print(f"⚠️ Falha ao interpretar data/hora: {e}", flush=True)

                # salvar se houver algo
                if dados_update:
                    await salvar_contexto_temporario(uid, dados_update)
                    contexto_salvo = {**(contexto_salvo or {}), **dados_update}
                    print(f"💾 Contexto atualizado antes do GPT: {dados_update}", flush=True)

        except Exception as e:
            print(f"⚠️ Falha ao salvar servico/data_hora antes do GPT: {e}", flush=True)


        # --- 3) Saudações curtas ---
        SAUDACOES_INICIAIS = {
            "oi", "ola", "olá", "opa", "e ai", "e aí", "eai", "eaí",
            "bom dia", "boa tarde", "boa noite", "tudo bem", "como vai",
            "beleza", "salve", "fala ai", "fala aí", "fala", "oie", "oiê", "oi oi"
        }
        if texto_normalizado in SAUDACOES_INICIAIS:
            try:
                if contexto_salvo.get("evento_criado") and contexto_salvo.get("ultima_acao") == "criar_evento":
                    if uid != "desconhecido":
                        await limpar_contexto_agendamento(uid)
                        await limpar_contexto(uid)
                    return {"resposta": "👋 Olá! Em que mais posso te ajudar hoje?", "acao": None, "dados": {}}
                elif any(contexto_salvo.get(k) for k in ["servico", "data_hora", "profissional_escolhido"]):
                    partes = []
                    if contexto_salvo.get("servico"):
                        partes.append(f"{contexto_salvo['servico']}")
                    if contexto_salvo.get("profissional_escolhido"):
                        partes.append(f"com {contexto_salvo['profissional_escolhido']}")
                    if contexto_salvo.get("data_hora"):
                        partes.append(f"para {formatar_data(contexto_salvo['data_hora'])}")
                    resumo = " ".join(partes)
                    return {
                        "resposta": f"Estamos no meio de um agendamento de {resumo}. Deseja confirmar, alterar ou cancelar?",
                        "acao": None,
                        "dados": {},
                    }
                else:
                    return {"resposta": "👋 Olá! Como posso te ajudar hoje?", "acao": None, "dados": {}}
            except Exception as e:
                print(f"⚠️ Erro ao tratar saudação com contexto: {e}", flush=True)
                return {"resposta": "👋 Olá! Como posso te ajudar hoje?", "acao": None, "dados": {}}

        # --- 4) Garantir dados do usuário e flags de plano no CONTEXTO ---
        try:
            cliente = await buscar_cliente(uid) or {}
        except Exception as e:
            print(f"[gpt_service] buscar_cliente falhou para uid={uid}: {e}", flush=True)
            cliente = {}

        if "pagamentoAtivo" not in cliente:
            cliente["pagamentoAtivo"] = True
        if not cliente.get("planosAtivos"):
            cliente["planosAtivos"] = ["secretaria"]
        elif "secretaria" not in cliente["planosAtivos"]:
            cliente["planosAtivos"] = list(set(cliente["planosAtivos"] + ["secretaria"]))

        usuario_merge = {**(contexto.get("usuario") or {}), **cliente}

        contexto["usuario"] = usuario_merge
        contexto["pagamentoAtivo"] = bool(usuario_merge.get("pagamentoAtivo", True))
        contexto["planosAtivos"] = usuario_merge.get("planosAtivos", ["secretaria"]) or ["secretaria"]

        print(
            f"🧾 [gpt_service] uid={uid} | pagamentoAtivo={contexto['pagamentoAtivo']} | planosAtivos={contexto['planosAtivos']}",
            flush=True,
        )

        # --- 4.9) FILTRO + TRAVA: profissionais aptos ao serviço (ANTES do prompt) ---
        try:
            servico_ctx = (contexto_salvo or {}).get("servico")
            profs = (contexto or {}).get("profissionais") or []

            if servico_ctx and isinstance(profs, list):
                servico_norm = unidecode.unidecode(str(servico_ctx).lower().strip())
                profs_filtrados = []

                for p in profs:
                    if not isinstance(p, dict):
                        continue
                    servs = p.get("servicos") or []
                    if isinstance(servs, str):
                        servs = [servs]

                    servs_norm = {
                        unidecode.unidecode(str(s).lower().strip())
                        for s in servs
                        if s
                    }

                    if servico_norm in servs_norm:
                        profs_filtrados.append(p)

                # substitui no contexto (isso é o que o prompt builder deve usar)
                contexto["profissionais"] = profs_filtrados

                # trava a lista permitida (pra não aceitar "terceira opção")
                nomes_ok = [
                    p.get("nome") for p in profs_filtrados
                    if isinstance(p, dict) and p.get("nome")
                ]
                if uid != "desconhecido":
                    await salvar_contexto_temporario(uid, {"ultima_opcao_profissionais": nomes_ok})
                    contexto_salvo["ultima_opcao_profissionais"] = nomes_ok

            # auditoria do que vai ao prompt
            profs_final = (contexto or {}).get("profissionais") or []
            nomes_final = [p.get("nome") for p in profs_final if isinstance(p, dict) and p.get("nome")]
            print(
                "🧾 [CTX->GPT] "
                f"uid={uid} "
                f"servico={servico_ctx} "
                f"data_hora={(contexto_salvo or {}).get('data_hora')} "
                f"profs={len(profs_final)} "
                f"nomes={nomes_final} "
                f"ultima_opcao_profissionais={(contexto_salvo or {}).get('ultima_opcao_profissionais')}",
                flush=True
            )
        except Exception as e:
            print(f"⚠️ Falha no filtro/trava CTX->GPT: {e}", flush=True)

        # --- 5) Monta prompt/mensagens para a chamada única do GPT ---
        messages = montar_prompt_com_contexto(instrucao, contexto, contexto_salvo, texto_usuario)

        print(
            f"🧾 [PROMPT BUILT] uid={uid} "
            f"type={type(messages).__name__} "
            f"len={len(messages) if isinstance(messages, list) else 'n/a'}",
            flush=True
        )

    
        texto_curto = (texto_usuario or "").strip().lower()
        m = re.match(r"^(?:a?s?\s*)?(?:às?\s*)?(\d{1,2})(?:(?::|h)(\d{2}))?\s*$", texto_curto)

        if m:
            hh = int(m.group(1))
            mm = int(m.group(2) or "00")

            if 0 <= hh <= 23 and 0 <= mm <= 59:
                contexto_tmp = await carregar_contexto_temporario(uid) or {}

                profissional = contexto_tmp.get("profissional_escolhido")
                servico = contexto_tmp.get("servico")
                data_hora_antiga = contexto_tmp.get("data_hora")  # ISO string

                if profissional and servico and data_hora_antiga:
                    base_dt = datetime.fromisoformat(str(data_hora_antiga))
                    nova_dt = base_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
                    nova_data_hora = nova_dt.isoformat()

                    duracao = estimar_duracao(servico)

                    from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                    data = nova_dt.strftime("%Y-%m-%d")
                    hora = nova_dt.strftime("%H:%M")

                    conflito = await verificar_conflito_e_sugestoes_profissional(
                        user_id=uid,
                        data=data,
                        hora_inicio=hora,
                        duracao_min=duracao,
                        profissional=profissional,
                        servico=servico,
                    )

                    if not conflito.get("conflito"):
                        contexto_tmp.update({
                            "data_hora": nova_data_hora,
                            "evento_criado": True,
                            "ultima_acao": "criar_evento",
                            "ultima_intencao": "criar_evento",
                            "dados_anteriores": {
                                "profissional": profissional,
                                "servico": servico,
                                "data_hora": nova_data_hora,
                                "duracao": duracao,
                            },
                        })
                        await salvar_contexto_temporario(uid, contexto_tmp)

                        return {
                            "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(nova_data_hora)}. ✂️",
                            "acao": "criar_evento",
                            "dados": {
                                "data_hora": nova_data_hora,
                                "descricao": formatar_descricao_evento(servico, profissional),
                                "duracao": duracao,
                                "profissional": profissional,
                            }
                        }

                    # conflito == True -> sugestões
                    sugestoes = conflito.get("sugestoes") or []
                    sugestoes_txt = "\n".join(f"🔄 {h}" for h in sugestoes)
                    sugestao_formatada = (
                        f"\n\n📌 *Horários disponíveis com {profissional}:*\n{sugestoes_txt}"
                        if sugestoes_txt else ""
                    )

                    alternativa = conflito.get("profissional_alternativo")
                    alternativa_formatada = f"\n\n💡 {alternativa} está disponível às {hora}." if alternativa else ""

                    contexto_tmp.update({
                        "data_hora": nova_data_hora,
                        "sugestoes": sugestoes,
                        "alternativa_profissional": alternativa,
                        "ultima_acao": "criar_evento",
                        "dados_anteriores": {
                            "profissional": profissional,
                            "servico": servico,
                            "data_hora": base_dt.replace(second=0, microsecond=0).isoformat(),
                            "duracao": duracao,
                        },
                    })
                    await salvar_contexto_temporario(uid, contexto_tmp)

                    return {
                        "resposta": (
                            f"⚠️ {profissional} está {adaptar_genero(profissional, 'ocupad')} às {hora}."
                            f"{sugestao_formatada}"
                            f"{alternativa_formatada}"
                            f"\n\nDeseja escolher outro horário com {profissional} ou prefere agendar com {alternativa}?"
                        ),
                        "acao": None,
                        "dados": {}
                    }

                # faltando dados para ajustar horário
                faltando = []
                if not profissional:
                    faltando.append("profissional")
                if not servico:
                    faltando.append("serviço")
                if not data_hora_antiga:
                    faltando.append("data")
                return {"resposta": f"Para ajustar o horário, falta: {', '.join(faltando)}.", "acao": None, "dados": {}}


        # --- 6) Chamada única ao GPT + registrar custo ---
        resposta = None
        try:
            print(f"🤖 [GPT CALL] linha=1354 uid={uid} texto={texto_usuario!r}", flush=True)

            resposta = await client.chat.completions.create(
                model="gpt-4o",
                temperature=0.4,
                messages=messages,
            )

            # custo (somente se resposta existe)
            try:
                firestore_client = firestore.Client()
            except TypeError:
                firestore_client = firestore.client()

            await registrar_custo_gpt(resposta, "gpt-4o", uid, firestore_client)

        except Exception as e:
            print(f"❌ Erro ao chamar OpenAI: {type(e).__name__}: {e}", flush=True)
            return {
                "resposta": "⚠️ Tive um problema para processar sua solicitação agora.",
                "acao": None,
                "dados": {}
            }
        
        # --- 7) Interpreta retorno (JSON) ---
        resultado = {"resposta": "❌ Não consegui entender a resposta da IA.", "acao": None, "dados": {}}

        try:
            conteudo = (resposta.choices[0].message.content or "").strip()
            print("📦 Conteúdo recebido da IA:\n", conteudo, flush=True)

            # remove code fences ```json ... ```
            if conteudo.startswith("```"):
                linhas = conteudo.splitlines()
                # remove primeira e última linha se forem fences
                if linhas and linhas[0].startswith("```"):
                    linhas = linhas[1:]
                if linhas and linhas[-1].startswith("```"):
                    linhas = linhas[:-1]
                conteudo = "\n".join(linhas).strip()

            # extrai somente o objeto JSON se vier texto extra
            if "{" in conteudo and "}" in conteudo:
                inicio = conteudo.index("{")
                fim = conteudo.rindex("}")
                conteudo = conteudo[inicio:fim + 1]

            resultado = json.loads(conteudo)

            if not isinstance(resultado, dict):
                raise ValueError("Resposta não é um objeto JSON.")

            resultado.setdefault("resposta", "OK")
            resultado.setdefault("acao", None)
            resultado.setdefault("dados", {})

        except Exception as e:
            print(f"❌ Erro ao acessar/interpretar a resposta da IA: {e}", flush=True)
            try:
                print("🧾 Objeto resposta:\n", resposta.model_dump_json(indent=2, ensure_ascii=False), flush=True)
            except Exception:
                print("🧾 Objeto resposta (raw):", resposta, flush=True)

        # --- 8) Persistir pequeno histórico ---
        try:
            if uid != "desconhecido":
                # garante que estamos trabalhando com um dict válido
                contexto_salvo = contexto_salvo or {}

                hist = (contexto_salvo.get("historico") or [])[-9:]
                hist.append({"usuario": texto_usuario, "bot": resultado.get("resposta")})

                # ✅ MERGE: atualiza só o histórico, preservando o resto do contexto
                contexto_salvo["historico"] = hist
                await salvar_contexto_temporario(uid, contexto_salvo)

        except Exception as e:
            print(f"⚠️ Falha ao salvar contexto temporário: {e}", flush=True)

        # 🛡️ Guard-rail: usuário pediu tarefas e o GPT veio sem ação → força buscar no Firestore
        texto_baixo_guard = (texto_usuario or "").lower()
        pediu_tarefas = any(
            gatilho in texto_baixo_guard
            for gatilho in [
                "listar tarefas",
                "liste as tarefas",
                "liste todas as tarefas",
                "minhas tarefas",
                "quais são as minhas tarefas",
                "quais sao as minhas tarefas",
                "ver tarefas",
                "mostrar tarefas",
                "tarefas",
                "to-do",
                "afazeres",
                "pendências",
                "pendencias",
            ]
        )

        if pediu_tarefas and (
            resultado.get("acao") is None
            or resultado.get("acao") not in {"buscar_tarefas_do_usuario", "criar_tarefa", "remover_tarefa"}
        ):
            return {
                "resposta": "Aqui estão suas tarefas:",
                "acao": "buscar_tarefas_do_usuario",
                "dados": {}
            }

        return resultado

    except Exception as e:
        print(f"❌ Erro geral em processar_com_gpt_com_acao: {e}", flush=True)
        return {"resposta": "⚠️ Tive um problema para processar sua solicitação agora.", "acao": None, "dados": {}}

        # 🧼 Se a ação detectada não for de agendamento e havia contexto salvo, limpa tudo
        if resultado.get("acao") not in ["agendar"] and any(
            contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]
        ):
            print("🔄 Ação mudou e há contexto antigo. Limpando contexto.")
            await limpar_contexto(user_id)
            await resetar_sessao(user_id)
            contexto_salvo = {}

        # 🚫 Detecta intenção de cancelamento explícita
        texto_lower = texto_usuario.strip().lower()
        palavras_cancelamento = [
            "cancela", "cancelar", "não quero", "nao quero", "esquece", "deixa pra lá", "deixa pra la",
            "parei", "sai", "não desejo mais", "desisto"
        ]
        if any(p in texto_lower for p in palavras_cancelamento):
            print("🛑 Cancelamento detectado. Limpando contexto.")
            await limpar_contexto_agendamento(user_id)
            await limpar_contexto(user_id)
            await resetar_sessao(user_id)
            contexto_salvo = {}

            return {
                "resposta": "✅ Tudo bem, cancelei o agendamento em andamento. Se precisar de algo, estou aqui!",
                "acao": None,
                "dados": {}
            }

        # ✅ Atualiza data/hora inteligente no contexto se aplicável
        data_inteligente = interpretar_data_e_hora(texto_usuario)
        if data_inteligente:
            nova_data_iso = data_inteligente.replace(second=0, microsecond=0).isoformat()
            if nova_data_iso != contexto_salvo.get("data_hora"):
                contexto_salvo["data_hora"] = nova_data_iso
                print(f"🧠 Data/hora atualizada para: {nova_data_iso}")
                await salvar_contexto_temporario(user_id, contexto_salvo)

        # 🧠 Extração antecipada
        texto_normalizado = unidecode.unidecode(texto_usuario.lower())
        data_hora_detectada = interpretar_data_e_hora(texto_usuario)
        servico_mencionado = None

        for p in contexto.get("profissionais", []):
            for s in p.get("servicos", []):
                if s.lower() in texto_normalizado:
                    servico_mencionado = s.lower()
                    break

        profissional_mencionado = None
        for p in contexto.get("profissionais", []):
            if p["nome"].lower() in texto_normalizado:
                profissional_mencionado = p["nome"]
                break

        # Atualiza contexto
        if profissional_mencionado and not contexto_salvo.get("profissional_escolhido"):
            contexto_salvo["profissional_escolhido"] = profissional_mencionado
        if servico_mencionado and not contexto_salvo.get("servico"):
            contexto_salvo["servico"] = servico_mencionado
        if data_hora_detectada and not contexto_salvo.get("data_hora"):
            contexto_salvo["data_hora"] = data_hora_detectada.replace(second=0, microsecond=0).isoformat()

        await salvar_contexto_temporario(user_id, contexto_salvo)

        # 🗂️ Detectar pedido de todos os preços
        gatilhos_todos_precos = [
            "todos os precos", "traga todos os precos", "mostrar todos os precos",
            "quais os precos", "listar precos", "precos de tudo", "todos precos", "precos completos", "me traga todos os precos",
            "todos os valores", "traga todos os valores", "mostrar todos os valores",
            "quais os valores", "listar valores", "valores de tudo", "todos valores", "valores completos", "me traga todos os valores"
        ]

        pedir_todos_precos = any(
            frase in texto_normalizado for frase in gatilhos_todos_precos
        )

        if pedir_todos_precos:
            print(f"✅ Gatilho acionado para TODOS PREÇOS. Texto: {texto_normalizado}")
            precos_texto = await consultar_todos_precos(user_id)
            return {
                "resposta": precos_texto,
                "acao": "responder_informacao",
                "dados": {}
            }
 
        # 💰 Consulta de preço tratada localmente (sem chamar o GPT)
        menciona_preco = any(
            chave in texto_normalizado for chave in ["preco", "preço", "valor", "custa", "quanto custa"]
        )

        if menciona_preco:
            from services.profissional_service import obter_precos_servico
            from services.normalizacao_service import encontrar_servico_mais_proximo

            if not servico_mencionado:
                servico_mencionado = await encontrar_servico_mais_proximo(texto_usuario, user_id)
                print(f"🔍 Serviço mencionado após normalização: {servico_mencionado}")

            if servico_mencionado:
                if profissional_mencionado:
                    preco = await obter_precos_servico(
                        user_id, servico_mencionado, profissional_mencionado
                    )
                    if preco is not None:
                        try:
                            valor_formatado = f"{float(preco):.2f}"
                        except Exception:
                            valor_formatado = str(preco)
                        resposta = (
                            f"O preço de *{servico_mencionado}* com *{profissional_mencionado}* é R$ {valor_formatado}"
                        )
                    else:
                        resposta = (
                            f"Infelizmente não temos o preço de {servico_mencionado} com {profissional_mencionado} ainda."
                        )
                else:
                    precos = await obter_precos_servico(user_id, servico_mencionado)
                    if not precos:
                        # tenta normalizar o serviço se não encontrou nenhum preço
                        servico_sugerido = await encontrar_servico_mais_proximo(texto_usuario, user_id)
                        if servico_sugerido and servico_sugerido != servico_mencionado:
                            servico_mencionado = servico_sugerido
                            precos = await obter_precos_servico(user_id, servico_mencionado)

                    if precos:
                        resposta = f"Valores de *{servico_mencionado}*:\n"
                        for nome, preco_val in precos.items():
                            try:
                                valor_formatado = f"{float(preco_val):.2f}"
                            except Exception:
                                valor_formatado = str(preco_val)
                            resposta += f"- *{nome}*: R$ {valor_formatado}\n"
                    else:
                        resposta = "Infelizmente não temos esse preço ainda."
            else:
                resposta = "❌ Não consegui identificar o serviço para informar o preço. Você pode tentar reformular a pergunta?"

            await atualizar_contexto(user_id, {"usuario": texto_usuario, "bot": resposta})

            return {
                "resposta": resposta,
                "acao": None,
                "dados": {}
            }

        # 🧠 Verifica se o usuário respondeu com um horário contido nas sugestões anteriores
        if contexto_salvo and contexto_salvo.get("sugestoes") and not contexto_salvo.get("data_hora_confirmada"):
            data_base = contexto_salvo.get("data_hora", "")[:10]
            sugestoes = contexto_salvo.get("sugestoes", [])
            texto_normalizado = unidecode.unidecode(texto_usuario.lower())

            # Tenta extrair horário do texto do usuário
            match_horario = re.search(r"\b(\d{1,2}):(\d{2})\b", texto_normalizado)
            if match_horario and data_base:
                hora_encontrada = match_horario.group(0)  # ex: "08:00"
                for sugestao in sugestoes:
                    if sugestao.startswith(hora_encontrada):
                        nova_data_hora = f"{data_base}T{hora_encontrada}:00"
                        contexto_salvo["data_hora"] = nova_data_hora
                        contexto_salvo["data_hora_confirmada"] = True  # evita substituir depois
                        print(f"🕓 Horário confirmado manualmente: {nova_data_hora}")
                        await salvar_contexto_temporario(user_id, contexto_salvo)
                        break

                print(f"🧠 [DEBUG CONTEXTO] após confirmação manual: {json.dumps(contexto_salvo, indent=2, ensure_ascii=False)}")


        # ⚡ Detecta troca direta para profissional sugerido (ex: "agende com a Carla")
        resposta_direta = texto_usuario.strip().lower()
        texto_normalizado = unidecode.unidecode(resposta_direta)
        alternativa = (contexto_salvo.get("alternativa_profissional") or "").lower() if contexto_salvo else ""

        if alternativa and alternativa in texto_normalizado:
            profissional = alternativa.capitalize()
            contexto_salvo["profissional_escolhido"] = profissional

            servico = contexto_salvo.get("servico")
            data_hora = contexto_salvo.get("data_hora")
            duracao = estimar_duracao(servico)

            if servico and data_hora:
                # ⚠️ Verifica se o novo profissional está realmente disponível no mesmo horário
                from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                data_str = datetime.fromisoformat(data_hora).strftime("%Y-%m-%d")
                hora_str = datetime.fromisoformat(data_hora).strftime("%H:%M")

                conflito = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id,
                    data=data_str,
                    hora_inicio=hora_str,
                    duracao_min=duracao,
                    profissional=profissional,
                    servico=servico
                )

                if not conflito["conflito"]:
                    contexto_salvo.update({
                        "profissional_escolhido": profissional,
                        "evento_criado": True,
                        "ultima_acao": "criar_evento",
                        "ultima_intencao": "criar_evento",
                        "dados_anteriores": {
                            "data_hora": data_hora,
                            "descricao": formatar_descricao_evento(servico, profissional),
                            "duracao": duracao,
                            "profissional": profissional
                        }
                    })
                    await salvar_contexto_temporario(user_id, contexto_salvo)

                    return {
                        "resposta": f"✅ {servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}.",
                        "acao": "criar_evento",
                        "dados": {
                            "profissional": profissional,
                            "servico": servico,
                            "data_hora": data_hora,
                            "duracao": duracao,
                            "descricao": formatar_descricao_evento(servico, profissional)
                        }
                    }
                else:
                    return {
                        "resposta": f"⚠️ {profissional} está ocupado nesse horário. Deseja escolher outro horário ou outra profissional?",
                        "acao": None,
                        "dados": {}
                    }

        # ⚡ Reconhecer respostas curtas de confirmação
        palavras_confirmacao = [
            "confirmar", "pode ser", "pode marcar", "fechar",
            "tá bom", "tudo certo", "ok", "isso", "agendar", "sim", "beleza", "claro",
            "desejo continuar", "quero continuar", "continuar", "vamos continuar"
        ]
        resposta_curta = (
            any(p in resposta_direta for p in palavras_confirmacao)
            and len(resposta_direta.split()) <= 6  # aumentei de 4 para 6 para pegar variações como "desejo continuar agora"
        )

        if resposta_curta and contexto_salvo.get("ultima_acao"):
            print("✅ Detectada confirmação de continuidade.")

            # ✅ Verifica se a última mensagem do BOT foi uma sugestão ou pergunta
            historico = contexto_salvo.get("historico", [])
            if historico:
                ultima_interacao = historico[-1]
                ultima_mensagem_bot = ultima_interacao.get("bot", "").lower()

                print("🧪 [DEBUG] Última mensagem do bot:", ultima_mensagem_bot)

                if any(p in ultima_mensagem_bot for p in [
                    "deseja", "prefere", "posso", "quer que", "confirmar", "gostaria", "agendar", "continuar", "seguir", "fechar", "?", "vamos", "pode"
                ]):
                    print("🧠 Última mensagem do bot indica ação pendente.")
                    print("➡️ Executando ação confirmada:", contexto_salvo.get("ultima_acao"))
                    return await executar_confirmacao_generica(user_id, contexto_salvo)
                else:
                    print("🚫 Última mensagem do bot não parece ser uma sugestão de ação.")
            else:
                print("🚫 Sem histórico suficiente para validar confirmação.")

            # ⛔️ Caso não seja uma resposta a uma sugestão, não executa ação
            return {
                "resposta": "❌ Não entendi o que deseja continuar. Pode repetir o pedido?",
                "acao": None,
                "dados": {}
            }

        # ✅ Verifica se há novos dados antes de seguir
        tem_novos_dados = profissional_mencionado or servico_mencionado or data_hora_detectada

        # Se o usuário não trouxe novos dados, e já temos um contexto anterior incompleto
        if not tem_novos_dados:
            if all(contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]):
                return {
                    "resposta": (
                        f"Você mencionou um {contexto_salvo['servico']} com "
                        f"{contexto_salvo['profissional_escolhido']} para "
                        f"{formatar_data(contexto_salvo['data_hora'])}. "
                        "Deseja confirmar, alterar ou cancelar?"
                    ),
                    "acao": None,
                    "dados": {}
                }
            elif any(contexto_salvo.get(k) for k in ["servico", "data_hora", "profissional_escolhido"]):
                partes = []
                if contexto_salvo.get("servico"):
                    partes.append(f"um {contexto_salvo['servico']}")
                if contexto_salvo.get("profissional_escolhido"):
                    partes.append(f"com {contexto_salvo['profissional_escolhido']}")
                if contexto_salvo.get("data_hora"):
                    partes.append(f"para {formatar_data(contexto_salvo['data_hora'])}")

                resumo = " ".join(partes) if partes else "um agendamento"

                # 🧠 Salva a intenção pendente no contexto
                contexto_salvo["ultima_acao"] = "criar_evento"
                contexto_salvo["ultima_intencao"] = "criar_evento"
                contexto_salvo["dados_anteriores"] = {
                    "profissional": contexto_salvo.get("profissional_escolhido"),
                    "servico": contexto_salvo.get("servico"),
                    "data_hora": contexto_salvo.get("data_hora"),
                    "duracao": estimar_duracao(contexto_salvo.get("servico", ""))
                }
                await salvar_contexto_temporario(user_id, contexto_salvo)
                await limpar_contexto_agendamento(user_id)

                return {
                    "resposta": (
                        f"Você estava iniciando {resumo}. "
                        "Deseja continuar ou começar algo novo?"
                    ),
                    "acao": None,
                    "dados": {}
                }

        #🔒Verifica se há sessão pendente (ex: aguardando_profissional)
        sessao = await pegar_sessao(user_id)
        if sessao and sessao.get("estado") in ["aguardando_profissional", "aguardando_nome_cliente"]:
            resposta = await tratar_mensagem_usuario(user_id, texto_usuario)
            return {
                "resposta": resposta,
                "acao": None,
                "dados": {}
            }

        contexto = contexto or {}  # <- esta linha precisa vir ANTES do .get
        profissionais = contexto.get("profissionais", [])
        texto_normalizado = unidecode.unidecode(texto_usuario.lower())

        # 📋 Verifica se o usuário quer apenas a lista de serviços disponíveis
        intencao_listar_servicos = any(
            chave in texto_normalizado
            for chave in [
                "quais servicos",
                "quais serviços",
                "servicos voce tem",
                "serviços você tem",
                "lista de servicos",
                "lista de serviços",
                "que servicos",
                "que serviços",
            ]
        )
        if intencao_listar_servicos:
            servicos = await listar_servicos_cadastrados(user_id)
            if servicos:
                resposta = "Aqui estão os serviços disponíveis:\n- " + "\n- ".join(servicos)
            else:
                resposta = "Não há serviços cadastrados no momento."
            await atualizar_contexto(
                user_id,
                {"usuario": texto_usuario, "bot": resposta},
            )
            return {"resposta": resposta, "acao": None, "dados": {}}

        # ✅ Atualiza a data/hora com base na nova mensagem, se for diferente
        nova_data = interpretar_data_e_hora(texto_usuario)
        if nova_data:
            nova_data_iso = nova_data.replace(second=0, microsecond=0).isoformat()
            if nova_data_iso != contexto_salvo.get("data_hora"):
                print(f"🆕 Substituindo data/hora antiga ({contexto_salvo.get('data_hora')}) por nova ({nova_data_iso})")
                contexto_salvo["data_hora"] = nova_data_iso
                await salvar_contexto_temporario(user_id, contexto_salvo)

        # ✅ Tenta agendar diretamente se contexto completo
        if all(contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]):
            try:
                profissional = contexto_salvo["profissional_escolhido"]
                servico = contexto_salvo["servico"]
                data_hora = contexto_salvo["data_hora"]

                duracao = estimar_duracao(servico)
                from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                data = datetime.fromisoformat(data_hora).strftime("%Y-%m-%d")
                hora = datetime.fromisoformat(data_hora).strftime("%H:%M")
                
                conflito = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id,
                    data=data,
                    hora_inicio=hora,
                    duracao_min=duracao,
                    profissional=profissional,
                    servico=servico,
                )

                if not conflito["conflito"]:
                    contexto_salvo.update(
                        {
                            "evento_criado": True,
                            "ultima_acao": "criar_evento",
                            "dados_anteriores": {
                                "data_hora": data_hora,
                                "descricao": formatar_descricao_evento(
                                    servico, profissional
                                ),
                                "duracao": duracao,
                                "profissional": profissional,
                            },
                        }
                    )
                    await salvar_contexto_temporario(user_id, contexto_salvo)

                    return {
                        "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                        "acao": "criar_evento",
                        "dados": {
                            "data_hora": data_hora,
                            "descricao": formatar_descricao_evento(
                                servico, profissional
                            ),
                            "duracao": duracao,
                            "profissional": profissional,
                        },
                    }
                else:
                    sugestoes_txt = (
                        "\n".join(f"🔄 {h}" for h in conflito["sugestoes"])
                        if conflito["sugestoes"]
                        else ""
                    )
                    sugestao_formatada = (
                        f"\n\n📌 *Horários disponíveis com {profissional}:*\n{sugestoes_txt}"
                        if sugestoes_txt else ""
                    )
                    alternativa_formatada = (
                        f"\n\n💡 {conflito['profissional_alternativo']} está disponível às {hora}."
                        if conflito.get("profissional_alternativo") else ""
                    )

                    await salvar_contexto_temporario(
                        user_id,
                        {
                            "profissional_escolhido": profissional,
                            "servico": servico,
                            "data_hora": data_hora,
                            "sugestoes": conflito["sugestoes"],
                            "alternativa_profissional": conflito["profissional_alternativo"],
                        },
                    )

                    return {
                        "resposta": (
                            f"⚠️ {profissional} está {adaptar_genero(profissional, 'ocupad')} às {hora}."
                            f"{sugestao_formatada}"
                            f"{alternativa_formatada}"
                            f"\n\nDeseja escolher outro horário com {profissional} ou prefere agendar com {conflito['profissional_alternativo']}?"
                        ),
                        "acao": None,
                        "dados": {},
                    }

            except Exception as e:
                print(f"⚠️ Erro ao tratar fluxo de agendamento automático: {e}")
                return {
                    "resposta": "👋 Como posso te ajudar hoje?",
                    "acao": None,
                    "dados": {}
                }

        # 🔄 Caso esteja no meio de um agendamento, ignora o "oi"
        #else:
        #    return {
        #        "resposta": "🔄 Estamos no meio de um agendamento. Por favor, diga o nome da profissional, a data ou o horário desejado para continuar.",
        #        "acao": None,
        #        "dados": {}
        #    }

        # 🔍 Detecta intenção de listar todos os profissionais
        intencao_listagem_ampla = any(p in texto_normalizado for p in [
            "todos os profissionais", "quem trabalha", "quantas profissionais",
            "quais são as profissionais", "todas as profissionais", "todo mundo que trabalha"
        ])

        # 🔎 Detecta serviço mencionado com base nos serviços disponíveis
        servicos_disponiveis = [s.lower() for p in profissionais for s in p.get("servicos", [])]
        servico_mencionado = None
        for s in servicos_disponiveis:
            if re.search(rf"\b{s.lower()}\b", texto_normalizado):
                servico_mencionado = s.lower()
                break

        data_hora_detectada = interpretar_data_e_hora(texto_usuario)

        # ✅ Aqui: Salva contexto atualizado antes de filtrar profissionais
        memoria_nova = {}

        if servico_mencionado:
            memoria_nova["servico"] = servico_mencionado

        if data_hora_detectada:
            data_hora_iso = data_hora_detectada.replace(second=0, microsecond=0).isoformat()
            if data_hora_iso != contexto_salvo.get("data_hora"):
                memoria_nova["data_hora"] = data_hora_iso

        
        if memoria_nova:
            # 🧼 Remove data_hora antiga se não vier nova
            if "data_hora" in memoria_nova:
                contexto_salvo["data_hora"] = memoria_nova["data_hora"]

            contexto_salvo.update(memoria_nova)
            await salvar_contexto_temporario(user_id, contexto_salvo)
            contexto_salvo = await carregar_contexto_temporario(user_id) or {}
            if contexto_salvo.get("profissional_escolhido"):
                contexto_salvo.pop("ultima_opcao_profissionais", None)

            data_inteligente = interpretar_data_e_hora(texto_usuario)
            if data_inteligente:
                nova_data_iso = data_inteligente.replace(second=0, microsecond=0).isoformat()
                if nova_data_iso != contexto_salvo.get("data_hora"):
                    contexto_salvo["data_hora"] = nova_data_iso
                    print(f"🧠 Data/hora atualizada para: {nova_data_iso}")
                    await salvar_contexto_temporario(user_id, contexto_salvo)

        if contexto_salvo is None:
            contexto_salvo = {}  # 🔧 Garante que temos ao menos um dicionário vazio

        # ✅ Garante que o contexto existe como dicionário
        contexto = contexto or {}

        # 🧠 Decide se filtra ou mantém todos
        if servico_mencionado and not intencao_listagem_ampla:
            profissionais_filtrados = [
                p for p in profissionais
                if servico_mencionado in [s.lower() for s in p.get("servicos", [])]
            ]
        else:
            profissionais_filtrados = profissionais  # Usa todos

        # Se houver um horário detectado, filtre apenas os disponíveis nesse horário
        if contexto_salvo.get("data_hora"):
            from services.event_service_async import verificar_conflito_e_sugestoes_profissional
            data = datetime.fromisoformat(contexto_salvo["data_hora"])
            data_str = data.strftime("%Y-%m-%d")
            hora_str = data.strftime("%H:%M")
            duracao = estimar_duracao(servico_mencionado) if servico_mencionado else 60

            profissionais_disponiveis = []
            for prof in profissionais_filtrados:

                conflito = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id,
                    data=data_str,
                    hora_inicio=hora_str,
                    duracao_min=duracao,
                    profissional=prof["nome"],
                    servico=servico_mencionado or ""
                )
                if not conflito["conflito"]:
                    profissionais_disponiveis.append(prof)

            contexto["profissionais"] = profissionais_disponiveis
        else:
            profissionais_disponiveis = profissionais_filtrados
            contexto["profissionais"] = profissionais_disponiveis

        # ✅ Listagem direta de profissionais
        if intencao_listagem_ampla and profissionais_disponiveis:
            profissionais_formatados = [
                f"- {p['nome']}: {', '.join(p['servicos'])}" for p in profissionais_disponiveis
            ]
            await atualizar_contexto(user_id, {
                "usuario": texto_usuario,
                "bot": "Aqui estão as profissionais cadastradas:\n" + "\n".join(profissionais_formatados)
            })
            return {
                "resposta": "Aqui estão as profissionais cadastradas:\n" + "\n".join(profissionais_formatados),
                "acao": None,
                "dados": {}
            }

        # ✅ Novo: se temos profissionais disponíveis, mas ainda não há um escolhido, sugerimos nomes
        if profissionais_disponiveis and not contexto_salvo.get("profissional_escolhido"):
            servico_para_frase = servico_mencionado or contexto_salvo.get("servico")
    
            if not servico_para_frase:
                return {
                    "resposta": "Para te mostrar os profissionais corretos, qual serviço você deseja?",
                    "acao": "aguardar_servico",
                    "dados": {}
                }

            # 🧠 Atualiza nome do serviço se novo
            if servico_mencionado and contexto_salvo.get("servico") != servico_mencionado:
                contexto_salvo["servico"] = servico_mencionado

            nomes = [p["nome"] for p in profissionais_disponiveis]
            contexto_salvo["ultima_opcao_profissionais"] = nomes

            servico_para_frase = (
                servico_mencionado or contexto_salvo.get("servico")
            ).strip()

            data_hora_str = contexto_salvo.get("data_hora")
            data_formatada = formatar_data(data_hora_str) if data_hora_str else "em breve"

            resposta = f"Temos disponibilidade para {servico_para_frase} {data_formatada}. Deseja ser atendido por {' ou '.join(nomes)}?"

            await atualizar_contexto(user_id, {
                "usuario": texto_usuario,
                "bot": resposta
            })

            await salvar_contexto_temporario(user_id, contexto_salvo)

            return {
                "resposta": resposta,
                "acao": None,
                "dados": {}
            }

        # 🧠 Salva também o serviço mencionado (se houver) para uso posterior
        if servico_mencionado:
            contexto_salvo = await carregar_contexto_temporario(user_id) or {}
            if contexto_salvo.get("profissional_escolhido"):
                contexto_salvo.pop("ultima_opcao_profissionais", None)

            data_inteligente = interpretar_data_e_hora(texto_usuario)
            if data_inteligente:
                nova_data_iso = data_inteligente.replace(second=0, microsecond=0).isoformat()
                if nova_data_iso != contexto_salvo.get("data_hora"):
                    contexto_salvo["data_hora"] = nova_data_iso
                    print(f"🧠 Data/hora atualizada para: {nova_data_iso}")
                    await salvar_contexto_temporario(user_id, contexto_salvo)

        nomes_profissionais = [p["nome"].lower() for p in contexto["profissionais"]]
        resposta_direta = texto_usuario.strip().lower()

        contexto_salvo = await carregar_contexto_temporario(user_id)
        print("📥 Contexto salvo atual:", contexto_salvo)  # 👈 Coloque aqui

        # ✅ Novo: o usuário respondeu diretamente com um nome da última sugestão?
        resposta_direta = texto_usuario.strip().title()
        opcoes_anteriores = contexto_salvo.get("ultima_opcao_profissionais", [])

        if any(resposta_direta.lower() in nome.lower() for nome in opcoes_anteriores):
            profissional = next((n for n in opcoes_anteriores if resposta_direta.lower() in n.lower()), resposta_direta)
            servico = contexto_salvo.get("servico")
            data_hora = contexto_salvo.get("data_hora")
  
            if servico and data_hora:
                duracao = estimar_duracao(servico)
                data_obj = datetime.fromisoformat(data_hora)
                data_str = data_obj.strftime("%Y-%m-%d")
                hora_str = data_obj.strftime("%H:%M")

                from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                conflito = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id,
                    data=data_str,
                    hora_inicio=hora_str,
                    duracao_min=duracao,
                    profissional=profissional,
                    servico=servico
                )

                if conflito["conflito"]:
                    sugestoes = conflito.get("sugestoes", [])
                    alternativa = conflito.get("profissional_alternativo")
                    sugestoes_txt = (
                        "\n".join(f"🔄 {h}" for h in sugestoes)
                        if sugestoes else ""
                    )
                    sugestao_formatada = (
                        f"\n\n📌 *Horários disponíveis com {profissional}:*\n{sugestoes_txt}"
                        if sugestoes_txt else ""
                    )
                    alternativa_formatada = (
                         f"\n\n💡 {alternativa} está disponível às {hora_str}."
                        if alternativa else ""
                    )

                    await salvar_contexto_temporario(user_id, {
                        "profissional_escolhido": profissional,
                        "servico": servico,
                        "data_hora": data_hora,
                        "sugestoes": sugestoes,
                        "alternativa_profissional": alternativa
                    })

                    return {
                        "resposta": (
                            f"⚠️ {profissional} está {adaptar_genero(profissional, 'ocupad')} às {hora_str}."
                            f"{sugestao_formatada}"
                            f"{alternativa_formatada}"
                            f"\n\nDeseja escolher outro horário com {profissional} ou prefere agendar com {alternativa}?"
                        ),
                        "acao": None,
                        "dados": {}
                    }

                # ✅ Se não houver conflito
                await salvar_contexto_temporario(user_id, {
                    "profissional_escolhido": profissional,
                    "servico": servico,
                    "data_hora": data_hora,
                    "evento_criado": True,
                    "ultima_acao": "criar_evento",
                    "ultima_intencao": "criar_evento",
                    "dados_anteriores": {
                        "profissional": profissional,
                        "servico": servico,
                        "data_hora": data_hora,
                        "duracao": duracao
                    }
                })

                
                return {
                    "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                    "acao": "criar_evento",
                    "dados": {
                        "data_hora": data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao,
                        "profissional": profissional
                    }
                }

            else:
                await salvar_contexto_temporario(user_id, {
                    "profissional_escolhido": profissional
                })
                
                return {
                    "resposta": f"Perfeito! {profissional} foi selecionada. Agora diga a data e o horário que você prefere.",
                    "acao": None,
                    "dados": {}
                }

        #⏰ Novo trecho: captura horário direto se já tem profissional e serviço
        hora_encontrada = re.search(
            r'^\s*(\d{1,2})(?:[:h](\d{2}))?\s*$',
            (texto_usuario or "").strip()
        )
        if hora_encontrada:
            hora = int(hora_encontrada.group(1))
            minuto = int(hora_encontrada.group(2) or 0)

            # valida horário
            if 0 <= hora <= 23 and 0 <= minuto <= 59:
                contexto_tmp = await carregar_contexto_temporario(user_id) or {}
                
                dados_ant = contexto_tmp.get("dados_anteriores") or {}

                # ✅ Fallbacks robustos
                profissional = (
                    contexto_tmp.get("profissional_escolhido")
                    or dados_ant.get("profissional")
                )
                servico = (
                    contexto_tmp.get("servico")
                    or dados_ant.get("servico")
                )
                data_hora_antiga = (
                    contexto_tmp.get("data_hora")
                    or dados_ant.get("data_hora")
                )

                # ⏰ Novo trecho: captura horário direto se já tem profissional e serviço
                hora_encontrada = re.search(
                    r'^\s*(\d{1,2})(?:[:h](\d{2}))?\s*$',
                    (texto_usuario or "").strip()
                )
                if hora_encontrada:
                    hora = int(hora_encontrada.group(1))
                    minuto = int(hora_encontrada.group(2) or 0)

                    # valida horário
                    if 0 <= hora <= 23 and 0 <= minuto <= 59:
                        contexto_tmp = await carregar_contexto_temporario(user_id) or {}
                        dados_ant = contexto_tmp.get("dados_anteriores") or {}

                        # ✅ Fallbacks robustos
                        profissional = (
                            contexto_tmp.get("profissional_escolhido")
                            or dados_ant.get("profissional")
                        )
                        servico = (
                            contexto_tmp.get("servico")
                            or dados_ant.get("servico")
                        )
                        data_hora_antiga = (
                            contexto_tmp.get("data_hora")
                            or dados_ant.get("data_hora")
                        )

                        # ✅ Se ainda não tem serviço, tenta derivar da descrição/título (se existir)
                        if not servico:
                            desc = (contexto_tmp.get("descricao") or contexto_tmp.get("titulo") or "")
                            if isinstance(desc, str) and " com " in desc:
                                servico = desc.split(" com ")[0].strip().lower()

                        # ✅ Se faltar algo, devolve agora (antes de qualquer cálculo)
                        if not (profissional and servico and data_hora_antiga):
                            faltando = []
                            if not profissional:
                                faltando.append("profissional")
                            if not servico:
                                faltando.append("serviço")
                            if not data_hora_antiga:
                                faltando.append("data")
                            return {
                                "resposta": f"Para ajustar o horário, falta: {', '.join(faltando)}.",
                                "acao": None,
                                "dados": {}
                            }

                        # ✅ Temos tudo → aplica novo horário mantendo o mesmo dia
                        data_original = datetime.fromisoformat(data_hora_antiga)
                        nova_dt = data_original.replace(hour=hora, minute=minuto, second=0, microsecond=0)
                        nova_data_hora = nova_dt.isoformat()

                        duracao = estimar_duracao(servico)

                        from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                        data_str = nova_dt.strftime("%Y-%m-%d")
                        hora_str = nova_dt.strftime("%H:%M")

                        conflito = await verificar_conflito_e_sugestoes_profissional(
                            user_id=user_id,
                            data=data_str,
                            hora_inicio=hora_str,
                            duracao_min=duracao,
                            profissional=profissional,
                            servico=servico
                        )

                        if conflito.get("conflito"):
                            sugestoes = conflito.get("sugestoes", [])
                            alternativa = conflito.get("profissional_alternativo")

                            sugestoes_txt = "\n".join(f"🔄 {h}" for h in sugestoes) if sugestoes else ""
                            sugestao_formatada = (
                                f"\n\n📌 *Horários disponíveis com {profissional}:*\n{sugestoes_txt}"
                                if sugestoes_txt else ""
                            )
                            alternativa_formatada = (
                                f"\n\n💡 {alternativa} está disponível às {hora_str}."
                                if alternativa else ""
                            )

                            await salvar_contexto_temporario(user_id, {
                                "profissional_escolhido": profissional,
                                "servico": servico,
                                "data_hora": nova_data_hora,  # mantém o dia e troca só a hora
                                "sugestoes": sugestoes,
                                "alternativa_profissional": alternativa,
                                "ultima_acao": "criar_evento",
                                "ultima_intencao": "criar_evento",
                                "dados_anteriores": {
                                    "profissional": profissional,
                                    "servico": servico,
                                    "data_hora": nova_data_hora,
                                    "duracao": duracao
                                }
                            })

                            return {
                                "resposta": (
                                    f"⚠️ {profissional} está {adaptar_genero(profissional, 'ocupad')} às {hora_str}."
                                    f"{sugestao_formatada}"
                                    f"{alternativa_formatada}"
                                    f"\n\nDeseja escolher outro horário com {profissional} ou prefere agendar com {alternativa}?"
                                ),
                                "acao": None,
                                "dados": {}
                            }

                        # ✅ sem conflito → já pode criar
                        await salvar_contexto_temporario(user_id, {
                            "profissional_escolhido": profissional,
                            "servico": servico,
                            "data_hora": nova_data_hora,
                            "evento_criado": True,
                            "ultima_acao": "criar_evento",
                            "ultima_intencao": "criar_evento",
                            "dados_anteriores": {
                                "profissional": profissional,
                                "servico": servico,
                                "data_hora": nova_data_hora,
                                "duracao": duracao
                            }
                        })

                        return {
                            "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(nova_data_hora)}. ✂️",
                            "acao": "criar_evento",
                            "dados": {
                                "data_hora": nova_data_hora,
                                "descricao": formatar_descricao_evento(servico, profissional),
                                "duracao": duracao,
                                "profissional": profissional
                            }
                        }

        # 🎯 Verifica se a resposta menciona diretamente um profissional
        texto_normalizado = unidecode.unidecode(resposta_direta.lower())

        for prof in nomes_profissionais:
            prof_normalizado = unidecode.unidecode(prof.lower())

            # Permite detectar frases como "pela Carla", "com a Carla", "Carla"
            if re.search(rf"\b(pela|com|com a|a|para|por)?\s*{prof_normalizado}\b", texto_normalizado):
                contexto_salvo["profissional_escolhido"] = prof.capitalize()
                opcoes_disponiveis = contexto_salvo.get("ultima_opcao_profissionais") or []

                # 🔁 Fallback inteligente: se não houver lista, usa alternativa_profissional
                if not opcoes_disponiveis and contexto_salvo.get("alternativa_profissional"):
                    opcoes_disponiveis = [contexto_salvo["alternativa_profissional"]]

                servico = contexto_salvo.get("servico")
                data_hora = contexto_salvo.get("data_hora")

                print(f"🔍 Verificação de dados: profissional={prof.capitalize()}, servico={servico}, data_hora={data_hora},    opções={opcoes_disponiveis}")

                if prof.capitalize() in opcoes_disponiveis and servico and data_hora:
                    duracao = estimar_duracao(servico)
                    await salvar_contexto_temporario(user_id, {
                        "profissional_escolhido": prof.capitalize(),
                        "servico": servico,
                        "data_hora": data_hora,
                        "evento_criado": True
                    })
                    await limpar_contexto_agendamento(user_id)
                    return {
                        "resposta": f"{servico.capitalize()} agendado com {prof.capitalize()} para {formatar_data(data_hora)}. ✂️",
                        "acao": "criar_evento",
                        "dados": {
                            "data_hora": data_hora,
                            "descricao": f"{servico} com {prof.capitalize()}",
                            "duracao": duracao
                        }
                    }
                else:
                    # 🧠 Salva o profissional escolhido e tenta completar depois
                    await salvar_contexto_temporario(user_id, {"profissional_escolhido": prof.capitalize()})
                    contexto_salvo = await carregar_contexto_temporario(user_id)

                    if contexto_salvo.get("evento_criado") and not contexto_salvo.get("ultima_acao"):
                        await limpar_contexto_agendamento(user_id)
                        return {
                            "resposta": "✅ O agendamento anterior foi registrado com sucesso. Podemos seguir com outro pedido?",
                            "acao": None,
                            "dados": {}
                        }

                    profissional = contexto_salvo.get("profissional_escolhido")
                    servico = contexto_salvo.get("servico")
                    data_hora = contexto_salvo.get("data_hora")

                    if profissional and servico and data_hora:
                        duracao = estimar_duracao(servico)
                        await salvar_contexto_temporario(user_id, {"evento_criado": True})
                        await limpar_contexto_agendamento(user_id)
                        return {
                            "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                            "acao": "criar_evento",
                            "dados": {
                                "data_hora": data_hora,
                                "descricao": formatar_descricao_evento(servico, profissional),
                                "duracao": duracao
                            }
                        }

        # 🔍 Garante que os dados do cliente estejam no contexto
        cliente = await buscar_cliente(user_id)
        if cliente:
            contexto["usuario"] = cliente
            contexto["pagamentoAtivo"] = cliente.get("pagamentoAtivo", False)
            contexto["planosAtivos"] = cliente.get("planosAtivos", [])

            # ✅ Força: se já temos serviço, filtra profissionais aptos ANTES do GPT
            try:
                servico_ctx = (contexto_salvo or {}).get("servico") or (contexto or {}).get("servico")
                servico_ctx = (servico_ctx or "").strip()

                if servico_ctx:
                    profs_brutos = (contexto or {}).get("profissionais") or []
                    aptos = []
                    for p in profs_brutos:
                        if not isinstance(p, dict):
                            continue
                        nome = (p.get("nome") or "").strip()
                        servs = p.get("servicos") or []
                        servs_norm = {unidecode.unidecode(str(s).lower().strip()) for s in servs}
                        if unidecode.unidecode(servico_ctx.lower().strip()) in servs_norm:
                            aptos.append(p)

                    # Se encontrou aptos, substitui a lista enviada ao GPT
                    if aptos:
                        contexto["profissionais"] = aptos

                        # salva opções para travar "terceira opção"
                        opcoes = [p.get("nome") for p in aptos if isinstance(p, dict) and p.get("nome")]
                        if uid != "desconhecido":
                            await salvar_contexto_temporario(uid, {"ultima_opcao_profissionais": opcoes})

                        print(f"✅ Profissionais aptos para '{servico_ctx}': {opcoes}", flush=True)
                    else:
                        # Se não há aptos, salva lista vazia para não inventar
                        contexto["profissionais"] = []
                        if uid != "desconhecido":
                            await salvar_contexto_temporario(uid, {"ultima_opcao_profissionais": []})
                        print(f"⚠️ Nenhum profissional apto encontrado para '{servico_ctx}'", flush=True)

            except Exception as e:
                print(f"⚠️ Falha ao filtrar profissionais por serviço: {e}", flush=True)

            messages = montar_prompt_com_contexto(INSTRUCAO_SECRETARIA, contexto, contexto_salvo, texto_usuario)

            # ✅ (1) FILTRO + TRAVA antes de montar messages
            try:
                servico_ctx = (contexto_salvo or {}).get("servico")
                profs = (contexto or {}).get("profissionais") or []

                # Filtra somente se tiver serviço e a estrutura for lista de dicts
                if servico_ctx and isinstance(profs, list):
                    servico_norm = str(servico_ctx).strip().lower()
                    profs_filtrados = []

                    for p in profs:
                        if not isinstance(p, dict):
                            continue
                        servs = p.get("servicos") or []

                        # normaliza servicos para lista
                        if isinstance(servs, str):
                            servs = [servs]

                        servs_norm = [str(s).strip().lower() for s in servs if s]

                        if any(servico_norm == s or servico_norm in s or s in servico_norm for s in servs_norm):
                            profs_filtrados.append(p)

                    # substitui no contexto (isso é o que o prompt builder deve usar)
                    contexto["profissionais"] = profs_filtrados

                    # trava a lista permitida (pra não aceitar "terceira opção")
                    nomes_ok = [p.get("nome") for p in profs_filtrados if isinstance(p, dict) and p.get("nome")]
                    contexto_salvo["ultima_opcao_profissionais"] = nomes_ok

                # 🧾 (2) AUDITORIA: agora sim prova do que VAI para o prompt
                profs_final = (contexto or {}).get("profissionais") or []
                nomes = []
                for p in profs_final:
                    if isinstance(p, dict) and p.get("nome"):
                        nomes.append(p.get("nome"))

                print(
                    "🧾 [CTX->GPT] "
                    f"uid={user_id} "
                    f"id_negocio={(contexto.get('usuario') or {}).get('id_negocio')} "
                    f"servico={(contexto_salvo or {}).get('servico')} "
                    f"data_hora={(contexto_salvo or {}).get('data_hora')} "
                    f"prof_escolhido={(contexto_salvo or {}).get('profissional_escolhido')} "
                    f"profs={len(profs_final)} "
                    f"nomes={nomes} "
                    f"ultima_opcao_profissionais={(contexto_salvo or {}).get('ultima_opcao_profissionais')}",
                    flush=True
                )
            except Exception as e:
                print(f"⚠️ Falha no filtro/auditoria CTX->GPT: {e}", flush=True)

            # ✅ (3) Só agora monta messages
            messages = montar_prompt_com_contexto(INSTRUCAO_SECRETARIA, contexto, contexto_salvo, texto_usuario)

            # ✅ (4) Marca a chamada (pra detectar duplicação)
            print(f"🤖 [GPT CALL] linha=1314 uid={user_id} texto={texto_usuario!r}", flush=True)

            resposta = await client.chat.completions.create(
                model="gpt-4o",
                temperature=0.4,
                messages=messages
            )

            firestore_client = firestore.client()
            await registrar_custo_gpt(resposta, "gpt-4o", user_id, firestore_client)
 
            try:
                conteudo = resposta.choices[0].message.content
                if conteudo:
                    conteudo = conteudo.strip()
                else:
                    raise ValueError("Conteúdo da resposta do GPT veio vazio.")

                print("📨 Conteúdo bruto do GPT:\n", conteudo)

                if "{" in conteudo and "}" in conteudo:
                    inicio = conteudo.index("{")
                    fim = conteudo.rindex("}")
                    json_puro = conteudo[inicio:fim + 1]
                else:
                    raise ValueError("JSON mal formado: delimitadores '{' ou '}' ausentes.")

                resultado = json.loads(json_puro)

            except Exception as e:
                print("🛑 Erro ao interpretar resposta do GPT:")
                print(f"❗ Tipo de erro: {type(e).__name__}")
                print(f"❗ Erro: {e}")
                print("📦 Objeto de resposta bruto:")
                print(resposta.model_dump_json(indent=2, ensure_ascii=False))

                return {
                    "resposta": "❌ A IA respondeu fora do formato esperado. Pode reformular a pergunta?",
                    "acao": None,
                    "dados": {}
                }

            # 🟡 Salve também o serviço e a data_hora se existirem, mesmo que estejam fora de 'dados'
            if "descricao" in resultado.get("dados", {}):
                descricao = resultado["dados"]["descricao"].lower()
                if "com" in descricao:
                    servico_detectado = descricao.split("com")[0].strip()
                    memoria_nova["servico"] = servico_detectado
                else:
                    memoria_nova["servico"] = descricao

            if "data_hora" in resultado.get("dados", {}):
                memoria_nova["data_hora"] = resultado["dados"]["data_hora"]

            # ✅ Verifica se já temos os 3 elementos e agenda diretamente
            profissional = memoria_nova.get("profissional_escolhido") or contexto_salvo.get("profissional_escolhido")
            servico = memoria_nova.get("servico") or contexto_salvo.get("servico")
            data_hora = memoria_nova.get("data_hora") or contexto_salvo.get("data_hora")

            if (
                profissional
                and servico
                and data_hora
                and not contexto_salvo.get("sugestoes")
                and not contexto_salvo.get("alternativa_profissional")
            ):
                duracao = estimar_duracao(servico)

                await salvar_contexto_temporario(user_id, {
                    "evento_criado": True,
                    "ultima_acao": "criar_evento",
                    "ultima_intencao": "criar_evento",
                    "dados_anteriores": {
                        "data_hora": data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao,
                        "profissional": profissional
                    }
                })

                return {
                    "resposta": f"{servico.capitalize()} agendado com {profissional} para {formatar_data(data_hora)}. ✂️",
                    "acao": "criar_evento",
                    "dados": {
                        "data_hora": data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao,
                        "profissional": profissional
                    }
                }

            # 🛡️ Protege contra acionamento incorreto de "consultar_preco_servico"
            texto_normalizado = unidecode.unidecode(texto_usuario.lower())
            menciona_preco = any(p in texto_normalizado for p in ["preco", "preço", "valor", "quanto", "custa"])

            # ⚠️ Corrige interpretação automática mal feita
            if resultado.get("acao") == "consultar_preco_servico" and not menciona_preco:
                resultado["acao"] = None
                resultado["dados"] = {}

            # ✅ Se não veio ação mas mencionou um serviço e a intenção foi clara de preço, força como consulta
            elif resultado.get("acao") is None and servico_mencionado and menciona_preco:
                resultado["acao"] = "consultar_preco_servico"
                resultado["dados"] = {"servico": servico_mencionado}

            memoria_nova = {}

            # 🧩 Correção automática se o GPT ignorar profissionais do contexto
            intencao_listagem_ampla = any(p in texto_usuario.lower() for p in [
                "todos os profissionais", "quem trabalha", "quantas profissionais",
                "quais são as profissionais", "todas as profissionais", "todo mundo que trabalha"
            ])

            if (
                intencao_listagem_ampla
                and contexto.get("profissionais")
                and not resultado.get("acao")
                and not resultado.get("resposta")
            ):

                profissionais_formatados = [
                    f"- {p['nome']}: {', '.join(p['servicos'])}" for p in contexto["profissionais"]
                ]
                resultado["resposta"] = "Aqui estão as profissionais cadastradas:\n" + "\n".join(profissionais_formatados)
                resultado["acao"] = None
                resultado["dados"] = {}

            if "profissional" in resultado.get("dados", {}):
                memoria_nova["profissional_escolhido"] = resultado["dados"]["profissional"]

            if "data_hora" in resultado.get("dados", {}):
                memoria_nova["data_hora"] = resultado["dados"]["data_hora"]

            # Verificar se a resposta contém algum nome de profissional
            nomes_validos = [p["nome"] for p in contexto.get("profissionais", [])]
            nomes_mencionados = []
            if "resposta" in resultado:
                nomes_mencionados = [nome for nome in nomes_validos if nome.lower() in resultado["resposta"].lower()]

            # Detectar intenção de listagem ampla (não salvar profissional nesse caso)
            intencao_listagem_ampla = any(p in texto_usuario.lower() for p in [
                "todos os profissionais", "quem trabalha", "quantas profissionais",
                "quais são as profissionais", "todas as profissionais", "todo mundo que trabalha"
            ])

            # Salvar profissional escolhido se:
            # 1. Só um nome foi mencionado E
            # 2. Não é uma listagem ampla
            # OU
            # 3. O nome mencionado estava na última listagem (continuidade de atendimento)
            if (
                len(nomes_mencionados) == 1 and not intencao_listagem_ampla
            ) or (
                len(nomes_mencionados) == 1
                and "ultima_opcao_profissionais" in contexto
                and nomes_mencionados[0] in contexto["ultima_opcao_profissionais"]
            ):
                memoria_nova["ultima_opcao_profissionais"] = [nomes_mencionados[0]]
                memoria_nova["profissional_escolhido"] = nomes_mencionados[0]

            # 🟡 Salve também o serviço e a data_hora se existirem, mesmo que estejam fora de 'dados'
            if "descricao" in resultado.get("dados", {}):
                descricao = resultado["dados"]["descricao"]
                memoria_nova["servico"] = descricao.split(" com ")[0].strip().lower()

            if "data_hora" in resultado.get("dados", {}):
                memoria_nova["data_hora"] = resultado["dados"]["data_hora"]


            # ✅ Antes de salvar, verifique se já dá para agendar
            profissional = memoria_nova.get("profissional_escolhido") or contexto_salvo.get("profissional_escolhido")
            servico = memoria_nova.get("servico") or contexto_salvo.get("servico")
            data_hora = memoria_nova.get("data_hora") or contexto_salvo.get("data_hora")

            if profissional and servico and data_hora:
                duracao = estimar_duracao(servico)
                start_dt = datetime.fromisoformat(data_hora)
                data = start_dt.strftime("%Y-%m-%d")
                hora = start_dt.strftime("%H:%M")

                from services.event_service_async import verificar_conflito_e_sugestoes_profissional
                conflito_info = await verificar_conflito_e_sugestoes_profissional(
                    user_id=user_id,
                    data=data,
                    hora_inicio=hora,
                    duracao_min=duracao,
                    profissional=profissional,
                    servico=servico
                )

                if conflito_info["conflito"]:
                    sugestoes = conflito_info.get("sugestoes", [])
                    alternativa = conflito_info.get("profissional_alternativo")
                    sugestoes_txt = (
                        "\n".join(f"🔄 {h}" for h in sugestoes)
                        if sugestoes else ""
                    )
                    sugestao_formatada = (
                        f"\n\n📌 *Horários disponíveis com {profissional}:*\n{sugestoes_txt}"
                        if sugestoes_txt else ""
                    )
                    alternativa_formatada = (
                        f"\n\n💡 {alternativa} está disponível às {hora}."
                        if alternativa else ""
                    )

                    await salvar_contexto_temporario(user_id, {
                        "profissional_escolhido": profissional,
                        "servico": servico,
                        "data_hora": data_hora,
                        "sugestoes": sugestoes,
                        "alternativa_profissional": alternativa
                    })

                    resultado = {
                        "resposta": (
                            f"⚠️ {profissional} está {adaptar_genero(profissional, 'ocupad')} às {hora}."
                            f"{sugestao_formatada}"
                            f"{alternativa_formatada}"
                            f"\n\nDeseja escolher outro horário com {profissional} ou prefere agendar com {alternativa}?"
                        ),
                        "acao": None,
                        "dados": {}
                    }
                    return resultado

                else:
                    resultado["acao"] = "criar_evento"
                    resultado["dados"] = {
                        "data_hora": data_hora,
                        "descricao": formatar_descricao_evento(servico, profissional),
                        "duracao": duracao
                    }

            # ✅ Salvar tudo junto
            if memoria_nova:
                contexto_salvo = await carregar_contexto_temporario(user_id) or {}
                if contexto_salvo.get("profissional_escolhido"):
                    contexto_salvo.pop("ultima_opcao_profissionais", None)

                data_inteligente = interpretar_data_e_hora(texto_usuario)
                if data_inteligente:
                    nova_data_iso = data_inteligente.replace(second=0, microsecond=0).isoformat()
                    if nova_data_iso != contexto_salvo.get("data_hora"):
                        contexto_salvo["data_hora"] = nova_data_iso
                        print(f"🧠 Data/hora atualizada para: {nova_data_iso}")
                        await salvar_contexto_temporario(user_id, contexto_salvo)

                contexto_salvo.update(memoria_nova)
                await salvar_contexto_temporario(user_id, contexto_salvo)

            # 🔧 Adiciona sugestão de profissionais compatíveis com o serviço, se for o caso
            if (
                servico_mencionado
                and resultado.get("acao") not in ["criar_evento", "consultar_preco_servico"]
                and resultado.get("resposta")
                and contexto.get("profissionais")
            ):
                profissionais_compativeis = []
                for p in contexto["profissionais"]:
                    servicos = [s.lower() for s in p.get("servicos", []) if isinstance(s, str)]
                    if servico_mencionado in servicos:
                        profissionais_compativeis.append(p["nome"])

                if profissionais_compativeis:
                    profissionais_compativeis = list(set(profissionais_compativeis))  # remove duplicados
                    nomes_formatados = ", ".join(profissionais_compativeis)

                    resposta_atual = resultado["resposta"].strip().lower()

                    # ✅ Evita repetir se nomes já estiverem mencionados
                    nomes_ja_mencionados = all(
                        nome.lower() in resposta_atual for nome in profissionais_compativeis
                    )

                    if not nomes_ja_mencionados:
                        resposta_base = resultado["resposta"].strip()

                        # Remove final padrão do GPT se existir
                        resposta_base = re.sub(
                            r"deseja ser atendido por.*?$", "", resposta_base, flags=re.IGNORECASE
                        ).strip()

                        nova_resposta = f"{resposta_base} Deseja ser atendido por {nomes_formatados}?"
                        resultado["resposta"] = nova_resposta

                    if (
                        servico_mencionado
                        and data_hora_detectada
                        and contexto["profissionais"]  # se houver sugestões reais
                    ):
                        await salvar_contexto_temporario(user_id, {
                            "servico": servico_mencionado,
                            "data_hora": data_hora_detectada.isoformat(),
                            "ultima_acao": "criar_evento",
                            "ultima_intencao": "criar_evento",
                            "dados_anteriores": {
                                "data_hora": data_hora_detectada.isoformat(),
                                "duracao": estimar_duracao(servico_mencionado),
                                "descricao": f"{servico_mencionado.capitalize()} com ...",  # incompleto
                                "profissional": None  # aguarda o usuário escolher
                            },
                            "ultima_opcao_profissionais": [p["nome"] for p in contexto["profissionais"]]
                        })


            if resultado.get("acao") and resultado.get("dados"):
                await salvar_contexto_temporario(user_id, {
                    "ultima_acao": resultado["acao"],
                    "dados_anteriores": resultado["dados"],
                    "ultima_intencao": resultado.get("acao")  # 👈 mesma ação por padrão
                })
                if resultado["acao"] == "criar_evento":
                    await limpar_contexto_agendamento(user_id)  # ✅ ADICIONE AQUI

            # 🧠 Se houver intenção nova e não estiver em meio a execução de ação, pode limpar contexto
            if resultado.get("acao") is None and intencao not in ["AGENDAR", "DESCONHECIDO"]:
                if any(contexto_salvo.get(k) for k in ["profissional_escolhido", "servico", "data_hora"]):
                    print("🧹 Mudança de assunto detectada sem ação pendente. Limpando contexto.")
                    await limpar_contexto(user_id)
                    await resetar_sessao(user_id)
                    contexto_salvo = {}

             # ✅ Verificações finais após processar toda a lógica principal
            if contexto_salvo.get("evento_criado") and not contexto_salvo.get("ultima_acao"):
                await limpar_contexto_agendamento(user_id)

                return {
                    "resposta": "👋 Olá! Em que mais posso te ajudar hoje?",
                    "acao": None,
                    "dados": {}
                }

            elif any(contexto_salvo.get(k) for k in ["servico", "data_hora", "profissional_escolhido"]):
                return {
                    "resposta": "😊 Podemos continuar de onde paramos. Deseja confirmar o profissional ou horário?",
                    "acao": None,
                    "dados": {}
                }

            return resultado

    except json.JSONDecodeError:
        return {
            "resposta": "❌ A IA respondeu fora do formato esperado.",
            "acao": None,
            "dados": {}
        }
    except Exception as e:
        print(f"❌ Erro em processar_com_gpt_com_acao: {e}")
        traceback.print_exc()
        return {
            "resposta": "❌ Ocorreu um erro ao tentar entender seu pedido.",
            "acao": None,
            "dados": {}
        }

from services.firebase_service_async import buscar_cliente

# ✅ Organização da semana (com dados de plano no prompt)
async def organizar_semana_com_gpt(tarefas: list, eventos: list, user_id: str, dia_inicio: str = "hoje"):
    try:
        hoje = datetime.now().date()

        dias_formatados = [
            (hoje + timedelta(days=i)).strftime("%A (%d/%m)") for i in range(5)
        ]

        # 🔍 Busca dados do cliente
        cliente = await buscar_cliente(user_id)
        pagamento_ativo = cliente.get("pagamentoAtivo", False) if cliente else False
        planos_ativos = cliente.get("planosAtivos", []) if cliente else []

        # 🧠 Prompt completo com contexto
        prompt = f"""
📌 Plano ativo: {pagamento_ativo}
🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}

Você é uma assistente virtual especializada em produtividade e organização semanal.

Ajude o usuário a planejar os próximos 5 dias, a partir de hoje: *{hoje.strftime("%A (%d/%m)")}.*  
Use os dias reais a seguir:

{chr(10).join(f"- {dia}" for dia in dias_formatados)}

Com base nas tarefas e eventos abaixo, distribua as atividades de forma inteligente e priorize o que é mais importante primeiro.

- Use título com o dia da semana e data. Ex: 📅 Sexta-feira (11/04)
- Organize os itens como: tarefas primeiro, eventos depois.
- Use emojis para dar destaque.
- Seja objetiva e evite texto explicativo.

Tarefas:
{chr(10).join(f"- {t}" for t in tarefas) or 'Nenhuma'}

Eventos:
{chr(10).join(f"- {e}" for e in eventos) or 'Nenhum'}

Responda apenas com o plano formatado.
"""
        # ✅ Identificador único do bloco (para diagnóstico)
        print(f"🔀 [REDIRECT] BLOCO-B@1751 -> processar_com_gpt_com_acao user_id={user_id}", flush=True)

        # Usa texto_usuario se existir; caso contrário, usa o prompt como fallback
        texto_base = texto_usuario if "texto_usuario" in locals() and texto_usuario else prompt

        resultado = await processar_com_gpt_com_acao(
            texto_usuario=texto_base,
            contexto=contexto if "contexto" in locals() and contexto else {},
            instrucao=INSTRUCAO_SECRETARIA,
            user_id=user_id,
        )

        if isinstance(resultado, dict):
            return (resultado.get("resposta") or "").strip()

        return str(resultado).strip()

    except Exception as e:
        print(f"[GPT] Erro ao organizar semana: {e}", flush=True)
        return "❌ Houve um erro ao tentar planejar sua semana."