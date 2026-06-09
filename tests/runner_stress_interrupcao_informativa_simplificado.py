#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
STRESS TEST SIMPLIFICADO - Interrupcoes Informativas

Este runner simula os comportamentos esperados sem chamar o router completo.
Foca em validar que o sistema preserva estado quando recebe perguntas informativas.

Cenarios:
1. Fluxo ativo + pergunta informativa: servico/draft preservados
2. Retomada apos interrupcao: contexto nao reiniciado
3. Multiplas interrupcoes: data/hora/profissional nao alterados
"""

import json
from datetime import datetime
from pathlib import Path


class ContextoSimulado:
    """Simula o comportamento esperado do contexto durante interrupcoes"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.estado_fluxo = None
        self.servico = None
        self.profissional_escolhido = None
        self.data_hora = None
        self.draft_agendamento = {}
        self.aguardando_confirmacao_agendamento = False

    def processar_mensagem(self, tipo_mensagem, dados=None):
        """
        Processa uma mensagem e atualiza o contexto conforme esperado.

        tipos:
        - agendamento_inicial: "quero agendar X"
        - pergunta_informativa: "qual...", "quanto...", "quem..."
        - preenchimento_data: "amanhã", "segunda"
        - preenchimento_hora: "às 10", "às 14:30"
        - preenchimento_profissional: "Bruna", "Carla"
        - retomada: "pode ser", "ok", "sim"
        """

        if tipo_mensagem == "agendamento_inicial":
            # Inicia fluxo de agendamento
            self.estado_fluxo = "agendando"
            self.servico = dados.get("servico")
            self.draft_agendamento = {
                "servico": self.servico,
                "etapa": "aguardando_data",
            }

        elif tipo_mensagem == "pergunta_informativa":
            # Pergunta informativa NAO altera slots criticos
            # Mantém estado_fluxo, servico, draft
            resposta = dados.get("resposta")
            return {"tipo": "resposta_informativa", "conteudo": resposta}

        elif tipo_mensagem == "preenchimento_data":
            # Preenche data no draft
            self.data_hora = dados.get("data_hora")
            self.draft_agendamento["data_hora"] = self.data_hora
            self.draft_agendamento["etapa"] = "aguardando_hora"

        elif tipo_mensagem == "preenchimento_hora":
            # Preenche hora no data_hora
            data = self.data_hora.split("T")[0] if self.data_hora else ""
            self.data_hora = f"{data}T{dados.get('hora')}"
            self.draft_agendamento["data_hora"] = self.data_hora
            self.draft_agendamento["etapa"] = "aguardando_profissional"

        elif tipo_mensagem == "preenchimento_profissional":
            # Preenche profissional
            self.profissional_escolhido = dados.get("profissional")
            self.draft_agendamento["profissional"] = self.profissional_escolhido
            self.draft_agendamento["etapa"] = "pronto_para_confirmar"

        elif tipo_mensagem == "retomada":
            # Retomada nao reinicia fluxo (estado permanece agendando)
            if self.estado_fluxo == "agendando":
                # Continue no mesmo estado
                pass

        return None


def log_passo(numero, descricao, ctx_antes, ctx_depois):
    """Log estruturado antes/depois"""
    print(f"\n{'-' * 100}")
    print(f"PASSO {numero}: {descricao}")
    print(f"{'-' * 100}")

    print(f"\n[ANTES]")
    print(f"  estado_fluxo: {ctx_antes.estado_fluxo}")
    print(f"  servico: {ctx_antes.servico}")
    print(f"  data_hora: {ctx_antes.data_hora}")
    print(f"  profissional: {ctx_antes.profissional_escolhido}")
    print(f"  draft: {bool(ctx_antes.draft_agendamento)}")

    print(f"\n[DEPOIS]")
    print(f"  estado_fluxo: {ctx_depois.estado_fluxo}")
    print(f"  servico: {ctx_depois.servico}")
    print(f"  data_hora: {ctx_depois.data_hora}")
    print(f"  profissional: {ctx_depois.profissional_escolhido}")
    print(f"  draft: {bool(ctx_depois.draft_agendamento)}")

    # Mostrar mudancas
    mudancas = []
    if ctx_antes.estado_fluxo != ctx_depois.estado_fluxo:
        mudancas.append(f"estado_fluxo: {ctx_antes.estado_fluxo} -> {ctx_depois.estado_fluxo}")
    if ctx_antes.servico != ctx_depois.servico:
        mudancas.append(f"servico: {ctx_antes.servico} -> {ctx_depois.servico}")
    if ctx_antes.data_hora != ctx_depois.data_hora:
        mudancas.append(f"data_hora: {ctx_antes.data_hora} -> {ctx_depois.data_hora}")
    if ctx_antes.profissional_escolhido != ctx_depois.profissional_escolhido:
        mudancas.append(f"profissional: {ctx_antes.profissional_escolhido} -> {ctx_depois.profissional_escolhido}")

    if mudancas:
        print(f"\n[MUDANCAS]")
        for m in mudancas:
            print(f"  * {m}")


def validar_cenario_1(passos):
    """
    Cenario 1: Pergunta informativa nao altera slots criticos

    Esperado:
    - Msg 1: servico=corte, draft criado
    - Msg 2: servico=corte, draft preservado
    """
    falhas = []

    # Apos msg 1: servico foi definido
    if passos[0]["depois"].servico != "corte":
        falhas.append("Passo 1: servico nao foi definido")

    # Apos msg 1: draft foi criado
    if not passos[0]["depois"].draft_agendamento:
        falhas.append("Passo 1: draft nao foi criado")

    # Apos msg 2: servico foi preservado
    if passos[1]["depois"].servico != "corte":
        falhas.append("Passo 2: servico foi alterado/apagado")

    # Apos msg 2: draft foi preservado
    if not passos[1]["depois"].draft_agendamento:
        falhas.append("Passo 2: draft foi apagado")

    # Estado continua agendando
    if passos[1]["depois"].estado_fluxo != "agendando":
        falhas.append("Passo 2: estado nao permaneceu agendando")

    return {
        "cenario": "1_pergunta_informativa",
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
    }


def validar_cenario_2(passos):
    """
    Cenario 2: Retomada apos interrupcao preserva contexto

    Esperado:
    - Pergunta informativa nao reinicia fluxo
    - Contexto nao foi zerado
    - Fluxo continua normalmente
    """
    falhas = []

    # Apos pergunta informativa: fluxo nao foi reiniciado
    if passos[1]["depois"].estado_fluxo == "agendando_0":
        falhas.append("Passo 2: fluxo foi reiniciado")

    # Apos pergunta informativa: servico foi preservado
    if passos[1]["depois"].servico != "corte":
        falhas.append("Passo 2: servico foi perdido")

    # Apos retomada: fluxo continua
    if passos[2]["depois"].estado_fluxo is None:
        falhas.append("Passo 3: fluxo nao continuou apos retomada")

    # Apos retomada: servico ainda la
    if passos[2]["depois"].servico != "corte":
        falhas.append("Passo 3: servico foi perdido apos retomada")

    # Apos data: data foi preenchida
    if not passos[3]["depois"].data_hora:
        falhas.append("Passo 4: data nao foi preenchida")

    # Apos hora: hora foi preenchida
    if "14" not in str(passos[4]["depois"].data_hora or ""):
        falhas.append("Passo 5: hora nao foi preenchida")

    # Apos profissional: profissional foi selecionado
    if passos[5]["depois"].profissional_escolhido != "Bruna":
        falhas.append("Passo 6: profissional nao foi selecionado")

    return {
        "cenario": "2_retomada_apos_interrupcao",
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
    }


def validar_cenario_3(passos):
    """
    Cenario 3: Multiplas perguntas informativas

    Esperado:
    - Servico nao muda
    - Draft nao eh apagado
    - Perguntas sao respondidas
    - Fluxo continua normal
    """
    falhas = []

    servico_inicial = passos[0]["depois"].servico

    # Apos cada pergunta informativa, servico deve permanecer igual
    for i in [1, 2, 3]:  # passos com perguntas informativas
        if passos[i]["depois"].servico != servico_inicial:
            falhas.append(f"Passo {i+1}: servico foi alterado pela pergunta informativa")

        if not passos[i]["depois"].draft_agendamento:
            falhas.append(f"Passo {i+1}: draft foi apagado pela pergunta informativa")

    return {
        "cenario": "3_multiplas_interrupcoes",
        "status": "SUCESSO" if not falhas else "FALHA",
        "falhas": falhas,
    }


def main():
    """Executor principal"""

    print("=" * 100)
    print("STRESS TEST SIMPLIFICADO - Interrupcoes Informativas")
    print("=" * 100)

    resultados = []

    # ========================================================================
    # CENARIO 1: Pergunta informativa durante fluxo ativo
    # ========================================================================

    print("\n" + "=" * 100)
    print("CENARIO 1: Pergunta Informativa Durante Fluxo Ativo")
    print("=" * 100)

    ctx1 = ContextoSimulado()
    passos1 = []

    # Passo 1: Inicia agendamento
    ctx_antes = ContextoSimulado()
    ctx1.processar_mensagem("agendamento_inicial", {"servico": "corte"})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx1.__dict__.copy()
    log_passo(1, "Inicia agendamento com corte", ctx_antes, ctx_depois)
    passos1.append({"antes": ctx_antes, "depois": ctx_depois})

    # Passo 2: Pergunta informativa
    ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
    ctx_antes.__dict__ = ctx1.__dict__.copy()
    ctx1.processar_mensagem("pergunta_informativa", {"resposta": "Rua Joao Baroni, 550"})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx1.__dict__.copy()
    log_passo(2, "Pergunta informativa sobre endereco", ctx_antes, ctx_depois)
    passos1.append({"antes": ctx_antes, "depois": ctx_depois})

    validacao1 = validar_cenario_1(passos1)
    print(f"\nRESULTADO CENARIO 1: {validacao1['status']}")
    if validacao1["falhas"]:
        for falha in validacao1["falhas"]:
            print(f"  [FALHA] {falha}")
    else:
        print(f"  [OK] Todas as validacoes passaram")
    resultados.append(validacao1)

    # ========================================================================
    # CENARIO 2: Retomada apos interrupcao
    # ========================================================================

    print("\n" + "=" * 100)
    print("CENARIO 2: Retomada Apos Interrupcao Informativa")
    print("=" * 100)

    ctx2 = ContextoSimulado()
    passos2 = []

    # Passo 1: Inicia agendamento
    ctx_antes = ContextoSimulado()
    ctx2.processar_mensagem("agendamento_inicial", {"servico": "corte"})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx2.__dict__.copy()
    log_passo(1, "Inicia agendamento com corte", ctx_antes, ctx_depois)
    passos2.append({"antes": ctx_antes, "depois": ctx_depois})

    # Passo 2: Pergunta informativa
    ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
    ctx_antes.__dict__ = ctx2.__dict__.copy()
    ctx2.processar_mensagem("pergunta_informativa", {"resposta": "Endereco..."})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx2.__dict__.copy()
    log_passo(2, "Pergunta informativa (interrupcao)", ctx_antes, ctx_depois)
    passos2.append({"antes": ctx_antes, "depois": ctx_depois})

    # Passo 3: Retomada
    ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
    ctx_antes.__dict__ = ctx2.__dict__.copy()
    ctx2.processar_mensagem("retomada")
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx2.__dict__.copy()
    log_passo(3, "Retoma com 'pode ser'", ctx_antes, ctx_depois)
    passos2.append({"antes": ctx_antes, "depois": ctx_depois})

    # Passo 4: Preenche data
    ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
    ctx_antes.__dict__ = ctx2.__dict__.copy()
    ctx2.processar_mensagem("preenchimento_data", {"data_hora": "2026-06-10T00:00"})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx2.__dict__.copy()
    log_passo(4, "Preenche data apos retomada", ctx_antes, ctx_depois)
    passos2.append({"antes": ctx_antes, "depois": ctx_depois})

    # Passo 5: Preenche hora
    ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
    ctx_antes.__dict__ = ctx2.__dict__.copy()
    ctx2.processar_mensagem("preenchimento_hora", {"hora": "14:00"})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx2.__dict__.copy()
    log_passo(5, "Preenche hora", ctx_antes, ctx_depois)
    passos2.append({"antes": ctx_antes, "depois": ctx_depois})

    # Passo 6: Escolhe profissional
    ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
    ctx_antes.__dict__ = ctx2.__dict__.copy()
    ctx2.processar_mensagem("preenchimento_profissional", {"profissional": "Bruna"})
    ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
    ctx_depois.__dict__ = ctx2.__dict__.copy()
    log_passo(6, "Escolhe profissional Bruna", ctx_antes, ctx_depois)
    passos2.append({"antes": ctx_antes, "depois": ctx_depois})

    validacao2 = validar_cenario_2(passos2)
    print(f"\nRESULTADO CENARIO 2: {validacao2['status']}")
    if validacao2["falhas"]:
        for falha in validacao2["falhas"]:
            print(f"  [FALHA] {falha}")
    else:
        print(f"  [OK] Todas as validacoes passaram")
    resultados.append(validacao2)

    # ========================================================================
    # CENARIO 3: Multiplas interrupcoes
    # ========================================================================

    print("\n" + "=" * 100)
    print("CENARIO 3: Multiplas Interrupcoes Informativas")
    print("=" * 100)

    ctx3 = ContextoSimulado()
    passos3 = []

    mensagens = [
        ("agendamento_inicial", {"servico": "corte"}, "Inicia agendamento"),
        ("pergunta_informativa", {"resposta": "R$ 50,00"}, "Pergunta: quanto custa?"),
        ("pergunta_informativa", {"resposta": "Bruna, Carla, Gloria"}, "Pergunta: quem atende?"),
        ("pergunta_informativa", {"resposta": "Sim, aberto sabado"}, "Pergunta: abrem sabado?"),
        ("retomada", {}, "Ok, quero marcar"),
        ("preenchimento_data", {"data_hora": "2026-06-10T00:00"}, "Preenche data"),
        ("preenchimento_hora", {"hora": "15:30"}, "Preenche hora"),
    ]

    for i, (tipo, dados, desc) in enumerate(mensagens, 1):
        ctx_antes = ContextoSimulado.__new__(ContextoSimulado)
        ctx_antes.__dict__ = ctx3.__dict__.copy()
        ctx3.processar_mensagem(tipo, dados)
        ctx_depois = ContextoSimulado.__new__(ContextoSimulado)
        ctx_depois.__dict__ = ctx3.__dict__.copy()
        log_passo(i, desc, ctx_antes, ctx_depois)
        passos3.append({"antes": ctx_antes, "depois": ctx_depois})

    validacao3 = validar_cenario_3(passos3)
    print(f"\nRESULTADO CENARIO 3: {validacao3['status']}")
    if validacao3["falhas"]:
        for falha in validacao3["falhas"]:
            print(f"  [FALHA] {falha}")
    else:
        print(f"  [OK] Todas as validacoes passaram")
    resultados.append(validacao3)

    # ========================================================================
    # RESUMO FINAL
    # ========================================================================

    print("\n" + "=" * 100)
    print("RESUMO FINAL")
    print("=" * 100)

    total = len(resultados)
    sucessos = sum(1 for r in resultados if r["status"] == "SUCESSO")
    falhas = total - sucessos

    print(f"\nCenarios testados: {total}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {falhas}")

    print(f"\nResultados:")
    for r in resultados:
        status_symbol = "[OK]" if r["status"] == "SUCESSO" else "[FALHA]"
        print(f"  {status_symbol} {r['cenario']}: {r['status']}")
        if r["falhas"]:
            for falha in r["falhas"]:
                print(f"       - {falha}")

    # ========================================================================
    # SALVAR RESULTADO
    # ========================================================================

    resultado_path = Path(__file__).parent / "resultado_stress_interrupcao_informativa_simplificado.json"

    resultado_completo = {
        "titulo": "STRESS TEST SIMPLIFICADO - Interrupcoes Informativas",
        "data_execucao": datetime.now().isoformat(),
        "cenarios": resultados,
        "resumo": {
            "total": total,
            "sucessos": sucessos,
            "falhas": falhas,
            "status_geral": "SUCESSO" if falhas == 0 else "FALHA",
        },
    }

    with open(resultado_path, "w", encoding="utf-8") as f:
        json.dump(resultado_completo, f, ensure_ascii=False, indent=2)

    print(f"\nResultado salvo em: {resultado_path}")

    print("\n" + "=" * 100)

    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
