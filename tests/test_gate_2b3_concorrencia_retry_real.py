"""
[TEST] C3.17-I2 GATE 2B.3: Firestore Real — Concorrencia e Retry (T09-T10)

Objetivo: Validar contra Firestore REAL:
- T09: Concorrencia / Race Condition
- T10: Retry / Idempotencia

SEGURANCA: Usa SOMENTE tenant de teste isolado
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


class FirestoreConcurrencyTestContext:
    """Gerenciador seguro de contexto de teste de concorrencia"""

    def __init__(self):
        self.tenant_id = f"c317_gate2b3_test_{str(uuid.uuid4())[:8]}"
        self.owner_id = gerar_actor_id_estavel(prefixo="owner")

        # Results
        self.t09_results = []
        self.t10_first = None
        self.t10_retry = None

        self.db = None
        print("\n[SETUP] Tenant: " + self.tenant_id)
        print("[SETUP] Owner: " + self.owner_id)

    async def setup(self):
        """Criar owner de teste"""
        try:
            self.db = get_db()
            now = datetime.now(pytz.UTC).isoformat()

            owner_data = {
                "tenant_id": self.tenant_id,
                "actor_id": self.owner_id,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_owner():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    self.owner_id
                ).set(owner_data)
            await asyncio.to_thread(criar_owner)
            print("[SETUP] Owner criado: " + self.owner_id)
            return True

        except Exception as e:
            print("[ERRO] Setup falhou: " + str(e))
            raise

    async def test_t09_concorrencia(self):
        """T09: Duas chamadas concorrentes com mesma operacao logica"""
        print("\n[T09] Testando concorrencia / race condition...")

        async def criar_profissional_concorrente(index):
            try:
                prof = await criar_ator_profissional(
                    tenant_id=self.tenant_id,
                    canal="",
                    identificador="",
                    nome="Profissional Concorrente",
                    criado_por=self.owner_id,
                    use_canonical=True
                )
                return {
                    "index": index,
                    "sucesso": True,
                    "actor_id": prof["actor_id"],
                    "erro": None
                }
            except Exception as e:
                return {
                    "index": index,
                    "sucesso": False,
                    "actor_id": None,
                    "erro": str(e)
                }

        try:
            # Executar duas chamadas concorrentes reais
            print("[T09] Executando duas criações concorrentes...")
            results = await asyncio.gather(
                criar_profissional_concorrente(1),
                criar_profissional_concorrente(2)
            )

            self.t09_results = results

            sucesso_count = sum(1 for r in results if r["sucesso"])
            actor_ids = [r["actor_id"] for r in results if r["actor_id"]]
            distinct_actor_ids = len(set(actor_ids))

            print("[T09] Chamadas concorrentes: 2")
            print("[T09] Criações aceitas: " + str(sucesso_count))
            print("[T09] Actor IDs distintos: " + str(distinct_actor_ids))

            # Consultar Firestore para contar documentos reais
            def contar_profissionais():
                docs = self.db.collection("Clientes").document(self.tenant_id).collection("Atores").stream()
                prof_docs = [d for d in docs if d.to_dict().get("nome") == "Profissional Concorrente"]
                return len(prof_docs), [d.to_dict()["actor_id"] for d in prof_docs]

            count, doc_actor_ids = await asyncio.to_thread(contar_profissionais)
            print("[T09] Documentos em Firestore: " + str(count))

            # Avaliar resultado
            if sucesso_count == 2 and distinct_actor_ids == 2 and count == 2:
                print("[T09] RESULTADO: Duas operacoes concorrentes criaram dois documentos")
                print("[T09] FALHA: Sem proteção de atomicidade/idempotencia")
                return False
            elif sucesso_count == 1 and count == 1:
                print("[T09] RESULTADO: Uma operacao foi aceita, outra rejeitada")
                print("[T09] PASS: Comportamento atômico determinístico")
                return True
            else:
                print("[T09] RESULTADO INCONCLUSIVO")
                print("[T09] BLOCKED: Comportamento não é determinístico")
                return None

        except Exception as e:
            print("[T09] FALHA: " + str(e))
            return False

    async def test_t10_retry(self):
        """T10: Retry da mesma operacao após sucesso"""
        print("\n[T10] Testando retry / idempotencia...")

        try:
            # Primeira execução
            print("[T10] Primeira execução...")
            prof1 = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Profissional Retry",
                criado_por=self.owner_id,
                use_canonical=True
            )
            self.t10_first = {
                "actor_id": prof1["actor_id"],
                "sucesso": True,
                "erro": None
            }
            print("[T10] Primeira execução: " + prof1["actor_id"])

            # Retry idêntico
            print("[T10] Executando retry idêntico...")
            try:
                prof2 = await criar_ator_profissional(
                    tenant_id=self.tenant_id,
                    canal="",
                    identificador="",
                    nome="Profissional Retry",
                    criado_por=self.owner_id,
                    use_canonical=True
                )
                self.t10_retry = {
                    "actor_id": prof2["actor_id"],
                    "sucesso": True,
                    "erro": None
                }
                print("[T10] Retry: " + prof2["actor_id"])
            except ValueError as e:
                self.t10_retry = {
                    "actor_id": None,
                    "sucesso": False,
                    "erro": str(e)
                }
                print("[T10] Retry rejeitado: " + str(e))

            # Analisar resultado
            if self.t10_first["actor_id"] == self.t10_retry["actor_id"]:
                print("[T10] RESULTADO: Retry retornou mesmo actor_id")
                print("[T10] PASS: Comportamento idempotente (retorna existente)")
                return True
            elif self.t10_retry["sucesso"] == False and "existe" in self.t10_retry["erro"].lower():
                print("[T10] RESULTADO: Retry rejeitado porque ja existe")
                print("[T10] PASS: Comportamento seguro/determinístico")
                return True
            elif self.t10_first["actor_id"] != self.t10_retry["actor_id"] and self.t10_retry["sucesso"]:
                print("[T10] RESULTADO: Retry criou novo actor_id diferente")
                print("[T10] FAIL: Operacao nao é idempotente")
                return False
            else:
                print("[T10] RESULTADO INCONCLUSIVO")
                print("[T10] BLOCKED: Comportamento indeterminado")
                return None

        except Exception as e:
            print("[T10] FALHA: " + str(e))
            return False

    async def validate_firestore_state(self):
        """Validar estado final no Firestore"""
        print("\n[VALIDACAO] Inspecionando estado do Firestore...")
        try:
            def listar_atores():
                docs = list(self.db.collection("Clientes").document(self.tenant_id).collection("Atores").stream())
                return [(d.id, d.to_dict()) for d in docs]

            atores = await asyncio.to_thread(listar_atores)
            print("[VALIDACAO] Total de atores: " + str(len(atores)))

            # Separar por nome
            concorrentes = [d for d in atores if d[1].get("nome") == "Profissional Concorrente"]
            retry_docs = [d for d in atores if d[1].get("nome") == "Profissional Retry"]

            print("[VALIDACAO] Profissionais Concorrente: " + str(len(concorrentes)))
            for actor_id, data in concorrentes:
                print("  - " + actor_id)

            print("[VALIDACAO] Profissionais Retry: " + str(len(retry_docs)))
            for actor_id, data in retry_docs:
                print("  - " + actor_id)

            return {
                "total": len(atores),
                "concorrentes": concorrentes,
                "retry": retry_docs
            }

        except Exception as e:
            print("[VALIDACAO] FALHA: " + str(e))
            return None

    async def cleanup(self):
        """Remover SOMENTE documentos de teste"""
        try:
            print("\n[CLEANUP] Iniciando limpeza...")

            # Deletar owner
            def deletar_owner():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    self.owner_id
                ).delete()

            await asyncio.to_thread(deletar_owner)
            print("[CLEANUP] Deletado: " + self.owner_id)

            # Deletar profissionais de teste (T09 + T10)
            if self.t09_results:
                for result in self.t09_results:
                    if result.get("actor_id"):
                        def deletar_t09(aid):
                            self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                                aid
                            ).delete()

                        await asyncio.to_thread(lambda aid=result["actor_id"]: deletar_t09(aid))
                        print("[CLEANUP] Deletado (T09): " + result["actor_id"])

            if self.t10_first and self.t10_first.get("actor_id"):
                def deletar_t10_first():
                    self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                        self.t10_first["actor_id"]
                    ).delete()

                await asyncio.to_thread(deletar_t10_first)
                print("[CLEANUP] Deletado (T10-First): " + self.t10_first["actor_id"])

            if self.t10_retry and self.t10_retry.get("actor_id"):
                def deletar_t10_retry():
                    self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                        self.t10_retry["actor_id"]
                    ).delete()

                await asyncio.to_thread(deletar_t10_retry)
                print("[CLEANUP] Deletado (T10-Retry): " + self.t10_retry["actor_id"])

            # Validar cleanup
            def verificar_vazio():
                docs = list(self.db.collection("Clientes").document(self.tenant_id).collection("Atores").stream())
                return len(docs) == 0

            vazio = await asyncio.to_thread(verificar_vazio)
            if vazio:
                print("[CLEANUP] PASS - Tenant vazio apos cleanup")
                return True
            else:
                print("[CLEANUP] FALHA - Documentos residuais")
                return False

        except Exception as e:
            print("[CLEANUP] FALHA: " + str(e))
            return False


async def main():
    print("\n" + "="*70)
    print("C3.17-I2 GATE 2B.3 - Concorrencia e Retry (T09-T10)")
    print("="*70)

    ctx = FirestoreConcurrencyTestContext()
    results = {
        "setup": False,
        "t09": None,
        "t10": None,
        "validation": False,
        "cleanup": False
    }

    try:
        # Setup
        await ctx.setup()
        results["setup"] = True

        # T09 e T10
        results["t09"] = await ctx.test_t09_concorrencia()
        results["t10"] = await ctx.test_t10_retry()

        # Validacao
        validation_result = await ctx.validate_firestore_state()
        results["validation"] = validation_result is not None

        # Cleanup
        results["cleanup"] = await ctx.cleanup()

        # Status
        t09_status = "PASS" if results["t09"] == True else ("FAIL" if results["t09"] == False else "BLOCKED")
        t10_status = "PASS" if results["t10"] == True else ("FAIL" if results["t10"] == False else "BLOCKED")

        gate_approved = results["t09"] == True and results["t10"] == True and results["cleanup"] == True

        print("\n" + "="*70)
        if gate_approved:
            print("RESULTADO: GATE APROVADO")
        else:
            print("RESULTADO: GATE BLOQUEADO")
        print("="*70)
        print("T09 (Concorrencia): " + t09_status)
        print("T10 (Retry): " + t10_status)
        print("Validacao: " + ("PASS" if results["validation"] else "FAIL"))
        print("Cleanup: " + ("PASS" if results["cleanup"] else "FAIL"))
        print("="*70 + "\n")

        return gate_approved

    except Exception as e:
        print("\n" + "="*70)
        print("RESULTADO: TESTE BLOQUEADO - EXCECAO")
        print("="*70)
        print("Erro: " + str(e))
        print("="*70 + "\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
