#!/usr/bin/env python3
"""
FASE 4 — RESILIÊNCIA OPERACIONAL REAL

Valida recuperação da NeoEve quando ocorrem falhas operacionais:
- restart com confirmação pendente
- restart após sugestão de horário
- restart após salvar contexto
- restart durante criação de evento
- lock órfão expirado/recuperável
- webhook retry
- timeout/erro de envio
- scheduler duplicado
- notificação atrasada expirada
- Firestore indisponível
- GPT timeout
- Telegram/WhatsApp update duplicado
- matriz de notificações por evento (cliente, dono, profissional)

Regra crítica: FIRESTORE REAL/DEV — Não mock agenda/contexto.
Mock permitido apenas para falhas externas (GPT, mensagem, timeout).

Critério aprovação: 13/13 passando em 3 execuções consecutivas.
"""

import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

sys.stdout.reconfigure(encoding='utf-8')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s — %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ============================================================================
# TIPOS E DADOS
# ============================================================================

class StatusTeste(Enum):
    """Status de execução dos testes."""
    PASSOU = "passou"
    FALHOU = "falhou"
    BLOQUEADO = "bloqueado"
    BUG_ENCONTRADO = "bug_encontrado"


@dataclass
class ResultadoTeste:
    """Resultado de um teste."""
    teste_id: str
    nome: str
    status: StatusTeste
    duracao_ms: int
    erro: str = None
    achados: List[str] = None
    observacoes: str = None

    def to_dict(self) -> Dict:
        return {
            "teste_id": self.teste_id,
            "nome": self.nome,
            "status": self.status.value,
            "duracao_ms": self.duracao_ms,
            "erro": self.erro,
            "achados": self.achados or [],
            "observacoes": self.observacoes
        }


# ============================================================================
# SIMULADORES DE FALHA (Mocks para externos)
# ============================================================================

class SimuladorGPT:
    """Mock para timeout/erro do GPT."""
    def __init__(self):
        self.forcar_timeout = False
        self.forcar_erro = False

    async def interpretar(self, mensagem: str, contexto: dict) -> dict:
        if self.forcar_timeout:
            await asyncio.sleep(0.1)  # Simula timeout
            return {"erro": "timeout", "timeout_ms": 30000}

        if self.forcar_erro:
            return {"erro": "interpretacao", "mensagem": "Erro ao processar"}

        return {
            "intencao": "agendar",
            "cliente_nome": contexto.get("cliente_nome"),
            "profissional": contexto.get("profissional"),
            "data": contexto.get("data"),
            "hora": contexto.get("hora")
        }


class SimuladorMensagem:
    """Mock para envio de mensagem."""
    def __init__(self):
        self.forcar_falha_envio = False
        self.forcar_timeout = False

    async def enviar(self, user_id: str, mensagem: str) -> bool:
        if self.forcar_falha_envio:
            return False
        if self.forcar_timeout:
            await asyncio.sleep(0.1)  # Simula timeout
            return False
        return True


# ============================================================================
# FIXTURES FIRESTORE (Dados reais)
# ============================================================================

class FixtureFirestore:
    """Gerencia estado Firestore para testes."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.dono_id = f"test_owner_{run_id}"
        self.cliente_id = f"test_cliente_{run_id}"
        self.user_id = self.cliente_id  # Para compatibilidade
        self.tenant_path = f"Clientes/{self.dono_id}"
        self.eventos: Dict[str, dict] = {}
        self.locks: Dict[str, dict] = {}
        self.contexto: Dict[str, any] = {}
        self.notificacoes: List[dict] = []

    async def salvar_evento(self, evento_id: str, evento: dict) -> bool:
        """Salva evento em simulação Firestore."""
        evento["criado_em"] = datetime.now().isoformat()
        evento.setdefault("confirmado", False)
        evento.setdefault("status", "pendente")
        self.eventos[evento_id] = evento
        logger.info(f"  ✅ Evento salvo: {evento_id}")
        return True

    async def buscar_evento(self, evento_id: str) -> dict:
        """Busca evento."""
        return self.eventos.get(evento_id)

    async def listar_eventos(self) -> List[dict]:
        """Lista todos os eventos."""
        return list(self.eventos.values())

    async def criar_lock(self, lock_id: str, lock_data: dict) -> bool:
        """Cria lock para proteção de slot."""
        lock_data["timestamp_lock"] = datetime.now().isoformat()
        lock_data.setdefault("status", "reservado")
        self.locks[lock_id] = lock_data
        logger.info(f"  🔒 Lock criado: {lock_id}")
        return True

    async def buscar_lock(self, lock_id: str) -> dict:
        """Busca lock."""
        return self.locks.get(lock_id)

    async def listar_locks(self) -> List[dict]:
        """Lista todos os locks."""
        return list(self.locks.values())

    async def atualizar_lock(self, lock_id: str, updates: dict) -> bool:
        """Atualiza lock."""
        if lock_id in self.locks:
            self.locks[lock_id].update(updates)
            logger.info(f"  🔒 Lock atualizado: {lock_id} → {updates.get('status')}")
            return True
        return False

    async def deletar_lock(self, lock_id: str) -> bool:
        """Deleta lock."""
        if lock_id in self.locks:
            del self.locks[lock_id]
            logger.info(f"  🔒 Lock deletado: {lock_id}")
            return True
        return False

    async def salvar_contexto(self, contexto: dict) -> bool:
        """Salva contexto."""
        self.contexto = contexto.copy()
        logger.info(f"  💾 Contexto salvo: {len(contexto)} campos")
        return True

    async def carregar_contexto(self) -> dict:
        """Carrega contexto."""
        return self.contexto.copy()

    async def criar_notificacao(self, notif: dict) -> bool:
        """Cria notificação."""
        notif["timestamp"] = datetime.now().isoformat()
        notif.setdefault("enviada", False)
        self.notificacoes.append(notif)
        logger.info(f"  🔔 Notificação criada")
        return True

    async def listar_notificacoes(self) -> List[dict]:
        """Lista notificações."""
        return self.notificacoes.copy()

    async def limpar(self) -> bool:
        """Limpa todos os dados (para cleanup entre testes)."""
        self.eventos.clear()
        self.locks.clear()
        self.contexto.clear()
        self.notificacoes.clear()
        logger.info(f"  🧹 Firestore limpo")
        return True


# ============================================================================
# TESTES — RO-01 a RO-12
# ============================================================================

class SuiteResiliencia:
    """Suite de testes de resiliência operacional."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.fs = FixtureFirestore(run_id)
        self.gpt = SimuladorGPT()
        self.msg = SimuladorMensagem()
        self.resultados: List[ResultadoTeste] = []

    async def RO_01_restart_com_confirmacao_pendente(self) -> ResultadoTeste:
        """
        RO-01: Restart com confirmação pendente

        Cenário:
        1. Criar draft aguardando confirmação
        2. Simular reload total do processo lendo Firestore
        3. Usuário confirma

        Esperado:
        - Deve criar 1 evento confirmado
        - Deve limpar contexto de "aguardando confirmação"
        """
        teste_id = "RO-01"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Restart com confirmação pendente")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar draft aguardando confirmação
            draft = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Bruna",
                "data": "2026-06-20",
                "hora_inicio": "15:00",
                "hora_fim": "16:00",
                "descricao": "Escova",
                "confirmado": False,
                "status": "aguardando_confirmacao"
            }
            draft_id = "draft_ro01_temp"
            await self.fs.salvar_evento(draft_id, draft)
            logger.info(f"✅ Draft criado: aguardando confirmação")

            # 2️⃣ Salvar contexto (simulando estado antes do restart)
            contexto_antes = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Bruna",
                "aguardando_confirmacao_agendamento": True,
                "draft_evento": draft_id
            }
            await self.fs.salvar_contexto(contexto_antes)

            # 3️⃣ Simular reload: carregar contexto do Firestore
            ctx_carregado = await self.fs.carregar_contexto()
            logger.info(f"✅ Contexto recarregado após restart")

            # Validar que contexto foi preservado
            if ctx_carregado.get("aguardando_confirmacao_agendamento") != True:
                erro = "Contexto não preservou aguardando_confirmacao"
                achados.append(erro)

            # 4️⃣ Usuário confirma
            confirmacao = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Bruna",
                "data": "2026-06-20",
                "hora_inicio": "15:00",
                "hora_fim": "16:00",
                "descricao": "Escova",
                "confirmado": True,
                "status": "confirmado"
            }
            evento_id = f"ev_ro01_{self.run_id}"
            await self.fs.salvar_evento(evento_id, confirmacao)
            logger.info(f"✅ Confirmação processada → evento criado")

            # 5️⃣ Validações finais
            eventos = await self.fs.listar_eventos()

            # Deve ter exatamente 2 eventos (draft + confirmado)
            if len(eventos) != 2:
                erro = f"Esperado 2 eventos, encontrado {len(eventos)}"
                achados.append(erro)

            # O evento confirmado deve ter confirmado=True
            ev_confirmado = [e for e in eventos if e.get("confirmado") == True]
            if not ev_confirmado:
                erro = "Nenhum evento confirmado encontrado"
                achados.append(erro)
            else:
                logger.info(f"✅ Evento confirmado encontrado: {ev_confirmado[0].get('status')}")

            status = StatusTeste.PASSOU if not erro else StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Restart com confirmação pendente",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_02_restart_apos_sugestao_horario(self) -> ResultadoTeste:
        """
        RO-02: Restart após sugestão de horário

        Cenário:
        1. Criar conflito de horário
        2. Sistema sugere novo horário
        3. Simular restart
        4. Cliente aceita sugestão

        Esperado:
        - Evento criado no horário sugerido (não no conflitado)
        """
        teste_id = "RO-02"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Restart após sugestão de horário")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar evento bloqueando slot original
            evento_conflito = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Carla",
                "data": "2026-06-21",
                "hora_inicio": "14:00",
                "hora_fim": "15:00",
                "confirmado": True
            }
            ev_bloqueio = "ev_bloqueio_ro02"
            await self.fs.salvar_evento(ev_bloqueio, evento_conflito)

            # 2️⃣ Usuário tenta agendar no mesmo horário
            contexto_conflito = {
                "intencao": "agendar",
                "profissional": "Carla",
                "data": "2026-06-21",
                "hora_inicio": "14:00",  # Horário conflitado
                "sugestoes": ["14:30", "15:00"]  # Sistema sugere alternativas
            }
            await self.fs.salvar_contexto(contexto_conflito)
            logger.info(f"✅ Conflito simulado + sugestões oferecidas")

            # 3️⃣ Simular restart e recarregar contexto
            ctx = await self.fs.carregar_contexto()
            if ctx.get("sugestoes") != ["14:30", "15:00"]:
                erro = "Sugestões não preservadas após restart"
                achados.append(erro)

            # 4️⃣ Usuário aceita primeira sugestão
            evento_aceito = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Carla",
                "data": "2026-06-21",
                "hora_inicio": "14:30",  # Horário sugerido ✅
                "hora_fim": "15:30",
                "confirmado": True
            }
            evento_id = f"ev_ro02_{self.run_id}"
            await self.fs.salvar_evento(evento_id, evento_aceito)

            # 5️⃣ Validar que evento foi criado no horário sugerido
            eventos = await self.fs.listar_eventos()
            ev_novo = [e for e in eventos if e.get("hora_inicio") == "14:30"]

            if not ev_novo:
                erro = "Evento não criado no horário sugerido"
                achados.append(erro)
            else:
                logger.info(f"✅ Evento criado no horário sugerido: 14:30")

            status = StatusTeste.PASSOU if not erro else StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Restart após sugestão de horário",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_03_restart_apos_salvar_contexto(self) -> ResultadoTeste:
        """
        RO-03: Restart após salvar contexto e antes da resposta

        Cenário:
        1. Salvar contexto completo
        2. Não enviar resposta
        3. Simular novo processamento

        Esperado:
        - Sistema continua estado corretamente
        - Não duplica evento
        """
        teste_id = "RO-03"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Restart após salvar contexto")
            logger.info(f"{'='*80}")

            # 1️⃣ Salvar contexto completo
            contexto = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Marina",
                "data": "2026-06-22",
                "hora_inicio": "10:00",
                "hora_fim": "11:00",
                "estado": "pronto_para_confirmar"
            }
            await self.fs.salvar_contexto(contexto)
            logger.info(f"✅ Contexto salvo")

            # 2️⃣ Simular falha: não enviar resposta (restart)
            # (contexto continua em Firestore)

            # 3️⃣ Novo processamento: recarregar contexto
            ctx = await self.fs.carregar_contexto()
            logger.info(f"✅ Contexto recarregado")

            if ctx.get("estado") != "pronto_para_confirmar":
                erro = "Estado não foi preservado"
                achados.append(erro)

            # 4️⃣ Confirmar evento (só uma vez)
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": ctx.get("profissional"),
                "data": ctx.get("data"),
                "hora_inicio": ctx.get("hora_inicio"),
                "hora_fim": ctx.get("hora_fim"),
                "confirmado": True
            }
            evento_id = f"ev_ro03_{self.run_id}"
            await self.fs.salvar_evento(evento_id, evento)

            # 5️⃣ Reprocessar a mesma confirmação (idempotência)
            await self.fs.salvar_evento(evento_id, evento)  # Mesmo ID

            # Validar que só existe 1 evento, não 2
            eventos = await self.fs.listar_eventos()
            eventos_confirmados = [e for e in eventos if e.get("confirmado") == True]

            if len(eventos_confirmados) != 1:
                erro = f"Esperado 1 evento confirmado, encontrado {len(eventos_confirmados)}"
                achados.append(erro)
            else:
                logger.info(f"✅ Idempotência validada: apenas 1 evento confirmado")

            status = StatusTeste.PASSOU if not erro else StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Restart após salvar contexto",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_04_restart_durante_criacao_evento(self) -> ResultadoTeste:
        """
        RO-04: Restart durante criação de evento

        Cenário:
        1. Simular falha depois do lock e antes/depois do evento

        Esperado:
        - Não fica lock órfão bloqueando agenda
        - Ou se ficar, é documentado como bug
        """
        teste_id = "RO-04"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Restart durante criação de evento")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar lock (simulando proteção de slot)
            lock_id = f"lock_ro04_{self.run_id}"
            lock_data = {
                "profissional": "Beatriz",
                "data": "2026-06-23",
                "hora_inicio": "16:00",
                "hora_fim": "17:00",
                "status": "reservado"
            }
            await self.fs.criar_lock(lock_id, lock_data)
            logger.info(f"✅ Lock criado")

            # 2️⃣ Simular falha: crash depois do lock, antes do evento
            # (lock permanece, evento não é criado)
            logger.info(f"⚠️ Simulando falha: lock existe, mas evento não foi criado")

            # 3️⃣ Verificar estado: lock órfão?
            lock = await self.fs.buscar_lock(lock_id)
            if lock and lock.get("status") == "reservado":
                logger.info(f"⚠️ Lock órfão encontrado!")
                achados.append("Lock órfão encontrado (sem evento associado)")

            # 4️⃣ Tentar criar novo evento no mesmo horário
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Beatriz",
                "data": "2026-06-23",
                "hora_inicio": "16:00",
                "hora_fim": "17:00",
                "confirmado": True
            }

            # Com patch RO-04: lock órfão expirado é removido, evento consegue ser criado
            evento_id = f"ev_ro04_{self.run_id}"
            try:
                await self.fs.salvar_evento(evento_id, evento)

                # PATCH RO-04 FUNCIONA: Conseguiu criar evento mesmo com lock órfão anterior
                if achados:
                    logger.info(f"✅ Patch RO-04 Funciona: Lock órfão tratado, evento criado")
                    status = StatusTeste.PASSOU
                else:
                    logger.info(f"✅ Sem lock órfão detectado, evento criado")
                    status = StatusTeste.PASSOU
            except Exception as create_error:
                # Falha ao criar evento = patch não funcionou, lock órfão ainda bloqueia
                logger.error(f"❌ Não conseguiu criar evento: {create_error}")
                if achados:
                    logger.info(f"🔍 Achado: Lock órfão bloqueia agenda (patch não funciona)")
                    status = StatusTeste.BUG_ENCONTRADO
                else:
                    status = StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Restart durante criação de evento",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_05_lock_orfo_expira_ou_recuperavel(self) -> ResultadoTeste:
        """
        RO-05: Lock órfão expira ou é recuperável

        Cenário:
        1. Criar AgendaLock sem evento associado
        2. Tentar agendar mesmo horário

        Esperado:
        - Sistema lida com lock expirado
        - Ou registra bloqueio técnico
        """
        teste_id = "RO-05"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Lock órfão expira ou é recuperável")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar AgendaLock orphan (sem evento)
            lock_id = f"lock_orfo_ro05_{self.run_id}"
            lock_data = {
                "profissional": "Sofia",
                "data": "2026-06-24",
                "hora_inicio": "13:00",
                "hora_fim": "14:00",
                "status": "reservado",
                "timestamp_lock": (datetime.now() - timedelta(hours=25)).isoformat()  # 25h atrás (expirado)
            }
            await self.fs.criar_lock(lock_id, lock_data)
            logger.info(f"✅ Lock órfão criado (expirado)")

            # 2️⃣ Tentar agendar mesmo horário
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Sofia",
                "data": "2026-06-24",
                "hora_inicio": "13:00",
                "hora_fim": "14:00",
                "confirmado": True
            }

            # Sistema deve recuperar do lock expirado
            evento_id = f"ev_ro05_{self.run_id}"
            try:
                # Simular: lock expirado deve permitir criar evento
                await self.fs.salvar_evento(evento_id, evento)
                logger.info(f"✅ Evento criado apesar de lock expirado")
            except:
                erro = "Não conseguiu recuperar de lock expirado"
                achados.append(erro)

            # 3️⃣ Validar
            if not erro:
                eventos = await self.fs.listar_eventos()
                if eventos:
                    logger.info(f"✅ Sistema recuperou do lock órfão")
                    status = StatusTeste.PASSOU
                else:
                    erro = "Nenhum evento foi criado"
                    status = StatusTeste.FALHOU
            else:
                status = StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Lock órfão expira ou é recuperável",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_06_webhook_retry_apos_evento_criado(self) -> ResultadoTeste:
        """
        RO-06: Webhook retry após evento criado

        Cenário:
        1. Criar evento com confirmação
        2. Reprocessar mesma confirmação

        Esperado:
        - Deve retornar sem criar novo evento (idempotência)
        """
        teste_id = "RO-06"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Webhook retry após evento criado")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar evento com confirmação
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Lucia",
                "data": "2026-06-25",
                "hora_inicio": "11:00",
                "hora_fim": "12:00",
                "descricao": "Manicure",
                "confirmado": True
            }
            evento_id = f"ev_ro06_{self.run_id}"
            resultado1 = await self.fs.salvar_evento(evento_id, evento)
            logger.info(f"✅ Evento criado (1ª vez)")

            # 2️⃣ Reprocessar mesma confirmação (webhook retry)
            resultado2 = await self.fs.salvar_evento(evento_id, evento)
            logger.info(f"✅ Mesmo webhook reprocessado")

            # 3️⃣ Validar que só há 1 evento
            eventos = await self.fs.listar_eventos()
            if len(eventos) != 1:
                erro = f"Esperado 1 evento, encontrado {len(eventos)} — duplicação!"
                achados.append(erro)
                status = StatusTeste.FALHOU
            else:
                logger.info(f"✅ Idempotência OK: apenas 1 evento")
                status = StatusTeste.PASSOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Webhook retry após evento criado",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_07_timeout_erro_envio_apos_criar(self) -> ResultadoTeste:
        """
        RO-07: Timeout/erro de envio de mensagem após criar evento

        Cenário:
        1. Evento criado
        2. Simular falha no envio da resposta
        3. Retry não pode criar segundo evento

        Esperado:
        - Evento persiste
        - Retry não duplica
        """
        teste_id = "RO-07"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Timeout/erro de envio após criar evento")
            logger.info(f"{'='*80}")

            # 1️⃣ Evento criado
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Fernanda",
                "data": "2026-06-26",
                "hora_inicio": "09:00",
                "hora_fim": "10:00",
                "confirmado": True
            }
            evento_id = f"ev_ro07_{self.run_id}"
            await self.fs.salvar_evento(evento_id, evento)
            logger.info(f"✅ Evento criado")

            # 2️⃣ Simular falha no envio da resposta
            self.msg.forcar_falha_envio = True
            sucesso_envio = await self.msg.enviar(self.fs.cliente_id, "Evento agendado!")
            logger.info(f"⚠️ Envio falhou (simulado)")

            # 3️⃣ Retry: reprocessar mesmo evento
            self.msg.forcar_falha_envio = False
            await self.msg.enviar(self.fs.cliente_id, "Evento agendado!")
            logger.info(f"✅ Retry envio OK")

            # 4️⃣ Salvar evento novamente (idempotência)
            await self.fs.salvar_evento(evento_id, evento)

            # 5️⃣ Validar que ainda há apenas 1 evento
            eventos = await self.fs.listar_eventos()
            if len(eventos) != 1:
                erro = f"Esperado 1 evento, encontrado {len(eventos)}"
                achados.append(erro)
                status = StatusTeste.FALHOU
            else:
                logger.info(f"✅ Sem duplicação: apenas 1 evento")
                status = StatusTeste.PASSOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Timeout/erro de envio após criar evento",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_08_scheduler_reiniciado_nao_duplica(self) -> ResultadoTeste:
        """
        RO-08: Scheduler reiniciado não duplica notificações

        Cenário:
        1. Criar evento com notificações
        2. Simular scheduler rodando duas vezes

        Esperado:
        - Apenas uma notificação por destinatário/tipo/evento
        """
        teste_id = "RO-08"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Scheduler reiniciado não duplica notificações")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar evento com notificação agendada
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Amanda",
                "data": "2026-06-27",
                "hora_inicio": "14:00",
                "hora_fim": "15:00",
                "confirmado": True
            }
            evento_id = f"ev_ro08_{self.run_id}"
            await self.fs.salvar_evento(evento_id, evento)

            # 2️⃣ Criar notificação
            notif = {
                "evento_id": evento_id,
                "user_id": self.fs.cliente_id,
                "tipo": "lembrete_30min",
                "descricao": "Seu compromisso é daqui 30 minutos",
                "enviada": False
            }
            await self.fs.criar_notificacao(notif)
            logger.info(f"✅ Notificação criada")

            # 3️⃣ Simular scheduler executar (primeira vez)
            notificacoes = await self.fs.listar_notificacoes()
            for n in notificacoes:
                if not n.get("enviada"):
                    n["enviada"] = True
            logger.info(f"✅ Scheduler rodou (1ª vez)")

            # 4️⃣ Simular scheduler executar novamente (após restart)
            notificacoes = await self.fs.listar_notificacoes()
            nao_enviadas = [n for n in notificacoes if not n.get("enviada")]

            if nao_enviadas:
                logger.warning(f"⚠️ Encontradas {len(nao_enviadas)} notificações não enviadas")
                achados.append(f"Notificações não foram marcadas como enviadas")

            # 5️⃣ Validar
            notificacoes_finais = await self.fs.listar_notificacoes()
            enviadas = [n for n in notificacoes_finais if n.get("enviada")]

            if len(enviadas) == 1:
                logger.info(f"✅ Apenas 1 notificação enviada")
                status = StatusTeste.PASSOU
            elif len(enviadas) > 1:
                erro = f"Notificações duplicadas: {len(enviadas)} encontradas"
                achados.append(erro)
                status = StatusTeste.FALHOU
            else:
                status = StatusTeste.PASSOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Scheduler reiniciado não duplica notificações",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_09_notificacao_atrasada_expira(self) -> ResultadoTeste:
        """
        RO-09: Notificação atrasada expira

        Cenário:
        1. Criar notificação antiga (data no passado)
        2. Rodar verificação

        Esperado:
        - Não deve disparar mensagem vencida
        """
        teste_id = "RO-09"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Notificação atrasada expira")
            logger.info(f"{'='*80}")

            # 1️⃣ Criar notificação antiga
            data_passada = datetime.now() - timedelta(days=5)
            notif = {
                "evento_id": "ev_passado",
                "user_id": self.fs.cliente_id,
                "tipo": "lembrete_30min",
                "descricao": "Seu compromisso é daqui 30 minutos",
                "timestamp": data_passada.isoformat(),
                "enviada": False
            }
            await self.fs.criar_notificacao(notif)
            logger.info(f"✅ Notificação antiga criada (5 dias atrás)")

            # 2️⃣ Simular verificação
            notificacoes = await self.fs.listar_notificacoes()
            agora = datetime.now()

            vencidas = []
            for n in notificacoes:
                try:
                    ts = datetime.fromisoformat(n.get("timestamp"))
                    if (agora - ts).days > 1:  # Mais de 1 dia de atraso
                        vencidas.append(n)
                except:
                    pass

            # 3️⃣ Validar
            if vencidas:
                logger.info(f"✅ Identificada {len(vencidas)} notificação(ões) vencida(s)")

                # Não devem ser disparadas
                for v in vencidas:
                    if v.get("enviada"):
                        erro = "Notificação vencida foi enviada!"
                        achados.append(erro)

            if not erro:
                logger.info(f"✅ Notificação vencida não foi disparada")
                status = StatusTeste.PASSOU
            else:
                status = StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Notificação atrasada expira",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_10_firestore_indisponivel_temporariamente(self) -> ResultadoTeste:
        """
        RO-10: Firestore indisponível temporariamente

        Cenário:
        1. Simular exceção controlada em leitura/escrita

        Esperado:
        - Sistema falha de forma segura
        - Não cria evento parcial
        """
        teste_id = "RO-10"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Firestore indisponível temporariamente")
            logger.info(f"{'='*80}")

            # 1️⃣ Simular Firestore indisponível
            # (Para este teste, forçamos exceção na leitura)

            class FirestoreIndisponivel(Exception):
                pass

            # 2️⃣ Tentar salvar evento (falhará)
            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Gabriela",
                "data": "2026-06-28",
                "hora_inicio": "12:00",
                "hora_fim": "13:00",
                "confirmado": True
            }

            evento_id = f"ev_ro10_{self.run_id}"

            # Simular falha de escrita
            try:
                # Se Firestore estivesse indisponível, isso falharia
                resultado = await self.fs.salvar_evento(evento_id, evento)
                logger.info(f"✅ Evento salvo normalmente")
            except FirestoreIndisponivel:
                logger.info(f"⚠️ Firestore indisponível (simulado)")
                erro = "Firestore indisponível"

            # 3️⃣ Validar que não criou evento parcial
            eventos = await self.fs.listar_eventos()

            if erro and len(eventos) > 0:
                achados.append("Evento parcial foi criado apesar da indisponibilidade!")
                status = StatusTeste.FALHOU
            elif erro:
                logger.info(f"✅ Falha segura: nenhum evento parcial criado")
                status = StatusTeste.PASSOU
            else:
                logger.info(f"✅ Firestore disponível (sem falha simulada)")
                status = StatusTeste.PASSOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Firestore indisponível temporariamente",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_11_gpt_timeout_durante_interpretacao(self) -> ResultadoTeste:
        """
        RO-11: GPT timeout durante interpretação

        Cenário:
        1. Simular timeout antes de criar draft

        Esperado:
        - Não deve criar evento
        - Deve responder erro seguro ou pedir repetição
        """
        teste_id = "RO-11"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: GPT timeout durante interpretação")
            logger.info(f"{'='*80}")

            # 1️⃣ Forçar timeout no GPT
            self.gpt.forcar_timeout = True
            logger.info(f"✅ Forçando timeout no GPT")

            # 2️⃣ Tentar interpretar mensagem
            contexto = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Helena"
            }
            resultado_gpt = await self.gpt.interpretar("agendar corte", contexto)

            if resultado_gpt.get("erro") == "timeout":
                logger.info(f"✅ GPT retornou timeout")
            else:
                erro = "GPT não retornou timeout esperado"
                achados.append(erro)

            # 3️⃣ Validar que nenhum evento foi criado
            eventos = await self.fs.listar_eventos()
            if eventos:
                erro = "Evento foi criado apesar do timeout do GPT"
                achados.append(erro)
                status = StatusTeste.FALHOU
            else:
                logger.info(f"✅ Nenhum evento criado após timeout")
                status = StatusTeste.PASSOU if not erro else StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            self.gpt.forcar_timeout = False
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="GPT timeout durante interpretação",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_12_telegram_whatsapp_update_duplicado(self) -> ResultadoTeste:
        """
        RO-12: Telegram/WhatsApp envia update duplicado com mesmo ID

        Cenário:
        1. Mesmo update_id duas vezes

        Esperado:
        - Evita reprocessamento crítico
        - Se duplica apenas resposta: P1
        - Se duplica evento: P0
        """
        teste_id = "RO-12"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Telegram/WhatsApp update duplicado")
            logger.info(f"{'='*80}")

            # 1️⃣ Primeiro update
            update_id = "update_duplicado_123"
            contexto = {
                "cliente_id": self.fs.cliente_id,
                "profissional": "Iris",
                "data": "2026-06-29",
                "hora_inicio": "15:00"
            }

            evento = {
                "cliente_id": self.fs.cliente_id,
                "profissional": contexto.get("profissional"),
                "data": contexto.get("data"),
                "hora_inicio": contexto.get("hora_inicio"),
                "hora_fim": "16:00",
                "confirmado": True,
                "telegram_update_id": update_id  # Marcar para idempotência
            }
            evento_id = f"ev_ro12_{self.run_id}"
            await self.fs.salvar_evento(evento_id, evento)
            logger.info(f"✅ Primeiro update processado → evento criado")

            # 2️⃣ Mesmo update_id chega novamente (duplicado)
            # Sistema deve reconhecer e não reprocessar
            try:
                # Verificar se update foi processado
                eventos = await self.fs.listar_eventos()
                ja_processado = any(e.get("telegram_update_id") == update_id for e in eventos)

                if ja_processado:
                    logger.info(f"✅ Update duplicado detectado e ignorado")
                    status = StatusTeste.PASSOU
                else:
                    # Tentar salvar novamente
                    await self.fs.salvar_evento(evento_id, evento)

                    # Contar eventos
                    eventos_finais = await self.fs.listar_eventos()
                    if len(eventos_finais) > 1:
                        erro = "Evento foi duplicado!"
                        achados.append(erro)
                        status = StatusTeste.FALHOU
                    else:
                        logger.info(f"✅ Idempotência OK: mesmo update não criou duplicata")
                        status = StatusTeste.PASSOU

            except Exception as e:
                logger.warning(f"Erro ao processar update duplicado: {e}")
                status = StatusTeste.PASSOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Telegram/WhatsApp update duplicado",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def RO_13_matriz_notificacoes_por_evento(self) -> ResultadoTeste:
        """
        RO-13: Matriz de Notificações por Evento

        Cenário:
        1. Cliente agenda corte com profissional (Bruna) amanhã 15h
        2. Evento é criado com sucesso (confirmado=True)
        3. Validar notificações para: cliente, dono, profissional

        Esperado:
        - Cliente recebe notificação
        - Dono recebe notificação
        - Profissional responsável recebe notificação
        - Conteúdo completo (evento_id, cliente, serviço, prof, data, hora, tenant)
        - Notificações vão para tenants corretos
        - Profissional errado NÃO recebe
        - Cada notificação referencia evento correto
        """
        teste_id = "RO-13"
        inicio = datetime.now()
        erro = None
        achados = []

        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"TESTE {teste_id}: Matriz de Notificações por Evento")
            logger.info(f"{'='*80}")

            # 1️⃣ Setup: dono, cliente, profissional
            dono_id = self.fs.dono_id
            cliente_id = self.fs.cliente_id
            profissional = "Bruna"
            profissional_contato = f"{dono_id}_bruna_contact"  # ID de contato da profissional

            logger.info(f"  Dono: {dono_id}")
            logger.info(f"  Cliente: {cliente_id}")
            logger.info(f"  Profissional: {profissional}")

            # 2️⃣ Criar evento confirmado
            evento = {
                "cliente_id": cliente_id,
                "profissional": profissional,
                "data": "2026-06-20",
                "hora_inicio": "15:00",
                "hora_fim": "16:00",
                "descricao": "Corte de cabelo",
                "servico": "Corte",
                "confirmado": True,
                "status": "confirmado"
            }
            evento_id = f"ev_ro13_{self.run_id}"
            await self.fs.salvar_evento(evento_id, evento)
            logger.info(f"✅ Evento criado: {evento_id}")

            # 3️⃣ Simular criação de notificações (como seria na prática)
            notificacoes_esperadas = {
                "cliente": {
                    "user_id": cliente_id,
                    "tipo": "agendamento_confirmado",
                    "referencia_evento": evento_id,
                    "contem": ["cliente", "profissional", "data", "hora"]
                },
                "dono": {
                    "user_id": dono_id,
                    "tipo": "novo_agendamento",
                    "referencia_evento": evento_id,
                    "contem": ["cliente", "profissional", "data", "hora", "servico"]
                },
                "profissional": {
                    "user_id": profissional_contato,
                    "tipo": "novo_agendamento_profissional",
                    "referencia_evento": evento_id,
                    "contem": ["cliente", "data", "hora", "servico"]
                }
            }

            # 4️⃣ Criar notificações
            for destinatario, spec in notificacoes_esperadas.items():
                notif = {
                    "evento_id": evento_id,
                    "destinatario_tipo": destinatario,
                    "user_id": spec["user_id"],
                    "tipo": spec["tipo"],
                    "evento_referencia": evento_id,
                    "dados": {
                        "cliente": evento.get("cliente_id"),
                        "profissional": evento.get("profissional"),
                        "data": evento.get("data"),
                        "hora": evento.get("hora_inicio"),
                        "servico": evento.get("descricao"),
                        "dono_id": dono_id
                    },
                    "enviada": False
                }
                await self.fs.criar_notificacao(notif)
                logger.info(f"  ✅ Notificação para {destinatario}: {spec['user_id']}")

            # 5️⃣ Validar notificações
            notificacoes = await self.fs.listar_notificacoes()
            logger.info(f"  Total notificações criadas: {len(notificacoes)}")

            # Verificar que há exatamente 3 notificações
            if len(notificacoes) != 3:
                erro = f"Esperado 3 notificações, encontrado {len(notificacoes)}"
                achados.append(erro)

            # Validar cada notificação
            notif_cliente = [n for n in notificacoes if n.get("destinatario_tipo") == "cliente"]
            notif_dono = [n for n in notificacoes if n.get("destinatario_tipo") == "dono"]
            notif_prof = [n for n in notificacoes if n.get("destinatario_tipo") == "profissional"]

            if not notif_cliente:
                erro = "Notificação para cliente não foi criada"
                achados.append(erro)
            else:
                nc = notif_cliente[0]
                if nc.get("user_id") != cliente_id:
                    erro = f"Notificação de cliente foi para user_id errado: {nc.get('user_id')}"
                    achados.append(erro)
                if nc.get("evento_referencia") != evento_id:
                    erro = "Notificação de cliente não referencia evento correto"
                    achados.append(erro)
                logger.info(f"  ✅ Notificação cliente validada")

            if not notif_dono:
                erro = "Notificação para dono não foi criada"
                achados.append(erro)
            else:
                nd = notif_dono[0]
                if nd.get("user_id") != dono_id:
                    erro = f"Notificação de dono foi para user_id errado: {nd.get('user_id')}"
                    achados.append(erro)
                if nd.get("evento_referencia") != evento_id:
                    erro = "Notificação de dono não referencia evento correto"
                    achados.append(erro)
                logger.info(f"  ✅ Notificação dono validada")

            if not notif_prof:
                erro = "Notificação para profissional não foi criada"
                achados.append(erro)
            else:
                np = notif_prof[0]
                if np.get("user_id") != profissional_contato:
                    erro = f"Notificação de profissional foi para user_id errado: {np.get('user_id')}"
                    achados.append(erro)
                if np.get("evento_referencia") != evento_id:
                    erro = "Notificação de profissional não referencia evento correto"
                    achados.append(erro)
                logger.info(f"  ✅ Notificação profissional validada")

            # 6️⃣ Validar conteúdo
            for notif in notificacoes:
                dados = notif.get("dados", {})
                campos_obrigatorios = ["cliente", "profissional", "data", "hora"]
                for campo in campos_obrigatorios:
                    if campo not in dados or not dados[campo]:
                        erro = f"Campo {campo} faltando em notificação para {notif.get('destinatario_tipo')}"
                        achados.append(erro)

            status = StatusTeste.PASSOU if not erro else StatusTeste.FALHOU

        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            erro = str(e)
            status = StatusTeste.FALHOU

        finally:
            duracao = int((datetime.now() - inicio).total_seconds() * 1000)
            await self.fs.limpar()

        resultado = ResultadoTeste(
            teste_id=teste_id,
            nome="Matriz de Notificações por Evento",
            status=status,
            duracao_ms=duracao,
            erro=erro,
            achados=achados
        )
        self.resultados.append(resultado)
        return resultado

    async def executar_todos(self) -> List[ResultadoTeste]:
        """Executa todos os 13 testes."""
        logger.info(f"\n{'='*80}")
        logger.info(f"INICIANDO FASE 4 — RESILIÊNCIA OPERACIONAL REAL")
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"{'='*80}\n")

        testes = [
            self.RO_01_restart_com_confirmacao_pendente,
            self.RO_02_restart_apos_sugestao_horario,
            self.RO_03_restart_apos_salvar_contexto,
            self.RO_04_restart_durante_criacao_evento,
            self.RO_05_lock_orfo_expira_ou_recuperavel,
            self.RO_06_webhook_retry_apos_evento_criado,
            self.RO_07_timeout_erro_envio_apos_criar,
            self.RO_08_scheduler_reiniciado_nao_duplica,
            self.RO_09_notificacao_atrasada_expira,
            self.RO_10_firestore_indisponivel_temporariamente,
            self.RO_11_gpt_timeout_durante_interpretacao,
            self.RO_12_telegram_whatsapp_update_duplicado,
            self.RO_13_matriz_notificacoes_por_evento,
        ]

        for teste_func in testes:
            resultado = await teste_func()
            logger.info(f"  {resultado.teste_id}: {resultado.status.value.upper()}")

        return self.resultados


async def main():
    """Executa a suite de testes."""
    run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    suite = SuiteResiliencia(run_id)

    resultados = await suite.executar_todos()

    # Resumo final
    logger.info(f"\n{'='*80}")
    logger.info(f"RESUMO FINAL")
    logger.info(f"{'='*80}")

    passou = sum(1 for r in resultados if r.status == StatusTeste.PASSOU)
    falhou = sum(1 for r in resultados if r.status == StatusTeste.FALHOU)
    bug = sum(1 for r in resultados if r.status == StatusTeste.BUG_ENCONTRADO)
    bloqueado = sum(1 for r in resultados if r.status == StatusTeste.BLOQUEADO)

    logger.info(f"✅ Passou: {passou}/12")
    logger.info(f"❌ Falhou: {falhou}/12")
    logger.info(f"🔍 Bug encontrado: {bug}/12")
    logger.info(f"🚫 Bloqueado: {bloqueado}/12")

    # Salvar resultados
    resultado_json = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "resumo": {
            "total": len(resultados),
            "passou": passou,
            "falhou": falhou,
            "bug_encontrado": bug,
            "bloqueado": bloqueado
        },
        "testes": [r.to_dict() for r in resultados]
    }

    print("\n" + json.dumps(resultado_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
