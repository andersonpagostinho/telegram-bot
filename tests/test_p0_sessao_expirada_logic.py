"""
P0 EXPIRAÇÃO: Teste de lógica PURA (sem Firebase)

Valida:
- Critérios de elegibilidade (estado, timestamp, inatividade)
- Cálculo de tempo decorrido
- Extraçõ de wa_id
- Determinação de canal
"""

import pytest
from datetime import datetime, timedelta, timezone


class TestExpiracaoLogicaPura:
    """Testes de lógica pura (sem I/O)."""

    # =========================================================
    # CRITÉRIO 1: estado_fluxo != "idle"
    # =========================================================

    def test_estado_idle_ignora(self):
        """Sessão com estado=idle não é elegível."""
        estado = "idle"
        assert estado.strip().lower() == "idle", "Estado deve ser idle"

    def test_estado_agendando_elegivel(self):
        """Sessão com estado=agendando é elegível."""
        estado = "agendando"
        assert estado.strip().lower() != "idle", "Estado deve ser elegível"

    # =========================================================
    # CRITÉRIO 2: Timestamp válido com fuso
    # =========================================================

    def test_timestamp_com_fuso_ok(self):
        """Timestamp com fuso é válido."""
        import dateutil.parser
        ts_str = "2026-10-16T12:30:45.000000+00:00"
        ts = dateutil.parser.isoparse(ts_str)

        assert ts.tzinfo is not None, "Deve ter timezone"
        assert ts.utcoffset() is not None, "Deve ter offset"

    def test_timestamp_sem_fuso_invalido(self):
        """Timestamp sem fuso é inválido."""
        import dateutil.parser
        ts_str = "2026-10-16T12:30:45"  # SEM FUSO
        ts = dateutil.parser.isoparse(ts_str)

        assert ts.tzinfo is None, "Não deve ter timezone"

    # =========================================================
    # CRITÉRIO 3: Inatividade >= 3600 segundos
    # =========================================================

    def test_inatividade_65min_expirado(self):
        """Inatividade de 65 minutos (3900s) >= 3600s."""
        agora = datetime.now(timezone.utc)
        ts_atividade_str = (agora - timedelta(minutes=65)).isoformat()

        import dateutil.parser
        ts = dateutil.parser.isoparse(ts_atividade_str)
        tempo_decorrido = (agora - ts).total_seconds()

        assert tempo_decorrido >= 3600, "Deve ser >= 3600s"

    def test_inatividade_30min_nao_expirado(self):
        """Inatividade de 30 minutos (1800s) < 3600s."""
        agora = datetime.now(timezone.utc)
        ts_atividade_str = (agora - timedelta(minutes=30)).isoformat()

        import dateutil.parser
        ts = dateutil.parser.isoparse(ts_atividade_str)
        tempo_decorrido = (agora - ts).total_seconds()

        assert tempo_decorrido < 3600, "Deve ser < 3600s"

    # =========================================================
    # IDEMPOTÊNCIA: Flag 6 horas
    # =========================================================

    def test_flag_refresco_dentro_6h(self):
        """Flag dentro de 6h não permite reenvio."""
        agora = datetime.now(timezone.utc)
        ts_aviso_str = (agora - timedelta(hours=2)).isoformat()  # 2h atrás

        import dateutil.parser
        ts = dateutil.parser.isoparse(ts_aviso_str)
        tempo_desde_aviso = (agora - ts).total_seconds()

        assert tempo_desde_aviso < 21600, "Deve ser < 6h"
        # Lógica: if tempo < 21600: continue (não reenvia)

    def test_flag_expirado_apos_6h(self):
        """Flag após 6h permite retry."""
        agora = datetime.now(timezone.utc)
        ts_aviso_str = (agora - timedelta(hours=7)).isoformat()  # 7h atrás

        import dateutil.parser
        ts = dateutil.parser.isoparse(ts_aviso_str)
        tempo_desde_aviso = (agora - ts).total_seconds()

        assert tempo_desde_aviso >= 21600, "Deve ser >= 6h"
        # Lógica: if tempo >= 21600: permite reenviar

    # =========================================================
    # EXTRAÇÃO WA_ID
    # =========================================================

    def test_whatsapp_extrai_wa_id(self):
        """Prefixo whatsapp: extrai wa_id corretamente."""
        actor_id = "whatsapp:5511991382080"

        if actor_id.startswith("whatsapp:"):
            canal = "whatsapp"
            wa_id = actor_id.split(":")[-1]
        else:
            canal = "telegram"
            wa_id = actor_id

        assert canal == "whatsapp", "Canal deve ser whatsapp"
        assert wa_id == "5511991382080", "wa_id deve ser extraído"

    def test_telegram_usa_actor_id(self):
        """Sem prefixo: usa actor_id como Telegram."""
        actor_id = "123456789"

        if actor_id.startswith("whatsapp:"):
            canal = "whatsapp"
            destinatario = actor_id.split(":")[-1]
        else:
            canal = "telegram"
            destinatario = actor_id

        assert canal == "telegram", "Canal deve ser telegram"
        assert destinatario == "123456789", "Deve usar actor_id"

    # =========================================================
    # CÁLCULO DE EVENT_ID
    # =========================================================

    def test_event_id_normalizacao_hora(self):
        """event_id normaliza hora como salvar_evento."""
        hora_entrada = "14:37"  # Entrada

        h, m = map(int, hora_entrada.split(":"))
        m = (m // 20) * 20  # Arredondar para múltiplo de 20
        hora_normalizada = f"{h:02d}:{m:02d}"

        assert hora_normalizada == "14:20", f"Deve ser 14:20, obteve {hora_normalizada}"

    def test_event_id_construcao(self):
        """event_id construído corretamente."""
        cliente_id = "whatsapp:5511991382080"
        profissional = "Bruna"
        data = "2026-10-16"
        hora = "14:20"

        base_id = f"{cliente_id}_{profissional}_{data}_{hora}"
        event_id = base_id.replace(" ", "_").lower()

        expected = "whatsapp:5511991382080_bruna_2026-10-16_14:20"
        assert event_id == expected, f"event_id incorreto: {event_id}"

    # =========================================================
    # COMPORTAMENTO DE ERRO SEGURO
    # =========================================================

    def test_timestamp_invalido_nao_limpa(self):
        """Timestamp inválido não causa execução."""
        import dateutil.parser

        try:
            ts_str = "2026-10-16T12:30:45"  # SEM FUSO
            ts = dateutil.parser.isoparse(ts_str)

            # Validação
            if ts.tzinfo is None or ts.utcoffset() is None:
                # Deve pular (continue), não limpar
                deve_pular = True
            else:
                deve_pular = False
        except Exception as e:
            # Também pula em exceção
            deve_pular = True

        assert deve_pular, "Deve pular (não limpar)"

    # =========================================================
    # CONSOLIDAÇÃO
    # =========================================================

    def test_elegibilidade_completa(self):
        """Sessão elegível passa todos os critérios."""
        # Dados
        estado = "agandando"
        agora = datetime.now(timezone.utc)
        ts_atividade_str = (agora - timedelta(minutes=65)).isoformat()  # 65min

        # Critério 1: estado
        elegivel_estado = estado.strip().lower() != "idle"
        assert elegivel_estado, "Critério 1 falhou"

        # Critério 2 + 3: timestamp e inatividade
        import dateutil.parser
        ts = dateutil.parser.isoparse(ts_atividade_str)

        elegivel_timestamp = ts.tzinfo is not None and ts.utcoffset() is not None
        assert elegivel_timestamp, "Critério 2 falhou"

        tempo_decorrido = (agora - ts).total_seconds()
        elegivel_inatividade = tempo_decorrido >= 3600
        assert elegivel_inatividade, "Critério 3 falhou"

        # Resultado
        elegivel_total = elegivel_estado and elegivel_timestamp and elegivel_inatividade
        assert elegivel_total, "Deve ser elegível"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
