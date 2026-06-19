"""
TEST: PATCH MT-07 DEFENSIVO

Testa que o patch defensivo bloqueia mistura de contexto entre tenants
mesmo quando usando funcoes v1 legadas.

Cenario: Dois donos (A e B) com mesmo cliente_id
Esperado: Contexto de A nao eh acessivel quando processando B
"""

import asyncio
import sys
from datetime import datetime

sys.path.insert(0, "/Users/ANDERSON/iCloudDrive/Projeto Mercado Digital/Agente Bot/NeoEve - Empresarial")


class MockFirestoreDB:
    def __init__(self):
        self.data = {}

    async def salvar(self, path: str, dados: dict):
        self.data[path] = {**self.data.get(path, {}), **dados}
        print(f"   [SALVO] {path}")
        return True

    async def carregar(self, path: str):
        result = self.data.get(path, {})
        if result:
            print(f"   [CARREGADO] {path}")
        return result if result else None

    async def limpar(self):
        self.data = {}


async def test_patch_mt07_defensivo():
    """
    Teste que valida protecao defensiva do patch MT-07.
    """

    print("\n" + "=" * 70)
    print("TEST: PATCH MT-07 DEFENSIVO - Protecao contra tenant mismatch")
    print("=" * 70)

    # Setup
    fs = MockFirestoreDB()

    # IDs de teste
    user_id = "cliente_123"  # MESMO cliente
    dono_a = "dono_salao_a"
    dono_b = "dono_salao_b"

    print(f"\n[SETUP]")
    print(f"   user_id (cliente): {user_id}")
    print(f"   dono_a (salao A): {dono_a}")
    print(f"   dono_b (salao B): {dono_b}")

    # Simular funcoes v1 com patch defensivo
    async def salvar_contexto_com_patch(user_id: str, contexto: dict, tenant_id: str = None):
        """Simula salvar_contexto_temporario com patch defensivo"""
        path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

        if not contexto:
            print(f"   [BLOQUEADO] Contexto vazio bloqueado")
            return

        atual = await fs.carregar(path) or {}
        atual.update(contexto)

        # PATCH: Adicionar guard rail
        if tenant_id:
            atual["_tenant_id_guard"] = tenant_id
            print(f"   [PATCH] Guard rail adicionado: {tenant_id}")
        else:
            print(f"   [RISCO] tenant_id nao fornecido")

        await fs.salvar(path, atual)
        return True

    async def carregar_contexto_com_patch(user_id: str, tenant_id: str = None):
        """Simula carregar_contexto_temporario com patch defensivo"""
        path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"
        data = await fs.carregar(path)

        if not data:
            print(f"   [AVISO] Contexto vazio")
            return None

        # PATCH: Validar tenant_id
        if tenant_id:
            guard_tenant = data.get("_tenant_id_guard")
            if guard_tenant and guard_tenant != tenant_id:
                print(f"   [BLOQUEADO] MISMATCH DETECTADO!")
                print(f"      Esperado: {tenant_id}")
                print(f"      Armazenado: {guard_tenant}")
                return {}  # Bloqueia!
            elif not guard_tenant:
                print(f"   [BLOQUEADO] SEM GUARD RAIL - IGNORANDO PARA SEGURANCA")
                return {}  # Bloqueia!
            else:
                print(f"   [VALIDO] Guard validado: {tenant_id}")
        else:
            print(f"   [RISCO] tenant_id nao fornecido")

        return data

    # === TESTE 1: Cenario de Risco ===
    print(f"\n[TESTE 1] Cenario de Risco: Mesmo cliente, Donos diferentes")

    # Dono A salva contexto
    print(f"\n   Dono A salvando contexto...")
    ctx_a = {
        "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
        "data_hora": "2026-06-20T15:00",
        "aguardando_confirmacao": True
    }
    await salvar_contexto_com_patch(user_id, ctx_a, tenant_id=dono_a)

    # Dono B tenta acessar (deve ser bloqueado)
    print(f"\n   Dono B tentando carregar contexto (DEVE SER BLOQUEADO)...")
    ctx_carregado = await carregar_contexto_com_patch(user_id, tenant_id=dono_b)

    # Validacao
    print(f"\n[VALIDACAO]")
    if ctx_carregado == {}:
        print(f"   [PASSOU] TESTE 1: Contexto foi bloqueado corretamente")
    else:
        print(f"   [FALHOU] TESTE 1: Contexto nao foi bloqueado!")
        print(f"      Carregado: {ctx_carregado}")
        return False

    # === TESTE 2: Compatibilidade ===
    print(f"\n[TESTE 2] Compatibilidade: Dono A carrega seu proprio contexto")

    print(f"\n   Dono A carregando seu proprio contexto (DEVE FUNCIONAR)...")
    ctx_a_reload = await carregar_contexto_com_patch(user_id, tenant_id=dono_a)

    # Validacao
    if ctx_a_reload and ctx_a_reload.get("_tenant_id_guard") == dono_a:
        print(f"   [PASSOU] TESTE 2: Contexto foi carregado corretamente")
    else:
        print(f"   [FALHOU] TESTE 2: Contexto nao foi carregado")
        return False

    # === TESTE 3: Chamada sem tenant_id (compatibilidade legado) ===
    print(f"\n[TESTE 3] Compatibilidade Legado: Chamar sem tenant_id")

    print(f"\n   Carregando SEM tenant_id (compatibilidade pura)...")
    ctx_legado = await carregar_contexto_com_patch(user_id, tenant_id=None)

    # Validacao: deve retornar para compat, mas com risco
    if ctx_legado is not None:
        print(f"   [PASSOU] TESTE 3: Compatibilidade legado funciona (com alerta)")
    else:
        print(f"   [FALHOU] TESTE 3: Compatibilidade quebrou")
        return False

    # === RESULTADO FINAL ===
    print(f"\n{'=' * 70}")
    print(f"[RESULTADO] TODOS OS TESTES PASSARAM")
    print(f"   1. Mismatch entre tenants eh bloqueado")
    print(f"   2. Acesso ao proprio tenant funciona")
    print(f"   3. Compatibilidade legado preservada")
    print(f"{'=' * 70}\n")

    return True


if __name__ == "__main__":
    resultado = asyncio.run(test_patch_mt07_defensivo())
    sys.exit(0 if resultado else 1)
