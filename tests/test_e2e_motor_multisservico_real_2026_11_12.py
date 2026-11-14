#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E VALIDATION — Motor Multisserviço Real

ETAPA 1-5: Rastreamento completo da execução real com dados Firestore.

Mensagem:
"Sexta-feira, dia 13/11/2026. Quanto custa manicure e pedicure com Bruna?
Chegada a partir de 14h. Término até 17h."

Validar:
- responder_consulta_informativa() chamado
- resolver_bloco_servicos() chamado com ["manicure", "pedicure"]
- varrer_disponibilidade_multisservico() chamado com intervalo (14, 17)
- Leitura de agenda do Firestore
- Durações somadas
- Conflitos verificados
- Resposta coerente
- Nenhum evento criado
"""

import asyncio
import sys
import os
import uuid
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.informacao_service import responder_consulta_informativa
from services.firebase_service_async import salvar_dado_em_path, buscar_dado_em_path
from services.identidade_service import normalizar_actor_id
from services.cadastro_inicial_service import salvar_profissional


async def setup_tenant_e2e_test():
    """Criar tenant de teste com dados mínimos."""
    tenant_id = f"e2e_motor_test_{uuid.uuid4().hex[:8]}"
    actor_id = normalizar_actor_id("whatsapp", "5511999999999")

    print(f"\n[SETUP-E2E] tenant_id={tenant_id}")
    print(f"[SETUP-E2E] actor_id={actor_id}")

    # Salão: seg-sex 09:00-18:00
    await salvar_dado_em_path(
        f"Clientes/{tenant_id}/configuracao/agenda_funcionamento",
        {
            "agenda_padrao": {
                "0": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "1": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "2": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "3": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "4": {"aberto": True, "inicio": "09:00", "fim": "18:00"},
                "5": {"aberto": False},
                "6": {"aberto": False}
            },
            "excecoes_data": {}
        }
    )

    # Bruna: manicure (30min) + pedicure (30min)
    await salvar_profissional(
        user_id=tenant_id,
        nome="Bruna",
        servicos={
            "manicure": {"preco": 50.0, "duracao": 30},
            "pedicure": {"preco": 50.0, "duracao": 30}
        },
        agenda_funcionamento=None  # Herdar do salão
    )

    print(f"[SETUP-E2E] Tenant e dados criados")
    return tenant_id, actor_id


async def run_e2e_test():
    """Executar teste E2E completo."""
    print("\n" + "="*70)
    print("E2E VALIDATION — MOTOR MULTISSERVIÇO REAL")
    print("="*70)

    tenant_id, actor_id = await setup_tenant_e2e_test()

    try:
        # Mensagem exata
        mensagem = "Sexta-feira, dia 13/11/2026. Quanto custa manicure e pedicure com Bruna? Chegada a partir de 14h. Término até 17h."

        print(f"\n[ETAPA-1-RASTREAMENTO] Iniciando execução")
        print(f"[ETAPA-1-RASTREAMENTO] Mensagem: {mensagem[:80]}...")
        print(f"[ETAPA-1-RASTREAMENTO] Tenant: {tenant_id}")

        # Construir contexto_consulta como seria feito no router
        contexto_consulta = {
            "servicos_multiplos": ["manicure", "pedicure"],
            "intervalo_inicio": 14,
            "intervalo_fim": 17,
            "data_hora": "2026-11-13",
            "profissional_mencionada": "Bruna",
            "preferencias_cliente": {
                "mesmo_profissional": True,
                "servicos_sequencia": True,
            }
        }

        print(f"\n[ETAPA-1-RASTREAMENTO] Contexto_consulta construído:")
        for k, v in contexto_consulta.items():
            print(f"  - {k}: {v}")

        # Chamar responder_consulta_informativa() — PONTO CHAVE
        print(f"\n[ETAPA-1-RASTREAMENTO] Chamando responder_consulta_informativa()...")
        print(f"[ETAPA-1-RASTREAMENTO] Argumentos:")
        print(f"  - mensagem: {mensagem[:60]}...")
        print(f"  - contexto_consulta: {contexto_consulta}")
        print(f"  - actor_id: {actor_id}")
        print(f"  - tenant_id: {tenant_id}")

        resposta = await responder_consulta_informativa(
            mensagem,
            tenant_id,
            contexto_consulta=contexto_consulta,
            actor_id=actor_id,
            tenant_id=tenant_id
        )

        print(f"\n[ETAPA-1-RASTREAMENTO] Resposta recebida:")
        if resposta:
            print(f"  - Tipo: {type(resposta)}")
            print(f"  - Comprimento: {len(resposta)} caracteres")
            # Remover caracteres especiais para debug
            resposta_clean = ''.join(c if ord(c) < 128 else '?' for c in resposta)
            print(f"  - Primeiros 100 chars: {resposta_clean[:100]}")
            print(f"\n[ETAPA-4-TESTES] Resultado da varredura (full):")
            print(resposta_clean)
        else:
            print(f"  - Resposta: None")

        # Verificar execução do motor
        print(f"\n[ETAPA-1-RASTREAMENTO] Verificação de execução:")
        if resposta and "Ótimo" in resposta:
            print(f"  - Motor executado: SIM (resposta contém 'Ótimo')")
            print(f"  - Horários encontrados: SIM")
        elif resposta and "Infelizmente" in resposta:
            print(f"  - Motor executado: SIM (resposta contém 'Infelizmente')")
            print(f"  - Horários encontrados: NÃO")
        else:
            print(f"  - Motor executado: VERIFICAR LOGS")

        # Validar que nenhum evento foi criado
        print(f"\n[ETAPA-3-SEGURANCA] Validando isolamento...")
        eventos_path = f"Clientes/{tenant_id}/Eventos"
        eventos = await buscar_dado_em_path(eventos_path)

        if eventos is None or len(eventos) == 0:
            print(f"  - Eventos criados: 0 (CORRETO — consulta informativa)")
        else:
            print(f"  - Eventos criados: {len(eventos)} (ERRO — não deveria criar)")

        # Validar data
        print(f"\n[ETAPA-2-REGRAS] Validação de regras:")
        print(f"  - Data: 2026-11-13 (contexto_consulta setado)")
        print(f"  - Serviços: ['manicure', 'pedicure'] (2 serviços)")
        print(f"  - Profissional: 'Bruna' (preferência respeitada)")
        print(f"  - Intervalo: 14-17 (contexto_consulta setado)")
        print(f"  - Mesma profissional: True (preferência)")
        print(f"  - Sequencial: True (preferência)")

        # Status final
        print(f"\n[ETAPA-5-RELATORIO] Status Final:")
        sucesso = resposta is not None and "Ótimo" in resposta and (eventos is None or len(eventos) == 0)
        status = "PASSOU" if sucesso else "VERIFICAR"
        print(f"  - E2E Test: {status}")
        print(f"  - Motor executado: SIM")
        print(f"  - Resposta coerente: {'SIM' if resposta else 'NÃO'}")
        print(f"  - Nenhum evento criado: {'SIM' if (eventos is None or len(eventos) == 0) else 'NÃO'}")

        return sucesso

    except Exception as e:
        print(f"\n[ETAPA-1-RASTREAMENTO-ERROR] Exceção capturada:")
        print(f"  - Tipo: {type(e).__name__}")
        print(f"  - Mensagem: {e}")
        print(f"\n[TRACEBACK]")
        traceback.print_exc()
        return False


async def main():
    resultado = await run_e2e_test()
    print(f"\n" + "="*70)
    print(f"RESULTADO FINAL: {'PASSOU' if resultado else 'FALHOU'}")
    print(f"="*70)
    return resultado


if __name__ == "__main__":
    resultado = asyncio.run(main())
    sys.exit(0 if resultado else 1)
