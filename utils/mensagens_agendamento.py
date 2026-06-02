"""
Formatação de mensagens para fluxo de agendamento.

Funções determinísticas que NÃO acessam Firebase, GPT ou decidem disponibilidade.
Única fonte de verdade para mensagens de pré-confirmação e sucesso.
"""

from datetime import datetime, timedelta


def formatar_data_hora_natural(data_hora: str) -> tuple[str, str]:
    try:
        dt = datetime.fromisoformat(data_hora)
        hoje = datetime.now().date()

        hora_str = f"{dt.hour}h" if dt.minute == 0 else f"{dt.hour}h{dt.minute:02d}"

        if dt.date() == hoje:
            quando = "hoje"
        elif dt.date() == hoje + timedelta(days=1):
            quando = "amanhã"
        else:
            quando = f"em {dt.strftime('%d/%m')}"

        return quando, hora_str
    except Exception:
        return "", ""


def montar_mensagem_preconfirmacao(servico: str, profissional: str, data_hora: str) -> str:
    quando, hora_str = formatar_data_hora_natural(data_hora)

    if quando and hora_str:
        return (
            f"Perfeito! Encontrei um horário com {profissional} "
            f"{quando} às {hora_str} para sua {servico}. Posso confirmar?"
        )

    return f"Encontrei um horário para {servico} com {profissional}. Posso confirmar?"


def montar_mensagem_confirmacao_sucesso(servico: str, profissional: str, data_hora: str) -> str:
    quando, hora_str = formatar_data_hora_natural(data_hora)

    if quando and hora_str:
        return (
            f"Pronto, sua {servico.lower()} com {profissional} "
            f"ficou agendada para {quando} às {hora_str}."
        )

    return "Pronto, seu agendamento foi confirmado."
