#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTE P0: Sessão V2 não é sobrescrita por legado

Objetivo: Validar que contexto V2 carregado não é perdido
quando router faz leitura de MemoriaTemporaria legado.

Bug: router na linha 3360 faz segunda leitura que sobrescreve V2
"""

import asyncio
import sys
import os
from pathlib import Path

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
projeto_dir = r"C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"
load_dotenv(Path(projeto_dir) / ".env")
sys.path.insert(0, projeto_dir)
os.chdir(projeto_dir)

from services.firestore_client import get_db
from services.identidade_service import normalizar_actor_id
from router.principal_router import roteador_principal


class MockBot:
    async def send_message(self, chat_id, text, **kwargs):
        return {"ok": True}


class MockContext:
    def __init__(self):
        self.user_data = {}
        self.bot = MockBot()


class TesteSessaoV2NaoSobrescritaLegado:
    def __init__(self):
        self.resultados = []

    async def setup(self, tenant_id: str):
        """Limpar tenant antes do teste"""
        try:
            get_db().collection("Clientes").document(tenant_id).delete()
        except:
            pass

    async def cleanup(self, tenant_id: str):
        """Limpar depois do teste"""
        try:
            get_db().collection("Clientes").document(tenant_id).delete()
        except:
            pass

    async def registrar_resultado(self, numero: int, nome: str, passou: bool, motivo: str = ""):
        resultado = {
            "numero": numero,
            "nome": nome,
            "status": "PASS" if passou else "FAIL",
            "motivo": motivo
        }
        self.resultados.append(resultado)
        status_str = "[PASS]" if passou else "[FAIL]"
        print(f"\n{status_str} Teste {numero}: {nome}")
        if motivo:
            print(f"    Motivo: {motivo}")

    async def teste_01_sessao_v2_ativa_legado_inexistente(self):
        """Teste 1: V2 ativa + legado inexistente"""
        tenant_id = "test_sessao_v2_vs_legado_001"
        actor_id = normalizar_actor_id("whatsapp", "5511999999999")
        await self.setup(tenant_id)

        try:
            # Criar Sessão V2 com estado ativo
            get_db().collection("Clientes").document(tenant_id).collection("Sessoes").document(actor_id).set({
                "estado_fluxo": "aguardando_profissional",
                "draft_agendamento": {
                    "servico": "corte",
                    "data_hora": "2026-06-29T16:00:00"
                },
                "_tenant_id_guard": tenant_id
            })

            # NÃO criar legado (deixar vazio propositalmente)

            # Chamar router
            context = MockContext()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem="Não tenho preferência",
                update=None,
                context=context
            )

            # Validações
            assert isinstance(resposta, dict), "Resposta deve ser dict"

            # ❌ BUG ATUAL: resposta contém motivo="contexto_neutro"
            # ✅ ESPERADO: resposta processa como "aguardando_profissional"

            motivo = resposta.get("motivo", "")
            if motivo == "contexto_neutro":
                raise AssertionError("BUG: Sessão V2 foi sobrescrita por legado vazio! Motivo=contexto_neutro")

            await self.registrar_resultado(
                1,
                "Sessão V2 ativa + legado inexistente",
                True,
                "V2 preservada, motivo != contexto_neutro"
            )

        except AssertionError as e:
            await self.registrar_resultado(1, "Sessão V2 ativa", False, str(e))
        finally:
            await self.cleanup(tenant_id)

    async def teste_02_sessao_v2_vence_legado_vazio(self):
        """Teste 2: V2 ativa + legado vazio"""
        tenant_id = "test_sessao_v2_vs_legado_002"
        actor_id = normalizar_actor_id("whatsapp", "5511988888888")
        await self.setup(tenant_id)

        try:
            # V2 ativa
            get_db().collection("Clientes").document(tenant_id).collection("Sessoes").document(actor_id).set({
                "estado_fluxo": "aguardando_profissional",
                "draft_agendamento": {"servico": "escova"},
                "_tenant_id_guard": tenant_id
            })

            # Legado vazio (documento não existe)
            # Verificar que não há em Clientes/{actor_id}/MemoriaTemporaria/contexto

            context = MockContext()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem="Qualquer um",
                update=None,
                context=context
            )

            assert resposta.get("motivo") != "contexto_neutro", \
                "V2 deveria vencer legado vazio"

            await self.registrar_resultado(2, "V2 vence legado vazio", True, "")

        except AssertionError as e:
            await self.registrar_resultado(2, "V2 vence legado vazio", False, str(e))
        finally:
            await self.cleanup(tenant_id)

    async def teste_03_sessao_v2_vence_legado_conflitante(self):
        """Teste 3: V2 ativa + legado com estado conflitante"""
        tenant_id = "test_sessao_v2_vs_legado_003"
        actor_id = normalizar_actor_id("whatsapp", "5511977777777")
        await self.setup(tenant_id)

        try:
            # V2 ativa e CORRETA
            get_db().collection("Clientes").document(tenant_id).collection("Sessoes").document(actor_id).set({
                "estado_fluxo": "aguardando_profissional",
                "draft_agendamento": {"servico": "corte"},
                "_tenant_id_guard": tenant_id
            })

            # Legado com estado DIFERENTE (conflitante)
            # Simular versão antiga que tem estado_fluxo=None
            get_db().collection("Clientes").document(actor_id).collection("MemoriaTemporaria").document("contexto").set({
                "_tenant_id_guard": tenant_id,  # Guard válido
                "estado_fluxo": None,  # ❌ Estado antigo/inválido
                "draft_agendamento": {}
            })

            context = MockContext()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem="Teste",
                update=None,
                context=context
            )

            # V2 deveria vencer
            assert resposta.get("motivo") != "contexto_neutro", \
                "V2 deve vencer legado conflitante"

            await self.registrar_resultado(
                3,
                "V2 vence legado conflitante",
                True,
                "V2 estado correto prevaleceu"
            )

        except AssertionError as e:
            await self.registrar_resultado(3, "V2 vence legado", False, str(e))
        finally:
            await self.cleanup(tenant_id)

    async def teste_04_nao_tenho_preferencia_em_aguardando_profissional(self):
        """Teste 4: 'Não tenho preferência' em aguardando_profissional funciona"""
        tenant_id = "test_sessao_v2_vs_legado_004"
        actor_id = normalizar_actor_id("whatsapp", "5511966666666")
        await self.setup(tenant_id)

        try:
            # V2 em aguardando_profissional
            get_db().collection("Clientes").document(tenant_id).collection("Sessoes").document(actor_id).set({
                "estado_fluxo": "aguardando_profissional",
                "draft_agendamento": {
                    "servico": "corte",
                    "data": "2026-06-29"
                },
                "_tenant_id_guard": tenant_id
            })

            context = MockContext()
            resposta = await roteador_principal(
                user_id=actor_id,
                mensagem="Não tenho preferência",
                update=None,
                context=context
            )

            # Esperado: processar como indifferente, não como contexto_neutro
            assert resposta.get("motivo") != "contexto_neutro", \
                "Deve processar 'Não tenho preferência', não tratar como neutro"

            await self.registrar_resultado(
                4,
                "'Não tenho preferência' em aguardando_profissional",
                True,
                "Funciona sem cair em contexto_neutro"
            )

        except AssertionError as e:
            await self.registrar_resultado(
                4,
                "'Não tenho preferência'",
                False,
                str(e)
            )
        finally:
            await self.cleanup(tenant_id)

    async def executar_todos(self):
        print("\n" + "="*80)
        print("TESTES P0: Sessão V2 Não Sobrescrita por Legado")
        print("="*80 + "\n")

        await self.teste_01_sessao_v2_ativa_legado_inexistente()
        await self.teste_02_sessao_v2_vence_legado_vazio()
        await self.teste_03_sessao_v2_vence_legado_conflitante()
        await self.teste_04_nao_tenho_preferencia_em_aguardando_profissional()

        total = len(self.resultados)
        passed = sum(1 for r in self.resultados if r["status"] == "PASS")

        print("\n" + "="*80)
        print(f"RESULTADO: {passed}/{total} PASS")
        print("="*80 + "\n")

        return passed == total


async def main():
    teste = TesteSessaoV2NaoSobrescritaLegado()
    sucesso = await teste.executar_todos()
    return 0 if sucesso else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
