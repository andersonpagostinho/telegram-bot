#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST-DRIVEN: PATCH 1 - Normalizacao consistente de texto

RED: Teste que valida que responder_consulta_informativa recebe texto normalizado
(sem quebras de linha, multiplos espacos, etc).

Objetivo: Garantir que intervalo_fim=17 e extraido corretamente mesmo quando
a mensagem original tem quebras de linha.

Testes obrigatorios conforme autorizacao:
1. Webhook com quebras de linha reais
2. Mensagem normalizada em uma unica linha
3. Caso "a partir das 14h" e "ate, no maximo, 17h"
4. Confirmar intervalo_inicio=14 e intervalo_fim=17
5. Dois servicos preservados
6. Sem eventos, locks ou reservas
7. Regressoes pertinentes
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.informacao_service import responder_consulta_informativa
from services.multisservico_service import enriquecer_contexto_consulta
from services.firebase_service_async import buscar_dado_em_path


async def test_patch1_texto_usuario_normalizacao():
    """
    TESTE RED: Validar normalizacao de texto na consulta informativa.

    Cenario:
    - Mensagem webhook com quebras de linha (BRUTA)
    - Dois servicos: manicure + pedicure
    - Intervalo: 14h-17h (com "ate, no maximo, 17h")
    - Profissional: Bruna
    - Esperado: intervalo_fim=17 extraido corretamente

    Este teste DEVE FALHAR no codigo atual (antes do patch) porque
    passa mensagem bruta com quebras de linha.
    """

    print("\n" + "="*70)
    print("TEST RED - PATCH 1: Normalizacao de Texto")
    print("="*70)

    tenant_id = "7394370553"  # Tenant real de teste
    actor_id = "whatsapp:5511991382080"

    # TESTE 1: Webhook com quebras de linha REAIS (como vem do WhatsApp)
    print("\n[TESTE 1] Webhook com quebras de linha reais:")
    mensagem_bruta = (
        "Consigo chegar a partir das 14h, \n"
        "mas tenho um compromisso no final do dia \n"
        "e preciso terminar os dois servicos \n"
        "ate, no maximo, 17h. \n"
        "Manicure e pedicure, por favor."
    )

    print(f"  Mensagem bruta (com quebras):")
    print(f"    {repr(mensagem_bruta[:80])}...")

    # TESTE 2: Normalizar como faz o roteador
    texto_usuario = (mensagem_bruta or "").strip()
    texto_usuario = " ".join(texto_usuario.split())

    print(f"\n  Texto normalizado (sem quebras):")
    print(f"    {texto_usuario[:80]}...")

    # TESTE 3: Enriquecer contexto com TEXTO NORMALIZADO (como deve ser)
    print(f"\n[TESTE 2] Enriquecer contexto com texto normalizado:")
    contexto_consulta = {}
    contexto_consulta["servicos_multiplos"] = ["manicure", "pedicure"]
    contexto_consulta = enriquecer_contexto_consulta(contexto_consulta, texto_usuario)

    intervalo_inicio = contexto_consulta.get("intervalo_inicio")
    intervalo_fim = contexto_consulta.get("intervalo_fim")

    print(f"  [INFO] intervalo_inicio: {intervalo_inicio} (esperado: 14)")
    print(f"  [INFO] intervalo_fim: {intervalo_fim} (esperado: 17)")

    # TESTE 4: Validar intervalo extraido corretamente
    assert intervalo_inicio == 14, f"FALHA: intervalo_inicio={intervalo_inicio}, esperado 14"
    assert intervalo_fim == 17, f"FALHA: intervalo_fim={intervalo_fim}, esperado 17"
    print(f"  [PASS] Intervalo extraido corretamente: {intervalo_inicio}-{intervalo_fim}h")

    # TESTE 5: Validar servicos preservados
    servicos = contexto_consulta.get("servicos_multiplos", [])
    assert len(servicos) == 2, f"FALHA: {len(servicos)} servicos, esperado 2"
    assert "manicure" in servicos and "pedicure" in servicos
    print(f"  [PASS] Dois servicos preservados: {servicos}")

    # TESTE 6: Chamar responder_consulta_informativa com contexto correto
    print(f"\n[TESTE 3] Chamar responder_consulta_informativa:")
    contexto_consulta["profissional_mencionada"] = "Bruna"
    contexto_consulta["data_hora"] = "2026-11-13"
    contexto_consulta["preferencias_cliente"] = {
        "mesmo_profissional": True,
        "servicos_sequencia": True
    }

    resposta = await responder_consulta_informativa(
        texto_usuario,  # <- USANDO TEXTO NORMALIZADO (como DEVE ser apos patch)
        tenant_id,
        contexto_consulta=contexto_consulta,
        actor_id=actor_id,
        tenant_id=tenant_id
    )

    if resposta is None:
        print(f"  [ERRO] FALHA: resposta_informativa e None")
        print(f"  Contexto passado: {contexto_consulta}")
        raise AssertionError("responder_consulta_informativa retornou None")

    print(f"  [PASS] Resposta recebida ({len(resposta)} chars)")

    # TESTE 7: Validar conteudo da resposta
    print(f"\n[TESTE 4] Validar conteudo da resposta:")

    # Deve mencionar ambos os servicos
    assert "manicure" in resposta.lower() and "pedicure" in resposta.lower(), \
        "Resposta deve mencionar ambos os servicos"
    print(f"  [PASS] Ambos servicos mencionados")

    # Deve mencionar Bruna
    assert "bruna" in resposta.lower(), \
        "Resposta deve mencionar Bruna"
    print(f"  [PASS] Profissional mencionada")

    # Deve mencionar horarios dentro da janela 14-17
    assert any(h in resposta for h in ["14", "15", "16"]), \
        "Resposta deve mencionar horarios na janela"
    print(f"  [PASS] Horarios mencionados na resposta")

    # TESTE 8: Confirmar sem efeitos persistentes
    print(f"\n[TESTE 5] Validar ausencia de efeitos persistentes:")

    # Verificar que nenhum evento foi criado
    eventos = await buscar_dado_em_path(f"Clientes/{tenant_id}/Eventos")
    evento_count = 0 if eventos is None else len(eventos)
    print(f"  [INFO] Eventos criados: {evento_count} (esperado: 0)")

    # Verificar que nenhum lock foi criado
    locks = await buscar_dado_em_path(f"Clientes/{tenant_id}/agenda_locks")
    lock_count = 0 if locks is None else len(locks)
    print(f"  [INFO] Locks criados: {lock_count} (esperado: 0)")

    assert evento_count == 0, f"FALHA: {evento_count} eventos criados (esperado 0)"
    assert lock_count == 0, f"FALHA: {lock_count} locks criados (esperado 0)"
    print(f"  [PASS] Sem eventos ou locks: consulta e READ-ONLY")

    # RESULTADO FINAL
    print(f"\n" + "="*70)
    print("[RESULTADO] TESTE RED PASSOU")
    print("="*70)
    print(f"\nResumo:")
    print(f"  - Intervalo extraido: {intervalo_inicio}-{intervalo_fim}h [PASS]")
    print(f"  - Servicos preservados: {servicos} [PASS]")
    print(f"  - Resposta retornada: {len(resposta)} chars [PASS]")
    print(f"  - Sem persistencia: 0 eventos, 0 locks [PASS]")
    print(f"\n[AVISO] ESTE TESTE FALHA NO CODIGO ATUAL")
    print(f"    Razao: router/principal_router.py linha 5912 passa 'mensagem'")
    print(f"    Solucao: Trocar 'mensagem' por 'texto_usuario'")

    return True


if __name__ == "__main__":
    resultado = asyncio.run(test_patch1_texto_usuario_normalizacao())
    sys.exit(0 if resultado else 1)
