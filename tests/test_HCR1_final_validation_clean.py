"""
HCR-1 FINAL VALIDATION — TEST1 REEXECUÇÃO COM TENANT EXCLUSIVO

Objetivo: eliminar dados residuais e validar ordenação em condições limpas.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from services.firebase_service_async import (
    atualizar_dado_em_path,
    buscar_dado_em_path,
)
from services.event_service_async import cancelar_evento_por_texto


async def test_1_clean():
    """Test 1: Dois eventos futuros em datas diferentes — CONDIÇÕES LIMPAS"""

    print("\n" + "=" * 80)
    print("HCR-1 FINAL VALIDATION — TEST1 REEXECUÇÃO")
    print("=" * 80)

    # Tenant exclusivo com timestamp
    tenant_teste = f"hrс1_final_clean_{int(datetime.now().timestamp())}"
    cliente_teste = f"cliente_final_{int(datetime.now().timestamp())}"

    print(f"\n[SETUP] Tenant novo: {tenant_teste}")
    print(f"[SETUP] Cliente novo: {cliente_teste}")

    try:
        # Verificar tenant vazio
        tenant_doc = await buscar_dado_em_path(f"Clientes/{tenant_teste}")
        if tenant_doc:
            print(f"❌ Tenant já existe! Abortar.")
            return "FAIL"

        print(f"✅ Tenant é novo (isolado)")

        # Criar EXATAMENTE 2 eventos
        data_futura_1 = (datetime.now() + timedelta(days=5)).date().isoformat()
        data_futura_2 = (datetime.now() + timedelta(days=10)).date().isoformat()

        print(f"\n[EVENTOS] Criando evento 1:")
        print(f"  - Data: {data_futura_1} (5 dias no futuro)")
        print(f"  - Profissional: Bruna")

        evento_1 = {
            "cliente_id": cliente_teste,
            "descricao": "Corte com Bruna",
            "profissional": "Bruna",
            "data": data_futura_1,
            "hora_inicio": "10:00",
            "hora_fim": "10:30",
            "servico": "corte",
            "status": "confirmado",
            "criado_em": (datetime.now() - timedelta(days=3)).isoformat(),
        }

        path_1 = f"Clientes/{tenant_teste}/Eventos/E_BRUNA_001"
        await atualizar_dado_em_path(path_1, evento_1)
        print(f"✅ Evento 1 criado: {path_1}")

        print(f"\n[EVENTOS] Criando evento 2:")
        print(f"  - Data: {data_futura_2} (10 dias no futuro)")
        print(f"  - Profissional: Gloria")

        evento_2 = {
            "cliente_id": cliente_teste,
            "descricao": "Corte com Gloria",
            "profissional": "Gloria",
            "data": data_futura_2,
            "hora_inicio": "14:00",
            "hora_fim": "14:30",
            "servico": "corte",
            "status": "confirmado",
            "criado_em": datetime.now().isoformat(),
        }

        path_2 = f"Clientes/{tenant_teste}/Eventos/E_GLORIA_001"
        await atualizar_dado_em_path(path_2, evento_2)
        print(f"✅ Evento 2 criado: {path_2}")

        # Verificar quantidade inicial
        print(f"\n[VALIDAÇÃO] Verificando quantidade de eventos...")
        from services.firebase_service_async import buscar_subcolecao
        eventos = await buscar_subcolecao(f"Clientes/{tenant_teste}/Eventos") or {}
        eventos_count = len(eventos)
        print(f"  - Total de eventos no tenant: {eventos_count}")

        if eventos_count != 2:
            print(f"❌ ERRO: Esperado 2, obteve {eventos_count}")
            return "FAIL"

        print(f"✅ Quantidade correta: 2 eventos")

        # Executar busca
        print(f"\n[BUSCA] Executando cancelar_evento_por_texto...")
        ok, msg, candidatos = await cancelar_evento_por_texto(
            user_id=cliente_teste,
            termo="corte",
            tenant_id=tenant_teste
        )

        print(f"  - Encontrados: {len(candidatos)} eventos")
        print(f"  - Mensagem: {msg[:80]}...")

        if len(candidatos) != 2:
            print(f"❌ ERRO: Esperado 2 candidatos, obteve {len(candidatos)}")
            return "FAIL"

        # Validar ordem
        print(f"\n[ORDEM] Validando ordem dos candidatos...")

        for i, (eid, ev) in enumerate(candidatos, start=1):
            prof = ev.get("profissional", "")
            data = ev.get("data", "")
            hora = ev.get("hora_inicio", "")
            print(f"  {i}) {prof:15} — {data} às {hora} (evento_id={eid})")

        primeiro_data = candidatos[0][1].get("data")
        segundo_data = candidatos[1][1].get("data")

        if primeiro_data < segundo_data:
            print(f"✅ Ordem CORRETA: {primeiro_data} < {segundo_data}")
            ordem_ok = True
        else:
            print(f"❌ Ordem INCORRETA: {primeiro_data} >= {segundo_data}")
            ordem_ok = False

        # Validar identidade
        print(f"\n[IDENTIDADE] Validando evento_ids...")
        eids = [eid for eid, _ in candidatos]

        if "E_BRUNA_001" in eids and "E_GLORIA_001" in eids:
            print(f"✅ Evento_ids preservados: {eids}")
            identidade_ok = True
        else:
            print(f"❌ Evento_ids PERDIDOS: {eids}")
            identidade_ok = False

        # Validar que documentos não foram alterados
        print(f"\n[INTEGRIDADE] Verificando que documentos não foram alterados...")
        ev1_check = await buscar_dado_em_path(path_1)
        ev2_check = await buscar_dado_em_path(path_2)

        if ev1_check and ev2_check:
            if (ev1_check.get("descricao") == evento_1["descricao"] and
                ev2_check.get("descricao") == evento_2["descricao"]):
                print(f"✅ Documentos íntegros (não foram alterados)")
                integridade_ok = True
            else:
                print(f"❌ Documentos foram MODIFICADOS")
                integridade_ok = False
        else:
            print(f"❌ Documentos não encontrados")
            integridade_ok = False

        # Resultado final
        print(f"\n" + "=" * 80)
        if ordem_ok and identidade_ok and integridade_ok:
            print(f"✅ TEST1 CLEAN — PASS")
            return "PASS"
        else:
            print(f"❌ TEST1 CLEAN — FAIL")
            print(f"  - Ordem: {'✅ OK' if ordem_ok else '❌ FALHOU'}")
            print(f"  - Identidade: {'✅ OK' if identidade_ok else '❌ FALHOU'}")
            print(f"  - Integridade: {'✅ OK' if integridade_ok else '❌ FALHOU'}")
            return "FAIL"

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return "ERROR"


async def main():
    resultado = await test_1_clean()
    sys.exit(0 if resultado == "PASS" else 1)


if __name__ == "__main__":
    asyncio.run(main())
