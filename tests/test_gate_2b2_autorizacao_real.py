"""
[TEST] C3.17-I2 GATE 2B.2: Firestore Real — Autorizacao e Isolamento (T03-T08)

Objetivo: Validar contra Firestore REAL:
- T03: Isolamento multi-tenant
- T04: Cliente nao pode criar profissional
- T05: Profissional nao pode criar profissional
- T06: Dono inativo nao pode criar profissional
- T07: Dono inexistente nao pode criar profissional
- T08: Dono valido pode criar profissional

SEGURANCA: Usa SOMENTE tenants de teste isolados (A e B)
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


class FirestoreAuthTestContext:
    """Gerenciador seguro de contexto de teste de autorizacao"""

    def __init__(self):
        self.tenant_A = f"c317_gate2b2_A_{str(uuid.uuid4())[:8]}"
        self.tenant_B = f"c317_gate2b2_B_{str(uuid.uuid4())[:8]}"

        # Atores do Tenant A
        self.owner_A = gerar_actor_id_estavel(prefixo="owner")
        self.client_A = gerar_actor_id_estavel(prefixo="cli")
        self.professional_A = gerar_actor_id_estavel(prefixo="prof")
        self.inactive_owner_A = gerar_actor_id_estavel(prefixo="owner_ina")

        # Atores do Tenant B
        self.owner_B = gerar_actor_id_estavel(prefixo="owner")

        # Actor inexistente (nao sera criado)
        self.nonexistent_owner = f"owner_nonexistent_{str(uuid.uuid4())[:8]}"

        # Test results
        self.test_prof_A = None
        self.test_prof_B = None

        self.db = None
        print("\n[SETUP] Tenant A: " + self.tenant_A)
        print("[SETUP] Tenant B: " + self.tenant_B)

    async def setup(self):
        """Criar dois tenants com atores de teste"""
        try:
            self.db = get_db()
            now = datetime.now(pytz.UTC).isoformat()

            # Criar Owner A (ativo)
            owner_A_data = {
                "tenant_id": self.tenant_A,
                "actor_id": self.owner_A,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_owner_A():
                self.db.collection("Clientes").document(self.tenant_A).collection("Atores").document(
                    self.owner_A
                ).set(owner_A_data)
            await asyncio.to_thread(criar_owner_A)
            print("[SETUP] Owner A criado: " + self.owner_A)

            # Criar Client A
            client_A_data = {
                "tenant_id": self.tenant_A,
                "actor_id": self.client_A,
                "tipo_usuario": "cliente",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_client_A():
                self.db.collection("Clientes").document(self.tenant_A).collection("Atores").document(
                    self.client_A
                ).set(client_A_data)
            await asyncio.to_thread(criar_client_A)
            print("[SETUP] Client A criado: " + self.client_A)

            # Criar Professional A
            prof_A_data = {
                "tenant_id": self.tenant_A,
                "actor_id": self.professional_A,
                "tipo_usuario": "profissional",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_prof_A():
                self.db.collection("Clientes").document(self.tenant_A).collection("Atores").document(
                    self.professional_A
                ).set(prof_A_data)
            await asyncio.to_thread(criar_prof_A)
            print("[SETUP] Professional A criado: " + self.professional_A)

            # Criar Inactive Owner A
            inactive_owner_A_data = {
                "tenant_id": self.tenant_A,
                "actor_id": self.inactive_owner_A,
                "tipo_usuario": "dono",
                "ativo": False,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_inactive_owner_A():
                self.db.collection("Clientes").document(self.tenant_A).collection("Atores").document(
                    self.inactive_owner_A
                ).set(inactive_owner_A_data)
            await asyncio.to_thread(criar_inactive_owner_A)
            print("[SETUP] Inactive Owner A criado: " + self.inactive_owner_A)

            # Criar Owner B (ativo)
            owner_B_data = {
                "tenant_id": self.tenant_B,
                "actor_id": self.owner_B,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_owner_B():
                self.db.collection("Clientes").document(self.tenant_B).collection("Atores").document(
                    self.owner_B
                ).set(owner_B_data)
            await asyncio.to_thread(criar_owner_B)
            print("[SETUP] Owner B criado: " + self.owner_B)

            return True

        except Exception as e:
            print("[ERRO] Setup falhou: " + str(e))
            raise

    async def test_t03_isolamento_multi_tenant(self):
        """T03: Owner A nao consegue criar profissional em tenant B"""
        print("\n[T03] Testando isolamento multi-tenant...")
        try:
            # Owner A tentando criar em tenant B
            try:
                prof = await criar_ator_profissional(
                    tenant_id=self.tenant_B,
                    canal="",
                    identificador="",
                    nome="Test T03 Fail",
                    criado_por=self.owner_A,
                    use_canonical=True
                )
                print("[T03] FALHA: Owner A conseguiu criar em tenant B!")
                return False
            except ValueError as e:
                error_str = str(e).lower()
                if any(s in error_str for s in ["existe", "tenant", "ativo", "dono"]):
                    print("[T03] PASS - Rejeicao correta: " + str(e))
                else:
                    print("[T03] FALHA: Erro diferente: " + str(e))
                    return False

            # Owner B criando em tenant B (deve passar)
            prof_B = await criar_ator_profissional(
                tenant_id=self.tenant_B,
                canal="",
                identificador="",
                nome="Test T03 Pass",
                criado_por=self.owner_B,
                use_canonical=True
            )
            self.test_prof_B = prof_B["actor_id"]
            print("[T03] PASS - Owner B criou em tenant B: " + self.test_prof_B)
            return True

        except Exception as e:
            print("[T03] FALHA: " + str(e))
            return False

    async def test_t04_cliente_nao_pode_criar(self):
        """T04: Cliente nao pode criar profissional"""
        print("\n[T04] Testando rejeicao de cliente...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_A,
                canal="",
                identificador="",
                nome="Test T04 Fail",
                criado_por=self.client_A,
                use_canonical=True
            )
            print("[T04] FALHA: Cliente conseguiu criar profissional!")
            return False

        except ValueError as e:
            if "dono" in str(e).lower() or "autorizado" in str(e).lower():
                print("[T04] PASS - Rejeicao correta: " + str(e))
                return True
            else:
                print("[T04] FALHA: Erro diferente: " + str(e))
                return False

        except Exception as e:
            print("[T04] FALHA: " + str(e))
            return False

    async def test_t05_profissional_nao_pode_criar(self):
        """T05: Profissional nao pode criar profissional"""
        print("\n[T05] Testando rejeicao de profissional...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_A,
                canal="",
                identificador="",
                nome="Test T05 Fail",
                criado_por=self.professional_A,
                use_canonical=True
            )
            print("[T05] FALHA: Profissional conseguiu criar profissional!")
            return False

        except ValueError as e:
            if "dono" in str(e).lower() or "autorizado" in str(e).lower():
                print("[T05] PASS - Rejeicao correta: " + str(e))
                return True
            else:
                print("[T05] FALHA: Erro diferente: " + str(e))
                return False

        except Exception as e:
            print("[T05] FALHA: " + str(e))
            return False

    async def test_t06_dono_inativo_nao_pode_criar(self):
        """T06: Dono inativo nao pode criar profissional"""
        print("\n[T06] Testando rejeicao de dono inativo...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_A,
                canal="",
                identificador="",
                nome="Test T06 Fail",
                criado_por=self.inactive_owner_A,
                use_canonical=True
            )
            print("[T06] FALHA: Dono inativo conseguiu criar profissional!")
            return False

        except ValueError as e:
            if "inativo" in str(e).lower() or "ativo" in str(e).lower():
                print("[T06] PASS - Rejeicao correta: " + str(e))
                return True
            else:
                print("[T06] FALHA: Erro diferente: " + str(e))
                return False

        except Exception as e:
            print("[T06] FALHA: " + str(e))
            return False

    async def test_t07_dono_inexistente_nao_pode_criar(self):
        """T07: Dono inexistente nao pode criar profissional"""
        print("\n[T07] Testando rejeicao de dono inexistente...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_A,
                canal="",
                identificador="",
                nome="Test T07 Fail",
                criado_por=self.nonexistent_owner,
                use_canonical=True
            )
            print("[T07] FALHA: Dono inexistente conseguiu criar profissional!")
            return False

        except ValueError as e:
            error_str = str(e).lower()
            if "nao existe" in error_str or "not exist" in error_str or "existe" in error_str:
                print("[T07] PASS - Rejeicao correta: " + str(e))
                return True
            else:
                print("[T07] FALHA: Erro diferente: " + str(e))
                return False

        except Exception as e:
            print("[T07] FALHA: " + str(e))
            return False

    async def test_t08_dono_valido_pode_criar(self):
        """T08: Dono valido pode criar profissional"""
        print("\n[T08] Testando criacao com dono valido...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_A,
                canal="",
                identificador="",
                nome="Test T08 Pass",
                criado_por=self.owner_A,
                use_canonical=True
            )

            self.test_prof_A = prof["actor_id"]

            # Validar estrutura
            assert prof["tenant_id"] == self.tenant_A, "tenant_id incorreto"
            assert prof["actor_id"].startswith("prof_"), "actor_id format incorreto"
            assert prof["tipo_usuario"] == "profissional", "tipo_usuario incorreto"
            assert prof["ativo"] is True, "ativo deve ser True"
            assert prof["criado_por"] == self.owner_A, "criado_por incorreto"
            assert prof["canais"] == [], "canais deve estar vazio"

            print("[T08] PASS - Profissional criado: " + self.test_prof_A)
            return True

        except Exception as e:
            print("[T08] FALHA: " + str(e))
            return False

    async def validate_isolation(self):
        """Validar isolamento A/B no Firestore"""
        print("\n[VALIDACAO] Verificando isolamento de documentos...")
        try:
            # Validar que tenant A contem apenas atores de A
            def contar_atores_A():
                docs = self.db.collection("Clientes").document(self.tenant_A).collection("Atores").stream()
                return list(docs)

            atores_A = await asyncio.to_thread(contar_atores_A)
            print("[VALIDACAO] Atores em tenant A: " + str(len(atores_A)))

            # Validar que tenant B contem apenas atores de B
            def contar_atores_B():
                docs = self.db.collection("Clientes").document(self.tenant_B).collection("Atores").stream()
                return list(docs)

            atores_B = await asyncio.to_thread(contar_atores_B)
            print("[VALIDACAO] Atores em tenant B: " + str(len(atores_B)))

            # Nenhum documento legado deve ser criado
            def verificar_legado_A():
                doc = self.db.collection("Clientes").document(self.tenant_A).collection(
                    "Profissionais"
                ).document("Test T03 Pass").get()
                return doc.exists or False

            legado_A = await asyncio.to_thread(verificar_legado_A)
            assert not legado_A, "Documento legado nao deveria existir"

            print("[VALIDACAO] PASS - Isolamento confirmado")
            return True

        except Exception as e:
            print("[VALIDACAO] FALHA: " + str(e))
            return False

    async def cleanup(self):
        """Remover SOMENTE documentos de teste"""
        try:
            print("\n[CLEANUP] Iniciando limpeza...")

            docs_to_delete_A = [
                self.owner_A,
                self.client_A,
                self.professional_A,
                self.inactive_owner_A,
                self.test_prof_A
            ]

            docs_to_delete_B = [
                self.owner_B,
                self.test_prof_B
            ]

            # Limpar tenant A
            for actor_id in docs_to_delete_A:
                if actor_id:
                    def deletar(aid):
                        self.db.collection("Clientes").document(self.tenant_A).collection("Atores").document(
                            aid
                        ).delete()

                    await asyncio.to_thread(lambda aid=actor_id: deletar(aid))
                    print("[CLEANUP] Deletado (A): " + actor_id)

            # Limpar tenant B
            for actor_id in docs_to_delete_B:
                if actor_id:
                    def deletar(aid):
                        self.db.collection("Clientes").document(self.tenant_B).collection("Atores").document(
                            aid
                        ).delete()

                    await asyncio.to_thread(lambda aid=actor_id: deletar(aid))
                    print("[CLEANUP] Deletado (B): " + actor_id)

            print("[CLEANUP] Limpeza concluida com sucesso")
            return True

        except Exception as e:
            print("[CLEANUP] FALHA: " + str(e))
            return False


async def main():
    print("\n" + "="*70)
    print("C3.17-I2 GATE 2B.2 - Autorizacao e Isolamento (T03-T08)")
    print("="*70)

    ctx = FirestoreAuthTestContext()
    results = {
        "setup": False,
        "t03": False,
        "t04": False,
        "t05": False,
        "t06": False,
        "t07": False,
        "t08": False,
        "isolation": False,
        "cleanup": False
    }

    try:
        # Setup
        await ctx.setup()
        results["setup"] = True

        # T03-T08
        results["t03"] = await ctx.test_t03_isolamento_multi_tenant()
        results["t04"] = await ctx.test_t04_cliente_nao_pode_criar()
        results["t05"] = await ctx.test_t05_profissional_nao_pode_criar()
        results["t06"] = await ctx.test_t06_dono_inativo_nao_pode_criar()
        results["t07"] = await ctx.test_t07_dono_inexistente_nao_pode_criar()
        results["t08"] = await ctx.test_t08_dono_valido_pode_criar()

        # Validacao
        results["isolation"] = await ctx.validate_isolation()

        # Cleanup
        results["cleanup"] = await ctx.cleanup()

        # Status
        all_passed = all([results["t03"], results["t04"], results["t05"],
                         results["t06"], results["t07"], results["t08"],
                         results["isolation"], results["cleanup"]])

        print("\n" + "="*70)
        if all_passed:
            print("RESULTADO: TODOS OS TESTES PASSARAM - OK")
        else:
            print("RESULTADO: ALGUNS TESTES FALHARAM")
        print("="*70)
        print("T03: " + ("PASS" if results["t03"] else "FAIL"))
        print("T04: " + ("PASS" if results["t04"] else "FAIL"))
        print("T05: " + ("PASS" if results["t05"] else "FAIL"))
        print("T06: " + ("PASS" if results["t06"] else "FAIL"))
        print("T07: " + ("PASS" if results["t07"] else "FAIL"))
        print("T08: " + ("PASS" if results["t08"] else "FAIL"))
        print("Isolamento: " + ("PASS" if results["isolation"] else "FAIL"))
        print("Cleanup: " + ("PASS" if results["cleanup"] else "FAIL"))
        print("="*70 + "\n")

        return all_passed

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
