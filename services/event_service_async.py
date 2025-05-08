from datetime import datetime, timedelta
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from services.firebase_service_async import salvar_dado_em_path, buscar_subcolecao, deletar_dado_em_path
from services.notificacao_service import criar_notificacao_agendada

# 🔁 Salvar ou atualizar um evento
async def salvar_evento(user_id: str, evento: dict, event_id: str = None) -> bool:
    try:
        if not event_id:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            nome_base = evento.get("descricao", "evento").replace(" ", "_").lower()
            event_id = f"{timestamp}_{nome_base}"

        evento.setdefault("criado_em", datetime.now().isoformat())
        evento.setdefault("confirmado", False)
        evento.setdefault("link", "")
        evento.setdefault("status", "pendente")

        path = f"Clientes/{user_id}/Eventos/{event_id}"
        await salvar_dado_em_path(path, evento)

        # Agenda o lembrete automaticamente 30 minutos antes
        try:
            await criar_notificacao_agendada(
                user_id=user_id,
                evento=evento,
                minutos_antes=30,
                canal="telegram"
            )
        except Exception as e:
            print(f"⚠️ Erro ao agendar notificação: {e}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar evento: {e}")
        return False

# 🔎 Buscar eventos por data (hoje, amanhã, etc.)
async def buscar_eventos_por_intervalo(user_id: str, dias: int = 0, semana: bool = False, dia_especifico: datetime.date = None):
    try:
        eventos = await buscar_subcolecao(f"Clientes/{user_id}/Eventos") or {}
        hoje = datetime.now().date()

        if dia_especifico:
            data_alvo = dia_especifico
        elif semana:
            data_inicio = hoje
            data_fim = hoje + timedelta(days=6)
        else:
            data_alvo = hoje + timedelta(days=dias)

        resultado = []

        for evento in eventos.values():
            data_str = evento.get("data")
            if not data_str:
                continue

            try:
                data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if semana:
                if data_inicio <= data_evento <= data_fim:
                    resultado.append(formatar_evento(evento))
            else:
                if data_evento == data_alvo:
                    resultado.append(formatar_evento(evento))

        return resultado
    except Exception as e:
        print(f"❌ Erro ao buscar eventos: {e}")
        return []

# 🧹 Deletar um evento (opcional)
async def deletar_evento(user_id: str, event_id: str) -> bool:
    try:
        await deletar_dado_em_path(f"Clientes/{user_id}/Eventos/{event_id}")
        return True
    except Exception as e:
        print(f"❌ Erro ao deletar evento: {e}")
        return False

# 🧾 Formatador para exibição
def formatar_evento(evento: dict) -> str:
    data = evento.get("data", "???")
    inicio = evento.get("hora_inicio", "??:??")
    fim = evento.get("hora_fim", "??:??")
    desc = evento.get("descricao", "Sem título")
    return f"📝 {desc} – {data} das {inicio} às {fim}"

