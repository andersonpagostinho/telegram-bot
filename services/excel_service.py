# services/excel_service.py
import io
from openpyxl import Workbook
from firebase_admin import storage
from services.firebase_service_async import obter_id_dono


async def gerar_excel_agenda(user_id: str, eventos: list, salvar_storage: bool = True) -> io.BytesIO:
    """
    Gera um Excel da agenda.
    - user_id: quem pediu (pode ser cliente ou dono)
    - eventos: lista já filtrada
    - salvar_storage: se True, sobe para o Storage na pasta do DONO
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Agenda"

    # Cabeçalho
    ws.append(["Descrição", "Data", "Hora Início", "Hora Fim", "Status", "Link"])

    for ev in eventos:
        ws.append([
            ev.get("descricao", ""),
            ev.get("data", ""),
            ev.get("hora_inicio", ""),
            ev.get("hora_fim", ""),
            "Confirmado ✅" if ev.get("confirmado") else "Pendente ⏳",
            ev.get("link", "")
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    if salvar_storage:
        try:
            # 🔑 garante que salva na pasta do dono, mesmo se quem pediu for cliente
            dono_id = await obter_id_dono(user_id)

            bucket = storage.bucket()
            blob = bucket.blob(f"agendas/{dono_id}/agenda_neoagenda.xlsx")
            blob.upload_from_file(
                stream,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            blob.make_public()  # opcional
            print("✅ Planilha enviada ao Firebase Storage.")
        except Exception as e:
            print(f"⚠️ Erro ao enviar planilha para Storage: {e}")

        # reposiciona para quem quiser mandar no Telegram depois
        stream.seek(0)

    return stream
