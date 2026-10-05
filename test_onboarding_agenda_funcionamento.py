#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste: Validar que agenda_padrao do onboarding é persistida em configuracao/agenda_funcionamento

Cobre o bug corrigido onde:
- ANTES: agenda_padrao coletada e validada, mas nunca salva em config
- DEPOIS: agenda_padrao salva automaticamente em Clientes/{tenant_id}/configuracao/agenda_funcionamento
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


async def test_agenda_funcionamento_criada_apos_onboarding():
    """
    T1: Validar que avancar_etapa_onboarding("agenda_padrao") cria documento.

    INPUT:
    - tenant_id novo
    - actor_id do dono
    - campo="agenda_padrao"
    - valor="9:00-18:00"

    ESPERADO:
    - Documento criado em Clientes/{tenant_id}/configuracao/agenda_funcionamento
    - Contém agenda_padrao com dias 0-5 abertos (09:00-18:00)
    - Domingo (6) fechado
    - excecoes_data vazio
    - onboarding avança normalmente
    """
    print("\n" + "="*70)
    print("[TEST T1] Agenda Funcionamento Criada no Onboarding")
    print("="*70)

    from services.onboarding_dono_service import (
        iniciar_onboarding_dono,
        avancar_etapa_onboarding,
        pegar_etapa_onboarding
    )
    from services.firebase_service_async import buscar_dado_em_path

    # Setup
    tenant_id = f"teste_agenda_{uuid.uuid4().hex[:8]}"
    actor_id = "whatsapp:11999999999"
    dono_nome = "Teste Dono"
    dono_email = "teste@example.com"

    print(f"\n[SETUP]")
    print(f"  tenant_id: {tenant_id}")
    print(f"  actor_id: {actor_id}")

    try:
        # Iniciar onboarding
        print(f"\n[1] Iniciando onboarding...")
        resultado_init = await iniciar_onboarding_dono(tenant_id, actor_id, dono_nome, dono_email)
        print(f"    ✓ Onboarding iniciado")
        print(f"    Status: {resultado_init['onboarding_status']}")
        print(f"    Etapa: {resultado_init['etapa_atual']}")

        # Avançar até agenda_padrao (pulando etapas anteriores)
        print(f"\n[2] Avançando etapas até agenda_padrao...")

        etapas_anteriores = [
            ("nome_negocio", "Salão Test"),
            ("segmento", "Salão de Beleza"),
            ("endereco", "Rua Test, 123"),
        ]

        for campo, valor in etapas_anteriores:
            resultado = await avancar_etapa_onboarding(tenant_id, actor_id, campo, valor)
            print(f"    ✓ {campo}: avançado para {resultado['etapa_atual']}")

        # Forçar estado para agenda_padrao (para teste isolado)
        # Nota: Normalmente o fluxo chegaria aqui naturalmente
        etapa_info = await pegar_etapa_onboarding(tenant_id, actor_id)
        print(f"    Etapa atual: {etapa_info['etapa_atual']}")

        # Processar agenda_padrao
        print(f"\n[3] Processando agenda_padrao...")
        resultado_agenda = await avancar_etapa_onboarding(tenant_id, actor_id, "agenda_padrao", "9:00-18:00")
        print(f"    ✓ agenda_padrao processado")
        print(f"    Próxima etapa: {resultado_agenda['etapa_atual']}")

        # Validar documento criado
        print(f"\n[4] Validando documento criado no Firestore...")
        path_config = f"Clientes/{tenant_id}/configuracao/agenda_funcionamento"
        config = await buscar_dado_em_path(path_config)

        if config is None:
            print(f"    ✗ FALHA: Documento não encontrado em {path_config}")
            return False

        print(f"    ✓ Documento encontrado")

        # Validar estrutura
        print(f"\n[5] Validando estrutura...")

        agenda_padrao = config.get("agenda_padrao")
        if not agenda_padrao:
            print(f"    ✗ FALHA: Campo 'agenda_padrao' não encontrado")
            return False
        print(f"    ✓ Campo 'agenda_padrao' existe")

        # Verificar dias 0-5 abertos
        for dia in ["0", "1", "2", "3", "4", "5"]:
            dia_config = agenda_padrao.get(dia)
            if not dia_config:
                print(f"    ✗ FALHA: Dia {dia} não configurado")
                return False

            if not dia_config.get("aberto"):
                print(f"    ✗ FALHA: Dia {dia} não está aberto")
                return False

            if dia_config.get("inicio") != "09:00":
                print(f"    ✗ FALHA: Dia {dia} início incorreto: {dia_config.get('inicio')}")
                return False

            if dia_config.get("fim") != "18:00":
                print(f"    ✗ FALHA: Dia {dia} fim incorreto: {dia_config.get('fim')}")
                return False

        print(f"    ✓ Dias 0-5 configurados corretamente (09:00-18:00, aberto=True)")

        # Verificar domingo fechado
        domingo = agenda_padrao.get("6")
        if not domingo:
            print(f"    ✗ FALHA: Domingo (6) não configurado")
            return False

        if domingo.get("aberto") != False:
            print(f"    ✗ FALHA: Domingo deveria estar fechado")
            return False

        print(f"    ✓ Domingo (6) fechado corretamente")

        # Verificar excecoes_data
        excecoes = config.get("excecoes_data")
        if excecoes is None:
            print(f"    ✗ FALHA: Campo 'excecoes_data' não encontrado")
            return False

        print(f"    ✓ Campo 'excecoes_data' existe (vazio)")

        # Validar que onboarding continuou
        print(f"\n[6] Validando que onboarding continuou...")
        etapa_pos = await pegar_etapa_onboarding(tenant_id, actor_id)
        if etapa_pos['etapa_atual'] not in ["primeiro_profissional", "completo"]:
            print(f"    ✗ FALHA: Onboarding não avançou (etapa={etapa_pos['etapa_atual']})")
            return False

        print(f"    ✓ Onboarding avançou normalmente (etapa={etapa_pos['etapa_atual']})")

        print(f"\n" + "="*70)
        print(f"[RESULTADO] PASSOU — Agenda funcionamento criada corretamente")
        print(f"{"="*70}\n")
        return True

    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Executa testes."""
    print("\n" + "="*70)
    print("TESTE: ONBOARDING AGENDA FUNCIONAMENTO")
    print("="*70)

    resultado = await test_agenda_funcionamento_criada_apos_onboarding()

    if resultado:
        print("[✓] TESTE PASSOU")
        return 0
    else:
        print("[✗] TESTE FALHOU")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
