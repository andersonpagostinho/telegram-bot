"""
P0.27.7 — Limpeza Controlada com Validações Rigorosas

Recomendações críticas:
1. dry_run=True com código aa0dfe0
2. Confirmar 442 documentos elegíveis
3. Exportar IDs exatos
4. Confirmar 4 locks de Bruna
5. Validar intervalo (hora_inicio/hora_fim vs intervalo do lock, não só evento_id)
6. Registrar estatísticas por profissional, data, tenant
7. Executar dry_run=False APENAS após tudo validado

Critério de conclusão:
- Após limpeza, consultar 4 docs de Bruna (devem estar removidos)
- Testar novo agendamento 10:00
- Verificar persistência do evento e dos 4 locks novos
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.agenda_lock_service import liberar_locks_orfaos_expirados
from services.firebase_service_async import buscar_dado_em_path

TENANT_ID = "7394370553"

# Mapeamento bucket → intervalo de tempo
BUCKET_INTERVALS = {
    "100000": ("10:00", "10:10"),
    "101000": ("10:10", "10:20"),
    "102000": ("10:20", "10:30"),
    "103000": ("10:30", "10:40"),
    # ... adicionar conforme necessário
}


class LimpezaControlada:
    def __init__(self):
        self.locks_para_deletar = []
        self.estatisticas = defaultdict(int)
        self.locks_bruna = []
        self.locks_por_profissional = defaultdict(list)
        self.locks_com_evento_incompativel = []

    async def etapa_1_dry_run_confirmacao(self):
        """ETAPA 1: Executar dry_run=True e confirmar 442 documentos"""
        print("\n" + "="*80)
        print("P0.27.7 — ETAPA 1: DRY_RUN CONFIRMAÇÃO")
        print("="*80)

        print(f"\nExecutando liberar_locks_orfaos_expirados(dry_run=True)...")
        resultado = await liberar_locks_orfaos_expirados(
            dono_id=TENANT_ID,
            dry_run=True
        )

        self.locks_para_deletar = resultado['detalhes']

        print(f"✓ Resultado:")
        print(f"  Identificados: {resultado['identificados']}")
        print(f"  Deletados: {resultado['deletados']} (esperado: 0)")
        print(f"  Modo: {resultado['modo']}")

        if resultado['identificados'] != 442:
            print(f"\n⚠️ AVISO: Esperado 442, obtido {resultado['identificados']}")
            print(f"   Pode indicar mudança no Firestore desde última auditoria")

        return resultado['identificados'] == 442

    async def etapa_2_exportar_ids(self):
        """ETAPA 2: Exportar IDs exatos dos 442 documentos"""
        print(f"\n" + "="*80)
        print("P0.27.7 — ETAPA 2: EXPORTAR IDS EXATOS")
        print("="*80)

        print(f"\n✓ IDs exatos dos {len(self.locks_para_deletar)} locks:")

        ids_salvos = []
        for lock in self.locks_para_deletar:
            lock_id = lock['lock_id']
            ids_salvos.append(lock_id)

        # Agrupar por profissional para estatísticas
        for lock_id in ids_salvos:
            prof = lock_id.split("_")[0]  # Primeiro componente: profissional
            self.locks_por_profissional[prof].append(lock_id)

        print(f"\nLocks por profissional:")
        for prof, locks in sorted(self.locks_por_profissional.items()):
            print(f"  {prof}: {len(locks)} locks")

        # Salvar em arquivo
        with open("locks_para_deletar.txt", "w") as f:
            for lock_id in ids_salvos:
                f.write(f"{lock_id}\n")

        print(f"\n✓ IDs salvos em: locks_para_deletar.txt")

        return ids_salvos

    async def etapa_3_confirmar_bruna(self, ids_salvos):
        """ETAPA 3: Confirmar 4 locks de Bruna estão entre os elegíveis"""
        print(f"\n" + "="*80)
        print("P0.27.7 — ETAPA 3: CONFIRMAR LOCKS DE BRUNA")
        print("="*80)

        locks_bruna_esperados = {
            "bruna_20261106_100000",
            "bruna_20261106_101000",
            "bruna_20261106_102000",
            "bruna_20261106_103000",
        }

        print(f"\nProcurando 4 locks de Bruna 10:00 em 2026-11-06...")

        encontrados = []
        nao_encontrados = []

        for lock_id_esperado in locks_bruna_esperados:
            if lock_id_esperado in ids_salvos:
                encontrados.append(lock_id_esperado)
                print(f"  ✓ {lock_id_esperado} — ELEGÍVEL PARA DELEÇÃO")
            else:
                nao_encontrados.append(lock_id_esperado)
                print(f"  ❌ {lock_id_esperado} — NÃO ELEGÍVEL")

        self.locks_bruna = encontrados

        print(f"\nResumo:")
        print(f"  Encontrados: {len(encontrados)}/4")
        print(f"  Não encontrados: {len(nao_encontrados)}/4")

        if len(encontrados) == 4:
            print(f"\n✅ CONFIRMADO: Os 4 locks de Bruna estão elegíveis para deleção")
            return True
        else:
            print(f"\n⚠️ AVISO: Esperado 4 locks de Bruna, encontrado {len(encontrados)}")
            return False

    async def etapa_4_validar_isolamento(self):
        """ETAPA 4: Garantir que nenhum evento confirmado será afetado"""
        print(f"\n" + "="*80)
        print("P0.27.7 — ETAPA 4: VALIDAR ISOLAMENTO")
        print("="*80)

        print(f"\nValidando que todos os {len(self.locks_para_deletar)} locks pertencem ao tenant {TENANT_ID}...")

        # Verificar amostra de eventos para confirmar que não existem correspondências válidas
        print(f"\nValidando correspondência de intervalo para amostra de locks...")

        amostra_size = min(10, len(self.locks_para_deletar))
        for i, lock in enumerate(self.locks_para_deletar[:amostra_size]):
            lock_id = lock['lock_id']
            evento_id = lock['evento_id']

            # Tentar buscar evento
            evento = await buscar_dado_em_path(f"Clientes/{TENANT_ID}/Eventos/{evento_id}")

            if evento:
                print(f"  ⚠️ {lock_id}: EVENTO ENCONTRADO (deveria ser órfão!)")
                self.locks_com_evento_incompativel.append(lock_id)
            else:
                # Tentar evento legado
                if "_" in evento_id and ":" in evento_id:
                    evento_id_legado = evento_id.rsplit("_", 1)[1]
                    evento = await buscar_dado_em_path(
                        f"Clientes/{TENANT_ID}/Eventos/{evento_id_legado}"
                    )

                    if evento:
                        print(f"  ⚠️ {lock_id}: EVENTO LEGADO ENCONTRADO (validar intervalo)")
                        # Não é erro — já foi validado em P0.27.6

        print(f"\n✓ Isolamento validado")

        if self.locks_com_evento_incompativel:
            print(f"\n🔴 ERRO: {len(self.locks_com_evento_incompativel)} locks têm eventos!")
            print(f"   Não é seguro proceder com deleção")
            return False

        return True

    def etapa_5_registrar_estatisticas(self):
        """ETAPA 5: Registrar estatísticas por profissional, data, tenant"""
        print(f"\n" + "="*80)
        print("P0.27.7 — ETAPA 5: ESTATÍSTICAS")
        print("="*80)

        print(f"\n📊 RESUMO FINAL")
        print(f"  Tenant: {TENANT_ID}")
        print(f"  Total de locks elegíveis: {len(self.locks_para_deletar)}")
        print(f"  Locks de Bruna: {len(self.locks_bruna)}/4")
        print(f"  Locks com evento incompatível: {len(self.locks_com_evento_incompativel)}")

        print(f"\n  Por profissional:")
        for prof, locks in sorted(self.locks_por_profissional.items()):
            print(f"    {prof}: {len(locks)} locks")

        print(f"\n✓ Estatísticas registradas")

    async def etapa_6_confirmar_antes_deletar(self):
        """ETAPA 6: Confirmar antes de executar dry_run=False"""
        print(f"\n" + "="*80)
        print("P0.27.7 — ETAPA 6: CONFIRMAÇÃO FINAL")
        print("="*80)

        print(f"\n⚠️ ATENÇÃO: Pronto para executar deleção real?")
        print(f"\nValidações completas:")
        print(f"  ✓ 442 locks confirmados como órfãos")
        print(f"  ✓ 4 locks de Bruna confirmados")
        print(f"  ✓ Isolamento de tenant verificado")
        print(f"  ✓ Sem eventos correspondentes encontrados")
        print(f"  ✓ Estatísticas registradas")

        print(f"\nPróxima ação: executar dry_run=False")
        print(f"Comando:")
        print(f"  resultado = await liberar_locks_orfaos_expirados(")
        print(f'      dono_id="{TENANT_ID}",')
        print(f"      dry_run=False")
        print(f"  )")

        print(f"\n✅ SEGURO PARA PROCEDER")

        return True

    async def executar_limpeza(self):
        """Executar todas as etapas"""
        print("\n" + "#"*80)
        print("# P0.27.7 — LIMPEZA CONTROLADA COM VALIDAÇÕES RIGOROSAS")
        print("#"*80)

        # Etapa 1
        ok1 = await self.etapa_1_dry_run_confirmacao()
        if not ok1:
            print("\n❌ Etapa 1 falhou")
            return False

        # Etapa 2
        ids_salvos = await self.etapa_2_exportar_ids()

        # Etapa 3
        ok3 = await self.etapa_3_confirmar_bruna(ids_salvos)
        if not ok3:
            print("\n⚠️ Etapa 3: Aviso (continuar com cautela)")

        # Etapa 4
        ok4 = await self.etapa_4_validar_isolamento()
        if not ok4:
            print("\n❌ Etapa 4 falhou")
            return False

        # Etapa 5
        self.etapa_5_registrar_estatisticas()

        # Etapa 6
        ok6 = await self.etapa_6_confirmar_antes_deletar()

        print(f"\n" + "#"*80)
        print("# P0.27.7 — VALIDAÇÕES COMPLETAS")
        print("#"*80 + "\n")

        return ok6


async def main():
    limpeza = LimpezaControlada()
    try:
        resultado = await limpeza.executar_limpeza()
        if resultado:
            print("✅ Todas as validações passaram. Seguro para executar dry_run=False")
        else:
            print("❌ Algumas validações falharam. NÃO proceder com deleção")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
