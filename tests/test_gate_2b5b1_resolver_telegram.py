"""
[TEST] GATE 2B.5-B.1: Resolver Canônico + Índice Telegram (T01-T10)

Objetivo: Validar infraestrutura de resolução:
- Telegram user_id → TelegramActors → tenant_id + actor_id
- Validação contra fonte canônica Atores.canais[]
- Isolamento multi-tenant
- Idempotência de sincronização
"""

import sys
import os
import asyncio
import uuid
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.identidade_service import (
    criar_ator_profissional,
    gerar_actor_id_estavel,
    resolver_ator_por_canal_canonico,
    sincronizar_indice_telegram,
)
from services.firestore_client import get_db


class TestContexto:
    def __init__(self):
        self.tenant_id = f"gate2b5b1_{str(uuid.uuid4())[:8]}"
        self.tenant_2 = f"gate2b5b1_t2_{str(uuid.uuid4())[:8]}"
        self.owner_id = gerar_actor_id_estavel(prefixo="owner")
        self.owner_2 = gerar_actor_id_estavel(prefixo="owner")

        self.telegram_user_1 = "123456789"
        self.telegram_user_2 = "987654321"
        self.telegram_user_inexistente = "111111111"

        self.db = None
        self.resultados = {}

    async def setup(self):
        """Criar tenants e atores de teste"""
        try:
            self.db = get_db()
            now = datetime.now(pytz.UTC).isoformat()

            # Owner 1 para tenant 1
            owner_data = {
                "tenant_id": self.tenant_id,
                "actor_id": self.owner_id,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_owner1():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    self.owner_id
                ).set(owner_data)
            await asyncio.to_thread(criar_owner1)
            print("[SETUP] Owner 1 criado: " + self.owner_id)

            # Owner 2 para tenant 2
            owner_data_2 = {
                "tenant_id": self.tenant_2,
                "actor_id": self.owner_2,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": now,
                "atualizado_em": now
            }
            def criar_owner2():
                self.db.collection("Clientes").document(self.tenant_2).collection("Atores").document(
                    self.owner_2
                ).set(owner_data_2)
            await asyncio.to_thread(criar_owner2)
            print("[SETUP] Owner 2 criado: " + self.owner_2)

            return True
        except Exception as e:
            print("[ERRO] Setup: " + str(e))
            raise

    async def test_t01_resolver_existente(self):
        """T01: Resolver ator Telegram existente"""
        print("\n[T01] Resolver ator Telegram existente...")
        try:
            # Criar profissional com vínculo Telegram
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="telegram",
                identificador=self.telegram_user_1,
                nome="João Telegram",
                criado_por=self.owner_id
            )
            actor_id = prof["actor_id"]
            print("[T01] Profissional criado: " + actor_id)

            # Sincronizar índice
            synced = await sincronizar_indice_telegram(
                self.telegram_user_1,
                self.tenant_id,
                actor_id,
                "profissional"
            )
            assert synced, "Sincronização falhou"
            print("[T01] Índice sincronizado")

            # Resolver
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                self.telegram_user_1
            )

            assert resultado is not None, "Resolver retornou None"
            assert resultado["actor_id"] == actor_id, "actor_id diverge"
            assert resultado["tipo_usuario"] == "profissional", "Tipo de usuário incorreto"
            assert resultado["ativo"] == True, "Ator inativo"

            self.resultados["t01"] = True
            print("[T01] PASS")
            return True
        except Exception as e:
            print("[T01] FALHA: " + str(e))
            self.resultados["t01"] = False
            return False

    async def test_t02_telegram_inexistente(self):
        """T02: Telegram user inexistente retorna None"""
        print("\n[T02] Telegram user inexistente...")
        try:
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                self.telegram_user_inexistente
            )

            assert resultado is None, "Deveria retornar None"

            self.resultados["t02"] = True
            print("[T02] PASS")
            return True
        except Exception as e:
            print("[T02] FALHA: " + str(e))
            self.resultados["t02"] = False
            return False

    async def test_t03_indice_ator_inexistente(self):
        """T03: Índice aponta para ator inexistente"""
        print("\n[T03] Índice aponta para ator inexistente...")
        try:
            # Criar índice órfão
            def criar_indice_orfao():
                self.db.collection("TelegramActors").document(self.telegram_user_2).set({
                    "tenant_id": self.tenant_id,
                    "actor_id": "prof_inexistente_xyz",
                    "papel": "profissional",
                    "ativo": True
                })
            await asyncio.to_thread(criar_indice_orfao)

            # Tentar resolver
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                self.telegram_user_2
            )

            # Não deve encontrar porque não há ator com esse vínculo
            assert resultado is None, "Deveria não encontrar ator"

            self.resultados["t03"] = True
            print("[T03] PASS - Inconsistência detectada")
            return True
        except Exception as e:
            print("[T03] FALHA: " + str(e))
            self.resultados["t03"] = False
            return False

    async def test_t04_isolamento_tenant(self):
        """T04: Isolamento entre tenants"""
        print("\n[T04] Isolamento entre tenants...")
        try:
            # Criar prof no tenant 2 com mesmo Telegram user_id
            prof2 = await criar_ator_profissional(
                tenant_id=self.tenant_2,
                canal="telegram",
                identificador=self.telegram_user_1,  # Mesmo ID do T01
                nome="João Tenant 2",
                criado_por=self.owner_2,
            )
            actor_id_2 = prof2["actor_id"]

            # Sincronizar
            await sincronizar_indice_telegram(
                self.telegram_user_1,
                self.tenant_2,
                actor_id_2,
                "profissional"
            )

            # Resolver no tenant 1 ainda deve retornar T01
            resultado1 = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                self.telegram_user_1
            )
            assert resultado1 is not None, "Deve encontrar no tenant 1"

            # Resolver no tenant 2 deve retornar tenant 2
            resultado2 = await resolver_ator_por_canal_canonico(
                self.tenant_2,
                "telegram",
                self.telegram_user_1
            )
            assert resultado2 is not None, "Deve encontrar no tenant 2"
            assert resultado2["actor_id"] == actor_id_2, "actor_id deve ser do tenant 2"

            self.resultados["t04"] = True
            print("[T04] PASS - Isolamento mantido")
            return True
        except Exception as e:
            print("[T04] FALHA: " + str(e))
            self.resultados["t04"] = False
            return False

    async def test_t05_ator_sem_vinculo(self):
        """T05: Ator sem vínculo Telegram"""
        print("\n[T05] Ator sem vínculo Telegram...")
        try:
            # Criar prof com OUTRO canal (não Telegram)
            prof_sem = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="whatsapp",
                identificador="5511999999999",
                nome="Profissional Sem Telegram",
                criado_por=self.owner_id,
            )

            # Tentar resolver com um telegram user_id qualquer
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                "999999999"
            )

            assert resultado is None, "Não deve encontrar prof sem Telegram"

            self.resultados["t05"] = True
            print("[T05] PASS")
            return True
        except Exception as e:
            print("[T05] FALHA: " + str(e))
            self.resultados["t05"] = False
            return False

    async def test_t06_ator_inativo(self):
        """T06: Ator inativo não é resolvido"""
        print("\n[T06] Ator inativo...")
        try:
            # Criar prof
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="telegram",
                identificador="555555555",
                nome="Profissional Inativo",
                criado_por=self.owner_id,
            )
            actor_id = prof["actor_id"]

            # Sincronizar
            await sincronizar_indice_telegram(
                "555555555",
                self.tenant_id,
                actor_id,
                "profissional"
            )

            # Desativar
            def desativar():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    actor_id
                ).update({"ativo": False})
            await asyncio.to_thread(desativar)

            # Resolver não deve retornar
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                "555555555"
            )

            assert resultado is None, "Não deve retornar ator inativo"

            self.resultados["t06"] = True
            print("[T06] PASS")
            return True
        except Exception as e:
            print("[T06] FALHA: " + str(e))
            self.resultados["t06"] = False
            return False

    async def test_t07_sincronizacao_idempotente(self):
        """T07: Sincronização é idempotente"""
        print("\n[T07] Sincronização idempotente...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="telegram",
                identificador="777777777",
                nome="Prof Idempotente",
                criado_por=self.owner_id,
            )
            actor_id = prof["actor_id"]

            # Sincronizar 3 vezes
            for i in range(3):
                result = await sincronizar_indice_telegram(
                    "777777777",
                    self.tenant_id,
                    actor_id,
                    "profissional"
                )
                assert result, f"Sincronização {i+1} falhou"

            # Verificar que apenas 1 documento existe
            def verificar():
                doc = self.db.collection("TelegramActors").document("777777777").get()
                return doc.exists  # Documento existe
            resultado = await asyncio.to_thread(verificar)
            assert resultado, "Documento não existe"

            self.resultados["t07"] = True
            print("[T07] PASS")
            return True
        except Exception as e:
            print("[T07] FALHA: " + str(e))
            self.resultados["t07"] = False
            return False

    async def test_t08_vinculo_inativo(self):
        """T08: Vínculo inativo não é resolvido"""
        print("\n[T08] Vínculo inativo...")
        try:
            prof = await criar_ator_profissional(
                tenant_id=self.tenant_id,
                canal="telegram",
                identificador="888888888",
                nome="Prof Vínculo Inativo",
                criado_por=self.owner_id,
            )
            actor_id = prof["actor_id"]

            # Desativar vínculo
            def desativar_vinculo():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    actor_id
                ).update({
                    "canais": [{
                        "canal": "telegram",
                        "identificador": "888888888",
                        "ativo": False,  # ← Inativo
                        "vinculado_em": datetime.now(pytz.UTC).isoformat()
                    }]
                })
            await asyncio.to_thread(desativar_vinculo)

            # Resolver não deve encontrar
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                "888888888"
            )

            assert resultado is None, "Vínculo inativo não deve ser resolvido"

            self.resultados["t08"] = True
            print("[T08] PASS")
            return True
        except Exception as e:
            print("[T08] FALHA: " + str(e))
            self.resultados["t08"] = False
            return False

    async def test_t09_dono_existente(self):
        """T09: Dono pode ser resolvido"""
        print("\n[T09] Dono Telegram...")
        try:
            # Sincronizar dono com Telegram
            await sincronizar_indice_telegram(
                "999999999",
                self.tenant_id,
                self.owner_id,
                "dono"
            )

            # Criar vínculo no ator dono
            def adicionar_vinculo_dono():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    self.owner_id
                ).update({
                    "canais": [{
                        "canal": "telegram",
                        "identificador": "999999999",
                        "ativo": True,
                        "vinculado_em": datetime.now(pytz.UTC).isoformat()
                    }]
                })
            await asyncio.to_thread(adicionar_vinculo_dono)

            # Resolver
            resultado = await resolver_ator_por_canal_canonico(
                self.tenant_id,
                "telegram",
                "999999999"
            )

            assert resultado is not None, "Deve resolver dono"
            assert resultado["tipo_usuario"] == "dono", "Deve ser dono"

            self.resultados["t09"] = True
            print("[T09] PASS")
            return True
        except Exception as e:
            print("[T09] FALHA: " + str(e))
            self.resultados["t09"] = False
            return False

    async def cleanup(self):
        """Limpeza de teste"""
        try:
            print("\n[CLEANUP] Deletando documentos de teste...")

            # Deletar collections
            def deletar():
                # Tenants
                for tenant in [self.tenant_id, self.tenant_2]:
                    atores = list(
                        self.db.collection("Clientes").document(tenant).collection("Atores").stream()
                    )
                    for ator in atores:
                        ator.reference.delete()

                # TelegramActors
                telegram_docs = list(self.db.collection("TelegramActors").stream())
                for doc in telegram_docs:
                    doc.reference.delete()

            await asyncio.to_thread(deletar)
            print("[CLEANUP] Completo")
            return True
        except Exception as e:
            print("[CLEANUP] Erro: " + str(e))
            return False


async def main():
    print("\n" + "=" * 70)
    print("GATE 2B.5-B.1 — RESOLVER CANÔNICO + ÍNDICE TELEGRAM (T01-T09)")
    print("=" * 70)

    ctx = TestContexto()

    try:
        await ctx.setup()

        await ctx.test_t01_resolver_existente()
        await ctx.test_t02_telegram_inexistente()
        await ctx.test_t03_indice_ator_inexistente()
        await ctx.test_t04_isolamento_tenant()
        await ctx.test_t05_ator_sem_vinculo()
        await ctx.test_t06_ator_inativo()
        await ctx.test_t07_sincronizacao_idempotente()
        await ctx.test_t08_vinculo_inativo()
        await ctx.test_t09_dono_existente()

        await ctx.cleanup()

        # Resultado
        total = sum(1 for v in ctx.resultados.values() if v)
        total_testes = len(ctx.resultados)

        print("\n" + "=" * 70)
        print("RESULTADO")
        print("=" * 70)
        for teste, resultado in ctx.resultados.items():
            status = "PASS" if resultado else "FAIL"
            print(f"{teste.upper()}: {status}")
        print(f"\nTOTAL: {total}/{total_testes} PASS")
        print("=" * 70 + "\n")

        return total == total_testes

    except Exception as e:
        print("\n" + "=" * 70)
        print("ERRO CRÍTICO")
        print("=" * 70)
        print(str(e))
        print("=" * 70 + "\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
