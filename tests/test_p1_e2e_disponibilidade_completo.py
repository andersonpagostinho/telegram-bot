"""
P1 E2E: Fluxo COMPLETO de Disponibilidade - VERSÃO SIMPLIFICADA
Valida: Classificação correta → Dados extraídos → Router ready

Reproduz: "a bruna esta disponivel amanha as 10?"
"""

import pytest
import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
if not os.getenv("FIREBASE_CREDENTIALS_B64"):
    from dotenv import load_dotenv
    load_dotenv()

TENANT = "7394370553"
WA_ID = "5511991382080"
ACTOR_ID = f"whatsapp:{WA_ID}"


class TestP1E2EDisponibilidadeCompleto:
    """E2E: Classificação corrigida para consulta de disponibilidade"""

    @pytest.mark.asyncio
    async def test_e2e_classificacao_disponibilidade_corrigida(self):
        """
        Valida que "a bruna esta disponivel amanha as 10?" é classificado como
        consulta_disponibilidade_aberta (não como indefinida)
        """
        print("\n" + "=" * 80)
        print("E2E: CLASSIFICAÇÃO DE DISPONIBILIDADE CORRIGIDA")
        print("=" * 80)

        from utils.contexto_temporario import (
            salvar_contexto_temporario_v2,
            carregar_contexto_temporario_v2,
            limpar_contexto_agendamento_v2
        )
        from services.classificador_conversa import classificar_intencao_conversacional

        # SETUP: Contexto limpo (como se fosse primeira mensagem)
        await limpar_contexto_agendamento_v2(TENANT, ACTOR_ID)
        await salvar_contexto_temporario_v2(TENANT, ACTOR_ID, {
            "tenant_id": TENANT,
            "actor_id": ACTOR_ID,
            "_tenant_id_guard": TENANT,
            "tipo_usuario": "cliente",
            "permissoes": ["ler", "agendamento"],
        })
        print("[SETUP] Contexto limpo (primeira mensagem)")
        print(f"  TENANT={TENANT}")
        print(f"  ACTOR_ID={ACTOR_ID}\n")

        # ============================================
        # TESTE 1: Pergunta sobre disponibilidade
        # ============================================
        msg1 = "a bruna esta disponivel amanha as 10?"
        print("[TESTE 1] PERGUNTA DE DISPONIBILIDADE")
        print(f"  Mensagem: '{msg1}'")

        ctx1 = await carregar_contexto_temporario_v2(TENANT, ACTOR_ID)
        resultado1 = classificar_intencao_conversacional(msg1, ctx1)
        intencao1 = resultado1.get("intencao_conversacional")
        features1 = resultado1.get("features", {})

        print(f"\n[RESULTADO CLASSIFICAÇÃO]")
        print(f"  intencao={intencao1}")
        print(f"  tem_pergunta={features1.get('tem_pergunta')}")
        print(f"  tem_tempo={features1.get('tem_tempo')}")
        print(f"  tem_ref_profissional={features1.get('tem_ref_profissional')}")
        print(f"  tem_indefinido={features1.get('tem_indefinido')}")

        # VALIDAÇÃO CRÍTICA
        assert intencao1 == "consulta_disponibilidade_aberta", \
            f"❌ ERRO: Esperado 'consulta_disponibilidade_aberta', recebido '{intencao1}'"
        assert features1.get("tem_ref_profissional") is True, \
            f"❌ ERRO: tem_ref_profissional deveria ser True"
        print(f"\n✅ CLASSIFICAÇÃO CORRETA\n")

        # ============================================
        # TESTE 2: Pergunta com profissional diferente
        # ============================================
        msg2 = "gloria esta livre amanha as 14?"
        print("[TESTE 2] PERGUNTA COM OUTRO PROFISSIONAL")
        print(f"  Mensagem: '{msg2}'")

        resultado2 = classificar_intencao_conversacional(msg2, ctx1)
        intencao2 = resultado2.get("intencao_conversacional")
        features2 = resultado2.get("features", {})

        print(f"\n[RESULTADO CLASSIFICAÇÃO]")
        print(f"  intencao={intencao2}")
        print(f"  tem_ref_profissional={features2.get('tem_ref_profissional')}")

        assert intencao2 == "consulta_disponibilidade_aberta", \
            f"❌ ERRO: Esperado 'consulta_disponibilidade_aberta', recebido '{intencao2}'"
        assert features2.get("tem_ref_profissional") is True
        print(f"\n✅ CLASSIFICAÇÃO CORRETA\n")

        # ============================================
        # TESTE 3: Com profissional no contexto
        # ============================================
        print("[TESTE 3] PERGUNTA COM PROFISSIONAL NO CONTEXTO")
        ctx3 = {
            **ctx1,
            "profissional_escolhido": "Joana",
        }
        msg3 = "joana tem disponibilidade amanha as 11?"
        print(f"  Mensagem: '{msg3}'")
        print(f"  Contexto: profissional_escolhido='Joana'")

        resultado3 = classificar_intencao_conversacional(msg3, ctx3)
        intencao3 = resultado3.get("intencao_conversacional")
        features3 = resultado3.get("features", {})

        print(f"\n[RESULTADO CLASSIFICAÇÃO]")
        print(f"  intencao={intencao3}")
        print(f"  tem_ref_profissional={features3.get('tem_ref_profissional')}")

        assert intencao3 == "consulta_disponibilidade_aberta"
        assert features3.get("tem_ref_profissional") is True
        print(f"\n✅ CLASSIFICAÇÃO CORRETA\n")

        # ============================================
        # TESTE 4: Pergunta SEM profissional (indefinida)
        # ============================================
        print("[TESTE 4] PERGUNTA SEM PROFISSIONAL (deve ser indefinida)")
        msg4 = "tem disponibilidade amanha as 10?"
        print(f"  Mensagem: '{msg4}'")

        resultado4 = classificar_intencao_conversacional(msg4, ctx1)
        intencao4 = resultado4.get("intencao_conversacional")
        features4 = resultado4.get("features", {})

        print(f"\n[RESULTADO CLASSIFICAÇÃO]")
        print(f"  intencao={intencao4}")
        print(f"  tem_ref_profissional={features4.get('tem_ref_profissional')}")

        # Sem profissional específico, deve ser indefinida (não consulta_disponibilidade_aberta)
        assert intencao4 == "indefinida", \
            f"❌ ERRO: Sem profissional, deveria ser 'indefinida', recebido '{intencao4}'"
        assert features4.get("tem_ref_profissional") is False
        print(f"\n✅ CLASSIFICAÇÃO CORRETA (indefinida sem profissional)\n")

        # ============================================
        # RESUMO FINAL
        # ============================================
        print("=" * 80)
        print("✅ TODOS OS TESTES PASSARAM")
        print("=" * 80)
        print(f"""
FIX APLICADO:
  📝 services/classificador_conversa.py linhas 151-172

MUDANÇA:
  ❌ ANTES: Procurava profissional APENAS no contexto
  ✅ DEPOIS: Procura profissional no contexto OU na própria mensagem

RESULTADO:
  ✅ "a bruna esta disponivel amanha as 10?" → consulta_disponibilidade_aberta
  ✅ "gloria esta livre amanha as 14?" → consulta_disponibilidade_aberta
  ✅ "tem disponibilidade amanha as 10?" → indefinida (correto)

PRÓXIMO PASSO:
  O router agora pode:
  1. Ler profissional do contexto (definido pelo handlers/bot.py)
  2. Acionar VALIDACAO_CONFLITO_PRE_GPT
  3. Mostrar tabela de conflito em vez de deixar GPT responder
""")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
