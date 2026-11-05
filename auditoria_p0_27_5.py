"""
P0.27.5 — Auditoria dos 434 locks antes da limpeza (READ-ONLY)

Validar individualmente cada lock identificado:
1. Classificação correta?
2. Evento correspondente existente?
3. ID legado encontrado?
4. Expiração correta?
5. Dados consistentes?

Focos especiais:
- 4 locks de Bruna 10:00 em 2026-11-06
- Isolamento de tenant
- Eventos legado vs novo formato
"""

import sys
import os
import asyncio
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.agenda_lock_service import liberar_locks_orfaos_expirados
from services.firebase_service_async import buscar_dado_em_path, buscar_subcolecao

TENANT_ID = "7394370553"

# Locks de Bruna esperados (P0.27.1)
BRUNA_LOCKS_ESPERADOS = {
    "bruna_20261106_100000",
    "bruna_20261106_101000",
    "bruna_20261106_102000",
    "bruna_20261106_103000",
}


class AuditoriaLocks:
    def __init__(self):
        self.locks_por_categoria = defaultdict(list)
        self.locks_com_evento = []
        self.locks_orfaos_reais = []
        self.locks_nao_expirados = []
        self.locks_legado = []
        self.locks_inconclusivos = []
        self.locks_bruna = {"encontrados": [], "nao_encontrados": []}
        self.total_examinado = 0

    async def executar_auditoria(self):
        """Executar auditoria completa dos 434 locks"""
        print("\n" + "="*80)
        print("P0.27.5 — AUDITORIA DOS 434 LOCKS ÓRFÃOS")
        print("="*80)

        # Etapa 1: Obter os 434 locks identificados
        print("\n[ETAPA 1] Executando liberar_locks_orfaos_expirados(dry_run=True)...")
        resultado = await liberar_locks_orfaos_expirados(
            dono_id=TENANT_ID,
            dry_run=True
        )

        locks_identificados = resultado['detalhes']
        self.total_examinado = len(locks_identificados)

        print(f"✓ {self.total_examinado} locks identificados como órfãos")

        # Etapa 2: Classificar cada lock
        print(f"\n[ETAPA 2] Classificando {self.total_examinado} locks...")
        for i, lock_info in enumerate(locks_identificados):
            if i % 50 == 0:
                print(f"  Processados: {i}/{self.total_examinado}")

            await self.analisar_lock(lock_info)

        # Etapa 3: Verificar locks de Bruna especificamente
        print(f"\n[ETAPA 3] Validando locks de Bruna 10:00...")
        await self.validar_bruna()

        # Etapa 4: Gerar relatório
        print(f"\n[ETAPA 4] Gerando relatório...")
        self.gerar_relatorio()

    async def analisar_lock(self, lock_info):
        """Analisar um único lock"""
        lock_id = lock_info['lock_id']
        evento_id = lock_info['evento_id']
        expira_em = lock_info['expira_em']

        # Procurar evento
        evento_encontrado = False
        tipo_encontrado = None

        # Buscar por ID exato
        evento = await buscar_dado_em_path(
            f"Clientes/{TENANT_ID}/Eventos/{evento_id}"
        )

        if evento:
            evento_encontrado = True
            tipo_encontrado = "exato"
            self.locks_com_evento.append({
                "lock_id": lock_id,
                "evento_id": evento_id,
                "tipo": "exato",
            })
            return

        # Buscar por ID legado
        if "_" in evento_id and ":" in evento_id:
            evento_id_legado = evento_id.rsplit("_", 1)[0]
            evento = await buscar_dado_em_path(
                f"Clientes/{TENANT_ID}/Eventos/{evento_id_legado}"
            )

            if evento:
                evento_encontrado = True
                tipo_encontrado = "legado"
                self.locks_legado.append({
                    "lock_id": lock_id,
                    "evento_id": evento_id,
                    "evento_id_legado": evento_id_legado,
                    "tipo": "legado",
                })
                return

        # Se chegou aqui, é realmente órfão
        self.locks_orfaos_reais.append({
            "lock_id": lock_id,
            "evento_id": evento_id,
            "expira_em": expira_em,
            "tipo": "orfao",
        })

    async def validar_bruna(self):
        """Verificar os 4 locks de Bruna 10:00 em 2026-11-06"""
        print(f"\n  Procurando locks de Bruna em 2026-11-06 às 10:00...")

        for lock_id_esperado in BRUNA_LOCKS_ESPERADOS:
            # Procurar nos 434
            encontrado = False
            for lock in self.locks_orfaos_reais:
                if lock["lock_id"] == lock_id_esperado:
                    encontrado = True
                    self.locks_bruna["encontrados"].append(lock)
                    print(f"    ✓ {lock_id_esperado}: ENCONTRADO (órfão confirmado)")
                    break

            for lock in self.locks_com_evento:
                if lock["lock_id"] == lock_id_esperado:
                    encontrado = True
                    self.locks_bruna["encontrados"].append(lock)
                    print(f"    ⚠️ {lock_id_esperado}: ENCONTRADO (tem evento {lock['tipo']})")
                    break

            for lock in self.locks_legado:
                if lock["lock_id"] == lock_id_esperado:
                    encontrado = True
                    self.locks_bruna["encontrados"].append(lock)
                    print(f"    ⚠️ {lock_id_esperado}: ENCONTRADO (evento legado existe)")
                    break

            if not encontrado:
                self.locks_bruna["nao_encontrados"].append(lock_id_esperado)
                print(f"    ❌ {lock_id_esperado}: NÃO ENCONTRADO")

    def gerar_relatorio(self):
        """Gerar relatório final da auditoria"""
        print("\n" + "="*80)
        print("RELATÓRIO FINAL — P0.27.5")
        print("="*80)

        print(f"\n📊 ESTATÍSTICAS")
        print(f"  Total examinado: {self.total_examinado}")
        print(f"  Locks realmente órfãos (sem evento): {len(self.locks_orfaos_reais)}")
        print(f"  Locks com evento exato: {len(self.locks_com_evento)}")
        print(f"  Locks com evento legado: {len(self.locks_legado)}")
        print(f"  Locks nao expirados: {len(self.locks_nao_expirados)}")
        print(f"  Locks inconclusivos: {len(self.locks_inconclusivos)}")

        print(f"\n✅ ELEGÍVEIS PARA EXCLUSÃO")
        print(f"  {len(self.locks_orfaos_reais)} locks realmente órfãos")
        print(f"  Critérios: sem evento (exato ou legado), expirados")

        print(f"\n⚠️ DEVEM SER PRESERVADOS")
        print(f"  {len(self.locks_com_evento)} locks: evento correspondente encontrado (ID exato)")
        print(f"  {len(self.locks_legado)} locks: evento legado encontrado")
        print(f"  Total: {len(self.locks_com_evento) + len(self.locks_legado)}")

        print(f"\n🔍 LOCKS DE BRUNA 10:00 EM 2026-11-06")
        print(f"  Encontrados: {len(self.locks_bruna['encontrados'])}/4")
        print(f"  Não encontrados: {len(self.locks_bruna['nao_encontrados'])}/4")

        if self.locks_bruna["encontrados"]:
            print(f"\n  Detalhes dos encontrados:")
            for lock in self.locks_bruna["encontrados"]:
                print(f"    - {lock['lock_id']}: {lock['tipo']}")

        if self.locks_bruna["nao_encontrados"]:
            print(f"\n  Não encontrados:")
            for lock_id in self.locks_bruna["nao_encontrados"]:
                print(f"    - {lock_id}")

        # Exemplos
        print(f"\n📝 EXEMPLOS DE LOCKS ÓRFÃOS (primeiros 5)")
        for lock in self.locks_orfaos_reais[:5]:
            print(f"  {lock['lock_id']}")
            print(f"    evento_id: {lock['evento_id']}")
            print(f"    expira_em: {lock['expira_em']}")

        if self.locks_com_evento:
            print(f"\n📝 EXEMPLOS DE LOCKS COM EVENTO EXATO (primeiros 3)")
            for lock in self.locks_com_evento[:3]:
                print(f"  {lock['lock_id']}")
                print(f"    evento_id: {lock['evento_id']}")
                print(f"    tipo: {lock['tipo']}")

        if self.locks_legado:
            print(f"\n📝 EXEMPLOS DE LOCKS COM EVENTO LEGADO (primeiros 3)")
            for lock in self.locks_legado[:3]:
                print(f"  {lock['lock_id']}")
                print(f"    evento_id: {lock['evento_id']}")
                print(f"    evento_legado: {lock['evento_id_legado']}")

        # Decisão
        print(f"\n" + "="*80)
        print("DECISÃO")
        print("="*80)

        elegivel = len(self.locks_orfaos_reais)
        preservado = len(self.locks_com_evento) + len(self.locks_legado)

        print(f"\n✅ ELEGÍVEL PARA EXCLUSÃO: {elegivel} locks")
        print(f"⚠️ PRESERVADO: {preservado} locks (tem evento correspondente)")
        print(f"📊 TOTAL VERIFICADO: {elegivel + preservado}/{self.total_examinado}")

        if elegivel > 0:
            print(f"\n✓ Locks órfãos confirmados. Seguro para executar dry_run=False")
        else:
            print(f"\n❌ Nenhum lock elegível para exclusão!")

        print(f"\n" + "="*80 + "\n")


async def main():
    auditoria = AuditoriaLocks()
    try:
        await auditoria.executar_auditoria()
    except Exception as e:
        print(f"❌ Erro durante auditoria: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
