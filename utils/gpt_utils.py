#gpt utils
import json
import re
from datetime import datetime
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA


def montar_prompt_com_contexto(instrucao, contexto, contexto_salvo, texto_usuario):
    profissionais = [p["nome"] for p in contexto.get("profissionais", [])]
    tarefas = contexto.get("tarefas", [])
    eventos = contexto.get("eventos", [])
    emails = contexto.get("emails", [])
    usuario = contexto.get("usuario", {})

    pagamento_ativo = contexto.get("pagamentoAtivo", usuario.get("pagamentoAtivo", False))
    planos_ativos = contexto.get("planosAtivos", usuario.get("planosAtivos", []))

    return [
        {"role": "system", "content": instrucao},
        {"role": "user", "content": f"""
📌 CONTEXTO ATUAL DO ATENDIMENTO:

📅 Data atual: {datetime.now().strftime('%Y-%m-%d')}
👤 Nome: {usuario.get('nome', 'Desconhecido')}
📌 Plano ativo: {pagamento_ativo}
🔐 Módulos: {', '.join(planos_ativos) or 'Nenhum'}
🏢 Tipo de negócio: {usuario.get('tipo_negocio', usuario.get('tipoNegocio', 'não informado'))}
🧑‍💼 Profissionais: {', '.join(profissionais) or 'Nenhum'}

📋 Tarefas:
{chr(10).join(f"- {t}" for t in tarefas) or 'Nenhuma'}

📆 Eventos:
{chr(10).join(f"- {e}" for e in eventos) or 'Nenhum'}

📧 E-mails:
{chr(10).join(f"- {e}" for e in emails) or 'Nenhum'}

📂 Contexto salvo:
{json.dumps(contexto_salvo or {}, indent=2, ensure_ascii=False)}

🗣️ Mensagem do usuário:
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