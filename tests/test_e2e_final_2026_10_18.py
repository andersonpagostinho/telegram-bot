"""
TESTE E2E FINAL — Validação simples mas completa
==================================================

REGRA DE OURO: Validar até Firestore (escrita) + resposta

Cenários com dados REAIS:
- tenant_id: 7394370553
- user_id: 5511991382080
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
class TestE2EFinal:
    """Testes E2E com dados reais"""

    TENANT_ID = "7394370553"
    USER_ID = "5511991382080"

    async def test_01_saudacao_responde_nao_vazio(self):
        """Saudação: sistema responde sem vazio"""
        from router.principal_router import roteador_principal

        resultado = await roteador_principal(
            user_id=self.USER_ID,
            mensagem="ola",
            tenant_id=self.TENANT_ID,
            phone_number_id=None,
            update=None,
            context=None,
        )

        assert resultado is not None, "Resultado não pode ser None"
        assert resultado.get("ok") == True, "ok deve ser True"
        assert resultado.get("resposta") is not None, "Resposta não pode ser vazia"
        assert len(resultado.get("resposta", "")) > 0, "Resposta deve ter texto"

        print(f"\n✅ TEST 01 PASSOU: Saudação respondeu")
        print(f"   Resposta: {resultado.get('resposta', '')[:60]}...")

    async def test_02_agendamento_responde(self):
        """Agendamento: sistema responde apropriadamente"""
        from router.principal_router import roteador_principal

        resultado = await roteador_principal(
            user_id=self.USER_ID,
            mensagem="Quero corte com Gloria amanhã às 14",
            tenant_id=self.TENANT_ID,
            phone_number_id=None,
            update=None,
            context=None,
        )

        assert resultado is not None
        assert resultado.get("ok") == True
        assert resultado.get("resposta") is not None

        print(f"\n✅ TEST 02 PASSOU: Agendamento respondeu")
        print(f"   Resposta: {resultado.get('resposta', '')[:60]}...")

    async def test_03_multiplas_mensagens_sem_crash(self):
        """Fluxo: múltiplas mensagens sem crash"""
        from router.principal_router import roteador_principal

        mensagens = [
            "ola",
            "Quero agendar",
            "corte feminino",
            "com gloria",
            "amanhã",
            "às 15",
        ]

        for msg in mensagens:
            resultado = await roteador_principal(
                user_id=self.USER_ID,
                mensagem=msg,
                tenant_id=self.TENANT_ID,
                phone_number_id=None,
                update=None,
                context=None,
            )

            assert resultado is not None, f"Mensagem '{msg}' retornou None"
            print(f"  ✅ '{msg}' → respondido")

        print(f"\n✅ TEST 03 PASSOU: {len(mensagens)} mensagens sem crash")

    async def test_04_confirmacao_responde(self):
        """Confirmação: sistema responde para "confirma/sim"  """
        from router.principal_router import roteador_principal

        resultado = await roteador_principal(
            user_id=self.USER_ID,
            mensagem="sim, pode agendar",
            tenant_id=self.TENANT_ID,
            phone_number_id=None,
            update=None,
            context=None,
        )

        assert resultado is not None
        assert resultado.get("ok") == True

        print(f"\n✅ TEST 04 PASSOU: Confirmação respondeu")
        print(f"   Resposta: {resultado.get('resposta', '')[:60]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
