#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Teste rápido dos cenários 06 e 07"""

import asyncio
import sys
import json

sys.path.insert(0, '.')

from tests.p1_robustez_fluxo_conversacional_real import (
    cenario_06_confirmacao_embutida,
    cenario_07_negacao_embutida,
    BateriaFluxo
)

async def main():
    bateria = BateriaFluxo()

    print('\n' + '='*80)
    print('TESTANDO CENÁRIO 06 (Confirmação)')
    print('='*80 + '\n')
    await cenario_06_confirmacao_embutida(bateria)

    print('\n' + '='*80)
    print('TESTANDO CENÁRIO 07 (Negação)')
    print('='*80 + '\n')
    await cenario_07_negacao_embutida(bateria)

    # Resultado
    print('\n' + '='*80)
    print('RESUMO')
    print('='*80)
    for resultado in bateria.cenarios:
        status = '[PASS]' if resultado.passou else '[FAIL]'
        print(f'{status} Cenário {resultado.numero}: {resultado.titulo}')
        if not resultado.passou:
            print(f'       Motivo: {resultado.motivo_falha}')

if __name__ == '__main__':
    asyncio.run(main())
