from firebase_admin import firestore
from datetime import datetime, timedelta
from utils.contexto_temporario import salvar_contexto_temporario
from services.firebase_service_async import obter_id_dono
from services.firestore_client import get_db
import pytz
import asyncio

# [INFRA-03] Usar singleton de firestore_client em vez de criar cliente independente
db = get_db()

# Tempo de expiração de sessão (em minutos)
SESSION_TTL_MINUTES = 30

async def criar_ou_atualizar_sessao(user_id, dados: dict):
    now = datetime.now(pytz.UTC)
    dados['last_updated'] = now
    await asyncio.to_thread(
        lambda: db.collection("sessions").document(user_id).set(dados, merge=True)
    )

async def pegar_sessao(user_id):
    doc = await asyncio.to_thread(
        lambda: db.collection("sessions").document(user_id).get()
    )
    if doc.exists:
        sessao = doc.to_dict()
        last_updated = sessao.get('last_updated')
        if last_updated and datetime.now(pytz.UTC) - last_updated > timedelta(minutes=SESSION_TTL_MINUTES):
            await resetar_sessao(user_id)
            return None
        return sessao
    return None

async def resetar_sessao(user_id):
    await asyncio.to_thread(
        lambda: db.collection("sessions").document(user_id).delete()
    )

async def limpar_sessoes_expiradas():
    limite = datetime.now(pytz.UTC) - timedelta(minutes=SESSION_TTL_MINUTES)
    docs = await asyncio.to_thread(
        lambda: list(db.collection("sessions").where("last_updated", "<", limite).stream())
    )
    for doc in docs:
        await asyncio.to_thread(doc.reference.delete)

async def sincronizar_contexto(user_id, sessao):
    # [P2-MIGRACAO-LOTE1-OC2] Resolver tenant_id deterministicamente
    tenant_id = await obter_id_dono(user_id)
    if not tenant_id:
        tenant_id = str(user_id)
        print(f"[TENANT_FALLBACK] sincronizar_contexto: obter_id_dono retornou None, usando user_id como fallback | user_id={user_id}")

    memoria = {
        "estado": sessao.get("estado"),
        "servico": sessao.get("servico"),
        "data_hora": None,
        "profissional_escolhido": sessao.get("profissional"),
        "ultima_opcao_profissionais": sessao.get("disponiveis")
    }

    # Monta a data_hora se tiver data e hora na sessão
    if sessao.get("data") and sessao.get("hora"):
        try:
            data_hora_iso = datetime.strptime(f"{sessao['data']} {sessao['hora']}", "%d/%m/%Y %H:%M").isoformat()
            memoria["data_hora"] = data_hora_iso
        except Exception as e:
            print(f"⚠️ Erro ao converter data/hora para ISO: {e}")

    # Remove campos vazios
    memoria_filtrada = {k: v for k, v in memoria.items() if v}

    print(f"🔄 Sincronizando contexto temporário para {user_id}: {memoria_filtrada}")
    await salvar_contexto_temporario(user_id, memoria_filtrada, tenant_id=tenant_id)  # [P2-MIGRACAO-LOTE1-OC2]
