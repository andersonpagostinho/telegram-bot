#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RASTREAMENTO COMPLETO: Persistencia do evento Manicure 14:30-15:00

Objetivo: Localizar exatamente onde/como o evento é persistido no Firestore
Rastrear cada etapa da escrita antes da consulta seguinte
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    atualizar_dado_em_path,
    obter_id_dono,
    deletar_dado_em_path,
    buscar_subcolecao,
    buscar_dado_em_path,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


async def main():
    """Rastrear persistencia do evento Manicure 14:30-15:00"""

    tenant_id = "rastreamento_evento_001"
    cliente_id = "rastreamento_cliente_001"
    data_teste = "2026-08-11"

    print("="*80)
    print("[RASTREAMENTO] Persistencia do evento Manicure")
    print("="*80)

    try:
        # SETUP
        print("\n[SETUP] Limpando dados antigos...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lock_id in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lock_id}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")

        print("[SETUP] Registrando cliente...")
        await atualizar_dado_em_path(f"Clientes/{cliente_id}", {
            "nome": "Cliente Rastreamento",
            "id_negocio": tenant_id,
            "tipo_usuario": "cliente"
        })

        # DADOS DO EVENTO A PERSISTIR
        print("\n" + "="*80)
        print("[EVENTO] Parametros a serem persistidos")
        print("="*80)

        evento_dados = {
            "descricao": "Manicure (rastreamento)",
            "profissional": "Carla",
            "servico": "Manicure",
            "data": data_teste,
            "hora_inicio": "14:30",
            "hora_fim": "15:00",
            "duracao": 30,
            "duracao_minutos": 30,
            "confirmado": True,
            "status": "confirmado",
            "cliente_id": "outro_cliente_123",
            "cliente_nome": "Maria"
        }

        event_id = f"evt_rastreamento_{data_teste}_1430"

        print(f"\nDados a serem persistidos:")
        print(f"  tenant_id (dono_id): {tenant_id}")
        print(f"  event_id: {event_id}")
        print(f"  cliente_id: {evento_dados['cliente_id']}")
        print(f"  cliente_nome: {evento_dados['cliente_nome']}")
        print(f"  profissional: {evento_dados['profissional']}")
        print(f"  servico: {evento_dados['servico']}")
        print(f"  data: {evento_dados['data']}")
        print(f"  hora_inicio: {evento_dados['hora_inicio']}")
        print(f"  hora_fim: {evento_dados['hora_fim']}")
        print(f"  duracao: {evento_dados['duracao']} min")
        print(f"  duracao_minutos: {evento_dados['duracao_minutos']} min")

        evento_path = f"Clientes/{tenant_id}/Eventos/{event_id}"
        print(f"\nFirestore path EVENTO: {evento_path}")

        # ETAPA 1: CRIAR EVENTO COM LOCK
        print("\n" + "="*80)
        print("[ETAPA 1] Chamar criar_com_lock_real()")
        print("="*80)

        print(f"\nParametros de entrada:")
        print(f"  dono_id: {tenant_id}")
        print(f"  evento: {evento_dados}")
        print(f"  event_id: {event_id}")

        timestamp_antes = time.time()
        resultado = await criar_com_lock_real(
            dono_id=tenant_id,
            evento=evento_dados,
            event_id=event_id
        )
        tempo_criacao = time.time() - timestamp_antes

        print(f"\nResultado da chamada:")
        print(f"  ok: {resultado.get('ok')}")
        print(f"  evento_id: {resultado.get('evento_id')}")
        print(f"  motivo: {resultado.get('motivo')}")
        print(f"  tipo_erro: {resultado.get('tipo_erro')}")
        print(f"  tempo decorrido: {tempo_criacao:.3f}s")

        if not resultado.get("ok"):
            print(f"\n[FALHA] Evento nao foi criado")
            return

        # ETAPA 2: VERIFICAR LOCKS CRIADOS
        print("\n" + "="*80)
        print("[ETAPA 2] Verificar locks criados")
        print("="*80)

        locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
        print(f"\nTotal de locks criados: {len(locks)}")

        for lock_id, lock_data in locks.items():
            print(f"\n  Lock ID: {lock_id}")
            print(f"    bucket: {lock_data.get('bucket')}")
            print(f"    profissional: {lock_data.get('profissional')}")
            print(f"    status: {lock_data.get('status')}")
            print(f"    evento_id: {lock_data.get('evento_id')}")
            print(f"    timestamp_lock: {lock_data.get('timestamp_lock')}")
            print(f"    timestamp_confirmacao: {lock_data.get('timestamp_confirmacao')}")

            lock_path = f"Clientes/{tenant_id}/AgendaLocks/{lock_id}"
            print(f"    Path: {lock_path}")

        # ETAPA 3: VERIFICAR EVENTO EM FIRESTORE
        print("\n" + "="*80)
        print("[ETAPA 3] Verificar evento em Firestore")
        print("="*80)

        timestamp_antes_busca = time.time()
        evento_persistido = await buscar_dado_em_path(evento_path)
        tempo_busca = time.time() - timestamp_antes_busca

        print(f"\nBuscando em: {evento_path}")
        print(f"Tempo de busca: {tempo_busca:.3f}s")

        if evento_persistido:
            print(f"\n[OK] Evento encontrado em Firestore!")
            print(f"\nDados persistidos:")
            for chave, valor in evento_persistido.items():
                print(f"  {chave}: {valor}")

            # Validar que todos os campos necessarios foram persistidos
            campos_obrigatorios = [
                "profissional", "servico", "data", "hora_inicio", "hora_fim",
                "duracao_minutos", "confirmado", "status", "cliente_id", "cliente_nome"
            ]

            print(f"\n[VALIDACAO] Campos obrigatorios:")
            todos_presente = True
            for campo in campos_obrigatorios:
                presente = campo in evento_persistido
                print(f"  {campo}: {'OK' if presente else 'FALTANDO'}")
                if not presente:
                    todos_presente = False

            if todos_presente:
                print(f"\n[SUCESSO] Todos os campos foram persistidos corretamente!")
            else:
                print(f"\n[AVISO] Alguns campos faltam!")

        else:
            print(f"\n[FALHA] Evento NAO foi encontrado em Firestore!")
            print(f"Path verificado: {evento_path}")

        # ETAPA 4: VERIFICAR LEITURA COM buscar_subcolecao
        print("\n" + "="*80)
        print("[ETAPA 4] Verificar leitura com buscar_subcolecao()")
        print("="*80)

        eventos_lista = await buscar_subcolecao(f"Clientes/{tenant_id}/Eventos")
        print(f"\nTotal de eventos encontrados: {len(eventos_lista)}")

        if event_id in eventos_lista:
            print(f"\n[OK] Evento encontrado em buscar_subcolecao()")
            print(f"Evento: {eventos_lista[event_id]}")
        else:
            print(f"\n[FALHA] Evento NAO encontrado em buscar_subcolecao()")
            print(f"IDs encontrados: {list(eventos_lista.keys())}")

        # RESUMO FINAL
        print("\n" + "="*80)
        print("[RESUMO] Rastreamento de persistencia")
        print("="*80)

        print(f"\n[CAMINHO DO EVENTO]")
        print(f"  Firestore Path: {evento_path}")
        print(f"  tenant_id: {tenant_id}")
        print(f"  event_id: {event_id}")

        print(f"\n[DADOS PERSISTIDOS]")
        print(f"  tenant_id: {tenant_id}")
        print(f"  evento_id: {event_id}")
        print(f"  cliente_id: {evento_dados['cliente_id']}")
        print(f"  profissional: {evento_dados['profissional']}")
        print(f"  servico: {evento_dados['servico']}")
        print(f"  data: {evento_dados['data']}")
        print(f"  hora_inicio: {evento_dados['hora_inicio']}")
        print(f"  hora_fim: {evento_dados['hora_fim']}")
        print(f"  duracao: {evento_dados['duracao_minutos']} minutos")

        print(f"\n[LOCKS]")
        print(f"  Total de locks criados: {len(locks)}")
        print(f"  Path base: Clientes/{tenant_id}/AgendaLocks/")

        print(f"\n[TEMPO DECORRIDO]")
        print(f"  Criacao (com locks): {tempo_criacao:.3f}s")
        print(f"  Busca do evento: {tempo_busca:.3f}s")

        print(f"\n[CONCLUSAO]")
        if evento_persistido and len(locks) > 0:
            print(f"[SUCESSO] Evento foi completamente persistido")
            print(f"[SUCESSO] Locks foram criados e confirmados")
            print(f"[SUCESSO] Dados estao prontos para proxima consulta")
        else:
            print(f"[FALHA] Problema na persistencia")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[CLEANUP] Limpando...")
        try:
            locks = await buscar_subcolecao(f"Clientes/{tenant_id}/AgendaLocks")
            for lock_id in locks.keys():
                await deletar_dado_em_path(f"Clientes/{tenant_id}/AgendaLocks/{lock_id}")
        except:
            pass
        await deletar_dado_em_path(f"Clientes/{tenant_id}")


if __name__ == "__main__":
    asyncio.run(main())
