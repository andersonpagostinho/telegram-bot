"""
F1-03: Testes de Retorno Pendente (Firebase Real)

Testes obrigatórios:
- marcar atendimento
- cliente atendido permanece antes de 15 dias
- cliente vira retorno_pendente após 15 dias
- novo agendamento remove retorno_pendente
- múltiplos clientes
- isolamento multi-tenant
- nenhuma sessão
- auditoria
- idempotência
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.retorno_pendente_service import (
    marcar_como_atendido,
    verificar_retorno_pendente,
    atualizar_retorno_pendente_tenant,
    listar_clientes_retorno_pendente,
    recuperar_de_retorno_pendente
)
from services.lead_status_service import atualizar_lead_status
from services.firestore_client import get_db


class TestF103RetornoPendente:
    """Testes de retorno pendente determinístico"""

    TENANT = "f1_03_tenant_teste"
    CLIENTE_1 = "whatsapp:1111111111"
    CLIENTE_2 = "whatsapp:2222222222"
    CLIENTE_3 = "whatsapp:3333333333"

    def setup_method(self):
        """Setup antes de cada teste"""
        db = get_db()
        try:
            db.collection("Clientes").document(self.TENANT).delete()
        except:
            pass

    def teardown_method(self):
        """Limpeza após cada teste"""
        db = get_db()
        try:
            db.collection("Clientes").document(self.TENANT).delete()
        except:
            pass

    @pytest.mark.asyncio
    async def test_marcar_como_atendido(self):
        """Marca cliente como atendido"""
        db = get_db()

        # Criar cliente atendido
        sucesso = await marcar_como_atendido(self.TENANT, self.CLIENTE_1)

        assert sucesso, "Falha ao marcar como atendido"

        # Verificar
        doc = db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).get()

        assert doc.exists
        assert doc.to_dict().get("lead_status") == "atendido"
        assert doc.to_dict().get("ultimo_atendimento") is not None

        print(f"[OK] Cliente marcado como atendido")

    @pytest.mark.asyncio
    async def test_atendido_permanece_antes_de_15_dias(self):
        """Cliente atendido permanece 'atendido' antes de 15 dias"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_5 = (agora - timedelta(days=5)).isoformat()

        # Criar cliente com atendimento há 5 dias
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_5,
            "ultima_interacao": dias_atras_5
        })

        # Verificar retorno_pendente
        deve_mudar = await verificar_retorno_pendente(
            self.TENANT,
            self.CLIENTE_1,
            dias_retorno=15
        )

        assert not deve_mudar, "Nao deveria ser retorno_pendente com 5 dias"
        print(f"[OK] Cliente atendido permanece atendido com 5 dias")

    @pytest.mark.asyncio
    async def test_atendido_vira_retorno_pendente_apos_15_dias(self):
        """Cliente atendido vira retorno_pendente após 15 dias"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_16 = (agora - timedelta(days=16)).isoformat()

        # Criar cliente com atendimento há 16 dias
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16,
            "ultima_interacao": dias_atras_16
        })

        # Verificar retorno_pendente
        deve_mudar = await verificar_retorno_pendente(
            self.TENANT,
            self.CLIENTE_1,
            dias_retorno=15
        )

        assert deve_mudar, "Deveria ser retorno_pendente com 16 dias"
        print(f"[OK] Cliente atendido vira retorno_pendente após 16 dias")

    @pytest.mark.asyncio
    async def test_atualizar_tenant_transiciona(self):
        """Atualizar tenant transiciona clientes automaticamente"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_16 = (agora - timedelta(days=16)).isoformat()

        # Criar dois clientes
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16,
            "ultima_interacao": dias_atras_16
        })

        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_2).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16,
            "ultima_interacao": dias_atras_16
        })

        # Atualizar tenant
        resumo = await atualizar_retorno_pendente_tenant(self.TENANT, dias_retorno=15)

        assert resumo["processados"] == 2, f"Processados: {resumo['processados']}"
        assert resumo["atualizados"] == 2, f"Atualizados: {resumo['atualizados']}"

        # Verificar status
        doc1 = db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).get()

        assert doc1.to_dict().get("lead_status") == "retorno_pendente"
        print(f"[OK] Atualizacao tenant transicionou 2 clientes")

    @pytest.mark.asyncio
    async def test_novo_agendamento_remove_retorno_pendente(self):
        """Novo agendamento recupera cliente de retorno_pendente"""
        db = get_db()

        # Criar cliente em retorno_pendente
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "retorno_pendente",
            "ultimo_atendimento": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        })

        # Recuperar para agendado
        sucesso = await recuperar_de_retorno_pendente(
            self.TENANT,
            self.CLIENTE_1,
            novo_status="agendado"
        )

        assert sucesso, "Falha ao recuperar"

        # Verificar
        doc = db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).get()

        assert doc.to_dict().get("lead_status") == "agendado"
        print(f"[OK] Novo agendamento removeu cliente de retorno_pendente")

    @pytest.mark.asyncio
    async def test_listar_retorno_pendente(self):
        """Lista clientes em retorno_pendente"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_16 = (agora - timedelta(days=16)).isoformat()

        # Criar clientes
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16
        })

        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_2).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16
        })

        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_3).set({
            "lead_status": "agendado"
        })

        # Listar
        clientes = await listar_clientes_retorno_pendente(self.TENANT, dias_retorno=15)

        assert len(clientes) == 2, f"Esperado 2, obtido {len(clientes)}"
        assert all(c["lead_status"] == "retorno_pendente" for c in clientes)
        print(f"[OK] Listou 2 clientes em retorno_pendente")

    @pytest.mark.asyncio
    async def test_multitenant_isolado(self):
        """Dois tenants isolados"""
        TENANT_A = "f1_03_tenant_a"
        TENANT_B = "f1_03_tenant_b"
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_16 = (agora - timedelta(days=16)).isoformat()

        # Criar clientes em tenants diferentes
        db.collection("Clientes").document(TENANT_A).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16
        })

        db.collection("Clientes").document(TENANT_B).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "agendado"
        })

        # Atualizar TENANT_A
        resumo_a = await atualizar_retorno_pendente_tenant(TENANT_A, dias_retorno=15)
        resumo_b = await atualizar_retorno_pendente_tenant(TENANT_B, dias_retorno=15)

        assert resumo_a["atualizados"] == 1
        assert resumo_b["atualizados"] == 0

        print(f"[OK] Multi-tenant isolado validado")

        db.collection("Clientes").document(TENANT_A).delete()
        db.collection("Clientes").document(TENANT_B).delete()

    @pytest.mark.asyncio
    async def test_nenhum_dado_em_sessao(self):
        """Retorno pendente não toca em Sessões"""
        import inspect
        from services import retorno_pendente_service

        source = inspect.getsource(retorno_pendente_service)

        # Remove comentários
        linhas_codigo = [
            linha for linha in source.split('\n')
            if not linha.strip().startswith('#') and not linha.strip().startswith('"""')
        ]
        codigo_sem_comentario = '\n'.join(linhas_codigo)

        assert "Sessoes" not in codigo_sem_comentario
        assert "salvar_contexto" not in codigo_sem_comentario

        print(f"[OK] Retorno pendente nao toca em Sessoes")

    @pytest.mark.asyncio
    async def test_idempotencia(self):
        """Executar múltiplas vezes não altera resultado"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_16 = (agora - timedelta(days=16)).isoformat()

        # Criar cliente
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "atendido",
            "ultimo_atendimento": dias_atras_16
        })

        # Executar múltiplas vezes
        resumo1 = await atualizar_retorno_pendente_tenant(self.TENANT, dias_retorno=15)
        resumo2 = await atualizar_retorno_pendente_tenant(self.TENANT, dias_retorno=15)
        resumo3 = await atualizar_retorno_pendente_tenant(self.TENANT, dias_retorno=15)

        # Na primeira: 1 processado, 1 atualizado
        # Na segunda e terceira: 1 processado, 0 atualizados (já está em retorno_pendente)
        assert resumo1["atualizados"] == 1
        assert resumo2["atualizados"] == 0
        assert resumo3["atualizados"] == 0

        print(f"[OK] Operacao idempotente validada")


async def main():
    """Executa testes"""
    print("\n" + "="*80)
    print("F1-03: TESTES DE RETORNO PENDENTE (FIREBASE REAL)")
    print("="*80 + "\n")

    test_suite = TestF103RetornoPendente()
    tests = [
        ("Marcar como atendido", test_suite.test_marcar_como_atendido),
        ("Atendido permanece antes de 15 dias", test_suite.test_atendido_permanece_antes_de_15_dias),
        ("Atendido vira retorno_pendente apos 15 dias", test_suite.test_atendido_vira_retorno_pendente_apos_15_dias),
        ("Atualizar tenant transiciona", test_suite.test_atualizar_tenant_transiciona),
        ("Novo agendamento remove retorno_pendente", test_suite.test_novo_agendamento_remove_retorno_pendente),
        ("Listar retorno pendente", test_suite.test_listar_retorno_pendente),
        ("Multi-tenant isolado", test_suite.test_multitenant_isolado),
        ("Nenhum dado em sessao", test_suite.test_nenhum_dado_em_sessao),
        ("Idempotencia", test_suite.test_idempotencia),
    ]

    passed = 0
    failed = 0

    for nome, teste in tests:
        try:
            test_suite.setup_method()
            await teste()
            print(f"[PASS] {nome}\n")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {nome}: {str(e)}\n")
            failed += 1
        except Exception as e:
            print(f"[ERRO] {nome}: {str(e)}\n")
            failed += 1
        finally:
            test_suite.teardown_method()

    print("="*80)
    print(f"RESULTADO: {passed} PASS / {failed} FAIL")
    print("="*80 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
