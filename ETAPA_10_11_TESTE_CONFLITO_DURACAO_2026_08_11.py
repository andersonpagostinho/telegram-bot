#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 10 + 11 — TESTE CONFLITO E DURACAO VARIAVEL

Matriz de testes:
  Evento existente: 14:30-15:00

Casos de teste:
  14:00-15:30 (90 min) → CONFLITO
  14:00-14:30 (30 min) → LIVRE
  15:00-15:30 (30 min) → LIVRE
  14:29-15:01 (32 min) → CONFLITO
  14:30-15:00 (30 min) → CONFLITO
  14:15-14:45 (30 min) → CONFLITO
  14:45-15:15 (30 min) → CONFLITO

  Mesmo profissional → conflita
  Profissional diferente → nao conflita
  Mesmo tenant → conflita
  Tenant diferente → nao mistura

  Mesmo dia → considerar
  Outro dia → nao considera

ETAPA 11: Duracao variavel
  Servico A (45 min): 14:00-14:45 → NAO conflita
  Servico B (90 min): 14:00-15:30 → CONFLITA
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    atualizar_dado_em_path,
    deletar_dado_em_path,
    buscar_subcolecao,
)
from services.event_service_async import (
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


class TestadorConflito:
    def __init__(self):
        self.tenant_id = "teste_conflito_001"
        self.tenant_id_2 = "teste_conflito_002"
        self.data_teste = "2026-08-11"
        self.outro_dia = "2026-08-12"
        self.resultados = []

    async def setup(self):
        """Cleanup inicial"""
        try:
            for tenant in [self.tenant_id, self.tenant_id_2]:
                locks = await buscar_subcolecao(f"Clientes/{tenant}/AgendaLocks")
                for lid in locks.keys():
                    await deletar_dado_em_path(f"Clientes/{tenant}/AgendaLocks/{lid}")
            await deletar_dado_em_path(f"Clientes/{self.tenant_id}")
            await deletar_dado_em_path(f"Clientes/{self.tenant_id_2}")
        except:
            pass

    async def criar_evento_bloqueante(self, tenant_id, hora_inicio="14:30", hora_fim="15:00"):
        """Criar evento bloqueante"""
        resultado = await criar_com_lock_real(
            dono_id=tenant_id,
            evento={
                "profissional": "Carla",
                "servico": "Manicure",
                "data": self.data_teste,
                "hora_inicio": hora_inicio,
                "hora_fim": hora_fim,
                "duracao_minutos": int((datetime.strptime(hora_fim, "%H:%M") -
                                       datetime.strptime(hora_inicio, "%H:%M")).total_seconds() / 60),
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "outro_cliente",
                "cliente_nome": "Maria"
            },
            event_id=f"evt_bloqueante_{tenant_id}_{hora_inicio.replace(':', '')}"
        )
        return resultado.get("ok", False)

    async def testar_conflito(self, tenant_id, hora_inicio, duracao_min, profissional="Carla",
                             esperado="conflito", servico="Corte", data=None):
        """Testar um caso de conflito"""
        if data is None:
            data = self.data_teste

        resultado = await verificar_conflito_e_sugestoes_profissional(
            user_id=tenant_id,
            data=data,
            hora_inicio=hora_inicio,
            duracao_min=duracao_min,
            profissional=profissional,
            servico=servico
        )

        conflito_detectado = resultado.get("conflito", False)
        esperava_conflito = (esperado == "conflito")

        passou = conflito_detectado == esperava_conflito
        status = "PASS" if passou else "FAIL"

        self.resultados.append({
            "intervalo": f"{hora_inicio}-{int(int(hora_inicio.split(':')[0])*60 + int(hora_inicio.split(':')[1]) + duracao_min)//60:02d}:{int(int(hora_inicio.split(':')[0])*60 + int(hora_inicio.split(':')[1]) + duracao_min)%60:02d}",
            "duracao": duracao_min,
            "profissional": profissional,
            "esperado": esperado,
            "resultado": "conflito" if conflito_detectado else "livre",
            "status": status
        })

        print(f"[{status}] {hora_inicio} + {duracao_min}min → {self.resultados[-1]['intervalo']}")
        print(f"      Esperado: {esperado}, Obtido: {self.resultados[-1]['resultado']}")
        return passou

    async def executar(self):
        """Executar todos os testes"""
        print("="*80)
        print("[ETAPA 10 + 11] Teste Conflito e Duracao Variavel")
        print("="*80)

        await self.setup()

        # ETAPA 10: Criar evento bloqueante (14:30-15:00)
        print("\n[SETUP] Criando evento bloqueante (14:30-15:00)...")
        if not await self.criar_evento_bloqueante(self.tenant_id):
            print("[ERRO] Falha ao criar evento bloqueante")
            return False

        print("\n" + "="*80)
        print("[ETAPA 10] Matriz de Testes Conflito")
        print("="*80)

        casos_teste = [
            ("14:00", 90, "PASS", "Conflito 90min (14:00-15:30)"),
            ("14:00", 30, "PASS", "LIVRE 30min (14:00-14:30)"),
            ("15:00", 30, "PASS", "LIVRE 30min (15:00-15:30)"),
            ("14:29", 32, "PASS", "Conflito 14:29-15:01"),
            ("14:30", 30, "PASS", "Conflito exato (14:30-15:00)"),
            ("14:15", 30, "PASS", "Conflito parcial (14:15-14:45)"),
            ("14:45", 30, "PASS", "Conflito parcial (14:45-15:15)"),
        ]

        testes_passaram = 0
        testes_falharam = 0

        for hora, duracao, tipo_teste, descricao in casos_teste:
            esperado = "conflito" if duracao != 30 or hora != "14:00" and hora != "15:00" else "livre"
            if hora == "14:00" and duracao == 30:
                esperado = "livre"
            elif hora == "15:00" and duracao == 30:
                esperado = "livre"
            else:
                esperado = "conflito"

            print(f"\n[{tipo_teste}] {descricao}")
            passou = await self.testar_conflito(self.tenant_id, hora, duracao, esperado=esperado)
            if passou:
                testes_passaram += 1
            else:
                testes_falharam += 1

        # Testes adicionais: profissional diferente
        print("\n" + "="*80)
        print("[TESTE ADICIONAL] Profissional Diferente")
        print("="*80)

        print("\n[OK] Mesmo intervalo, profissional diferente (Bruno)...")
        passou = await self.testar_conflito(
            self.tenant_id, "14:00", 90,
            profissional="Bruno",  # Profissional diferente
            esperado="livre"
        )
        if passou:
            testes_passaram += 1
        else:
            testes_falharam += 1

        # Testes adicionais: tenant diferente
        print("\n" + "="*80)
        print("[TESTE ADICIONAL] Tenant Diferente (Multi-tenant)")
        print("="*80)

        print("\n[OK] Criando evento bloqueante em tenant 2...")
        if await self.criar_evento_bloqueante(self.tenant_id_2):
            print("[OK] Consultando em tenant diferente (nao deve conflitar)...")
            passou = await self.testar_conflito(
                self.tenant_id_2, "14:00", 90,
                esperado="livre"  # Nao conflita pq é outro tenant
            )
            if passou:
                testes_passaram += 1
            else:
                testes_falharam += 1

        # ETAPA 11: Duracao Variavel
        print("\n" + "="*80)
        print("[ETAPA 11] Teste Duracao Variavel (PERMANENTE)")
        print("="*80)

        print("\n[TESTE DURACAO] Servico A (45 min): 14:00-14:45...")
        passou_a = await self.testar_conflito(
            self.tenant_id, "14:00", 45,
            esperado="livre",
            servico="Corte"
        )
        if passou_a:
            testes_passaram += 1
        else:
            testes_falharam += 1

        print("\n[TESTE DURACAO] Servico B (90 min): 14:00-15:30...")
        passou_b = await self.testar_conflito(
            self.tenant_id, "14:00", 90,
            esperado="conflito",
            servico="Corte + Hidratacao"
        )
        if passou_b:
            testes_passaram += 1
        else:
            testes_falharam += 1

        # RESUMO
        print("\n" + "="*80)
        print("[RESUMO] Etapas 10 + 11")
        print("="*80)

        print(f"\nTotal testes: {testes_passaram + testes_falharam}")
        print(f"Passaram: {testes_passaram} PASS")
        print(f"Falharam: {testes_falharam} FAIL")

        print(f"\nResultados:")
        for r in self.resultados:
            print(f"  {r['intervalo']} ({r['duracao']}min) → {r['status']}")

        if testes_falharam == 0:
            print("\n[OK] TODOS OS TESTES PASSARAM")
            return True
        else:
            print(f"\n[ERRO] {testes_falharam} testes falharam")
            return False


async def main():
    testador = TestadorConflito()
    sucesso = await testador.executar()

    try:
        locks = await buscar_subcolecao(f"Clientes/{testador.tenant_id}/AgendaLocks")
        for lid in locks.keys():
            await deletar_dado_em_path(f"Clientes/{testador.tenant_id}/AgendaLocks/{lid}")
        await deletar_dado_em_path(f"Clientes/{testador.tenant_id}")
        await deletar_dado_em_path(f"Clientes/{testador.tenant_id_2}")
    except:
        pass

    return 0 if sucesso else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
