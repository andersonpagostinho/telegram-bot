"""
[TEST] C3.17-I2 GATE 2B.4-E: Idempotencia Multicanal com Transacao (T09-R1 a T10-R6)

Objetivo: Validar contra Firestore REAL:
- T09-R1: Retry mesma operation_id → mesmo actor_id
- T09-R2: Concorrencia mesma operation_id → um unico ator
- T09-R3: Mesmo nome, operation_ids diferentes → atores DIFERENTES (correto)
- T09-R4: Tenant isolation
- T10-R1: Parametros salvos em OperacoesProfissional
- T10-R2: Autorizacao (cliente rejeitado)
- T10-R3: Profissional sem canal
- T10-R4: Nenhum legado criado
- T10-R5: Telegram operation_id format
- T10-R6: WhatsApp operation_id format

SEGURANCA: Usa SOMENTE tenants de teste isolados

CONTRATO GATE 2B.4-E:
- actor_id = UUID v4 puro, independente de operation_id
- operation_id = identidade da operacao (deduplicacao de retry)
- Mesma operacao, tenants diferentes = atores diferentes
- Operacoes diferentes com mesmo nome = atores diferentes (SEM deduplicacao automatica)
- Transacao Firestore real implementada
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


class FirestoreIdempotenciaTestContext:
    """Gerenciador seguro de contexto de teste de idempotencia com transacao"""

    def __init__(self):
        self.tenant_id = f"c317_gate2b4e_{str(uuid.uuid4())[:8]}"
        self.owner_id = gerar_actor_id_estavel(prefixo="owner")
        self.db = None
        self.results = {}
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
            print("[SETUP] Owner criado")
            return True
        except Exception as e:
            print("[ERRO] Setup falhou: " + str(e))
            raise

    async def test_t09r1_retry_mesma_operation(self):
        """T09-R1: Retry com mesma operation_id"""
        print("\n[T09-R1] Testando retry mesma operation_id...")
        try:
            operation_id = f"telegram:123456:cadastrar_profissional"

            # Primeira execucao
            prof1 = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Profissional T09R1",
                criado_por=self.owner_id,
                operation_id=operation_id
            )
            actor_id_1 = prof1["actor_id"]
            print("[T09-R1] Primeira execucao: " + actor_id_1)

            # Retry com mesma operation_id
            prof2 = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Profissional T09R1",
                criado_por=self.owner_id,
                operation_id=operation_id
            )
            actor_id_2 = prof2["actor_id"]
            print("[T09-R1] Retry: " + actor_id_2)

            # Validar: retry deve retornar MESMO actor_id
            assert actor_id_1 == actor_id_2, "Retry deve retornar mesmo actor_id"

            # Validar que somente um documento foi criado
            def contar_operacoes():
                doc = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).document(operation_id).get()
                return doc.exists

            existe = await asyncio.to_thread(contar_operacoes)
            assert existe, "Documento de operacao deve existir"

            self.results["T09-R1"] = True
            print("[T09-R1] PASS")
            return True

        except Exception as e:
            print("[T09-R1] FALHA: " + str(e))
            self.results["T09-R1"] = False
            return False

    async def test_t09r2_concorrencia_mesma_operation(self):
        """T09-R2: Concorrencia com mesma operation_id - um unico ator criado"""
        print("\n[T09-R2] Testando concorrencia mesma operation_id...")
        try:
            operation_id = f"telegram:654321:cadastrar_profissional"

            # Duas chamadas concorrentes com MESMA operation_id
            results = await asyncio.gather(
                criar_ator_profissional(
                    tenant_id=self.tenant_id,
                    canal="",
                    identificador="",
                    nome="Profissional T09R2",
                    criado_por=self.owner_id,
                        operation_id=operation_id
                ),
                criar_ator_profissional(
                    tenant_id=self.tenant_id,
                    canal="",
                    identificador="",
                    nome="Profissional T09R2",
                    criado_por=self.owner_id,
                        operation_id=operation_id
                ),
                return_exceptions=True
            )

            actor_ids = [r["actor_id"] for r in results if isinstance(r, dict)]
            print("[T09-R2] Actor IDs retornados: " + str(len(actor_ids)))

            # Validar: ambos devem retornar mesmo actor_id
            assert len(actor_ids) == 2, "Ambas chamadas devem retornar resultado"
            assert actor_ids[0] == actor_ids[1], "Ambas devem retornar MESMO actor_id"

            # Validar que apenas UM documento Atores foi criado
            def contar_atores():
                docs = list(self.db.collection("Clientes").document(self.tenant_id).collection("Atores").stream())
                prof_docs = [d for d in docs if d.to_dict().get("nome") == "Profissional T09R2"]
                return len(prof_docs)

            count_atores = await asyncio.to_thread(contar_atores)
            assert count_atores == 1, f"Deve haver exatamente UM ator, encontrados {count_atores}"

            self.results["T09-R2"] = True
            print("[T09-R2] PASS - transacao criou exatamente um ator")
            return True

        except Exception as e:
            print("[T09-R2] FALHA: " + str(e))
            self.results["T09-R2"] = False
            return False

    async def test_t09r3_mesmo_nome_ops_diferentes(self):
        """T09-R3: Mesmo nome com operation_ids diferentes - atores DIFERENTES (correto)"""
        print("\n[T09-R3] Testando mesmo nome com operation_ids diferentes...")
        try:
            # Operacao 1 - Maria via Telegram
            prof1 = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Maria Silva",
                criado_por=self.owner_id,
                operation_id="telegram:111111:cadastrar"
            )
            actor_id_1 = prof1["actor_id"]

            # Operacao 2 - Maria via WhatsApp (operation_id diferente)
            prof2 = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Maria Silva",
                criado_por=self.owner_id,
                operation_id="whatsapp:222222:cadastrar"
            )
            actor_id_2 = prof2["actor_id"]

            # CORRETO: operation_ids diferentes devem gerar atores diferentes
            assert actor_id_1 != actor_id_2, "operation_ids diferentes devem gerar atores DIFERENTES"
            print("[T09-R3] PASS - operacoes diferentes criaram atores diferentes")

            # Validar ambos foram registrados
            def verificar_operacoes():
                op1 = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).document("telegram:111111:cadastrar").get().exists
                op2 = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).document("whatsapp:222222:cadastrar").get().exists
                return op1 and op2

            ambas_exist = await asyncio.to_thread(verificar_operacoes)
            assert ambas_exist, "Ambas operacoes devem estar registradas"

            self.results["T09-R3"] = True
            return True

        except Exception as e:
            print("[T09-R3] FALHA: " + str(e))
            self.results["T09-R3"] = False
            return False

    async def test_t09r4_tenant_isolation(self):
        """T09-R4: Isolamento de tenant"""
        print("\n[T09-R4] Testando isolamento de tenant...")
        try:
            # Criar segundo tenant
            tenant_2 = f"c317_gate2b4e_b_{str(uuid.uuid4())[:8]}"
            owner_2 = gerar_actor_id_estavel(prefixo="owner")
            now = datetime.now(pytz.UTC).isoformat()

            def criar_owner_2():
                self.db.collection("Clientes").document(tenant_2).collection("Atores").document(
                    owner_2
                ).set({
                    "tenant_id": tenant_2,
                    "actor_id": owner_2,
                    "tipo_usuario": "dono",
                    "ativo": True,
                    "criado_em": now,
                    "atualizado_em": now
                })

            await asyncio.to_thread(criar_owner_2)

            # Mesma operation_id textual, mas tenants DIFERENTES
            operation_id = "telegram:333333:cadastrar"

            prof1 = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Test T09R4",
                criado_por=self.owner_id,
                operation_id=operation_id
            )

            prof2 = await criar_ator_profissional(
                tenant_id=tenant_2,
                canal="",
                identificador="",
                nome="Test T09R4",
                criado_por=owner_2,
                operation_id=operation_id
            )

            assert prof1["actor_id"] != prof2["actor_id"], "Tenants isolados devem ter atores diferentes"
            assert prof1["tenant_id"] != prof2["tenant_id"], "Tenants devem ser diferentes"

            # Cleanup tenant_2
            def cleanup_tenant_2():
                self.db.collection("Clientes").document(tenant_2).collection("Atores").document(owner_2).delete()
                self.db.collection("Clientes").document(tenant_2).collection("OperacoesProfissional").document(
                    operation_id
                ).delete()
                self.db.collection("Clientes").document(tenant_2).collection("Atores").document(
                    prof2["actor_id"]
                ).delete()

            await asyncio.to_thread(cleanup_tenant_2)

            self.results["T09-R4"] = True
            print("[T09-R4] PASS")
            return True

        except Exception as e:
            print("[T09-R4] FALHA: " + str(e))
            self.results["T09-R4"] = False
            return False

    async def test_t10r1_parametros_salvos(self):
        """T10-R1: Parametros salvos em OperacoesProfissional"""
        print("\n[T10-R1] Testando parametros salvos...")
        try:
            operation_id = "telegram:444444:cadastrar"

            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Test Parametros",
                criado_por=self.owner_id,
                operation_id=operation_id
            )

            def verificar_operacao():
                doc = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).document(operation_id).get()
                return doc.to_dict() if doc.exists else None

            operacao = await asyncio.to_thread(verificar_operacao)
            assert operacao is not None, "Operacao deve estar registrada"
            assert operacao.get("parametros", {}).get("nome") == "Test Parametros", "Nome deve estar nos parametros"
            assert operacao.get("actor_id") == prof["actor_id"], "actor_id deve estar registrado"
            assert operacao.get("status") == "completed", "Status deve ser completed"

            self.results["T10-R1"] = True
            print("[T10-R1] PASS")
            return True

        except Exception as e:
            print("[T10-R1] FALHA: " + str(e))
            self.results["T10-R1"] = False
            return False

    async def test_t10r2_autorizacao(self):
        """T10-R2: Autorizacao - cliente rejeitado"""
        print("\n[T10-R2] Testando autorizacao...")
        try:
            # Criar cliente (nao autorizado)
            client_id = gerar_actor_id_estavel(prefixo="cli")
            now = datetime.now(pytz.UTC).isoformat()

            def criar_client():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    client_id
                ).set({
                    "tenant_id": self.tenant_id,
                    "actor_id": client_id,
                    "tipo_usuario": "cliente",
                    "ativo": True,
                    "criado_em": now,
                    "atualizado_em": now
                })

            await asyncio.to_thread(criar_client)

            # Tentar criar com cliente (deve falhar)
            try:
                prof = await criar_ator_profissional(
                    tenant_id=self.tenant_id,
                    canal="",
                    identificador="",
                    nome="Test T10R2 Fail",
                    criado_por=client_id,
                        operation_id="telegram:555555:cadastrar"
                )
                print("[T10-R2] FALHA: Cliente conseguiu criar profissional!")
                self.results["T10-R2"] = False
                return False
            except ValueError as e:
                if "dono" in str(e).lower():
                    print("[T10-R2] PASS - Cliente rejeitado")
                    self.results["T10-R2"] = True
                    return True
                else:
                    print("[T10-R2] FALHA: Erro diferente: " + str(e))
                    self.results["T10-R2"] = False
                    return False

        except Exception as e:
            print("[T10-R2] FALHA: " + str(e))
            self.results["T10-R2"] = False
            return False

    async def test_t10r3_sem_canal(self):
        """T10-R3: Profissional sem canal permitido"""
        print("\n[T10-R3] Testando profissional sem canal...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Profissional Sem Canal T10R3",
                criado_por=self.owner_id,
                operation_id="telegram:666666:cadastrar"
            )

            assert prof["canais"] == [], "Canais deve estar vazio"
            assert prof["actor_id"].startswith("prof_"), "Actor ID deve ter prefixo"

            self.results["T10-R3"] = True
            print("[T10-R3] PASS")
            return True

        except Exception as e:
            print("[T10-R3] FALHA: " + str(e))
            self.results["T10-R3"] = False
            return False

    async def test_t10r4_nenhum_legado(self):
        """T10-R4: Nenhum documento legado criado"""
        print("\n[T10-R4] Validando que legado nao foi criado...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Teste Legado T10R4",
                criado_por=self.owner_id,
                operation_id="telegram:777777:cadastrar"
            )

            def verificar_legado():
                doc = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "Profissionais"
                ).document("Teste Legado T10R4").get()
                return doc.exists

            legado_existe = await asyncio.to_thread(verificar_legado)
            assert not legado_existe, "Documento legado nao deve ser criado"

            self.results["T10-R4"] = True
            print("[T10-R4] PASS")
            return True

        except Exception as e:
            print("[T10-R4] FALHA: " + str(e))
            self.results["T10-R4"] = False
            return False

    async def test_t10r5_telegram_operation_id(self):
        """T10-R5: Telegram operation_id format"""
        print("\n[T10-R5] Validando formato Telegram operation_id...")
        try:
            operation_id = "telegram:123456789:cadastrar_profissional"

            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Test T10R5 Telegram",
                criado_por=self.owner_id,
                operation_id=operation_id
            )

            def verificar_operacao():
                doc = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).document(operation_id).get()
                return doc.to_dict() if doc.exists else None

            operacao = await asyncio.to_thread(verificar_operacao)
            assert operacao is not None, "Operacao Telegram deve existir"
            assert "telegram:" in operacao.get("operation_id", ""), "Operation_id deve conter 'telegram:'"

            self.results["T10-R5"] = True
            print("[T10-R5] PASS")
            return True

        except Exception as e:
            print("[T10-R5] FALHA: " + str(e))
            self.results["T10-R5"] = False
            return False

    async def test_t10r6_whatsapp_operation_id(self):
        """T10-R6: WhatsApp operation_id format"""
        print("\n[T10-R6] Validando formato WhatsApp operation_id...")
        try:
            operation_id = "whatsapp:wamid.abc123def456:cadastrar_profissional"

            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="",
                identificador="",
                nome="Test T10R6 WhatsApp",
                criado_por=self.owner_id,
                operation_id=operation_id
            )

            def verificar_operacao():
                doc = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).document(operation_id).get()
                return doc.to_dict() if doc.exists else None

            operacao = await asyncio.to_thread(verificar_operacao)
            assert operacao is not None, "Operacao WhatsApp deve existir"
            assert "whatsapp:" in operacao.get("operation_id", ""), "Operation_id deve conter 'whatsapp:'"

            self.results["T10-R6"] = True
            print("[T10-R6] PASS")
            return True

        except Exception as e:
            print("[T10-R6] FALHA: " + str(e))
            self.results["T10-R6"] = False
            return False

    async def cleanup(self):
        """Remover documentos de teste"""
        print("\n[CLEANUP] Limpando documentos de teste...")
        try:
            def cleanup_all():
                operacoes = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "OperacoesProfissional"
                ).stream()
                for op in operacoes:
                    op.reference.delete()

                atores = self.db.collection("Clientes").document(self.tenant_id).collection(
                    "Atores"
                ).stream()
                for ator in atores:
                    ator.reference.delete()

            await asyncio.to_thread(cleanup_all)
            print("[CLEANUP] PASS")
            return True

        except Exception as e:
            print("[CLEANUP] FALHA: " + str(e))
            return False


async def main():
    print("\n" + "="*70)
    print("C3.17-I2 GATE 2B.4-E - Idempotencia Multicanal com Transacao")
    print("="*70)

    ctx = FirestoreIdempotenciaTestContext()

    try:
        await ctx.setup()

        await ctx.test_t09r1_retry_mesma_operation()
        await ctx.test_t09r2_concorrencia_mesma_operation()
        await ctx.test_t09r3_mesmo_nome_ops_diferentes()
        await ctx.test_t09r4_tenant_isolation()
        await ctx.test_t10r1_parametros_salvos()
        await ctx.test_t10r2_autorizacao()
        await ctx.test_t10r3_sem_canal()
        await ctx.test_t10r4_nenhum_legado()
        await ctx.test_t10r5_telegram_operation_id()
        await ctx.test_t10r6_whatsapp_operation_id()

        await ctx.cleanup()

        print("\n" + "="*70)
        print("RESULTADO")
        print("="*70)

        for test_name, passed in sorted(ctx.results.items()):
            status = "PASS" if passed else "FAIL"
            print(test_name + ": " + status)

        all_passed = all(ctx.results.values())
        print("\nTOTAL: " + str(sum(ctx.results.values())) + "/" + str(len(ctx.results)) + " PASS")

        if all_passed:
            print("\nRESULTADO FINAL: PASS")
            return True
        else:
            print("\nRESULTADO FINAL: BLOCKED")
            return False

    except Exception as e:
        print("\n" + "="*70)
        print("RESULTADO: EXCECAO")
        print("="*70)
        print("Erro: " + str(e))
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
