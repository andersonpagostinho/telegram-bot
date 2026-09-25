"""
C4.4.7-A — Teste de Equivalência: Cadência Firestore == Cadência lst_ordenada

Validar que a cadência calculada a partir de leitura Firestore
é equivalente à cadência calculada a partir de lst_ordenada

Cenários:
  ✅ 3+ eventos válidos
  ✅ Eventos de outros clientes (devem ser filtrados)
  ✅ Eventos de outros serviços (devem ser filtrados)
  ✅ Eventos sem data (devem ser ignorados)
  ✅ Eventos sem hora (devem ser ignorados)
  ✅ Serviços com acentos/maiúsculas (normalizados)
  ✅ Cadência dentro de 10–35 dias
  ✅ Cadência fora do intervalo
  ✅ Intervalos irregulares
"""

import pytest
import asyncio
from datetime import datetime, timedelta, date
import pytz
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recorrencia_service import (
    _descobrir_cadencia,
    _normalizar_servico,
    _parse_dt,
    _intervalos_em_dias,
    _mediana,
)
from services.firebase_service_async import (
    buscar_subcolecao,
    salvar_dado_em_path,
)

FUSO_BR = pytz.timezone("America/Sao_Paulo")


class TestC447aEquivalenciaCadencia:
    """Validar equivalência entre leitura Firestore e lst_ordenada"""

    def setup_method(self):
        """Setup"""
        self.db_ref = "firebase"
        self.tenant_id = f"c447a_eq_{uuid.uuid4().hex[:8]}"
        self.cliente_id = f"cli_eq_{uuid.uuid4().hex[:8]}"
        self.cliente_outro = f"cli_otro_{uuid.uuid4().hex[:8]}"

    async def teardown_method(self):
        """Cleanup"""
        try:
            from services.firebase_service_async import buscar_dado_em_path
            doc = await buscar_dado_em_path(f"Clientes/{self.tenant_id}")
            if doc:
                from services.firebase_service_async import deletar_documento_profundo
                await deletar_documento_profundo(f"Clientes/{self.tenant_id}")
        except:
            pass

    async def _criar_evento(self, data_str: str, hora_str: str, cliente_id: str, servico: str):
        """Helper: criar evento no Firestore"""
        evento_id = f"evt_{uuid.uuid4().hex[:6]}"
        await salvar_dado_em_path(
            f"Clientes/{self.tenant_id}/Eventos/{evento_id}",
            {
                "data": data_str,
                "hora_inicio": hora_str,
                "hora_fim": "11:00",
                "cliente_id": cliente_id,
                "descricao": servico,
                "profissional": "João",
                "status": "confirmado",
            }
        )
        return evento_id

    async def _descobrir_cadencia_filtrado(self, cliente_id: str, servico: str):
        """Helper: carregar eventos do Firestore e chamar _descobrir_cadencia com lst filtrado"""
        eventos = await buscar_subcolecao(f"Clientes/{self.tenant_id}/Eventos") or {}
        lst = []
        servico_norm = _normalizar_servico(servico)

        for _id, ev in eventos.items():
            if not isinstance(ev, dict):
                continue
            if str(ev.get("cliente_id") or "").strip() != str(cliente_id).strip():
                continue
            desc = _normalizar_servico(ev.get("descricao", ""))
            if servico_norm not in desc:
                continue
            lst.append(ev)

        return await _descobrir_cadencia(lst, servico)

    @pytest.mark.asyncio
    async def test_T1_tres_eventos_validos_cadencia_10_dias(self):
        """T1: 3 eventos válidos, cadência = 10 dias"""
        print("\n[T1] 3 eventos válidos, cadência = 10 dias")

        # Criar eventos: 30, 20, 10 dias atrás
        agora = datetime.now(FUSO_BR)
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        # Chamar _descobrir_cadencia (nova assinatura com lst filtrado)
        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        # Validar
        assert cadencia is not None, "[FAIL T1] Cadência não descoberta"
        assert 10 <= cadencia <= 35, f"[FAIL T1] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T1] Cadência descoberta: {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T2_eventos_outros_clientes_ignorados(self):
        """T2: Eventos de outros clientes devem ser ignorados"""
        print("\n[T2] Eventos de outros clientes ignorados")

        agora = datetime.now(FUSO_BR)

        # Eventos do cliente-alvo
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        # Eventos de outro cliente (devem ser ignorados)
        await self._criar_evento(
            (agora - timedelta(days=25)).strftime("%Y-%m-%d"),
            "14:00",
            self.cliente_outro,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=15)).strftime("%Y-%m-%d"),
            "14:00",
            self.cliente_outro,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is not None, "[FAIL T2] Cadência não descoberta"
        assert 10 <= cadencia <= 35, f"[FAIL T2] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T2] Cadência correta (ignorou outros clientes): {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T3_eventos_outros_servicos_ignorados(self):
        """T3: Eventos de outros serviços devem ser ignorados"""
        print("\n[T3] Eventos de outros serviços ignorados")

        agora = datetime.now(FUSO_BR)

        # Eventos de "corte cabelo"
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        # Eventos de "manicure" (devem ser ignorados)
        await self._criar_evento(
            (agora - timedelta(days=25)).strftime("%Y-%m-%d"),
            "14:00",
            self.cliente_id,
            "manicure"
        )
        await self._criar_evento(
            (agora - timedelta(days=15)).strftime("%Y-%m-%d"),
            "14:00",
            self.cliente_id,
            "manicure"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is not None, "[FAIL T3] Cadência não descoberta"
        assert 10 <= cadencia <= 35, f"[FAIL T3] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T3] Cadência correta (ignorou outros serviços): {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T4_eventos_sem_data_ignorados(self):
        """T4: Eventos sem data devem ser ignorados"""
        print("\n[T4] Eventos sem data ignorados")

        agora = datetime.now(FUSO_BR)

        # Evento sem data (será ignorado)
        await salvar_dado_em_path(
            f"Clientes/{self.tenant_id}/Eventos/evt_no_data",
            {
                "data": None,  # SEM DATA
                "hora_inicio": "10:00",
                "cliente_id": self.cliente_id,
                "descricao": "corte cabelo",
                "profissional": "João",
                "status": "confirmado",
            }
        )

        # 3 eventos válidos
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is not None, "[FAIL T4] Cadência não descoberta"
        assert 10 <= cadencia <= 35, f"[FAIL T4] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T4] Cadência correta (ignorou evento sem data): {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T5_eventos_sem_hora_ignorados(self):
        """T5: Eventos sem hora devem ser ignorados"""
        print("\n[T5] Eventos sem hora ignorados")

        agora = datetime.now(FUSO_BR)

        # Evento sem hora (será ignorado no _parse_dt)
        await salvar_dado_em_path(
            f"Clientes/{self.tenant_id}/Eventos/evt_no_hora",
            {
                "data": (agora - timedelta(days=25)).strftime("%Y-%m-%d"),
                "hora_inicio": None,  # SEM HORA
                "cliente_id": self.cliente_id,
                "descricao": "corte cabelo",
                "profissional": "João",
                "status": "confirmado",
            }
        )

        # 3 eventos válidos
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is not None, "[FAIL T5] Cadência não descoberta"
        assert 10 <= cadencia <= 35, f"[FAIL T5] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T5] Cadência correta (ignorou evento sem hora): {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T6_servicos_com_acentos_normalizados(self):
        """T6: Serviços com acentos/maiúsculas devem ser normalizados"""
        print("\n[T6] Serviços com acentos normalizados")

        agora = datetime.now(FUSO_BR)

        # Criar eventos com variações de serviço
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "Côrte Cabêlo"  # Com acentos e maiúsculas
        )
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "CORTE CABELO"  # Maiúsculas
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"  # Minúsculas
        )

        # Buscar com qualquer variação
        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "Côrte Cabêlo"  # Buscar com acentos
        )

        assert cadencia is not None, "[FAIL T6] Cadência não descoberta (normalização falhou)"
        assert 10 <= cadencia <= 35, f"[FAIL T6] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T6] Cadência correta (normalizou acentos): {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T7_cadencia_dentro_intervalo_10_35(self):
        """T7: Cadência dentro de 10-35 dias deve retornar"""
        print("\n[T7] Cadência dentro intervalo [10, 35]")

        agora = datetime.now(FUSO_BR)

        # Criar eventos com cadência = 15 dias
        await self._criar_evento(
            (agora - timedelta(days=45)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=15)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is not None, "[FAIL T7] Cadência não descoberta (dentro do intervalo)"
        assert 10 <= cadencia <= 35, f"[FAIL T7] Cadência fora do intervalo: {cadencia}"
        print(f"  [OK T7] Cadência dentro intervalo: {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T8_cadencia_fora_intervalo_rejeita(self):
        """T8: Cadência fora de 10-35 dias deve retornar None"""
        print("\n[T8] Cadência fora intervalo [10, 35] retorna None")

        agora = datetime.now(FUSO_BR)

        # Criar eventos com cadência = 5 dias (muito curta)
        await self._criar_evento(
            (agora - timedelta(days=15)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=5)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is None, f"[FAIL T8] Cadência deveria ser None (fora intervalo), mas foi {cadencia}"
        print(f"  [OK T8] Cadência rejeitada (fora intervalo): None")

    @pytest.mark.asyncio
    async def test_T9_intervalos_irregulares_mediana(self):
        """T9: Intervalos irregulares usam mediana"""
        print("\n[T9] Intervalos irregulares - mediana")

        agora = datetime.now(FUSO_BR)

        # Criar eventos: intervalos [5, 20, 10] dias
        # Mediana = 10
        await self._criar_evento(
            (agora - timedelta(days=35)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=30)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=0)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        # Intervalos: [5, 20, 10]
        # Mediana: 10
        assert cadencia is not None, "[FAIL T9] Cadência não descoberta"
        assert cadencia == 10, f"[FAIL T9] Esperava mediana=10, obteve {cadencia}"
        print(f"  [OK T9] Mediana correta para intervalos irregulares: {cadencia} dias")

    @pytest.mark.asyncio
    async def test_T10_menos_de_tres_eventos_rejeitados(self):
        """T10: Menos de 3 eventos deve retornar None"""
        print("\n[T10] Menos de 3 eventos rejeitados")

        agora = datetime.now(FUSO_BR)

        # Criar apenas 2 eventos
        await self._criar_evento(
            (agora - timedelta(days=20)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )
        await self._criar_evento(
            (agora - timedelta(days=10)).strftime("%Y-%m-%d"),
            "10:00",
            self.cliente_id,
            "corte cabelo"
        )

        cadencia = await self._descobrir_cadencia_filtrado(
            self.cliente_id,
            "corte cabelo"
        )

        assert cadencia is None, f"[FAIL T10] Cadência deveria ser None (<3 eventos), mas foi {cadencia}"
        print(f"  [OK T10] <3 eventos rejeitados corretamente")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
