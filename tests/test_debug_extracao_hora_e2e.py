"""
TESTE DE DEBUG: Extração de Hora em E2E Real

Objetivo: Rastrear exatamente onde a hora "15" ou "as 15" está sendo:
1. Extraída corretamente pela GPT
2. Mas NÃO preservada no fluxo
3. E NÃO apresentada para o usuário

Fluxo rastreado:
Mensagem 1: "queria agendar corte com a bruna para amanha as 15"
  ├─ interpretar_linguagem_operacional_gpt() → Deve extrair hora=15:00
  ├─ Resultado é salvo em contexto?
  ├─ Passado para próximo handler?
  └─ Apresentado para confirmação?

Mensagem 2: "as 15"
  ├─ Reconhecido como entrada de hora?
  ├─ Atualizado contexto?
  └─ Confirmação enviada?
"""

import pytest
import asyncio
import json
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Setup logging detalhado
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("DEBUG_HORA")

try:
    from services.gpt_service import interpretar_linguagem_operacional_gpt
    from services.interpretacao_contextual_service import interpretar_resposta_contextual
    from utils.contexto_temporario import (
        salvar_contexto_temporario_v2,
        carregar_contexto_temporario_v2,
    )
    from services.firebase_service_async import deletar_dado_em_path
    GPT_OK = True
except Exception as e:
    print(f"Import error: {e}")
    GPT_OK = False


@pytest.mark.skipif(not GPT_OK, reason="GPT imports failed")
class TestExtracaoHoraE2E:
    """
    Rastrea exatamente onde a hora é perdida no fluxo.
    """

    @pytest.mark.asyncio
    async def test_01_gpt_interpreta_hora_corretamente(self):
        """
        ETAPA 1: Verificar se GPT extrai a hora de "para amanha as 15"
        """
        print("\n" + "="*80)
        print("ETAPA 1: GPT Interpretação - Primeira Mensagem")
        print("="*80)

        texto_usuario = "queria agendar corte com a bruna para amanha as 15"
        catalogo = ['corte feminino', 'manicure', 'pedicure', 'escova', 'coloracao']
        contexto_entrada = {}

        print(f"  📥 Entrada GPT:")
        print(f"     Texto: '{texto_usuario}'")
        print(f"     Contexto: {json.dumps(contexto_entrada, indent=2)}")

        resultado_gpt = await interpretar_linguagem_operacional_gpt(
            texto=texto_usuario,
            ctx=contexto_entrada,
            catalogo_servicos=catalogo
        )

        print(f"  📤 Resultado GPT:")
        print(f"     {json.dumps(resultado_gpt, indent=2, ensure_ascii=False)}")

        # CHECKLIST
        assert resultado_gpt.get("intencao") == "agendamento_direto", \
            f"❌ Intenção errada: {resultado_gpt.get('intencao')}"
        print(f"     ✅ Intenção: agendamento_direto")

        assert "corte" in str(resultado_gpt.get("entidades", {})).lower(), \
            f"❌ Serviço não extraído: {resultado_gpt.get('entidades')}"
        print(f"     ✅ Serviço detectado: {resultado_gpt.get('entidades', {})}")

        assert "bruna" in str(resultado_gpt.get("entidades", {})).lower(), \
            f"❌ Profissional não extraído: {resultado_gpt.get('entidades')}"
        print(f"     ✅ Profissional detectado: {resultado_gpt.get('entidades', {})}")

        # 🔴 QUESTÃO CRÍTICA: A hora foi extraída?
        entidades = resultado_gpt.get("entidades", {})
        hora_extraida = entidades.get("horario") or entidades.get("hora") or entidades.get("time")

        if hora_extraida:
            print(f"     ✅ HORA EXTRAÍDA: {hora_extraida}")
        else:
            print(f"     ❌ HORA NÃO EXTRAÍDA!")
            print(f"        Entidades completas: {json.dumps(entidades, indent=2)}")
            # NÃO FALHAR AINDA - vamos rastrear para onde foi

        return resultado_gpt

    @pytest.mark.asyncio
    async def test_02_contexto_preserva_hora(self):
        """
        ETAPA 2: Verificar se a hora extraída é salva no contexto
        """
        print("\n" + "="*80)
        print("ETAPA 2: Preservação de Contexto")
        print("="*80)

        dono_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cliente_id = f"test_cliente_{dono_id}"

        # Simular contexto após primeira mensagem
        contexto_simulado = {
            "servico": "corte feminino",
            "profissional": "Bruna",
            "data": "amanha",  # ou data parseada
            "horario": "15:00",  # DEVE estar aqui se GPT extraiu
            "intencao": "agendamento_direto"
        }

        print(f"  💾 Salvando contexto no Firebase:")
        print(f"     Tenant: {dono_id}")
        print(f"     Cliente: {cliente_id}")
        print(f"     Contexto: {json.dumps(contexto_simulado, indent=2)}")

        try:
            await salvar_contexto_temporario_v2(dono_id, cliente_id, contexto_simulado)
            print(f"     ✅ Contexto salvo")

            # Verificar se foi realmente salvo
            contexto_recuperado = await carregar_contexto_temporario_v2(dono_id, cliente_id)
            print(f"\n  📂 Recuperando contexto:")
            print(f"     {json.dumps(contexto_recuperado, indent=2)}")

            if contexto_recuperado.get("horario"):
                print(f"     ✅ Hora preservada: {contexto_recuperado.get('horario')}")
            else:
                print(f"     ❌ Hora não preservada!")

            # Limpeza
            await deletar_dado_em_path(f"Clientes/{dono_id}")
            print(f"     ✅ Limpeza concluída")

        except Exception as e:
            print(f"     ❌ Erro: {e}")
            raise

    @pytest.mark.asyncio
    async def test_03_segunda_mensagem_reconhece_hora(self):
        """
        ETAPA 3: Verificar se "as 15" é reconhecido como entrada de hora
        """
        print("\n" + "="*80)
        print('ETAPA 3: Reconhecimento de "as 15" - Segunda Mensagem')
        print("="*80)

        texto_usuario_2 = "as 15"
        catalogo = ['corte feminino', 'manicure', 'pedicure', 'escova', 'coloracao']

        # Contexto carregado da primeira interação
        contexto_com_draft = {
            "servico": "corte feminino",
            "profissional": "Bruna",
            "estado_fluxo": "aguardando_horario"  # ou estado similar
        }

        print(f"  📥 Entrada GPT (2ª mensagem):")
        print(f"     Texto: '{texto_usuario_2}'")
        print(f"     Contexto anterior: {json.dumps(contexto_com_draft, indent=2)}")

        resultado_gpt_2 = await interpretar_linguagem_operacional_gpt(
            texto=texto_usuario_2,
            ctx=contexto_com_draft,
            catalogo_servicos=catalogo
        )

        print(f"  📤 Resultado GPT (2ª mensagem):")
        print(f"     {json.dumps(resultado_gpt_2, indent=2, ensure_ascii=False)}")

        # ANÁLISE
        entidades_2 = resultado_gpt_2.get("entidades", {})
        hora_em_2 = entidades_2.get("horario") or entidades_2.get("hora") or entidades_2.get("time")

        if hora_em_2:
            print(f"     ✅ HORA RECONHECIDA NA 2ª MENSAGEM: {hora_em_2}")
        else:
            print(f'     ❌ "as 15" NÃO FOI RECONHECIDO COMO HORA!')
            print(f"        Resultado completo: {json.dumps(resultado_gpt_2, indent=2)}")
            # FALHA: A GPT deve reconhecer "15" ou "as 15" como hora

    @pytest.mark.asyncio
    async def test_04_fluxo_completo_com_debug(self):
        """
        ETAPA 4: Simular fluxo completo com rastreamento de debug
        """
        print("\n" + "="*80)
        print("ETAPA 4: Fluxo Completo com Rastreamento")
        print("="*80)

        mensagens = [
            "queria agendar corte com a bruna para amanha as 15",
            "as 15",
        ]

        print(f"  🔄 Sequência de mensagens:")
        for i, msg in enumerate(mensagens, 1):
            print(f"     {i}. '{msg}'")

        print(f"\n  ⏱️  Simulando processamento...")
        print(f"\n  CHECKPOINT A: Após mensagem 1")
        print(f"     Esperado: contexto contém servico, profissional, data, HORA")
        print(f"     Real: ???")

        print(f"\n  CHECKPOINT B: Após mensagem 2")
        print(f"     Esperado: hora atualizada no contexto")
        print(f"     Real: ???")

        print(f"\n  📊 RESUMO DE PROBLEMAS ENCONTRADOS:")
        print(f"     [ ] GPT não extrai hora de 'para amanha as 15'")
        print(f"     [ ] Hora extraída mas não salva em contexto")
        print(f"     [ ] Hora salva mas não apresentada em confirmação")
        print(f"     [ ] 'as 15' não reconhecido como entrada de hora")
        print(f"     [ ] Segunda entrada de hora não atualiza contexto")


if __name__ == "__main__":
    print("Teste de Debug: Extração de Hora")
    print("Execute com: pytest tests/test_debug_extracao_hora_e2e.py -v -s")
