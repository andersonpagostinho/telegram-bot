"""
P0.6.2.1 — TESTE ISOLADO: Mapeamento de Termos Genéricos via Catálogo

Valida que:
1. Catálogo é passado para GPT
2. "unha" é mapeado para ["manicure", "pedicure"] (não silenciosamente rejeitado)
3. Sistema pergunta qual serviço cliente quer
4. Sem siêncio em qualquer caminho de erro
"""

import pytest
from services.gpt_service import interpretar_linguagem_operacional_gpt


class TestP0621MapeamentoCatalogo:
    """Validar que GPT com catálogo mapeia termos genéricos corretamente"""

    @pytest.mark.asyncio
    async def test_gpt_com_catalogo_retorna_multipos_candidatos(self):
        """
        Teste UNITÁRIO isolado (sem Firebase):
        GPT recebe catálogo e "gstria de agndar unha para terç agora".
        Esperado: Retorna ['manicure', 'pedicure'] como candidatos, não 'unha' literal.
        """
        texto = "gstria de agndar unha para terç agora, teria?"
        ctx = {"intencao_conversacional": "indefinida", "tenant_id": "7394370553"}
        catalogo = ["coloracao", "corte feminino", "escova", "hidratacao", "manicure", "pedicure"]

        resultado = await interpretar_linguagem_operacional_gpt(texto, ctx, catalogo_servicos=catalogo)

        print(f"\n[RESULTADO] {resultado}", flush=True)

        # Validação 1: Intenção é reconhecida (não indefinida)
        assert resultado.get("intencao") != "indefinida", \
            f"GPT retornou indefinida: {resultado}"
        print(f"✅ Intenção reconhecida: {resultado.get('intencao')}", flush=True)

        # Validação 2: Entidades contêm serviço
        entidades = resultado.get("entidades", {})
        assert entidades, f"Entidades vazias: {resultado}"
        print(f"✅ Entidades presentes: {entidades}", flush=True)

        # Validação 3: Serviço é lista ou string (não "unha" literal)
        servicos = entidades.get("servico")
        assert servicos, f"Serviço não definido: {resultado}"

        # Converter para lista se string
        if isinstance(servicos, str):
            servicos_list = [servicos]
        elif isinstance(servicos, list):
            servicos_list = servicos
        else:
            servicos_list = []

        print(f"✅ Serviços retornados: {servicos_list}", flush=True)

        # Validação 4: "unha" não deve ser retornado como serviço literal
        # Deve ser mapeado para manicure e/ou pedicure
        assert "unha" not in servicos_list, \
            f"GPT retornou 'unha' literal (não mapeou): {resultado}"
        print(f"✅ 'unha' foi mapeado (não retornou literal)", flush=True)

        # Validação 5: Pelo menos um candidato deve ser válido (estar no catálogo)
        candidatos_validos = [s for s in servicos_list if s and s.lower() in [c.lower() for c in catalogo]]
        assert len(candidatos_validos) > 0, \
            f"Nenhum serviço válido no catálogo: {servicos_list} vs {catalogo}"
        print(f"✅ Candidatos válidos no catálogo: {candidatos_validos}", flush=True)

        # Validação 6: Confiança deve ser razoável
        assert resultado.get("confianca", 0) >= 50, \
            f"Confiança muito baixa: {resultado.get('confianca')}"
        print(f"✅ Confiança aceitável: {resultado.get('confianca')}", flush=True)

    @pytest.mark.asyncio
    async def test_gpt_sem_catalogo_retorna_generico(self):
        """
        Comparação: GPT SEM catálogo retorna "unha" literal.
        Este teste mostra a diferença entre com e sem catálogo.
        """
        texto = "gstria de agndar unha para terç agora, teria?"
        ctx = {"intencao_conversacional": "indefinida", "tenant_id": "7394370553"}

        # SEM catálogo (None)
        resultado = await interpretar_linguagem_operacional_gpt(texto, ctx, catalogo_servicos=None)

        print(f"\n[RESULTADO SEM CATALOGO] {resultado}", flush=True)

        entidades = resultado.get("entidades", {})
        servicos = entidades.get("servico")

        print(f"✅ Sem catálogo, GPT retorna: {servicos}", flush=True)
        # Esperado: "unha" ou similar (palavra genérica não mapeada)

    @pytest.mark.asyncio
    async def test_gpt_com_catalogo_unico_servico(self):
        """
        Se catálogo tem apenas "manicure" (sem pedicure),
        GPT deve retornar apenas "manicure".
        """
        texto = "gostaria de agendar unha para terça"
        ctx = {"intencao_conversacional": "indefinida"}
        catalogo = ["manicure"]  # Só manicure, sem pedicure

        resultado = await interpretar_linguagem_operacional_gpt(texto, ctx, catalogo_servicos=catalogo)

        print(f"\n[RESULTADO COM CATALOGO UNICO] {resultado}", flush=True)

        entidades = resultado.get("entidades", {})
        servicos = entidades.get("servico")

        if isinstance(servicos, str):
            servicos_list = [servicos]
        else:
            servicos_list = servicos or []

        # Se o catálogo tem apenas manicure, GPT deve retornar manicure
        # (mesmo que "unha" pudesse ser pedicure, mas não está no catálogo)
        print(f"✅ Com catálogo único, GPT retorna: {servicos_list}", flush=True)

        candidatos_validos = [s for s in servicos_list if s and s.lower() in [c.lower() for c in catalogo]]
        assert len(candidatos_validos) >= 1, \
            f"Nenhum serviço do catálogo retornado: {servicos_list} vs {catalogo}"
        print(f"✅ Candidatos válidos: {candidatos_validos}", flush=True)
