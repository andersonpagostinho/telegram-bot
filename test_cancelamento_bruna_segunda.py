#!/usr/bin/env python3
"""
Teste E2E — Cancelamento com Bruna na Segunda
"""

import asyncio
from services.event_service_async import cancelar_evento_por_texto

async def test():
    print('\n' + '='*80)
    print('TESTE E2E CANCELAMENTO COM BRUNA NA SEGUNDA')
    print('='*80 + '\n')

    # Parâmetros corretos
    user_id = '7371670478'  # Cliente
    tenant_id = '7394370553'  # Dono real
    termo = 'Cancelar com a Bruna na segunda'

    print(f'[INPUT] termo="{termo}"')
    print(f'[INPUT] user_id={user_id}')
    print(f'[INPUT] tenant_id={tenant_id}')
    print(f'\n[LOGS DIAGNOSTICO]')
    print('-' * 80)

    try:
        resultado, mensagem, candidatos = await cancelar_evento_por_texto(
            user_id=user_id,
            termo=termo,
            tenant_id=tenant_id
        )

        print('-' * 80)
        print(f'\n[RESULTADO] encontrados={len(candidatos)}')
        print(f'[RESULTADO] mensagem={mensagem}')

        if candidatos:
            print(f'\n[SUCESSO] Encontrou {len(candidatos)} evento(s):')
            for i, (eid, ev) in enumerate(candidatos, 1):
                print(f'  {i}. {eid}')
                print(f'     profissional={ev.get("profissional")}')
                print(f'     data={ev.get("data")}')
                print(f'     hora={ev.get("hora_inicio")}')
                print(f'     status={ev.get("status")}')
        else:
            print(f'\n[FALHA] Nenhum evento encontrado')
            print(f'Verifique os logs [P0-DIAG-*] acima para diagnosticar')
    except Exception as e:
        print(f'\n[ERRO] {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
