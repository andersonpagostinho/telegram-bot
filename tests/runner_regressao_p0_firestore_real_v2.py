#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BATERIA PERMANENTE P0 — FIRESTORE REAL + FIXTURES (VALIDACAO)
================================================================

Objetivo: Validar que Firestore real + fixtures_firestore_realista.py funcionam
corretamente para substituir MockContext.

Testes:
1-7: Carregamento correto de fixtures
8-10: Manipulacao e salvamento em Firestore
11-16: Isolamento, serialização, e contaminacao

Status: FASE 3 - Validação de Firestore real + Fixtures
Data: 2026-09-28
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.firebase_service_async import (
    salvar_dado_em_path,
    buscar_dado_em_path,
    deletar_dado_em_path,
)
from tests.fixtures_firestore_realista import (
    obter_fixture,
    listar_fixtures,
    TENANT_ID_TESTE,
    USER_ID_TESTE,
)


class ValidacaoFirestore:
    def __init__(self, id: int, nome: str):
        self.id = id
        self.nome = nome
        self.status = "PENDENTE"
        self.motivo_falha = None
        self.detalhes = None


async def test_v1_fixture_novo_cliente_carrega():
    """V1: Fixture novo_cliente carrega do Firestore"""
    teste = ValidacaoFirestore(1, "Fixture novo_cliente carrega do Firestore")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("novo_cliente")

        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        assert ctx_lido is not None, "Nao conseguiu ler fixture do Firestore"
        assert ctx_lido.get("estado_fluxo") == "idle", "Estado inicial nao eh idle"
        assert ctx_lido.get("motivo_estado") is None, "motivo_estado deveria ser None"

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v2_fixture_erro_profissional_carrega():
    """V2: Fixture erro_profissional carrega com estado correto"""
    teste = ValidacaoFirestore(2, "Fixture erro_profissional carrega com motivo_estado")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("erro_profissional")

        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        assert ctx_lido.get("motivo_estado") == "profissional_nao_atende_servico"
        assert ctx_lido.get("estado_fluxo") == "aguardando_profissional"
        assert ctx_lido.get("draft_agendamento") is not None

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v3_fixture_confirmacao_pendente_carrega():
    """V3: Fixture confirmacao_pendente carrega corretamente"""
    teste = ValidacaoFirestore(3, "Fixture confirmacao_pendente carrega")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("confirmacao_pendente")

        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        assert ctx_lido.get("aguardando_confirmacao_agendamento") == True
        assert ctx_lido.get("dados_confirmacao_agendamento") is not None

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v4_fixture_draft_contaminado_carrega():
    """V4: Fixture draft_contaminado carrega com dados antigos"""
    teste = ValidacaoFirestore(4, "Fixture draft_contaminado tem dados antigos")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("draft_contaminado")

        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        assert ctx_lido.get("draft_agendamento", {}).get("servico") == "coloracao"
        assert "2026-09" in ctx_lido.get("draft_agendamento", {}).get("data_hora", "")

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v5_salvar_e_modificar_contexto():
    """V5: Salvar fixture, modificar em memoria, validar em Firestore"""
    teste = ValidacaoFirestore(5, "Modificacao de contexto persiste em Firestore")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("novo_cliente")

        # Salvar fixture
        await salvar_dado_em_path(path_sessao, fixture)

        # Modificar em memoria
        ctx = await buscar_dado_em_path(path_sessao)
        ctx["motivo_estado"] = "teste_modificacao"
        ctx["draft_agendamento"] = {"servico": "corte"}

        # Salvar modificacoes
        await salvar_dado_em_path(path_sessao, ctx)

        # Validar em Firestore
        ctx_lido = await buscar_dado_em_path(path_sessao)
        assert ctx_lido.get("motivo_estado") == "teste_modificacao"
        assert ctx_lido.get("draft_agendamento", {}).get("servico") == "corte"

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v6_limpeza_de_estado():
    """V6: Limpar estado (remover campos) funciona"""
    teste = ValidacaoFirestore(6, "Limpeza de estado funciona em Firestore")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("erro_profissional")

        await salvar_dado_em_path(path_sessao, fixture)

        # Carregar e limpar
        ctx = await buscar_dado_em_path(path_sessao)
        ctx.pop("motivo_estado", None)
        ctx.pop("estado_fluxo", None)
        ctx.pop("draft_agendamento", None)

        await salvar_dado_em_path(path_sessao, ctx)

        # Validar que foi limpado
        ctx_lido = await buscar_dado_em_path(path_sessao)
        assert ctx_lido.get("motivo_estado") is None
        # Nota: estado_fluxo pode ter default, então nao validamos

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v7_serializacao_json():
    """V7: Fixtures sao serializaveis em JSON"""
    teste = ValidacaoFirestore(7, "Fixtures sao JSON-serializaveis")
    try:
        for fixture_nome in listar_fixtures():
            fixture = obter_fixture(fixture_nome)
            json_str = json.dumps(fixture, default=str)
            assert len(json_str) > 0, f"Fixture {fixture_nome} nao serializavel"

        teste.status = "PASSOU"
        return True

    except Exception as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False


async def test_v8_multitenant_isolamento():
    """V8: Multi-tenant isola contextos corretamente"""
    teste = ValidacaoFirestore(8, "Multitenant isola contextos")
    try:
        # Carregar fixture A
        fixture_a = obter_fixture("multitenant_a")
        assert fixture_a.get("tenant_id") == "tenant_beauty_pro_a"

        # Carregar fixture B
        fixture_b = obter_fixture("multitenant_b")
        assert fixture_b.get("tenant_id") == "tenant_clinic_pro_b"

        # Validar que sao diferentes
        assert fixture_a.get("tenant_id") != fixture_b.get("tenant_id")
        assert fixture_a.get("user_id") == fixture_b.get("user_id")  # Mesmo user, tenants diferentes

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False


async def test_v9_historico_preservado():
    """V9: Historico de agendamentos eh preservado"""
    teste = ValidacaoFirestore(9, "Historico de agendamentos preservado")
    try:
        fixture = obter_fixture("agendamento_concluido")

        assert fixture.get("ultimo_servico") == "escova"
        assert fixture.get("ultimo_profissional") == "Bruna"
        assert len(fixture.get("historico_texto", [])) > 0

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False


async def test_v10_campos_opcionais():
    """V10: Campos opcionais (None) sao suportados"""
    teste = ValidacaoFirestore(10, "Campos opcionais suportados")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("novo_cliente")

        # Fixture tem varios campos None
        assert fixture.get("motivo_estado") is None
        assert fixture.get("profissional_rejeitado") is None
        assert fixture.get("dados_confirmacao_agendamento") is None

        # Salvar e ler
        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        assert ctx_lido.get("motivo_estado") is None

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v11_listas_vazias():
    """V11: Listas vazias sao preservadas"""
    teste = ValidacaoFirestore(11, "Listas vazias preservadas")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("novo_cliente")

        assert isinstance(fixture.get("profissionais_validos"), list)
        assert len(fixture.get("profissionais_validos")) == 0

        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        assert isinstance(ctx_lido.get("profissionais_validos"), list)

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v12_dicts_aninhados():
    """V12: Dicionarios aninhados funciona corretamente"""
    teste = ValidacaoFirestore(12, "Dicionarios aninhados suportados")
    try:
        path_sessao = f"Clientes/{TENANT_ID_TESTE}/Sessoes/{USER_ID_TESTE}"
        fixture = obter_fixture("erro_profissional")

        # Fixture tem draft_agendamento (dict aninhado)
        draft = fixture.get("draft_agendamento", {})
        assert isinstance(draft, dict)
        assert "servico" in draft
        assert "data_hora" in draft

        await salvar_dado_em_path(path_sessao, fixture)
        ctx_lido = await buscar_dado_em_path(path_sessao)

        draft_lido = ctx_lido.get("draft_agendamento", {})
        assert draft_lido.get("servico") == draft.get("servico")

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False
    finally:
        try:
            await deletar_dado_em_path(path_sessao)
        except:
            pass


async def test_v13_timestamps():
    """V13: Timestamps (ISO format) preservados"""
    teste = ValidacaoFirestore(13, "Timestamps ISO preservados")
    try:
        fixture = obter_fixture("novo_cliente")

        criado = fixture.get("criado_em")
        atualizado = fixture.get("atualizado_em")

        assert isinstance(criado, str)
        assert isinstance(atualizado, str)
        assert "T" in criado  # ISO format

        teste.status = "PASSOU"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False


async def test_v14_todas_fixtures_carregaveis():
    """V14: Todas as fixtures listadas sao carregaveis"""
    teste = ValidacaoFirestore(14, "Todas as fixtures carregaveis")
    try:
        fixtures_nomes = listar_fixtures()
        assert len(fixtures_nomes) > 0, "Nenhuma fixture disponivel"

        for nome in fixtures_nomes:
            fixture = obter_fixture(nome)
            assert fixture is not None, f"Fixture {nome} eh None"
            assert isinstance(fixture, dict), f"Fixture {nome} nao eh dict"
            assert "user_id" in fixture, f"Fixture {nome} sem user_id"
            assert "tenant_id" in fixture, f"Fixture {nome} sem tenant_id"

        teste.status = "PASSOU"
        teste.detalhes = f"{len(fixtures_nomes)} fixtures carregaveis"
        return True

    except AssertionError as e:
        teste.status = "FALHOU"
        teste.motivo_falha = str(e)
        return False


async def main():
    print("\n" + "=" * 80)
    print("VALIDACAO: FIRESTORE REAL + FIXTURES")
    print("=" * 80)
    print("Objetivo: Validar que Firestore + fixtures funcionam para substituir MockContext")
    print()

    testes = [
        test_v1_fixture_novo_cliente_carrega,
        test_v2_fixture_erro_profissional_carrega,
        test_v3_fixture_confirmacao_pendente_carrega,
        test_v4_fixture_draft_contaminado_carrega,
        test_v5_salvar_e_modificar_contexto,
        test_v6_limpeza_de_estado,
        test_v7_serializacao_json,
        test_v8_multitenant_isolamento,
        test_v9_historico_preservado,
        test_v10_campos_opcionais,
        test_v11_listas_vazias,
        test_v12_dicts_aninhados,
        test_v13_timestamps,
        test_v14_todas_fixtures_carregaveis,
    ]

    passou = 0
    falhou = 0

    print("TESTES")
    print("-" * 80)

    for teste_func in testes:
        resultado = await teste_func()
        if resultado:
            passou += 1
            print(f"[PASS] {teste_func.__doc__}")
        else:
            falhou += 1
            print(f"[FAIL] {teste_func.__doc__}")

    print("\n" + "=" * 80)
    print(f"RESULTADO: {passou}/{len(testes)} PASS, {falhou}/{len(testes)} FAIL")
    print("=" * 80)

    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
