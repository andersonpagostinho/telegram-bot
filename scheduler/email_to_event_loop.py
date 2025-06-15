import asyncio
import hashlib
from datetime import datetime, timedelta, time
import pytz
from dateutil.parser import parse as parse_date
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from google.cloud.firestore_v1.async_client import AsyncClient
from services.gpt_service import processar_com_gpt_com_acao
from services.email_service import ler_emails_google
from services.firebase_service_async import buscar_subcolecao, salvar_dado_em_path
from handlers.acao_router_handler import executar_acao_por_nome
from prompts.manual_secretaria import INSTRUCAO_SECRETARIA


import re  # certifique-se de ter essa importação no topo

async def processar_emails_para_eventos(user_id, context=None):
    emails = await ler_emails_google(user_id=user_id, num_emails=20)

    for email in emails:
        corpo = email.get("corpo", "")
        prioridade = email.get("prioridade", "baixa")
        
        if not corpo:
            continue

        # 🔍 Filtro 1: Ignorar e-mails com prioridade baixa
        if prioridade == "baixa":
            print(f"⏭️ Ignorado (prioridade baixa): {email.get('assunto')}")
            continue

        # 🔍 Filtro 2: Ignorar e-mails sem data aparente
        if not re.search(r"\d{1,2}/\d{1,2}", corpo):
            print(f"⏭️ Ignorado (sem data): {email.get('assunto')}")
            continue

        hash_email = hashlib.md5(corpo.encode()).hexdigest()
        print(f"\n🔍 Processando e-mail: {email.get('assunto')}")

        contexto = {
            "usuario": {
                "user_id": user_id,
                "nome": "Cliente",
                "pagamentoAtivo": True,
                "planosAtivos": ["secretaria"],
                "tipo_negocio": "serviço"
            },
            "tarefas": [],
            "eventos": [],
            "emails": [corpo],
            "profissionais": []
        }

        resultado = await processar_com_gpt_com_acao(corpo, contexto, INSTRUCAO_SECRETARIA)
        acao = resultado.get("acao")
        dados = resultado.get("dados", {})

        if acao in ["criar_tarefa", "criar_evento"]:
            from handlers.task_handler import add_task_por_gpt
            from handlers.event_handler import add_evento_por_gpt

            class DummyMessage:
                from_user = type("user", (), {"id": user_id})
                async def reply_text(self, msg):
                    print(f"[Simulado] {msg}")

            class DummyUpdate:
                message = DummyMessage()

            dummy = {"update": DummyUpdate(), "context": type("ctx", (), {"chat_data": {}})}

            if acao == "criar_tarefa":
                await add_task_por_gpt(dummy["update"], dummy["context"], dados)
            elif acao == "criar_evento":
                agora = datetime.utcnow().replace(tzinfo=pytz.UTC)
                dados["data_hora"] = dados.get("data_hora") or (agora + timedelta(minutes=5)).isoformat()
                dados["descricao"] = dados.get("descricao") or "Verificar e-mail importante"
                dados["duracao"] = dados.get("duracao") or 15
                await add_evento_por_gpt(dummy["update"], dummy["context"], dados)

        # 🔧 Processa e salva dados do e-mail
        data_str = email.get("data")
        data_iso = None
        data_ts = None

        if data_str:
            try:
                dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    dt = parse_date(data_str)
                except Exception as e:
                    print(f"⚠️ Erro ao converter data '{data_str}': {e}")
                    dt = None
            if dt:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                data_iso = dt.isoformat()
                data_ts = dt

        dados_email = {
            "assunto": email.get("assunto"),
            "remetente": email.get("remetente"),
            "data": data_iso,
            "data_timestamp": data_ts or SERVER_TIMESTAMP
        }

        print(f"✅ Salvando e-mail processado: {email.get('assunto')}")
        await salvar_dado_em_path(f"Clientes/{user_id}/EmailsProcessados/{hash_email}", dados_email)

async def limpar_emails_antigos_sem_acao(user_id, dias_antigos=3):
    print(f"🧹 Limpando e-mails antigos (sem ação) do usuário {user_id}...")
    db = AsyncClient()
    cutoff = datetime.now(pytz.UTC) - timedelta(days=dias_antigos)

    collection_path = f"Clientes/{user_id}/EmailsProcessados"
    snapshots = await db.collection(collection_path).get()

    for doc in snapshots:
        data = doc.to_dict()
        data_ts = data.get("data_timestamp")
        if not data_ts:
            continue
        if isinstance(data_ts, datetime) and data_ts < cutoff:
            print(f"🗑️ Deletando: {doc.id} - {data.get('assunto')}")
            await db.document(f"{collection_path}/{doc.id}").delete()

    print(f"✅ Limpeza concluída para {user_id}.")


async def listar_clientes_com_email():
    clientes = await buscar_subcolecao("Clientes") or {}
    return [uid for uid, dados in clientes.items() if dados.get("email_config")]

HORARIOS_EXECUCAO = [time(10, 0), time(17, 0)]

async def loop_verificacao_emails():
    print("🚀 Loop de verificação de e-mails INICIADO")

    horarios_executados_hoje = set()

    while True:
        agora = datetime.now()
        hora_atual = agora.time()

        for horario in HORARIOS_EXECUCAO:
            if (
                hora_atual.hour == horario.hour and
                hora_atual.minute == horario.minute and
                horario not in horarios_executados_hoje
            ):
                print(f"⏰ Executando verificação programada para {horario.strftime('%H:%M')}")
                clientes = await listar_clientes_com_email()
                for user_id in clientes:
                    try:
                        await processar_emails_para_eventos(user_id)
                        await limpar_emails_antigos_sem_acao(user_id)
                    except Exception as e:
                        print(f"❌ Erro com usuário {user_id}: {e}")

                horarios_executados_hoje.add(horario)

        # Reseta o controle à meia-noite
        if hora_atual.hour == 0 and hora_atual.minute == 0:
            horarios_executados_hoje.clear()

        await asyncio.sleep(60)  # verifica a cada minuto

