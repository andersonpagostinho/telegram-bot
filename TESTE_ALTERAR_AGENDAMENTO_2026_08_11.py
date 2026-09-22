#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE P0: ALTERAR AGENDAMENTO / REAGENDAMENTO

Cenarios:
1. Criar agendamento original
2. Alterar para novo horario (sem conflito)
3. Validar que evento antigo foi cancelado
4. Validar que evento novo foi criado
5. Validar que novo evento está no Firestore
6. Testar conflito no novo horario
7. Testar ownership (cliente nao pode alterar evento alheio)
8. Testar multi-tenant (isolamento)
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    buscar_subcolecao,
    deletar_dado_em_path,
    buscar_dado_em_path,
)
from services.event_service_async import (
    alterar_agendamento,
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real


class TestadorAlteracao:
    def __init__(self):
        self.tenant_id = "teste_alteracao_001"
        self.cliente_id = "cliente_alteracao_001"
        self.data_original = "2026-08-11"
        self.data_nova = "2026-08-12"
        self.resultados = []

    async def setup(self):
        """Cleanup inicial"""
        try:
            for tenant in [self.tenant_id]:
                locks = await buscar_subcolecao(f"Clientes/{tenant}/AgendaLocks")
                for lid in locks.keys():
                    await deletar_dado_em_path(f"Clientes/{tenant}/AgendaLocks/{lid}")
            await deletar_dado_em_path(f"Clientes/{self.tenant_id}")
        except:
            pass

    async def teste_cenario(self, nome: str, teste_fn):
        """Executar teste e registrar resultado"""
        try:
            resultado = await teste_fn()
            status = "[PASS]" if resultado else "[FAIL]"
            self.resultados.append({
                "nome": nome,
                "status": status,
                "resultado": resultado
            })
            print(f"{status} {nome}")
            return resultado
        except Exception as e:
            print(f"[ERRO] {nome}: {str(e)}")
            self.resultados.append({
                "nome": nome,
                "status": "[ERRO]",
                "resultado": str(e)
            })
            return False

    async def cenario_1_criar_agendamento_original(self):
        """Cenario 1: Criar agendamento original"""
        print("\n[CENARIO 1] Criando agendamento original...")

        resultado = await criar_com_lock_real(
            dono_id=self.tenant_id,
            evento={
                "profissional": "Carla",
                "servico": "Manicure",
                "data": self.data_original,
                "hora_inicio": "14:30",
                "hora_fim": "15:00",
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": self.cliente_id,
                "cliente_nome": "Teste Alteracao"
            },
            event_id="evt_original_001"
        )

        self.evento_original_id = "evt_original_001"
        self.evento_criado = resultado.get("ok", False)

        if self.evento_criado:
            print(f"[OK] Evento original criado: {self.evento_original_id}")
            # Verificar persistencia
            evento = await buscar_dado_em_path(
                f"Clientes/{self.tenant_id}/Eventos/{self.evento_original_id}"
            )
            return evento is not None
        return False

    async def cenario_2_alterar_sem_conflito(self):
        """Cenario 2: Alterar para novo horario (sem conflito)"""
        print("\n[CENARIO 2] Alterando agendamento para novo horario...")
        print(f"[DEBUG] event_id={self.evento_original_id}, user_id={self.cliente_id}")

        try:
            resultado = await alterar_agendamento(
                user_id=self.cliente_id,
                event_id=self.evento_original_id,
                nova_data=self.data_nova,
                nova_hora_inicio="10:00",
                nova_duracao_minutos=30
            )

            print(f"[DEBUG] Resultado completo: {resultado}")

            if resultado.get("ok"):
                self.evento_novo_id = resultado.get("evento_id")
                print(f"[OK] Agendamento alterado para novo evento: {self.evento_novo_id}")
                return True

            print(f"[FALHA] Motivo: {resultado.get('motivo')}")
            return False
        except Exception as e:
            print(f"[ERRO_EXCECAO] {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def cenario_3_validar_evento_antigo_cancelado(self):
        """Cenario 3: Validar que evento antigo foi cancelado"""
        print("\n[CENARIO 3] Validando cancelamento do evento antigo...")

        evento_antigo = await buscar_dado_em_path(
            f"Clientes/{self.tenant_id}/Eventos/{self.evento_original_id}"
        )

        if evento_antigo:
            status = evento_antigo.get("status", "").lower()
            cancelado = status == "cancelado"

            if cancelado:
                print(f"[OK] Evento original cancelado: {evento_antigo.get('cancelado_em', 'N/A')}")
                return True
            else:
                print(f"[FALHA] Evento ainda ativo: status={status}")
                return False

        print(f"[FALHA] Evento original nao encontrado")
        return False

    async def cenario_4_validar_evento_novo_criado(self):
        """Cenario 4: Validar que evento novo foi criado"""
        print("\n[CENARIO 4] Validando criacao do evento novo...")

        evento_novo = await buscar_dado_em_path(
            f"Clientes/{self.tenant_id}/Eventos/{self.evento_novo_id}"
        )

        if evento_novo:
            print(f"[OK] Evento novo criado e persistido")
            print(f"    Data: {evento_novo.get('data')}")
            print(f"    Hora: {evento_novo.get('hora_inicio')}")
            print(f"    Profissional: {evento_novo.get('profissional')}")
            return True

        print(f"[FALHA] Evento novo nao encontrado: {self.evento_novo_id}")
        return False

    async def cenario_5_validar_dados_evento_novo(self):
        """Cenario 5: Validar que dados do evento novo estao corretos"""
        print("\n[CENARIO 5] Validando dados do evento novo...")

        evento_novo = await buscar_dado_em_path(
            f"Clientes/{self.tenant_id}/Eventos/{self.evento_novo_id}"
        )

        if not evento_novo:
            print(f"[FALHA] Evento novo nao encontrado")
            return False

        validacoes = [
            ("data", self.data_nova, evento_novo.get("data")),
            ("hora_inicio", "10:00", evento_novo.get("hora_inicio")),
            ("profissional", "Carla", evento_novo.get("profissional")),
            ("servico", "Manicure", evento_novo.get("servico")),
            ("duracao_minutos", 30, evento_novo.get("duracao_minutos")),
            ("confirmado", True, evento_novo.get("confirmado")),
            ("status", "confirmado", evento_novo.get("status")),
            ("cliente_id", self.cliente_id, evento_novo.get("cliente_id")),
        ]

        todos_ok = True
        for campo, esperado, obtido in validacoes:
            match = esperado == obtido
            status = "[OK]" if match else "[FALHA]"
            print(f"  {status} {campo}: esperado={esperado}, obtido={obtido}")
            if not match:
                todos_ok = False

        return todos_ok

    async def cenario_6_alterar_com_conflito(self):
        """Cenario 6: Testar que alterar para horario ocupado falha"""
        print("\n[CENARIO 6] Testando alterar com conflito...")

        # Criar outro evento occupado no mesmo horario
        resultado_bloqueante = await criar_com_lock_real(
            dono_id=self.tenant_id,
            evento={
                "profissional": "Carla",
                "servico": "Corte",
                "data": self.data_nova,
                "hora_inicio": "15:00",
                "hora_fim": "15:30",
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "outro_cliente",
                "cliente_nome": "Outro Cliente"
            },
            event_id="evt_bloqueante_conflito"
        )

        if not resultado_bloqueante.get("ok"):
            print(f"[FALHA] Nao consegui criar evento bloqueante")
            return False

        # Tentar alterar evento novo para horario ocupado
        resultado_conflito = await alterar_agendamento(
            user_id=self.cliente_id,
            event_id=self.evento_novo_id,
            nova_data=self.data_nova,
            nova_hora_inicio="15:00",
            nova_duracao_minutos=30
        )

        if resultado_conflito.get("conflito"):
            print(f"[OK] Conflito detectado corretamente")
            print(f"    Sugestoes oferecidas: {resultado_conflito.get('sugestoes', [])}")
            return True

        if not resultado_conflito.get("ok"):
            print(f"[OK] Alteracao bloqueada: {resultado_conflito.get('motivo')}")
            return True

        print(f"[FALHA] Deveria ter detectado conflito")
        return False

    async def cenario_7_ownership_cliente_nao_pode_alterar_alheio(self):
        """Cenario 7: Cliente nao pode alterar evento de outro cliente"""
        print("\n[CENARIO 7] Validando ownership (cliente nao pode alterar evento alheio)...")

        # Criar evento de outro cliente
        resultado_outro = await criar_com_lock_real(
            dono_id=self.tenant_id,
            evento={
                "profissional": "Bruno",
                "servico": "Corte",
                "data": self.data_original,
                "hora_inicio": "11:00",
                "hora_fim": "11:30",
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": "outro_cliente_002",
                "cliente_nome": "Outro"
            },
            event_id="evt_outro_cliente"
        )

        if not resultado_outro.get("ok"):
            print(f"[FALHA] Nao consegui criar evento para outro cliente")
            return False

        # Tentar alterar evento de outro cliente com user_id diferente
        resultado_tentativa = await alterar_agendamento(
            user_id=self.cliente_id,  # Cliente diferente!
            event_id="evt_outro_cliente",
            nova_data=self.data_nova,
            nova_hora_inicio="16:00"
        )

        if not resultado_tentativa.get("ok"):
            print(f"[OK] Alteracao bloqueada corretamente: {resultado_tentativa.get('motivo')}")
            return True

        print(f"[FALHA] Deveria ter bloqueado alteracao")
        return False

    async def cenario_8_multi_tenant_isolamento(self):
        """Cenario 8: Multi-tenant isolado"""
        print("\n[CENARIO 8] Validando isolamento multi-tenant...")

        tenant_2 = "teste_alteracao_002"
        cliente_2 = "cliente_alteracao_002"

        # Criar evento em tenant 2
        resultado_tenant2 = await criar_com_lock_real(
            dono_id=tenant_2,
            evento={
                "profissional": "Carla",
                "servico": "Manicure",
                "data": self.data_original,
                "hora_inicio": "10:00",
                "hora_fim": "10:30",
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": cliente_2,
                "cliente_nome": "Teste Tenant 2"
            },
            event_id="evt_tenant2_001"
        )

        if not resultado_tenant2.get("ok"):
            print(f"[FALHA] Nao consegui criar evento em tenant 2")
            return False

        # Tentar alterar evento de tenant 2 usando cliente de tenant 1
        resultado_cross = await alterar_agendamento(
            user_id=self.cliente_id,  # Cliente de tenant 1
            event_id="evt_tenant2_001",  # Evento de tenant 2
            nova_data=self.data_nova,
            nova_hora_inicio="14:00"
        )

        # Deveria falhar porque evento nao existe no tenant 1
        if not resultado_cross.get("ok"):
            print(f"[OK] Cross-tenant bloqueado corretamente")
            return True

        print(f"[FALHA] Deveria ter bloqueado cross-tenant")
        return False

    async def executar(self):
        """Executar todos os cenarios"""
        print("="*80)
        print("[P0] TESTE ALTERAR AGENDAMENTO / REAGENDAMENTO")
        print("="*80)

        await self.setup()

        # Executar cenarios em sequencia
        await self.teste_cenario(
            "1. Criar agendamento original",
            self.cenario_1_criar_agendamento_original
        )

        await self.teste_cenario(
            "2. Alterar para novo horario (sem conflito)",
            self.cenario_2_alterar_sem_conflito
        )

        await self.teste_cenario(
            "3. Validar evento antigo cancelado",
            self.cenario_3_validar_evento_antigo_cancelado
        )

        await self.teste_cenario(
            "4. Validar evento novo criado",
            self.cenario_4_validar_evento_novo_criado
        )

        await self.teste_cenario(
            "5. Validar dados evento novo",
            self.cenario_5_validar_dados_evento_novo
        )

        await self.teste_cenario(
            "6. Alterar com conflito",
            self.cenario_6_alterar_com_conflito
        )

        await self.teste_cenario(
            "7. Ownership cliente bloqueado",
            self.cenario_7_ownership_cliente_nao_pode_alterar_alheio
        )

        await self.teste_cenario(
            "8. Multi-tenant isolado",
            self.cenario_8_multi_tenant_isolamento
        )

        # Resumo
        print("\n" + "="*80)
        print("[RESUMO]")
        print("="*80)

        passed = sum(1 for r in self.resultados if r["status"] == "[PASS]")
        failed = sum(1 for r in self.resultados if r["status"] == "[FAIL]")
        errors = sum(1 for r in self.resultados if r["status"] == "[ERRO]")

        print(f"\nPassou: {passed}/8")
        print(f"Falhou: {failed}/8")
        print(f"Erros: {errors}/8")

        if failed == 0 and errors == 0:
            print(f"\n[OK] TODOS OS CENARIOS PASSARAM")
            return 0
        else:
            print(f"\n[FALHA] Alguns cenarios falharam")
            return 1


async def main():
    testador = TestadorAlteracao()
    return await testador.executar()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
