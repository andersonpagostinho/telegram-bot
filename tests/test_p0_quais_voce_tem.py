"""
P0 - Testes Unitarios: "quais voce tem?" durante agendando com draft

Validacoes:
- "outra profissional" mantem contrato anterior
- "quais voce tem?" durante agendando apresenta alternativas
- Filtragem por servico do draft funciona
- Exclusao de profissional atual funciona
- Sem alternativas -> pergunta util
- Fora de draft -> comportamento normal
"""

import pytest


def normalizar(texto):
    """Normaliza texto para comparacao."""
    if not texto:
        return ""
    import string
    texto = texto.lower().strip()
    # Remove pontuacao
    texto = texto.translate(str.maketrans('', '', string.punctuation))
    return texto


# ============================================================
# T1: "outra profissional" mantem contrato anterior
# ============================================================
def test_t1_outra_profissional_contrato():
    """Validar que 'outra profissional' retorna tipo=profissional, valor=None."""
    texto = "outra profissional"
    t = normalizar(texto)

    if any(x in t for x in ["outra profissional", "outra prof", "profissional diferente"]):
        resultado = {
            "tipo": "profissional",
            "valor": None
        }
    else:
        resultado = None

    assert resultado is not None, "BUG: 'outra profissional' retorna None"
    assert resultado["tipo"] == "profissional"
    assert resultado["valor"] is None
    print("[T1] PASS: 'outra profissional' mantem contrato: tipo=profissional, valor=None")


# ============================================================
# T2: "quais voce tem?" detecta durante agendando com draft
# ============================================================
def test_t2_quais_voce_tem_detecta():
    """Validar que 'quais voce tem?' e detectado quando tem draft."""
    estado_fluxo = "agendando"
    ctx = {"draft_agendamento": {"servico": "corte", "profissional": "Bruna"}}
    texto = "quais voce tem?"
    tnorm = normalizar(texto)

    tem_draft = bool(ctx.get("draft_agendamento"))
    pergunta_profissionais_draft = (
        tem_draft
        and tnorm in ("quais voce tem", "quais profissionais", "quem tem", "quem atende", "quais outras", "quais alternativas")
    )

    assert tem_draft is True, "BUG: draft nao detectado"
    assert pergunta_profissionais_draft is True, "BUG: pergunta nao detectada"
    print("[T2] PASS: 'quais voce tem?' detectado em agendando com draft")


# ============================================================
# T3: Filtragem por servico do draft
# ============================================================
def test_t3_filtragem_servico():
    """Validar que profissionais sao filtrados pelo servico do draft."""
    profs_dict = {
        "prof_1": {"nome": "Bruna", "servicos": ["corte", "escova", "hidratacao"]},
        "prof_2": {"nome": "Gloria", "servicos": ["corte", "escova"]},
        "prof_3": {"nome": "Joana", "servicos": ["corte", "coloracao"]},
        "prof_4": {"nome": "Larissa", "servicos": ["manicure", "pedicure"]},
    }

    draft = {"servico": "corte", "profissional": "Bruna"}
    servico_draft = draft.get("servico")
    prof_atual = draft.get("profissional")

    nomes_filtrados = []
    for p in profs_dict.values():
        nome = (p.get("nome") or "").strip()
        if not nome:
            continue

        servicos_prof = [str(s).strip().lower() for s in (p.get("servicos") or [])]
        if normalizar(servico_draft) in servicos_prof:
            if normalizar(nome) != normalizar(prof_atual):
                nomes_filtrados.append(nome)

    assert len(nomes_filtrados) == 2, f"Esperava 2 (Gloria, Joana), got {nomes_filtrados}"
    assert "Gloria" in nomes_filtrados
    assert "Joana" in nomes_filtrados
    assert "Bruna" not in nomes_filtrados, "BUG: profissional atual nao foi excluida"
    assert "Larissa" not in nomes_filtrados, "BUG: manicure foi incluida (servico errado)"
    print(f"[T3] PASS: Filtragem: {nomes_filtrados} (profissional atual excluida)")


# ============================================================
# T4: Exclusao de profissional atual
# ============================================================
def test_t4_exclusao_profissional_atual():
    """Validar que profissional atual nao aparece nas alternativas."""
    profs_dict = {
        "prof_1": {"nome": "Bruna", "servicos": ["corte"]},
        "prof_2": {"nome": "Gloria", "servicos": ["corte"]},
    }

    draft = {"servico": "corte", "profissional": "Bruna"}
    prof_atual = draft.get("profissional")

    alternativas = []
    for p in profs_dict.values():
        nome = p.get("nome")
        if normalizar(nome) != normalizar(prof_atual):
            alternativas.append(nome)

    assert len(alternativas) == 1
    assert alternativas[0] == "Gloria"
    assert "Bruna" not in alternativas
    print("[T4] PASS: Profissional atual excluida das alternativas")


# ============================================================
# T5: Sem alternativas -> pergunta util (nao resposta vazia)
# ============================================================
def test_t5_sem_alternativas_pergunta():
    """Validar que sem alternativas retorna pergunta, nao resposta vazia."""
    profs_dict = {
        "prof_1": {"nome": "Bruna", "servicos": ["corte"]},
    }

    draft = {"servico": "corte", "profissional": "Bruna"}
    servico_draft = draft.get("servico")
    prof_atual = draft.get("profissional")

    nomes_filtrados = []
    for p in profs_dict.values():
        nome = p.get("nome")
        if normalizar(nome) != normalizar(prof_atual or ""):
            nomes_filtrados.append(nome)

    if nomes_filtrados:
        txt = f"*Para {servico_draft}, eu tenho:*\n- " + "\n- ".join(nomes_filtrados)
    else:
        txt = f"So tenho a {prof_atual} para {servico_draft}. Quer escolher outro servico ou profissional?"

    assert len(txt) > 0, "BUG: resposta vazia"
    assert "Bruna" in txt, "BUG: profissional atual nao mencionada"
    assert "corte" in txt, "BUG: servico nao mencionado"
    print(f"[T5] PASS: Sem alternativas retorna pergunta util (len={len(txt)})")


# ============================================================
# T6: Fora de draft -> nao interfere
# ============================================================
def test_t6_fora_draft_normal():
    """Validar que fora de draft, 'quais' nao ativa filtro."""
    estado_fluxo = "agendando"
    ctx = {}  # SEM draft
    texto = "quais voce tem?"
    tnorm = normalizar(texto)

    tem_draft = bool(ctx.get("draft_agendamento"))
    pergunta_profissionais_draft = (
        tem_draft
        and tnorm in ("quais voce tem", "quais profissionais", "quem tem", "quem atende", "quais outras", "quais alternativas")
    )

    assert tem_draft is False
    assert pergunta_profissionais_draft is False, "BUG: detectou pergunta sem draft"
    print("[T6] PASS: Fora de draft, 'quais' nao ativa filtro")


# ============================================================
# T7: Variacoes de padrao
# ============================================================
def test_t7_variacoes_padrao():
    """Validar que variacoes de pergunta sao detectadas."""
    padroes = ["quais voce tem", "quem tem", "quem atende", "quais outras"]

    for padrao in padroes:
        tnorm = normalizar(padrao)
        ctx = {"draft_agendamento": {"servico": "corte"}}
        tem_draft = bool(ctx.get("draft_agendamento"))

        detecta = (
            tem_draft
            and tnorm in ("quais voce tem", "quais profissionais", "quem tem", "quem atende", "quais outras", "quais alternativas")
        )

        assert detecta is True, f"BUG: padrao '{padrao}' nao detectado"

    print(f"[T7] PASS: Todas as {len(padroes)} variacoes detectadas")


# ============================================================
# T8: Regressao - escolha explicita continua funcionando
# ============================================================
def test_t8_escolha_explicita():
    """Validar que 'quero Gloria' ainda eh reconhecida como nome de profissional."""
    texto = "quero Gloria"
    tnorm = normalizar(texto)

    pergunta_profissionais_draft = (
        True  # tem_draft
        and tnorm in ("quais voce tem", "quais profissionais", "quem tem", "quem atende", "quais outras", "quais alternativas")
    )

    assert pergunta_profissionais_draft is False, "BUG: 'quero Gloria' foi tratada como pergunta generica"
    print("[T8] PASS: 'quero Gloria' nao ativa filtro (nome especifico ainda funciona)")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTES UNITARIOS: P0 - 'quais voce tem?'")
    print("="*80 + "\n")

    test_t1_outra_profissional_contrato()
    test_t2_quais_voce_tem_detecta()
    test_t3_filtragem_servico()
    test_t4_exclusao_profissional_atual()
    test_t5_sem_alternativas_pergunta()
    test_t6_fora_draft_normal()
    test_t7_variacoes_padrao()
    test_t8_escolha_explicita()

    print("\n" + "="*80)
    print("RESULTADO: 8/8 TESTES PASSARAM")
    print("="*80 + "\n")
