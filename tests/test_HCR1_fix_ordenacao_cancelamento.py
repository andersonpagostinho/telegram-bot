"""
HCR-1 FIX — Validação de ordenação em cancelamentos

Testa que eventos futuros são apresentados em ordem de proximidade (mais próxima primeiro).
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


class TestHCR1Fix:
    """Suite de testes para validação de HCR-1 (ordenação em cancelamentos)."""

    def __init__(self):
        self.tenant_teste = "tenant_hrс1_fix_20261105"
        self.cliente_teste = "cliente_hrc1_20261105"
        self.resultados = []
        self.dados_criados = []

    async def setup(self):
        """Setup de teste."""
        print("\n" + "=" * 80)
        print("TESTES HCR-1 FIX — ORDENAÇÃO EM CANCELAMENTOS")
        print("=" * 80)
        print(f"[SETUP] Tenant: {self.tenant_teste}")
        print(f"[SETUP] Cliente: {self.cliente_teste}")

    async def criar_evento(self, evento_id: str, descricao: str, profissional: str, data: str, hora: str, dias_atras: int = 0):
        """Criar evento de teste."""
        evento = {
            "cliente_id": self.cliente_teste,
            "descricao": descricao,
            "profissional": profissional,
            "data": data,
            "hora_inicio": hora,
            "hora_fim": f"{int(hora.split(':')[0])+1}:00",
            "servico": "corte",
            "status": "confirmado",
            "criado_em": (datetime.now() - timedelta(days=dias_atras)).isoformat(),
        }

        path = f"Clientes/{self.tenant_teste}/Eventos/{evento_id}"
        await atualizar_dado_em_path(path, evento)
        self.dados_criados.append(path)
        return evento_id, evento

    async def test_1_dois_eventos_datas_diferentes(self):
        """Teste 1: Dois eventos futuros em datas diferentes."""
        print("\n" + "-" * 80)
        print("TESTE 1: Dois eventos futuros em datas diferentes")
        print("-" * 80)

        try:
            data_futura_1 = (datetime.now() + timedelta(days=5)).date().isoformat()
            data_futura_2 = (datetime.now() + timedelta(days=10)).date().isoformat()

            await self.criar_evento("E1_ANTERIOR", "Corte com Bruna", "Bruna", data_futura_1, "10:00", dias_atras=3)
            await self.criar_evento("E2_POSTERIOR", "Corte com Gloria", "Gloria", data_futura_2, "14:00", dias_atras=0)

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=self.cliente_teste,
                termo="corte",
                tenant_id=self.tenant_teste
            )

            if len(candidatos) == 2:
                primeiro = candidatos[0]
                segunda = candidatos[1]

                primeiro_data = primeiro[1].get("data")
                segunda_data = segunda[1].get("data")

                if primeiro_data < segunda_data:
                    print(f"✅ [TEST1-PASS] Ordem correta: {primeiro_data} → {segunda_data}")
                    resultado = "PASS"
                else:
                    print(f"❌ [TEST1-FAIL] Ordem incorreta: {primeira_data} → {segunda_data}")
                    resultado = "FAIL"
            else:
                print(f"❌ [TEST1-FAIL] Esperado 2 candidatos, obteve {len(candidatos)}")
                resultado = "FAIL"

            self.resultados.append({
                "teste": "TEST1",
                "descricao": "Dois eventos - datas diferentes",
                "resultado": resultado,
                "candidatos_count": len(candidatos),
            })

        except Exception as e:
            print(f"❌ [TEST1-ERROR] {e}")
            self.resultados.append({
                "teste": "TEST1",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def test_2_evento_antigo_futuro(self):
        """Teste 2: Evento antigo (criado dias atrás) vs novo."""
        print("\n" + "-" * 80)
        print("TESTE 2: Evento antigo vs novo (mesmo cenário de diagnóstico)")
        print("-" * 80)

        try:
            data_futura_bruna = (datetime.now() + timedelta(days=5)).date().isoformat()
            data_futura_gloria = (datetime.now() + timedelta(days=7)).date().isoformat()

            await self.criar_evento("E_BRUNA_OLD", "Corte com Bruna", "Bruna", data_futura_bruna, "10:00", dias_atras=3)
            await self.criar_evento("E_GLORIA_NEW", "Corte com Gloria", "Gloria", data_futura_gloria, "14:00", dias_atras=0)

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=self.cliente_teste,
                termo="corte",
                tenant_id=self.tenant_teste
            )

            if len(candidatos) >= 2:
                # Procura Bruna e Gloria na lista
                bruna_idx = None
                gloria_idx = None

                for i, (eid, ev) in enumerate(candidatos):
                    prof = ev.get("profissional", "").lower()
                    if "bruna" in prof:
                        bruna_idx = i
                    elif "gloria" in prof:
                        gloria_idx = i

                if bruna_idx is not None and gloria_idx is not None:
                    if bruna_idx < gloria_idx:
                        print(f"✅ [TEST2-PASS] Bruna (5 dias) aparece antes de Gloria (7 dias)")
                        resultado = "PASS"
                    else:
                        print(f"❌ [TEST2-FAIL] Gloria aparece antes de Bruna (ordem invertida)")
                        resultado = "FAIL"
                else:
                    print(f"❌ [TEST2-FAIL] Não encontrou ambos os profissionais")
                    resultado = "FAIL"
            else:
                print(f"❌ [TEST2-FAIL] Esperado >= 2 candidatos, obteve {len(candidatos)}")
                resultado = "FAIL"

            self.resultados.append({
                "teste": "TEST2",
                "descricao": "Evento antigo vs novo (diagnóstico)",
                "resultado": resultado,
                "candidatos_count": len(candidatos),
            })

        except Exception as e:
            print(f"❌ [TEST2-ERROR] {e}")
            self.resultados.append({
                "teste": "TEST2",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def test_3_dois_eventos_mesma_data_horas_diferentes(self):
        """Teste 3: Dois eventos no mesmo dia com horários diferentes."""
        print("\n" + "-" * 80)
        print("TESTE 3: Mesma data, horários diferentes")
        print("-" * 80)

        try:
            data_futura = (datetime.now() + timedelta(days=3)).date().isoformat()

            await self.criar_evento("E_CEDO", "Corte matutino", "Bruna", data_futura, "09:00", dias_atras=0)
            await self.criar_evento("E_TARDE", "Corte vespertino", "Gloria", data_futura, "14:00", dias_atras=0)

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=self.cliente_teste,
                termo="corte",
                tenant_id=self.tenant_teste
            )

            if len(candidatos) >= 2:
                primeira_hora = candidatos[0][1].get("hora_inicio")
                segunda_hora = candidatos[1][1].get("hora_inicio")

                if primeira_hora <= segunda_hora:
                    print(f"✅ [TEST3-PASS] Ordem correta: {primeira_hora} → {segunda_hora}")
                    resultado = "PASS"
                else:
                    print(f"❌ [TEST3-FAIL] Ordem incorreta: {primeira_hora} → {segunda_hora}")
                    resultado = "FAIL"
            else:
                print(f"❌ [TEST3-FAIL] Esperado >= 2 candidatos, obteve {len(candidatos)}")
                resultado = "FAIL"

            self.resultados.append({
                "teste": "TEST3",
                "descricao": "Mesma data, horários diferentes",
                "resultado": resultado,
                "candidatos_count": len(candidatos),
            })

        except Exception as e:
            print(f"❌ [TEST3-ERROR] {e}")
            self.resultados.append({
                "teste": "TEST3",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def test_4_preservacao_evento_ids(self):
        """Teste 4: Preservação de evento_ids após ordenação."""
        print("\n" + "-" * 80)
        print("TESTE 4: Preservação de evento_ids")
        print("-" * 80)

        try:
            data_1 = (datetime.now() + timedelta(days=3)).date().isoformat()
            data_2 = (datetime.now() + timedelta(days=5)).date().isoformat()

            eid1, _ = await self.criar_evento("PRESERVE_001", "Corte A", "Profissional A", data_1, "10:00")
            eid2, _ = await self.criar_evento("PRESERVE_002", "Corte B", "Profissional B", data_2, "11:00")

            ok, msg, candidatos = await cancelar_evento_por_texto(
                user_id=self.cliente_teste,
                termo="corte",
                tenant_id=self.tenant_teste
            )

            # Verificar que evento_ids estão presentes e idênticos
            eids_na_lista = [eid for eid, _ in candidatos]

            if eid1 in eids_na_lista and eid2 in eids_na_lista:
                print(f"✅ [TEST4-PASS] Ambos evento_ids preservados: {eid1}, {eid2}")
                resultado = "PASS"
            else:
                print(f"❌ [TEST4-FAIL] Faltam evento_ids: {eids_na_lista}")
                resultado = "FAIL"

            self.resultados.append({
                "teste": "TEST4",
                "descricao": "Preservação de evento_ids",
                "resultado": resultado,
                "evento_ids_preservados": eid1 in eids_na_lista and eid2 in eids_na_lista,
            })

        except Exception as e:
            print(f"❌ [TEST4-ERROR] {e}")
            self.resultados.append({
                "teste": "TEST4",
                "resultado": "ERROR",
                "erro": str(e),
            })

    async def relatorio_final(self):
        """Gerar relatório final."""
        print("\n" + "=" * 80)
        print("RELATÓRIO FINAL — HCR-1 FIX")
        print("=" * 80)

        passed = sum(1 for r in self.resultados if r.get("resultado") == "PASS")
        failed = sum(1 for r in self.resultados if r.get("resultado") == "FAIL")
        error = sum(1 for r in self.resultados if r.get("resultado") == "ERROR")

        print(f"\n📊 RESUMO:")
        print(f"   ✅ PASS: {passed}")
        print(f"   ❌ FAIL: {failed}")
        print(f"   🔥 ERROR: {error}")
        print(f"   TOTAL: {len(self.resultados)}")

        print(f"\n📋 RESULTADOS:")
        for r in self.resultados:
            icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "🔥"}.get(r.get("resultado"), "❓")
            print(f"{icon} {r.get('teste')}: {r.get('resultado')} - {r.get('descricao')}")

        print("\n" + "=" * 80)

        # Retornar sucesso se todos passarem
        return failed == 0 and error == 0

    async def executar(self):
        """Executar suite de testes."""
        await self.setup()
        await self.test_1_dois_eventos_datas_diferentes()
        await self.test_2_evento_antigo_futuro()
        await self.test_3_dois_eventos_mesma_data_horas_diferentes()
        await self.test_4_preservacao_evento_ids()
        await self.relatorio_final()
        return await self.relatorio_final()


async def main():
    """Ponto de entrada."""
    suite = TestHCR1Fix()
    sucesso = await suite.executar()
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    asyncio.run(main())
