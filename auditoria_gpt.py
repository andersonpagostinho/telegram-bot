#!/usr/bin/env python3
"""
Auditor Técnico da NeoEve.

Usa GPT-4o para auditar:
- Padrões de concorrência
- Riscos de RMW (Read-Modify-Write)
- Perda de contexto de sessão
- Bugs de agendamento

Uso:
    from auditoria_gpt import auditar

    resultado = auditar(
        codigo="...trecho de código...",
        logs="...logs de execução...",
        hipotese="...hipótese do Claude..."
    )
    print(resultado)
"""

import os
import json
import httpx
from dotenv import load_dotenv
from openai import OpenAI

# Carregar variáveis de ambiente
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY não encontrada em .env")

# Inicializar cliente OpenAI com httpx (SSL verification desabilidado)
try:
    client = OpenAI(
        api_key=OPENAI_API_KEY,
        http_client=httpx.Client(verify=False)
    )
except Exception as e:
    print(f"[AVISO] Fallback para cliente OpenAI padrão: {e}")
    client = OpenAI(api_key=OPENAI_API_KEY)

# Ler o manual da secretaria para contexto
def _ler_manual_secretaria():
    """Lê o manual de comportamento do sistema."""
    try:
        from prompts.manual_secretaria import INSTRUCAO_SECRETARIA
        return INSTRUCAO_SECRETARIA[:2000]  # Primeiros 2000 chars para context
    except Exception as e:
        print(f"⚠️ Aviso: não consegui ler manual_secretaria.py: {e}")
        return ""

MANUAL_SNIPPET = _ler_manual_secretaria()

SYSTEM_PROMPT_AUDITORIA = f"""Você é auditor técnico da NeoEve.

==================================================
CONTEXTO DA ARQUITETURA
==================================================

{MANUAL_SNIPPET}

==================================================
PRINCÍPIOS DE ARQUITETURA
==================================================

- GPT interpreta linguagem natural.
- Motor determinístico executa lógica.
- **AGENDA É CRÍTICA** → prioridade máxima.
- Contexto de sessão não pode sobrescrever dados de negócio.
- Prioridade de validação: serviço → duração → disponibilidade → conflito → sugestão → criação.

==================================================
PADRÕES PERIGOSOS
==================================================

1. **RMW (Read-Modify-Write) sem lock**:
   - GET contexto do Firestore
   - UPDATE dict em memória
   - SET de volta (sem transação)
   → Risco: msg2 pode sobrescrever mudança de msg1

2. **Context switching durante await**:
   - await carregar_contexto()
   - [processamento]
   - await salvar_contexto()
   → Risco: mensagens paralelas intercaladas

3. **Perda de campo no merge**:
   - salva {{"profissional": "Bruna"}}
   - recarrega contexto
   - {{"servico"}} foi perdido se outra msg sobrescreveu

==================================================
TAREFA
==================================================

Ao receber logs, trecho de código e hipótese do Claude, você deve retornar:

1. **diagnóstico**: descreva exatamente qual é o problema
2. **risco**: classifique como P0 (crítico), P1 (alto), P2 (médio), P3 (baixo)
3. **causa_raiz**: qual é a raiz técnica
4. **padrão_detectado**: qual dos padrões perigosos foi acionado
5. **patch_mínimo**: sugestão de fix incremental
6. **regressões_possíveis**: que outras coisas podem quebrar
7. **aprovação**: YES/NO/CONDITIONAL (com justificativa)

Retorne SEMPRE em JSON válido com esses campos exatos.

==================================================
CRITÉRIOS DE APROVAÇÃO
==================================================

✅ APROVE (YES) se:
- O problema é claramente identificado
- O patch é mínimo e incremental
- Nenhuma regressão conhecida
- Agenda continua segura

❌ REJEITE (NO) se:
- O patch é muito agressivo
- Há risco de perda de dados
- Complexidade aumenta muito
- Agenda fica menos segura

⚠️ CONDICIONAL (CONDITIONAL) se:
- Precisa de mais evidência (logs reais, teste)
- Patch é bom mas precisa validação
- Alternativa melhor existe
"""

def auditar(codigo: str, logs: str = "", hipotese: str = "") -> dict:
    """
    Audita código, logs e hipótese usando GPT-4o.

    Args:
        codigo: Trecho de código Python a auditar
        logs: Logs de execução (opcional)
        hipotese: Hipótese do Claude (opcional)

    Returns:
        dict com campos: diagnóstico, risco, causa_raiz, padrão_detectado,
                         patch_mínimo, regressões_possíveis, aprovação
    """

    # Montar mensagem do usuário
    user_message = f"""
==================================================
AUDITORIA SOLICITADA
==================================================

CÓDIGO:
```python
{codigo}
```

LOGS (se houver):
```
{logs if logs else "[nenhum log fornecido]"}
```

HIPÓTESE:
{hipotese if hipotese else "[nenhuma hipótese fornecida]"}

==================================================
Retorne a análise em JSON válido com campos:
- diagnóstico
- risco (P0/P1/P2/P3)
- causa_raiz
- padrão_detectado
- patch_mínimo (ou "sem patch necessário")
- regressões_possíveis
- aprovação (YES/NO/CONDITIONAL)
- justificativa (breve explicação)
==================================================
"""

    print("[ENVIANDO] Auditoria para GPT-4o...")
    print(f"   Codigo: {len(codigo)} chars | Logs: {len(logs)} chars | Hipotese: {len(hipotese)} chars")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_AUDITORIA},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Determinístico
            top_p=0.95,
            timeout=60
        )

        # Extrair resposta
        resposta_texto = response.choices[0].message.content.strip()

        print("[OK] Resposta recebida do GPT-4o")

        # Tentar parsear como JSON
        try:
            resultado = json.loads(resposta_texto)
        except json.JSONDecodeError:
            # Se não for JSON válido, retornar como texto
            print("[AVISO] Resposta não é JSON válido, retornando como texto")
            resultado = {
                "resposta_bruta": resposta_texto,
                "erro": "resposta não foi JSON válido"
            }

        return resultado

    except Exception as e:
        print(f"[ERRO] Não consegui chamar OpenAI: {e}")
        print("[FALLBACK] Retornando análise local...")

        # Fallback: análise baseada em padrões locais
        return _analisar_localmente(codigo, logs, hipotese)

def _analisar_localmente(codigo: str, logs: str, hipotese: str) -> dict:
    """
    Análise local quando OpenAI não estiver disponível.
    Detecta padrões conhecidos de RMW e concorrência.
    """

    # Detectar RMW
    tem_rmw = ("await" in codigo and "buscar" in codigo and "atualizar" in codigo)
    tem_await_duplo = (codigo.count("await ") > 1)
    tem_salvar_carregar_sequencial = (
        "salvar_contexto" in codigo and "carregar_contexto" in codigo
    )

    risco = "P0" if tem_rmw else "P1" if tem_await_duplo else "P2"

    return {
        "diagnóstico": "Padrão RMW detectado: GET → UPDATE → SET sem lock" if tem_rmw else "Possível context switching em awaits múltiplos",
        "risco": risco,
        "causa_raiz": "Falta de sincronização entre leitura e escrita no Firestore" if tem_rmw else "Event loop Python permite intercalação de coroutines",
        "padrão_detectado": "RMW sem transação" if tem_rmw else "Context switching em await",
        "patch_mínimo": "Implementar atualizar_contexto_temporario(patch) para update parcial" if tem_rmw else "Adicionar asyncio.Lock por user_id",
        "regressões_possíveis": ["Latência adicional em lock", "Possível deadlock se mal implementado"],
        "aprovação": "CONDITIONAL",
        "justificativa": "Análise local: precisa validação com logs reais. Faça teste de 3 mensagens rápidas.",
        "modo": "FALLBACK_LOCAL"
    }

if __name__ == "__main__":
    # Teste simples
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("[TESTE] auditoria_gpt.py\n")

    codigo_teste = """
async def salvar_contexto_temporario(user_id: str, contexto: dict):
    path = f"Clientes/{user_id}/MemoriaTemporaria/contexto"

    # ⚠️ PADRÃO RMW SEM LOCK
    atual = await buscar_dado_em_path(path) or {}
    atual.update(contexto)
    return await atualizar_dado_em_path(path, atual)
"""

    hipotese_teste = """
Suspeita: múltiplas mensagens do mesmo usuário podem ser processadas em paralelo
no event loop Python. Se msg1 e msg2 chegarem em <1s, ambas podem fazer GET
do contexto ANTES de qualquer uma fazer SET. msg2 então sobrescreve msg1.
"""

    resultado = auditar(
        codigo=codigo_teste,
        hipotese=hipotese_teste
    )

    print("\n" + "="*80)
    print("RESULTADO DA AUDITORIA")
    print("="*80)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
