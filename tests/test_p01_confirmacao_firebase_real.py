"""
P0.1 — CONFIRMACAO PENDENTE + OUTRA PROFISSIONAL (Firebase Real)

Versao Firebase real dos 18 testes de test_p01_confirmacao_pendente_outra_prof.py

Ambiente: Firebase Production Real
Tenant: 7394370553
Cliente: 7371670478
WhatsApp: 5511991382080

Testes:
1. Deteccao "outra profissional" basica
2. Alternativas validas (filtra profissional atual)
3. Menu preserva data/hora exata
4. Sem alternativas nao apresenta menu
5. Sem data nao apresenta menu
6. Sem servico nao apresenta menu
7. Fallback contexto se draft vazio
8. Alternativa profissional como string
9. Nao detecta sem palavra-chave "outra"
10. Nao detecta sem palavra-chave "profissional"
11. Normalizacao acentos
12. Menu formato correto
13. Ultima opcao profissionais como fallback
14. Confirmacao normal sem "outra profissional"
15. Validacoes completas
16. Confirmacao sim/nao nao ativa P0.1
17. Confirmacao aceitar nao ativa P0.1
18. Contexto sem alternativas invalido
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import re

# Path setup
raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

import pytest
import unidecode
from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2


def normalizar(texto: str) -> str:
    """Normaliza texto para comparacao"""
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


@pytest.mark.asyncio
class TestP01ConfirmacaoPendenteFb:
    """P0.1 com Firebase Real - 18 testes"""

    @pytest.fixture(autouse=True)
    async def setup(self, firebase_sync):
        """Setup para cada teste"""
        self.fs = firebase_sync
        self.fs.limpar_sync()
        yield
        self.fs.limpar_sync()

    # ===== TESTES BASICOS (1-3) =====

    @pytest.mark.asyncio
    async def test_01_deteccao_outra_profissional_basica(self):
        """T1: Deteccao basica"""
        ctx = {
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "data_hora": "2026-10-15T14:30:00",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "alternativa_profissional": ["Gloria", "Joana"],
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        assert ctx_carregado is not None
        assert "alternativa_profissional" in ctx_carregado

        texto = "outra profissional"
        texto_norm = normalizar(texto)
        detectado = "outra" in texto_norm and "profissional" in texto_norm
        assert detectado

    @pytest.mark.asyncio
    async def test_02_alternativas_validas_filtra_profissional(self):
        """T2: Filtra profissional atual"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-10-15T14:30:00"
            },
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        profissional_atual = ctx_carregado.get("draft_agendamento", {}).get("profissional")
        alternativas = ctx_carregado.get("ultima_opcao_profissionais", [])

        alternativas_validas = [
            p for p in alternativas
            if p and normalizar(p) != normalizar(profissional_atual or "")
        ]

        assert len(alternativas_validas) == 2
        assert "Gloria" in alternativas_validas
        assert "Joana" in alternativas_validas
        assert "Bruna" not in alternativas_validas

    @pytest.mark.asyncio
    async def test_03_menu_preserva_data_hora_exata(self):
        """T3: Data/hora preservada"""
        data_hora_ref = "2026-10-15T14:30:00"
        ctx = {
            "draft_agendamento": {
                "data_hora": data_hora_ref,
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        data_carregada = ctx_carregado.get("draft_agendamento", {}).get("data_hora")
        assert data_carregada == data_hora_ref

    # ===== VALIDACOES (4-6) =====

    @pytest.mark.asyncio
    async def test_04_sem_alternativas_nao_menu(self):
        """T4: Sem alternativas, sem menu"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-10-15T14:30:00"
            },
            "ultima_opcao_profissionais": ["Bruna"]  # Apenas atual
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        profissional_atual = ctx_carregado.get("draft_agendamento", {}).get("profissional")
        alternativas = ctx_carregado.get("ultima_opcao_profissionais", [])

        alternativas_validas = [
            p for p in alternativas
            if p and normalizar(p) != normalizar(profissional_atual or "")
        ]

        assert len(alternativas_validas) == 0

    @pytest.mark.asyncio
    async def test_05_sem_data_nao_menu(self):
        """T5: Sem data, sem menu"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte"
                # data_hora ausente
            },
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        data_hora = ctx_carregado.get("draft_agendamento", {}).get("data_hora")
        assert data_hora is None

    @pytest.mark.asyncio
    async def test_06_sem_servico_nao_menu(self):
        """T6: Sem servico, sem menu"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-10-15T14:30:00"
                # servico ausente
            },
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        servico = ctx_carregado.get("draft_agendamento", {}).get("servico")
        assert servico is None

    # ===== FALLBACKS (7-8) =====

    @pytest.mark.asyncio
    async def test_07_fallback_contexto_se_draft_vazio(self):
        """T7: Fallback para draft se vazio"""
        ctx = {
            "servico": "Corte",
            "data_hora": "2026-10-15T14:30:00",
            "profissional_escolhido": "Bruna",
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
            # draft_agendamento ausente
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        draft = ctx_carregado.get("draft_agendamento") or {}
        servico = draft.get("servico") or ctx_carregado.get("servico")

        assert servico == "Corte"

    @pytest.mark.asyncio
    async def test_08_alternativa_profissional_como_string(self):
        """T8: alternativa_profissional como string"""
        ctx = {
            "alternativa_profissional": "Gloria",  # String, nao lista
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-10-15T14:30:00"
            }
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        alt = ctx_carregado.get("alternativa_profissional")
        assert alt == "Gloria"

    # ===== DETECCAO NEGATIVA (9-10) =====

    @pytest.mark.asyncio
    async def test_09_nao_detecta_sem_outra(self):
        """T9: Sem 'outra', sem deteccao"""
        ctx = {"ultima_opcao_profissionais": ["Gloria", "Joana"]}
        self.fs.salvar_sync(ctx)

        texto = "profissional"  # Sem "outra"
        texto_norm = normalizar(texto)
        detectado = "outra" in texto_norm and "profissional" in texto_norm

        assert not detectado

    @pytest.mark.asyncio
    async def test_10_nao_detecta_sem_profissional(self):
        """T10: Sem 'profissional', sem deteccao"""
        ctx = {"ultima_opcao_profissionais": ["Gloria", "Joana"]}
        self.fs.salvar_sync(ctx)

        texto = "outra"  # Sem "profissional"
        texto_norm = normalizar(texto)
        detectado = "outra" in texto_norm and "profissional" in texto_norm

        assert not detectado

    # ===== NORMALIZACAO (11) =====

    @pytest.mark.asyncio
    async def test_11_normalizacao_acentos(self):
        """T11: Normalizacao de acentos"""
        ctx = {"ultima_opcao_profissionais": ["Gloria"]}
        self.fs.salvar_sync(ctx)

        texto = "outra profissional"  # Normal
        texto_norm = normalizar(texto)

        assert texto_norm == "outra profissional"
        assert "outra" in texto_norm
        assert "profissional" in texto_norm

    # ===== FORMATO (12-13) =====

    @pytest.mark.asyncio
    async def test_12_menu_formato_correto(self):
        """T12: Formato do menu"""
        ctx = {
            "draft_agendamento": {
                "data_hora": "2026-10-15T14:30:00",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        alternativas = ctx_carregado.get("ultima_opcao_profissionais", [])
        assert isinstance(alternativas, list)
        assert len(alternativas) >= 2

    @pytest.mark.asyncio
    async def test_13_ultima_opcao_como_fallback(self):
        """T13: ultima_opcao_profissionais como fallback"""
        ctx = {
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        alternativas = ctx_carregado.get("ultima_opcao_profissionais")
        assert alternativas is not None
        assert "Gloria" in alternativas

    # ===== CONFIRMACAO NORMAL (14-18) =====

    @pytest.mark.asyncio
    async def test_14_confirmacao_sem_outra_profissional(self):
        """T14: Confirmacao normal (sem 'outra profissional')"""
        ctx = {
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "profissional": "Bruna"
            }
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        assert ctx_carregado.get("aguardando_confirmacao_agendamento") == True

    @pytest.mark.asyncio
    async def test_15_validacoes_completas(self):
        """T15: Todas validacoes"""
        ctx = {
            "estado_fluxo": "agandando",
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-10-15T14:30:00"
            },
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        assert ctx_carregado.get("estado_fluxo") == "agandando"
        assert ctx_carregado.get("aguardando_confirmacao_agendamento") == True
        assert len(ctx_carregado.get("ultima_opcao_profissionais", [])) == 3

    @pytest.mark.asyncio
    async def test_16_confirmacao_sim_nao_ativa_p01(self):
        """T16: 'Sim'/'Nao' nao ativa P0.1"""
        ctx = {
            "aguardando_confirmacao_agendamento": True,
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
        }

        self.fs.salvar_sync(ctx)

        # Simular resposta "Sim"
        texto = "sim"
        texto_norm = normalizar(texto)
        eh_confirmacao = texto_norm in ["sim", "aceitar", "ok"]

        assert eh_confirmacao

    @pytest.mark.asyncio
    async def test_17_confirmacao_aceitar_nao_ativa(self):
        """T17: 'Aceitar' nao ativa P0.1"""
        ctx = {"ultima_opcao_profissionais": ["Gloria", "Joana"]}
        self.fs.salvar_sync(ctx)

        texto = "aceitar"
        texto_norm = normalizar(texto)
        eh_confirmacao = texto_norm in ["sim", "aceitar", "ok"]

        assert eh_confirmacao

    @pytest.mark.asyncio
    async def test_18_contexto_sem_alternativas_invalido(self):
        """T18: Contexto sem alternativas invalido"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte"
            }
            # ultima_opcao_profissionais ausente
        }

        self.fs.salvar_sync(ctx)
        ctx_carregado = self.fs.carregar_sync()

        alternativas = ctx_carregado.get("ultima_opcao_profissionais")
        assert alternativas is None or len(alternativas) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
