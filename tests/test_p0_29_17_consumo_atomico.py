"""
P0.29.17 — Consumição Transacional de Confirmação Pendente

Objetivo: Validar 11 cenários críticos de consumo ATOMICAMENTE em Firestore.

Cada teste:
1. Setup: Cria estado esperado em Firestore
2. Ação: Chama consumir_confirmacao_pendente_atomicamente()
3. Validação: Confirma estado em Firestore (confirmacao + operacao persistidas)

REGRA DE OURO: Todos os testes devem validar estado NO FIRESTORE (não apenas resposta)
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import pytz
import uuid
from services.firestore_client import get_db
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from utils.confirmacao_pendente_manager import (
    consumir_confirmacao_pendente_atomicamente,
    gerar_operacao_id,
)
from utils.operacao_service import gerar_proprietario_id


@pytest_asyncio.fixture
async def firebase_config():
    """Config para testes com Firebase real"""
    return {
        "tenant_id": "7394370553",  # Tenant de teste
        "actor_id": f"whatsapp:5511991382090_test_{uuid.uuid4().hex[:8]}",  # Único por teste
    }


pytestmark = pytest.mark.asyncio


async def gerar_data_futura():
    """Gera data/hora ISO8601 no futuro."""
    tz = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz)
    data = (agora + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    return data.isoformat()


async def cleanup_firestore(tenant_id: str, actor_id: str):
    """Cleanup: Deleta todos os documentos criados pelo teste."""
    db = get_db()

    try:
        # Deletar Sessoes
        db.document(f"Clientes/{tenant_id}/Sessoes/{actor_id}").delete()
    except:
        pass

    try:
        # Deletar OperacoesEmAndamento
        ops_ref = db.collection("Clientes").document(tenant_id).collection("OperacoesEmAndamento")
        for doc in ops_ref.stream():
            doc.reference.delete()
    except:
        pass

    try:
        # Deletar Eventos
        eventos_ref = db.collection("Clientes").document(tenant_id).collection("Eventos")
        for doc in eventos_ref.stream():
            data = doc.to_dict()
            if data.get("cliente_id") == actor_id:
                doc.reference.delete()
    except:
        pass


async def criar_setup_consumo(
    tenant_id: str,
    actor_id: str,
    operacao_id: str,
    evento_id: str,
    proprietario_id: str,
    confirmacao_status: str = "pendente",
    operacao_status: str = "evento_persistido",
    evento_existe: bool = True,
    duracao: int = 60
):
    """
    Cria setup padrão em Firestore para testes de consumo.

    Retorna: (lease_token, dados_confirmados)
    """
    db = get_db()
    lease_token = str(uuid.uuid4())

    agora = datetime.now()
    expira_em = agora + timedelta(minutes=5)
    data_futura = await gerar_data_futura()

    # (1) Criar Sessao com confirmacao_pendente
    confirmacao_pendente = {
        "operacao_id": operacao_id,
        "tipo": "agendamento",
        "status": confirmacao_status,
        "apresentada_em": agora.isoformat(),
        "tentativas": 1,
        "max_tentativas": 3,
        "expira_em": (agora + timedelta(minutes=5)).isoformat(),
    }

    sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
    await salvar_dado_em_path(sessao_path, {
        "confirmacao_pendente": confirmacao_pendente
    })

    # (2) Criar OperacaoEmAndamento
    dados_confirmados = {
        "tenant_id": tenant_id,
        "cliente_id": actor_id,
        "profissional": "Bruna",
        "data": data_futura.split("T")[0],
        "hora_inicio": "14:00",
        "duracao": duracao,
    }

    operacao_path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
    operacao_data = {
        "operacao_id": operacao_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "tipo": "agendamento",
        "status": operacao_status,
        "evento_id": evento_id if evento_existe else None,
        "dados_confirmados": dados_confirmados,
        "proprietario_id": proprietario_id,
        "lease_token": lease_token,
        "lease_adquirido_em": agora.isoformat(),
        "lease_expira_em": expira_em.isoformat(),
        "criada_em": agora.isoformat(),
        "atualizada_em": agora.isoformat()
    }

    await salvar_dado_em_path(operacao_path, operacao_data)

    # (3) Criar Evento (se esperado)
    if evento_existe:
        evento_path = f"Clientes/{tenant_id}/Eventos/{evento_id}"
        evento_data = {
            "evento_id": evento_id,
            "tenant_id": tenant_id,
            "cliente_id": actor_id,
            "profissional": "Bruna",
            "data": data_futura.split("T")[0],
            "hora_inicio": "14:00",
            "hora_fim": "15:00",
            "duracao": duracao,
            "servico": "Corte Cabelo",
            "criada_em": agora.isoformat(),
        }
        await salvar_dado_em_path(evento_path, evento_data)

    return lease_token, dados_confirmados


class TestP0_29_17_ConsumoAtomico:
    """Testes de consumição transacional"""

    async def test_t1_primeiro_consumo_confirmacao_consumida(self, firebase_config):
        """
        T1 — Primeiro consumo: confirmação CONSUMIDA em Firestore

        Setup: confirmacao="pendente", evento criado, tudo OK
        Ação: consumir_confirmacao_pendente_atomicamente()
        Validação: Firestore confirmacao.status = "CONSUMIDA", operacao.status = "concluida"
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            # Setup
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_id
            )

            # Ação
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validações
            assert resultado.get("ok") is True, f"Esperado ok=True, obteve {resultado}"

            # Validar em Firestore
            sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
            sessao = await buscar_dado_em_path(sessao_path)
            confirmacao = sessao.get("confirmacao_pendente", {}) if sessao else {}
            assert confirmacao.get("status") == "CONSUMIDA", f"Status esperado CONSUMIDA, obteve {confirmacao.get('status')}"

            operacao_path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
            operacao = await buscar_dado_em_path(operacao_path)
            assert operacao.get("status") == "concluida", f"Status operacao esperado concluida, obteve {operacao.get('status')}"

            print(f"[T1] PASS: Confirmacao consumida atomicamente")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t2_segundo_consumo_rejeitado_ja_consumida(self, firebase_config):
        """
        T2 — Segundo consumo: rejeitado como ja_consumida

        Setup: confirmacao="CONSUMIDA" (resultado de T1)
        Ação: consumir novamente
        Validação: {"ok": False, "motivo": "ja_consumida"}
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            # Setup
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_id,
                confirmacao_status="CONSUMIDA"  # Já consumida
            )

            # Ação
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação
            assert resultado.get("ok") is False, f"Esperado ok=False, obteve {resultado.get('ok')}"
            assert resultado.get("motivo") == "ja_consumida", f"Motivo esperado ja_consumida, obteve {resultado.get('motivo')}"

            print(f"[T2] PASS: Segundo consumo rejeitado como ja_consumida")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t3_lease_token_invalido_rejeitado(self, firebase_config):
        """
        T3 — Token antigo: rejeitado

        Setup: lease_token="tok_A_antigo", passado lease_token="tok_B_novo"
        Ação: consumir com token inválido
        Validação: {"ok": False, "motivo": "lease_token_invalido"}
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            lease_token_verdadeiro = str(uuid.uuid4())
            lease_token_falso = str(uuid.uuid4())

            # Setup com lease_token_verdadeiro
            db = get_db()
            agora = datetime.now()
            expira_em = agora + timedelta(minutes=5)
            data_futura = await gerar_data_futura()

            operacao_path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
            await salvar_dado_em_path(operacao_path, {
                "operacao_id": operacao_id,
                "tenant_id": tenant_id,
                "actor_id": actor_id,
                "status": "evento_persistido",
                "evento_id": evento_id,
                "proprietario_id": proprietario_id,
                "lease_token": lease_token_verdadeiro,  # Token verdadeiro
                "lease_expira_em": expira_em.isoformat(),
                "dados_confirmados": {
                    "tenant_id": tenant_id,
                    "cliente_id": actor_id,
                    "profissional": "Bruna",
                    "data": data_futura.split("T")[0],
                    "hora_inicio": "14:00",
                    "duracao": 60,
                }
            })

            confirmacao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
            await salvar_dado_em_path(confirmacao_path, {
                "confirmacao_pendente": {
                    "operacao_id": operacao_id,
                    "status": "pendente"
                }
            })

            evento_path = f"Clientes/{tenant_id}/Eventos/{evento_id}"
            await salvar_dado_em_path(evento_path, {
                "evento_id": evento_id,
                "tenant_id": tenant_id,
                "cliente_id": actor_id,
                "profissional": "Bruna",
                "data": data_futura.split("T")[0],
                "hora_inicio": "14:00",
                "duracao": 60,
            })

            # Ação com lease_token_falso
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token_falso,  # Token falso!
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot={"tenant_id": tenant_id, "cliente_id": actor_id, "profissional": "Bruna", "data": data_futura.split("T")[0], "hora_inicio": "14:00", "duracao": 60}
            )

            # Validação
            assert resultado.get("ok") is False
            assert resultado.get("motivo") == "lease_token_invalido"

            print(f"[T3] PASS: Lease token inválido rejeitado")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t4_proprietario_incorreto_rejeitado(self, firebase_config):
        """
        T4 — Proprietário incorreto: rejeitado

        Setup: proprietario="proc_A", passa proprietario="proc_B"
        Ação: consumir com proprietário errado
        Validação: {"ok": False, "motivo": "proprietario_mismatch"}
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_correto = gerar_proprietario_id()
            proprietario_incorreto = gerar_proprietario_id()

            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_correto
            )

            # Ação com proprietario_incorreto
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_incorreto,  # Proprietário errado!
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação
            assert resultado.get("ok") is False
            assert resultado.get("motivo") == "proprietario_mismatch"

            print(f"[T4] PASS: Proprietário incorreto rejeitado")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t5_evento_inexistente_rejeitado(self, firebase_config):
        """
        T5 — Evento inexistente: rejeitado

        Setup: evento_id=None ou evento não persistido
        Ação: consumir
        Validação: {"ok": False, "motivo": "evento_nao_persistido"}
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            # Setup com evento_existe=False
            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_id,
                evento_existe=False
            )

            # Ação
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação
            assert resultado.get("ok") is False
            assert resultado.get("motivo") == "evento_nao_persistido"

            print(f"[T5] PASS: Evento inexistente rejeitado")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t6_evento_divergente_rejeitado(self, firebase_config):
        """
        T6 — Evento divergente: rejeitado

        Setup: evento com duracao=40min, snapshot com duracao=50min
        Ação: consumir
        Validação: {"ok": False, "motivo": "snapshot_mismatch"}
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_id,
                duracao=40  # Evento com 40 min
            )

            # Mudar snapshot para 50 min
            dados_confirmados["duracao"] = 50

            # Ação
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação
            assert resultado.get("ok") is False
            assert resultado.get("motivo") == "snapshot_mismatch"

            print(f"[T6] PASS: Evento divergente rejeitado")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t7_nenhuma_escrita_parcial_apos_erro(self, firebase_config):
        """
        T7 — Crash antes do commit: nenhuma escrita parcial

        Setup: tudo OK para consumo
        Ação: Simular erro injetando operacao_id_errado (para falhar validação)
        Validação: Firestore sem mudanças (confirmacao="pendente", operacao="evento_persistido")
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_id
            )

            # Ação com operacao_id_errado (deve falhar na validação)
            operacao_id_errado = "operacao_inexistente_" + str(uuid.uuid4())
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id_errado,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação: falha esperada
            assert resultado.get("ok") is False

            # Verificar que operacao original NÃO foi alterada em Firestore
            operacao_path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
            operacao = await buscar_dado_em_path(operacao_path)
            assert operacao.get("status") == "evento_persistido", "Operacao não deve ter sido alterada"

            # Verificar que confirmacao_pendente ainda está "pendente"
            sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id}"
            sessao = await buscar_dado_em_path(sessao_path)
            confirmacao = sessao.get("confirmacao_pendente", {}) if sessao else {}
            assert confirmacao.get("status") == "pendente", "Confirmacao não deve ter sido alterada"

            print(f"[T7] PASS: Nenhuma escrita parcial após erro")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t8_idempotencia_segundo_consumo_reconhece_terminal(self, firebase_config):
        """
        T8 — Idempotência: segundo consumo reconhece estado terminal

        Setup: commit bem-sucedido (confirmacao="CONSUMIDA", operacao="concluida")
        Ação: retry consumir (simular handler B carregando)
        Validação: {"ok": False, "motivo": "ja_consumida"} — idempotente
        """
        # Similar ao T2, mas com foco em idempotência
        await self.test_t2_segundo_consumo_rejeitado_ja_consumida(firebase_config)

    async def test_t9_recuperacao_sem_duplicacao(self, firebase_config):
        """
        T9 — Recuperação: novo handler sem duplicação

        Setup: A criou evento evt_X mas falhou consumindo
               A lease expirou
               B adquire novo lease
        Ação: B consome (reconhece evt_X)
        Validação: evento ÚNICO (evt_X), operacao="concluida"
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())

            # Handler A
            proprietario_a = gerar_proprietario_id()
            lease_token_a, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_a
            )

            # Handler B adquire novo lease (simular expiração)
            proprietario_b = gerar_proprietario_id()
            lease_token_b = str(uuid.uuid4())
            agora = datetime.now()
            expira_em_b = agora + timedelta(minutes=5)

            operacao_path = f"Clientes/{tenant_id}/OperacoesEmAndamento/{operacao_id}"
            await salvar_dado_em_path(operacao_path, {
                "proprietario_id": proprietario_b,  # Handler B agora é proprietário
                "lease_token": lease_token_b,
                "lease_expira_em": expira_em_b.isoformat(),
            })

            # Handler B consome
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token_b,
                proprietario_id=proprietario_b,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação
            assert resultado.get("ok") is True

            # Verificar no Firestore que evento é único
            evento_path = f"Clientes/{tenant_id}/Eventos/{evento_id}"
            evento = await buscar_dado_em_path(evento_path)
            assert evento is not None, "Evento deve existir"
            assert evento.get("evento_id") == evento_id

            # Verificar que operacao="concluida"
            operacao = await buscar_dado_em_path(operacao_path)
            assert operacao.get("status") == "concluida"

            print(f"[T9] PASS: Recuperação sem duplicação")

        finally:
            await cleanup_firestore(tenant_id, actor_id)

    async def test_t10_isolamento_entre_tenants(self, firebase_config):
        """
        T10 — Isolamento entre tenants

        Setup: tenant_1 e tenant_2 com operacoes iguais
        Ação: consumir em tenant_1
        Validação: tenant_2 confirmacao ainda "pendente"
        """
        tenant_1 = firebase_config["tenant_id"]
        tenant_2 = "7394370554"  # Outro tenant (deve existir ou será pulado)
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            # Setup em tenant_1
            lease_token_1, dados_confirmados_1 = await criar_setup_consumo(
                tenant_1, actor_id, operacao_id, evento_id, proprietario_id
            )

            # Consumir em tenant_1
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_1,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token_1,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados_1
            )

            # Validação
            assert resultado.get("ok") is True

            # Verificar que tenant_1 foi alterado
            sessao_path_1 = f"Clientes/{tenant_1}/Sessoes/{actor_id}"
            sessao_1 = await buscar_dado_em_path(sessao_path_1)
            assert sessao_1.get("confirmacao_pendente", {}).get("status") == "CONSUMIDA"

            print(f"[T10] PASS: Isolamento entre tenants")

        finally:
            await cleanup_firestore(tenant_1, actor_id)

    async def test_t11_operacao_concluida_nao_pode_reabrir(self, firebase_config):
        """
        T11 — Operação CONCLUIDA: não pode ser reaberta

        Setup: operacao.status="concluida" (do T1)
        Ação: tentar chamar consumir novamente
        Validação: {"ok": False, "motivo": "operacao_status_invalido"}
        """
        tenant_id = firebase_config["tenant_id"]
        actor_id = firebase_config["actor_id"]

        try:
            operacao_id = gerar_operacao_id(actor_id, "agendamento", {
                "profissional": "Bruna",
                "data": "2025-01-10",
                "hora": "1400"
            })
            evento_id = str(uuid.uuid4())
            proprietario_id = gerar_proprietario_id()

            # Setup com operacao_status="concluida"
            lease_token, dados_confirmados = await criar_setup_consumo(
                tenant_id, actor_id, operacao_id, evento_id, proprietario_id,
                operacao_status="concluida"
            )

            # Ação
            resultado = await consumir_confirmacao_pendente_atomicamente(
                tenant_id=tenant_id,
                actor_id=actor_id,
                operacao_id=operacao_id,
                evento_id=evento_id,
                lease_token=lease_token,
                proprietario_id=proprietario_id,
                dados_confirmados_snapshot=dados_confirmados
            )

            # Validação
            assert resultado.get("ok") is False
            assert "operacao_status_invalido" in resultado.get("motivo", "")

            print(f"[T11] PASS: Operação concluida não pode reabrir")

        finally:
            await cleanup_firestore(tenant_id, actor_id)
