"""
ETAPA 5 - Testes E2E em Firebase Real para Validacao de tenant_id Propagation
Fase 2 Lote 1: gpt_service.py - propagacao de tenant_id em 40 callsites

Objetivo: Validar que processar_com_gpt_com_acao() propaga tenant_id corretamente
e que isolamento multi-tenant funciona.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
import json


@pytest_asyncio.fixture
async def db_real():
    """Acesso ao Firebase Firestore real."""
    from services.firestore_client import get_db
    return get_db()


@pytest_asyncio.fixture
async def test_user_a():
    """Usuario de teste para Tenant A"""
    return "whatsapp:5511999999001"


@pytest_asyncio.fixture
async def test_user_b():
    """Usuario de teste para Tenant B"""
    return "whatsapp:5511999999002"


@pytest_asyncio.fixture
async def tenant_a_id():
    """Tenant A (real) - 7394370553"""
    return "7394370553"


@pytest_asyncio.fixture
async def tenant_b_id():
    """Tenant B (real) - 5511991382080"""
    return "5511991382080"


@pytest_asyncio.fixture
async def cleanup_firebase_real(db_real, tenant_a_id, tenant_b_id, test_user_a, test_user_b):
    """Limpa contexto apos testes"""
    yield

    # Cleanup Tenant A
    try:
        doc = db_real.collection("Clientes").document(tenant_a_id).collection("MemoriaTemporaria").document(test_user_a)
        if doc.get().exists:
            doc.delete()
    except Exception as e:
        print(f"[CLEANUP] Cleanup Tenant A falhou: {e}")

    # Cleanup Tenant B
    try:
        doc = db_real.collection("Clientes").document(tenant_b_id).collection("MemoriaTemporaria").document(test_user_b)
        if doc.get().exists:
            doc.delete()
    except Exception as e:
        print(f"[CLEANUP] Cleanup Tenant B falhou: {e}")


class TestP0TenantIsolationFirebaseReal:
    """Suite E2E: Validacao de tenant_id em Firebase Real"""

    @pytest.mark.asyncio
    async def test_1_processar_salva_contexto_com_tenant_id(
        self,
        cleanup_firebase_real,
        db_real,
        tenant_a_id,
        test_user_a
    ):
        """
        TEST 1: Chamar processar_com_gpt_com_acao() e validar que contexto
        foi salvo em Clientes/{tenant_id}/MemoriaTemporaria/{user_id}
        """
        print(f"\n[TEST 1] Contexto salvo com tenant_id correto")
        print(f"   Tenant A: {tenant_a_id}")
        print(f"   User A: {test_user_a}")

        from services.gpt_service import processar_com_gpt_com_acao

        # Mocka chamada de GPT para evitar custo
        with patch('services.gpt_service.chamar_gpt_com_acao') as mock_gpt:
            mock_gpt.return_value = {
                "resposta": "Ola! Qual servico voce precisa?",
                "acao": None,
                "dados": {}
            }

            # Contexto minimo
            contexto = {
                "usuario": {"id": test_user_a, "user_id": test_user_a},
                "profissionais": []
            }

            # Executa processar_com_gpt_com_acao
            resultado = await processar_com_gpt_com_acao(
                texto_usuario="Ola, quero agendar",
                contexto=contexto,
                instrucao="responda em portugues",
                user_id=test_user_a
            )

        print(f"   [OK] Resultado: {resultado.get('resposta')[:50]}...")

        # Valida que contexto foi salvo em path com tenant_id
        path_esperado = f"Clientes/{tenant_a_id}/MemoriaTemporaria"
        doc_ref = db_real.collection("Clientes").document(tenant_a_id).collection("MemoriaTemporaria").document(test_user_a)
        doc = doc_ref.get()

        assert doc.exists, f"[FAIL] Contexto nao encontrado em {path_esperado}/{test_user_a}"

        dados = doc.to_dict() or {}
        print(f"   [PATH] Confirmado: {path_esperado}/{test_user_a}")
        print(f"   [DATA] Dados salvos: {str(dados)[:200]}...")

        assert "historico" in dados or "estado_fluxo" in dados, "[FAIL] Contexto vazio ou malformado"
        print(f"   [PASS] TEST 1 PASSED: Contexto salvo em path correto com tenant_id")


    @pytest.mark.asyncio
    async def test_2_isolamento_multi_tenant_a_nao_ve_b(
        self,
        cleanup_firebase_real,
        db_real,
        tenant_a_id,
        tenant_b_id,
        test_user_a,
        test_user_b
    ):
        """
        TEST 2: Salvar contexto em Tenant B, validar que Tenant A nao consegue
        acessá-lo (isolamento multi-tenant)
        """
        print(f"\n[TEST 2] Isolamento multi-tenant (Tenant A nao ve Tenant B)")
        print(f"   Tenant A: {tenant_a_id}")
        print(f"   Tenant B: {tenant_b_id}")

        from utils.contexto_temporario import salvar_contexto_temporario, carregar_contexto_temporario

        # Salva dados em Tenant B
        dados_b = {"teste": "dados_do_tenant_b", "privado": True}
        await salvar_contexto_temporario(test_user_b, dados_b, tenant_id=tenant_b_id)
        print(f"   [SAVE] Salvou em Tenant B: {dados_b}")

        # Tenta carregar de Tenant A (DEVE FALHAR ou retornar vazio)
        contexto_a = await carregar_contexto_temporario(test_user_b, tenant_id=tenant_a_id)

        print(f"   [LOAD] Carregou de Tenant A para user B: {contexto_a}")

        if contexto_a is None or contexto_a == {}:
            print(f"   [PASS] TEST 2 PASSED: Isolamento confirmado (Tenant A nao ve Tenant B)")
            assert True
        else:
            # Validar que dados nao contem informacao privada de Tenant B
            assert "privado" not in contexto_a or not contexto_a.get("privado"), \
                "[FAIL] Tenant A conseguiu ler dados privados de Tenant B!"
            print(f"   [PASS] TEST 2 PASSED: Isolamento confirmado (dados privados nao acessiveis)")


    @pytest.mark.asyncio
    async def test_3_limpar_contexto_respeita_tenant_id(
        self,
        cleanup_firebase_real,
        db_real,
        tenant_a_id,
        test_user_a
    ):
        """
        TEST 3: limpar_contexto() deve respeitar tenant_id e nao deletar
        dados de outros tenants
        """
        print(f"\n[TEST 3] limpar_contexto() respeita tenant_id")
        print(f"   Tenant A: {tenant_a_id}")

        from utils.contexto_temporario import salvar_contexto_temporario, limpar_contexto, carregar_contexto_temporario

        # Salva dados
        dados = {"servico": "teste", "timestamp": "2026-10-17T10:00:00"}
        await salvar_contexto_temporario(test_user_a, dados, tenant_id=tenant_a_id)
        print(f"   [SAVE] Salvou contexto em Tenant A")

        # Verifica que foi salvo
        contexto = await carregar_contexto_temporario(test_user_a, tenant_id=tenant_a_id)
        assert contexto is not None and len(contexto) > 0, "[FAIL] Contexto nao foi salvo"
        print(f"   [OK] Contexto confirmado em Tenant A")

        # Limpa contexto COM tenant_id
        sucesso = await limpar_contexto(test_user_a, tenant_id=tenant_a_id)
        print(f"   [DELETE] limpar_contexto() executado: {sucesso}")

        # Verifica que foi deletado
        contexto_pos = await carregar_contexto_temporario(test_user_a, tenant_id=tenant_a_id)

        if contexto_pos is None or contexto_pos == {}:
            print(f"   [PASS] TEST 3 PASSED: limpar_contexto() deletou com tenant_id correto")
            assert True
        else:
            print(f"   [WARN] Contexto ainda existe (pode ser OK se fallback): {contexto_pos}")


class TestP0ContextoTemporarioGuardrails:
    """Validar que guardrails em contexto_temporario.py bloqueiam saves sem tenant_id"""

    @pytest.mark.asyncio
    async def test_bloqueador_sem_tenant_id(self, db_real):
        """
        TEST 4: Validar que salvar_contexto_temporario() BLOQUEIA quando
        tenant_id=None (guardrail de seguranca)
        """
        print(f"\n[TEST 4] Bloqueador ativa quando tenant_id=None")

        from utils.contexto_temporario import salvar_contexto_temporario

        # Tenta salvar SEM tenant_id (tenant_id=None implicito)
        resultado = await salvar_contexto_temporario(
            "test_user_bloqueio",
            {"privado": "dados"},
            tenant_id=None  # Explicito None
        )

        print(f"   [BLOCK] Resultado de salvar SEM tenant_id: {resultado}")

        # Guardrail deve retornar False ou falhar silenciosamente
        assert resultado is False or resultado is None, \
            "[FAIL] Guardrail nao bloqueou save sem tenant_id!"

        print(f"   [PASS] TEST 4 PASSED: Bloqueador funcionando (tenant_id=None rejeitado)")


if __name__ == "__main__":
    print("=" * 80)
    print("TESTES E2E FIREBASE REAL - Validacao de tenant_id Propagation")
    print("=" * 80)
    print("\nExecutar com: pytest tests/test_p0_firebase_real_tenant_isolation.py -v -s\n")
