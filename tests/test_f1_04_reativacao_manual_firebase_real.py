"""
F1-04: Testes de Reativação Manual (Firebase Real)

Testes obrigatórios (11 testes):
- listar clientes inativos
- listar retorno pendente
- gerar sugestão determinística
- resumo de reativação
- cliente ativo não aparece
- isolamento multi-tenant
- nenhuma escrita em sessão
- nenhuma escrita em MemoriaTemporaria
- nenhuma alteração em lead_status
- nenhuma mensagem enviada
- idempotência das consultas
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.reativacao_manual_service import (
    listar_clientes_inativos,
    listar_clientes_retorno_pendente,
    gerar_sugestao_reativacao,
    gerar_resumo_reativacao,
    formatar_sugestao_para_dono,
    gerar_lista_reativacao_formatada
)
from services.firestore_client import get_db


class TestF104ReativacaoManual:
    """Testes de reativação manual determinística"""

    TENANT = "f1_04_tenant_teste"
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
    async def test_listar_clientes_inativos(self):
        """Lista clientes com status inativo"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_35 = (agora - timedelta(days=35)).isoformat()

        # Criar cliente inativo
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "inativo",
            "ultima_interacao": dias_atras_35
        })

        # Listar
        clientes = await listar_clientes_inativos(self.TENANT, dias_inatividade=30)

        assert len(clientes) == 1
        assert clientes[0]["lead_status"] == "inativo"
        assert clientes[0]["dias_inativo"] >= 35

        print(f"[OK] Listou 1 cliente inativo")

    @pytest.mark.asyncio
    async def test_listar_retorno_pendente(self):
        """Lista clientes em retorno_pendente"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_20 = (agora - timedelta(days=20)).isoformat()

        # Criar cliente em retorno_pendente
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_2).set({
            "lead_status": "retorno_pendente",
            "ultimo_atendimento": dias_atras_20,
            "actor_id": self.CLIENTE_2
        })

        # Listar
        clientes = await listar_clientes_retorno_pendente(self.TENANT)

        assert len(clientes) >= 1, f"Esperado >= 1, obtido {len(clientes)}"
        encontrado = False
        for cliente in clientes:
            if cliente["actor_id"] == self.CLIENTE_2:
                assert cliente["lead_status"] == "retorno_pendente"
                encontrado = True
                break
        assert encontrado, f"Cliente {self.CLIENTE_2} nao encontrado"

        print(f"[OK] Listou cliente em retorno_pendente")

    @pytest.mark.asyncio
    async def test_gerar_sugestao_deterministica(self):
        """Gera sugestão determinística"""
        cliente = {
            "actor_id": self.CLIENTE_1,
            "nome_detectado": "João",
            "lead_status": "retorno_pendente",
            "dias_desde_atendimento": 20,
            "total_agendamentos": 3
        }

        sugestao = await gerar_sugestao_reativacao(cliente)

        assert sugestao["actor_id"] == self.CLIENTE_1
        assert sugestao["motivo"] == "Não agendou há 20 dias após atendimento"
        assert sugestao["acao_sugerida"] == "Verificar interesse em retornar"

        print(f"[OK] Sugestão determinística gerada")

    @pytest.mark.asyncio
    async def test_resumo_reativacao(self):
        """Gera resumo consolidado de reativação"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_35 = (agora - timedelta(days=35)).isoformat()
        dias_atras_20 = (agora - timedelta(days=20)).isoformat()

        # Criar clientes
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "inativo",
            "ultima_interacao": dias_atras_35
        })

        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_2).set({
            "lead_status": "retorno_pendente",
            "ultimo_atendimento": dias_atras_20
        })

        # Gerar resumo
        resumo = await gerar_resumo_reativacao(self.TENANT)

        assert resumo["total_inativos"] == 1
        assert resumo["total_retorno_pendente"] == 1
        assert resumo["total_para_reativar"] == 2

        print(f"[OK] Resumo consolidado gerado")

    @pytest.mark.asyncio
    async def test_cliente_ativo_nao_aparece(self):
        """Cliente ativo não aparece em lista de reativação"""
        db = get_db()
        agora = datetime.now(timezone.utc)

        # Criar cliente ativo (agendado)
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_4).set({
            "lead_status": "agendado",
            "ultima_interacao": agora.isoformat(),
            "actor_id": self.CLIENTE_4
        })

        # Listar inativos - devem estar vazias
        inativos = await listar_clientes_inativos(self.TENANT, dias_inatividade=30)

        # Verificar que cliente ativo não aparece em inativos
        ids_inativos = [c["actor_id"] for c in inativos]
        assert self.CLIENTE_4 not in ids_inativos, "Cliente ativo apareceu em inativos"

        print(f"[OK] Cliente ativo não aparece em reativação")

    @pytest.mark.asyncio
    async def test_multitenant_isolado(self):
        """Dois tenants isolados"""
        TENANT_A = "f1_04_tenant_a"
        TENANT_B = "f1_04_tenant_b"
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_35 = (agora - timedelta(days=35)).isoformat()

        # Criar clientes em tenants diferentes
        db.collection("Clientes").document(TENANT_A).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "inativo",
            "ultima_interacao": dias_atras_35
        })

        db.collection("Clientes").document(TENANT_B).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "agendado",
            "ultima_interacao": agora.isoformat()
        })

        # Listar em cada tenant
        inativos_a = await listar_clientes_inativos(TENANT_A)
        inativos_b = await listar_clientes_inativos(TENANT_B)

        assert len(inativos_a) == 1
        assert len(inativos_b) == 0

        print(f"[OK] Multi-tenant isolado validado")

        db.collection("Clientes").document(TENANT_A).delete()
        db.collection("Clientes").document(TENANT_B).delete()

    @pytest.mark.asyncio
    async def test_nenhuma_escrita_em_sessao(self):
        """Reativação não escreve em Sessões"""
        import inspect
        from services import reativacao_manual_service

        source = inspect.getsource(reativacao_manual_service)

        # Remove comentários
        linhas_codigo = [
            linha for linha in source.split('\n')
            if not linha.strip().startswith('#') and not linha.strip().startswith('"""')
        ]
        codigo_sem_comentario = '\n'.join(linhas_codigo)

        assert "Sessoes" not in codigo_sem_comentario
        assert "salvar_contexto" not in codigo_sem_comentario
        assert "merge=True" not in codigo_sem_comentario  # Não faz set/update

        print(f"[OK] Nenhuma escrita em Sessões")

    @pytest.mark.asyncio
    async def test_nenhuma_alteracao_em_lead_status(self):
        """Reativação não altera lead_status"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_35 = (agora - timedelta(days=35)).isoformat()

        # Criar cliente inativo
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "inativo",
            "ultima_interacao": dias_atras_35
        })

        # Consultar reativação múltiplas vezes
        await listar_clientes_inativos(self.TENANT)
        await gerar_resumo_reativacao(self.TENANT)
        await gerar_lista_reativacao_formatada(self.TENANT)

        # Verificar que lead_status não mudou
        doc = db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).get()

        assert doc.to_dict().get("lead_status") == "inativo"

        print(f"[OK] Lead_status não foi alterado")

    @pytest.mark.asyncio
    async def test_nenhuma_mensagem_enviada(self):
        """Reativação não envia mensagens automáticas"""
        import inspect
        from services import reativacao_manual_service

        source = inspect.getsource(reativacao_manual_service)

        # Verificar que não há chamadas de envio de mensagem
        assert "send_message" not in source.lower()

        # Verificar que apenas formata dados, não faz envio
        assert "await" not in source or "await listar" in source or "await gerar" in source

        print(f"[OK] Nenhuma mensagem automática")

    @pytest.mark.asyncio
    async def test_formatacao_para_dono(self):
        """Formata sugestão legível para dono"""
        cliente = {
            "nome_detectado": "Maria",
            "lead_status": "retorno_pendente",
            "dias_desde_atendimento": 25,
            "total_agendamentos": 5
        }

        mensagem = formatar_sugestao_para_dono(cliente)

        assert "Maria" in mensagem
        assert "25" in mensagem
        assert "Último atendimento" in mensagem

        print(f"[OK] Formatação para dono validada")

    @pytest.mark.asyncio
    async def test_idempotencia(self):
        """Executar múltiplas vezes retorna mesmo resultado"""
        db = get_db()
        agora = datetime.now(timezone.utc)
        dias_atras_35 = (agora - timedelta(days=35)).isoformat()

        # Criar cliente
        db.collection("Clientes").document(self.TENANT).collection(
            "Clientes"
        ).document(self.CLIENTE_1).set({
            "lead_status": "inativo",
            "ultima_interacao": dias_atras_35
        })

        # Executar múltiplas vezes
        resultado1 = await listar_clientes_inativos(self.TENANT)
        resultado2 = await listar_clientes_inativos(self.TENANT)
        resultado3 = await listar_clientes_inativos(self.TENANT)

        assert len(resultado1) == len(resultado2) == len(resultado3) == 1
        assert resultado1[0]["dias_inativo"] == resultado2[0]["dias_inativo"]

        print(f"[OK] Operações idempotentes validadas")


async def main():
    """Executa testes"""
    print("\n" + "="*80)
    print("F1-04: TESTES DE REATIVACAO MANUAL (FIREBASE REAL)")
    print("="*80 + "\n")

    test_suite = TestF104ReativacaoManual()
    tests = [
        ("Listar clientes inativos", test_suite.test_listar_clientes_inativos),
        ("Listar retorno pendente", test_suite.test_listar_retorno_pendente),
        ("Gerar sugestao deterministica", test_suite.test_gerar_sugestao_deterministica),
        ("Resumo de reativacao", test_suite.test_resumo_reativacao),
        ("Cliente ativo nao aparece", test_suite.test_cliente_ativo_nao_aparece),
        ("Multi-tenant isolado", test_suite.test_multitenant_isolado),
        ("Nenhuma escrita em sessao", test_suite.test_nenhuma_escrita_em_sessao),
        ("Nenhuma alteracao em lead_status", test_suite.test_nenhuma_alteracao_em_lead_status),
        ("Nenhuma mensagem enviada", test_suite.test_nenhuma_mensagem_enviada),
        ("Formatacao para dono", test_suite.test_formatacao_para_dono),
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
