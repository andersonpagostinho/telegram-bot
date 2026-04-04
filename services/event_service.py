# services/event_service.py

from datetime import datetime, timedelta
from services.firebase_service_async import buscar_subcolecao, obter_id_dono

async def buscar_eventos_por_intervalo(user_id, dias=0, semana=False, dia_especifico=None):
    id_dono = await obter_id_dono(user_id)  # 🔑 aqui está o pulo do gato
    eventos_dict = await buscar_subcolecao(f"Clientes/{id_dono}/Eventos")
    eventos_filtrados = []

    hoje = datetime.now().date()

    if dia_especifico:
        data_inicio = data_fim = dia_especifico
    elif semana:
        data_inicio = hoje
        data_fim = hoje + timedelta(days=6)
    else:
        data_inicio = hoje + timedelta(days=dias)
        data_fim = data_inicio  # Mesmo dia se não for semana

    print(f"🔎 Procurando eventos de {data_inicio} até {data_fim}")

    for evento in eventos_dict.values():
        if "data" in evento:
            try:
                data_evento = datetime.strptime(evento["data"], "%Y-%m-%d").date()
                print(f"📅 Evento encontrado: {evento['descricao']} em {data_evento}")

                if data_inicio <= data_evento <= data_fim:
                    descricao_formatada = f"{evento['descricao']} em {data_evento.strftime('%d/%m')} às {evento.get('hora_inicio', 'horário indefinido')}"
                    eventos_filtrados.append(descricao_formatada)
            except Exception as e:
                print(f"⚠️ Erro ao processar evento: {e}")

    print(f"✅ Eventos filtrados: {eventos_filtrados}")
    return eventos_filtrados
