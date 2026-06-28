#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTE P0: Bloqueio de Promoção Automática Cliente → Dono

Objetivo: Validar que cliente não é promovido a dono automaticamente
por fallback em obter_id_dono() ou tenant_tem_dono()==False

Cenários:
1. Cliente com modo_uso="atendimento_cliente" não recebe onboarding_dono
2. Cliente desconhecido é criado como cliente, não dono
3. Novo dono explícito (user_id==tenant_id) ainda funciona
4. Dono existente sem onboarding continua funcionando
5. Multi-tenant: cliente não vira dono em outro tenant
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
projeto_dir = r"C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
load_dotenv(Path(projeto_dir) / ".env")
sys.path.insert(0, projeto_dir)
os.chdir(projeto_dir)

from services.firestore_client import get_db
from services.identidade_service import normalizar_actor_id
from router.integracao_identidade_onboarding import resolver_ator_e_validar_guard


class TesteBloqueioPromocaoCliente:
    def __init__(self):
        self.resultados = []
        self.limpar = True

    async def setup_tenant_novo(self, tenant_id: str):
        """Limpar tenant novo para teste"""
        try:
            get_db().collection("Clientes").document(tenant_id).delete()
        except:
            pass

    async def cleanup_tenant(self, tenant_id: str):
        """Limpar tenant após teste"""
        try:
            get_db().collection("Clientes").document(tenant_id).delete()
        except:
            pass

    async def registrar_resultado(self, numero: int, nome: str, passou: bool, motivo: str = ""):
        """Registrar resultado"""
        resultado = {
            "numero": numero,
            "nome": nome,
            "status": "PASS" if passou else "FAIL",
            "motivo": motivo,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.resultados.append(resultado)
        status_str = "[PASS]" if passou else "[FAIL]"
        print(f"\n{status_str} Teste {numero}: {nome}")
        if motivo:
            print(f"    Motivo: {motivo}")

    async def teste_01_cliente_com_modo_uso(self):
        """Teste 1: Cliente com modo_uso='atendimento_cliente' não recebe onboarding"""
        tenant_id = "test_bloqueio_cliente_modo_uso"
        await self.setup_tenant_novo(tenant_id)

        try:
            # Criar um tenant DONO para referência
            dono_id = normalizar_actor_id("whatsapp", "5511988888888")
            actor_dono = normalizar_actor_id("whatsapp", "5511988888888")

            # Cliente com modo_uso
            cliente_id = normalizar_actor_id("whatsapp", "5511999999999")

            # Simular: resolver_ator_e_validar_guard com tenant conhecido
            resultado = await resolver_ator_e_validar_guard(
                user_id=cliente_id,
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="5511999999999"
            )

            # Validações
            assert resultado.get("sucesso"), "Resolver ator deve ser bem-sucedido"
            assert resultado.get("tipo_usuario") == "cliente", \
                f"Cliente deve ter tipo_usuario='cliente', obteve '{resultado.get('tipo_usuario')}'"
            assert resultado.get("requer_onboarding") == False, \
                "Cliente não deve requerer onboarding_dono"
            assert resultado.get("proxima_acao") != "onboarding", \
                f"proxima_acao deveria ser 'normal', obteve '{resultado.get('proxima_acao')}'"

            await self.registrar_resultado(
                1,
                "Cliente com modo_uso não recebe onboarding",
                True,
                "Cliente criado corretamente com tipo_usuario='cliente'"
            )

        except AssertionError as e:
            await self.registrar_resultado(1, "Cliente com modo_uso não recebe onboarding", False, str(e))
        finally:
            if self.limpar:
                await self.cleanup_tenant(tenant_id)

    async def teste_02_cliente_desconhecido_fallback_seguro(self):
        """Teste 2: Cliente desconhecido é criado como cliente, não dono"""
        tenant_id = "test_bloqueio_cliente_novo"
        await self.setup_tenant_novo(tenant_id)

        try:
            cliente_id = normalizar_actor_id("whatsapp", "5511977777777")

            # Tenant não tem dono, actor é desconhecido
            resultado = await resolver_ator_e_validar_guard(
                user_id=cliente_id,
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador="5511977777777"
            )

            # Validações (fallback seguro: cliente, não dono)
            assert resultado.get("sucesso"), "Resolver deve ser bem-sucedido"
            assert resultado.get("tipo_usuario") == "cliente", \
                f"Actor desconhecido deve ser cliente (fallback seguro), obteve '{resultado.get('tipo_usuario')}'"
            assert resultado.get("requer_onboarding") == False, \
                "Cliente não deve requerer onboarding de dono"

            await self.registrar_resultado(
                2,
                "Cliente desconhecido criado como cliente (fallback seguro)",
                True,
                "Bloqueio de promoção automática funcionando"
            )

        except AssertionError as e:
            await self.registrar_resultado(2, "Cliente desconhecido", False, str(e))
        finally:
            if self.limpar:
                await self.cleanup_tenant(tenant_id)

    async def teste_03_novo_dono_explicito_funciona(self):
        """Teste 3: Novo dono (user_id==tenant_id) ainda funciona"""
        tenant_id = "test_bloqueio_novo_dono"
        await self.setup_tenant_novo(tenant_id)

        try:
            # Caso explícito: user_id == tenant_id
            dono_id = tenant_id

            resultado = await resolver_ator_e_validar_guard(
                user_id=dono_id,
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador=dono_id
            )

            # Validações
            assert resultado.get("sucesso"), "Resolver deve ser bem-sucedido"
            assert resultado.get("tipo_usuario") == "dono", \
                f"Dono explícito deve ter tipo_usuario='dono', obteve '{resultado.get('tipo_usuario')}'"
            assert resultado.get("requer_onboarding") == True, \
                "Dono deve requerer onboarding"
            assert resultado.get("proxima_acao") == "onboarding", \
                f"proxima_acao deveria ser 'onboarding', obteve '{resultado.get('proxima_acao')}'"

            await self.registrar_resultado(
                3,
                "Novo dono explícito (user_id==tenant_id) funciona",
                True,
                "Onboarding de dono inicia corretamente"
            )

        except AssertionError as e:
            await self.registrar_resultado(3, "Novo dono explícito", False, str(e))
        finally:
            if self.limpar:
                await self.cleanup_tenant(tenant_id)

    async def teste_04_dono_existente_sem_onboarding(self):
        """Teste 4: Dono existente sem onboarding continua funcionando"""
        tenant_id = "test_bloqueio_dono_existente"
        await self.setup_tenant_novo(tenant_id)

        try:
            # Primeiro acesso: criar dono
            dono_id = tenant_id
            resultado1 = await resolver_ator_e_validar_guard(
                user_id=dono_id,
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador=dono_id
            )

            assert resultado1.get("tipo_usuario") == "dono", "Primeiro acesso cria dono"

            # Segundo acesso: dono já existe
            resultado2 = await resolver_ator_e_validar_guard(
                user_id=dono_id,
                tenant_id=tenant_id,
                canal="whatsapp",
                identificador=dono_id
            )

            # Validações
            assert resultado2.get("sucesso"), "Segundo acesso deve ser bem-sucedido"
            assert resultado2.get("tipo_usuario") == "dono", \
                "Dono existente continua como dono"
            assert resultado2.get("requer_onboarding") == True, \
                "Onboarding não completo retorna True"

            await self.registrar_resultado(
                4,
                "Dono existente sem onboarding",
                True,
                "Fluxo de retomada de onboarding funciona"
            )

        except AssertionError as e:
            await self.registrar_resultado(4, "Dono existente", False, str(e))
        finally:
            if self.limpar:
                await self.cleanup_tenant(tenant_id)

    async def teste_05_regressao_cliente_real(self):
        """Teste 5: Cliente real não vira dono em outro tenant"""
        tenant1 = "test_bloqueio_multi_tenant_1"
        tenant2 = "test_bloqueio_multi_tenant_2"

        await self.setup_tenant_novo(tenant1)
        await self.setup_tenant_novo(tenant2)

        try:
            cliente_id = normalizar_actor_id("whatsapp", "5511966666666")

            # Tenant 1: Cliente é criado
            resultado1 = await resolver_ator_e_validar_guard(
                user_id=cliente_id,
                tenant_id=tenant1,
                canal="whatsapp",
                identificador="5511966666666"
            )

            assert resultado1.get("tipo_usuario") == "cliente", "Tenant 1: cliente criado"

            # Tenant 2: Mesmo actor não vira dono
            resultado2 = await resolver_ator_e_validar_guard(
                user_id=cliente_id,
                tenant_id=tenant2,
                canal="whatsapp",
                identificador="5511966666666"
            )

            assert resultado2.get("tipo_usuario") == "cliente", \
                f"Tenant 2: deve ser cliente (fallback), obteve '{resultado2.get('tipo_usuario')}'"
            assert resultado2.get("proxima_acao") != "onboarding", \
                "Tenant 2: não deve ter onboarding de dono"

            await self.registrar_resultado(
                5,
                "Multi-tenant: cliente não vira dono",
                True,
                "Isolamento por tenant funciona"
            )

        except AssertionError as e:
            await self.registrar_resultado(5, "Multi-tenant", False, str(e))
        finally:
            if self.limpar:
                await self.cleanup_tenant(tenant1)
                await self.cleanup_tenant(tenant2)

    async def executar_todos(self):
        """Executar todos os testes"""
        print("\n" + "="*80)
        print("TESTES P0: Bloqueio de Promoção Automática Cliente → Dono")
        print("="*80 + "\n")

        await self.teste_01_cliente_com_modo_uso()
        await self.teste_02_cliente_desconhecido_fallback_seguro()
        await self.teste_03_novo_dono_explicito_funciona()
        await self.teste_04_dono_existente_sem_onboarding()
        await self.teste_05_regressao_cliente_real()

        # Resumo
        total = len(self.resultados)
        passed = sum(1 for r in self.resultados if r["status"] == "PASS")
        failed = total - passed

        print("\n" + "="*80)
        print(f"RESULTADO: {passed}/{total} PASS")
        print("="*80 + "\n")

        if failed > 0:
            print("Testes falhados:")
            for r in self.resultados:
                if r["status"] == "FAIL":
                    print(f"  - {r['numero']}: {r['nome']}")
                    print(f"    Motivo: {r['motivo']}")
            return False

        return True


async def main():
    teste = TesteBloqueioPromocaoCliente()
    sucesso = await teste.executar_todos()
    return 0 if sucesso else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
