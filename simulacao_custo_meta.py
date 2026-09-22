#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
SIMULACAO DE CUSTO META - PREVISAO DE IMPACTO FINANCEIRO
================================================================================

AVISOS OBRIGATORIOS:

1. Todos os valores de Meta, LLM e Hotmart sao ESTIMATIVAS.
2. A taxa oficial brasileira de mensagens de servico para outubro de 2026
   ainda precisa ser confirmada pela Meta.
3. TAXA_META_POR_MENSAGEM_SERVICO e um PLACEHOLDER e devera ser atualizada
   quando a tarifa oficial for publicada.
4. As estimativas de mensagens e chamadas de LLM por ciclo devem ser
   substituidas por telemetria real da NeoEve.
5. Esta simulacao NAO inclui:
   - Infraestrutura (servidores, bancos de dados)
   - Impostos
   - Suporte tecnico
   - Inadimplencia
   - Estornos de chargeback
   - Custos de aquisicao de clientes
   - Demais custos operacionais
6. O resultado representa MARGEM DE CONTRIBUICAO ESTIMADA, nao margem liquida contabil.

NOTAS IMPORTANTES SOBRE MENSAGENS:

- Mensagens INBOUND (cliente -> NeoEve) NAO geram custo com Meta.
- Apenas mensagens OUTBOUND (NeoEve -> cliente) sao cobradas.
- Um cliente que envia multiplos fragmentos mas recebe uma unica resposta
  consolidada deve contar como UMA mensagem Meta enviada pela NeoEve.
- NAO usar quantidade de mensagens inbound como substituto de outbound.

================================================================================
"""

from typing import Dict, List, Tuple
from domain.plan_catalog import PLAN_CATALOG, get_plan_price

# ==============================================================================
# CONSTANTES EDITAVEIS - TAXAS E PRECOS
# ==============================================================================

# META: Taxa por mensagem de servico outbound enviada pela NeoEve
# PLACEHOLDER: Aguardando tarifa oficial brasileira para outubro/2026
# Referencia anterior (US): ~$0.0079, mas Brasil pode ter taxa diferente
TAXA_META_POR_MENSAGEM_SERVICO = 0.037

# LLM: Custo medio por chamada de API (interpretacao de linguagem, fallbacks, etc.)
# Deve ser calibrado com tokens reais e modelo utilizado (ex: GPT-3.5, GPT-4)
# Observacao: NeoEve executa maior parte da logica deterministicamente;
# GPT atua apenas em interpretacao de linguagem e fallbacks
CUSTO_MEDIO_POR_CHAMADA_LLM = 0.01

# HOTMART: Taxa pela plataforma de pagamentos
# Pode incluir componente percentual e/ou fixo por transacao
TAXA_HOTMART_PERCENTUAL = 0.0997
TAXA_HOTMART_FIXA = 0.00

# ===== MIGRAÇÃO PARA PLANOS CANÔNICOS (2026-08-17) =====
# Antes: 5 planos (SOLO, SOLO_PRO, STUDIO, SALAO, PRO)
# Agora: 3 planos canônicos (SOLO, PROFISSIONAL, SALÕES)
# Fonte única: domain/plan_catalog.py
# Preços atualizados conforme CATALOGO_COMERCIAL_NEOEVE.md V1.2

# Dicionario de planos (construído a partir da fonte canônica)
PLANOS = {}
for plan_id, plan_def in PLAN_CATALOG.items():
    PLANOS[plan_def.name] = plan_def.price_brl

# ==============================================================================
# PERFIS DE CONVERSACAO
# ==============================================================================

# Definem o padrao de interacao de clientes com a NeoEve:
# - direto: cliente direto ao ponto, pouquissimas duvidas
# - medio: cliente com duvidas normais
# - conversador: cliente conversador, muitas interacoes
# - extremo: cliente muito conversador, cria muita carga
#
# Cada perfil define:
#   - mensagens_meta_por_ciclo: outbound enviadas pela NeoEve por ciclo
#   - chamadas_llm_por_ciclo: chamadas de IA por ciclo

PERFIS_CONVERSACAO = {
    "direto": {
        "mensagens_meta_por_ciclo": 3,
        "chamadas_llm_por_ciclo": 0.20,
    },
    "medio": {
        "mensagens_meta_por_ciclo": 5,
        "chamadas_llm_por_ciclo": 0.50,
    },
    "conversador": {
        "mensagens_meta_por_ciclo": 8,
        "chamadas_llm_por_ciclo": 1.00,
    },
    "extremo": {
        "mensagens_meta_por_ciclo": 12,
        "chamadas_llm_por_ciclo": 1.50,
    },
}

# ==============================================================================
# DISTRIBUICOES DE CLIENTES
# ==============================================================================

# Percentual de clientes em cada perfil.
# Deve somar 1.0 (com tolerancia de ponto flutuante).

# Distribuicao PADRAO: mix realista baseado em observacoes iniciais
DISTRIBUICAO_PADRAO_CLIENTES = {
    "direto": 0.50,
    "medio": 0.35,
    "conversador": 0.12,
    "extremo": 0.03,
}

# Distribuicao PESSIMISTA: publico com baixa familiaridade com tecnologia
# tende a gerar mais idas e vindas com um bot do que a distribuicao original assume.
# Este cenario ajuda a identificar risco de modelo se a adocao virar populacao
# menos tech-savvy que o esperado.
DISTRIBUICAO_PESSIMISTA_CLIENTES = {
    "direto": 0.30,
    "medio": 0.35,
    "conversador": 0.25,
    "extremo": 0.10,
}

# ==============================================================================
# TEMPLATES UTILITY (FUTURO)
# ==============================================================================

# Meta: Taxa por template utility (lembretes, confirmacoes, notificacoes)
# Inicialmente zerado; sera atualizado quando a regra e tarifa forem confirmadas
TAXA_META_TEMPLATE_UTILITY = 0.00

# Estimativa de templates por agendamento concluido
# Sera preenchida com telemetria real
TEMPLATES_UTILITY_POR_AGENDAMENTO = 0.00

# ==============================================================================
# FATOR DE CICLOS (TELEMETRIA)
# ==============================================================================

# Nem todo agendamento termina em conclusao na primeira interacao.
# Este fator representa a media de ciclos de atendimento por agendamento concluido,
# considerando:
#   - Duvidas e esclarecimentos
#   - Desistencias e retornos
#   - Conflitos e reagendamentos
#   - Cancelamentos
#
# Exemplo: 1.30 significa que, para cada agendamento concluido,
# houve em media 1,30 ciclos de interacao.
FATOR_CICLOS_POR_AGENDAMENTO_CONCLUIDO = 1.30

# ==============================================================================
# GRADES DE SIMULACAO
# ==============================================================================

# Intervalo de agendamentos concluidos por mes
AGENDAMENTOS_MIN = 20
AGENDAMENTOS_MAX = 400
AGENDAMENTOS_PASSO = 20

# Margens-alvo para analise de volume maximo
MARGENS_ALVO = [0.50, 0.40, 0.30, 0.20, 0.00]

# ==============================================================================
# FUNCOES DE VALIDACAO
# ==============================================================================


def validar_distribuicao_clientes():
    """Valida que as distribuicoes de clientes somam 1.0 (tolerancia 1e-6)."""
    tolerancia = 1e-6

    soma_padrao = sum(DISTRIBUICAO_PADRAO_CLIENTES.values())
    if abs(soma_padrao - 1.0) > tolerancia:
        raise ValueError(
            f"Distribuicao PADRAO deve somar 1.0, mas soma {soma_padrao:.6f}. "
            f"Valores: {DISTRIBUICAO_PADRAO_CLIENTES}"
        )

    soma_pessimista = sum(DISTRIBUICAO_PESSIMISTA_CLIENTES.values())
    if abs(soma_pessimista - 1.0) > tolerancia:
        raise ValueError(
            f"Distribuicao PESSIMISTA deve somar 1.0, mas soma {soma_pessimista:.6f}. "
            f"Valores: {DISTRIBUICAO_PESSIMISTA_CLIENTES}"
        )


def calcular_media_ponderada_perfil(distribuicao: Dict[str, float]) -> Dict[str, float]:
    """
    Calcula media ponderada de mensagens e chamadas LLM a partir de uma distribuicao.
    """
    msg_media = 0.0
    chamadas_media = 0.0

    for perfil_nome, peso in distribuicao.items():
        if perfil_nome not in PERFIS_CONVERSACAO:
            raise ValueError(f"Perfil desconhecido: {perfil_nome}")
        perfil = PERFIS_CONVERSACAO[perfil_nome]
        msg_media += peso * perfil["mensagens_meta_por_ciclo"]
        chamadas_media += peso * perfil["chamadas_llm_por_ciclo"]

    return {
        "mensagens_meta_por_ciclo": msg_media,
        "chamadas_llm_por_ciclo": chamadas_media,
    }

# ==============================================================================
# FUNCOES DE CALCULO
# ==============================================================================


def calcular_ciclos_atendimento(agendamentos_concluidos: float) -> float:
    """Retorna quantidade de ciclos de atendimento (fator de expansao)."""
    return agendamentos_concluidos * FATOR_CICLOS_POR_AGENDAMENTO_CONCLUIDO


def calcular_mensagens_meta(ciclos: float, msg_por_ciclo: float) -> float:
    """Retorna total de mensagens Meta."""
    return ciclos * msg_por_ciclo


def calcular_chamadas_llm(ciclos: float, chamadas_por_ciclo: float) -> float:
    """Retorna total de chamadas LLM."""
    return ciclos * chamadas_por_ciclo


def calcular_custo_meta_servico(mensagens: float) -> float:
    """Retorna custo total de mensagens de servico."""
    return mensagens * TAXA_META_POR_MENSAGEM_SERVICO


def calcular_custo_meta_templates(templates: float) -> float:
    """Retorna custo total de templates utility."""
    return templates * TAXA_META_TEMPLATE_UTILITY


def calcular_custo_llm(chamadas: float) -> float:
    """Retorna custo total de chamadas LLM."""
    return chamadas * CUSTO_MEDIO_POR_CHAMADA_LLM


def calcular_custo_hotmart(preco_plano: float) -> float:
    """Retorna custo Hotmart (percentual + fixo)."""
    return preco_plano * TAXA_HOTMART_PERCENTUAL + TAXA_HOTMART_FIXA


def calcular_margem_contribuicao(
    preco_plano: float,
    custo_meta_servico: float,
    custo_meta_templates: float,
    custo_llm: float,
    custo_hotmart: float,
) -> float:
    """Retorna margem de contribuicao em reais."""
    return (
        preco_plano
        - custo_meta_servico
        - custo_meta_templates
        - custo_llm
        - custo_hotmart
    )


def calcular_margem_percentual(margem_contribuicao: float, preco_plano: float) -> float:
    """Retorna margem de contribuicao em percentual."""
    if preco_plano == 0:
        return 0.0
    return (margem_contribuicao / preco_plano) * 100


def calcular_break_even_agendamentos(
    preco_plano: float,
    msg_por_ciclo: float,
    chamadas_por_ciclo: float,
) -> Tuple[float, int, bool]:
    """
    Calcula break-even matematico (margem = 0).

    Retorna:
        (break_even_teorico, primeiro_inteiro, encontrado_em_grade)
    """
    fator_ciclos = FATOR_CICLOS_POR_AGENDAMENTO_CONCLUIDO
    custo_hotmart = calcular_custo_hotmart(preco_plano)

    coeficiente = fator_ciclos * (
        msg_por_ciclo * TAXA_META_POR_MENSAGEM_SERVICO
        + chamadas_por_ciclo * CUSTO_MEDIO_POR_CHAMADA_LLM
    )

    if coeficiente == 0:
        return float("inf"), -1, False

    break_even_teorico = (preco_plano - custo_hotmart) / coeficiente
    primeiro_inteiro = int(break_even_teorico) + (
        1 if break_even_teorico % 1 > 0 else 0
    )

    # Verificar se primeiro_inteiro esta na grade simulada
    encontrado_em_grade = (
        AGENDAMENTOS_MIN
        <= primeiro_inteiro
        <= AGENDAMENTOS_MAX
        and (primeiro_inteiro - AGENDAMENTOS_MIN) % AGENDAMENTOS_PASSO == 0
    )

    return break_even_teorico, primeiro_inteiro, encontrado_em_grade


def calcular_volume_margem_alvo(
    preco_plano: float,
    margem_alvo: float,
    msg_por_ciclo: float,
    chamadas_por_ciclo: float,
) -> float:
    """
    Calcula maximo de agendamentos para atingir uma margem-alvo (em percentual).

    Exemplo: margem_alvo=0.30 significa 30% de margem.
    """
    fator_ciclos = FATOR_CICLOS_POR_AGENDAMENTO_CONCLUIDO
    custo_hotmart = calcular_custo_hotmart(preco_plano)

    custo_variavel_por_agendamento = fator_ciclos * (
        msg_por_ciclo * TAXA_META_POR_MENSAGEM_SERVICO
        + chamadas_por_ciclo * CUSTO_MEDIO_POR_CHAMADA_LLM
    )

    if custo_variavel_por_agendamento == 0:
        return float("inf")

    volume = (preco_plano * (1 - margem_alvo) - custo_hotmart) / custo_variavel_por_agendamento

    return max(0, volume)


def simular_perfil(
    nome_plano: str,
    preco_plano: float,
    nome_perfil: str,
    msg_por_ciclo: float,
    chamadas_por_ciclo: float,
) -> Dict:
    """Simula um plano com um perfil de conversacao especifico."""

    print(f"\n{'-' * 100}")
    print(f"PLANO: {nome_plano.upper()} | PERFIL: {nome_perfil.upper()}")
    print(f"Preco: R$ {preco_plano:.2f}/mes | Msgs/ciclo: {msg_por_ciclo:.1f} | Chamadas/ciclo: {chamadas_por_ciclo:.2f}")
    print(f"{'-' * 100}\n")

    # Cabecalho da tabela
    print(
        f"{'Agend.':>6} | "
        f"{'Ciclos':>7} | "
        f"{'Msg Meta':>8} | "
        f"{'Chamadas':>8} | "
        f"{'Custo Meta':>11} | "
        f"{'Custo LLM':>10} | "
        f"{'Custo HM':>9} | "
        f"{'Margem R$':>10} | "
        f"{'Margem %':>8}"
    )
    print("-" * 100)

    linhas_resultado = []

    for agendamentos in range(AGENDAMENTOS_MIN, AGENDAMENTOS_MAX + 1, AGENDAMENTOS_PASSO):
        ciclos = calcular_ciclos_atendimento(agendamentos)
        mensagens = calcular_mensagens_meta(ciclos, msg_por_ciclo)
        chamadas = calcular_chamadas_llm(ciclos, chamadas_por_ciclo)
        templates = agendamentos * TEMPLATES_UTILITY_POR_AGENDAMENTO

        custo_meta_srv = calcular_custo_meta_servico(mensagens)
        custo_meta_tpl = calcular_custo_meta_templates(templates)
        custo_llm = calcular_custo_llm(chamadas)
        custo_hm = calcular_custo_hotmart(preco_plano)

        margem_contrib = calcular_margem_contribuicao(
            preco_plano,
            custo_meta_srv,
            custo_meta_tpl,
            custo_llm,
            custo_hm,
        )
        margem_pct = calcular_margem_percentual(margem_contrib, preco_plano)

        print(
            f"{agendamentos:>6} | "
            f"{ciclos:>7.2f} | "
            f"{mensagens:>8.1f} | "
            f"{chamadas:>8.2f} | "
            f"R$ {custo_meta_srv:>9.2f} | "
            f"R$ {custo_llm:>8.2f} | "
            f"R$ {custo_hm:>7.2f} | "
            f"R$ {margem_contrib:>8.2f} | "
            f"{margem_pct:>7.1f}%"
        )

        linhas_resultado.append(
            {
                "agendamentos": agendamentos,
                "ciclos": ciclos,
                "mensagens": mensagens,
                "chamadas": chamadas,
                "custo_meta_srv": custo_meta_srv,
                "custo_llm": custo_llm,
                "custo_hm": custo_hm,
                "margem_contrib": margem_contrib,
                "margem_pct": margem_pct,
            }
        )

    # BREAK-EVEN
    print(f"\n{'-' * 100}")
    print(f"ANALISE DE BREAK-EVEN")
    print(f"{'-' * 100}\n")

    break_even_teorico, primeiro_inteiro, encontrado = calcular_break_even_agendamentos(
        preco_plano, msg_por_ciclo, chamadas_por_ciclo
    )

    if break_even_teorico == float("inf"):
        print("  [!] Coeficiente de custo e zero; break-even nao e aplicavel.\n")
    else:
        print(f"  Break-even teorico: {break_even_teorico:.2f} agendamentos/mes")
        print(f"  Primeiro inteiro com margem <= 0: {primeiro_inteiro}")

        if primeiro_inteiro > AGENDAMENTOS_MAX:
            print(f"  [OK] Break-even nao ocorre na grade (> {AGENDAMENTOS_MAX})")
        else:
            if encontrado:
                print(f"  [OK] Break-even encontrado na grade em {primeiro_inteiro} agendamentos")
            else:
                print(
                    f"  [i] Primeiro inteiro ({primeiro_inteiro}) nao esta na grade "
                    f"(grade: {AGENDAMENTOS_MIN}-{AGENDAMENTOS_MAX}, passo {AGENDAMENTOS_PASSO})"
                )
        print()

    # MARGENS-ALVO
    print(f"{'-' * 100}")
    print(f"VOLUME MAXIMO POR MARGEM-ALVO")
    print(f"{'-' * 100}\n")

    for margem_alvo in MARGENS_ALVO:
        volume_max = calcular_volume_margem_alvo(
            preco_plano, margem_alvo, msg_por_ciclo, chamadas_por_ciclo
        )
        if volume_max == float("inf"):
            print(f"  Margem {margem_alvo*100:>5.0f}%: Infinito")
        elif margem_alvo == 0.00:
            print(f"  Margem {margem_alvo*100:>5.0f}% (Break-even): {volume_max:>7.1f} agendamentos/mes")
        else:
            print(f"  Margem {margem_alvo*100:>5.0f}%: ate {volume_max:>7.1f} agendamentos/mes")

    print()

    return {
        "linhas": linhas_resultado,
        "break_even_teorico": break_even_teorico,
        "primeiro_inteiro": primeiro_inteiro,
    }


def simular_plano_todos_perfis(
    nome_plano: str,
    preco_plano: float,
) -> Dict:
    """Simula um plano para todos os perfis individuais + distribuicao mista."""

    print(f"\n{'=' * 100}")
    print(f"PLANO: {nome_plano.upper()} (R$ {preco_plano:.2f}/mes)")
    print(f"{'=' * 100}")

    resultados = {}

    # Simular cada perfil individual
    for perfil_nome, perfil_dados in PERFIS_CONVERSACAO.items():
        resultado = simular_perfil(
            nome_plano,
            preco_plano,
            perfil_nome,
            perfil_dados["mensagens_meta_por_ciclo"],
            perfil_dados["chamadas_llm_por_ciclo"],
        )
        resultados[perfil_nome] = resultado

    # Simular distribuicao padrao (mix realista)
    media_ponderada = calcular_media_ponderada_perfil(DISTRIBUICAO_PADRAO_CLIENTES)
    resultado_mix = simular_perfil(
        nome_plano,
        preco_plano,
        "DISTRIBUICAO_MISTA",
        media_ponderada["mensagens_meta_por_ciclo"],
        media_ponderada["chamadas_llm_por_ciclo"],
    )
    resultados["distribuicao_mista"] = resultado_mix

    return resultados


# ==============================================================================
# EXIBICAO DE CONSTANTES
# ==============================================================================


def exibir_constantes():
    """Exibe todas as constantes usadas na simulacao."""

    print("\n" + "=" * 100)
    print("CONSTANTES DA SIMULACAO")
    print("=" * 100 + "\n")

    print("TAXAS E CUSTOS:")
    print(f"  TAXA_META_POR_MENSAGEM_SERVICO ........... R$ {TAXA_META_POR_MENSAGEM_SERVICO:.4f}")
    print(f"    [!] PLACEHOLDER -- Aguardando tarifa oficial brasileira para out/2026")
    print(f"  CUSTO_MEDIO_POR_CHAMADA_LLM ............. R$ {CUSTO_MEDIO_POR_CHAMADA_LLM:.4f}")
    print(f"    [i] Deve ser calibrado com tokens e modelo reais")
    print(f"  TAXA_HOTMART_PERCENTUAL ................. {TAXA_HOTMART_PERCENTUAL*100:.2f}%")
    print(f"  TAXA_HOTMART_FIXA ........................ R$ {TAXA_HOTMART_FIXA:.2f}")
    print(f"  TAXA_META_TEMPLATE_UTILITY .............. R$ {TAXA_META_TEMPLATE_UTILITY:.4f}")
    print(f"    [i] Sera atualizado quando regra e tarifa forem confirmadas")

    print(f"\nPRECOS DOS PLANOS:")
    for plano_nome, preco in PLANOS.items():
        print(f"  {plano_nome:.<35} R$ {preco:.2f}/mes")

    print(f"\nPERFIS DE CONVERSACAO:")
    for perfil_nome, perfil_dados in PERFIS_CONVERSACAO.items():
        print(f"  {perfil_nome.upper():.<20} Msgs: {perfil_dados['mensagens_meta_por_ciclo']:.1f} | LLM: {perfil_dados['chamadas_llm_por_ciclo']:.2f}")

    print(f"\nDISTRIBUICHAO PADRAO DE CLIENTES:")
    for perfil_nome, peso in DISTRIBUICAO_PADRAO_CLIENTES.items():
        print(f"  {perfil_nome.upper():.<20} {peso*100:>5.1f}%")
    soma_dist = sum(DISTRIBUICAO_PADRAO_CLIENTES.values())
    print(f"  {'SOMA':.<20} {soma_dist*100:>5.1f}% {'[OK]' if abs(soma_dist - 1.0) < 1e-6 else '[ERRO]'}")

    print(f"\nDISTRIBUICHAO PESSIMISTA DE CLIENTES (tech-savvy menor):")
    for perfil_nome, peso in DISTRIBUICAO_PESSIMISTA_CLIENTES.items():
        print(f"  {perfil_nome.upper():.<20} {peso*100:>5.1f}%")
    soma_dist_pess = sum(DISTRIBUICAO_PESSIMISTA_CLIENTES.values())
    print(f"  {'SOMA':.<20} {soma_dist_pess*100:>5.1f}% {'[OK]' if abs(soma_dist_pess - 1.0) < 1e-6 else '[ERRO]'}")

    media_pond = calcular_media_ponderada_perfil(DISTRIBUICAO_PADRAO_CLIENTES)
    print(f"\nMEDIA PONDERADA (MIX PADRAO):")
    print(f"  Mensagens Meta por ciclo ................. {media_pond['mensagens_meta_por_ciclo']:.2f}")
    print(f"  Chamadas LLM por ciclo ................... {media_pond['chamadas_llm_por_ciclo']:.2f}")

    media_pond_pess = calcular_media_ponderada_perfil(DISTRIBUICAO_PESSIMISTA_CLIENTES)
    print(f"\nMEDIA PONDERADA (MIX PESSIMISTA):")
    print(f"  Mensagens Meta por ciclo ................. {media_pond_pess['mensagens_meta_por_ciclo']:.2f}")
    print(f"  Chamadas LLM por ciclo ................... {media_pond_pess['chamadas_llm_por_ciclo']:.2f}")

    print(f"\nFATORES:")
    print(f"  FATOR_CICLOS_POR_AGENDAMENTO_CONCLUIDO .. {FATOR_CICLOS_POR_AGENDAMENTO_CONCLUIDO}")
    print(f"    [i] Representa ciclos medios (duvidas, reagendamentos, cancelamentos)")
    print(f"  TEMPLATES_UTILITY_POR_AGENDAMENTO ....... {TEMPLATES_UTILITY_POR_AGENDAMENTO}")

    print(f"\nGRADE DE SIMULACAO:")
    print(f"  Agendamentos: {AGENDAMENTOS_MIN} a {AGENDAMENTOS_MAX} (passo {AGENDAMENTOS_PASSO})")
    print(f"  Margens-alvo: {', '.join(f'{m*100:.0f}%' for m in MARGENS_ALVO)}")

    print("\n" + "=" * 100 + "\n")


# ==============================================================================
# TABELAS CONSOLIDADAS
# ==============================================================================


def gerar_matriz_break_even_todos_planos() -> Dict[str, Dict[str, float]]:
    """
    Calcula break-even para todas as combinacoes de planos x perfis.

    Retorna dicionario:
        {plano_nome: {perfil_nome: break_even_teorico}}
    """
    resultado = {}

    for plano_nome, preco in PLANOS.items():
        resultado[plano_nome] = {}

        # Perfis individuais
        for perfil_nome, perfil_dados in PERFIS_CONVERSACAO.items():
            be, _, _ = calcular_break_even_agendamentos(
                preco,
                perfil_dados["mensagens_meta_por_ciclo"],
                perfil_dados["chamadas_llm_por_ciclo"],
            )
            resultado[plano_nome][perfil_nome] = be

        # Mix padrao
        media_pond = calcular_media_ponderada_perfil(DISTRIBUICAO_PADRAO_CLIENTES)
        be, _, _ = calcular_break_even_agendamentos(
            preco,
            media_pond["mensagens_meta_por_ciclo"],
            media_pond["chamadas_llm_por_ciclo"],
        )
        resultado[plano_nome]["mix_padrao"] = be

    return resultado


def exibir_tabela_consolidada_planos_perfis(matriz: Dict[str, Dict[str, float]]):
    """Exibe tabela com planos nas linhas e perfis nas colunas."""

    print("\n" + "=" * 130)
    print("TABELA CONSOLIDADA - BREAK-EVEN POR PLANO E PERFIL")
    print("(Agendamentos/mes para margem = 0%)")
    print("=" * 130 + "\n")

    perfis_ordem = ["direto", "medio", "conversador", "extremo", "mix_padrao"]
    perfis_display = ["DIRETO", "MEDIO", "CONVERSADOR", "EXTREMO", "MIX PADRAO"]

    # Cabecalho
    print(f"{'Plano':.<15} | ", end="")
    for perfil_display in perfis_display:
        print(f"{perfil_display:>15} | ", end="")
    print()

    print("-" * 130)

    # Linhas
    for plano_nome in PLANOS.keys():
        print(f"{plano_nome:.<15} | ", end="")
        for perfil_key in perfis_ordem:
            be = matriz[plano_nome][perfil_key]
            if be == float("inf"):
                print(f"{'inf':>15} | ", end="")
            else:
                print(f"{be:>15.2f} | ", end="")
        print()

    print("=" * 130 + "\n")


def gerar_matriz_break_even_pessimista() -> Dict[str, float]:
    """
    Calcula break-even para Mix pessimista em todos os planos.

    Retorna dicionario:
        {plano_nome: break_even_teorico}
    """
    resultado = {}
    media_pond = calcular_media_ponderada_perfil(DISTRIBUICAO_PESSIMISTA_CLIENTES)

    for plano_nome, preco in PLANOS.items():
        be, _, _ = calcular_break_even_agendamentos(
            preco,
            media_pond["mensagens_meta_por_ciclo"],
            media_pond["chamadas_llm_por_ciclo"],
        )
        resultado[plano_nome] = be

    return resultado


def exibir_comparacao_padrao_vs_pessimista(
    matriz_padrao: Dict[str, Dict[str, float]],
    matriz_pessimista: Dict[str, float],
):
    """Exibe tabela comparando Mix padrao vs Mix pessimista."""

    print("\n" + "=" * 110)
    print("TESTE DE SENSIBILIDADE - MIX PADRAO vs MIX PESSIMISTA")
    print("=" * 110 + "\n")

    print(f"{'Plano':.<15} | {'Mix Padrao':>15} | {'Mix Pessimista':>15} | {'Diferenca %':>12} | Analise")
    print("-" * 110)

    diferencas_percentuais = []

    for plano_nome in PLANOS.keys():
        be_padrao = matriz_padrao[plano_nome]["mix_padrao"]
        be_pessimista = matriz_pessimista[plano_nome]

        if be_padrao == float("inf") or be_pessimista == float("inf"):
            diff_pct_str = "N/A"
            analise = "Break-even nao alcancado"
        else:
            diff_pct = ((be_pessimista - be_padrao) / be_padrao) * 100
            diff_pct_str = f"{diff_pct:>11.1f}%"
            diferencas_percentuais.append(diff_pct)

            # Nota: diferença negativa significa break-even menor (pior) no mix pessimista
            # Usar valor absoluto para avaliar magnitude da sensibilidade
            abs_diff_pct = abs(diff_pct)
            if abs_diff_pct > 20:
                if diff_pct < 0:
                    analise = "[ALTO RISCO] Muito sensivel (piora com mix pessimista)"
                else:
                    analise = "[ALTO RISCO] Muito sensivel"
            elif abs_diff_pct > 10:
                if diff_pct < 0:
                    analise = "[MEDIO] Sensibilidade moderada (piora)"
                else:
                    analise = "[MEDIO] Sensibilidade moderada"
            else:
                analise = "[OK] Pouco sensivel"

        be_padrao_str = f"{be_padrao:.2f}" if be_padrao != float("inf") else "inf"
        be_pessimista_str = f"{be_pessimista:.2f}" if be_pessimista != float("inf") else "inf"

        print(f"{plano_nome:.<15} | {be_padrao_str:>15} | {be_pessimista_str:>15} | {diff_pct_str} | {analise}")

    print("=" * 110 + "\n")

    if diferencas_percentuais:
        media_diff = sum(diferencas_percentuais) / len(diferencas_percentuais)
        print(f"Diferenca percentual media (todos os planos): {media_diff:.1f}%\n")


def exibir_resumo_executivo(
    matriz_todos: Dict[str, Dict[str, float]],
    matriz_pessimista: Dict[str, float],
):
    """Exibe resumo executivo com insights chave."""

    print("\n" + "=" * 110)
    print("RESUMO EXECUTIVO")
    print("=" * 110 + "\n")

    # 1. Planos com break-even < 100 em algum cenario
    print("1. ZONA DE RISCO ALTO (break-even < 100 agendamentos/mes em algum cenario):\n")
    zona_risco = False

    for plano_nome in PLANOS.keys():
        min_be = float("inf")
        perfil_risco = None

        for perfil_nome, be in matriz_todos[plano_nome].items():
            if be != float("inf") and be < min_be:
                min_be = be
                perfil_risco = perfil_nome

        if min_be < 100:
            zona_risco = True
            perfil_display = perfil_risco.upper().replace("_", " ")
            print(f"   [!] {plano_nome:.<15} Break-even MINIMO: {min_be:.2f} agendamentos ({perfil_display})")

    if not zona_risco:
        print("   [OK] Nenhum plano quebra com break-even < 100 agendamentos.")

    # 2. Planos seguros ate 400 agendamentos mesmo no pessimista
    print("\n2. ZONA SEGURA (break-even > 400 agendamentos ate 400 em Mix pessimista):\n")
    zona_segura = []

    for plano_nome in PLANOS.keys():
        be_pessimista = matriz_pessimista[plano_nome]
        if be_pessimista != float("inf") and be_pessimista > 400:
            zona_segura.append(plano_nome)
            print(f"   [OK] {plano_nome:.<15} Nunca quebra (break-even: {be_pessimista:.2f} agendamentos)")

    if not zona_segura:
        print("   [!] Nenhum plano permanece seguro ate 400 agendamentos no cenario pessimista.")

    # 3. Diferenca percentual media
    print("\n3. SENSIBILIDADE DO MODELO:\n")

    diferencas = []
    for plano_nome in PLANOS.keys():
        be_padrao = matriz_todos[plano_nome]["mix_padrao"]
        be_pessimista = matriz_pessimista[plano_nome]

        if be_padrao != float("inf") and be_pessimista != float("inf"):
            diff_pct = ((be_pessimista - be_padrao) / be_padrao) * 100
            diferencas.append(diff_pct)

    if diferencas:
        media_diff = sum(diferencas) / len(diferencas)
        media_abs_diff = sum(abs(d) for d in diferencas) / len(diferencas)
        max_diff = max(diferencas, key=abs)
        min_diff = min(diferencas, key=abs)

        print(f"   Media de variacao entre Mix padrao e Mix pessimista: {media_diff:.1f}%")
        print(f"   Media de variacao absoluta: {media_abs_diff:.1f}%")
        print(f"   Intervalo: {min_diff:.1f}% a {max_diff:.1f}%")
        print()

        if media_abs_diff > 20:
            print(f"   [!] Modelo e MUITO SENSIVEL a distribuicao assumida.")
            print(f"       Mix pessimista deteriora o break-even em media {media_abs_diff:.1f}%")
        elif media_abs_diff > 10:
            print(f"   [i] Modelo tem SENSIBILIDADE MODERADA a distribuicao assumida.")
            print(f"       Variacao media de {media_abs_diff:.1f}%")
        else:
            print(f"   [OK] Modelo e POUCO SENSIVEL a distribuicao assumida.")

    print("\n" + "=" * 110 + "\n")


# ==============================================================================
# RESUMO COMPARATIVO
# ==============================================================================


def exibir_resumo_comparativo(resultados_por_plano: Dict):
    """Exibe comparacao de custos e break-evens entre perfis."""

    print("\n\n")
    print("=" * 100)
    print("RESUMO COMPARATIVO - BREAK-EVEN POR PERFIL")
    print("=" * 100 + "\n")

    # Usar apenas os 3 planos canônicos
    for plano_nome in ["SOLO", "PROFISSIONAL", "SALÕES"]:
        if plano_nome in resultados_por_plano:
            preco = PLANOS.get(plano_nome)
            if preco is None:
                continue

            print(f"\n{plano_nome} (R$ {preco:.2f}/mes):")
            print(f"  {'-' * 80}")
            print(f"  {'Perfil':.<20} {'Break-even (teorico)':>20} {'Primeiro inteiro':>15}")
            print(f"  {'-' * 80}")

            resultado = resultados_por_plano[plano_nome]

            for perfil_nome in ["direto", "medio", "conversador", "extremo", "distribuicao_mista"]:
                if perfil_nome in resultado:
                    data = resultado[perfil_nome]
                    be = data["break_even_teorico"]
                    pi = data["primeiro_inteiro"]

                    be_str = f"{be:.2f}" if be != float("inf") else "inf"
                    pi_str = f"{pi}" if pi != -1 else "N/A"

                    nome_display = "MIX PADRAO" if perfil_nome == "distribuicao_mista" else perfil_nome.upper()
                    print(f"  {nome_display:.<20} {be_str:>20} {pi_str:>15}")

            print()

    print("=" * 100 + "\n")


# ==============================================================================
# MAIN
# ==============================================================================


if __name__ == "__main__":
    # Validar distribuicoes de clientes
    validar_distribuicao_clientes()

    exibir_constantes()

    print("\n\n")
    print("+" + "=" * 98 + "+")
    print("|" + " SIMULACAO DE IMPACTO DE CUSTOS META ".center(98) + "|")
    print("+" + "=" * 98 + "+")

    # PARTE 1: Matriz consolidada de break-even para todos os planos e perfis
    print("\n[GERANDO MATRIZ CONSOLIDADA DE BREAK-EVEN...]")
    matriz_break_even_todos = gerar_matriz_break_even_todos_planos()
    exibir_tabela_consolidada_planos_perfis(matriz_break_even_todos)

    # PARTE 2: Teste de sensibilidade (Mix padrao vs Mix pessimista)
    print("\n[GERANDO TESTE DE SENSIBILIDADE...]")
    matriz_break_even_pessimista = gerar_matriz_break_even_pessimista()
    exibir_comparacao_padrao_vs_pessimista(matriz_break_even_todos, matriz_break_even_pessimista)

    # PARTE 3: Resumo executivo
    print("\n[GERANDO RESUMO EXECUTIVO...]")
    exibir_resumo_executivo(matriz_break_even_todos, matriz_break_even_pessimista)

    print("=" * 100)
    print("FIM DA SIMULACAO")
    print("=" * 100 + "\n")
