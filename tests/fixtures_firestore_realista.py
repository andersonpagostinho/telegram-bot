#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE 2: FIXTURES REALISTAS CENTRALIZADAS
==========================================

Biblioteca de fixtures que replicam EXATAMENTE os estados que existem em produção.

Cada fixture representa um estado REAL que foi diagnosticado em Firestore.
Todos os testes usarão MESMAS fixtures para garantir consistência.

Fixtures criadas com base em auditoria de 2026-09-28:
- Gap: Novo agendamento após erro não era testado
- Solução: Fixtures que replicam contaminação de produção

Status: FASE 2 — Criação de Fixtures Centralizadas
Data: 2026-09-28
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta


# ============================================================================
# TENANT DE TESTE
# ============================================================================

TENANT_ID_TESTE = "test_tenant_neoeve_2026"
USER_ID_TESTE = "user_teste_7371670478"  # ID real de produção (para compatibilidade)
DONO_ID_TESTE = "dono_teste_7394370553"  # ID real de dono (para compatibilidade)


# ============================================================================
# FIXTURE 0: CONTEXTO LIMPO (Novo usuário, nenhum histórico)
# ============================================================================

FIXTURE_NOVO_CLIENTE = {
    """
    Estado: Cliente novo, sem histórico, nenhuma sessão anterior
    Uso: Teste do caminho feliz, novo agendamento simples
    Características: Tudo limpo, nenhuma contaminação
    """
    "user_id": USER_ID_TESTE,
    "tenant_id": TENANT_ID_TESTE,

    # Estado do fluxo
    "estado_fluxo": "idle",
    "motivo_estado": None,

    # Draft e contexto anterior
    "draft_agendamento": None,
    "profissional_escolhido": None,
    "profissional_rejeitado": None,
    "profissionais_validos": [],

    # Confirmação
    "aguardando_confirmacao_agendamento": False,
    "dados_confirmacao_agendamento": None,

    # Histórico
    "historico_texto": [],
    "ultimo_servico": None,
    "ultimo_profissional": None,

    # Metadados
    "criado_em": datetime.now().isoformat(),
    "atualizado_em": datetime.now().isoformat(),
}


# ============================================================================
# FIXTURE 1: CONTEXTO COM ERRO ANTERIOR (Profissional não atende)
# ============================================================================

FIXTURE_ERRO_PROFISSIONAL = {
    """
    Estado: Cliente tentou agendar, profissional não atende o serviço
    Fluxo anterior:
      1. "Quero corte com Carla amanhã às 17h"
      2. Sistema responde: "Carla não atende corte, escolha entre: Bruna, Gloria, Joana"
      3. Cliente AINDA NÃO escolheu (está em aguardando_profissional)

    Uso: Teste de ajuste (usuário escolhe outro profissional)
    Uso: Teste de novo agendamento (usuário pede escova, não corte)

    Características:
    - motivo_estado é o "STUCK STATE" histórico da NeoEve
    - estado_fluxo ainda está em fluxo anterior
    - draft tem dados ANTIGOS (corte, não escova)
    - profissional_rejeitado impede reutilizar Carla

    CRÍTICO PARA PATCH_P0.5:
    - Se usuário faz NOVO agendamento (não ajuste), PATCH_P0.5 deve limpar tudo isto
    - Se usuário faz ajuste profissional, deve PRESERVAR draft
    """
    "user_id": USER_ID_TESTE,
    "tenant_id": TENANT_ID_TESTE,

    # Estado de erro anterior
    "estado_fluxo": "aguardando_profissional",
    "motivo_estado": "profissional_nao_atende_servico",
    "profissional_rejeitado": "Carla",
    "profissionais_validos": ["Bruna", "Gloria", "Joana"],

    # Draft do agendamento que FALHOU
    "draft_agendamento": {
        "servico": "corte",
        "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),
        "profissional": None,  # Carla foi rejeitada
        "duracao_minutos": 30,
    },
    "profissional_escolhido": None,

    # Confirmação
    "aguardando_confirmacao_agendamento": False,
    "dados_confirmacao_agendamento": None,

    # Histórico que contexto carrega
    "historico_texto": [
        "Quero corte com Carla amanhã às 17h",
        # Sistema respondeu oferecendo alternativas
    ],
    "ultimo_servico": "corte",
    "ultimo_profissional": "Carla",

    # Metadados
    "criado_em": (datetime.now() - timedelta(hours=2)).isoformat(),
    "atualizado_em": (datetime.now() - timedelta(minutes=5)).isoformat(),
}


# ============================================================================
# FIXTURE 2: DRAFT CONTAMINADO (Serviço antigo residual)
# ============================================================================

FIXTURE_DRAFT_CONTAMINADO = {
    """
    Estado: Draft de agendamento anterior ainda em memória/Firestore
    Cenário que causou bugs históricos:

    Fluxo anterior (DIAS AGO):
      1. "Quero coloração"
      2. "Amanhã (que era dias atrás) às 15h"
      3. Sistema confirmou agendamento

    Fluxo atual:
      1. Nova sessão, mas contexto NÃO foi limpado
      2. draft_agendamento ainda tem "coloração" de dias atrás
      3. Cliente novo pede "corte"
      4. Sistema deveria LIMPAR draft antigo

    Uso: Teste de contaminação de estado
    Uso: Teste de PATCH_P0.5 que limpa draft antigo

    Características:
    - Serviço é "coloracao" (antigo, não mais relevante)
    - Data é PASSADA (data anterior a hoje)
    - estado_fluxo ainda ativo
    - Sem motivo_estado, mas draft está "sujo"
    """
    "user_id": USER_ID_TESTE,
    "tenant_id": TENANT_ID_TESTE,

    # Estado que permite draft sujo
    "estado_fluxo": "agendando",
    "motivo_estado": None,

    # Draft CONTAMINADO (dias atrás)
    "draft_agendamento": {
        "servico": "coloracao",  # ← ANTIGO, não é o que cliente quer agora
        "data_hora": (datetime.now() - timedelta(days=3)).isoformat(),  # ← PASSADO!
        "profissional": None,
        "duracao_minutos": 120,
    },
    "profissional_escolhido": None,
    "profissional_rejeitado": None,
    "profissionais_validos": [],

    # Confirmação de agendamento antigo
    "aguardando_confirmacao_agendamento": False,
    "dados_confirmacao_agendamento": {
        "servico": "coloracao",
        "data_hora": (datetime.now() - timedelta(days=3)).isoformat(),
        "profissional": "Bruna",
        "descricao": "Coloração - já realizada",
    },

    # Histórico antigo
    "historico_texto": [
        "Quero coloração",
        "Amanhã às 15h",  # Amanhã era dias atrás
        "Confirma?",
        # ... mais mensagens antigas
    ],
    "ultimo_servico": "coloracao",
    "ultimo_profissional": "Bruna",

    # Metadados mostram que é antigo
    "criado_em": (datetime.now() - timedelta(days=10)).isoformat(),
    "atualizado_em": (datetime.now() - timedelta(days=3)).isoformat(),
}


# ============================================================================
# FIXTURE 3: CONFIRMAÇÃO PENDENTE (Agendamento aprovado, aguardando confirmação final)
# ============================================================================

FIXTURE_CONFIRMACAO_PENDENTE = {
    """
    Estado: Agendamento foi construído, dados validados, aguardando confirmação do cliente

    Fluxo:
      1. "Quero escova com Bruna"
      2. "Amanhã às 14h" (horário validado, sem conflito)
      3. Sistema: "Vou agendar: Escova com Bruna amanhã 14h. Confirma?"
      4. Cliente: AINDA NÃO respondeu (ou está relendo)

    Uso: Teste de timeout de confirmação
    Uso: Teste de mudança de ideia na confirmação
    Uso: Teste de confirmação válida

    Características:
    - estado_fluxo está em "agendando" (quase pronto)
    - aguardando_confirmacao_agendamento = True
    - dados_confirmacao_agendamento tem tudo preenchido
    - Nenhum motivo_estado (validação passou)
    """
    "user_id": USER_ID_TESTE,
    "tenant_id": TENANT_ID_TESTE,

    # Estado: aguardando confirmação
    "estado_fluxo": "agendando",
    "motivo_estado": None,

    # Draft COMPLETO (ready to confirm)
    "draft_agendamento": {
        "servico": "escova",
        "data_hora": (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0).isoformat(),
        "profissional": "Bruna",
        "duracao_minutos": 60,
    },
    "profissional_escolhido": "Bruna",
    "profissional_rejeitado": None,
    "profissionais_validos": [],

    # Dados prontos para confirmação
    "aguardando_confirmacao_agendamento": True,
    "dados_confirmacao_agendamento": {
        "servico": "escova",
        "profissional": "Bruna",
        "data_hora": (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0).isoformat(),
        "descricao": "Escova com Bruna - Segunda-feira às 14h",
        "duracao_minutos": 60,
    },

    # Histórico da construção
    "historico_texto": [
        "Quero escova com Bruna",
        "Amanhã às 14h",
        # Esperando confirmação
    ],
    "ultimo_servico": "escova",
    "ultimo_profissional": "Bruna",

    # Metadados: criado recentemente
    "criado_em": (datetime.now() - timedelta(hours=1)).isoformat(),
    "atualizado_em": (datetime.now() - timedelta(minutes=2)).isoformat(),
}


# ============================================================================
# FIXTURE 4: MULTI-TENANT (Mesmo user_id em dois tenants diferentes)
# ============================================================================

FIXTURE_MULTITENANT_A = {
    """
    Estado: Cliente que usa NeoEve em DOIS estabelecimentos

    Tenant A: Salão de beleza "Beauty Pro"
    - Clientes: Bruna, Carla, Ana
    - Serviços: Corte, Escova, Coloração

    Cenário de risco: Draft de um tenant contamina outro?
    Validação: Isolamento por tenant_id funciona?

    Características:
    - user_id = USER_ID_TESTE (mesmo)
    - tenant_id = tenant_a (DIFERENTE)
    - draft_agendamento tem dados do Tenant A apenas
    """
    "user_id": USER_ID_TESTE,
    "tenant_id": "tenant_beauty_pro_a",  # Tenant A

    "estado_fluxo": "agendando",
    "motivo_estado": None,

    "draft_agendamento": {
        "servico": "corte",
        "data_hora": (datetime.now() + timedelta(days=1)).isoformat(),
        "profissional": "Bruna",
        "duracao_minutos": 30,
        # Nota: Bruna só existe em Beauty Pro, não em Clinic Pro
    },
    "profissional_escolhido": "Bruna",
    "profissional_rejeitado": None,

    "aguardando_confirmacao_agendamento": False,
    "dados_confirmacao_agendamento": None,

    "historico_texto": ["Quero corte com Bruna"],
    "ultimo_servico": "corte",
    "ultimo_profissional": "Bruna",

    "criado_em": (datetime.now() - timedelta(hours=1)).isoformat(),
    "atualizado_em": (datetime.now() - timedelta(minutes=1)).isoformat(),
}


FIXTURE_MULTITENANT_B = {
    """
    Estado: MESMO user_id, DIFERENTE tenant_id (Clinic Pro)

    Tenant B: Clínica odontológica "Clinic Pro"
    - Clientes: Dr. Silva, Dr. Santos
    - Serviços: Limpeza, Restauração, Tratamento
    - DIFERENTE de Beauty Pro

    Validação crítica:
    - user_id é o mesmo (USER_ID_TESTE)
    - tenant_id é diferente ("tenant_clinic_pro_b")
    - Contexto de Beauty Pro não deve contaminar Clinic Pro
    """
    "user_id": USER_ID_TESTE,  # Mesmo usuário
    "tenant_id": "tenant_clinic_pro_b",  # Tenant B (DIFERENTE)

    "estado_fluxo": "idle",
    "motivo_estado": None,

    "draft_agendamento": None,  # Clinic Pro começa limpo
    "profissional_escolhido": None,
    "profissional_rejeitado": None,

    "aguardando_confirmacao_agendamento": False,
    "dados_confirmacao_agendamento": None,

    "historico_texto": [],
    "ultimo_servico": None,
    "ultimo_profissional": None,

    "criado_em": (datetime.now() - timedelta(hours=24)).isoformat(),
    "atualizado_em": (datetime.now() - timedelta(hours=24)).isoformat(),
}


# ============================================================================
# FIXTURE 5: AGENDAMENTO CONCLUÍDO (Histórico)
# ============================================================================

FIXTURE_AGENDAMENTO_CONCLUIDO = {
    """
    Estado: Agendamento foi criado, confirmado, e executado

    Uso: Teste de contexto histórico (último serviço, último profissional)
    Uso: Teste de sugestão baseada em histórico
    Uso: Teste de recorrência

    Características:
    - estado_fluxo = "idle" (fluxo terminado)
    - draft_agendamento = None (já foi confirmado)
    - dados_confirmacao_agendamento = histórico da execução
    - ultimo_servico e ultimo_profissional preenchidos
    """
    "user_id": USER_ID_TESTE,
    "tenant_id": TENANT_ID_TESTE,

    "estado_fluxo": "idle",
    "motivo_estado": None,

    "draft_agendamento": None,  # Já foi confirmado
    "profissional_escolhido": None,
    "profissional_rejeitado": None,

    "aguardando_confirmacao_agendamento": False,
    "dados_confirmacao_agendamento": {
        "servico": "escova",
        "profissional": "Bruna",
        "data_hora": (datetime.now() - timedelta(days=7)).isoformat(),
        "descricao": "Escova com Bruna - já realizada",
        "duracao_minutos": 60,
        "status": "concluido",
    },

    "historico_texto": [
        "Quero escova com Bruna",
        "Próxima segunda às 14h",
        "Confirma?",
        "Pode",
        # ... mais histórico
    ],
    "ultimo_servico": "escova",
    "ultimo_profissional": "Bruna",

    "criado_em": (datetime.now() - timedelta(days=30)).isoformat(),
    "atualizado_em": (datetime.now() - timedelta(days=7)).isoformat(),
}


# ============================================================================
# GETTER FUNCTIONS: Facilitar uso em testes
# ============================================================================

def obter_fixture(nome: str) -> Dict[str, Any]:
    """
    Obter uma fixture pelo nome.

    Nomes disponíveis:
    - "novo_cliente"
    - "erro_profissional"
    - "draft_contaminado"
    - "confirmacao_pendente"
    - "multitenant_a"
    - "multitenant_b"
    - "agendamento_concluido"
    """
    fixtures = {
        "novo_cliente": FIXTURE_NOVO_CLIENTE,
        "erro_profissional": FIXTURE_ERRO_PROFISSIONAL,
        "draft_contaminado": FIXTURE_DRAFT_CONTAMINADO,
        "confirmacao_pendente": FIXTURE_CONFIRMACAO_PENDENTE,
        "multitenant_a": FIXTURE_MULTITENANT_A,
        "multitenant_b": FIXTURE_MULTITENANT_B,
        "agendamento_concluido": FIXTURE_AGENDAMENTO_CONCLUIDO,
    }

    fixture = fixtures.get(nome)
    if not fixture:
        raise ValueError(f"Fixture '{nome}' não encontrada. Disponíveis: {list(fixtures.keys())}")

    # Retornar cópia para evitar mutação
    import copy
    return copy.deepcopy(fixture)


def listar_fixtures() -> list:
    """Listar todas as fixtures disponíveis."""
    return [
        "novo_cliente",
        "erro_profissional",
        "draft_contaminado",
        "confirmacao_pendente",
        "multitenant_a",
        "multitenant_b",
        "agendamento_concluido",
    ]


# ============================================================================
# VALIDAÇÃO: Garantir que todas as fixtures são serializáveis
# ============================================================================

if __name__ == "__main__":
    import json

    print("Validando fixtures...")
    for nome in listar_fixtures():
        try:
            fixture = obter_fixture(nome)
            json_str = json.dumps(fixture, default=str)
            print(f"✅ {nome}: Serializável ({len(json_str)} bytes)")
        except Exception as e:
            print(f"❌ {nome}: ERRO - {e}")

    print("\nFixtures criadas com sucesso!")
    print(f"Total: {len(listar_fixtures())} fixtures prontas para uso em testes.")
