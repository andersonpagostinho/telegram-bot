import io
from openpyxl import Workbook
from firebase_admin import storage

async def gerar_excel_agenda(user_id: str, eventos: list) -> io.BytesIO:
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
    return stream
async def gerar_excel_agenda(user_id: str, eventos: list, salvar_storage: bool = True) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Agenda"

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
            bucket = storage.bucket()
            blob = bucket.blob(f"agendas/{user_id}/agenda_neoagenda.xlsx")
            blob.upload_from_file(stream, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            blob.make_public()  # opcional: deixa o link acessível publicamente
            print("✅ Planilha enviada ao Firebase Storage.")
        except Exception as e:
            print(f"⚠️ Erro ao enviar planilha para Storage: {e}")

        stream.seek(0)  # reposiciona para envio posterior por Telegram

    return stream