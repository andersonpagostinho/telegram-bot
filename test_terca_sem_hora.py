#!/usr/bin/env python
"""Teste: terça-feira sem hora deve ser reconhecida como data sem hora (genérica)"""

import asyncio
from router.principal_router import extrair_slots_e_mesclar

async def main():
    # Teste 1: Terça sem hora
    print("[TESTE 1] Terça-feira sem hora")
    ctx = {
        'tipo_usuario': 'cliente',
        'estado_fluxo': 'aguardando_data',
        'draft_agendamento': {
            'servico': 'corte feminino',
            'profissional': None
        }
    }

    resultado = await extrair_slots_e_mesclar(
        ctx=ctx,
        texto_usuario='marque para terça feira entao por favor',
        dono_id='7394370553',
        cliente_id='whatsapp:5511991382080'
    )

    print(f"  estado_fluxo: {resultado.get('estado_fluxo')}")
    print(f"  data_sem_hora: {resultado.get('data_sem_hora')}")
    print(f"  hora_confirmada: {resultado.get('hora_confirmada')}")
    print(f"  data_hora: {resultado.get('data_hora')}")

    assert resultado.get('data_sem_hora') == True, 'FAIL: data_sem_hora deveria ser True'
    assert resultado.get('hora_confirmada') == False, 'FAIL: hora_confirmada deveria ser False'
    assert "2026-10-" in str(resultado.get('data_hora')), 'FAIL: data_hora deveria ter valor'
    print("✅ TESTE 1 PASSOU\n")

    # Teste 2: Terça COM hora (explícita)
    print("[TESTE 2] Terça-feira às 14h (hora explícita)")
    ctx2 = {
        'tipo_usuario': 'cliente',
        'estado_fluxo': 'aguardando_data',
        'draft_agendamento': {
            'servico': 'corte feminino',
            'profissional': None
        }
    }

    resultado2 = await extrair_slots_e_mesclar(
        ctx=ctx2,
        texto_usuario='marque para terça feira às 14h',
        dono_id='7394370553',
        cliente_id='whatsapp:5511991382080'
    )

    print(f"  estado_fluxo: {resultado2.get('estado_fluxo')}")
    print(f"  data_sem_hora: {resultado2.get('data_sem_hora')}")
    print(f"  hora_confirmada: {resultado2.get('hora_confirmada')}")
    print(f"  data_hora: {resultado2.get('data_hora')}")

    assert resultado2.get('hora_confirmada') == True, 'FAIL: hora_confirmada deveria ser True quando hora explícita'
    assert "14:00" in str(resultado2.get('data_hora')), 'FAIL: data_hora deveria ter 14:00'
    print("✅ TESTE 2 PASSOU\n")

    # Teste 3: Próxima quinta sem hora
    print("[TESTE 3] Próxima quinta sem hora")
    ctx3 = {
        'tipo_usuario': 'cliente',
        'estado_fluxo': 'aguardando_data',
        'draft_agendamento': {
            'servico': 'corte feminino',
            'profissional': None
        }
    }

    resultado3 = await extrair_slots_e_mesclar(
        ctx=ctx3,
        texto_usuario='agendar para proxima quinta por favor',
        dono_id='7394370553',
        cliente_id='whatsapp:5511991382080'
    )

    print(f"  estado_fluxo: {resultado3.get('estado_fluxo')}")
    print(f"  data_sem_hora: {resultado3.get('data_sem_hora')}")
    print(f"  hora_confirmada: {resultado3.get('hora_confirmada')}")
    print(f"  data_hora: {resultado3.get('data_hora')}")

    assert resultado3.get('data_sem_hora') == True, 'FAIL: data_sem_hora deveria ser True'
    assert resultado3.get('hora_confirmada') == False, 'FAIL: hora_confirmada deveria ser False'
    print("✅ TESTE 3 PASSOU\n")

    print("✅✅✅ TODOS OS TESTES PASSARAM")

if __name__ == "__main__":
    asyncio.run(main())
