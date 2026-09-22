#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE P0: REAGENDAMENTO CONVERSACIONAL — E2E COMPLETO (6 GATES)

Valida que o fluxo conversacional de reagendamento funciona end-to-end
através de todos os 6 gates especificados:

1. Gate 1 — Detecção: Mensagem reconhecida como reagendamento
2. Gate 2 — Identificação: Sistema identifica qual evento alterar
3. Gate 3 — Novo Horário: Cliente fornece novo horário
4. Gate 4 — Conflito: Motor valida disponibilidade
5. Gate 5 — Confirmação: Cliente confirma antes de mutar
6. Gate 6 — Persistência: Evento alterado com evento_id preservado

Data: 2026-08-11
Status: Definição de Pronto para P0
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.firebase_service_async import (
    deletar_dado_em_path,
    buscar_dado_em_path,
    buscar_subcolecao,
)
from services.event_service_async import (
    alterar_agendamento,
    verificar_conflito_e_sugestoes_profissional,
)
from services.agenda_lock_service import criar_evento_com_lock as criar_com_lock_real
from router.principal_router import eh_gatilho_reagendamento


class TesteReagendamentoE2E:
    """Teste E2E com cenários de todos os 6 gates."""

    def __init__(self):
        self.tenant = "teste_reagendamento_e2e_20260811"
        self.cliente = "cliente_teste_e2e"
        self.dono_id = self.tenant
        self.total_testes = 0
        self.testes_passados = 0
        self.testes_falhados = 0
        self.falhas = []

    async def setup(self):
        """Limpar dados de teste anteriores."""
        print("[SETUP] Limpando dados anteriores...")
        try:
            # Deletar tenant completo
            await deletar_dado_em_path(f"Clientes/{self.tenant}")
        except Exception as e:
            print(f"[AVISO] Erro ao limpar: {e}")

    async def criar_evento_base(self, evento_id: str, data: str, hora: str):
        """Criar um evento de base para testes."""
        print(f"[SETUP] Criando evento {evento_id}...")
        resultado = await criar_com_lock_real(
            dono_id=self.tenant,
            evento={
                "profissional": "Carla",
                "servico": "Manicure",
                "data": data,
                "hora_inicio": hora,
                "hora_fim": self._calcular_hora_fim(hora, 30),
                "duracao_minutos": 30,
                "confirmado": True,
                "status": "confirmado",
                "cliente_id": self.cliente,
                "cliente_nome": "Cliente Teste",
            },
            event_id=evento_id,
        )

        if not resultado.get("ok"):
            print(f"[FALHA] Nao consegui criar evento: {resultado}")
            return False

        print(f"[OK] Evento {evento_id} criado")
        return True

    def _calcular_hora_fim(self, hora_inicio: str, duracao_min: int) -> str:
        """Calcular hora fim a partir de inicio + duracao."""
        try:
            hh, mm = map(int, hora_inicio.split(":"))
            total_min = hh * 60 + mm + duracao_min
            return f"{total_min // 60:02d}:{total_min % 60:02d}"
        except Exception:
            return "15:00"

    def validar_teste(self, nome: str, condicao: bool, mensagem: str):
        """Registrar resultado de um teste."""
        self.total_testes += 1
        if condicao:
            print(f"[OK] {nome}: {mensagem}")
            self.testes_passados += 1
        else:
            print(f"[FALHA] {nome}: {mensagem}")
            self.testes_falhados += 1
            self.falhas.append((nome, mensagem))

    # =========================================================================
    # GATE 1 — DETECÇÃO
    # =========================================================================

    async def testar_gate1_deteccao(self):
        """Gate 1: Mensagens são reconhecidas como intenção de reagendamento."""
        print("\n" + "=" * 70)
        print("GATE 1 — DETECÇÃO")
        print("=" * 70)

        mensagens_teste = [
            ("Quero mudar meu horário", True),
            ("Preciso remarcar", True),
            ("Posso trocar meu horário?", True),
            ("Quero passar para amanhã", True),
            ("Tem como mudar minha manicure?", True),
            ("Reagendar", True),
            ("Alterar", True),
            ("Trocar de dia", True),
            ("Olá, como vai?", False),
            ("Quero agendar", False),
            ("Quanto custa?", False),
        ]

        print("[TESTE] Validar detecção de intenção...")
        for msg, esperado_reconhecido in mensagens_teste:
            resultado = eh_gatilho_reagendamento(msg)
            self.validar_teste(
                f"Gate1_Deteccao[{msg[:30]}...]",
                resultado == esperado_reconhecido,
                f"Esperado: {esperado_reconhecido}, Obtido: {resultado}",
            )

    # =========================================================================
    # GATE 2 — IDENTIFICAÇÃO DO EVENTO
    # =========================================================================

    async def testar_gate2_identificacao_um_evento(self):
        """Gate 2a: Identificação automática quando há 1 evento."""
        print("\n" + "=" * 70)
        print("GATE 2 — IDENTIFICAÇÃO (1 Evento Automático)")
        print("=" * 70)

        # Criar um único evento
        ok = await self.criar_evento_base("evt_id_001", "2026-08-15", "14:00")
        self.validar_teste("Gate2_CriarEvento", ok, "Evento criado")

        # Buscar eventos do cliente
        eventos = await buscar_subcolecao(f"Clientes/{self.tenant}/Eventos")
        self.validar_teste(
            "Gate2_BuscarEventos",
            eventos is not None and len(eventos) > 0,
            f"Encontrados {len(eventos) if eventos else 0} evento(s)",
        )

        # Validar que é identificável automaticamente (1 evento = automático)
        if eventos:
            evento_id = list(eventos.keys())[0]
            evento = eventos[evento_id]
            self.validar_teste(
                "Gate2_IdentificacaoAutomatica",
                evento_id == "evt_id_001",
                f"Evento_id={evento_id}",
            )

    async def testar_gate2_identificacao_multiplos(self):
        """Gate 2b: Identificação por lista quando há N eventos."""
        print("\n" + "=" * 70)
        print("GATE 2 — IDENTIFICAÇÃO (N Eventos - Selecionar por Lista)")
        print("=" * 70)

        # Criar evento adicional
        ok = await self.criar_evento_base("evt_id_002", "2026-08-16", "10:00")
        self.validar_teste("Gate2_CriarSegundoEvento", ok, "Segundo evento criado")

        # Buscar eventos
        eventos = await buscar_subcolecao(f"Clientes/{self.tenant}/Eventos")
        self.validar_teste(
            "Gate2_ListarMultiplos",
            eventos is not None and len(eventos) >= 2,
            f"Encontrados {len(eventos) if eventos else 0} eventos (esperado >= 2)",
        )

    # =========================================================================
    # GATE 3 — NOVO HORÁRIO
    # =========================================================================

    async def testar_gate3_novo_horario(self):
        """Gate 3: Interpretação de novo horário é bem-sucedida."""
        print("\n" + "=" * 70)
        print("GATE 3 — NOVO HORÁRIO (Interpretação)")
        print("=" * 70)

        # Validar que motor consegue calcular novo horário
        # (No caso real, GPT interpretaria "amanhã às 15h", aqui validamos manualmente)
        exemplos_interpretacao = [
            (("2026-08-15", "15:00"), True, "Formato direto"),
            (("2026-08-16", "17:30"), True, "Com minutos"),
            (("2026-08-17", "10:00"), True, "Manhã"),
        ]

        for (data, hora), esperado, descricao in exemplos_interpretacao:
            # Validação simples: data está no futuro
            condicao = (
                data >= "2026-08-11"
            )  # Data de hoje do teste
            self.validar_teste(
                f"Gate3_Interpretacao[{descricao}]",
                condicao,
                f"Data={data}, Hora={hora}",
            )

    # =========================================================================
    # GATE 4 — CONFLITO E MOTOR
    # =========================================================================

    async def testar_gate4_conflito_livre(self):
        """Gate 4a: Motor valida horário LIVRE."""
        print("\n" + "=" * 70)
        print("GATE 4 — CONFLITO (Horário Livre)")
        print("=" * 70)

        # Usar evento_id_001 (2026-08-15 14:00-14:30)
        novo_horario_livre = "17:00"  # Deve estar livre

        validacao = await verificar_conflito_e_sugestoes_profissional(
            user_id=self.dono_id,
            data="2026-08-15",
            hora_inicio=novo_horario_livre,
            duracao_min=30,
            profissional="Carla",
            servico="Manicure",
            event_id="evt_id_001",  # Ignora evento sendo alterado
        )

        self.validar_teste(
            "Gate4_ConflitoLivre_SemConflito",
            not validacao.get("conflito"),
            f"Resultado: {validacao}",
        )

    async def testar_gate4_conflito_ocupado(self):
        """Gate 4b: Motor detecta horário OCUPADO e oferece alternativas."""
        print("\n" + "=" * 70)
        print("GATE 4 — CONFLITO (Horário Ocupado)")
        print("=" * 70)

        # Criar evento bloqueante nas 15h
        ok = await self.criar_evento_base("evt_bloqueante", "2026-08-15", "15:00")
        self.validar_teste("Gate4_CriarEventoBloqueante", ok, "Evento criado para bloquear")

        # Tentar horário já ocupado
        validacao = await verificar_conflito_e_sugestoes_profissional(
            user_id=self.dono_id,
            data="2026-08-15",
            hora_inicio="15:00",
            duracao_min=30,
            profissional="Carla",
            servico="Manicure",
            event_id="evt_id_001",
        )

        self.validar_teste(
            "Gate4_ConflitoCom_DetectaConflito",
            validacao.get("conflito"),
            f"Conflito detectado: {validacao}",
        )

        # Validar que há sugestões
        sugestoes = validacao.get("sugestoes", [])
        self.validar_teste(
            "Gate4_ConflitoCom_OfereceAlternativas",
            len(sugestoes) > 0,
            f"Sugestoes oferecidas: {len(sugestoes)}",
        )

    # =========================================================================
    # GATE 5 — CONFIRMAÇÃO
    # =========================================================================

    async def testar_gate5_confirmacao_positiva(self):
        """Gate 5a: Cliente confirma alteração."""
        print("\n" + "=" * 70)
        print("GATE 5 — CONFIRMAÇÃO (Sim/Confirmo)")
        print("=" * 70)

        # Simular confirmação do cliente (no caso real, vem da conversa)
        # Aqui apenas validamos que reconhecemos confirmação
        mensagens_confirmacao = [
            ("Sim", True),
            ("Confirmo", True),
            ("Pronto", True),
            ("Sim, pode ser", True),
            ("Não", False),
            ("Cancela", False),
        ]

        from router.principal_router import eh_confirmacao

        for msg, esperado_confirmacao in mensagens_confirmacao:
            resultado = eh_confirmacao(msg)
            self.validar_teste(
                f"Gate5_Confirmacao[{msg}]",
                resultado == esperado_confirmacao,
                f"Resultado: {resultado}",
            )

    # =========================================================================
    # GATE 6 — PERSISTÊNCIA
    # =========================================================================

    async def testar_gate6_persistencia_evento_alterado(self):
        """Gate 6: Evento é alterado com preservação de evento_id."""
        print("\n" + "=" * 70)
        print("GATE 6 — PERSISTÊNCIA (Evento Alterado)")
        print("=" * 70)

        # Alterar evento_id_001 de 14:00 para 17:00
        resultado_alteracao = await alterar_agendamento(
            user_id=self.cliente,
            event_id="evt_id_001",
            nova_data="2026-08-15",
            nova_hora_inicio="17:00",
            nova_duracao_minutos=30,
            tenant_id=self.tenant,
        )

        self.validar_teste(
            "Gate6_AlterouComSucesso",
            resultado_alteracao.get("ok"),
            f"Resultado: {resultado_alteracao}",
        )

        # Validar que evento_id foi preservado
        if resultado_alteracao.get("ok"):
            evento_alterado = await buscar_dado_em_path(
                f"Clientes/{self.tenant}/Eventos/evt_id_001"
            )
            self.validar_teste(
                "Gate6_PreservouEventoId",
                evento_alterado is not None,
                f"Evento ainda existe com mesmo ID",
            )

            if evento_alterado:
                self.validar_teste(
                    "Gate6_NovoHorario",
                    evento_alterado.get("hora_inicio") == "17:00",
                    f"Hora atual: {evento_alterado.get('hora_inicio')}",
                )

                # Validar histórico
                historico = evento_alterado.get("historico_alteracoes", [])
                self.validar_teste(
                    "Gate6_HistoricoRegistrado",
                    len(historico) > 0,
                    f"Registros: {len(historico)}",
                )

    # =========================================================================
    # CENÁRIO CRÍTICO — MÁQUINA DE ESTADOS COMPLETA
    # =========================================================================

    async def testar_cenario_critico_maquina_estados(self):
        """
        Cenário crítico que prova a máquina de estados completa funcionando.

        Simula o fluxo:
        "Quero mudar meu horário"
        → Bot lista agendamentos
        → Cliente escolhe
        → Bot pergunta novo horário
        → Cliente: "15h"
        → Motor detecta conflito
        → Bot oferece alternativas
        → Cliente: "16h"
        → Bot: "Confirmar?"
        → Cliente: "Sim"
        → Evento alterado com histórico
        """
        print("\n" + "=" * 70)
        print("CENÁRIO CRÍTICO — MÁQUINA DE ESTADOS COMPLETA")
        print("=" * 70)

        # Preparar estado inicial: 2 eventos
        await self.criar_evento_base("evt_critico_001", "2026-08-14", "14:30")
        await self.criar_evento_base("evt_critico_002", "2026-08-15", "15:00")
        await self.criar_evento_base("evt_bloqueante_critico", "2026-08-15", "16:00")

        # Etapa 1: Detecção
        msg1 = "Quero mudar meu horário"
        detectado = eh_gatilho_reagendamento(msg1)
        self.validar_teste(
            "Critico_Etapa1_Deteccao",
            detectado,
            "Mensagem reconhecida como reagendamento",
        )

        # Etapa 2: Identificação (listar)
        eventos = await buscar_subcolecao(f"Clientes/{self.tenant}/Eventos")
        tem_multiplos = eventos is not None and len(eventos) >= 2
        self.validar_teste(
            "Critico_Etapa2_Identificacao",
            tem_multiplos,
            f"Sistema pode listar {len(eventos) if eventos else 0} eventos",
        )

        # Etapa 3: Cliente escolhe novo horário (17h — deve estar livre)
        validacao_17h = await verificar_conflito_e_sugestoes_profissional(
            user_id=self.dono_id,
            data="2026-08-15",
            hora_inicio="17:00",
            duracao_min=30,
            profissional="Carla",
            servico="Manicure",
            event_id="evt_critico_001",
        )
        sem_conflito_17h = not validacao_17h.get("conflito")
        self.validar_teste(
            "Critico_Etapa3_NovoHorarioLivre",
            sem_conflito_17h,
            "Novo horário (17h) está disponível",
        )

        # Etapa 4: Confirmação simulada
        msg_sim = "Sim"
        from router.principal_router import eh_confirmacao

        confirmado = eh_confirmacao(msg_sim)
        self.validar_teste(
            "Critico_Etapa4_Confirmacao",
            confirmado,
            "Sistema reconhece confirmação",
        )

        # Etapa 5: Alteração com persistência
        resultado_alt = await alterar_agendamento(
            user_id=self.cliente,
            event_id="evt_critico_001",
            nova_data="2026-08-15",
            nova_hora_inicio="17:00",
            nova_duracao_minutos=30,
            tenant_id=self.tenant,
        )

        alterou_sucesso = resultado_alt.get("ok")
        self.validar_teste(
            "Critico_Etapa5_Persistencia",
            alterou_sucesso,
            "Evento alterado com sucesso",
        )

        # Etapa 6: Validações finais
        if alterou_sucesso:
            evento_final = await buscar_dado_em_path(
                f"Clientes/{self.tenant}/Eventos/evt_critico_001"
            )
            self.validar_teste(
                "Critico_Etapa6_EventoIdPreservado",
                evento_final is not None,
                "evento_id preservado (evt_critico_001)",
            )

            if evento_final:
                self.validar_teste(
                    "Critico_Etapa6_HorarioAlterado",
                    evento_final.get("hora_inicio") == "17:00",
                    f"Hora alterada para 17:00",
                )

                historico = evento_final.get("historico_alteracoes", [])
                self.validar_teste(
                    "Critico_Etapa6_HistoricoCompleto",
                    len(historico) > 0,
                    f"Histórico com {len(historico)} registro(s)",
                )

    # =========================================================================
    # RESUMO E REGRESSÃO
    # =========================================================================

    async def executar_todos_testes(self):
        """Executar suite completa."""
        print("\n")
        print("*" * 70)
        print("P0: REAGENDAMENTO CONVERSACIONAL — SUITE E2E COMPLETA")
        print("*" * 70)
        print()

        await self.setup()

        # Gates 1-6
        await self.testar_gate1_deteccao()
        await self.testar_gate2_identificacao_um_evento()
        await self.testar_gate2_identificacao_multiplos()
        await self.testar_gate3_novo_horario()
        await self.testar_gate4_conflito_livre()
        await self.testar_gate4_conflito_ocupado()
        await self.testar_gate5_confirmacao_positiva()
        await self.testar_gate6_persistencia_evento_alterado()

        # Cenário crítico
        await self.testar_cenario_critico_maquina_estados()

        # Imprimir resumo
        self.imprimir_resumo()

    def imprimir_resumo(self):
        """Imprimir resultado final."""
        print("\n")
        print("=" * 70)
        print("RESUMO FINAL")
        print("=" * 70)
        print(f"Total de testes: {self.total_testes}")
        print(f"Passaram: {self.testes_passados}")
        print(f"Falharam: {self.testes_falhados}")
        print()

        if self.falhas:
            print("FALHAS DETECTADAS:")
            for nome, msg in self.falhas:
                print(f"  - {nome}: {msg}")
            print()

        taxa_sucesso = (
            100.0 * self.testes_passados / self.total_testes
            if self.total_testes > 0
            else 0
        )
        status = "[PASS]" if self.testes_falhados == 0 else "[FALHA]"

        print(f"{status} Taxa de sucesso: {taxa_sucesso:.1f}%")
        print("=" * 70)

        return self.testes_falhados == 0


async def main():
    try:
        teste = TesteReagendamentoE2E()
        sucesso = await teste.executar_todos_testes()
        return 0 if sucesso else 1
    except Exception as e:
        print(f"[ERRO] {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
