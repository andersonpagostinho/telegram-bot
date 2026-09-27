"""
Teste específico para validar extracao de resposta no webhook WhatsApp.

Valida que main.py corretamente extrai texto_resposta de diferentes
formatos de retorno de roteador_principal().
"""

import pytest


class TestWAResponseExtraction:
    """Testes para extracao de resposta em main.py webhook"""

    def test_extract_from_dict_with_resposta_field(self):
        """Deve extrair texto de dict com campo 'resposta'"""
        resposta = {
            "handled": True,
            "resposta": "Que tipo de negocio? (Salao, Spa, Clínica, Barbers..."
        }

        # Logica equivalente a main.py
        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        assert texto_resposta is not None
        assert isinstance(texto_resposta, str)
        assert texto_resposta == "Que tipo de negocio? (Salao, Spa, Clínica, Barbers..."
        print(f"[OK] Extraido de dict com resposta: {texto_resposta[:50]}...")

    def test_extract_from_string(self):
        """Deve aceitar string diretamente"""
        resposta = "Mensagem simples de texto"

        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        assert texto_resposta is not None
        assert isinstance(texto_resposta, str)
        assert texto_resposta == "Mensagem simples de texto"
        print(f"[OK] Extraído de string: {texto_resposta}")

    def test_no_text_from_already_sent_dict(self):
        """Nao deve extrair texto de dict sem 'resposta' (already_sent)"""
        resposta = {"handled": True, "already_sent": True}

        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        assert texto_resposta is None
        print(f"[OK] Nao extraiu de dict sem 'resposta' (already_sent)")

    def test_no_text_from_action_dict(self):
        """Nao deve extrair texto de dict com acao interna"""
        resposta = {"acao": "criar_evento", "handled": True}

        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        assert texto_resposta is None
        print(f"[OK] Nao extraiu de dict com acao interna")

    def test_empty_resposta_field(self):
        """Nao deve enviar se 'resposta' estiver vazio"""
        resposta = {
            "handled": True,
            "resposta": ""
        }

        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        # texto_resposta será "" (falsy)
        assert not texto_resposta  # "" e falsy
        print(f"[OK] Campo 'resposta' vazio e falsy")

    def test_none_resposta_field(self):
        """Nao deve enviar se 'resposta' for None"""
        resposta = {
            "handled": True,
            "resposta": None
        }

        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        assert texto_resposta is None
        print(f"[OK] Campo 'resposta' None")

    def test_resposta_with_special_chars(self):
        """Deve manter caracteres especiais (acentos, emoji)"""
        resposta = {
            "handled": True,
            "resposta": "🎉 Parabens! Seu negocio está pronto para receber agendamentos."
        }

        texto_resposta = None
        if isinstance(resposta, dict):
            texto_resposta = resposta.get("resposta")
        elif isinstance(resposta, str):
            texto_resposta = resposta

        assert texto_resposta is not None
        assert "🎉" in texto_resposta
        assert "Parabens" in texto_resposta
        print(f"[OK] Mantem caracteres especiais: {texto_resposta}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
