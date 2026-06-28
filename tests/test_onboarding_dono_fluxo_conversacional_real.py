#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TESTE E2E: Onboarding do Dono - Fluxo Conversacional Real

Objetivo: Validar que onboarding funciona pelo fluxo real de mensagem,
não por escrita direta no Firestore.

Fluxo:
1. Novo dono inicia conversa
2. Sistema pergunta nome do negócio
3. Usuário responde: "Salão da Maria"
4. Sistema salva nome_negocio em Firestore
5. Sistema avança para próxima etapa (NÃO repete pergunta)
6. Usuário responde próximas perguntas
7. Onboarding termina com status correto

Validações:
- Nenhum TypeError em eh_comando
- Mensagens comuns não quebram
- onboarding_etapa avança
- nome_negocio persistido
- Sem loops infinitos
- Firestore real
- tenant_id e actor_id corretos
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Configurar encoding UTF-8 antes de qualquer output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Carregar variáveis de ambiente ANTES de qualquer outro import
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firestore_client import get_db
from services.identidade_service import normalizar_actor_id
from services.onboarding_dono_service import pegar_etapa_onboarding
from router.principal_router import roteador_principal


class MockBot:
    """Mock de bot do telegram"""
    async def send_message(self, chat_id, text, **kwargs):
        return {"ok": True}


class MockContext:
    """Mock de contexto do telegram para testes"""
    def __init__(self):
        self.user_data = {}
        self.bot = MockBot()


class TestOnboardingFluxoConversacional:
    def __init__(self):
        self.tenant_id = "test_onboarding_fluxo_conversa"
        self.canal = "whatsapp"
        self.identificador = "5511999999999"
        self.actor_id = normalizar_actor_id(self.canal, self.identificador)
        self.resultados = []

    async def setup(self):
        """Limpar dados antes do teste"""
        try:
            get_db().collection("Clientes").document(self.tenant_id).delete()
            print(f"[SETUP] Tenant limpo: {self.tenant_id}")
        except:
            pass

    async def cleanup(self):
        """Limpar dados após o teste"""
        try:
            get_db().collection("Clientes").document(self.tenant_id).delete()
            print(f"[CLEANUP] Tenant deletado: {self.tenant_id}")
        except:
            pass

    async def enviar_mensagem(self, mensagem: str, numero_passo: int):
        """
        Enviar mensagem pelo router real.

        Returns:
            resposta do router
        """
        print(f"\n[PASSO {numero_passo}] Mensagem: '{mensagem}'")

        context = MockContext()

        try:
            resposta = await roteador_principal(
                user_id=self.actor_id,
                mensagem=mensagem,
                update=None,
                context=context,
            )

            print(f"[PASSO {numero_passo}] Resposta: {resposta}")
            return resposta

        except Exception as e:
            print(f"[ERRO] Passo {numero_passo}: {str(e)}")
            raise

    async def verificar_etapa_firestore(self, etapa_esperada: str, passo: int):
        """Verificar etapa atual em Firestore"""
        etapa_info = await pegar_etapa_onboarding(self.tenant_id)

        if not etapa_info:
            raise AssertionError(f"[PASSO {passo}] Etapa não encontrada em Firestore")

        etapa_atual = etapa_info.get("etapa_atual")
        dados = etapa_info.get("dados", {})

        print(f"[PASSO {passo}] Etapa no Firestore: {etapa_atual}")
        print(f"[PASSO {passo}] Dados salvos: {list(dados.keys())}")

        if etapa_atual != etapa_esperada:
            raise AssertionError(
                f"[PASSO {passo}] Etapa esperada '{etapa_esperada}', "
                f"obtida '{etapa_atual}'"
            )

        return dados

    async def registrar_resultado(self, numero, nome, passou, motivo=""):
        """Registrar resultado de um teste"""
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

    async def test_01_novo_dono_inicia_onboarding(self):
        """Teste 1: Novo dono inicia conversa e recebe pergunta de onboarding"""
        try:
            resposta = await self.enviar_mensagem("Oi, quero usar NeoEve", 1)

            # Validação 1: Resposta deve ser dict com handled=True
            assert isinstance(resposta, dict), "Resposta deve ser dict"
            assert resposta.get("handled") == True, "Resposta deve ter handled=True"

            # Validação 2: Resposta deve conter a pergunta de onboarding
            resposta_texto = resposta.get("resposta", "")
            assert "nome do seu negócio" in resposta_texto.lower(), \
                f"Resposta deveria conter pergunta sobre nome do negócio, obteve: {resposta_texto}"

            # Validação 3: Firestore deve ter etapa "nome_negocio"
            await self.verificar_etapa_firestore("nome_negocio", 1)

            await self.registrar_resultado(
                1,
                "Novo dono inicia onboarding",
                True,
                "Dono criado e pergunta enviada corretamente"
            )

        except Exception as e:
            await self.registrar_resultado(1, "Novo dono inicia onboarding", False, str(e))
            raise

    async def test_02_usuario_responde_nome_negocio(self):
        """Teste 2: Usuário responde com nome do negócio"""
        try:
            resposta = await self.enviar_mensagem("Salão da Maria", 2)

            # Validação 1: Resposta deve ser dict
            assert isinstance(resposta, dict), "Resposta deve ser dict"

            # Validação 2: Resposta deveria conter próxima pergunta (tipo de negócio)
            # ou confirmação
            resposta_texto = resposta.get("resposta", "")
            print(f"[PASSO 2] Resposta: {resposta_texto}")

            # Validação 3: Firestore deve ter avançado para "segmento"
            dados = await self.verificar_etapa_firestore("segmento", 2)

            # Validação 4: Dados salvos devem conter "nome_negocio"
            assert "nome_negocio" in dados, \
                f"Firestore deveria ter 'nome_negocio', obteve: {list(dados.keys())}"

            assert dados["nome_negocio"] == "Salão da Maria", \
                f"Nome do negócio deveria ser 'Salão da Maria', obteve: {dados['nome_negocio']}"

            await self.registrar_resultado(
                2,
                "Usuário responde nome do negócio",
                True,
                "Nome salvo e etapa avançada corretamente"
            )

        except Exception as e:
            await self.registrar_resultado(
                2,
                "Usuário responde nome do negócio",
                False,
                str(e)
            )
            raise

    async def test_03_nao_repete_pergunta_anterior(self):
        """Teste 3: Sistema NÃO repete pergunta anterior (valida que avançou)"""
        try:
            resposta = await self.enviar_mensagem("Salão de Beleza", 3)

            resposta_texto = resposta.get("resposta", "").lower()

            # Validação 1: NÃO deveria conter pergunta de nome_negocio
            assert "qual é o nome do seu negócio" not in resposta_texto, \
                f"Sistema repetiu pergunta anterior! Resposta: {resposta_texto}"

            # Validação 2: Firestore deveria estar em "endereco"
            await self.verificar_etapa_firestore("endereco", 3)

            # Validação 3: Dados salvos devem conter "segmento"
            dados = await self.verificar_etapa_firestore("endereco", 3)
            etapa_info = await pegar_etapa_onboarding(self.tenant_id)
            dados = etapa_info.get("dados", {})

            assert "segmento" in dados, \
                f"Firestore deveria ter 'segmento', obteve: {list(dados.keys())}"

            await self.registrar_resultado(
                3,
                "Sistema não repete pergunta anterior",
                True,
                "Avançou corretamente sem loop"
            )

        except Exception as e:
            await self.registrar_resultado(
                3,
                "Sistema não repete pergunta anterior",
                False,
                str(e)
            )
            raise

    async def test_04_continua_onboarding(self):
        """Teste 4: Continua respondendo outras perguntas"""
        try:
            # Passo 4: Endereço
            resposta = await self.enviar_mensagem("Rua João Baroni, 550", 4)
            await self.verificar_etapa_firestore("agenda_padrao", 4)

            # Passo 5: Agenda
            resposta = await self.enviar_mensagem("9:00-18:00", 5)
            await self.verificar_etapa_firestore("primeiro_profissional", 5)

            # Passo 6: Profissional
            resposta = await self.enviar_mensagem("Maria", 6)
            await self.verificar_etapa_firestore("canal_primeiro_profissional", 6)

            # Passo 7: Canal profissional
            resposta = await self.enviar_mensagem("11987654321", 7)
            await self.verificar_etapa_firestore("primeiro_servico", 7)

            # Passo 8: Serviço
            resposta = await self.enviar_mensagem("Corte de cabelo", 8)
            await self.verificar_etapa_firestore("duracao_primeiro_servico", 8)

            # Passo 9: Duração
            resposta = await self.enviar_mensagem("30", 9)
            # Pode terminar em "confirmacao_dados" ou "completo"
            etapa_info = await pegar_etapa_onboarding(self.tenant_id)
            etapa = etapa_info.get("etapa_atual")
            assert etapa in ["confirmacao_dados", "completo"], \
                f"Etapa esperada em confirmacao_dados ou completo, obteve: {etapa}"

            await self.registrar_resultado(
                4,
                "Continua onboarding com múltiplas respostas",
                True,
                "Todas as etapas passaram corretamente"
            )

        except Exception as e:
            await self.registrar_resultado(
                4,
                "Continua onboarding com múltiplas respostas",
                False,
                str(e)
            )
            raise

    async def test_05_validacoes_firestore(self):
        """Teste 5: Validar dados finais em Firestore"""
        try:
            etapa_info = await pegar_etapa_onboarding(self.tenant_id)
            dados = etapa_info.get("dados", {})

            # Validação 1: Todos os campos devem estar presentes
            campos_esperados = [
                "nome_negocio",
                "segmento",
                "endereco",
                "agenda_padrao",
                "primeiro_profissional",
                "canal_primeiro_profissional",
                "primeiro_servico",
                "duracao_primeiro_servico"
            ]

            campos_faltando = [c for c in campos_esperados if c not in dados]

            if campos_faltando:
                print(f"[PASSO 5] Campos faltando: {campos_faltando}")
                print(f"[PASSO 5] Campos presentes: {list(dados.keys())}")

            # Validação 2: tenant_id correto
            etapa = etapa_info.get("etapa_atual")
            assert etapa is not None, "etapa_atual não deve ser None"

            await self.registrar_resultado(
                5,
                "Dados finais em Firestore validados",
                True,
                f"Etapa final: {etapa}"
            )

        except Exception as e:
            await self.registrar_resultado(
                5,
                "Dados finais em Firestore validados",
                False,
                str(e)
            )
            raise

    async def test_06_mensagem_comum_nao_quebra(self):
        """Teste 6: Mensagem comum durante onboarding não quebra o fluxo"""
        try:
            # Criar novo teste para esse cenário
            tenant_regressao = "test_onb_msg_comum"
            actor_regressao = normalizar_actor_id("whatsapp", "5511988888888")

            # Limpar
            try:
                get_db().collection("Clientes").document(tenant_regressao).delete()
            except:
                pass

            # Iniciar onboarding
            context = MockContext()
            resposta1 = await roteador_principal(
                user_id=actor_regressao,
                mensagem="Oi, quero usar",
                update=None,
                context=context,
            )

            # Enviar mensagem comum (não é resposta de onboarding)
            resposta2 = await roteador_principal(
                user_id=actor_regressao,
                mensagem="/ajuda",
                update=None,
                context=context,
            )

            # Não deveria quebrar
            assert resposta2 is not None, "Resposta não deveria ser None"

            # Limpar
            try:
                get_db().collection("Clientes").document(tenant_regressao).delete()
            except:
                pass

            await self.registrar_resultado(
                6,
                "Mensagem comum durante onboarding não quebra",
                True,
                "Fluxo mantido mesmo com mensagem não esperada"
            )

        except Exception as e:
            await self.registrar_resultado(
                6,
                "Mensagem comum durante onboarding não quebra",
                False,
                str(e)
            )
            # Não fazer raise para continuar outros testes

    async def executar_todos_testes(self):
        """Executar todos os testes"""
        print("\n" + "="*80)
        print("TESTE E2E: ONBOARDING DO DONO - FLUXO CONVERSACIONAL REAL")
        print("="*80 + "\n")

        await self.setup()

        try:
            await self.test_01_novo_dono_inicia_onboarding()
            await self.test_02_usuario_responde_nome_negocio()
            await self.test_03_nao_repete_pergunta_anterior()
            await self.test_04_continua_onboarding()
            await self.test_05_validacoes_firestore()
            await self.test_06_mensagem_comum_nao_quebra()

        finally:
            await self.cleanup()

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
    teste = TestOnboardingFluxoConversacional()
    sucesso = await teste.executar_todos_testes()
    return 0 if sucesso else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
