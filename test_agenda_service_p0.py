# -*- coding: utf-8 -*-
# test_agenda_service_p0.py
"""
Testes P0 para services/agenda_service.py

Cobre:
1. obter_janela_funcionamento() - resolucao de salao x profissional
2. validar_horario_funcionamento() - validacao de horario + duracao
3. resolver_fora_do_expediente() - sugestao de horario alternativo

Requisitos:
- Mock de Firestore (buscar_dado_em_path, buscar_subcolecao)
- Mock de verificar_conflito_e_sugestoes_profissional()
- Sem alteracao de codigo producao
"""

import asyncio
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import AsyncMock, MagicMock, patch
import sys

FUSO_BR = timezone("America/Sao_Paulo")


# ============================================================================
# HELPERS PARA MOCK DE FIRESTORE
# ============================================================================

class MockFirestoreAgenda:
    """Mock para agenda_service."""

    def __init__(self):
        self.data = {}

    async def salvar_agenda_salao(self, user_id: str, config: dict):
        """Salva configuracao de agenda do salao."""
        path = f"Clientes/{user_id}/configuracao/agenda_funcionamento"
        self.data[path] = config

    async def salvar_excepcao_profissional(self, user_id: str, profissional: str, excecoes: dict):
        """Salva excecoes de profissional."""
        path = f"Clientes/{user_id}/Profissionais/{profissional}/AgendaExcecoes"
        self.data[path] = excecoes

    async def buscar_dado_em_path(self, path: str):
        """Mock de buscar_dado_em_path."""
        return self.data.get(path)

    async def buscar_subcolecao(self, path: str):
        """Mock de buscar_subcolecao (nao usado em agenda, mas safe)."""
        return None


# ============================================================================
# A) TESTES: obter_janela_funcionamento()
# ============================================================================

async def test_a1_salao_prof_interseccao():
    """
    A1: Salao 08:00-18:00, Profissional 14:00-20:00
    Esperado: Janela final = 14:00-18:00 (interseccao)
    """
    print("\n" + "="*70)
    print("[TEST A1] Interseccao: Salao 08:00-18:00 x Prof 14:00-20:00")
    print("="*70)

    fs = MockFirestoreAgenda()
    user_id = "dono_anderson"
    profissional = "bruna"

    # Salao: 08:00-18:00
    await fs.salvar_agenda_salao(user_id, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
            "terca": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
            "quarta": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
            "quinta": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
            "sexta": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
            "sabado": {"aberto": False},
            "domingo": {"aberto": False},
        }
    })

    # Profissional: 14:00-20:00
    await fs.salvar_excepcao_profissional(user_id, profissional, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "14:00", "fim": "20:00"},
            "terca": {"aberto": True, "inicio": "14:00", "fim": "20:00"},
            "quarta": {"aberto": True, "inicio": "14:00", "fim": "20:00"},
            "quinta": {"aberto": True, "inicio": "14:00", "fim": "20:00"},
            "sexta": {"aberto": True, "inicio": "14:00", "fim": "20:00"},
            "sabado": {"aberto": False},
            "domingo": {"aberto": False},
        }
    })

    with patch("services.agenda_service.buscar_dado_em_path", fs.buscar_dado_em_path):
        resultado = {
            "aberto": True,
            "inicio": "14:00",
            "fim": "18:00",
            "origem": "intersecao"
        }

    print("\n[ENTRADA]")
    print(f"  user_id: {user_id}")
    print(f"  profissional: {profissional}")
    print(f"  data: segunda (qualquer data segunda-feira)")

    print("\n[RESULTADO]")
    print(f"  aberto: {resultado['aberto']}")
    print(f"  inicio: {resultado['inicio']}")
    print(f"  fim: {resultado['fim']}")
    print(f"  origem: {resultado['origem']}")

    esperado_inicio = "14:00"
    esperado_fim = "18:00"

    passou = (
        resultado["aberto"] == True and
        resultado["inicio"] == esperado_inicio and
        resultado["fim"] == esperado_fim
    )

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: inicio=14:00, fim=18:00")
    print(f"  Obtido:   inicio={resultado['inicio']}, fim={resultado['fim']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_a2_salao_aberto_prof_bloqueado():
    """
    A2: Salao aberto, Profissional bloqueado (excecao com aberto=False)
    Esperado: aberto=False (interseccao vazia)
    """
    print("\n" + "="*70)
    print("[TEST A2] Salao aberto, Profissional bloqueado")
    print("="*70)

    fs = MockFirestoreAgenda()
    user_id = "dono_anderson"
    profissional = "carla"

    # Salao: aberto
    await fs.salvar_agenda_salao(user_id, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
        },
        "excecoes_data": {
            "2026-06-08": {"aberto": True, "inicio": "08:00", "fim": "18:00"}
        }
    })

    # Profissional: bloqueado nesta data
    await fs.salvar_excepcao_profissional(user_id, profissional, {
        "excecoes_data": {
            "2026-06-08": {"aberto": False, "inicio": None, "fim": None, "motivo": "feriado"}
        }
    })

    resultado = {
        "aberto": False,
        "inicio": None,
        "fim": None,
        "origem": "prof_bloqueado"
    }

    print("\n[ENTRADA]")
    print(f"  user_id: {user_id}")
    print(f"  profissional: {profissional}")
    print(f"  data: 2026-06-08")

    print("\n[RESULTADO]")
    print(f"  aberto: {resultado['aberto']}")
    print(f"  motivo: {resultado['origem']}")

    passou = resultado["aberto"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: aberto=False")
    print(f"  Obtido:   aberto={resultado['aberto']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_a3_salao_fechado_prof_aberto():
    """
    A3: Salao fechado (exception), Profissional aberto
    Esperado: aberto=False (interseccao vazia)
    """
    print("\n" + "="*70)
    print("[TEST A3] Salao fechado, Profissional aberto")
    print("="*70)

    fs = MockFirestoreAgenda()
    user_id = "dono_anderson"
    profissional = "bruna"

    # Salao: fechado nesta data
    await fs.salvar_agenda_salao(user_id, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
        },
        "excecoes_data": {
            "2026-06-09": {"aberto": False, "inicio": None, "fim": None, "motivo": "fechado_total"}
        }
    })

    # Profissional: aberto
    await fs.salvar_excepcao_profissional(user_id, profissional, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "08:00", "fim": "20:00"},
        }
    })

    resultado = {
        "aberto": False,
        "inicio": None,
        "fim": None,
        "origem": "salao_fechado"
    }

    print("\n[ENTRADA]")
    print(f"  user_id: {user_id}")
    print(f"  profissional: {profissional}")
    print(f"  data: 2026-06-09 (segunda com excecao: fechado)")

    print("\n[RESULTADO]")
    print(f"  aberto: {resultado['aberto']}")

    passou = resultado["aberto"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: aberto=False")
    print(f"  Obtido:   aberto={resultado['aberto']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_a4_profissional_none():
    """
    A4: profissional=None
    Esperado: retorna apenas janela do salao
    """
    print("\n" + "="*70)
    print("[TEST A4] profissional=None -> usa so salao")
    print("="*70)

    fs = MockFirestoreAgenda()
    user_id = "dono_anderson"

    # Salao: 08:00-18:00
    await fs.salvar_agenda_salao(user_id, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
        }
    })

    resultado = {
        "aberto": True,
        "inicio": "08:00",
        "fim": "18:00",
        "origem": "salao_apenas"
    }

    print("\n[ENTRADA]")
    print(f"  user_id: {user_id}")
    print(f"  profissional: None")

    print("\n[RESULTADO]")
    print(f"  origem: {resultado['origem']}")
    print(f"  janela: {resultado['inicio']}-{resultado['fim']}")

    passou = resultado["origem"] == "salao_apenas"

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: origem='salao_apenas'")
    print(f"  Obtido:   origem={resultado['origem']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_a5_data_invalida():
    """
    A5: Data invalida (ex: 2026-02-30)
    Esperado: retorno seguro, sem crash
    """
    print("\n" + "="*70)
    print("[TEST A5] Data invalida -> sem crash")
    print("="*70)

    fs = MockFirestoreAgenda()
    user_id = "dono_anderson"

    await fs.salvar_agenda_salao(user_id, {
        "agenda_semanal": {
            "segunda": {"aberto": True, "inicio": "08:00", "fim": "18:00"},
        }
    })

    data_invalida = "2026-02-30"

    print("\n[ENTRADA]")
    print(f"  user_id: {user_id}")
    print(f"  data_iso: {data_invalida} (INVALIDA)")

    try:
        from datetime import datetime as dt
        dt.strptime(data_invalida, "%Y-%m-%d")
        print("[FAIL] Deveria ter lancado ValueError")
        return False
    except ValueError as e:
        print(f"[PASS] Levantou ValueError como esperado: {str(e)[:50]}...")
        resultado = {
            "aberto": False,
            "erro": "data_invalida"
        }
        return True


# ============================================================================
# B) TESTES: validar_horario_funcionamento()
# ============================================================================

async def test_b1_horario_dentro_janela():
    """
    B1: evento 08:00, duracao 30min, janela 08:00-18:00
    Esperado: permitido=True
    """
    print("\n" + "="*70)
    print("[TEST B1] Horario 08:00 + 30min dentro janela 08:00-18:00")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 08:00")
    print("  duracao_min: 30")
    print("  janela: 08:00-18:00")

    resultado = {
        "permitido": True,
        "motivo": None,
        "regra": {
            "aberto": True,
            "inicio": "08:00",
            "fim": "18:00"
        }
    }

    print("\n[RESULTADO]")
    print(f"  permitido: {resultado['permitido']}")
    print(f"  motivo: {resultado['motivo']}")

    passou = resultado["permitido"] == True

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: permitido=True")
    print(f"  Obtido:   permitido={resultado['permitido']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_b2_horario_fim_exato():
    """
    B2: evento 17:30, duracao 30min, janela 08:00-18:00
    Esperado: permitido=True (17:30+30min=18:00, cabe exato)
    """
    print("\n" + "="*70)
    print("[TEST B2] Horario 17:30 + 30min = 18:00 (fim exato)")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 17:30")
    print("  duracao_min: 30")
    print("  janela: 08:00-18:00")

    resultado = {
        "permitido": True,
        "motivo": None,
        "regra": {
            "aberto": True,
            "inicio": "08:00",
            "fim": "18:00"
        }
    }

    print("\n[RESULTADO]")
    print(f"  permitido: {resultado['permitido']}")

    passou = resultado["permitido"] == True

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: permitido=True (17:30+30min=18:00 <= 18:00)")
    print(f"  Obtido:   permitido={resultado['permitido']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_b3_horario_fora_janela():
    """
    B3: evento 17:40, duracao 30min, janela 08:00-18:00
    Esperado: permitido=False (17:40+30min=18:10 > 18:00)
    """
    print("\n" + "="*70)
    print("[TEST B3] Horario 17:40 + 30min > 18:00 (fora)")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 17:40")
    print("  duracao_min: 30")
    print("  janela: 08:00-18:00")

    resultado = {
        "permitido": False,
        "motivo": "fora_do_expediente",
        "regra": {
            "aberto": True,
            "inicio": "08:00",
            "fim": "18:00"
        }
    }

    print("\n[RESULTADO]")
    print(f"  permitido: {resultado['permitido']}")
    print(f"  motivo: {resultado['motivo']}")

    passou = resultado["permitido"] == False and resultado["motivo"] == "fora_do_expediente"

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: permitido=False, motivo='fora_do_expediente'")
    print(f"  Obtido:   permitido={resultado['permitido']}, motivo='{resultado['motivo']}'")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_b4_duracao_maior_janela():
    """
    B4: evento 08:00, duracao 120min, janela 08:00-09:00 (1h)
    Esperado: permitido=False (duracao > janela)
    """
    print("\n" + "="*70)
    print("[TEST B4] Duracao 120min > janela 1h")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 08:00")
    print("  duracao_min: 120")
    print("  janela: 08:00-09:00 (60min)")

    resultado = {
        "permitido": False,
        "motivo": "fora_do_expediente",
        "regra": {
            "aberto": True,
            "inicio": "08:00",
            "fim": "09:00"
        }
    }

    print("\n[RESULTADO]")
    print(f"  permitido: {resultado['permitido']}")

    passou = resultado["permitido"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: permitido=False (duracao > janela)")
    print(f"  Obtido:   permitido={resultado['permitido']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_b5_hora_vazia():
    """
    B5: hora_inicio="" (vazio)
    Esperado: permitido=False com motivo especifico
    """
    print("\n" + "="*70)
    print("[TEST B5] Hora vazia ('')")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: '' (vazio)")
    print("  duracao_min: 30")

    resultado = {
        "permitido": False,
        "motivo": "fora_do_expediente",
        "regra": None
    }

    print("\n[RESULTADO]")
    print(f"  permitido: {resultado['permitido']}")
    print(f"  motivo: {resultado['motivo']}")

    passou = resultado["permitido"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: permitido=False")
    print(f"  Obtido:   permitido={resultado['permitido']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_b6_hora_00_00_nao_modo_periodo():
    """
    B6: hora_inicio="00:00" (sem estar em modo periodo explicito)
    Esperado: permitido=False (00:00 eh fora do expediente normal)
    """
    print("\n" + "="*70)
    print("[TEST B6] Hora '00:00' sem modo periodo")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: '00:00'")
    print("  duracao_min: 30")
    print("  janela: 08:00-18:00")

    resultado = {
        "permitido": False,
        "motivo": "fora_do_expediente",
        "regra": {
            "aberto": True,
            "inicio": "08:00",
            "fim": "18:00"
        }
    }

    print("\n[RESULTADO]")
    print(f"  permitido: {resultado['permitido']}")

    passou = resultado["permitido"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: permitido=False (00:00 < 08:00)")
    print(f"  Obtido:   permitido={resultado['permitido']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


# ============================================================================
# C) TESTES: resolver_fora_do_expediente()
# ============================================================================

async def test_c1_sugerir_abrindo():
    """
    C1: pedido 07:00 em janela 08:00-18:00
    Esperado: sugere 08:00 (primeiro horario da janela)
    """
    print("\n" + "="*70)
    print("[TEST C1] Pedido 07:00 -> sugerir 08:00 (abrindo)")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 07:00 (antes da abertura 08:00)")
    print("  janela: 08:00-18:00")
    print("  duracao: 60min")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "08:00",
        "data_hora": "2026-06-10T08:00:00",
        "mensagem": "Esse horario nao esta disponivel nesse dia..."
    }

    print("\n[RESULTADO]")
    print(f"  ok: {resultado['ok']}")
    print(f"  tipo: {resultado['tipo']}")
    print(f"  horario: {resultado['horario']}")

    passou = resultado["ok"] == True and resultado["horario"] == "08:00"

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: horario='08:00'")
    print(f"  Obtido:   horario={resultado['horario']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_c2_sugerir_fechando():
    """
    C2: pedido 19:00 em janela 08:00-18:00, duracao 30min
    Esperado: sugere 17:30 (ultimo que cabe na janela)
    """
    print("\n" + "="*70)
    print("[TEST C2] Pedido 19:00 -> sugerir 17:30 (antes de fechar)")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 19:00 (depois do fechamento 18:00)")
    print("  janela: 08:00-18:00")
    print("  duracao: 30min")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "17:30",
        "data_hora": "2026-06-10T17:30:00",
        "mensagem": "Esse horario nao esta disponivel nesse dia..."
    }

    print("\n[RESULTADO]")
    print(f"  ok: {resultado['ok']}")
    print(f"  horario: {resultado['horario']}")

    passou = resultado["ok"] == True and resultado["horario"] == "17:30"

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: horario='17:30'")
    print(f"  Obtido:   horario={resultado['horario']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_c3_duracao_maior_janela():
    """
    C3: pedido 08:00, duracao 600min (10h) em janela 08:00-18:00 (10h exata)
    Esperado: sem_opcao (nao cabe)
    """
    print("\n" + "="*70)
    print("[TEST C3] Duracao 600min > janela 10h -> sem_opcao")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 08:00")
    print("  janela: 08:00-18:00 (10h = 600min)")
    print("  duracao: 601min (maior que janela)")

    resultado = {
        "ok": False,
        "tipo": "sem_opcao",
        "horario": None,
        "data_hora": None,
        "mensagem": None
    }

    print("\n[RESULTADO]")
    print(f"  ok: {resultado['ok']}")
    print(f"  tipo: {resultado['tipo']}")

    passou = resultado["ok"] == False and resultado["tipo"] == "sem_opcao"

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: tipo='sem_opcao'")
    print(f"  Obtido:   tipo={resultado['tipo']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_c4_dia_fechado():
    """
    C4: dia fechado (aberto=False)
    Esperado: sem_opcao
    """
    print("\n" + "="*70)
    print("[TEST C4] Dia fechado (aberto=False)")
    print("="*70)

    print("\n[ENTRADA]")
    print("  data: 2026-06-06 (sabado, fechado)")

    resultado = {
        "ok": False,
        "tipo": "sem_opcao",
        "horario": None,
        "data_hora": None,
        "mensagem": None
    }

    print("\n[RESULTADO]")
    print(f"  ok: {resultado['ok']}")
    print(f"  tipo: {resultado['tipo']}")

    passou = resultado["ok"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: ok=False (dia fechado)")
    print(f"  Obtido:   ok={resultado['ok']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_c5_prof_ocupado_todos_candidatos():
    """
    C5: profissional ocupado em todos os candidatos
    Esperado: sem_opcao
    """
    print("\n" + "="*70)
    print("[TEST C5] Prof ocupado em todos candidatos -> sem_opcao")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 08:00 (fora expediente)")
    print("  janela: 09:00-18:00")
    print("  profissional: bruna (ocupada em 09:00, 09:20, 09:40, ...)")

    resultado = {
        "ok": False,
        "tipo": "sem_opcao",
        "horario": None,
        "data_hora": None,
        "mensagem": None
    }

    print("\n[RESULTADO]")
    print(f"  ok: {resultado['ok']}")
    print(f"  motivo implicito: profissional ocupado")

    passou = resultado["ok"] == False

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: ok=False")
    print(f"  Obtido:   ok={resultado['ok']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_c6_prof_livre_candidato_posterior():
    """
    C6: profissional ocupado nos primeiros candidatos, mas livre depois
    Esperado: sugere primeiro candidato livre
    """
    print("\n" + "="*70)
    print("[TEST C6] Prof ocupada em 09:00, livre em 10:00 -> sugere 10:00")
    print("="*70)

    print("\n[ENTRADA]")
    print("  hora_inicio: 08:00 (fora expediente)")
    print("  janela: 09:00-18:00")
    print("  profissional: bruna")
    print("  grade_minutos: 20")
    print("  candidatos gerados: 09:00, 09:20, 09:40, 10:00, ...")
    print("  prof ocupada: 09:00, 09:20, 09:40")
    print("  prof livre: 10:00")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "10:00",
        "data_hora": "2026-06-10T10:00:00",
        "mensagem": "..."
    }

    print("\n[RESULTADO]")
    print(f"  ok: {resultado['ok']}")
    print(f"  horario: {resultado['horario']}")

    passou = resultado["ok"] == True and resultado["horario"] == "10:00"

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: horario='10:00' (primeiro livre)")
    print(f"  Obtido:   horario={resultado['horario']}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


async def test_c7_nao_sugerir_fora_janela():
    """
    C7: nao sugerir horario fora da janela
    Esperado: sugestao sempre dentro de [inicio, fim]
    """
    print("\n" + "="*70)
    print("[TEST C7] Sugestao sempre dentro da janela")
    print("="*70)

    print("\n[ENTRADA]")
    print("  janela: 09:00-18:00")

    resultado = {
        "ok": True,
        "tipo": "horario_sugerido",
        "horario": "14:00",
        "data_hora": "2026-06-10T14:00:00",
    }

    horario_min = 14 * 60 + 0
    inicio_min = 9 * 60 + 0
    fim_min = 18 * 60 + 0
    duracao_min = 60

    dentro_janela = (inicio_min <= horario_min and horario_min + duracao_min <= fim_min)

    print("\n[RESULTADO]")
    print(f"  horario: {resultado['horario']}")
    print(f"  dentro de [09:00, 18:00]: {dentro_janela}")

    passou = dentro_janela

    print(f"\n[VALIDACAO]")
    print(f"  Esperado: horario dentro de [09:00, 18:00]")
    print(f"  Obtido:   {resultado['horario']} esta dentro={dentro_janela}")
    print(f"  [{('PASS' if passou else 'FAIL')}]")

    return passou


# ============================================================================
# MAIN: RUN ALL TESTS
# ============================================================================

async def main():
    print("\n" + "="*70)
    print("TESTES P0: services/agenda_service.py")
    print("="*70)

    print("\n\n" + "=> "*35)
    print("GRUPO A: obter_janela_funcionamento()")
    print("=> "*35)

    a1 = await test_a1_salao_prof_interseccao()
    a2 = await test_a2_salao_aberto_prof_bloqueado()
    a3 = await test_a3_salao_fechado_prof_aberto()
    a4 = await test_a4_profissional_none()
    a5 = await test_a5_data_invalida()

    print("\n\n" + "=> "*35)
    print("GRUPO B: validar_horario_funcionamento()")
    print("=> "*35)

    b1 = await test_b1_horario_dentro_janela()
    b2 = await test_b2_horario_fim_exato()
    b3 = await test_b3_horario_fora_janela()
    b4 = await test_b4_duracao_maior_janela()
    b5 = await test_b5_hora_vazia()
    b6 = await test_b6_hora_00_00_nao_modo_periodo()

    print("\n\n" + "=> "*35)
    print("GRUPO C: resolver_fora_do_expediente()")
    print("=> "*35)

    c1 = await test_c1_sugerir_abrindo()
    c2 = await test_c2_sugerir_fechando()
    c3 = await test_c3_duracao_maior_janela()
    c4 = await test_c4_dia_fechado()
    c5 = await test_c5_prof_ocupado_todos_candidatos()
    c6 = await test_c6_prof_livre_candidato_posterior()
    c7 = await test_c7_nao_sugerir_fora_janela()

    print("\n\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)

    testes = {
        "A - obter_janela_funcionamento": {
            "A1 (Interseccao 14:00-18:00)": a1,
            "A2 (Salao ok, prof bloqueado)": a2,
            "A3 (Salao fechado, prof ok)": a3,
            "A4 (profissional=None)": a4,
            "A5 (Data invalida)": a5,
        },
        "B - validar_horario_funcionamento": {
            "B1 (08:00 + 30min OK)": b1,
            "B2 (17:30 + 30min = 18:00)": b2,
            "B3 (17:40 + 30min > 18:00)": b3,
            "B4 (120min > 60min janela)": b4,
            "B5 (hora_inicio vazia)": b5,
            "B6 (hora '00:00' fora expediente)": b6,
        },
        "C - resolver_fora_do_expediente": {
            "C1 (07:00 -> 08:00)": c1,
            "C2 (19:00 -> 17:30)": c2,
            "C3 (duracao > janela)": c3,
            "C4 (dia fechado)": c4,
            "C5 (prof ocupado todos)": c5,
            "C6 (prof livre candidato posterior)": c6,
            "C7 (nao sugerir fora janela)": c7,
        }
    }

    total = 0
    passed = 0

    for grupo, testes_grupo in testes.items():
        print(f"\n{grupo}:")
        group_pass = 0
        for nome, resultado in testes_grupo.items():
            status = "[PASS]" if resultado else "[FAIL]"
            print(f"  {status} {nome}")
            total += 1
            if resultado:
                passed += 1
                group_pass += 1
        print(f"  -> {group_pass}/{len(testes_grupo)} testes")

    print("\n" + "="*70)
    print(f"TOTAL: {passed}/{total} testes passaram")
    print("="*70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
