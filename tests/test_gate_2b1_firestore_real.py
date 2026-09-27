"""
[TEST] C3.17-I2 GATE 2B.1: Firestore Real — Setup + T01/T02

Objetivo: Validar contra Firestore REAL:
- T01: Criação canônica
- T02: Profissional sem canal

SEGURANÇA: Usa SOMENTE tenant de teste isolado
"""

import sys
import os
import asyncio
import uuid
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.identidade_service import criar_ator_profissional, gerar_actor_id_estavel
from services.firestore_client import get_db


class FirestoreTestContext:
    """Gerenciador seguro de contexto de teste"""

    def __init__(self):
        self.test_tenant = f"c317_gate2b1_test_{str(uuid.uuid4())[:8]}"
        self.owner_actor_id = None
        self.prof1_actor_id = None
        self.prof2_actor_id = None
        self.db = None
        print("\n[SETUP] Tenant de teste: " + self.test_tenant)

    async def setup(self):
        """Criar tenant e owner de teste"""
        try:
            self.db = get_db()

            # Criar owner de teste
            self.owner_actor_id = gerar_actor_id_estavel(prefixo="owner")
            now = datetime.now(pytz.UTC).isoformat()

            owner_data = {
                "tenant_id": self.test_tenant,
                "actor_id": self.owner_actor_id,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }

            # Escrever owner
            def criar_owner():
                self.db.collection("Clientes").document(self.test_tenant).collection("Atores").document(
                    self.owner_actor_id
                ).set(owner_data)
                return True

            await asyncio.to_thread(criar_owner)
            print("[SETUP] Owner de teste criado: " + self.owner_actor_id)
            return True

        except Exception as e:
            print("[ERRO] Setup falhou: " + str(e))
            raise

    async def test_t01_criacao_canonica(self):
        """T01: Criar profissional com modelo canonico"""
        try:
            print("\n[T01] Iniciando criacao canonica...")

            prof = await criar_ator_profissional(
                tenant_id=self.test_tenant,
                canal="",
                identificador="",
                nome="Profissional Gate 2B1",
                criado_por=self.owner_actor_id
            )

            self.prof1_actor_id = prof["actor_id"]

            # Validacoes
            assert prof["tenant_id"] == self.test_tenant, "tenant_id incorreto: " + prof['tenant_id']
            assert prof["actor_id"].startswith("prof_"), "actor_id nao comeca com 'prof_': " + prof['actor_id']
            assert prof["tipo_usuario"] == "profissional", "tipo_usuario incorreto: " + prof['tipo_usuario']
            assert prof["nome"] == "Profissional Gate 2B1", "nome incorreto: " + prof['nome']
            assert prof["ativo"] is True, "ativo incorreto: " + str(prof['ativo'])
            assert prof["criado_por"] == self.owner_actor_id, "criado_por incorreto: " + prof['criado_por']
            assert prof["canais"] == [], "canais deve ser vazio: " + str(prof['canais'])

            # Validacao: nao contem informacoes sensiveis
            assert "whatsapp" not in prof["actor_id"].lower(), "actor_id nao deve conter 'whatsapp'"
            assert not prof["actor_id"].replace("prof_", "").replace("_", "").isdigit(), \
                "actor_id nao deve parecer telefone"

            # Ler novamente do Firestore para confirmar persistencia
            def ler_prof():
                doc = self.db.collection("Clientes").document(self.test_tenant).collection("Atores").document(
                    self.prof1_actor_id
                ).get()
                return doc.to_dict() if doc.exists else None

            prof_lido = await asyncio.to_thread(ler_prof)
            assert prof_lido is not None, "Profissional nao encontrado em Firestore"
            assert prof_lido["tipo_usuario"] == "profissional", "Persistencia falhou: tipo_usuario"

            print("[T01] PASS - actor_id: " + self.prof1_actor_id)
            return True

        except Exception as e:
            print("[T01] FALHA: " + str(e))
            raise

    async def test_t02_profissional_sem_canal(self):
        """T02: Criar profissional sem canal"""
        try:
            print("\n[T02] Iniciando criacao sem canal...")

            prof = await criar_ator_profissional(
                tenant_id=self.test_tenant,
                canal="",
                identificador="",
                nome="Profissional Sem Canal",
                criado_por=self.owner_actor_id
            )

            self.prof2_actor_id = prof["actor_id"]

            # Validacoes
            assert prof["canais"] == [], "canais deve estar vazio: " + str(prof['canais'])
            assert prof["tipo_usuario"] == "profissional", "tipo_usuario incorreto"
            assert prof["nome"] == "Profissional Sem Canal", "nome incorreto"
            assert prof["actor_id"].startswith("prof_"), "actor_id format incorreto"

            # Nao deve ter dependencia de canal
            assert "email" not in prof["actor_id"].lower(), "actor_id nao deve conter 'email'"
            assert ":" not in prof["actor_id"], "actor_id nao deve conter ':' (padrao legado)"

            # Ler novamente do Firestore
            def ler_prof():
                doc = self.db.collection("Clientes").document(self.test_tenant).collection("Atores").document(
                    self.prof2_actor_id
                ).get()
                return doc.to_dict() if doc.exists else None

            prof_lido = await asyncio.to_thread(ler_prof)
            assert prof_lido is not None, "Profissional nao encontrado em Firestore"
            assert prof_lido["canais"] == [], "Persistencia falhou: canais"

            print("[T02] PASS - actor_id: " + self.prof2_actor_id)
            return True

        except Exception as e:
            print("[T02] FALHA: " + str(e))
            raise

    async def validate_no_legacy(self):
        """Validar que Profissionais/{nome} nao foi criado"""
        try:
            print("\n[VALIDACAO] Verificando que legado nao foi alterado...")

            def verificar_legado():
                # Tentar buscar Profissionais/{nome} para T01
                doc = self.db.collection("Clientes").document(self.test_tenant).collection(
                    "Profissionais"
                ).document("Profissional Gate 2B1").get()

                if doc.exists:
                    return "ENCONTRADO"  # Problema!
                return "NAO ENCONTRADO"  # Esperado

            resultado = await asyncio.to_thread(verificar_legado)
            assert resultado == "NAO ENCONTRADO", "Documento legado foi criado! " + resultado

            print("[VALIDACAO] Legado nao foi alterado")
            return True

        except Exception as e:
            print("[VALIDACAO] FALHA: " + str(e))
            raise

    async def cleanup(self):
        """Remover SOMENTE documentos de teste"""
        try:
            print("\n[CLEANUP] Iniciando limpeza...")

            docs_to_delete = [
                self.owner_actor_id,
                self.prof1_actor_id,
                self.prof2_actor_id
            ]

            for actor_id in docs_to_delete:
                if actor_id:
                    def deletar(aid):
                        self.db.collection("Clientes").document(self.test_tenant).collection("Atores").document(
                            aid
                        ).delete()

                    await asyncio.to_thread(lambda aid=actor_id: deletar(aid))
                    print("[CLEANUP] Deletado: " + actor_id)

            # Validar que foi deletado
            def verificar_deletado():
                doc = self.db.collection("Clientes").document(self.test_tenant).collection("Atores").document(
                    self.prof1_actor_id
                ).get()
                return doc.exists

            ainda_existe = await asyncio.to_thread(verificar_deletado)
            assert not ainda_existe, "Cleanup falhou: documento ainda existe"

            print("[CLEANUP] Limpeza concluida com sucesso")
            return True

        except Exception as e:
            print("[CLEANUP] FALHA: " + str(e))
            raise


async def main():
    print("\n" + "="*70)
    print("C3.17-I2 GATE 2B.1 — FIRESTORE REAL — SETUP + T01/T02")
    print("="*70)

    ctx = FirestoreTestContext()
    results = {
        "setup": False,
        "t01": False,
        "t02": False,
        "validation": False,
        "cleanup": False
    }

    try:
        # Setup
        await ctx.setup()
        results["setup"] = True

        # T01
        await ctx.test_t01_criacao_canonica()
        results["t01"] = True

        # T02
        await ctx.test_t02_profissional_sem_canal()
        results["t02"] = True

        # Validação
        await ctx.validate_no_legacy()
        results["validation"] = True

        # Cleanup
        await ctx.cleanup()
        results["cleanup"] = True

        print("\n" + "="*70)
        print("RESULTADO: TODOS OS TESTES PASSARAM - OK")
        print("="*70)
        print("Tenant de teste: " + ctx.test_tenant)
        print("Actor 1: " + ctx.prof1_actor_id)
        print("Actor 2: " + ctx.prof2_actor_id)
        print("Setup: " + ("OK" if results['setup'] else "FALHA"))
        print("T01: " + ("OK" if results['t01'] else "FALHA"))
        print("T02: " + ("OK" if results['t02'] else "FALHA"))
        print("Validacao Legado: " + ("OK" if results['validation'] else "FALHA"))
        print("Cleanup: " + ("OK" if results['cleanup'] else "FALHA"))
        print("="*70 + "\n")

        return all(results.values())

    except Exception as e:
        print("\n" + "="*70)
        print("RESULTADO: TESTE BLOQUEADO - FALHA")
        print("="*70)
        print("Erro: " + str(e))
        print("Status: " + str(results))
        print("="*70 + "\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
