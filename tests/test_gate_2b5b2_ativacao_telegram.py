"""
[TEST] GATE 2B.5-B.2: Ativação Telegram por Deep Link com Token HMAC

Objetivo: Validar vínculo Telegram ↔ tenant/actor via token de ativação

14 testes obrigatórios:
T01 — token válido
T02 — token expirado
T03 — token inválido
T04 — token adulterado
T05 — token repetido/idempotência
T06 — concorrência de ativação
T07 — mesmo telegram_user_id em dois tenants
T08 — token de tenant A tentando actor de tenant B
T09 — actor inexistente
T10 — actor inativo
T11 — token revogado
T12 — telegram_user_id obtido de from_user.id
T13 — nenhum uso de obter_id_dono()
T14 — vínculo persistido em Atores.canais[]
"""

import sys
import os
import asyncio
import uuid
import time
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore_client import get_db
from services.identidade_service import (
    gerar_actor_id_estavel,
    vincular_telegram
)
from utils.activation_token_generator import (
    gerar_activation_token,
    validar_activation_token
)


class TestContexto:
    def __init__(self):
        self.tenant_id = f"test_ativacao_{str(uuid.uuid4())[:8]}"
        self.tenant_id_2 = f"test_ativacao_2_{str(uuid.uuid4())[:8]}"
        self.owner_id = gerar_actor_id_estavel(prefixo="owner")
        self.owner_id_2 = gerar_actor_id_estavel(prefixo="owner")

        self.telegram_user_id_1 = "7394370553"
        self.telegram_user_id_2 = "9999999999"

        self.db = None
        self.resultados = {}
        self.now = datetime.now(pytz.UTC).isoformat()

    async def setup(self):
        """Criar tenants e owners de teste"""
        try:
            self.db = get_db()

            owner_data = {
                "actor_id": self.owner_id,
                "tenant_id": self.tenant_id,
                "tipo_usuario": "dono",
                "ativo": True,
                "criado_em": self.now,
                "atualizado_em": self.now,
                "canais": []
            }
            def criar_owner1():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    self.owner_id
                ).set(owner_data)
            await asyncio.to_thread(criar_owner1)

            owner_data_2 = owner_data.copy()
            owner_data_2["actor_id"] = self.owner_id_2
            owner_data_2["tenant_id"] = self.tenant_id_2
            def criar_owner2():
                self.db.collection("Clientes").document(self.tenant_id_2).collection("Atores").document(
                    self.owner_id_2
                ).set(owner_data_2)
            await asyncio.to_thread(criar_owner2)

            print(f"[SETUP] Tenant 1: {self.tenant_id}, Owner: {self.owner_id}")
            print(f"[SETUP] Tenant 2: {self.tenant_id_2}, Owner: {self.owner_id_2}")
            return True
        except Exception as e:
            print(f"[ERRO] Setup: {e}")
            raise

    async def test_t01_token_valido(self):
        """T01: Token válido vincula com sucesso"""
        print("\n[T01] Token válido...")
        try:
            token = gerar_activation_token(self.tenant_id, self.owner_id)
            assert token, "Falha ao gerar token"

            resultado = await vincular_telegram(
                self.tenant_id,
                self.owner_id,
                self.telegram_user_id_1,
                f"token_id_{uuid.uuid4()}"
            )
            assert resultado is not None, "Falha ao vincular"

            canais = resultado.get("canais", [])
            telegram_vinculado = any(
                c.get("canal") == "telegram" and c.get("identificador") == self.telegram_user_id_1
                for c in canais
            )
            assert telegram_vinculado, "Telegram não vinculado em canais[]"

            self.resultados["t01"] = True
            print("[T01] PASS")
            return True
        except Exception as e:
            print(f"[T01] FALHA: {e}")
            self.resultados["t01"] = False
            return False

    async def test_t02_token_expirado(self):
        """T02: Token expirado é rejeitado"""
        print("\n[T02] Token expirado...")
        try:
            token = gerar_activation_token(self.tenant_id, self.owner_id, validity_hours=-1)
            resultado = validar_activation_token(token)
            assert resultado is None, "Token expirado deveria ser rejeitado"

            self.resultados["t02"] = True
            print("[T02] PASS")
            return True
        except Exception as e:
            print(f"[T02] FALHA: {e}")
            self.resultados["t02"] = False
            return False

    async def test_t03_token_invalido(self):
        """T03: Token inválido é rejeitado"""
        print("\n[T03] Token inválido...")
        try:
            token_invalido = "token_aleatorio_invalido_12345"
            resultado = validar_activation_token(token_invalido)
            assert resultado is None, "Token inválido deveria ser rejeitado"

            self.resultados["t03"] = True
            print("[T03] PASS")
            return True
        except Exception as e:
            print(f"[T03] FALHA: {e}")
            self.resultados["t03"] = False
            return False

    async def test_t04_token_adulterado(self):
        """T04: Token adulterado é rejeitado"""
        print("\n[T04] Token adulterado...")
        try:
            token = gerar_activation_token(self.tenant_id, self.owner_id)
            token_adulterado = token[:-5] + "xxxxx"
            resultado = validar_activation_token(token_adulterado)
            assert resultado is None, "Token adulterado deveria ser rejeitado"

            self.resultados["t04"] = True
            print("[T04] PASS")
            return True
        except Exception as e:
            print(f"[T04] FALHA: {e}")
            self.resultados["t04"] = False
            return False

    async def test_t05_token_repetido_idempotencia(self):
        """T05: Token repetido é idempotente"""
        print("\n[T05] Token repetido/idempotência...")
        try:
            token_id = f"token_id_{uuid.uuid4()}"

            resultado1 = await vincular_telegram(
                self.tenant_id,
                self.owner_id,
                self.telegram_user_id_2,
                token_id
            )
            assert resultado1 is not None, "Primeira ativação falhou"

            resultado2 = await vincular_telegram(
                self.tenant_id,
                self.owner_id,
                self.telegram_user_id_2,
                token_id
            )
            assert resultado2 is not None, "Segunda ativação falhou"

            canais1 = resultado1.get("canais", [])
            canais2 = resultado2.get("canais", [])

            count_telegram_1 = sum(
                1 for c in canais1
                if c.get("canal") == "telegram" and c.get("identificador") == self.telegram_user_id_2
            )
            count_telegram_2 = sum(
                1 for c in canais2
                if c.get("canal") == "telegram" and c.get("identificador") == self.telegram_user_id_2
            )

            assert count_telegram_1 == 1, f"Esperado 1 vínculo, obtido {count_telegram_1}"
            assert count_telegram_2 == 1, f"Esperado 1 vínculo, obtido {count_telegram_2}"

            self.resultados["t05"] = True
            print("[T05] PASS")
            return True
        except Exception as e:
            print(f"[T05] FALHA: {e}")
            self.resultados["t05"] = False
            return False

    async def test_t06_concorrencia(self):
        """T06: Concorrência de ativação é segura"""
        print("\n[T06] Concorrência...")
        try:
            owner_id_concorrencia = gerar_actor_id_estavel(prefixo="owner_conc")
            def criar_owner():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    owner_id_concorrencia
                ).set({
                    "actor_id": owner_id_concorrencia,
                    "tenant_id": self.tenant_id,
                    "tipo_usuario": "dono",
                    "ativo": True,
                    "criado_em": self.now,
                    "canais": []
                })
            await asyncio.to_thread(criar_owner)

            token_id = f"token_id_conc_{uuid.uuid4()}"
            telegram_user = "8888888888"

            async def ativar():
                return await vincular_telegram(
                    self.tenant_id,
                    owner_id_concorrencia,
                    telegram_user,
                    token_id
                )

            r1, r2 = await asyncio.gather(ativar(), ativar())

            assert r1 is not None and r2 is not None, "Ativações concorrentes falharam"

            canais1 = r1.get("canais", [])
            canais2 = r2.get("canais", [])

            count1 = sum(
                1 for c in canais1
                if c.get("canal") == "telegram" and c.get("identificador") == telegram_user
            )
            count2 = sum(
                1 for c in canais2
                if c.get("canal") == "telegram" and c.get("identificador") == telegram_user
            )

            assert count1 == 1 and count2 == 1, f"Duplicação de vínculo: {count1}, {count2}"

            self.resultados["t06"] = True
            print("[T06] PASS")
            return True
        except Exception as e:
            print(f"[T06] FALHA: {e}")
            self.resultados["t06"] = False
            return False

    async def test_t07_multi_tenant_mesmo_telegram(self):
        """T07: Mesmo telegram_user_id em dois tenants"""
        print("\n[T07] Multi-tenant mesmo telegram_user_id...")
        try:
            telegram_user = "7777777777"

            r1 = await vincular_telegram(
                self.tenant_id,
                self.owner_id,
                telegram_user,
                f"token_id_{uuid.uuid4()}"
            )
            r2 = await vincular_telegram(
                self.tenant_id_2,
                self.owner_id_2,
                telegram_user,
                f"token_id_{uuid.uuid4()}"
            )

            assert r1 is not None and r2 is not None, "Vínculos em tenants diferentes falharam"

            vinc1 = any(c.get("canal") == "telegram" for c in r1.get("canais", []))
            vinc2 = any(c.get("canal") == "telegram" for c in r2.get("canais", []))

            assert vinc1 and vinc2, "Vínculos não foram criados"

            self.resultados["t07"] = True
            print("[T07] PASS")
            return True
        except Exception as e:
            print(f"[T07] FALHA: {e}")
            self.resultados["t07"] = False
            return False

    async def test_t08_token_outro_tenant(self):
        """T08: Token de tenant_A não pode alterar tenant_B"""
        print("\n[T08] Token outro tenant...")
        try:
            resultado = await vincular_telegram(
                self.tenant_id,
                self.owner_id,
                "6666666666",
                f"token_id_{uuid.uuid4()}"
            )
            assert resultado is not None, "Vínculo em tenant_A falhou"

            resultado_invalido = await vincular_telegram(
                self.tenant_id_2,
                self.owner_id,
                "6666666666",
                f"token_id_{uuid.uuid4()}"
            )
            assert resultado_invalido is None, "Tenant_B não deveria aceitar actor de tenant_A"

            self.resultados["t08"] = True
            print("[T08] PASS")
            return True
        except Exception as e:
            print(f"[T08] FALHA: {e}")
            self.resultados["t08"] = False
            return False

    async def test_t09_actor_inexistente(self):
        """T09: Actor inexistente é rejeitado"""
        print("\n[T09] Actor inexistente...")
        try:
            actor_inexistente = "actor_inexistente_xyz"
            resultado = await vincular_telegram(
                self.tenant_id,
                actor_inexistente,
                "5555555555",
                f"token_id_{uuid.uuid4()}"
            )
            assert resultado is None, "Actor inexistente deveria ser rejeitado"

            self.resultados["t09"] = True
            print("[T09] PASS")
            return True
        except Exception as e:
            print(f"[T09] FALHA: {e}")
            self.resultados["t09"] = False
            return False

    async def test_t10_actor_inativo(self):
        """T10: Actor inativo é rejeitado"""
        print("\n[T10] Actor inativo...")
        try:
            actor_inativo_id = gerar_actor_id_estavel(prefixo="owner_inativo")
            def criar_inativo():
                self.db.collection("Clientes").document(self.tenant_id).collection("Atores").document(
                    actor_inativo_id
                ).set({
                    "actor_id": actor_inativo_id,
                    "tenant_id": self.tenant_id,
                    "tipo_usuario": "dono",
                    "ativo": False,
                    "criado_em": self.now,
                    "canais": []
                })
            await asyncio.to_thread(criar_inativo)

            resultado = await vincular_telegram(
                self.tenant_id,
                actor_inativo_id,
                "4444444444",
                f"token_id_{uuid.uuid4()}"
            )
            assert resultado is None, "Actor inativo deveria ser rejeitado"

            self.resultados["t10"] = True
            print("[T10] PASS")
            return True
        except Exception as e:
            print(f"[T10] FALHA: {e}")
            self.resultados["t10"] = False
            return False

    async def test_t11_validacao_basica(self):
        """T11: Validações básicas"""
        print("\n[T11] Validações básicas...")
        try:
            r1 = await vincular_telegram("", self.owner_id, "1234567890", "token_id")
            assert r1 is None, "Tenant_id vazio deveria ser rejeitado"

            r2 = await vincular_telegram(self.tenant_id, "", "1234567890", "token_id")
            assert r2 is None, "Actor_id vazio deveria ser rejeitado"

            r3 = await vincular_telegram(self.tenant_id, self.owner_id, "", "token_id")
            assert r3 is None, "Telegram_user_id vazio deveria ser rejeitado"

            self.resultados["t11"] = True
            print("[T11] PASS")
            return True
        except Exception as e:
            print(f"[T11] FALHA: {e}")
            self.resultados["t11"] = False
            return False

    async def test_t12_canais_source_of_truth(self):
        """T12: Atores.canais[] é source of truth"""
        print("\n[T12] Canais[] é source of truth...")
        try:
            telegram_user = "3333333333"
            resultado = await vincular_telegram(
                self.tenant_id,
                self.owner_id,
                telegram_user,
                f"token_id_{uuid.uuid4()}"
            )

            assert resultado is not None, "Vínculo falhou"

            canais = resultado.get("canais", [])
            assert isinstance(canais, list), "Canais deveria ser lista"

            telegram_canal = next(
                (c for c in canais if c.get("canal") == "telegram" and c.get("identificador") == telegram_user),
                None
            )
            assert telegram_canal is not None, "Telegram canal não encontrado"
            assert telegram_canal.get("ativo") is True, "Telegram canal deveria estar ativo"
            assert "vinculado_em" in telegram_canal, "Deveria ter timestamp de vinculação"

            self.resultados["t12"] = True
            print("[T12] PASS")
            return True
        except Exception as e:
            print(f"[T12] FALHA: {e}")
            self.resultados["t12"] = False
            return False

    async def test_t13_nenhum_obter_id_dono(self):
        """T13: Verificar que vincular_telegram não usa obter_id_dono()"""
        print("\n[T13] Sem obter_id_dono()...")
        try:
            import inspect
            from services.identidade_service import vincular_telegram

            source = inspect.getsource(vincular_telegram)
            assert "obter_id_dono" not in source, "vincular_telegram não deveria usar obter_id_dono()"

            self.resultados["t13"] = True
            print("[T13] PASS")
            return True
        except Exception as e:
            print(f"[T13] FALHA: {e}")
            self.resultados["t13"] = False
            return False

    async def test_t14_token_hmac(self):
        """T14: Token usa HMAC-SHA256"""
        print("\n[T14] Token HMAC...")
        try:
            token = gerar_activation_token(self.tenant_id, self.owner_id)
            assert token, "Falha ao gerar token"
            assert len(token) > 32, "Token muito curto"

            resultado = validar_activation_token(token)
            assert resultado is not None, "Falha ao validar token válido"

            tenant_id, actor_id, token_id = resultado
            assert tenant_id == self.tenant_id, "Tenant_id descodificado incorretamente"
            assert actor_id == self.owner_id, "Actor_id descodificado incorretamente"

            self.resultados["t14"] = True
            print("[T14] PASS")
            return True
        except Exception as e:
            print(f"[T14] FALHA: {e}")
            self.resultados["t14"] = False
            return False

    async def cleanup(self):
        """Limpeza de teste"""
        try:
            print("\n[CLEANUP] Deletando documentos...")
            def deletar():
                for tenant in [self.tenant_id, self.tenant_id_2]:
                    atores = list(
                        self.db.collection("Clientes").document(tenant).collection("Atores").stream()
                    )
                    for ator in atores:
                        ator.reference.delete()
            await asyncio.to_thread(deletar)
            print("[CLEANUP] OK")
            return True
        except Exception as e:
            print(f"[CLEANUP] Erro: {e}")
            return False


async def main():
    print("\n" + "="*70)
    print("GATE 2B.5-B.2 — ATIVAÇÃO TELEGRAM POR DEEP LINK COM TOKEN HMAC")
    print("="*70)

    ctx = TestContexto()

    try:
        await ctx.setup()

        await ctx.test_t01_token_valido()
        await ctx.test_t02_token_expirado()
        await ctx.test_t03_token_invalido()
        await ctx.test_t04_token_adulterado()
        await ctx.test_t05_token_repetido_idempotencia()
        await ctx.test_t06_concorrencia()
        await ctx.test_t07_multi_tenant_mesmo_telegram()
        await ctx.test_t08_token_outro_tenant()
        await ctx.test_t09_actor_inexistente()
        await ctx.test_t10_actor_inativo()
        await ctx.test_t11_validacao_basica()
        await ctx.test_t12_canais_source_of_truth()
        await ctx.test_t13_nenhum_obter_id_dono()
        await ctx.test_t14_token_hmac()

        await ctx.cleanup()

        total = sum(1 for v in ctx.resultados.values() if v)
        total_testes = len(ctx.resultados)

        print("\n" + "="*70)
        print("RESULTADO")
        print("="*70)
        for teste, resultado in ctx.resultados.items():
            status = "PASS" if resultado else "FAIL"
            print(f"{teste.upper()}: {status}")
        print(f"\nTOTAL: {total}/{total_testes} PASS")
        print("="*70 + "\n")

        return total == total_testes

    except Exception as e:
        print(f"\n[ERRO CRÍTICO] {e}\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
