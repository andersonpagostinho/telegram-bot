import pytest
import pytest_asyncio
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest_asyncio.fixture
async def firebase_services():
    from services.firebase_service_async import (
        buscar_dado_em_path,
        atualizar_dado_em_path,
        deletar_dado_em_path
    )

    return {
        "buscar": buscar_dado_em_path,
        "salvar": atualizar_dado_em_path,
        "deletar": deletar_dado_em_path
    }


@pytest_asyncio.fixture
async def test_tenant_id():
    return f"tenant_lote3_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def cleanup_firestore(firebase_services, test_tenant_id):
    yield

    try:
        await firebase_services["deletar"](f"Clientes/{test_tenant_id}")
    except Exception:
        pass


# ========== GRUPO B: FIXTURES PARA FIREBASE REAL ==========

@pytest_asyncio.fixture
async def db_real():
    """Acesso ao Firebase Firestore real."""
    from services.firestore_client import get_db
    return get_db()


@pytest_asyncio.fixture
async def grupo_b_tenant_id():
    """Tenant isolado para Grupo B."""
    return f"p1_clienteprofile_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def grupo_b_cliente_id():
    """Cliente isolado para Grupo B."""
    return f"cliente_{uuid.uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def grupo_b_cleanup(db_real, grupo_b_tenant_id):
    """Cleanup automático para Grupo B."""
    yield

    try:
        # Deletar ClienteProfiles
        profiles = db_real.collection("Clientes").document(grupo_b_tenant_id).collection(
            "ClienteProfiles"
        ).stream()
        for doc in profiles:
            doc.reference.delete()

        # Deletar documento tenant
        db_real.collection("Clientes").document(grupo_b_tenant_id).delete()
    except Exception:
        pass
