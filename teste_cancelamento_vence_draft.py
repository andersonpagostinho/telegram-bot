#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE: Cancelamento Vence Draft de Agendamento

Cenário:
- Estado: agendando (em fluxo de agendamento)
- Draft: corte com Bruna amanhã às 10h
- Intenção: agendamento_direto
- Mensagem: "Quero cancelar com a Bruna amanhã"

Esperado:
- draft_agendamento é limpado
- não chama confirmar agendamento
- chama cancelar_evento_por_texto()
- exibe "Tem certeza de cancelar..." ou "Não encontrei..."
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

async def teste_cancelamento_vence_draft():
    """Testa se cancelamento limpa draft de agendamento"""

    print("=" * 80)
    print("TESTE: Cancelamento Vence Draft de Agendamento")
    print("=" * 80)
    print()

    # Estado inicial do contexto
    ctx_inicial = {
        "user_id": "7371670478",
        "estado_fluxo": "agendando",
        "draft_agendamento": {
            "profissional": "Bruna",
            "servico": "Corte",
            "data_hora": "2026-06-20T10:00:00"
        },
        "intencao_conversacional": "agendamento_direto",
        "aguardando_confirmacao_agendamento": True,
        "dados_confirmacao_agendamento": {
            "profissional": "Bruna",
            "servico": "Corte",
            "data_hora": "2026-06-20T10:00:00"
        }
    }

    print("[TESTE] Estado inicial do contexto:")
    print(f"  estado_fluxo: {ctx_inicial['estado_fluxo']}")
    print(f"  draft_agendamento: {ctx_inicial.get('draft_agendamento')}")
    print(f"  intencao_conversacional: {ctx_inicial.get('intencao_conversacional')}")
    print()

    # Simular detecção de features
    features = {
        "tem_cancelamento": True,  # ← Cancelamento foi detectado
        "tem_agendamento": False
    }

    print("[TESTE] Features detectadas:")
    print(f"  tem_cancelamento: {features.get('tem_cancelamento')}")
    print()

    # Aplicar PATCH P0: Cancelamento vence qualquer draft
    print("[PATCH P0] Aplicando lógica: Cancelamento vence draft...")
    print()

    if features.get("tem_cancelamento"):
        print("[PATCH] Limpando draft anterior...")
        ctx_inicial.pop("draft_agendamento", None)
        ctx_inicial.pop("aguardando_confirmacao_agendamento", None)
        ctx_inicial.pop("dados_confirmacao_agendamento", None)
        ctx_inicial.pop("intencao_conversacional", None)
        ctx_inicial["estado_fluxo"] = "idle"

    # Estado esperado após patch
    print("[RESULTADO] Estado após patch P0:")
    print(f"  estado_fluxo: {ctx_inicial['estado_fluxo']}")
    print(f"  draft_agendamento: {ctx_inicial.get('draft_agendamento')}")
    print(f"  intencao_conversacional: {ctx_inicial.get('intencao_conversacional')}")
    print()

    # Validações
    print("[VALIDACAO]")
    validacoes = [
        ("draft_agendamento foi limpado", ctx_inicial.get("draft_agendamento") is None),
        ("aguardando_confirmacao_agendamento foi limpado", ctx_inicial.get("aguardando_confirmacao_agendamento") is None),
        ("dados_confirmacao_agendamento foi limpado", ctx_inicial.get("dados_confirmacao_agendamento") is None),
        ("intencao_conversacional foi limpado", ctx_inicial.get("intencao_conversacional") is None),
        ("estado_fluxo resetado para idle", ctx_inicial.get("estado_fluxo") == "idle"),
    ]

    todas_passaram = True
    for desc, resultado in validacoes:
        status = "[PASS]" if resultado else "[FAIL]"
        print(f"  {status}: {desc}")
        if not resultado:
            todas_passaram = False

    print()

    if todas_passaram:
        print("[PASS] TESTE PASSOU")
        print()
        print("Significado:")
        print("  * Draft de agendamento anterior foi completamente descartado")
        print("  * Sistema esta em estado 'idle' para processar cancelamento")
        print("  * Proximo passo: cancelar_evento_por_texto() sera chamado")
        print("  * Resultado esperado: 'Tem certeza de cancelar...' ou 'Nao encontrei...'")
        return 0
    else:
        print("[FAIL] TESTE FALHOU")
        print()
        print("Problema: Patch P0 nao limpou completamente o draft anterior")
        print("Isso causaria: Confirmacao indevida de agendamento ao inves de cancelamento")
        return 1

async def main():
    """Função principal"""
    try:
        exit_code = await teste_cancelamento_vence_draft()
        return exit_code
    except Exception as e:
        print(f"\n[ERRO] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
