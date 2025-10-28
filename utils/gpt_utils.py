# gpt_utils.py
import json
import re
from datetime import datetime
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA


def montar_prompt_com_contexto(instrucao, contexto, contexto_salvo, texto_usuario):
    """
    Monta o prompt para o modelo com:
      - Mensagem de sistema (instrução + regras anti-bloqueio)
      - Um resumo de contexto como 'assistant' (sem travar por plano)
      - A mensagem do usuário
    Retorna uma lista de mensagens compatível com chat.completions.
    """

    # --- Coleta segura do contexto ---
    usuario = contexto.get("usuario", {}) or {}
    profissionais = contexto.get("profissionais", []) or []
    tarefas = contexto.get("tarefas", []) or []
    eventos = contexto.get("eventos", []) or []
    emails = contexto.get("emails", []) or []

    # Flags de plano (se não vierem, assumimos ativo e com 'secretaria')
    pagamento_ativo = bool(contexto.get("pagamentoAtivo", usuario.get("pagamentoAtivo", True)))
    planos_ativos = list(
        set((contexto.get("planosAtivos") or usuario.get("planosAtivos") or []) + ["secretaria"])
    )

    # --- Resumos enxutos para não inflar tokens ---
    # profissionais pode ser lista de dicts, strings ou mista
    prof_nomes = []
    for p in profissionais:
        if isinstance(p, dict) and p.get("nome"):
            prof_nomes.append(str(p["nome"]))
        elif isinstance(p, str):
            prof_nomes.append(p.strip())
    resumo_prof = ", ".join(prof_nomes[:12]) + (", ..." if len(prof_nomes) > 12 else "")

    resumo_tarefas = [str(t) for t in tarefas[:12]]
    resumo_eventos = [str(e) for e in eventos[:12]]
    resumo_emails = [str(e) for e in emails[:6]]

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
        '- Use null em "acao" quando não houver ação a executar.\n'
    )

    system_msg = {
        "role": "system",
        "content": f"{instrucao}\n\n{regras_antibloqueio}",
    }

    # --- Mensagem de contexto para a IA (sem mencionar plano inativo) ---
    contexto_assistant = {
        "role": "assistant",
        "content": (
            "📌 CONTEXTO ATUAL DO ATENDIMENTO\n"
            f"- Data atual: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"- Pagamento ativo (assumido): {str(pagamento_ativo)}\n"
            f"- Módulos ativos (assumidos): {', '.join(sorted(set(str(p).lower() for p in planos_ativos)))}\n"
            f"- Tipo de negócio: {usuario.get('tipo_negocio') or usuario.get('tipoNegocio') or 'não informado'}\n"
            f"- Profissionais: {resumo_prof or 'nenhum'}\n"
            f"- Tarefas (amostra): {', '.join(resumo_tarefas) or 'nenhuma'}\n"
            f"- Eventos (amostra): {', '.join(resumo_eventos) or 'nenhum'}\n"
            f"- E-mails (amostra): {', '.join(resumo_emails) or 'nenhum'}\n"
            f"- Contexto temporário: {json.dumps(ctx_tmp, ensure_ascii=False)}\n"
            "Lembrete: execute o fluxo solicitado sem bloquear por plano."
        ),
    }

    # --- Mensagem do usuário ---
    user_msg = {
        "role": "user",
        "content": texto_usuario or "",
    }

    return [system_msg, contexto_assistant, user_msg]


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
    try:
        return mapa.get(servico.lower(), 60)
    except Exception:
        return 60


def formatar_data(data_iso):
    try:
        dt = datetime.fromisoformat(data_iso)
        return dt.strftime("dia %d/%m às %H:%Mh")
    except Exception:
        return data_iso


def limpar_nome_duplicado(resposta, nomes):
    """Evita repetição do mesmo nome na resposta final."""
    texto = resposta or ""
    for nome in nomes or []:
        padrao = rf"(\b{re.escape(nome)}\b[,\s]*)+"
        texto = re.sub(padrao, f"{nome}, ", texto, flags=re.IGNORECASE)
    return re.sub(r",\s*,", ",", texto).strip(", ").strip()
