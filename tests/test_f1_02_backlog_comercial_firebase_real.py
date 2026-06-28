"""
F1-02: Testes de Backlog Comercial

Testes obrigatórios:
- listar_por_status
- interessados sem agendamento
- clientes em negociação
- retorno pendente
- clientes inativos
- resumo comercial
- multi-tenant isolado
- nenhum dados em sessão
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.backlog_comercial_service import (
    listar_por_status,
    listar_interessados_sem_agendamento,
    listar_clientes_em_negociacao,
    listar_retorno_pendente,
    listar_clientes_inativos,
    gerar_resumo_comercial,
    formatar_resumo_para_mensagem,
    formatar_lista_para_mensagem
)
from services.firestore_client import get_db


class TestF102BacklogComercial:
    """Testes de backlog comercial determinístico"""

    TENANT = "f1_02_tenant_teste"
    CLIENTE_1 = "whatsapp:1111111111"
    CLIENTE_2 = "whatsapp:2222222222"
    CLIENTE_3 = "whatsapp:3333333333"
    CLIENTE_4 = "whatsapp:4444444444"

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
    async def test_listar_por_status_novo(self):
        """Lista clientes com status 'novo'"""
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_1
        ).set({
            "lead_status": "novo",
            "lead_status_updated_at": now,
            "ultima_interacao": now,
            "total_agendamentos": 0
        })

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_2
        ).set({
            "lead_status": "interessado",
            "lead_status_updated_at": now,
            "ultima_interacao": now,
            "total_agendamentos": 0
        })

        clientes = await listar_por_status(self.TENANT, "novo")

        assert len(clientes) == 1, f"Esperado 1 cliente novo, obtido {len(clientes)}"
        assert clientes[0]["lead_status"] == "novo"
        print(f"[OK] listar_por_status('novo') retornou 1 cliente")

    @pytest.mark.asyncio
    async def test_interessados_sem_agendamento(self):
        """Lista interessados que nunca agendaram"""
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_1
        ).set({
            "lead_status": "interessado",
            "total_agendamentos": 0,
            "ultima_interacao": now
        })

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_2
        ).set({
            "lead_status": "interessado",
            "total_agendamentos": 1,
            "ultima_interacao": now
        })

        clientes = await listar_interessados_sem_agendamento(self.TENANT)

        assert len(clientes) == 1, f"Esperado 1 interessado sem agendamento, obtido {len(clientes)}"
        assert clientes[0]["total_agendamentos"] == 0
        print(f"[OK] interessados_sem_agendamento retornou 1 cliente")

    @pytest.mark.asyncio
    async def test_clientes_em_negociacao(self):
        """Lista clientes em negociação"""
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_1
        ).set({
            "lead_status": "negociacao",
            "ultima_interacao": now
        })

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_2
        ).set({
            "lead_status": "agendado",
            "ultima_interacao": now
        })

        clientes = await listar_clientes_em_negociacao(self.TENANT)

        assert len(clientes) == 1, f"Esperado 1 cliente em negociacao, obtido {len(clientes)}"
        assert clientes[0]["lead_status"] == "negociacao"
        print(f"[OK] clientes_em_negociacao retornou 1 cliente")

    @pytest.mark.asyncio
    async def test_retorno_pendente(self):
        """Lista clientes com retorno pendente"""
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_1
        ).set({
            "lead_status": "retorno_pendente",
            "ultima_interacao": now
        })

        clientes = await listar_retorno_pendente(self.TENANT)

        assert len(clientes) == 1
        assert clientes[0]["lead_status"] == "retorno_pendente"
        print(f"[OK] retorno_pendente retornou 1 cliente")

    @pytest.mark.asyncio
    async def test_clientes_inativos(self):
        """Lista clientes inativos"""
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_1
        ).set({
            "lead_status": "inativo",
            "ultima_interacao": now
        })

        clientes = await listar_clientes_inativos(self.TENANT)

        assert len(clientes) == 1
        assert clientes[0]["lead_status"] == "inativo"
        print(f"[OK] clientes_inativos retornou 1 cliente")

    @pytest.mark.asyncio
    async def test_resumo_comercial(self):
        """Gera resumo comercial com contagem de status"""
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_1
        ).set({"lead_status": "novo", "ultima_interacao": now})

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_2
        ).set({"lead_status": "interessado", "ultima_interacao": now})

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_3
        ).set({"lead_status": "agendado", "ultima_interacao": now})

        db.collection("Clientes").document(self.TENANT).collection("Clientes").document(
            self.CLIENTE_4
        ).set({"lead_status": "atendido", "ultima_interacao": now})

        resumo = await gerar_resumo_comercial(self.TENANT)

        assert resumo.get("total_clientes") == 4, f"Esperado 4 clientes, obtido {resumo.get('total_clientes')}"
        assert resumo.get("total_novo") == 1
        assert resumo.get("total_interessado") == 1
        assert resumo.get("total_agendado") == 1
        assert resumo.get("total_atendido") == 1
        print(f"[OK] resumo_comercial contou 4 clientes corretamente")

    @pytest.mark.asyncio
    async def test_multitenant_isolado(self):
        """Dois tenants isolados"""
        TENANT_A = "f1_02_tenant_a"
        TENANT_B = "f1_02_tenant_b"
        db = get_db()
        now = datetime.now().isoformat()

        db.collection("Clientes").document(TENANT_A).collection("Clientes").document(
            self.CLIENTE_1
        ).set({"lead_status": "novo", "ultima_interacao": now})

        db.collection("Clientes").document(TENANT_B).collection("Clientes").document(
            self.CLIENTE_1
        ).set({"lead_status": "interessado", "ultima_interacao": now})

        clientes_a = await listar_por_status(TENANT_A, "novo")
        clientes_b = await listar_por_status(TENANT_B, "novo")

        assert len(clientes_a) == 1, f"TENANT_A: esperado 1 novo, obtido {len(clientes_a)}"
        assert len(clientes_b) == 0, f"TENANT_B: esperado 0 novo, obtido {len(clientes_b)}"

        clientes_b_int = await listar_por_status(TENANT_B, "interessado")
        assert len(clientes_b_int) == 1

        print(f"[OK] Multi-tenant isolado validado")

        db.collection("Clientes").document(TENANT_A).delete()
        db.collection("Clientes").document(TENANT_B).delete()

    @pytest.mark.asyncio
    async def test_nenhum_dado_em_sessao(self):
        """Backlog nao armazena em Sessoes"""
        import inspect
        from services import backlog_comercial_service

        source = inspect.getsource(backlog_comercial_service)

        # Remove comentarios para busca exata
        linhas_codigo = [
            linha for linha in source.split('\n')
            if not linha.strip().startswith('#') and not linha.strip().startswith('"""') and not linha.strip().startswith("'''")
        ]
        codigo_sem_comentario = '\n'.join(linhas_codigo)

        assert "Sessoes" not in codigo_sem_comentario, "backlog_comercial_service usa Sessoes"
        assert "salvar_contexto" not in codigo_sem_comentario, "backlog_comercial_service usa contexto temporario"

        print(f"[OK] Sessao nao contem dados de backlog (arquitetura validada)")

    @pytest.mark.asyncio
    async def test_formatacao_resumo(self):
        """Formata resumo para mensagem legivel"""
        resumo = {
            "total_clientes": 10,
            "total_novo": 2,
            "total_interessado": 3,
            "total_negociacao": 2,
            "total_agendado": 2,
            "total_atendido": 1,
            "total_retorno_pendente": 0,
            "total_inativo": 0
        }

        mensagem = formatar_resumo_para_mensagem(resumo)

        assert "Resumo Comercial" in mensagem
        assert "10" in mensagem
        assert "Novo: 2" in mensagem
        assert "Interessado: 3" in mensagem

        print(f"[OK] Formatacao de resumo validada")


async def main():
    """Executa testes"""
    print("\n" + "="*80)
    print("F1-02: TESTES DE BACKLOG COMERCIAL")
    print("="*80 + "\n")

    test_suite = TestF102BacklogComercial()
    tests = [
        ("Listar por status (novo)", test_suite.test_listar_por_status_novo),
        ("Interessados sem agendamento", test_suite.test_interessados_sem_agendamento),
        ("Clientes em negociacao", test_suite.test_clientes_em_negociacao),
        ("Retorno pendente", test_suite.test_retorno_pendente),
        ("Clientes inativos", test_suite.test_clientes_inativos),
        ("Resumo comercial", test_suite.test_resumo_comercial),
        ("Multi-tenant isolado", test_suite.test_multitenant_isolado),
        ("Nenhum dado em sessao", test_suite.test_nenhum_dado_em_sessao),
        ("Formatacao de resumo", test_suite.test_formatacao_resumo),
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
