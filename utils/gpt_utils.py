#gpt utils
import json
import re
from datetime import datetime
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA


def montar_prompt_com_contexto(instrucao, contexto, contexto_salvo, texto_usuario):
    # --- Coleta segura do contexto ---
    usuario = contexto.get("usuario", {}) or {}
    profissionais = contexto.get("profissionais", []) or []
    tarefas = contexto.get("tarefas", []) or []
    eventos = contexto.get("eventos", []) or []
    emails = contexto.get("emails", []) or []

    # Flags de plano (já devem ter sido forçadas previamente para evitar bloqueio)
    pagamento_ativo = bool(contexto.get("pagamentoAtivo", usuario.get("pagamentoAtivo", True)))
    planos_ativos = list(set((contexto.get("planosAtivos") or usuario.get("planosAtivos") or []) + ["secretaria"]))

    # --- Resumos enxutos para não inflar tokens ---
    prof_nomes = [p.get("nome") for p in profissionais if isinstance(p, dict) and p.get("nome")]
    resumo_prof = ", ".join(prof_nomes[:12]) + (", ..." if len(prof_nomes) > 12 else "")
    resumo_tarefas = [str(t) for t in (tarefas[:12])]
    resumo_eventos = [str(e) for e in (eventos[:12])]
    resumo_emails = [str(e) for e in (emails[:6])]

    # Contexto salvo relevante (apenas chaves úteis)
    ctx_tmp_keys = ["servico", "data_hora", "profissional_escolhido", "ultima_acao", "evento_criado"]
    ctx_tmp = {k: contexto_salvo.get(k) for k in ctx_tmp_keys if k in contexto_salvo}

    # --- Regras de sistema (ANTI-BLOQUEIO + formato JSON) ---
    regras_antibloqueio = (
        "REGRAS IMPORTANTES SOBRE PLANO/LICENÇA:\n"
        "- Nunca diga que o plano está inativo ou bloqueie ações por causa de plano.\n"
        "- Sempre ASSUMA que o plano está ativo e prossiga normalmente com o pedido.\n"
        "- Você SEMPRE pode executar ações de agenda/tarefas/relatórios/e-mail.\n"
        "- Se faltar algum dado, solicite de forma breve e continue o fluxo.\n"
        "\nFORMATO DE SAÍDA:\n"
        'Responda SEMPRE em JSON puro (sem markdown, sem texto extra), no formato:\n'
        '{"resposta": "<texto ao usuário>", "acao": "<nome_acao_ou_null>", "dados": { ... }}\n'
        "- Use null em \"acao\" quando não houver ação a executar.\n"
    )

    system_msg = {
        "role": "system",
        "content": f"{instrucao}\n\n{regras_antibloqueio}"
    }

    # --- Mensagem de contexto para a IA (sem mencionar plano inativo) ---
    contexto_assistant = {
        "role": "assistant",
        "content": (
            "📌 CONTEXTO ATUAL DO ATENDIMENTO\n"
            f"- Pagamento ativo (assumido): {str(pagamento_ativo)}\n"
            f"- Módulos ativos (assumidos): {', '.join(sorted(set(str(p).lower() for p in planos_ativos)))}\n"
            f"- Tipo de negócio: {usuario.get('tipo_negocio') or usuario.get('tipoNegocio') or 'não informado'}\n"
            f"- Profissionais: {resumo_prof or 'nenhum'}\n"
            f"- Tarefas (amostra): {', '.join(resumo_tarefas) or 'nenhuma'}\n"
            f"- Eventos (amostra): {', '.join(resumo_eventos) or 'nenhum'}\n"
            f"- E-mails (amostra): {', '.join(resumo_emails) or 'nenhum'}\n"
            f"- Contexto temporário: {ctx_tmp or '{}'}\n"
            "\nLembrete: execute o fluxo solicitado sem bloquear por plano."
        )
    }

    # --- Mensagem do usuário ---
    user_msg = {
        "role": "user",
        "content": texto_usuario or ""
    }

    # Retorna a lista de mensagens para o chat.completions
    return [system_msg, contexto_assistant, user_msg]

"📌 CONTEXTO ATUAL DO ATENDIMENTO:"

f"📅 Data atual: {datetime.now().strftime('%Y-%m-%d')}"
"👤 Nome: {usuario.get('nome', 'Desconhecido')}"
"📌 Plano ativo: {pagamento_ativo}"
"🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}"
"🏢 Tipo de negócio: {usuario.get('tipo_negocio', usuario.get('tipoNegocio', 'não informado'))}"
"🧑‍💼 Profissionais: {', '.join(profissionais) or 'Nenhum'}"

"📋 Tarefas:"
{chr(10).join(f"- {t}" for t in tarefas) or 'Nenhuma'}

"📆 Eventos:"
{chr(10).join(f"- {e}" for e in eventos) or 'Nenhum'}

"📧 E-mails:"
{chr(10).join(f"- {e}" for e in emails) or 'Nenhum'}

"📂 Contexto salvo:"
{json.dumps(contexto_salvo or {}, indent=2, ensure_ascii=False)}

"🗣️ Mensagem do usuário:"
\"{texto_usuario}\"
"""}]


def formatar_descricao_evento(servico: str, profissional: str) -> str:
    """Remove duplicação de nomes no serviço e formata a descrição."""
    servico_limpo = re.sub(
        rf"\bcom\s+{re.escape(profissional)}\b",
        "",
        servico,
        flags=re.IGNORECASE,
    ).strip()
    return f"{servico_limpo.capitalize()} com {profissional}"


def estimar_duracao(servico):
    mapa = {"corte": 30, "escova": 40, "coloração": 90}
    return mapa.get(servico.lower(), 60)


def formatar_data(data_iso):
    try:
        dt = datetime.fromisoformat(data_iso)
        return dt.strftime("dia %d/%m às %H:%Mh")
    except Exception:
        return data_iso


def limpar_nome_duplicado(resposta, nomes):
    for nome in nomes:
        padrao = rf"(\b{re.escape(nome)}\b[,\s]*)+"
        resposta = re.sub(padrao, f"{nome}, ", resposta, flags=re.IGNORECASE)
    return re.sub(r",\s*,", ",", resposta).strip(", ").strip()