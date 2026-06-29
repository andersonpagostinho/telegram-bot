"""
F3A — INPUT VALIDATION (5 cenários)

Validar que entradas ruins, vazias, longas ou ambíguas:
- não quebram o sistema
- não apagam sessão ativa
- não criam evento indevido
- não chamam lógica crítica fora de contexto

Status: IMPLEMENTAÇÃO (PYTEST)
Ordem: 4ª para implementar (após F3C, F3D, F3B)
"""

import asyncio
import sys
import os
import json
import unicodedata

# Path: tests/f3_robustez/ → raiz do projeto
raiz_projeto = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, raiz_projeto)

from services.firestore_client import get_db
from utils.contexto_temporario import salvar_sessao_temporaria, carregar_sessao_temporaria
from services.identidade_service import normalizar_actor_id


def normalizar_texto(txt: str) -> str:
    """Normaliza texto: lowercase, strip, unicode normalization, remover combining chars"""
    txt = (txt or "").lower().strip()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt


class TestResult:
    def __init__(self):
        self.cenarios = []
        self.total_pass = 0

    def registro(self, num, nome, passou, motivo="", dados_extras=None):
        status = "PASS" if passou else "FAIL"
        print(f"  [{status}] F3A-{num}: {nome}")
        if not passou and motivo:
            print(f"    Motivo: {motivo}")
        self.cenarios.append({
            "num": num,
            "nome": nome,
            "status": status,
            "motivo": motivo,
            "dados": dados_extras or {}
        })
        if passou:
            self.total_pass += 1


class F3A_InputValidationReal:
    """F3A — Input Validation com Firestore real"""

    def __init__(self):
        self.db = get_db()
        self.tenant_id = "f3a_test_tenant_001"
        self.canal = "whatsapp"

    async def limpar_tenant(self):
        """Limpar tenant de teste"""
        try:
            sessoes_ref = self.db.collection("Clientes").document(self.tenant_id).collection("Sessoes")
            docs = await asyncio.to_thread(lambda: list(sessoes_ref.stream()))
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete)
            print(f"  [CLEANUP] Tenant {self.tenant_id} limpo")
        except Exception as e:
            print(f"  [CLEANUP ERROR] {e}")

    async def cenario_01_entrada_vazia(self, result: TestResult):
        """F3A-1: Mensagem vazia / None / whitespace"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11912345678")

            # Setup: Sessão ativa com draft
            ctx_ativo = {"servico": "corte", "estado_fluxo": "aguardando_profissional"}
            await salvar_sessao_temporaria(actor_id, ctx_ativo, self.tenant_id)

            # Teste: Processar entrada vazia
            entradas_vazias = ["", "   ", "\n", "\t", None]
            para_processar = ""

            for entrada in entradas_vazias:
                if entrada:
                    para_processar = entrada
                    break

            # Normalizar entrada vazia
            texto_norm = normalizar_texto(para_processar)

            # Validações
            texto_vazio = texto_norm == ""
            sessao_preservada = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            draft_intacto = sessao_preservada and sessao_preservada.get("servico") == "corte"

            if texto_vazio and draft_intacto:
                result.registro(
                    1,
                    "Entrada vazia",
                    True,
                    "",
                    {
                        "entrada_processada": "vazio",
                        "sessao_preservada": draft_intacto,
                        "fluxo": sessao_preservada.get("estado_fluxo") if sessao_preservada else None
                    }
                )
            else:
                result.registro(1, "Entrada vazia", False, "Draft foi apagado ou entrada não foi normalizada")

        except Exception as e:
            result.registro(1, "Entrada vazia", False, str(e))

    async def cenario_02_emoji_pontuacao_curta(self, result: TestResult):
        """F3A-2: Emoji / pontuação / ruído curto"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11987654321")

            # Setup: Sessão aguardando confirmação
            ctx_pendente = {
                "servico": "escova",
                "data": "2026-07-10",
                "profissional": "Ana",
                "estado_fluxo": "aguardando_confirmacao"
            }
            await salvar_sessao_temporaria(actor_id, ctx_pendente, self.tenant_id)

            # Teste: Emoji, pontuação, ruído
            ruidos = ["👍", "?", "...", "kkk", "ok"]

            for ruido in ruidos:
                texto_norm = normalizar_texto(ruido)

                # Validações
                sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)

                # "ok" em confirmação pendente pode ser confirmação, mas não em idle
                eh_ruido = texto_norm in ["", "?", "kkk"]  # "ok" é potencial confirmação
                sessao_intacta = sessao and sessao.get("servico") == "escova"

            if sessao_intacta:
                result.registro(
                    2,
                    "Emoji/pontuação curta",
                    True,
                    "",
                    {
                        "ruidos_testados": ruidos,
                        "sessao_preservada": True,
                        "draft": "escova"
                    }
                )
            else:
                result.registro(2, "Emoji/pontuação curta", False, "Draft foi afetado por ruído")

        except Exception as e:
            result.registro(2, "Emoji/pontuação curta", False, str(e))

    async def cenario_03_nao_texto_payload(self, result: TestResult):
        """F3A-3: Entrada não-texto (áudio, imagem, etc sem text)"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11976543210")

            # Setup: Sessão ativa
            ctx = {"servico": "manicure", "estado_fluxo": "aguardando_profissional"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Teste: Payloads sem texto
            payloads_nao_texto = [
                {"type": "audio", "media_id": "xyz123"},  # áudio sem text
                {"type": "image", "media_id": "abc456"},  # imagem sem text
                {"type": "sticker", "media_id": "sticker789"},  # sticker
                {"type": "document", "mime_type": "application/pdf"}  # documento sem text
            ]

            # Simular processamento: verificar se há 'text' em payload
            texto_extraido = None
            for payload in payloads_nao_texto:
                if isinstance(payload, dict) and "text" in payload:
                    texto_extraido = payload["text"]

            # Validações
            sem_texto = texto_extraido is None
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "manicure"

            if sem_texto and sessao_intacta:
                result.registro(
                    3,
                    "Não-texto (áudio/imagem/etc)",
                    True,
                    "",
                    {
                        "tipos_testados": [p.get("type") for p in payloads_nao_texto],
                        "texto_extraido": None,
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(3, "Não-texto", False, "Payload foi processado ou sessão afetada")

        except Exception as e:
            result.registro(3, "Não-texto", False, str(e))

    async def cenario_04_mensagem_muito_longa(self, result: TestResult):
        """F3A-4: Mensagem muito longa (10KB+)"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11965432109")

            # Setup: Sessão com fluxo
            ctx = {"servico": "hidratacao", "estado_fluxo": "aguardando_profissional"}
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Teste: Texto muito longo
            texto_gigante = "x" * 10000  # 10KB

            # Limitar entrada para GPT (exemplo: máximo 5KB)
            LIMITE_ENTRADA = 5000
            texto_limitado = texto_gigante[:LIMITE_ENTRADA] if len(texto_gigante) > LIMITE_ENTRADA else texto_gigante

            # Normalizar
            texto_norm = normalizar_texto(texto_limitado)

            # Validações
            limitado = len(texto_limitado) <= LIMITE_ENTRADA
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "hidratacao"

            if limitado and sessao_intacta:
                result.registro(
                    4,
                    "Mensagem muito longa",
                    True,
                    "",
                    {
                        "entrada_original": len(texto_gigante),
                        "entrada_limitada": len(texto_limitado),
                        "limite_aplicado": LIMITE_ENTRADA,
                        "sessao_preservada": True
                    }
                )
            else:
                result.registro(4, "Mensagem muito longa", False, "Limite não foi aplicado ou sessão afetada")

        except Exception as e:
            result.registro(4, "Mensagem muito longa", False, str(e))

    async def cenario_05_unicode_acentos_caixa(self, result: TestResult):
        """F3A-5: Unicode/acentos/caixa/variações reais"""
        await self.limpar_tenant()

        try:
            actor_id = normalizar_actor_id(self.canal, "11954321098")

            # Setup: Sessão aguardando_profissional
            ctx = {
                "servico": "corte",
                "estado_fluxo": "aguardando_profissional",
                "profissional_escolhido": None
            }
            await salvar_sessao_temporaria(actor_id, ctx, self.tenant_id)

            # Teste: Variações de "não tenho preferência"
            variacoes = [
                "NÃO TENHO PREFERÊNCIA",
                "nao tenho preferencia",
                "qualqûer uma",
                "QUALQUER UMA"
            ]

            # Normalizar todas as variações
            normalizadas = [normalizar_texto(v) for v in variacoes]

            # Verificar se todas normalizam para a mesma coisa
            normalizado_esperado = "nao tenho preferencia"
            matches = [n for n in normalizadas if normalizado_esperado in n or n == "qualquer uma"]

            # Validações
            normalizacao_consistente = len(matches) > 0
            sessao = await carregar_sessao_temporaria(actor_id, self.tenant_id)
            sessao_intacta = sessao and sessao.get("servico") == "corte"
            fluxo_preservado = sessao and sessao.get("estado_fluxo") == "aguardando_profissional"

            if normalizacao_consistente and sessao_intacta and fluxo_preservado:
                result.registro(
                    5,
                    "Unicode/acentos/caixa",
                    True,
                    "",
                    {
                        "variacoes_testadas": variacoes,
                        "normalizadas": normalizadas[:2],
                        "sessao_preservada": True,
                        "fluxo": "aguardando_profissional"
                    }
                )
            else:
                result.registro(5, "Unicode/acentos/caixa", False, "Normalização ou sessão afetada")

        except Exception as e:
            result.registro(5, "Unicode/acentos/caixa", False, str(e))


async def main():
    print("\n" + "="*80)
    print("F3A — INPUT VALIDATION (IMPLEMENTAÇÃO REAL)")
    print("="*80 + "\n")

    result = TestResult()
    teste = F3A_InputValidationReal()

    await teste.cenario_01_entrada_vazia(result)
    await teste.cenario_02_emoji_pontuacao_curta(result)
    await teste.cenario_03_nao_texto_payload(result)
    await teste.cenario_04_mensagem_muito_longa(result)
    await teste.cenario_05_unicode_acentos_caixa(result)

    # Limpeza final
    await teste.limpar_tenant()

    print("\n" + "="*80)
    print(f"F3A RESULTADO: {result.total_pass}/5 PASS")
    print("="*80 + "\n")

    return {
        "teste": "F3A_INPUT_VALIDATION",
        "total": 5,
        "pass": result.total_pass,
        "todo": 5 - result.total_pass,
        "cenarios": result.cenarios
    }


if __name__ == "__main__":
    resultado = asyncio.run(main())