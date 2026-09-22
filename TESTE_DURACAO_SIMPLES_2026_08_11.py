#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE SIMPLES: Validacao de duracao com motor corrigido
Sem emojis - ASCII puro
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    atualizar_dado_em_path,
    obter_id_dono,
    deletar_dado_em_path,
    buscar_subcolecao,
)
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def main():
    """Teste simples de duracao"""

    tenant_id = "teste_duracao_fix"
    cliente_id = "teste_cliente_fix"
    data_teste = datetime.now().strftime("%Y-%m-%d")

    print("="*80)
    print("[TESTE] Validacao de duracao - Motor corrigido")
    print("="*80)

    try:
        # SETUP
        print("\n[SETUP] Limpando dados...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lid in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lid}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")

        print("[SETUP] Registrando cliente...")
        await atualizar_dado_em_path(f"Clientes/{cliente_id}", {
            "nome": "Cliente",
            "id_negocio": tenant_id,
            "tipo_usuario": "cliente"
        })

        # ETAPA 1: Criar evento bloqueante
        print("\n[ETAPA 1] Criar Manicure 14:30-15:00")
        resultado = await criar_com_lock_real(
            dono_id=tenant_id,
            evento={
                "profissional": "Carla",
                "servico": "Manicure",
                "data": data_teste,
                "hora_inicio": "14:30",
                "hora_fim": "15:00",
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "outro_cliente",
                "cliente_nome": "Maria"
            },
            event_id=f"evt_test_{data_teste}_1430"
        )
        print(f"[ETAPA 1] Resultado: ok={resultado.get('ok')}")

        if not resultado.get("ok"):
            print("[FALHA] Evento nao foi criado")
            return

        # ETAPA 2: Validar Corte 45 min
        print("\n[ETAPA 2] Validar Corte 14:00-14:45 (45 min)")
        await asyncio.sleep(1)

        val2 = await verificar_conflito_e_sugestoes_profissional(
            user_id=tenant_id,
            data=data_teste,
            hora_inicio="14:00",
            duracao_min=45,
            profissional="Carla",
            servico="Corte"
        )

        print(f"[ETAPA 2] Conflito={val2.get('conflito')}")
        if val2.get('conflito'):
            print("[AVISO] Detectou conflito em Corte 45min (pode ser esperado)")
        else:
            print("[OK] Sem conflito em Corte 45min (esperado)")

        # ETAPA 3: CRÍTICA - Validar Corte+Hidratação 90 min
        print("\n[ETAPA 3] CRITICA - Validar Corte+Hidratacao 14:00-15:30 (90 min)")
        print("[ETAPA 3] Motor DEVE detectar conflito com Manicure 14:30-15:00")

        val3 = await verificar_conflito_e_sugestoes_profissional(
            user_id=tenant_id,
            data=data_teste,
            hora_inicio="14:00",
            duracao_min=90,
            profissional="Carla",
            servico="Corte + Hidratacao"
        )

        conflito_detectado = val3.get('conflito')
        sugestoes = len(val3.get('sugestoes', []))

        print(f"[ETAPA 3] Conflito={conflito_detectado}")
        print(f"[ETAPA 3] Sugestoes={sugestoes}")

        # RESULTADO
        print("\n" + "="*80)
        print("[RESULTADO]")
        print("="*80)

        if conflito_detectado:
            print("[SUCESSO] Motor detectou conflito corretamente!")
            print("[SUCESSO] Sistema esta PRONTO para reagendamento")
            print(f"[SUCESSO] Alternativas oferecidas: {sugestoes}")
            exit_code = 0
        else:
            print("[FALHA] Motor NAO detectou conflito!")
            print("[FALHA] Bloqueador ainda existe")
            exit_code = 1

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()
        exit_code = 2

    finally:
        print("\n[CLEANUP] Limpando...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lid in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lid}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")

    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
