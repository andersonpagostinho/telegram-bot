#!/usr/bin/env python3
"""
RUNNER E2E DIAGNÓSTICO — Cancelamento com Bruna na segunda

Objetivo: Reproduzir o bug P0 e coletar logs de diagnóstico

Cenário:
- Usuário: "Cancelar com a Bruna na segunda"
- Eventos esperados em Firestore: 2 eventos em 2026-06-22 com Bruna
- Resultado esperado: Sistema encontra e lista os 2 eventos
- Resultado atual: Sistema retorna "Não encontrei nenhum evento"

Execução:
python tests/runner_diagnostico_cancelamento_bruna.py
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar caminho do projeto
projeto_dir = Path(__file__).parent.parent
sys.path.insert(0, str(projeto_dir))

async def main():
    print("\n" + "="*70)
    print("RUNNER E2E DIAGNÓSTICO — Cancelamento com Bruna na Segunda")
    print("="*70)

    # Import Firebase
    try:
        from services.firebase_service_async import (
            buscar_subcolecao,
            salvar_dado_em_path,
            obter_id_dono,
        )
        from services.event_service_async import cancelar_evento_por_texto
        print("[OK] Firebase services importados")
    except Exception as e:
        print(f"[ERRO] Falha ao importar: {e}")
        return

    # Setup
    dono_id = "7371670478"  # Seu tenant/dono_id
    user_id = "7371670478"

    print(f"\n[CONFIG] dono_id={dono_id} user_id={user_id}")

    # Data para teste
    hoje = datetime.now().date()
    proxima_segunda = hoje + timedelta(days=(7-hoje.weekday()))  # Próxima segunda
    data_teste = str(proxima_segunda)

    print(f"[CONFIG] data_teste={data_teste}")

    # ========================================================================
    # ETAPA 1: Verificar eventos existentes
    # ========================================================================
    print("\n[ETAPA 1] Verificando eventos existentes em Firestore...")
    print("-" * 70)

    try:
        eventos = await buscar_subcolecao(f"Clientes/{dono_id}/Eventos") or {}
        print(f"[INFO] Total de eventos carregados: {len(eventos or {})}")

        # Listar eventos de Bruna
        print(f"\n[INFO] Eventos com profissional='Bruna':")
        bruna_events = []
        for eid, ev in (eventos or {}).items():
            if isinstance(ev, dict):
                prof = ev.get("profissional", "").strip()
                data = ev.get("data", "")
                status = ev.get("status", "").strip()
                hora = ev.get("hora_inicio", "")

                if prof.lower() == "bruna":
                    print(f"  - eid={eid}")
                    print(f"    profissional={prof} data={data} hora={hora} status={status}")
                    bruna_events.append((eid, ev))

        if not bruna_events:
            print("  [AVISO] Nenhum evento com Bruna encontrado!")
            print("  Você precisa criar eventos de teste primeiro.")
            print(f"  Veja docs/ para script de populacao de teste.")
            return

    except Exception as e:
        print(f"[ERRO] Falha ao buscar eventos: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # ETAPA 2: Executar cancelamento com diagnóstico
    # ========================================================================
    print("\n[ETAPA 2] Executando cancelar_evento_por_texto() com diagnóstico...")
    print("-" * 70)

    termo = "Cancelar com a Bruna na segunda"
    print(f"\n[INPUT] termo='{termo}'")
    print(f"[INPUT] user_id={user_id}")
    print(f"[INPUT] tenant_id={dono_id}")

    try:
        resultado, mensagem, candidatos = await cancelar_evento_por_texto(
            user_id=user_id,
            termo=termo,
            tenant_id=dono_id
        )

        print(f"\n[OUTPUT] resultado={resultado}")
        print(f"[OUTPUT] mensagem='{mensagem}'")
        print(f"[OUTPUT] candidatos_encontrados={len(candidatos)}")

        if candidatos:
            print(f"\n[OK] Encontrou {len(candidatos)} evento(s):")
            for i, (eid, ev) in enumerate(candidatos, 1):
                print(f"  {i}. {eid}")
                print(f"     profissional={ev.get('profissional')}")
                print(f"     data={ev.get('data')}")
                print(f"     hora={ev.get('hora_inicio')}")
        else:
            print(f"\n[ERRO] Nenhum candidato encontrado!")
            print(f"[ERRO] Mensagem: {mensagem}")
            print(f"\n[DIAGNÓSTICO]")
            print(f"  Verifique acima os logs [P0-DIAG-*]")
            print(f"  Eles mostram exatamente por qual filtro cada evento foi rejeitado")

    except Exception as e:
        print(f"[ERRO] Falha na execução: {e}")
        import traceback
        traceback.print_exc()
        return

    # ========================================================================
    # ETAPA 3: Resumo
    # ========================================================================
    print("\n" + "="*70)
    print("RESUMO")
    print("="*70)

    if candidatos:
        print(f"✓ SUCESSO: Sistema encontrou {len(candidatos)} evento(s)")
        print(f"✓ Bug NÃO confirmado - sistema está funcionando")
    else:
        print(f"✗ FALHA: Sistema não encontrou eventos")
        print(f"✗ Bug CONFIRMADO")
        print(f"\n[PRÓXIMO PASSO]")
        print(f"  1. Verificar logs [P0-DIAG-*] acima")
        print(f"  2. Identificar por qual filtro os eventos foram rejeitados")
        print(f"  3. Executar fix baseado em causa raiz")

    print()

if __name__ == "__main__":
    asyncio.run(main())
