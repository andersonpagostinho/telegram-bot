import pytest
import pytest_asyncio
import uuid
import sys
import os
import io
from pathlib import Path
from dotenv import load_dotenv

# [ENCODING FIX] Force UTF-8 output for emoji support in Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env first
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar fixtures Firebase real de conftest_fb
from tests.conftest_fb import firebase_config, firebase_contexto


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


# ========== USO 2 FIXTURES: ALTERNATIVAS COM DURATIONS ==========

@pytest_asyncio.fixture
async def uso2_t1_setup(firebase_services):
    """
    Setup USO 2 Test Tenant 1: uso2_t1
    - Profissionais: Bruna (corte 60min), Gloria (corte 60min), Joana (corte 50min)
    - Service: corte
    """
    tenant_id = "uso2_t1"

    # Create tenant root
    await firebase_services["salvar"](f"Clientes/{tenant_id}", {"_setup": "uso2_t1"})

    # Create professionais with durations
    profissionais_data = {
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte", "escova"],
            "duracoes": {"corte": 60, "escova": 45}
        },
        "Gloria": {
            "nome": "Gloria",
            "servicos": ["corte", "pedicure"],
            "duracoes": {"corte": 60, "pedicure": 50}
        },
        "Joana": {
            "nome": "Joana",
            "servicos": ["corte", "escova", "manicure"],
            "duracoes": {"corte": 50, "escova": 55, "manicure": 40}
        }
    }

    for prof_nome, prof_data in profissionais_data.items():
        # Create operational config in Profissionais
        await firebase_services["salvar"](
            f"Clientes/{tenant_id}/Profissionais/{prof_nome}",
            prof_data
        )
        # Create identity in Atores
        await firebase_services["salvar"](
            f"Clientes/{tenant_id}/Atores/{prof_nome}",
            {
                "nome": prof_nome,
                "tipo_usuario": "profissional"
            }
        )

    yield tenant_id

    # Cleanup
    try:
        await firebase_services["deletar"](f"Clientes/{tenant_id}")
        await firebase_services["deletar"](f"Atores/{tenant_id}")
    except Exception:
        pass


@pytest_asyncio.fixture
async def uso2_t2_setup(firebase_services):
    """
    Setup USO 2 Test Tenant 2: uso2_t2
    - Profissionais: Bruna (corte 60min), Carla (corte 45min), Rafael (no corte)
    - Tests: Duration configured vs not configured
    """
    tenant_id = "uso2_t2"

    await firebase_services["salvar"](f"Clientes/{tenant_id}", {"_setup": "uso2_t2"})

    profissionais_data = {
        "Bruna": {
            "nome": "Bruna",
            "servicos": ["corte"],
            "duracoes": {"corte": 60}
        },
        "Carla": {
            "nome": "Carla",
            "servicos": ["corte", "coloracao"],
            "duracoes": {"corte": 45, "coloracao": 120}
        },
        "Rafael": {
            "nome": "Rafael",
            "servicos": ["manicure", "pedicure"],
            "duracoes": {"manicure": 30, "pedicure": 35}
            # NOTE: NO corte configured
        }
    }

    for prof_nome, prof_data in profissionais_data.items():
        # Create operational config in Profissionais
        await firebase_services["salvar"](
            f"Clientes/{tenant_id}/Profissionais/{prof_nome}",
            prof_data
        )
        # Create identity in Atores
        await firebase_services["salvar"](
            f"Clientes/{tenant_id}/Atores/{prof_nome}",
            {
                "nome": prof_nome,
                "tipo_usuario": "profissional"
            }
        )

    yield tenant_id

    try:
        await firebase_services["deletar"](f"Clientes/{tenant_id}")
        await firebase_services["deletar"](f"Atores/{tenant_id}")
    except Exception:
        pass


@pytest_asyncio.fixture
async def uso2_t3_and_t4_setup(firebase_services):
    """
    Setup USO 2 Test Tenants 3 & 4: Multi-tenant isolation test
    - Tenant 1 (uso2_t3): Gloria corte 60min
    - Tenant 2 (uso2_t4): Gloria corte 35min (different!)
    """
    tenant_t3 = "uso2_t3"
    tenant_t4 = "uso2_t4"

    # Tenant 3: Gloria 60min
    await firebase_services["salvar"](f"Clientes/{tenant_t3}", {"_setup": "uso2_t3"})
    await firebase_services["salvar"](
        f"Clientes/{tenant_t3}/Profissionais/Gloria",
        {
            "nome": "Gloria",
            "servicos": ["corte"],
            "duracoes": {"corte": 60}
        }
    )
    await firebase_services["salvar"](
        f"Clientes/{tenant_t3}/Atores/Gloria",
        {
            "nome": "Gloria",
            "tipo_usuario": "profissional"
        }
    )

    # Tenant 4: Gloria 35min
    await firebase_services["salvar"](f"Clientes/{tenant_t4}", {"_setup": "uso2_t4"})
    await firebase_services["salvar"](
        f"Clientes/{tenant_t4}/Profissionais/Gloria",
        {
            "nome": "Gloria",
            "servicos": ["corte"],
            "duracoes": {"corte": 35}
        }
    )
    await firebase_services["salvar"](
        f"Clientes/{tenant_t4}/Atores/Gloria",
        {
            "nome": "Gloria",
            "tipo_usuario": "profissional"
        }
    )

    yield (tenant_t3, tenant_t4)

    try:
        for tenant in [tenant_t3, tenant_t4]:
            await firebase_services["deletar"](f"Clientes/{tenant}")
            await firebase_services["deletar"](f"Atores/{tenant}")
    except Exception:
        pass


@pytest_asyncio.fixture
async def uso2_t5_setup(firebase_services):
    """
    Setup USO 2 Test Tenant 5: uso2_t5
    - For testing None handling (unknown service/professional)
    """
    tenant_id = "uso2_t5"

    await firebase_services["salvar"](f"Clientes/{tenant_id}", {"_setup": "uso2_t5"})

    yield tenant_id

    try:
        await firebase_services["deletar"](f"Clientes/{tenant_id}")
    except Exception:
        pass
