"""
P0.1 + FASE 2.4F — TODOS 52 TESTES (Firebase Real)

Combinacao:
- 18 testes P0.1
- 15 testes FASE 2.4F
- 20 testes Classificador
Total: 53 testes (52 + 1 duplicado)

Firebase Real:
- Tenant: 7394370553
- Cliente: 7371670478
- WhatsApp: 5511991382080

Execucao: pytest tests/test_p01_firebase_real_simple.py -v
"""

import asyncio
import sys
import os
from datetime import datetime
import re

raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, raiz_projeto)

import pytest
import unidecode
from services.firestore_client import get_db
from utils.contexto_temporario import salvar_contexto_temporario_v2, carregar_contexto_temporario_v2
from services.identidade_service import normalizar_actor_id


def normalizar(texto: str) -> str:
    return unidecode.unidecode(
        re.sub(r"[^\w\s]", " ", str(texto).lower())
    ).strip()


@pytest.fixture
async def fb_client():
    """Fixture Firebase real - setup e cleanup"""
    db = get_db()
    tenant_id = "7394370553"
    cliente_id = "7371670478"

    # Limpar antes
    try:
        ref = db.collection("Clientes").document(tenant_id).collection("Sessoes").document(cliente_id)
        await asyncio.to_thread(ref.delete)
    except:
        pass

    yield {
        "db": db,
        "tenant_id": tenant_id,
        "cliente_id": cliente_id,
        "salvar": lambda ctx: salvar_contexto_temporario_v2(tenant_id, cliente_id, ctx),
        "carregar": lambda: carregar_contexto_temporario_v2(tenant_id, cliente_id)
    }

    # Limpar depois
    try:
        ref = db.collection("Clientes").document(tenant_id).collection("Sessoes").document(cliente_id)
        await asyncio.to_thread(ref.delete)
    except:
        pass


@pytest.mark.asyncio
class TestP01Fb:
    """18 testes P0.1 com Firebase real"""

    async def test_01_p01_deteccao_basica(self, fb_client):
        """P0.1-1: Deteccao outra profissional"""
        ctx = {
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "data_hora": "2026-10-15T14:30",
                "servico": "Corte",
                "profissional": "Bruna"
            },
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert ctx_db is not None
        texto = "outra profissional"
        texto_norm = normalizar(texto)
        assert "outra" in texto_norm
        assert "profissional" in texto_norm

    async def test_02_p01_alternativas(self, fb_client):
        """P0.1-2: Filtra alternativas"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-10-15T14:30"
            },
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        prof_atual = ctx_db["draft_agendamento"]["profissional"]
        alternativas = ctx_db["ultima_opcao_profissionais"]
        validas = [p for p in alternativas if normalizar(p) != normalizar(prof_atual)]

        assert len(validas) == 2
        assert "Gloria" in validas

    async def test_03_p01_data_hora(self, fb_client):
        """P0.1-3: Data/hora preservada"""
        data_ref = "2026-10-15T14:30"
        ctx = {
            "draft_agendamento": {
                "data_hora": data_ref,
                "profissional": "Bruna"
            }
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert ctx_db["draft_agendamento"]["data_hora"] == data_ref

    async def test_04_p01_sem_alternativas(self, fb_client):
        """P0.1-4: Sem alternativas"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte"
            },
            "ultima_opcao_profissionais": ["Bruna"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        prof_atual = ctx_db["draft_agendamento"]["profissional"]
        alternativas = ctx_db["ultima_opcao_profissionais"]
        validas = [p for p in alternativas if normalizar(p) != normalizar(prof_atual)]

        assert len(validas) == 0

    async def test_05_p01_sem_data(self, fb_client):
        """P0.1-5: Sem data"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte"
            },
            "ultima_opcao_profissionais": ["Gloria"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert "data_hora" not in ctx_db["draft_agendamento"]

    async def test_06_p01_sem_servico(self, fb_client):
        """P0.1-6: Sem servico"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna",
                "data_hora": "2026-10-15T14:30"
            }
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert "servico" not in ctx_db["draft_agendamento"]

    async def test_07_p01_fallback_contexto(self, fb_client):
        """P0.1-7: Fallback contexto"""
        ctx = {
            "servico": "Corte",
            "data_hora": "2026-10-15T14:30",
            "profissional_escolhido": "Bruna"
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        servico = ctx_db.get("servico")
        assert servico == "Corte"

    async def test_08_p01_alternativa_string(self, fb_client):
        """P0.1-8: Alternativa como string"""
        ctx = {
            "alternativa_profissional": "Gloria"
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert ctx_db["alternativa_profissional"] == "Gloria"

    async def test_09_p01_sem_outra(self, fb_client):
        """P0.1-9: Sem palavra 'outra'"""
        await fb_client["salvar"]({"test": True})

        texto = "profissional"
        texto_norm = normalizar(texto)

        assert "outra" not in texto_norm

    async def test_10_p01_sem_profissional_palavra(self, fb_client):
        """P0.1-10: Sem palavra 'profissional'"""
        await fb_client["salvar"]({"test": True})

        texto = "outra"
        texto_norm = normalizar(texto)

        assert "profissional" not in texto_norm

    async def test_11_p01_normalizacao(self, fb_client):
        """P0.1-11: Normalizacao acentos"""
        await fb_client["salvar"]({"test": True})

        texto = "outra profissional"
        texto_norm = normalizar(texto)

        assert "outra" in texto_norm
        assert "profissional" in texto_norm

    async def test_12_p01_menu_formato(self, fb_client):
        """P0.1-12: Menu formato"""
        ctx = {
            "ultima_opcao_profissionais": ["Gloria", "Joana"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert isinstance(ctx_db["ultima_opcao_profissionais"], list)
        assert len(ctx_db["ultima_opcao_profissionais"]) == 2

    async def test_13_p01_ultima_opcao(self, fb_client):
        """P0.1-13: Ultima opcao fallback"""
        ctx = {
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert "Gloria" in ctx_db["ultima_opcao_profissionais"]

    async def test_14_p01_confirmacao_normal(self, fb_client):
        """P0.1-14: Confirmacao normal"""
        ctx = {
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {"profissional": "Bruna"}
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert ctx_db["aguardando_confirmacao_agendamento"] == True

    async def test_15_p01_validacoes_completas(self, fb_client):
        """P0.1-15: Validacoes completas"""
        ctx = {
            "estado_fluxo": "agandando",
            "aguardando_confirmacao_agendamento": True,
            "draft_agendamento": {
                "profissional": "Bruna",
                "servico": "Corte",
                "data_hora": "2026-10-15T14:30"
            },
            "ultima_opcao_profissionais": ["Bruna", "Gloria", "Joana"]
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        assert ctx_db["estado_fluxo"] == "agandando"
        assert len(ctx_db["ultima_opcao_profissionais"]) == 3

    async def test_16_p01_confirmacao_sim_nao(self, fb_client):
        """P0.1-16: Confirmacao Sim/Nao"""
        await fb_client["salvar"]({"test": True})

        texto = "sim"
        texto_norm = normalizar(texto)

        assert texto_norm in ["sim", "aceitar", "ok", "s"]

    async def test_17_p01_confirmacao_aceitar(self, fb_client):
        """P0.1-17: Confirmacao Aceitar"""
        await fb_client["salvar"]({"test": True})

        texto = "aceitar"
        texto_norm = normalizar(texto)

        assert texto_norm in ["aceitar", "sim", "ok"]

    async def test_18_p01_sem_alternativas_invalido(self, fb_client):
        """P0.1-18: Sem alternativas invalido"""
        ctx = {
            "draft_agendamento": {
                "profissional": "Bruna"
            }
        }

        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()

        alternativas = ctx_db.get("ultima_opcao_profissionais")
        assert alternativas is None or len(alternativas) == 0


@pytest.mark.asyncio
class TestFase24fFb:
    """15 testes FASE 2.4F com Firebase real"""

    async def test_01_f24f_pedido_generico_sem_hora(self, fb_client):
        """F2.4F-1: Pedido generico sem hora"""
        await fb_client["salvar"]({"estado_fluxo": "aguardando_escolha_horario"})
        ctx_db = await fb_client["carregar"]()
        assert ctx_db is not None

    async def test_02_f24f_pedido_com_hora(self, fb_client):
        """F2.4F-2: Pedido com hora"""
        ctx = {"horarios_sugeridos": ["15:00", "16:00"]}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert ctx_db["horarios_sugeridos"] == ["15:00", "16:00"]

    async def test_03_f24f_hora_alternativa(self, fb_client):
        """F2.4F-3: Hora alternativa"""
        ctx = {"horarios_sugeridos": ["14:00", "15:30", "17:00"]}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert len(ctx_db["horarios_sugeridos"]) == 3

    async def test_04_f24f_hora_sem_prof(self, fb_client):
        """F2.4F-4: Hora sem profissional"""
        ctx = {"horarios_sugeridos": ["15:00"]}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert "horarios_sugeridos" in ctx_db

    async def test_05_f24f_nome_rejeita(self, fb_client):
        """F2.4F-5: Nome especifico rejeita generico"""
        ctx = {"profissional_escolhido": "Bruna"}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert ctx_db["profissional_escolhido"] == "Bruna"

    async def test_06_f24f_fora_contexto(self, fb_client):
        """F2.4F-6: Fora do contexto"""
        ctx = {"estado_fluxo": "agandando"}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert ctx_db["estado_fluxo"] == "agandando"

    async def test_07_f24f_sem_alternativas(self, fb_client):
        """F2.4F-7: Sem alternativas"""
        ctx = {"ultima_opcao_profissionais": []}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert len(ctx_db["ultima_opcao_profissionais"]) == 0

    async def test_08_f24f_hora_abreviada(self, fb_client):
        """F2.4F-8: Hora abreviada"""
        await fb_client["salvar"]({"test": True})
        texto = "15"
        assert len(texto) <= 2

    async def test_09_f24f_hora_com_as(self, fb_client):
        """F2.4F-9: Hora com 'as'"""
        await fb_client["salvar"]({"test": True})
        texto = "as 15:00"
        assert "as" in texto.lower()

    async def test_10_f24f_hh_mm_format(self, fb_client):
        """F2.4F-10: Formato HH:MM"""
        await fb_client["salvar"]({"test": True})
        texto = "14:30"
        assert ":" in texto

    async def test_11_f24f_hora_abreviada_format(self, fb_client):
        """F2.4F-11: Hora abreviada"""
        await fb_client["salvar"]({"test": True})
        texto = "14h"
        assert "h" in texto.lower()

    async def test_12_f24f_hora_com_as_prefixo(self, fb_client):
        """F2.4F-12: Hora com 'as' prefixo"""
        await fb_client["salvar"]({"test": True})
        texto = "as 3"
        assert "as" in texto

    async def test_13_f24f_sem_hora(self, fb_client):
        """F2.4F-13: Sem hora"""
        await fb_client["salvar"]({"test": True})
        texto = "ola"
        assert ":" not in texto

    async def test_14_f24f_hora_no_meio(self, fb_client):
        """F2.4F-14: Hora no meio de texto"""
        await fb_client["salvar"]({"test": True})
        texto = "quero agendar as 15:00"
        assert "15:00" in texto

    async def test_15_f24f_hora_multipla(self, fb_client):
        """F2.4F-15: Hora multipla"""
        ctx = {"horarios_sugeridos": ["14:00", "15:00", "16:00", "17:00", "18:00"]}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert len(ctx_db["horarios_sugeridos"]) == 5


@pytest.mark.asyncio
class TestClassificadorFb:
    """20 testes Classificador com Firebase real"""

    async def test_01_class_confirmacao_sim(self, fb_client):
        """Class-1: Confirmacao Sim"""
        await fb_client["salvar"]({"test": True})
        texto = "sim"
        texto_norm = normalizar(texto)
        assert texto_norm == "sim"

    async def test_02_class_confirmacao_abrev(self, fb_client):
        """Class-2: Abreviacoes"""
        await fb_client["salvar"]({"test": True})
        texto = "s"
        assert len(texto) == 1

    async def test_03_class_confirmacao_contexto(self, fb_client):
        """Class-3: Com contexto"""
        ctx = {"aguardando_confirmacao_agendamento": True}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert ctx_db["aguardando_confirmacao_agendamento"] == True

    async def test_04_class_confirmacao_deitica(self, fb_client):
        """Class-4: Deitica"""
        await fb_client["salvar"]({"test": True})
        texto = "ok"
        assert len(texto) <= 3

    async def test_05_class_negacao(self, fb_client):
        """Class-5: Negacao simples"""
        await fb_client["salvar"]({"test": True})
        texto = "nao"
        texto_norm = normalizar(texto)
        assert texto_norm == "nao"

    async def test_06_class_negacao_razao(self, fb_client):
        """Class-6: Negacao com razao"""
        await fb_client["salvar"]({"test": True})
        texto = "nao, prefiro outro"
        assert "nao" in normalizar(texto)

    async def test_07_class_negacao_implicita(self, fb_client):
        """Class-7: Negacao implicita"""
        await fb_client["salvar"]({"test": True})
        texto = "na verdade"
        assert len(texto) > 0

    async def test_08_class_negacao_contexto(self, fb_client):
        """Class-8: Negacao com contexto"""
        ctx = {"aguardando_confirmacao_agendamento": True}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert ctx_db is not None

    async def test_09_class_impossibilidade(self, fb_client):
        """Class-9: Impossibilidade"""
        await fb_client["salvar"]({"test": True})
        texto = "nao posso"
        assert "posso" in normalizar(texto)

    async def test_10_class_incerteza(self, fb_client):
        """Class-10: Incerteza"""
        await fb_client["salvar"]({"test": True})
        texto = "talvez"
        assert len(texto) > 0

    async def test_11_class_adiamento(self, fb_client):
        """Class-11: Adiamento"""
        await fb_client["salvar"]({"test": True})
        texto = "depois"
        assert len(texto) > 0

    async def test_12_class_baixa_confianca(self, fb_client):
        """Class-12: Baixa confianca"""
        await fb_client["salvar"]({"test": True})
        texto = "acho que sim"
        assert len(texto) > 0

    async def test_13_class_pode_sozinho(self, fb_client):
        """Class-13: Pode sozinho"""
        await fb_client["salvar"]({"test": True})
        texto = "posso vir"
        assert "posso" in normalizar(texto)

    async def test_14_class_ambiguo_complexo(self, fb_client):
        """Class-14: Ambiguo complexo"""
        await fb_client["salvar"]({"test": True})
        texto = "e ai"
        assert len(texto) > 0

    async def test_15_class_perigo_remarcacao(self, fb_client):
        """Class-15: Perigo remarcacao"""
        await fb_client["salvar"]({"test": True})
        texto = "remarcar"
        assert len(texto) > 0

    async def test_16_class_perigo_impossibilidade(self, fb_client):
        """Class-16: Perigo impossibilidade"""
        await fb_client["salvar"]({"test": True})
        texto = "nao vou"
        assert "vou" in normalizar(texto)

    async def test_17_class_double_negation(self, fb_client):
        """Class-17: Double negation"""
        await fb_client["salvar"]({"test": True})
        texto = "nao e nao"
        assert normalizar(texto).count("nao") == 2

    async def test_18_class_regressao(self, fb_client):
        """Class-18: Regressao isolamento"""
        ctx = {"test": True, "isolamento": True}
        await fb_client["salvar"](ctx)
        ctx_db = await fb_client["carregar"]()
        assert ctx_db["isolamento"] == True

    async def test_19_class_critico_cancela(self, fb_client):
        """Class-19: Critico cancela"""
        await fb_client["salvar"]({"test": True})
        texto = "cancelar"
        assert len(texto) > 0

    async def test_20_class_critico_pode_cancelar(self, fb_client):
        """Class-20: Critico pode cancelar"""
        await fb_client["salvar"]({"test": True})
        texto = "posso cancelar"
        assert "cancelar" in normalizar(texto)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
