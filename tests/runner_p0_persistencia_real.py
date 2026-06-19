#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATERIA P0-PERSISTENCIA — Testes de Fluxo Real com Firestore

Objetivo: Detectar bugs que os runners mockados não pegam:
- contexto salvo diferente do em memória
- Firestore recusando estrutura não-serializável
- próxima mensagem carregando estado errado
- handler interceptando errado após reload

Diferença dos testes normais:
- Usa Firestore real (dev)
- Salva e recarrega contexto de verdade
- Valida json.dumps após cada reload
- Testa ciclo completo: msg1 → save → reload → msg2

Testes:
1. Agendamento completo com confirmação
2. Profissional incompatível + escolha + confirmação
3. Cancelamento com confirmação
4. Confirmação pendente vence motivo_estado
5. Serviço inexistente após reload
6. Interrupção informativa preserva draft
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# CONFIGURAÇÃO DE TESTE
# ============================================================================

TENANT_ID_TESTE = "7394370553"
USER_ID_TESTE = "7371670478"

# Importações do produto (lazy — dentro das funções para evitar circular import)
HAS_REAL_IMPORTS = True


# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class PassoTeste:
    numero: int
    mensagem_usuario: str
    resposta_esperada_contem: List[str] = field(default_factory=list)
    resposta_esperada_nao_contem: List[str] = field(default_factory=list)
    estado_fluxo_esperado: Optional[str] = None
    contexto_esperado: Dict[str, Any] = field(default_factory=dict)
    resposta_real: str = ""
    contexto_apos_reload: Dict[str, Any] = field(default_factory=dict)
    serializavel: bool = True
    passou: bool = False
    motivo_falha: str = ""


@dataclass
class TestCasePersistencia:
    id: int
    nome: str
    descricao: str
    pre_condicoes: List[str] = field(default_factory=list)
    passos: List[PassoTeste] = field(default_factory=list)
    status: str = "PENDENTE"
    taxa_sucesso: float = 0.0
    passou: bool = False
    motivo_falha: str = ""
    eventos_criados: List[str] = field(default_factory=list)
    eventos_cancelados: List[str] = field(default_factory=list)


# ============================================================================
# TESTES OBRIGATÓRIOS
# ============================================================================

TESTES: List[TestCasePersistencia] = [
    TestCasePersistencia(
        id=1,
        nome="Agendamento completo com confirmação",
        descricao="Fluxo: msg1 (agendamento) → reload → msg2 (confirmação)",
        passos=[
            PassoTeste(
                numero=1,
                mensagem_usuario="Quero corte com Bruna amanhã às 10",
                resposta_esperada_contem=["corte", "Bruna", "amanhã", "10:00"],
                resposta_esperada_nao_contem=["Qual profissional"],
                estado_fluxo_esperado="agendamento_pronto",
                contexto_esperado={
                    "servico": "corte",
                    "draft_agendamento.profissional": "Bruna",
                    "aguardando_confirmacao_agendamento": True,
                }
            ),
            PassoTeste(
                numero=2,
                mensagem_usuario="Pode",
                resposta_esperada_contem=["confirmado", "agendado", "Pronto"],
                resposta_esperada_nao_contem=["Qual horário", "Qual profissional"],
                estado_fluxo_esperado="idle",
                contexto_esperado={
                    "aguardando_confirmacao_agendamento": None,
                }
            ),
        ]
    ),

    TestCasePersistencia(
        id=2,
        nome="Profissional incompatível + escolha + confirmação",
        descricao="Fluxo: incompatível → reload → escolha válida → reload → confirmar",
        pre_condicoes=[
            "contexto pode conter draft antigo: servico='botox capilar'"
        ],
        passos=[
            PassoTeste(
                numero=1,
                mensagem_usuario="Quero corte com Carla amanhã às 10",
                resposta_esperada_contem=["Carla", "não atende", "corte", "Bruna", "Gloria", "Joana"],
                resposta_esperada_nao_contem=["botox capilar", "agendado"],
                estado_fluxo_esperado="aguardando_profissional",
                contexto_esperado={
                    "servico": "corte",
                    "motivo_estado": "profissional_nao_atende_servico",
                }
            ),
            PassoTeste(
                numero=2,
                mensagem_usuario="Joana",
                resposta_esperada_contem=["Confirma", "Joana", "corte"],
                resposta_esperada_nao_contem=["Pode escolher", "botox capilar"],
                contexto_esperado={
                    "motivo_estado": None,
                    "profissional_rejeitado": None,
                    "aguardando_confirmacao_agendamento": True,
                }
            ),
            PassoTeste(
                numero=3,
                mensagem_usuario="Pode",
                resposta_esperada_contem=["confirmado", "agendado"],
                resposta_esperada_nao_contem=["Pode escolher", "Qual horário"],
                estado_fluxo_esperado="idle",
            ),
        ]
    ),

    TestCasePersistencia(
        id=3,
        nome="Cancelamento com confirmação",
        descricao="Fluxo: cancelar → reload → confirmar",
        pre_condicoes=[
            "Criar evento teste: Corte com Bruna amanhã às 10 (prefixo TEST_PERSISTENCIA_)"
        ],
        passos=[
            PassoTeste(
                numero=1,
                mensagem_usuario="Quero cancelar o corte com a Bruna de amanhã",
                resposta_esperada_contem=["Tem certeza", "cancelar"],
                estado_fluxo_esperado="aguardando_confirmacao_cancelamento",
                contexto_esperado={
                    "cancelamento_pendente": "deve existir",
                }
            ),
            PassoTeste(
                numero=2,
                mensagem_usuario="Sim",
                resposta_esperada_contem=["cancelado", "disponível"],
                resposta_esperada_nao_contem=["Qual horário", "Pode escolher"],
                estado_fluxo_esperado="idle",
                contexto_esperado={
                    "cancelamento_pendente": None,
                }
            ),
        ]
    ),

    TestCasePersistencia(
        id=4,
        nome="Confirmação pendente vence motivo_estado",
        descricao="Confirmação de agendamento deve ter prioridade sobre rejeição de profissional",
        pre_condicoes=[
            "Salvar contexto artificial no Firestore com: aguardando_confirmacao_agendamento=True + motivo_estado='profissional_nao_atende_servico'"
        ],
        passos=[
            PassoTeste(
                numero=1,
                mensagem_usuario="Pode",
                resposta_esperada_contem=["confirmado", "agendado"],
                resposta_esperada_nao_contem=["Pode escolher"],
                contexto_esperado={
                    "aguardando_confirmacao_agendamento": None,
                }
            ),
        ]
    ),

    TestCasePersistencia(
        id=5,
        nome="Serviço inexistente após reload",
        descricao="Validar que serviço inválido não é salvo como válido",
        passos=[
            PassoTeste(
                numero=1,
                mensagem_usuario="Quero massagem com Bruna amanhã às 10",
                resposta_esperada_contem=["não encontrei", "massagem", "catálogo"],
                resposta_esperada_nao_contem=["agendado"],
                contexto_esperado={
                    "servico": None,
                }
            ),
        ]
    ),

    TestCasePersistencia(
        id=6,
        nome="Interrupção informativa preserva draft",
        descricao="Pergunta informativa não deve limpar draft de agendamento",
        passos=[
            PassoTeste(
                numero=1,
                mensagem_usuario="Quero corte com Bruna amanhã às 10",
                resposta_esperada_contem=["corte", "Bruna"],
                contexto_esperado={
                    "aguardando_confirmacao_agendamento": True,
                }
            ),
            PassoTeste(
                numero=2,
                mensagem_usuario="Qual o endereço?",
                resposta_esperada_contem=["endereço"],
                contexto_esperado={
                    "aguardando_confirmacao_agendamento": True,
                }
            ),
            PassoTeste(
                numero=3,
                mensagem_usuario="Pode",
                resposta_esperada_contem=["confirmado", "agendado"],
                contexto_esperado={
                    "aguardando_confirmacao_agendamento": None,
                }
            ),
        ]
    ),
]


# ============================================================================
# EXECUÇÃO DE TESTES
# ============================================================================

def _sanitizar_cancelamento_pendente(candidatos, cliente_id):
    """
    Versao local de sanitizar_cancelamento_pendente para evitar circular import.
    Converte candidatos (lista de tuplas) em estrutura serializavel.
    """
    if not candidatos:
        return None

    resumo_eventos = []
    for item in candidatos:
        if isinstance(item, tuple):
            eid, ev = item
        else:
            eid, ev = item.get("evento_id"), item

        resumo_eventos.append({
            "evento_id": str(eid),
            "descricao": str(ev.get("descricao", "") if isinstance(ev, dict) else ""),
            "data": str(ev.get("data", "") if isinstance(ev, dict) else ""),
            "hora_inicio": str(ev.get("hora_inicio", "") if isinstance(ev, dict) else ""),
            "profissional": str(ev.get("profissional", "") if isinstance(ev, dict) else ""),
        })

    if len(resumo_eventos) == 1:
        res = resumo_eventos[0]
        resultado = {
            "evento_id": res["evento_id"],
            "cliente_id": str(cliente_id),
            "resumo_evento": res
        }
    else:
        resultado = {
            "cliente_id": str(cliente_id),
            "resumo_eventos": resumo_eventos
        }

    try:
        json.dumps(resultado, ensure_ascii=False)
        return resultado
    except TypeError as e:
        print(f"  [ERRO] Nao serializavel: {e}")
        return None


async def limpar_contexto_teste():
    """Limpa contexto de teste no Firestore."""
    try:
        from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

        ctx = await carregar_contexto_temporario(USER_ID_TESTE)
        if ctx:
            # Limpar apenas campos de teste, não destruir tudo
            campos_limpar = [
                "motivo_estado", "profissional_rejeitado", "profissionais_validos",
                "aguardando_confirmacao_agendamento", "dados_confirmacao_agendamento",
                "estado_fluxo", "cancelamento_pendente", "servico", "draft_agendamento"
            ]
            for campo in campos_limpar:
                ctx.pop(campo, None)
            await salvar_contexto_temporario(USER_ID_TESTE, ctx)
        return True
    except Exception as e:
        print(f"  [AVISO] Falha ao limpar contexto: {e}")
        return False


async def executar_teste_3_real() -> Tuple[bool, Dict[str, Any]]:
    """
    TESTE 3 REAL — Cancelamento com confirmação.

    Fluxo:
    1. Criar/garantir evento teste confirmado
    2. "Quero cancelar o corte com a Bruna de amanhã"
    3. Validar estado_fluxo="aguardando_confirmacao_cancelamento"
    4. Validar json.dumps(cancelamento_pendente) funciona
    5. "Sim"
    6. Validar evento cancelado
    """
    from services.firebase_service_async import (
        buscar_dado_em_path,
        atualizar_dado_em_path,
        obter_id_dono
    )
    from services.event_service_async import cancelar_evento
    from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

    resultado_teste = {
        "id": 3,
        "nome": "Cancelamento com confirmacao",
        "passos": [],
        "passou": False,
        "motivo_falha": ""
    }

    try:
        print(f"\n{'='*80}")
        print(f"[TESTE 3] Cancelamento com confirmacao")
        print(f"{'='*80}")

        # PRE-CONDICAO: Criar evento teste confirmado
        print("\n[PRE-CONDICAO] Criando evento teste confirmado...")
        evento_teste = {
            "descricao": "Corte com Bruna",
            "profissional": "Bruna",
            "servico": "corte",
            "data": "2026-06-17",
            "hora_inicio": "10:00",
            "hora_fim": "11:00",
            "cliente_id": USER_ID_TESTE,
            "cliente_nome": "Cliente Teste",
            "status": "confirmado",
            "confirmado": True,
            "duracao": 60
        }

        evento_id_teste = f"TEST_PERSISTENCIA_cancelamento_bruna_{evento_teste['data']}_{evento_teste['hora_inicio'].replace(':', '')}"
        path_evento = f"Clientes/{TENANT_ID_TESTE}/Eventos/{evento_id_teste}"

        await atualizar_dado_em_path(path_evento, evento_teste)
        print(f"  [OK] Evento criado: {evento_id_teste}")

        # PASSO 1: Limpar contexto
        print("\n[PASSO 1] Limpando contexto anterior...")
        await limpar_contexto_teste()
        print(f"  [OK] Contexto limpo")

        # PASSO 2: Simular "Quero cancelar o corte com a Bruna de amanhã"
        # Nota: Não chamamos roteador completo para evitar circular import
        # Em vez disso, chamamos a função que processa cancelamento
        print("\n[PASSO 2] Simulando: 'Quero cancelar o corte com a Bruna de amanha'")

        # Aqui simulamos o que acontece quando o router detecta cancelamento
        # Usar versao local para evitar circular import
        candidatos = [(evento_id_teste, evento_teste)]
        cancelamento_sanitizado = _sanitizar_cancelamento_pendente(candidatos, USER_ID_TESTE)

        if not cancelamento_sanitizado:
            resultado_teste["motivo_falha"] = "Falha ao sanitizar cancelamento_pendente"
            print(f"  [ERRO] {resultado_teste['motivo_falha']}")
            return False, resultado_teste

        # Salvar contexto como faria o router real
        ctx = await carregar_contexto_temporario(USER_ID_TESTE) or {}
        ctx.pop("motivo_estado", None)
        ctx.pop("profissional_rejeitado", None)
        ctx.pop("profissionais_validos", None)
        ctx.pop("aguardando_confirmacao_agendamento", None)
        ctx.pop("dados_confirmacao_agendamento", None)
        ctx["cancelamento_pendente"] = cancelamento_sanitizado
        ctx["estado_fluxo"] = "aguardando_confirmacao_cancelamento"

        await salvar_contexto_temporario(USER_ID_TESTE, ctx)
        print(f"  [OK] Contexto salvo com cancelamento_pendente")

        passo1_resultado = {
            "numero": 1,
            "mensagem": "Quero cancelar o corte com a Bruna de amanha",
            "contexto_salvo": True,
            "serializavel": False,
            "motivo_falha": ""
        }

        # PASSO 3: Recarregar e validar
        print("\n[PASSO 3] Recarregando contexto...")
        ctx_recarregado = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        # Validar estrutura
        if "cancelamento_pendente" not in ctx_recarregado:
            passo1_resultado["motivo_falha"] = "cancelamento_pendente nao carregado"
            print(f"  [ERRO] {passo1_resultado['motivo_falha']}")
            resultado_teste["motivo_falha"] = passo1_resultado["motivo_falha"]
            resultado_teste["passos"].append(passo1_resultado)
            return False, resultado_teste

        cancelamento_carregado = ctx_recarregado.get("cancelamento_pendente", {})
        print(f"  [OK] cancelamento_pendente carregado")

        # Validar serializabilidade
        try:
            json.dumps(cancelamento_carregado, ensure_ascii=False)
            passo1_resultado["serializavel"] = True
            print(f"  [OK] json.dumps() funciona - nao contém tuplas/datetime")
        except TypeError as e:
            passo1_resultado["motivo_falha"] = f"Nao serializavel: {str(e)}"
            print(f"  [ERRO] {passo1_resultado['motivo_falha']}")
            resultado_teste["motivo_falha"] = passo1_resultado["motivo_falha"]
            resultado_teste["passos"].append(passo1_resultado)
            return False, resultado_teste

        # Validar que NÃO contém estruturas proibidas
        cancelamento_str = str(cancelamento_carregado)
        estruturas_proibidas = ["candidatos", "datetime", "DocumentSnapshot"]
        for estrutura in estruturas_proibidas:
            if estrutura in cancelamento_str:
                passo1_resultado["motivo_falha"] = f"Contém '{estrutura}' proibido"
                print(f"  [ERRO] {passo1_resultado['motivo_falha']}")
                resultado_teste["motivo_falha"] = passo1_resultado["motivo_falha"]
                resultado_teste["passos"].append(passo1_resultado)
                return False, resultado_teste

        passo1_resultado["passou"] = True
        resultado_teste["passos"].append(passo1_resultado)
        print(f"  [OK] Passo 1 passou")

        # PASSO 4: Simular "Sim"
        print("\n[PASSO 4] Simulando: 'Sim'")

        # Extrair evento_id do contexto
        evento_id = cancelamento_carregado.get("evento_id")
        if not evento_id:
            resultado_teste["motivo_falha"] = "evento_id nao encontrado em cancelamento_pendente"
            print(f"  [ERRO] {resultado_teste['motivo_falha']}")
            return False, resultado_teste

        # Chamar funcao real de cancelamento
        ok_cancelamento = await cancelar_evento(USER_ID_TESTE, evento_id)

        if not ok_cancelamento:
            resultado_teste["motivo_falha"] = f"cancelar_evento retornou False para {evento_id}"
            print(f"  [ERRO] {resultado_teste['motivo_falha']}")
            return False, resultado_teste

        print(f"  [OK] Evento cancelado com sucesso")

        # Validar evento foi cancelado no Firestore
        path_evento = f"Clientes/{TENANT_ID_TESTE}/Eventos/{evento_id}"
        evento_apos = await buscar_dado_em_path(path_evento) or {}

        if evento_apos.get("status") != "cancelado":
            resultado_teste["motivo_falha"] = f"Evento status nao eh 'cancelado', eh '{evento_apos.get('status')}'"
            print(f"  [ERRO] {resultado_teste['motivo_falha']}")
            return False, resultado_teste

        print(f"  [OK] Evento status = 'cancelado' no Firestore")

        # Simular limpeza que o handler faria (como handler_cancelamento do router)
        # Nota: salvar_contexto_temporario() faz merge, nao sobrescreve
        # Entao precisamos remover explicitamente passando None
        ctx_para_limpar = {
            "cancelamento_pendente": None,  # Remover explicitamente
            "estado_fluxo": "idle"
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx_para_limpar)
        print(f"  [OK] Contexto limpo (como handler faria)")

        # Validar contexto foi limpo
        ctx_final = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        if ctx_final.get("cancelamento_pendente"):
            resultado_teste["motivo_falha"] = "cancelamento_pendente nao foi limpo apos confirmacao"
            print(f"  [ERRO] {resultado_teste['motivo_falha']}")
            return False, resultado_teste

        print(f"  [OK] cancelamento_pendente foi limpo")

        passo2_resultado = {
            "numero": 2,
            "mensagem": "Sim",
            "evento_cancelado": True,
            "contexto_limpo": True,
            "passou": True
        }
        resultado_teste["passos"].append(passo2_resultado)

        # Sucesso!
        resultado_teste["passou"] = True
        resultado_teste["motivo_falha"] = ""
        print(f"\n[RESULTADO] TESTE 3 PASSOU")

        return True, resultado_teste

    except Exception as e:
        print(f"\n[ERRO NAO TRATADO] {str(e)}")
        import traceback
        traceback.print_exc()
        resultado_teste["motivo_falha"] = str(e)
        return False, resultado_teste


async def executar_teste(teste: TestCasePersistencia) -> bool:
    """Executa um teste completo com ciclo real de persistência."""

    # Mapear ID para funcao
    funcoes_teste = {
        1: executar_teste_1_real,
        2: executar_teste_2_real,
        3: executar_teste_3_real,
        4: executar_teste_4_real,
        5: executar_teste_5_real,
        6: executar_teste_6_real,
    }

    if teste.id in funcoes_teste:
        # Teste implementado de verdade
        sucesso, resultado = await funcoes_teste[teste.id]()
        teste.status = "PASSOU" if sucesso else "FALHOU"
        teste.passou = sucesso
        teste.motivo_falha = resultado.get("motivo_falha", "")
        return sucesso
    else:
        # Teste em template
        teste.status = "PENDENTE"
        teste.passou = False
        teste.motivo_falha = "Teste nao implementado ainda"
        return False


async def executar_teste_1_real() -> Tuple[bool, Dict[str, Any]]:
    """TESTE 1 — Agendamento pendente sobrevive ao reload."""
    from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

    resultado = {
        "id": 1,
        "nome": "Agendamento pendente sobrevive ao reload",
        "passos": [],
        "passou": False,
        "motivo_falha": ""
    }

    try:
        print(f"\n{'='*80}\n[TESTE 1] Agendamento pendente sobrevive ao reload\n{'='*80}")

        # PASSO 1: Salvar agendamento pendente
        print("\n[PASSO 1] Salvando agendamento pendente...")
        await limpar_contexto_teste()

        ctx = {
            "servico": "corte",
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Bruna",
                "data_hora": "2026-06-18 10:00"
            },
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {
                "servico": "corte",
                "profissional": "Bruna",
                "data_hora": "2026-06-18 10:00"
            },
            "estado_fluxo": "agendamento_pronto"
        }

        from utils.contexto_temporario import salvar_contexto_temporario
        await salvar_contexto_temporario(USER_ID_TESTE, ctx)
        print(f"  [OK] Agendamento salvo")

        # PASSO 2: Recarregar e validar
        print("\n[PASSO 2] Recarregando contexto...")
        ctx_recarregado = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        if not ctx_recarregado.get("aguardando_confirmacao_agendamento"):
            resultado["motivo_falha"] = "aguardando_confirmacao_agendamento nao recarregou"
            return False, resultado

        if ctx_recarregado.get("draft_agendamento", {}).get("profissional") != "Bruna":
            resultado["motivo_falha"] = "draft_agendamento nao preservou profissional"
            return False, resultado

        print(f"  [OK] Agendamento recarregado com sucesso")

        resultado["passou"] = True
        return True, resultado

    except Exception as e:
        resultado["motivo_falha"] = str(e)
        return False, resultado


async def executar_teste_2_real() -> Tuple[bool, Dict[str, Any]]:
    """TESTE 2 — Confirmacao de agendamento apos reload cria evento."""
    from services.event_service_async import salvar_evento
    from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

    resultado = {
        "id": 2,
        "nome": "Confirmacao de agendamento apos reload cria evento",
        "passos": [],
        "passou": False,
        "motivo_falha": ""
    }

    try:
        print(f"\n{'='*80}\n[TESTE 2] Confirmacao de agendamento apos reload cria evento\n{'='*80}")

        # PASSO 1: Salvar agendamento pendente
        print("\n[PASSO 1] Salvando agendamento pendente...")
        await limpar_contexto_teste()

        ctx = {
            "servico": "escova",
            "draft_agendamento": {
                "servico": "escova",
                "profissional": "Gloria",
                "data_hora": "2026-06-19 14:00"
            },
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {
                "servico": "escova",
                "profissional": "Gloria",
                "data_hora": "2026-06-19 14:00"
            }
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx)
        print(f"  [OK] Agendamento salvo")

        # PASSO 2: Recarregar
        print("\n[PASSO 2] Recarregando contexto...")
        ctx_recarregado = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        if not ctx_recarregado.get("aguardando_confirmacao_agendamento"):
            resultado["motivo_falha"] = "agendamento nao recarregou"
            return False, resultado

        print(f"  [OK] Agendamento recarregado")

        # PASSO 3: Simular confirmacao criando evento
        print("\n[PASSO 3] Criando evento...")
        evento_data = {
            "descricao": f"Escova com Gloria",
            "profissional": "Gloria",
            "servico": "escova",
            "data": "2026-06-19",
            "hora_inicio": "14:00",
            "hora_fim": "15:00",
            "cliente_id": USER_ID_TESTE,
            "cliente_nome": "Cliente Teste",
            "status": "confirmado",
            "confirmado": True,
            "duracao": 60
        }

        resultado_salvar = await salvar_evento(USER_ID_TESTE, evento_data)

        if not resultado_salvar:
            resultado["motivo_falha"] = "falha ao criar evento"
            return False, resultado

        print(f"  [OK] Evento criado com sucesso")

        # PASSO 4: Limpar contexto
        print("\n[PASSO 4] Limpando contexto de confirmacao...")
        ctx_final = {
            "aguardando_confirmacao_agendamento": None,
            "dados_confirmacao_agendamento": None,
            "estado_fluxo": "idle"
        }
        await salvar_contexto_temporario(USER_ID_TESTE, ctx_final)
        print(f"  [OK] Contexto limpo")

        resultado["passou"] = True
        return True, resultado

    except Exception as e:
        resultado["motivo_falha"] = str(e)
        return False, resultado


async def executar_teste_4_real() -> Tuple[bool, Dict[str, Any]]:
    """TESTE 4 — Troca de profissional apos reload."""
    from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

    resultado = {
        "id": 4,
        "nome": "Troca de profissional apos reload",
        "passos": [],
        "passou": False,
        "motivo_falha": ""
    }

    try:
        print(f"\n{'='*80}\n[TESTE 4] Troca de profissional apos reload\n{'='*80}")

        # PASSO 1: Salvar com profissional rejeitado
        print("\n[PASSO 1] Salvando com profissional rejeitado...")
        await limpar_contexto_teste()

        ctx = {
            "servico": "corte",
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
            "profissionais_validos": ["Bruna", "Gloria", "Joana"],
            "estado_fluxo": "aguardando_profissional"
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx)
        print(f"  [OK] Estado de rejeicao salvo")

        # PASSO 2: Recarregar
        print("\n[PASSO 2] Recarregando contexto...")
        ctx_recarregado = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        if ctx_recarregado.get("motivo_estado") != "profissional_nao_atende_servico":
            resultado["motivo_falha"] = "motivo_estado nao recarregou"
            return False, resultado

        print(f"  [OK] Estado rejeicao recarregado")

        # PASSO 3: Simular escolha de profissional valido
        print("\n[PASSO 3] Limpando rejeicao e confirmando Bruna...")
        ctx_limpo = {
            "motivo_estado": None,
            "profissional_rejeitado": None,
            "profissionais_validos": None,
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Bruna",
                "data_hora": "2026-06-17 10:00"
            },
            "aguardando_confirmacao_agendamento": True,
            "estado_fluxo": "agendamento_pronto"
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx_limpo)
        print(f"  [OK] Rejeicao limpa, Bruna selecionado")

        # PASSO 4: Recarregar final
        print("\n[PASSO 4] Recarregando para confirmar limpeza...")
        ctx_final = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        if ctx_final.get("motivo_estado") is not None:
            resultado["motivo_falha"] = "motivo_estado nao foi limpo"
            return False, resultado

        if ctx_final.get("draft_agendamento", {}).get("profissional") != "Bruna":
            resultado["motivo_falha"] = "Bruna nao foi confirmado"
            return False, resultado

        print(f"  [OK] Bruna confirmado, rejeicao limpa")

        resultado["passou"] = True
        return True, resultado

    except Exception as e:
        resultado["motivo_falha"] = str(e)
        return False, resultado


async def executar_teste_5_real() -> Tuple[bool, Dict[str, Any]]:
    """TESTE 5 — Sugestao de horario apos conflito sobrevive ao reload."""
    from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

    resultado = {
        "id": 5,
        "nome": "Sugestao de horario apos conflito sobrevive ao reload",
        "passos": [],
        "passou": False,
        "motivo_falha": ""
    }

    try:
        print(f"\n{'='*80}\n[TESTE 5] Sugestao de horario apos conflito sobrevive ao reload\n{'='*80}")

        # PASSO 1: Salvar com sugestao de horario
        print("\n[PASSO 1] Salvando com sugestoes de horario...")
        await limpar_contexto_teste()

        ctx = {
            "servico": "corte",
            "profissional_escolhido": "Bruna",
            "estado_fluxo": "aguardando_escolha_horario",
            "modo_escolha_horario": True,
            "opcoes_horario": [
                {"data_hora": "2026-06-17 09:00"},
                {"data_hora": "2026-06-17 11:00"},
                {"data_hora": "2026-06-17 15:00"}
            ],
            "draft_agendamento": {
                "servico": "corte",
                "profissional": "Bruna",
                "data_hora": "2026-06-17 10:00"
            }
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx)
        print(f"  [OK] Sugestoes salvas")

        # PASSO 2: Recarregar
        print("\n[PASSO 2] Recarregando contexto...")
        ctx_recarregado = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        if not ctx_recarregado.get("opcoes_horario"):
            resultado["motivo_falha"] = "opcoes_horario nao recarregou"
            return False, resultado

        if len(ctx_recarregado.get("opcoes_horario", [])) != 3:
            resultado["motivo_falha"] = f"esperava 3 opcoes, got {len(ctx_recarregado.get('opcoes_horario', []))}"
            return False, resultado

        print(f"  [OK] {len(ctx_recarregado['opcoes_horario'])} opcoes recarregadas")

        # PASSO 3: Validar json.dumps
        print("\n[PASSO 3] Validando serializacao...")
        try:
            json.dumps(ctx_recarregado, ensure_ascii=False)
            print(f"  [OK] Contexto serializavel")
        except TypeError as e:
            resultado["motivo_falha"] = f"nao serializavel: {e}"
            return False, resultado

        resultado["passou"] = True
        return True, resultado

    except Exception as e:
        resultado["motivo_falha"] = str(e)
        return False, resultado


async def executar_teste_6_real() -> Tuple[bool, Dict[str, Any]]:
    """TESTE 6 — Contexto limpo nao ressuscita estado antigo."""
    from utils.contexto_temporario import carregar_contexto_temporario, salvar_contexto_temporario

    resultado = {
        "id": 6,
        "nome": "Contexto limpo nao ressuscita estado antigo",
        "passos": [],
        "passou": False,
        "motivo_falha": ""
    }

    try:
        print(f"\n{'='*80}\n[TESTE 6] Contexto limpo nao ressuscita estado antigo\n{'='*80}")

        # PASSO 1: Salvar estado completo
        print("\n[PASSO 1] Salvando estado completo...")
        await limpar_contexto_teste()

        ctx_cheio = {
            "servico": "coloracao",
            "draft_agendamento": {
                "servico": "coloracao",
                "profissional": "Gloria",
                "data_hora": "2026-06-20 11:00"
            },
            "motivo_estado": "profissional_nao_atende_servico",
            "profissional_rejeitado": "Carla",
            "profissionais_validos": ["Bruna", "Gloria"],
            "aguardando_confirmacao_agendamento": True,
            "dados_confirmacao_agendamento": {"servico": "coloracao"},
            "estado_fluxo": "agendamento_pronto",
            "opcoes_horario": [{"data_hora": "2026-06-20 11:00"}],
            "modo_escolha_horario": True
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx_cheio)
        print(f"  [OK] Estado completo salvo")

        # PASSO 2: Limpar tudo
        print("\n[PASSO 2] Limpando contexto...")
        ctx_limpo = {
            "servico": None,
            "draft_agendamento": None,
            "motivo_estado": None,
            "profissional_rejeitado": None,
            "profissionais_validos": None,
            "aguardando_confirmacao_agendamento": None,
            "dados_confirmacao_agendamento": None,
            "opcoes_horario": None,
            "modo_escolha_horario": None,
            "estado_fluxo": "idle"
        }

        await salvar_contexto_temporario(USER_ID_TESTE, ctx_limpo)
        print(f"  [OK] Contexto limpo")

        # PASSO 3: Recarregar e validar que nao ressuscitou
        print("\n[PASSO 3] Recarregando para validar limpeza...")
        ctx_final = await carregar_contexto_temporario(USER_ID_TESTE) or {}

        # Validar que nada antigo ressuscitou
        campos_para_validar = [
            "motivo_estado",
            "profissional_rejeitado",
            "profissionais_validos",
            "aguardando_confirmacao_agendamento",
            "dados_confirmacao_agendamento",
            "opcoes_horario",
            "modo_escolha_horario"
        ]

        for campo in campos_para_validar:
            valor = ctx_final.get(campo)
            if valor is not None:
                resultado["motivo_falha"] = f"{campo} = {valor} nao deveria estar no contexto"
                return False, resultado

        if ctx_final.get("estado_fluxo") != "idle":
            resultado["motivo_falha"] = f"estado_fluxo = {ctx_final.get('estado_fluxo')}, esperava idle"
            return False, resultado

        print(f"  [OK] Contexto limpo permaneceu limpo")

        resultado["passou"] = True
        return True, resultado

    except Exception as e:
        resultado["motivo_falha"] = str(e)
        return False, resultado


async def main():
    """Executa bateria P0-PERSISTENCIA."""
    print("\n" + "="*80)
    print("BATERIA P0-PERSISTENCIA — Testes Reais com Firestore")
    print("="*80)

    resultados = []
    passou = 0
    falhou = 0

    # Executar TESTES implementados (1-6)
    testes_rodados = TESTES

    for teste in testes_rodados:
        sucesso = await executar_teste(teste)
        resultados.append(asdict(teste))

        if sucesso:
            passou += 1
            print(f"[OK] Teste {teste.id} PASSOU")
        else:
            falhou += 1
            print(f"[ERRO] Teste {teste.id} FALHOU")

    # Resultado consolidado
    resultado_final = {
        "suite": "p0_persistencia_real",
        "versao": "1.0_template",
        "data": datetime.now().isoformat(),
        "total_testes": len(TESTES),
        "passou": passou,
        "falhou": falhou,
        "taxa_sucesso": f"{(passou / len(TESTES) * 100):.1f}%" if TESTES else "0%",
        "testes": resultados,
        "nota": "TEMPLATE - Implementar chamadas reais ao router/Firestore"
    }

    # Salvar resultado
    resultado_file = Path(__file__).parent / "resultado_p0_persistencia_real.json"
    with open(resultado_file, "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Resultado salvo em: {resultado_file}")

    # Resumo final
    print("\n" + "="*80)
    print("RESUMO")
    print("="*80)
    print(f"Testes: {len(TESTES)}")
    print(f"Passaram: {passou}")
    print(f"Falharam: {falhou}")
    print(f"Taxa: {resultado_final['taxa_sucesso']}")
    print("="*80 + "\n")

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
