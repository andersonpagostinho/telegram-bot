# handlers/dashboard_handler.py
"""
Handler para Dashboard do Dono

Comando: /dashboard
Variações: /dados, /relatorio, /saude

Função:
- Dono solicita: /dashboard
- Sistema retorna: Dashboard completo
- Motor determinístico (sem GPT)
"""

from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from services.firebase_service_async import obter_id_dono
from services.dashboard_service import (
    obter_dashboard_completo,
    obter_resumo_hoje,
    obter_resumo_semana,
    obter_metricas_profissionais,
    obter_metricas_clientes,
    obter_metricas_servicos,
    obter_alertas_operacionais,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE CHECK — CRÍTICO PARA SEGURANÇA
# ============================================================================

async def _validar_acesso_dono(user_id: str) -> tuple[bool, str | None]:
    """
    Valida se user_id é realmente um DONO (owner/tenant).

    Retorna: (é_dono: bool, tenant_id: str | None)

    CRÍTICO: Sem isso, clientes e profissionais acessam dados de outros.
    Vazamento de dados do salão.
    """
    tenant_id = await obter_id_dono(user_id)

    # Se obter_id_dono() retorna user_id mesmo, então user_id É o dono
    # Se retorna outro valor, então user_id é cliente de tenant_id
    eh_dono = (tenant_id == user_id)

    return eh_dono, tenant_id if eh_dono else None


# ============================================================================
# COMANDO PRINCIPAL: /dashboard
# ============================================================================

async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /dashboard

    Retorna dashboard completo com:
    - Resumo do dia
    - Resumo da semana
    - Alertas críticos
    - Profissionais top
    - Serviços top

    SEGURANÇA: Apenas donos (owners) podem acessar.
    Clientes e profissionais são bloqueados.

    Uso:
        /dashboard
        /dados
        /relatorio
    """
    try:
        user_id = str(update.message.from_user.id)

        # 🚨 ROLE CHECK CRÍTICO — Validar se é dono
        eh_dono, tenant_id = await _validar_acesso_dono(user_id)

        if not eh_dono:
            logger.warning(f"⚠️ ACESSO BLOQUEADO: Cliente {user_id} tentou acessar /dashboard")
            await update.message.reply_text(
                "⚠️ Acesso negado. Dashboard é apenas para donos do negócio.\n"
                "Se você é dono, configure seus dados com /meuplano"
            )
            return

        if not tenant_id:
            await update.message.reply_text(
                "⚠️ Não foi possível identificar seu salão/negócio. "
                "Configure seus dados com /meuplano ou /meusperfil"
            )
            return

        # Buscar dashboard completo
        dashboard = await obter_dashboard_completo(tenant_id)

        # Formatar mensagem
        msg = _formatar_dashboard_completo(dashboard)

        # Enviar
        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"❌ Erro ao gerar dashboard: {e}")
        await update.message.reply_text(
            "❌ Erro ao gerar dashboard. Tente novamente."
        )


# ============================================================================
# VARIANTES — Dados específicos
# ============================================================================

async def cmd_resumo_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /hoje

    Retorna apenas resumo de hoje.
    SEGURANÇA: Apenas donos.
    """
    try:
        user_id = str(update.message.from_user.id)

        # 🚨 Role check
        eh_dono, tenant_id = await _validar_acesso_dono(user_id)
        if not eh_dono or not tenant_id:
            await update.message.reply_text("⚠️ Acesso negado. Dashboard é apenas para donos.")
            return

        resumo = await obter_resumo_hoje(tenant_id)
        msg = _formatar_resumo_hoje(resumo)

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"❌ Erro ao gerar resumo hoje: {e}")
        await update.message.reply_text("❌ Erro ao gerar resumo.")


async def cmd_resumo_semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /semana

    Retorna apenas resumo da semana.
    SEGURANÇA: Apenas donos.
    """
    try:
        user_id = str(update.message.from_user.id)

        # 🚨 Role check
        eh_dono, tenant_id = await _validar_acesso_dono(user_id)
        if not eh_dono or not tenant_id:
            await update.message.reply_text("⚠️ Acesso negado. Dashboard é apenas para donos.")
            return

        resumo = await obter_resumo_semana(tenant_id)
        msg = _formatar_resumo_semana(resumo)

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"❌ Erro ao gerar resumo semana: {e}")
        await update.message.reply_text("❌ Erro ao gerar resumo.")


async def cmd_metricas_profissionais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /profissionais

    Retorna métricas de cada profissional.
    SEGURANÇA: Apenas donos.
    """
    try:
        user_id = str(update.message.from_user.id)

        # 🚨 Role check
        eh_dono, tenant_id = await _validar_acesso_dono(user_id)
        if not eh_dono or not tenant_id:
            await update.message.reply_text("⚠️ Acesso negado. Dashboard é apenas para donos.")
            return

        profs = await obter_metricas_profissionais(tenant_id)
        msg = _formatar_metricas_profissionais(profs)

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"❌ Erro ao gerar métricas profissionais: {e}")
        await update.message.reply_text("❌ Erro ao gerar métricas.")


async def cmd_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando: /alertas

    Retorna apenas alertas críticos e avisos.
    SEGURANÇA: Apenas donos.
    """
    try:
        user_id = str(update.message.from_user.id)

        # 🚨 Role check
        eh_dono, tenant_id = await _validar_acesso_dono(user_id)
        if not eh_dono or not tenant_id:
            await update.message.reply_text("⚠️ Acesso negado. Dashboard é apenas para donos.")
            return

        alertas = await obter_alertas_operacionais(tenant_id)
        msg = _formatar_alertas(alertas)

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.exception(f"❌ Erro ao gerar alertas: {e}")
        await update.message.reply_text("❌ Erro ao gerar alertas.")


# ============================================================================
# FORMATADORES — Estruturar mensagens
# ============================================================================

def _formatar_dashboard_completo(dashboard) -> str:
    """Formata dashboard completo em mensagem legível."""

    msg = f"""
<b>📊 DASHBOARD DO DONO</b>
<code>{dashboard.timestamp}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📅 HOJE</b>
├─ <b>Ocupação:</b> {dashboard.resumo_hoje.taxa_ocupacao:.0f}%
├─ <b>Agendamentos:</b> {dashboard.resumo_hoje.agendamentos_total}
│  └─ Confirmados: {dashboard.resumo_hoje.agendamentos_confirmados}
│  └─ Cancelados: {dashboard.resumo_hoje.agendamentos_cancelados}
├─ <b>Taxa cancelamento:</b> {dashboard.resumo_hoje.taxa_cancelamento:.0f}%
├─ <b>Encaixes:</b> {dashboard.resumo_hoje.encaixes_convertidos}
└─ <b>Fila de espera:</b> {dashboard.resumo_hoje.fila_espera_ativa}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📈 SEMANA</b>
├─ <b>Total agendamentos:</b> {dashboard.resumo_semana.agendamentos_total}
├─ <b>Ocupação média:</b> {dashboard.resumo_semana.taxa_ocupacao:.0f}%
├─ <b>Taxa cancelamento:</b> {dashboard.resumo_semana.taxa_cancelamento:.0f}%
└─ <b>Encaixes convertidos:</b> {dashboard.resumo_semana.encaixes_convertidos}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>👥 CLIENTES</b>
├─ <b>Novos (7 dias):</b> {dashboard.metricas_clientes.clientes_novos_7_dias}
├─ <b>Recorrentes:</b> {dashboard.metricas_clientes.clientes_recorrentes}
├─ <b>Sem retorno (30d):</b> {dashboard.metricas_clientes.clientes_sem_retorno_30_dias}
├─ <b>Sem retorno (60d):</b> {dashboard.metricas_clientes.clientes_sem_retorno_60_dias}
└─ <b>Sem retorno (90d):</b> {dashboard.metricas_clientes.clientes_sem_retorno_90_dias}

<b>Top clientes:</b>
{_formatar_top_clientes(dashboard.metricas_clientes.top_clientes)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💼 PROFISSIONAIS</b> ({len(dashboard.metricas_profissionais)})

{_formatar_profissionais_resumo(dashboard.metricas_profissionais)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🛠️ SERVIÇOS</b> (Top 5)

{_formatar_servicos_resumo(dashboard.metricas_servicos[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🚨 ALERTAS</b> ({len(dashboard.alertas)})

{_formatar_alertas(dashboard.alertas)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>Comandos disponíveis:</i>
/hoje — resumo de hoje
/semana — resumo da semana
/profissionais — métricas por profissional
/alertas — apenas alertas críticos
"""

    return msg.strip()


def _formatar_resumo_hoje(resumo) -> str:
    """Formata resumo do dia."""
    return f"""
<b>📅 RESUMO DE HOJE</b>

<b>Agendamentos:</b> {resumo.agendamentos_total}
├─ Confirmados: {resumo.agendamentos_confirmados}
├─ Cancelados: {resumo.agendamentos_cancelados}
└─ Concluídos: {resumo.agendamentos_concluidos}

<b>Ocupação:</b> {resumo.taxa_ocupacao:.0f}%
<b>Taxa cancelamento:</b> {resumo.taxa_cancelamento:.0f}%

<b>Encaixes convertidos:</b> {resumo.encaixes_convertidos}
<b>Fila de espera:</b> {resumo.fila_espera_ativa}
"""


def _formatar_resumo_semana(resumo) -> str:
    """Formata resumo da semana."""
    return f"""
<b>📈 RESUMO DA SEMANA</b>

<b>Agendamentos:</b> {resumo.agendamentos_total}
├─ Confirmados: {resumo.agendamentos_confirmados}
├─ Cancelados: {resumo.agendamentos_cancelados}
└─ Concluídos: {resumo.agendamentos_concluidos}

<b>Ocupação média:</b> {resumo.taxa_ocupacao:.0f}%
<b>Taxa cancelamento:</b> {resumo.taxa_cancelamento:.0f}%

<b>Encaixes convertidos:</b> {resumo.encaixes_convertidos}
<b>Fila de espera ativa:</b> {resumo.fila_espera_ativa}
"""


def _formatar_metricas_profissionais(profs) -> str:
    """Formata métricas de profissionais."""
    if not profs:
        return "<b>💼 Nenhum profissional cadastrado</b>"

    msg = "<b>💼 PROFISSIONAIS</b>\n\n"

    for prof in profs[:10]:  # Top 10
        servicos_str = ", ".join(
            f"{s[0]} ({s[1]})" for s in prof.servicos_mais_realizados[:3]
        ) or "—"

        msg += f"""
<b>{prof.profissional}</b>
├─ Atendimentos: {prof.atendimentos}
├─ Ocupação: {prof.ocupacao_percentual:.0f}%
├─ Faturamento: R$ {prof.faturamento_estimado:.2f}
├─ Cancelamentos: {prof.cancelamentos_recebidos} ({prof.taxa_cancelamento:.0f}%)
├─ Top serviços: {servicos_str}
└─ Dias sem agenda: {prof.dias_sem_agendamento}

"""

    return msg.strip()


def _formatar_servicos_resumo(servicos) -> str:
    """Formata resumo de serviços."""
    if not servicos:
        return "Nenhum serviço ainda"

    msg = ""
    for i, srv in enumerate(servicos, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "   "
        msg += f"""
{emoji} <b>{srv.servico}</b>
   ├─ Quantidade: {srv.quantidade}
   ├─ Ticket médio: R$ {srv.ticket_medio:.2f}
   ├─ Duração: {srv.duracao_media_estimada} min (real: {srv.duracao_media_real} min)
   └─ Com complementares: {srv.taxa_complementares:.0f}%

"""

    return msg.strip()


def _formatar_alertas(alertas) -> str:
    """Formata alertas operacionais."""
    if not alertas:
        return "✅ Nenhum alerta"

    msg = ""

    for alerta in alertas:
        emoji_sev = "🔴" if alerta.severidade == "critical" else \
                    "🟡" if alerta.severidade == "warning" else "ℹ️"

        msg += f"""
{emoji_sev} <b>{alerta.tipo.upper()}</b>
   {alerta.descricao}

   <i>Ações sugeridas:</i>
"""

        for acao in alerta.acoes_sugeridas:
            msg += f"   • {acao}\n"

        msg += "\n"

    return msg.strip()


def _formatar_top_clientes(clientes) -> str:
    """Formata top clientes."""
    if not clientes:
        return "—"

    msg = ""
    for i, cli in enumerate(clientes, 1):
        emoji = "🏆" if i == 1 else "⭐"
        msg += f"{emoji} {cli['nome']} — {cli['frequencia']} agendamentos\n"

    return msg.strip()


def _formatar_profissionais_resumo(profs) -> str:
    """Formata resumo rápido de profissionais (sem detalhes)."""
    if not profs:
        return "—"

    msg = ""
    for prof in profs[:5]:  # Top 5
        emoji = "🟢" if prof.ocupacao_percentual > 70 else "🟡" if prof.ocupacao_percentual > 50 else "🔴"
        msg += f"{emoji} {prof.profissional}: {prof.ocupacao_percentual:.0f}% (R$ {prof.faturamento_estimado:.0f})\n"

    return msg.strip()
