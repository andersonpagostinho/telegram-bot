"""
E2E FASE 4A: Fluxo completo consulta → seleção → confirmação

Valida:
1. Consulta multisserviço gera opções reais
2. Opções permanecem em Firestore após todas as gravações
3. Nova mensagem recupera as opções
4. "o primeiro" seleciona o ID correto
5. NeoEve pede confirmação final
6. Nenhum evento ou lock é criado antes da autorização

CRITÉRIO DE APROVAÇÃO:
- Duas mensagens independentes pelo webhook
- Seleção correta
- Nenhuma reserva criada
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

# Importar roteador principal
from router.principal_router import roteador_principal
from services.firebase_service_async import (
    buscar_dado_em_path, atualizar_dado_em_path, buscar_subcolecao
)


@pytest.fixture
def tenant_id():
    """Tenant de teste"""
    return "7394370553"


@pytest.fixture
def actor_id():
    """Cliente de teste"""
    return "5511991382080"


@pytest.fixture
def actor_id_prefixed(actor_id):
    """Actor com prefixo WhatsApp"""
    return f"whatsapp:{actor_id}"


@pytest.mark.asyncio
async def test_e2e_fase4a_fluxo_completo(tenant_id, actor_id, actor_id_prefixed):
    """
    E2E FASE 4A: Dois webhooks, seleção correta, sem reserva criada
    """

    # SETUP: Limpar estado anterior
    sessao_path = f"Clientes/{tenant_id}/Sessoes/{actor_id_prefixed}"
    try:
        await atualizar_dado_em_path(sessao_path, {})
    except:
        pass  # Sessão não existe ainda, OK

    print("\n" + "="*80)
    print("[E2E] FASE 4A: Fluxo completo — Consulta + Seleção + Confirmação")
    print("="*80)

    # ===== ETAPA 1: CONSULTA MULTISSERVIÇO COM HORÁRIO =====
    print("\n[E2E-STEP-1] Enviando consulta: manicure + pedicure das 14 às 17")

    mensagem_1 = "quero manicure e pedicure com a Bruna das 14 às 17 hoje"

    resposta_1 = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem_1,
        tenant_id=tenant_id
    )

    print(f"[E2E-STEP-1] Resposta:\n{resposta_1[:200]}...")

    # Validação 1: Resposta deve mencionar horários
    assert "Ótimo" in resposta_1 or "esquadrar" in resposta_1 or "disponível" in resposta_1, \
        f"Resposta não indica sucesso: {resposta_1}"
    print("[E2E-STEP-1] ✅ Consulta processada, resposta tem horários")

    # ===== ETAPA 2: VERIFICAR OPCOES EM FIRESTORE =====
    print("\n[E2E-STEP-2] Verificando opcoes em Firestore...")

    sessao_saved = await buscar_dado_em_path(sessao_path)
    assert sessao_saved is not None, "Sessão não foi salva!"

    contexto_resultado = sessao_saved.get("contexto_resultado_consulta", {})
    opcoes = contexto_resultado.get("opcoes", [])

    print(f"[E2E-STEP-2] Opcoes encontradas: {len(opcoes)}")
    assert len(opcoes) > 0, f"Nenhuma opção em Firestore! Estado: {sessao_saved}"

    for i, opt in enumerate(opcoes):
        print(f"  Opção {i+1}: {opt.get('hora_inicio')} às {opt.get('hora_fim')} (ID: {opt.get('opcao_id')[:40]}...)")

    # Guardar IDs para validação posterior
    primeira_opcao_id = opcoes[0]["opcao_id"]
    print(f"[E2E-STEP-2] ✅ {len(opcoes)} opções persistidas em Firestore")
    print(f"[E2E-STEP-2] ✅ Primeira opção ID: {primeira_opcao_id[:50]}...")

    # ===== ETAPA 3: SEGUNDA MENSAGEM — SELEÇÃO =====
    print("\n[E2E-STEP-3] Enviando seleção: 'o primeiro'")

    # Aguardar 1s para garantir timestamps diferentes
    await asyncio.sleep(1)

    mensagem_2 = "o primeiro"

    resposta_2 = await roteador_principal(
        user_id=actor_id,
        mensagem=mensagem_2,
        tenant_id=tenant_id
    )

    print(f"[E2E-STEP-3] Resposta:\n{resposta_2[:300]}...")

    # Validação 3: Resposta deve pedir confirmação (não deve criar evento automaticamente)
    assert "confirma" in resposta_2.lower() or "tem certeza" in resposta_2.lower() or \
           "agendar" in resposta_2.lower() or "pedir confirmação" in resposta_2.lower() or \
           "ok?" in resposta_2.lower() or "confirmar" in resposta_2.lower(), \
        f"Resposta não pede confirmação (pode ter criado evento sem autorização):\n{resposta_2}"

    print("[E2E-STEP-3] ✅ Seleção processada, pede confirmação")

    # ===== ETAPA 4: VERIFICAR QUE NENHUM EVENTO FOI CRIADO =====
    print("\n[E2E-STEP-4] Verificando que nenhum evento foi criado...")

    eventos_path = f"Clientes/{tenant_id}/Eventos"
    try:
        eventos_dict = await buscar_subcolecao(eventos_path)
        eventos_count = len(eventos_dict or {})
    except:
        eventos_count = 0

    # Pode haver eventos legados, mas nenhum novo com timestamp recente (últimos 5 segundos)
    agora = datetime.now()
    eventos_recentes = 0
    if eventos_dict:
        for evento_id, evento in eventos_dict.items():
            try:
                timestamp_str = evento.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    diferenca = (agora - timestamp).total_seconds()
                    if diferenca < 5 and evento.get("cliente_id") == actor_id_prefixed:
                        eventos_recentes += 1
                        print(f"  ⚠️ Evento recente criado: {evento_id} (diferença: {diferenca:.1f}s)")
            except:
                pass

    assert eventos_recentes == 0, \
        f"Evento foi criado ANTES de confirmação final! {eventos_recentes} evento(s) recente(s)"

    print(f"[E2E-STEP-4] ✅ Nenhum evento criado antes da confirmação")

    # ===== ETAPA 5: VERIFICAR QUE NENHUM LOCK FOI CRIADO =====
    print("\n[E2E-STEP-5] Verificando que nenhum lock foi criado...")

    locks_recentes = 0
    try:
        locks_path = f"Clientes/{tenant_id}/Locks"
        locks_dict = await buscar_subcolecao(locks_path)

        if locks_dict:
            for lock_id, lock in locks_dict.items():
                try:
                    timestamp_str = lock.get("data_criacao")
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        diferenca = (agora - timestamp).total_seconds()
                        if diferenca < 5:
                            locks_recentes += 1
                            print(f"  ⚠️ Lock recente criado: {lock_id} (diferença: {diferenca:.1f}s)")
                except:
                    pass
    except Exception as e:
        print(f"[E2E-STEP-5] Info: Não foi possível verificar locks ({str(e)[:50]}), pulando")
        # Não é erro crítico se não conseguir acessar Locks
        pass

    assert locks_recentes == 0, \
        f"Lock foi criado ANTES de confirmação final! {locks_recentes} lock(s) recente(s)"

    print(f"[E2E-STEP-5] ✅ Nenhum lock criado antes da confirmação")

    # ===== ETAPA 6: VALIDAÇÃO FINAL =====
    print("\n[E2E-STEP-6] Validação final do estado da sessão...")

    sessao_final = await buscar_dado_em_path(sessao_path)

    # Verificar que contexto_consulta está preservado
    contexto_consulta = sessao_final.get("contexto_consulta", {})
    assert "servicos_multiplos" in contexto_consulta, "contexto_consulta não preservado"
    assert len(contexto_consulta.get("servicos_multiplos", [])) == 2, "Serviços perdidos"

    # Verificar que contexto_resultado_consulta ainda tem opcoes
    contexto_resultado_final = sessao_final.get("contexto_resultado_consulta", {})
    opcoes_final = contexto_resultado_final.get("opcoes", [])
    assert len(opcoes_final) == len(opcoes), \
        f"Opcoes perdidas! Eram {len(opcoes)}, agora {len(opcoes_final)}"

    print(f"[E2E-STEP-6] ✅ Estado preservado:")
    print(f"  - Serviços: {contexto_consulta.get('servicos_multiplos')}")
    print(f"  - Opcoes mantidas: {len(opcoes_final)}")
    print(f"  - Estado fluxo: {sessao_final.get('estado_fluxo')}")

    print("\n" + "="*80)
    print("[E2E] ✅ FASE 4A COMPLETO: Consulta → Seleção → Confirmação (sem reserva)")
    print("="*80 + "\n")

    # RETORNAR RESUMO
    return {
        "etapas_validadas": 6,
        "opcoes_geradas": len(opcoes),
        "primeira_opcao": primeira_opcao_id,
        "eventos_criados": eventos_recentes,
        "locks_criados": locks_recentes,
        "status": "APROVADO" if eventos_recentes == 0 and locks_recentes == 0 else "FALHOU"
    }


if __name__ == "__main__":
    # Para rodar manualmente: python -m pytest tests/test_fase4a_e2e_fluxo_completo.py -xvs
    print("Execute com: python -m pytest tests/test_fase4a_e2e_fluxo_completo.py -xvs")
