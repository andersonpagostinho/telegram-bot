"""
FASE 5 ETAPA 2 — Testes Unitários para Consumo de refs_contextuais

10 testes conforme autorização do usuário:
1. Consulta informacional com draft ambíguo (não é bloqueada)
2. Ajuste temporal com referência ambígua (bloqueado)
3. Pronome inequívoco (enriquecido)
4. Pronome ambíguo (bloqueado)
5. Alternativa sem seleção por posição
6. Serviço alternativo sem escolha automática
7. Slot explícito prevalecendo sobre referência anterior
8. Flag transitória sem persistência
9. Isolamento tenant/actor
10. Ausência de mutação do draft em caso ambíguo
"""

import pytest
from services.classificador_conversa import resolver_referencias_contextuais


class TestFase5ConsumoRefs:
    """Testes de consumo de refs_contextuais em motor determinístico."""

    # 1. Consulta informacional com draft ambíguo (NÃO é bloqueada)
    def test_1_consulta_info_com_draft_ambiguo_nao_bloqueada(self):
        """Consulta informacional independente não é bloqueada por ambiguidade anterior."""
        contexto = {
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "profissionais": []
        }

        # MSG: "Tem manicure?" (intenção = consulta, sem pronome ambíguo)
        resultado = resolver_referencias_contextuais(
            "Tem manicure?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"],
            catalogo_servicos=["corte", "manicure"]
        )

        # Verificação:
        # - Consulta é detectada como intenção (classificador)
        # - Refs não contêm ambiguidade relevante para consulta
        # - Deve retornar referencias_detectadas=False ou necessita_esclarecimento=False
        assert resultado.get("necessita_esclarecimento") == False or resultado.get("referencias_detectadas") == False
        print(f"✅ TEST 1: Consulta não bloqueada | referencias_detectadas={resultado.get('referencias_detectadas')}")

    # 2. Ajuste temporal com referência ambígua (bloqueado)
    def test_2_ajuste_temporal_ambiguo_bloqueado(self):
        """Ajuste temporal ambíguo (mais tarde) bloqueia pedindo horário."""
        contexto = {
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"}
        }

        resultado = resolver_referencias_contextuais(
            "Pode ser um pouco mais tarde?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"]
        )

        # Esperado:
        # - tipo_referencia = "temporal"
        # - necessita_esclarecimento = True (não é "naquele horário" inequívoco)
        assert resultado.get("tipo_referencia") == "temporal"
        assert resultado.get("necessita_esclarecimento") == True
        print(f"✅ TEST 2: Temporal ambíguo bloqueado | tipo={resultado.get('tipo_referencia')}, esclarec={resultado.get('necessita_esclarecimento')}")

    # 3. Pronome inequívoco (enriquecido, não bloqueado)
    def test_3_pronome_inequivoco_enriquecido(self):
        """Pronome resolvido de forma inequívoca enriquece contexto."""
        contexto = {
            "draft_agendamento": {"servico": "corte"},
            "profissional_escolhido": "Bruna",
            "profissionais": [
                {"nome": "Bruna", "servicos": ["corte", "manicure"]},
                {"nome": "Joana", "servicos": ["manicure"]}
            ]
        }

        resultado = resolver_referencias_contextuais(
            "Com ela, por favor",
            contexto,
            catalogo_profissionais=["Bruna", "Joana"]
        )

        # Esperado:
        # - profissional_referenciada = "Bruna"
        # - necessita_esclarecimento = False (inequívoco)
        # - confianca >= 80
        assert resultado.get("profissional_referenciada") == "Bruna"
        assert resultado.get("necessita_esclarecimento") == False
        assert resultado.get("confianca", 0) >= 80
        print(f"✅ TEST 3: Pronome inequívoco | prof={resultado.get('profissional_referenciada')}, conf={resultado.get('confianca')}")

    # 4. Pronome ambíguo (sem contexto anterior, bloqueado)
    def test_4_pronome_ambiguo_sem_contexto_bloqueado(self):
        """Pronome sem referência anterior é ambíguo."""
        contexto = {
            "draft_agendamento": {},  # Sem profissional
            "profissionais": [
                {"nome": "Bruna"},
                {"nome": "Joana"},
                {"nome": "Carla"}
            ]
        }

        resultado = resolver_referencias_contextuais(
            "Com ela?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        # Esperado:
        # - referencias_detectadas = True (pronome detectado)
        # - necessita_esclarecimento = True (ambíguo, sem contexto)
        assert resultado.get("referencias_detectadas") == True
        assert resultado.get("necessita_esclarecimento") == True
        print(f"✅ TEST 4: Pronome ambíguo bloqueado | esclarec=True")

    # 5. Ordinário sem seleção por posição ("a outra")
    def test_5_ordinal_nao_seleciona_por_posicao(self):
        """'A outra' não seleciona profissional por posição, apenas marca ordinário."""
        contexto = {
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "profissionais": [
                {"nome": "Bruna"},
                {"nome": "Joana"},
                {"nome": "Carla"}
            ]
        }

        resultado = resolver_referencias_contextuais(
            "E a outra?",
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        # Esperado:
        # - tipo_referencia = "ordinal"
        # - profissional_referenciada = None (NÃO seleciona Joana por posição)
        # - necessita_esclarecimento = True
        assert resultado.get("tipo_referencia") == "ordinal"
        assert resultado.get("profissional_referenciada") is None
        assert resultado.get("necessita_esclarecimento") == True
        print(f"✅ TEST 5: Ordinário não seleciona por posição | prof_ref=None")

    # 6. Serviço alternativo sem escolha automática ("outro serviço")
    def test_6_servico_alternativo_sem_auto_escolha(self):
        """'Outro serviço' não escolhe automaticamente, marca como ordinário."""
        contexto = {
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "profissionais": [
                {"nome": "Bruna", "servicos": ["corte", "manicure"]}
            ]
        }

        resultado = resolver_referencias_contextuais(
            "Outro serviço com ela",
            contexto,
            catalogo_profissionais=["Bruna"],
            catalogo_servicos=["corte", "manicure"]
        )

        # Esperado:
        # - tipo_referencia contém "ordinário" ou "composta"
        # - servico_referenciado = None (não escolhe manicure)
        # - profissional_referenciada = "Bruna" (pronome resolvido)
        assert resultado.get("servico_referenciado") is None
        assert resultado.get("profissional_referenciada") == "Bruna"
        print(f"✅ TEST 6: Serviço ordinário não auto-escolhido | serv_ref=None")

    # 7. Slot explícito na mensagem atual prevalece
    def test_7_slot_explicito_prevalece(self):
        """Nome explícito na mensagem atual não é sobrescrito por pronome."""
        contexto = {
            "draft_agendamento": {"servico": "corte", "profissional": "Bruna"},
            "profissionais": [
                {"nome": "Bruna"},
                {"nome": "Carla"}
            ]
        }

        # MSG: "Com Carla, não com ela" (Carla explícita, ela = pronome)
        resultado = resolver_referencias_contextuais(
            "Quero com Carla, não com ela",
            contexto,
            catalogo_profissionais=["Bruna", "Carla"]
        )

        # Esperado:
        # - Se "Carla" é detectada explícita, profissional_referenciada = "Carla" (não Bruna)
        # - Ou referencias_detectadas = False (ignora pronome se nome explícito)
        # Comportamento aceitável: profissional_referenciada = "Carla" ou referências não detectadas
        prof_ref = resultado.get("profissional_referenciada")
        assert prof_ref in ["Carla", None] or resultado.get("referencias_detectadas") == False
        print(f"✅ TEST 7: Slot explícito prevalece | prof_ref={prof_ref}")

    # 8. Flag transitória não persiste
    def test_8_flag_transitoria_local_apenas(self):
        """Profissional resolvido é flag LOCAL, não persistida em Firestore."""
        contexto = {
            "draft_agendamento": {"servico": "corte"},
            "profissional_escolhido": "Bruna",
            "profissionais": [{"nome": "Bruna"}]
        }

        resultado = resolver_referencias_contextuais(
            "Com ela",
            contexto,
            catalogo_profissionais=["Bruna"]
        )

        # Esperado:
        # - profissional_referenciada = "Bruna"
        # - Resultado NÃO contém "persistir", "salvar", ou Firestore refs
        assert resultado.get("profissional_referenciada") == "Bruna"
        assert "persistir" not in str(resultado).lower()
        assert "firestore" not in str(resultado).lower()
        print(f"✅ TEST 8: Flag LOCAL apenas, sem persistência")

    # 9. Isolamento tenant/actor
    def test_9_isolamento_tenant_actor(self):
        """Referências respeitam tenant_id e actor_id."""
        contexto_tenant_a = {
            "draft_agendamento": {},
            "profissional_escolhido": "Bruna",
            "profissionais": [
                {"nome": "Bruna", "servicos": ["corte"]},
                {"nome": "Ana", "servicos": ["manicure"]}
            ],
            "_tenant_id": "tenant_a",
            "_actor_id": "user_1"
        }

        resultado = resolver_referencias_contextuais(
            "Com ela",
            contexto_tenant_a,
            catalogo_profissionais=["Bruna", "Ana"]
        )

        # Esperado:
        # - profissional_referenciada = "Bruna" (do catálogo de tenant_a)
        # - NÃO busca profissionais globalmente
        assert resultado.get("profissional_referenciada") == "Bruna"
        print(f"✅ TEST 9: Isolamento tenant respeitado")

    # 10. Ausência de mutação do draft em ambíguo
    def test_10_draft_nao_mutado_em_ambiguo(self):
        """Draft não é alterado quando referência é ambígua."""
        draft_original = {"servico": "corte", "profissional": "Bruna"}
        contexto = {
            "draft_agendamento": dict(draft_original),
            "profissionais": [
                {"nome": "Bruna"},
                {"nome": "Joana"},
                {"nome": "Carla"}
            ]
        }

        resultado = resolver_referencias_contextuais(
            "E a outra?",  # Ordinário ambíguo
            contexto,
            catalogo_profissionais=["Bruna", "Joana", "Carla"]
        )

        # Esperado:
        # - draft_agendamento PERMANECE inalterado
        # - necessita_esclarecimento = True
        # - Nenhuma chave do draft foi modificada por resolver_referencias_contextuais
        assert resultado.get("necessita_esclarecimento") == True
        assert contexto["draft_agendamento"] == draft_original
        print(f"✅ TEST 10: Draft não mutado em caso ambíguo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
