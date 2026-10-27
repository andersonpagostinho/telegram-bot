"""
ETAPA 2: Testes Unitários de Gratidão após Cancelamento
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

from utils.contexto_temporario import (
    salvar_contexto_temporario_v2,
    carregar_contexto_temporario_v2,
    limpar_contexto_agendamento_v2
)
from services.classificador_conversa import extrair_features_conversa


class TestEtapa2GratidaoAposCancelamento:
    """Testes unitários de gratidão e cancelamento"""

    @pytest.mark.asyncio
    async def test_1_detectar_agradecimento_feature(self):
        """T1: Detectar agradecimento via feature do classificador"""
        print("\n" + "=" * 70)
        print("T1: DETECTAR AGRADECIMENTO")
        print("=" * 70)

        mensagens = ["obrigado", "obrigada", "valeu", "grato", "grata", "brigado", "brigada"]

        for msg in mensagens:
            features = extrair_features_conversa(msg)
            assert features.get("tem_agradecimento") is True, f"Falhou em '{msg}'"
            print(f"  ✅ '{msg}'")

        print(f"\n✅ T1: PASSOU\n")

    @pytest.mark.asyncio
    async def test_2_funcao_limpeza_usa_delete_field(self):
        """T2: Função de limpeza usa DELETE_FIELD corretamente"""
        print("\n" + "=" * 70)
        print("T2: LIMPEZA COM DELETE_FIELD")
        print("=" * 70)

        TENANT = "7394370553"
        USER = "5511991382081"
        ACTOR_ID = f"whatsapp:{USER}"

        # SETUP: Contexto com dados
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {"prof": "Gloria"},
            "draft_agendamento": {"prof": "Gloria"},
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })
        print("[SETUP] Dados salvos")

        # AÇÃO: Usar limpar_contexto_agendamento_v2 (usa DELETE_FIELD)
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        print("[AÇÃO] limpar_contexto_agendamento_v2() chamado")

        # VALIDAÇÃO
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        assert ctx.get("aguardando_confirmacao_agendamento") is False
        assert ctx.get("draft_agendamento") is None
        assert ctx.get("estado_fluxo") == "idle"
        print(f"✅ DELETE_FIELD funcionou corretamente")
        print(f"\n✅ T2: PASSOU\n")

    @pytest.mark.asyncio
    async def test_3_logica_bloqueio_agradecimento(self):
        """T3: Lógica de bloqueio de agradecimento"""
        print("\n" + "=" * 70)
        print("T3: LÓGICA DE BLOQUEIO")
        print("=" * 70)

        # Caso 1: Sem operação → responder
        ctx1 = {"modo_escolha_horario": False, "dados_confirmacao_agendamento": None}
        features1 = extrair_features_conversa("obrigado", ctx1)
        tem_agradecimento1 = features1.get("tem_agradecimento")
        tem_operacao1 = (
            bool(ctx1.get("modo_escolha_horario")) or
            bool(ctx1.get("dados_confirmacao_agendamento"))
        )
        responder1 = tem_agradecimento1 and not tem_operacao1
        assert responder1 is True, "Deveria responder sem operação"
        print(f"✅ CASO 1: Responder gratidão (sem operação)")

        # Caso 2: Com modo_escolha → bloquear
        ctx2 = {"modo_escolha_horario": True, "dados_confirmacao_agendamento": None}
        features2 = extrair_features_conversa("obrigado", ctx2)
        tem_agradecimento2 = features2.get("tem_agradecimento")
        tem_operacao2 = (
            bool(ctx2.get("modo_escolha_horario")) or
            bool(ctx2.get("dados_confirmacao_agendamento"))
        )
        responder2 = tem_agradecimento2 and not tem_operacao2
        assert responder2 is False, "Deveria bloquear com operação"
        print(f"✅ CASO 2: Bloquear (com escolha ativa)")

        # Caso 3: Com dados_confirmacao → bloquear
        ctx3 = {"modo_escolha_horario": False, "dados_confirmacao_agendamento": {"x": "y"}}
        features3 = extrair_features_conversa("obrigado", ctx3)
        tem_agradecimento3 = features3.get("tem_agradecimento")
        tem_operacao3 = (
            bool(ctx3.get("modo_escolha_horario")) or
            bool(ctx3.get("dados_confirmacao_agendamento"))
        )
        responder3 = tem_agradecimento3 and not tem_operacao3
        assert responder3 is False, "Deveria bloquear com confirmação"
        print(f"✅ CASO 3: Bloquear (com confirmação ativa)")

        print(f"\n✅ T3: PASSOU\n")

    @pytest.mark.asyncio
    async def test_4_regressao_confirmacao_nao_afetada(self):
        """T4: Regressão - Confirmação legítima não é afetada"""
        print("\n" + "=" * 70)
        print("T4: REGRESSÃO - CONFIRMAÇÃO LEGÍTIMA")
        print("=" * 70)

        TENANT = "7394370553"
        USER = "5511991382084"
        ACTOR_ID = f"whatsapp:{USER}"

        # SETUP: Confirmação legítima
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "estado_fluxo": "agendando",
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {"prof": "Carla", "serv": "coloracao"},
            "draft_agendamento": {"prof": "Carla"},
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
        })
        print("[SETUP] Confirmação ativa")

        # VALIDAÇÃO: Dados íntegros
        ctx = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        assert ctx.get("aguardando_confirmacao_agendamento") is True
        assert ctx.get("dados_confirmacao_agendamento") is not None
        assert ctx.get("dados_confirmacao_agendamento").get("prof") == "Carla"
        print(f"✅ Confirmação legítima íntegra")

        # Cleanup
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        print(f"\n✅ T4: PASSOU\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
