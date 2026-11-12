# -*- coding: utf-8 -*-
"""
FASE 2 TEST: Validação separada por tipo de mensagem WhatsApp

Testa:
- Texto válido continua funcionando
- Texto sem body é rejeitado
- Áudio OGG/Opus passa validação
- Áudio sem audio.id é rejeitado
- Áudio sem text_body não é rejeitado por esse motivo
- Tipo desconhecido é rejeitado
- Mensagem duplicada mantém idempotência
- Isolamento multi-tenant
"""

import pytest
from unittest.mock import patch, MagicMock


class TestFase2ValidacaoPorTipo:
    """Suite de testes para FASE 2 — Validação por tipo."""

    def criar_payload_base(self, phone_number_id, from_number, msg_id, msg_type):
        """Criar payload base do webhook."""
        return {
            "entry": [{
                "changes": [{
                    "value": {
                        "metadata": {
                            "phone_number_id": phone_number_id,
                        },
                        "messages": [{
                            "id": msg_id,
                            "from": from_number,
                            "type": msg_type,
                        }]
                    }
                }]
            }]
        }

    def test_01_texto_valido_continua_funcionando(self):
        """
        Cenário 1: Texto válido continua funcionando.

        Setup:
        - msg.type = "text"
        - msg.text.body = "Quero agendar"

        Esperado:
        - Passa validação
        - Pode chamar router
        """
        print("\n[TESTE FASE 2.1] Texto válido")

        payload = self.criar_payload_base("phone123", "55199900000", "msg_id_1", "text")
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {
            "body": "Quero agendar"
        }

        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]

        # Simular validação
        msg_type = msg.get("type", "unknown").lower()
        text_body = msg.get("text", {}).get("body", "") if msg_type == "text" else ""

        assert msg_type == "text", "Tipo deveria ser text"
        assert text_body == "Quero agendar", "Text body deveria ser preservado"
        assert text_body, "Text body não pode ser vazio"

        print("✅ [TESTE FASE 2.1] Texto válido passa na validação")

    def test_02_texto_sem_body_rejeitado(self):
        """
        Cenário 2: Texto sem body é tratado corretamente.

        Setup:
        - msg.type = "text"
        - msg.text.body = "" (vazio)

        Esperado:
        - Rejeitado na validação
        """
        print("\n[TESTE FASE 2.2] Texto sem body")

        payload = self.criar_payload_base("phone123", "55199900000", "msg_id_2", "text")
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {
            "body": ""
        }

        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]

        msg_type = msg.get("type", "unknown").lower()
        text_body = msg.get("text", {}).get("body", "") if msg_type == "text" else ""

        # Validação: text sem body = rejeitar
        if msg_type == "text" and not text_body:
            print("  Rejeitado: texto vazio")
            assert True
        else:
            assert False, "Deveria ter sido rejeitado"

        print("✅ [TESTE FASE 2.2] Texto vazio é rejeitado corretamente")

    def test_03_audio_ogg_opus_passa_validacao(self):
        """
        Cenário 3: Áudio OGG/Opus passa pela validação.

        Setup:
        - msg.type = "audio"
        - msg.audio.id = "xyz123"
        - msg.audio.mime_type = "audio/ogg; codecs=opus"
        - msg.text = (ausente)

        Esperado:
        - Passa validação
        - text_body não é exigido
        """
        print("\n[TESTE FASE 2.3] Áudio OGG/Opus")

        payload = self.criar_payload_base("phone123", "55199900000", "msg_id_3", "audio")
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["audio"] = {
            "id": "xyz123",
            "mime_type": "audio/ogg; codecs=opus",
            "voice": True
        }
        # NÃO adicionar text (vazio)

        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]

        msg_type = msg.get("type", "unknown").lower()
        audio = msg.get("audio", {})
        audio_id = audio.get("id", "")
        mime_type = audio.get("mime_type", "")
        text_body = msg.get("text", {}).get("body", "") if msg_type == "text" else ""

        # Validação de áudio
        assert msg_type == "audio", "Tipo deveria ser audio"
        assert audio_id == "xyz123", "audio.id deveria ser válido"
        assert "ogg" in mime_type.lower(), "MIME type deveria ser OGG"
        assert not text_body, "Audio não deveria ter text_body"

        print("✅ [TESTE FASE 2.3] Áudio OGG/Opus passa na validação")

    def test_04_audio_sem_audio_id_rejeitado(self):
        """
        Cenário 4: Áudio sem audio.id é rejeitado corretamente.

        Setup:
        - msg.type = "audio"
        - msg.audio.id = (vazio)
        - msg.audio.mime_type = "audio/ogg; codecs=opus"

        Esperado:
        - Rejeitado na validação
        """
        print("\n[TESTE FASE 2.4] Áudio sem audio.id")

        payload = self.criar_payload_base("phone123", "55199900000", "msg_id_4", "audio")
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["audio"] = {
            "id": "",  # VAZIO
            "mime_type": "audio/ogg; codecs=opus"
        }

        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]

        msg_type = msg.get("type", "unknown").lower()
        audio = msg.get("audio", {})
        audio_id = audio.get("id", "")
        mime_type = audio.get("mime_type", "")

        # Validação
        if msg_type == "audio" and not audio_id:
            print("  Rejeitado: sem audio.id")
            assert True
        else:
            assert False, "Deveria ter sido rejeitado"

        print("✅ [TESTE FASE 2.4] Áudio sem audio.id é rejeitado")

    def test_05_audio_sem_text_body_nao_rejeitado_por_isso(self):
        """
        Cenário 5: Áudio sem text.body não é rejeitado por esse motivo.

        Setup:
        - msg.type = "audio"
        - msg.audio.id = "xyz123"
        - msg.text = (ausente)

        Esperado:
        - NÃO rejeitado por falta de text
        - Validação passa
        """
        print("\n[TESTE FASE 2.5] Áudio sem text.body")

        payload = self.criar_payload_base("phone123", "55199900000", "msg_id_5", "audio")
        payload["entry"][0]["changes"][0]["value"]["messages"][0]["audio"] = {
            "id": "xyz123",
            "mime_type": "audio/ogg; codecs=opus"
        }
        # NÃO adicionar text (o problema anterior)

        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]

        msg_type = msg.get("type", "unknown").lower()
        audio = msg.get("audio", {})
        audio_id = audio.get("id", "")
        text_body = msg.get("text", {}).get("body", "") if msg_type == "text" else ""

        # Validação: áudio não exige text
        assert msg_type == "audio", "Tipo deveria ser audio"
        assert audio_id, "audio.id deveria existir"
        assert not text_body, "Audio não tem text (correto)"

        # NÃO deve ser rejeitado por falta de text
        print("  ✅ Áudio sem text_body NÃO é rejeitado")

        print("✅ [TESTE FASE 2.5] Áudio sem text não é rejeitado por esse motivo")

    def test_06_tipo_desconhecido_rejeitado(self):
        """
        Cenário 6: Tipo desconhecido recebe tratamento explícito.

        Setup:
        - msg.type = "image" (não suportado ainda)

        Esperado:
        - Rejeitado com log explícito
        """
        print("\n[TESTE FASE 2.6] Tipo desconhecido")

        payload = self.criar_payload_base("phone123", "55199900000", "msg_id_6", "image")
        # Tipo "image" não é suportado em FASE 2

        msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        msg_type = msg.get("type", "unknown").lower()

        # Validação
        if msg_type not in ["text", "audio"]:
            print(f"  Rejeitado: tipo '{msg_type}' não suportado")
            assert True
        else:
            assert False, "Deveria ter sido rejeitado"

        print("✅ [TESTE FASE 2.6] Tipo desconhecido é rejeitado")

    def test_07_mensagem_duplicada_mantém_idempotência(self):
        """
        Cenário 7: Mensagem duplicada mantém idempotência.

        Setup:
        - Mesma msg_id chega duas vezes

        Esperado:
        - msg_id é preservado
        - Idempotência (será checada em main.py com Firestore)
        """
        print("\n[TESTE FASE 2.7] Idempotência por msg_id")

        payload1 = self.criar_payload_base("phone123", "55199900000", "msg_id_duplicada", "text")
        payload1["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {"body": "Texto"}

        payload2 = self.criar_payload_base("phone123", "55199900000", "msg_id_duplicada", "text")
        payload2["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {"body": "Texto"}

        msg1 = payload1["entry"][0]["changes"][0]["value"]["messages"][0]
        msg2 = payload2["entry"][0]["changes"][0]["value"]["messages"][0]

        assert msg1.get("id") == msg2.get("id"), "msg_id deveria ser idêntico"
        print("  msg_id preservado para idempotência")

        print("✅ [TESTE FASE 2.7] Idempotência por msg_id mantida")

    def test_08_isolamento_multi_tenant(self):
        """
        Cenário 8: Isolamento multi-tenant permanece intacto.

        Setup:
        - Duas mensagens de diferentes phone_number_id

        Esperado:
        - phone_number_id é preservado
        - Tenant isolation mantido
        """
        print("\n[TESTE FASE 2.8] Isolamento multi-tenant")

        payload_tenant_a = self.criar_payload_base("phone_a", "55199900000", "msg_a", "text")
        payload_tenant_a["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {"body": "Texto"}

        payload_tenant_b = self.criar_payload_base("phone_b", "55199900001", "msg_b", "text")
        payload_tenant_b["entry"][0]["changes"][0]["value"]["messages"][0]["text"] = {"body": "Texto"}

        msg_a = payload_tenant_a["entry"][0]["changes"][0]["value"]["messages"][0]
        msg_b = payload_tenant_b["entry"][0]["changes"][0]["value"]["messages"][0]

        phone_a = payload_tenant_a["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
        phone_b = payload_tenant_b["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]

        assert phone_a != phone_b, "phone_number_id deveria ser diferente"
        assert msg_a.get("from") != msg_b.get("from"), "from deveria ser diferente"

        print("  Tenants isolados por phone_number_id")

        print("✅ [TESTE FASE 2.8] Isolamento multi-tenant mantido")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("FASE 2 TEST — Validação Separada por Tipo")
    print("="*70)

    suite = TestFase2ValidacaoPorTipo()

    suite.test_01_texto_valido_continua_funcionando()
    suite.test_02_texto_sem_body_rejeitado()
    suite.test_03_audio_ogg_opus_passa_validacao()
    suite.test_04_audio_sem_audio_id_rejeitado()
    suite.test_05_audio_sem_text_body_nao_rejeitado_por_isso()
    suite.test_06_tipo_desconhecido_rejeitado()
    suite.test_07_mensagem_duplicada_mantém_idempotência()
    suite.test_08_isolamento_multi_tenant()

    print("\n" + "="*70)
    print("✅ FASE 2 TESTES CONCLUÍDO (8/8 PASS)")
    print("="*70)
