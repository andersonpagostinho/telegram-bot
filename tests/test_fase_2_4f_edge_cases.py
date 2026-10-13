"""
FASE 2.4F — Testes locais isolados de edge cases
Validar:
1. "queria manter o horario com outra profissional"
2. "14:30 com outra profissional"
3. Escolha de outro horário com mesma profissional
4. Seleção de profissional pelo nome
5. Alternativa indisponível na revalidação
6. Sem criação de evento antes de confirmação
7. Limpeza de estado

Teste sem Firestore — apenas lógica de detecção
"""

import re
import pytest


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação"""
    import unidecode
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


def extrair_horas(texto: str):
    """Simula extração de horas (matches)"""
    texto_norm = (texto or "").strip().lower().replace("às", "as")
    matches = []

    # HH:MM primeiro
    for h, m in re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", texto_norm):
        matches.append((h, m))

    # Só captura hora isolada se NÃO houver HH:MM
    if not matches:
        for h in re.findall(r"\b(?:as\s*)?([01]?\d|2[0-3])h?\b", texto_norm):
            matches.append((h, "00"))

    return matches


def detectar_pedido_generico(
    texto_usuario: str,
    estado_fluxo: str,
    alternativas: list,
) -> bool:
    """
    Simula a lógica de FASE 2.4F:
    Detecta "outra profissional" genérico APENAS se não há hora
    """
    texto_norm_generico = normalizar(texto_usuario or "")
    estado_ativo = (estado_fluxo or "").strip().lower()

    # Calcular matches ANTES da detecção
    matches = extrair_horas(texto_usuario)

    # Detecção com proteção contra hora
    eh_pedido_generico = (
        estado_ativo == "aguardando_escolha_horario"
        and "outra" in texto_norm_generico
        and "profissional" in texto_norm_generico
        and not matches  # ← PROTEÇÃO: só genérico se NÃO há hora
        and any(nome and normalizar(nome) not in texto_norm_generico for nome in alternativas)
    )

    return eh_pedido_generico


class TestFase24FEdgeCases:
    """Testes de FASE 2.4F sem Firestore"""

    def test_1_pedido_generico_sem_hora(self):
        """Cenário 1: "queria manter o horário com outra profissional" → Deve aceitar"""
        texto = "queria manter o horario com outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna", "Joana", "Maria"]
        )
        assert resultado is True, "Deve detectar pedido genérico sem hora"

    def test_2_pedido_generico_com_hora_rejeita(self):
        """Cenário 2: "14:30 com outra profissional" → Deve REJEITAR menu genérico"""
        texto = "14:30 com outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna", "Joana", "Maria"]
        )
        assert resultado is False, "NÃO deve detectar genérico quando há hora"

    def test_2b_pedido_com_hora_alternativa(self):
        """Variação: "queria 14:30 com outra profissional" → Rejeita genérico"""
        texto = "queria 14:30 com outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna", "Joana"]
        )
        assert resultado is False, "NÃO deve detectar genérico com hora"

    def test_3_hora_sem_profissional(self):
        """Cenário 3: "14:30" sozinho → Deve rejeitar genérico"""
        texto = "14:30"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna", "Joana"]
        )
        assert resultado is False, "NÃO é pedido genérico"

    def test_4_nome_especifico_rejeita_generico(self):
        """Cenário 4: "com Bruna" → Rejeita genérico (nome foi mencionado)"""
        texto = "com Bruna"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna", "Joana"]
        )
        # Deve rejeitar porque "bruna" está no texto
        # (4ª condição: any(nome not in texto) será False)
        assert resultado is False, "NÃO é pedido genérico quando nome mencionado"

    def test_5_fora_do_contexto_rejeita(self):
        """Cenário 5: Mesmo texto mas fora de conflito"""
        texto = "queria outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "agendando",  # ← Estado errado
            ["Bruna", "Joana"]
        )
        assert resultado is False, "Rejeita se não está em conflito"

    def test_6_sem_alternativas_rejeita(self):
        """Cenário 6: Sem alternativas disponíveis"""
        texto = "queria outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            []  # ← Vazio
        )
        assert resultado is False, "Rejeita sem alternativas"

    def test_7_hora_abreviada_com_generico(self):
        """Variação: "11h com outra profissional"  → Deve rejeitar menu genérico"""
        texto = "11h com outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna"]
        )
        assert resultado is False, "NÃO deve detectar genérico com hora abreviada"

    def test_8_hora_com_as_prefixo(self):
        """Variação: "as 14 com outra profissional" → Deve rejeitar genérico"""
        texto = "as 14 com outra profissional"
        resultado = detectar_pedido_generico(
            texto,
            "aguardando_escolha_horario",
            ["Bruna"]
        )
        assert resultado is False, "NÃO deve detectar genérico com 'as 14'"


class TestExtrairHoras:
    """Testes da função de extração de horas"""

    def test_hh_mm_format(self):
        """14:30 → encontra hora"""
        matches = extrair_horas("14:30")
        assert len(matches) > 0
        assert matches[0] == ("14", "30")

    def test_hora_abreviada(self):
        """14h ou 14 → encontra hora"""
        matches1 = extrair_horas("14h")
        matches2 = extrair_horas("14")
        assert len(matches1) > 0
        assert len(matches2) > 0

    def test_hora_com_as(self):
        """as 14 → encontra hora"""
        matches = extrair_horas("as 14")
        assert len(matches) > 0

    def test_sem_hora(self):
        """texto sem hora → nada"""
        matches = extrair_horas("queria outra profissional")
        assert len(matches) == 0

    def test_hora_no_meio_de_texto(self):
        """"14:30 com Bruna" → encontra hora"""
        matches = extrair_horas("14:30 com Bruna")
        assert len(matches) > 0


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v"])
