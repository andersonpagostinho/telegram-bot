"""
P0.27.6 — Validação Semântica dos Eventos Legados (READ-ONLY)

Questão crítica: Encontrar evento com ID legado não é suficiente.
É preciso validar se o evento REALMENTE corresponde ao intervalo de horário
protegido pelo lock.

Exemplo:
- Lock: bruna_20261106_100000 (10:00, bucket 100)
- Evento encontrado: whatsapp:5511991382080_bruna_2026-11-06
- Mas evento é para 14:00-15:00?
  → Falsa correspondência! Lock é realmente órfão.

Validações necessárias:
- tenant_id
- cliente_id
- profissional
- data
- hora_inicio / hora_fim (correspondem ao bucket?)
- status do evento
"""

import sys
import os
import asyncio
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.firebase_service_async import buscar_dado_em_path, buscar_subcolecao

TENANT_ID = "7394370553"

# Mapeamento bucket → horário
BUCKET_HOURS = {
    "080000": ("08:00", "08:10"),
    "081000": ("08:10", "08:20"),
    "082000": ("08:20", "08:30"),
    "083000": ("08:30", "08:40"),
    "084000": ("08:40", "08:50"),
    "085000": ("08:50", "09:00"),
    "090000": ("09:00", "09:10"),
    "091000": ("09:10", "09:20"),
    "092000": ("09:20", "09:30"),
    "093000": ("09:30", "09:40"),
    "094000": ("09:40", "09:50"),
    "095000": ("09:50", "10:00"),
    "100000": ("10:00", "10:10"),
    "101000": ("10:10", "10:20"),
    "102000": ("10:20", "10:30"),
    "103000": ("10:30", "10:40"),
    "104000": ("10:40", "10:50"),
    "105000": ("10:50", "11:00"),
    "110000": ("11:00", "11:10"),
    "111000": ("11:10", "11:20"),
    "112000": ("11:20", "11:30"),
    "113000": ("11:30", "11:40"),
    "114000": ("11:40", "11:50"),
    "115000": ("11:50", "12:00"),
    "120000": ("12:00", "12:10"),
    # ... (adicionar mais conforme necessário)
    "150000": ("15:00", "15:10"),
    "151000": ("15:10", "15:20"),
    "152000": ("15:20", "15:30"),
    "153000": ("15:30", "15:40"),
    # ...
}


class ValidadorSemantico:
    def __init__(self):
        self.locks_semanticamente_validos = []
        self.locks_falsa_correspondencia = []
        self.locks_orfaos_confirmados = []
        self.locks_evento_nao_encontrado = []
        self.locks_evento_incompleto = []
        self.total_processado = 0

    async def validar_bruna(self):
        """Validar especificamente os 4 locks de Bruna em 2026-11-06 10:00"""
        print("\n" + "="*80)
        print("P0.27.6 — VALIDAÇÃO SEMÂNTICA: BRUNA 2026-11-06 10:00")
        print("="*80)

        locks_bruna = [
            {
                "lock_id": "bruna_20261106_100000",
                "bucket": "100000",
                "profissional": "Bruna",
                "data": "2026-11-06",
            },
            {
                "lock_id": "bruna_20261106_101000",
                "bucket": "101000",
                "profissional": "Bruna",
                "data": "2026-11-06",
            },
            {
                "lock_id": "bruna_20261106_102000",
                "bucket": "102000",
                "profissional": "Bruna",
                "data": "2026-11-06",
            },
            {
                "lock_id": "bruna_20261106_103000",
                "bucket": "103000",
                "profissional": "Bruna",
                "data": "2026-11-06",
            },
        ]

        print(f"\nLocks esperados:")
        for lock in locks_bruna:
            bucket = lock["bucket"]
            hora_inicio, hora_fim = BUCKET_HOURS.get(bucket, ("?", "?"))
            print(f"  {lock['lock_id']}: {hora_inicio}-{hora_fim}")

        # Buscar evento legado
        evento_id_legado = "whatsapp:5511991382080_bruna_2026-11-06"
        print(f"\nBuscando evento legado: {evento_id_legado}")

        evento = await buscar_dado_em_path(f"Clientes/{TENANT_ID}/Eventos/{evento_id_legado}")

        if not evento:
            print(f"  ❌ Evento não encontrado")
            return

        print(f"  ✓ Evento encontrado")

        # Validar semântica
        print(f"\nValidações semânticas:")
        print(f"  tenant: {TENANT_ID}")
        print(f"  cliente_id: {evento.get('cliente_id')}")
        print(f"  profissional: {evento.get('profissional')}")
        print(f"  data: {evento.get('data')}")
        print(f"  hora_inicio: {evento.get('hora_inicio')}")
        print(f"  hora_fim: {evento.get('hora_fim')}")
        print(f"  status: {evento.get('status')}")

        # Verificar correspondência de horário
        evento_hora_inicio = evento.get("hora_inicio")
        evento_hora_fim = evento.get("hora_fim")

        print(f"\nCorrespondência com locks:")
        for lock in locks_bruna:
            bucket = lock["bucket"]
            lock_hora_inicio, lock_hora_fim = BUCKET_HOURS.get(bucket, ("?", "?"))

            # Verificar se evento cobre esse intervalo
            print(f"  {lock['lock_id']} ({lock_hora_inicio}-{lock_hora_fim}):", end=" ")

            if evento_hora_inicio == "10:00" and evento_hora_fim == "10:40":
                print(f"✓ VÁLIDA (evento ocupa 10:00-10:40)")
            else:
                print(f"⚠️ INCOMPATÍVEL (evento é {evento_hora_inicio}-{evento_hora_fim})")

    async def validar_amostra_434(self):
        """Validar uma amostra dos 434 locks"""
        print(f"\n" + "="*80)
        print("P0.27.6 — AMOSTRA DOS 434 LOCKS")
        print("="*80)

        # Obter todos os locks
        locks_dict = await buscar_subcolecao(f"Clientes/{TENANT_ID}/AgendaLocks")

        print(f"\nTotal de locks no tenant: {len(locks_dict)}")

        # Filtrar por expiração e status confirmado
        locks_candidatos = []
        for lock_id, lock_data in locks_dict.items():
            if lock_data.get("status") == "confirmado":
                expira_em_str = lock_data.get("expira_em")
                if expira_em_str:
                    expira_em = datetime.fromisoformat(expira_em_str)
                    if expira_em <= datetime.now():
                        locks_candidatos.append((lock_id, lock_data))

        print(f"Locks confirmados expirados: {len(locks_candidatos)}")

        # Validar amostra (primeiros 50)
        amostra_size = min(50, len(locks_candidatos))
        print(f"\nValidando amostra de {amostra_size} locks...")

        for i, (lock_id, lock_data) in enumerate(locks_candidatos[:amostra_size]):
            if i % 10 == 0:
                print(f"  Processados: {i}/{amostra_size}")

            evento_id = lock_data.get("evento_id")
            bucket = lock_data.get("bucket")

            if not evento_id or not bucket:
                continue

            # Tentar encontrar evento legado
            if "_" in evento_id and ":" in evento_id:
                evento_id_legado = evento_id.rsplit("_", 1)[0]

                evento = await buscar_dado_em_path(
                    f"Clientes/{TENANT_ID}/Eventos/{evento_id_legado}"
                )

                if evento:
                    # Validar correspondência semântica
                    evento_prof = evento.get("profissional", "").lower()
                    evento_data = evento.get("data")
                    evento_hora_inicio = evento.get("hora_inicio")
                    evento_hora_fim = evento.get("hora_fim")

                    # Extrair esperado do lock
                    lock_prof = lock_data.get("profissional", "").lower()

                    # Verificar se data corresponde
                    lock_data_match = evento_data and evento_data in evento_id_legado

                    # Verificar se horário corresponde
                    lock_hora_inicio, lock_hora_fim = BUCKET_HOURS.get(bucket, (None, None))
                    hora_match = (
                        evento_hora_inicio == lock_hora_inicio
                        and evento_hora_fim == lock_hora_fim
                    )

                    if evento_prof == lock_prof and lock_data_match and hora_match:
                        self.locks_semanticamente_validos.append(lock_id)
                    else:
                        self.locks_falsa_correspondencia.append({
                            "lock_id": lock_id,
                            "evento_id": evento_id,
                            "evento_id_legado": evento_id_legado,
                            "motivo": f"prof:{evento_prof}=={lock_prof}, data:{lock_data_match}, hora:{hora_match}",
                        })
                else:
                    self.locks_orfaos_confirmados.append(lock_id)
            else:
                self.locks_orfaos_confirmados.append(lock_id)

        self.total_processado = amostra_size

    def gerar_relatorio(self):
        """Gerar relatório da validação semântica"""
        print(f"\n" + "="*80)
        print("RELATÓRIO — VALIDAÇÃO SEMÂNTICA P0.27.6")
        print("="*80)

        print(f"\n📊 ESTATÍSTICAS (amostra de {self.total_processado})")
        print(f"  Semanticamente válidos: {len(self.locks_semanticamente_validos)}")
        print(f"  Falsa correspondência: {len(self.locks_falsa_correspondencia)}")
        print(f"  Realmente órfãos: {len(self.locks_orfaos_confirmados)}")
        print(f"  Evento incompleto: {len(self.locks_evento_incompleto)}")

        if self.locks_falsa_correspondencia:
            print(f"\n⚠️ FALSA CORRESPONDÊNCIA (primeiras 5):")
            for lock in self.locks_falsa_correspondencia[:5]:
                print(f"  {lock['lock_id']}")
                print(f"    evento_id: {lock['evento_id']}")
                print(f"    evento_legado: {lock['evento_id_legado']}")
                print(f"    motivo: {lock['motivo']}")

        print(f"\n" + "="*80)
        print("CONCLUSÃO")
        print("="*80)

        total_elegivel = len(self.locks_orfaos_confirmados) + len(self.locks_falsa_correspondencia)
        print(f"\n✅ ELEGÍVEL PARA DELEÇÃO: {total_elegivel}/{self.total_processado}")
        print(f"  Realmente órfãos: {len(self.locks_orfaos_confirmados)}")
        print(f"  Falsa correspondência: {len(self.locks_falsa_correspondencia)}")

        print(f"\n⚠️ PRESERVADO POR CORRESPONDÊNCIA VÁLIDA: {len(self.locks_semanticamente_validos)}/{self.total_processado}")

        print(f"\n" + "="*80 + "\n")


async def main():
    validador = ValidadorSemantico()

    try:
        # Validação específica: Bruna
        await validador.validar_bruna()

        # Amostra dos 434
        await validador.validar_amostra_434()

        # Relatório
        validador.gerar_relatorio()

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
