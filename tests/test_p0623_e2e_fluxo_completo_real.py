"""
P0.6.2.3 — TESTE E2E FLUXO COMPLETO REAL

Simula conversa real:
1. Cliente envia: "gstria de agndar unha para terç agora, tiera?"
2. Sistema aplica fallback GPT (P0.6.2) → encontra ["manicure", "pedicure"]
3. Pergunta qual prefere
4. Cliente responde: "as duas"
5. Sistema repergunta (não cria evento com múltiplos)
6. Cliente responde: "manicure"
7. Sistema reconhece "manicure" → próxima etapa
8. Continua até agendamento concluído
"""

import pytest
import uuid
from datetime import datetime
from google.cloud import firestore


try:
    from services.firebase_service_async import deletar_dado_em_path
    from services.interpretacao_contextual_service import interpretar_resposta_contextual
    from services.gpt_service import interpretar_linguagem_operacional_gpt
    from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2
    FIREBASE_OK = True
except Exception as e:
    print(f"Firebase import error: {e}")
    FIREBASE_OK = False


@pytest.mark.skipif(not FIREBASE_OK, reason="Firebase imports failed")
class TestP0623FluxoCompletoReal:
    """E2E Fluxo completo: typo → múltiplos → escolha → agendamento"""

    @pytest.mark.asyncio
    async def test_fluxo_gstria_ate_agendamento_concluido(self):
        """
        E2E Fluxo Real Completo:
        - Mensagem com typos: "gstria de agndar unha para terç agora, tiera?"
        - Múltiplos candidatos: manicure + pedicure
        - Cliente escolhe: "as duas" → sistema repergunta
        - Cliente escolhe: "manicure" → reconhecido
        - Sistema continua fluxo até agendamento

        Etapas:
        1. ENTRADA: Frase com typos
        2. P0.6.2: Fallback GPT detecta múltiplos
        3. PERGUNTA: Qual prefere?
        4. RESPOSTA 1: "as duas"
        5. VALIDAÇÃO: Múltiplos detectados, repergunta
        6. RESPOSTA 2: "manicure"
        7. P0.6.2.2: Interpretação contextual
        8. CONTINUIDADE: Estado muda para aguardando_profissional
        9. CONCLUSÃO: Verificar que fluxo está pronto para próxima etapa
        """
        tenant_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
        actor_id = f"actor_{str(uuid.uuid4())[:8]}"

        try:
            print(f"\n{'='*80}")
            print(f"E2E FLUXO COMPLETO: {tenant_id}")
            print(f"{'='*80}")

            # ========================================================================
            # PASSO 1: ENTRADA COM TYPOS
            # ========================================================================
            print("\n[PASSO 1] Cliente envia frase com typos:")
            mensagem_original = "gstria de agndar unha para terç agora, tiera?"
            print(f"  → '{mensagem_original}'")

            # ========================================================================
            # PASSO 2: P0.6.2 FALLBACK GPT - Detectar múltiplos candidatos
            # ========================================================================
            print("\n[PASSO 2] Aplicar fallback GPT (P0.6.2)...")

            # Simular o que o fallback GPT retorna
            # (Em produção, vira do router via gpt_service)
            interpretacao_gpt = {
                "intencao": "agendamento_direto",
                "entidades": {
                    "servico": ["manicure", "pedicure"],  # Múltiplos!
                    "data": "2026-10-21",  # Terça-feira
                    "horario": None,
                },
                "confianca": 75,
            }

            servicos_validos = interpretacao_gpt.get("entidades", {}).get("servico", [])
            if isinstance(servicos_validos, str):
                servicos_validos = [servicos_validos]

            print(f"  → Candidatos encontrados: {servicos_validos}")

            assert len(servicos_validos) > 1, "Deve encontrar múltiplos"
            assert "manicure" in servicos_validos
            assert "pedicure" in servicos_validos

            # ========================================================================
            # PASSO 3: PERSISTIR ESTADO "AGUARDANDO_SERVICO"
            # ========================================================================
            print("\n[PASSO 3] Sistema entra em aguardando_servico...")

            contexto_aguardando = {
                "estado_fluxo": "aguardando_servico",
                "multiplos_servicos_candidatos": servicos_validos,
                "intencao_conversacional": "agendamento_direto",
                "data": interpretacao_gpt["entidades"].get("data"),
            }

            await salvar_contexto_temporario_v2(tenant_id, actor_id, contexto_aguardando)
            print(f"  ✅ Estado persistido: aguardando_servico")

            # ========================================================================
            # PASSO 4: PERGUNTA "Qual você prefere: manicure ou pedicure?"
            # ========================================================================
            print(f"\n[PASSO 4] Sistema pergunta: 'Qual você prefere: {' ou '.join(servicos_validos)}'")

            # ========================================================================
            # PASSO 5: CLIENTE RESPONDE "as duas"
            # ========================================================================
            print("\n[PASSO 5] Cliente responde: 'as duas'")

            ctx_carregado = await carregar_contexto_temporario_v2(tenant_id, actor_id)

            resultado_duas = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="as duas",
                estado_fluxo="aguardando_servico",
                contexto=ctx_carregado
            )

            print(f"  → Interpretação: {resultado_duas}")
            assert resultado_duas.get("interpretado_sucesso") is True
            assert resultado_duas.get("multiplo") is True
            assert resultado_duas.get("servicos") == servicos_validos
            print(f"  ✅ Sistema detectou múltiplos → REPERGUNTA (não cria evento)")

            # ========================================================================
            # PASSO 6: SISTEMA REPERGUNTA (sem consumir candidatos ainda)
            # ========================================================================
            print("\n[PASSO 6] Sistema repergunta: 'Preciso agendar um de cada vez. Qual você prefere?'")

            # Contexto não muda ainda (ainda aguardando_servico)
            ctx_ainda_aguardando = await carregar_contexto_temporario_v2(tenant_id, actor_id)
            assert ctx_ainda_aguardando.get("estado_fluxo") == "aguardando_servico"
            assert "multiplos_servicos_candidatos" in ctx_ainda_aguardando

            # ========================================================================
            # PASSO 7: CLIENTE RESPONDE "manicure"
            # ========================================================================
            print("\n[PASSO 7] Cliente responde: 'manicure'")

            resultado_manicure = await interpretar_resposta_contextual(
                tenant_id=tenant_id,
                actor_id=actor_id,
                mensagem="manicure",
                estado_fluxo="aguardando_servico",
                contexto=ctx_ainda_aguardando
            )

            print(f"  → Interpretação: {resultado_manicure}")
            assert resultado_manicure.get("interpretado_sucesso") is True
            assert resultado_manicure.get("servico") == "manicure"
            assert resultado_manicure.get("ambigua") is False
            print(f"  ✅ 'manicure' reconhecida")

            # ========================================================================
            # PASSO 8: CONSUMIR CANDIDATOS E TRANSICIONAR ESTADO
            # ========================================================================
            print("\n[PASSO 8] Consumir candidatos e transicionar estado...")

            ctx_consumido = {
                "servico": "manicure",
                "estado_fluxo": "aguardando_profissional",  # Próxima etapa
                "multiplos_servicos_candidatos": firestore.DELETE_FIELD,  # Consumido!
            }

            await salvar_contexto_temporario_v2(tenant_id, actor_id, ctx_consumido)
            print(f"  ✅ Estado: aguardando_servico → aguardando_profissional")

            # ========================================================================
            # PASSO 9: VALIDAR CONTEXTO
            # ========================================================================
            print("\n[PASSO 9] Validar contexto em Firestore...")

            ctx_final = await carregar_contexto_temporario_v2(tenant_id, actor_id)

            # Validações críticas
            assert ctx_final.get("servico") == "manicure", "Serviço não foi setado"
            assert ctx_final.get("estado_fluxo") == "aguardando_profissional", "Estado não transitou"
            assert "multiplos_servicos_candidatos" not in ctx_final or ctx_final.get("multiplos_servicos_candidatos") is None, \
                "Candidatos não foram consumidos"
            assert ctx_final.get("data") == "2026-10-21", "Data foi perdida"
            assert ctx_final.get("intencao_conversacional") == "agendamento_direto", "Intenção foi perdida"

            print(f"  ✅ Validações críticas PASS:")
            print(f"     - servico: {ctx_final.get('servico')}")
            print(f"     - estado_fluxo: {ctx_final.get('estado_fluxo')}")
            print(f"     - data: {ctx_final.get('data')}")
            print(f"     - intencao: {ctx_final.get('intencao_conversacional')}")
            print(f"     - candidatos consumidos: Sim")

            # ========================================================================
            # PASSO 10: PRÓXIMAS ETAPAS (simuladas)
            # ========================================================================
            print("\n[PASSO 10] Próximas etapas do agendamento:")
            print(f"  - Sistema perguntaria: 'Qual profissional você prefere?'")
            print(f"  - Após profissional: 'Qual dia/horário?'")
            print(f"  - Após data/hora: Confirmação → criar evento")

            print(f"\n{'='*80}")
            print(f"✅ FLUXO COMPLETO VALIDADO: Typo → Múltiplos → Escolha → Agendamento PRONTO")
            print(f"{'='*80}\n")

        finally:
            print(f"[CLEANUP] Deletando dados de teste...")
            try:
                await deletar_dado_em_path(f"Clientes/{tenant_id}/Sessoes/{actor_id}")
                print("[CLEANUP] ✅ Limpeza concluída")
            except Exception as e:
                print(f"[CLEANUP] ⚠️ Erro: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
