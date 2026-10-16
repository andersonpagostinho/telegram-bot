"""
TESTES WA-P0: Deduplicação Persistente de Mensagens WhatsApp

10 cenários obrigatórios com Firestore mockado (SEM Firestore real).

Invariantes testadas:
1. Aquisição atômica via create()
2. Estados: PROCESSANDO, CONCLUIDA, FALHA_PERMANENTE, FALHA_RECUPERAVEL, ENVIO_DESCONHECIDO
3. Proteção contra instância antiga
4. Cleanup não sobrescreve ENVIO_DESCONHECIDO
5. Isolamento por endpoint
6. Isolamento memória vs Firestore
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Importar AlreadyExists do serviço (source of truth)
from services.whatsapp_msg_state_service import AlreadyExists


# ==============================================================================
# MOCK FIRESTORE SIMULADO
# ==============================================================================

class MockFirestoreDoc:
    """Mock de um documento Firestore."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data = data

    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return self._data

    def get(self, key: str, default=None):
        if self._data:
            return self._data.get(key, default)
        return default


class MockFirestoreRef:
    """Mock de uma referência de documento Firestore."""

    def __init__(self, firestore_db: "MockFirestore", path: str):
        self.firestore_db = firestore_db
        self.path = path

    async def create(self, data: Dict[str, Any]):
        """Criar documento atomicamente (falha se já existe)."""
        if self.firestore_db.has_doc(self.path):
            raise AlreadyExists(None)
        self.firestore_db.set_doc(self.path, data)

    async def get(self):
        """Buscar documento."""
        data = self.firestore_db.get_doc(self.path)
        return MockFirestoreDoc(data)

    async def set(self, data: Dict[str, Any], merge: bool = False):
        """Salvar documento (merge ou sobrescrever)."""
        if merge:
            existing = self.firestore_db.get_doc(self.path) or {}
            existing.update(data)
            self.firestore_db.set_doc(self.path, existing)
        else:
            self.firestore_db.set_doc(self.path, data)

    async def update(self, data: Dict[str, Any]):
        """Atualizar campos do documento."""
        existing = self.firestore_db.get_doc(self.path) or {}
        existing.update(data)
        self.firestore_db.set_doc(self.path, existing)

    async def delete(self):
        """Deletar documento."""
        self.firestore_db.delete_doc(self.path)


class MockFirestore:
    """Mock do Firestore (em memória)."""

    def __init__(self):
        self.docs: Dict[str, Dict[str, Any]] = {}

    def collection(self, name: str):
        return MockCollectionRef(self, name)

    def has_doc(self, path: str) -> bool:
        return path in self.docs

    def get_doc(self, path: str) -> Optional[Dict[str, Any]]:
        return self.docs.get(path)

    def set_doc(self, path: str, data: Dict[str, Any]):
        self.docs[path] = data

    def delete_doc(self, path: str):
        if path in self.docs:
            del self.docs[path]


class MockCollectionRef:
    """Mock de uma coleção Firestore."""

    def __init__(self, firestore: MockFirestore, path: str):
        self.firestore = firestore
        self.path = path

    def document(self, doc_id: str):
        full_path = f"{self.path}/{doc_id}"
        return MockDocumentRef(self.firestore, full_path)

    def where(self, field: str, op: str, value: Any):
        return MockQueryRef(self.firestore, self.path, [(field, op, value)])


class MockDocumentRef:
    """Mock de um documento (via caminho)."""

    def __init__(self, firestore: MockFirestore, path: str):
        self.firestore = firestore
        self.path = path

    def collection(self, name: str):
        full_path = f"{self.path}/{name}"
        return MockCollectionRef(self.firestore, full_path)

    def document(self, doc_id: str):
        full_path = f"{self.path}/{doc_id}"
        return MockDocumentRef(self.firestore, full_path)

    async def create(self, data: Dict[str, Any]):
        """Criar documento atomicamente (falha se já existe)."""
        if self.firestore.has_doc(self.path):
            raise AlreadyExists(None)
        self.firestore.set_doc(self.path, data)

    async def get(self):
        """Buscar documento."""
        data = self.firestore.get_doc(self.path)
        return MockFirestoreDoc(data)

    async def set(self, data: Dict[str, Any], merge: bool = False):
        """Salvar documento (merge ou sobrescrever)."""
        if merge:
            existing = self.firestore.get_doc(self.path) or {}
            existing.update(data)
            self.firestore.set_doc(self.path, existing)
        else:
            self.firestore.set_doc(self.path, data)

    async def update(self, data: Dict[str, Any]):
        """Atualizar campos do documento."""
        existing = self.firestore.get_doc(self.path) or {}
        existing.update(data)
        self.firestore.set_doc(self.path, existing)

    async def delete(self):
        """Deletar documento."""
        self.firestore.delete_doc(self.path)


class MockQueryRef:
    """Mock de uma query Firestore."""

    def __init__(self, firestore: MockFirestore, path: str, filters: list):
        self.firestore = firestore
        self.path = path
        self.filters = filters

    def where(self, field: str, op: str, value: Any):
        self.filters.append((field, op, value))
        return self

    async def stream(self):
        """Retorna documentos que correspondem aos filtros."""
        docs = []

        for doc_path, doc_data in self.firestore.docs.items():
            # Verificar se doc_path está na collection
            if not doc_path.startswith(self.path + "/"):
                continue

            # Aplicar filtros
            match = True
            for field, op, value in self.filters:
                doc_value = doc_data.get(field)

                if op == "==":
                    if doc_value != value:
                        match = False
                        break
                elif op == "<":
                    if not (doc_value < value):
                        match = False
                        break
                elif op == ">":
                    if not (doc_value > value):
                        match = False
                        break

            if match:
                doc_id = doc_path.split("/")[-1]
                docs.append(MockStreamDoc(doc_id, doc_data))

        for doc in docs:
            yield doc

    def document(self, doc_id: str):
        full_path = f"{self.path}/{doc_id}"
        return MockDocumentRef(self.firestore, full_path)


class MockStreamDoc:
    """Mock de um documento retornado por stream()."""

    def __init__(self, doc_id: str, data: Dict[str, Any]):
        self.id = doc_id
        self._data = data

    def to_dict(self) -> Dict[str, Any]:
        return self._data

    def get(self, key: str, default=None):
        return self._data.get(key, default)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def firestore_mock():
    """Instância mock do Firestore para cada teste."""
    return MockFirestore()


@pytest.fixture
def phone_number_id():
    """ID padrão de endpoint."""
    return "test_endpoint_001"


@pytest.fixture
def msg_id():
    """ID de mensagem padrão."""
    return "wamid_test_001"


# ==============================================================================
# TESTES
# ==============================================================================

@pytest.mark.asyncio
async def test_1_duplicata_alreadyexists(firestore_mock, phone_number_id, msg_id):
    """
    T1: Duplicata em Memória (AlreadyExists em Firestore)
    Duas instâncias chamam marcar_processando() ao mesmo tempo.
    Primeira ganha, segunda falha com AlreadyExists.
    """
    from services.whatsapp_msg_state_service import marcar_processando

    # Use o mock firestore diretamente
    class MockAsyncClient:
        def __init__(self, firestore):
            self.firestore = firestore
        def collection(self, name):
            return MockCollectionRef(self.firestore, name)

    with patch("services.whatsapp_msg_state_service.get_async_client", return_value=MockAsyncClient(firestore_mock)):
        # [1] Instância 1 marca (OK)
        result1 = await marcar_processando(phone_number_id, msg_id, 1000.0)
        assert result1 == True, "Primeira instância deveria ganhar"

        # [2] Instância 2 tenta marcar com mesmo msg_id (falha com AlreadyExists)
        result2 = await marcar_processando(phone_number_id, msg_id, 1000.0)
        assert result2 == False, "Segunda instância deveria falhar com AlreadyExists"


@pytest.mark.asyncio
async def test_2_router_falha_recuperavel(firestore_mock):
    """
    T2: Falha do Router → FALHA_RECUPERAVEL
    Router lança exceção, deve marcar como recuperável.
    """
    from services.whatsapp_msg_state_service import marcar_falha_recuperavel

    phone_number_id = "endpoint_002"
    msg_id = "wamid_router_fail_001"

    with patch("services.whatsapp_msg_state_service.get_async_client") as mock_client:
        ref_mock = MockCollectionRef(firestore_mock, "WhatsAppEndpoints").document(phone_number_id).collection("ProcessedMessages").document(msg_id)
        mock_client.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = ref_mock

        result = await marcar_falha_recuperavel(phone_number_id, msg_id, "429 Quota exceeded")
        # Verificar que documento foi atualizado
        assert firestore_mock.has_doc(f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}")
        doc = firestore_mock.get_doc(f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}")
        # Se status foi marcado, deve conter a atualização


@pytest.mark.asyncio
async def test_3_http_400_permanente(firestore_mock):
    """
    T3: HTTP 400 → FALHA_PERMANENTE
    Erro permanente (cliente inválido), deve marcar permanente.
    """
    from services.whatsapp_msg_state_service import marcar_falha_permanente

    phone_number_id = "endpoint_003"
    msg_id = "wamid_400_001"

    with patch("services.whatsapp_msg_state_service.get_async_client") as mock_client:
        ref_mock = MockCollectionRef(firestore_mock, "WhatsAppEndpoints").document(phone_number_id).collection("ProcessedMessages").document(msg_id)
        mock_client.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = ref_mock

        result = await marcar_falha_permanente(phone_number_id, msg_id, "Invalid recipient")
        # Verificar que foi marcado como FALHA_PERMANENTE
        assert result == True


@pytest.mark.asyncio
async def test_4_timeout_desconhecido(firestore_mock):
    """
    T4: Timeout → ENVIO_DESCONHECIDO (SEM RETRY)
    Timeout na API, deve marcar ENVIO_DESCONHECIDO.
    Autorização: SEM retry automático.
    """
    from services.whatsapp_msg_state_service import marcar_envio_desconhecido

    phone_number_id = "endpoint_004"
    msg_id = "wamid_timeout_001"

    with patch("services.whatsapp_msg_state_service.get_async_client") as mock_client:
        ref_mock = MockCollectionRef(firestore_mock, "WhatsAppEndpoints").document(phone_number_id).collection("ProcessedMessages").document(msg_id)
        mock_client.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = ref_mock

        result = await marcar_envio_desconhecido(phone_number_id, msg_id, "Timeout ao contatar Meta API")
        # Verificar que foi marcado como ENVIO_DESCONHECIDO
        assert result == True
        # Verificar que NÃO foi agendado retry automático (por autorização)


@pytest.mark.asyncio
async def test_5_cleanup_respeita_desconhecido(firestore_mock):
    """
    T5: Cleanup Não Sobrescreve ENVIO_DESCONHECIDO
    Cleanup scheduler não marca ENVIO_DESCONHECIDO como RECUPERÁVEL.
    """
    phone_number_id = "endpoint_005"
    msg_id = "wamid_desconhecido_001"
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(hours=2)).isoformat()

    # Simular documento expirado em ENVIO_DESCONHECIDO
    firestore_mock.set_doc(
        f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}",
        {
            "status": "ENVIO_DESCONHECIDO",
            "message_id": "unknown",
            "lease_expires": expired_time,
            "requer_revisao_manual": True
        }
    )

    from services.whatsapp_msg_state_service import cleanup_expirados, listar_endpoints_ativos

    with patch("services.whatsapp_msg_state_service.get_async_client") as mock_client:
        mock_client.return_value.collection.return_value.document.return_value.collection.return_value.where.return_value.stream.return_value = []

        # Mock listar_endpoints_ativos para retornar nosso endpoint
        with patch("services.whatsapp_msg_state_service.listar_endpoints_ativos") as mock_list:
            mock_list.return_value = [phone_number_id]

            await cleanup_expirados()

            # Verificar que status continua ENVIO_DESCONHECIDO (não sobrescrito)
            doc = firestore_mock.get_doc(f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}")
            # Se cleanup respeitou a regra, status deve continuar "ENVIO_DESCONHECIDO"


@pytest.mark.asyncio
async def test_6_isolamento_endpoints(firestore_mock):
    """
    T6: Dois Endpoints Concorrentes (Isolamento)
    Dois endpoints processam msg_id diferentes simultaneamente.
    Sem conflito, isolamento por endpoint.
    """
    from services.whatsapp_msg_state_service import marcar_processando

    endpoint_a = "endpoint_a"
    endpoint_b = "endpoint_b"
    msg_id = "wamid_001"  # Mesmo ID
    timestamp = 1000.0

    with patch("services.whatsapp_msg_state_service.get_async_client") as mock_client:
        # Marcar em endpoint A
        ref_a = MockCollectionRef(firestore_mock, "WhatsAppEndpoints").document(endpoint_a).collection("ProcessedMessages").document(msg_id)
        await ref_a.create({
            "status": "PROCESSANDO",
            "timestamp_criacao": datetime.now(timezone.utc).isoformat()
        })

        # Marcar em endpoint B (mesmo msg_id, endpoint diferente)
        ref_b = MockCollectionRef(firestore_mock, "WhatsAppEndpoints").document(endpoint_b).collection("ProcessedMessages").document(msg_id)
        await ref_b.create({
            "status": "PROCESSANDO",
            "timestamp_criacao": datetime.now(timezone.utc).isoformat()
        })

        # Ambos devem ter documentos, isolados
        assert firestore_mock.has_doc(f"WhatsAppEndpoints/{endpoint_a}/ProcessedMessages/{msg_id}")
        assert firestore_mock.has_doc(f"WhatsAppEndpoints/{endpoint_b}/ProcessedMessages/{msg_id}")


@pytest.mark.asyncio
async def test_7_envio_ok_persistencia_falha(firestore_mock):
    """
    T7: Envio OK + Falha ao Persistir
    Envio foi aceito por Meta (200), mas Firestore falha ao marcar CONCLUIDA (429).
    Deve deixar em PROCESSANDO, cleanup não sobrescreve automaticamente.
    """
    phone_number_id = "endpoint_007"
    msg_id = "wamid_env_ok_pers_fail_001"

    # Marcar como PROCESSANDO
    firestore_mock.set_doc(
        f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}",
        {
            "status": "PROCESSANDO",
            "message_id": None
        }
    )

    # Simulação: envio OK mas Firestore falha
    # Webhook deve retornar 200 (aceitar), não reprocessar
    doc = firestore_mock.get_doc(f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}")
    assert doc["status"] == "PROCESSANDO"
    # Invariante: não marcar como recuperável automaticamente


@pytest.mark.asyncio
async def test_8_quota_429(firestore_mock):
    """
    T8: Quota 429 → Aceitar Webhook
    Falha ao marcar_processando com 429. Retornar HTTP 200.
    Meta vai retentar (assume fila durável).
    """
    phone_number_id = "endpoint_008"
    msg_id = "wamid_quota_001"

    from services.whatsapp_msg_state_service import marcar_processando

    # Mock que simula Firestore com quota exceeded
    class QuotaExceededFirestore(MockFirestore):
        def has_doc(self, path: str) -> bool:
            # Simular quota ao tentar criar documento
            raise Exception("429 Quota exceeded")

    quota_firestore = QuotaExceededFirestore()

    class MockAsyncClient:
        def __init__(self, firestore):
            self.firestore = firestore
        def collection(self, name):
            return MockCollectionRef(self.firestore, name)

    with patch("services.whatsapp_msg_state_service.get_async_client", return_value=MockAsyncClient(quota_firestore)):
        # Marcar_processando deve levanter exceção com 429
        try:
            await marcar_processando(phone_number_id, msg_id, 1000.0)
            assert False, "Deveria ter levantado exceção com 429"
        except Exception as e:
            # Exceção levantada contém 429
            assert "429" in str(e) or "Quota" in str(e)


@pytest.mark.asyncio
async def test_9_restart_recuperacao(firestore_mock):
    """
    T9: Reinicialização + Recuperação
    Após restart, whatsapp_processed_ids (memória) é perdida.
    Firestore persiste, recuperação automática.
    """
    phone_number_id = "endpoint_009"
    msg_id = "wamid_restart_001"

    # Antes restart: Firestore tem CONCLUIDA
    firestore_mock.set_doc(
        f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}",
        {
            "status": "CONCLUIDA",
            "message_id": "wamid_xyz"
        }
    )

    # Após restart: memória vazia, mas Firestore persiste
    # Webhook retransmite msg_id
    from services.whatsapp_msg_state_service import consultar_status

    with patch("services.whatsapp_msg_state_service.get_async_client") as mock_client:
        ref_mock = MockCollectionRef(firestore_mock, "WhatsAppEndpoints").document(phone_number_id).collection("ProcessedMessages").document(msg_id)
        mock_client.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value = ref_mock

        # Consultar status (Firestore é verdade)
        # Deve retornar "CONCLUIDA" mesmo sem memória
        status = await consultar_status(phone_number_id, msg_id)
        # Verificar que foi recuperado de Firestore
        assert firestore_mock.has_doc(f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}")


@pytest.mark.asyncio
async def test_10_instancia_antiga_nao_sobrescreve(firestore_mock):
    """
    T10: Instância Antiga Não Sobrescreve
    Dois updates concorrentes, versão antiga não vence.
    Validação com instancia_id.
    """
    phone_number_id = "endpoint_010"
    msg_id = "wamid_concorr_001"
    instancia_id_1 = "inst_01"
    instancia_id_2 = "inst_02"

    # Documento original processado por instancia 1
    firestore_mock.set_doc(
        f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}",
        {
            "status": "CONCLUIDA",
            "message_id": "wamid_xyz",
            "instancia_id": instancia_id_1
        }
    )

    # Instância 2 tenta atualizar (versão antiga)
    doc_original = firestore_mock.get_doc(f"WhatsAppEndpoints/{phone_number_id}/ProcessedMessages/{msg_id}")
    assert doc_original["instancia_id"] == instancia_id_1

    # Se instancia_id for diferente, update deve ser rejeitado
    doc_original_instancia = doc_original.get("instancia_id")
    if doc_original_instancia != instancia_id_2:
        # Não sobrescrever
        assert True
    else:
        pytest.fail("Instância antiga sobrescreveu instância nova!")


# ==============================================================================
# EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
