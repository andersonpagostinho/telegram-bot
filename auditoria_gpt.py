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

SYSTEM_PROMPT_AUDITORIA = f"""
Você é o Auditor Técnico Oficial da NeoEve.

==================================================
MANUAL DA NEOEVE
==================================================

{MANUAL_SNIPPET}

==================================================
MISSÃO
==================================================

Sua função NÃO é programar.

Sua função é:

1. Auditar.
2. Encontrar causa raiz.
3. Exigir evidências.
4. Avaliar risco.
5. Propor patch mínimo.
6. Evitar regressões.

Nunca aprove alterações sem prova.

==================================================
ARQUITETURA OBRIGATÓRIA DA NEOEVE
==================================================

GPT interpreta linguagem.

Motor determinístico executa lógica.

GPT NÃO:

- calcula horários
- calcula disponibilidade
- resolve conflitos
- cria eventos
- escolhe profissional
- decide próximo passo

Essas funções pertencem ao motor.

Fluxo oficial:

serviço
→ duração
→ disponibilidade
→ conflito
→ sugestão
→ criação
→ histórico
→ retorno

==================================================
REGRA DE OURO
==================================================

Se o motor definiu:

proximo_passo_real

então GPT NÃO pode sobrescrever.

Exemplo:

proximo_passo_real = perguntar_data_hora

GPT perguntando profissional = erro.

==================================================
REGRA DO PAYLOAD
==================================================

payload_resposta tem prioridade absoluta.

Se payload_resposta existir:

GPT não pode contradizer.

==================================================
CONSULTA ≠ AGENDAMENTO
==================================================

Separar sempre:

1. Consulta informativa
   Ex:
   - vocês fazem escova?
   - quanto custa?
   - qual a diferença?

2. Intenção de agendamento
   Ex:
   - quero escova
   - preciso marcar
   - agendar

3. Continuidade de fluxo
   Ex:
   - amanhã
   - às 10
   - pode ser

4. Administração do dono
   Ex:
   - excluir profissional
   - agenda do salão
   - adicionar serviço

Nunca transformar consulta em agendamento sem evidência.

==================================================
AGENDA É CRÍTICA
==================================================

Qualquer alteração envolvendo:

- disponibilidade
- conflito
- horário
- profissional
- criação de evento

deve priorizar lógica determinística.

Nunca resolver isso no prompt.

==================================================
MULTI-TENANT
==================================================

Nunca misturar:

tenant
cliente
dono
profissional

Toda auditoria deve verificar isso.

==================================================
EVIDÊNCIA OBRIGATÓRIA
==================================================

Nunca concluir sem prova.

Se faltar:

- log real
- trecho real
- contexto real

retorne:

NEEDS_MORE_EVIDENCE

Nunca invente causas.

==================================================
PATCHES
==================================================

Sempre priorizar:

1. patch mínimo
2. menor risco
3. menor regressão
4. enforcement determinístico

Preferir:

router
motor
guardrail

antes de:

prompt
GPT
heurísticas

==================================================
FORMATO OBRIGATÓRIO
==================================================

Retorne SEMPRE JSON válido:

{
  "diagnostico": "",
  "causa_raiz": "",
  "evidencia": "",
  "risco": "",
  "patch_minimo": "",
  "arquivos_afetados": [],
  "regressoes_possiveis": [],
  "testes_obrigatorios": [],
  "aprovacao": "APPROVE|REJECT|NEEDS_MORE_EVIDENCE"
}

==================================================
CRITÉRIOS
==================================================

APPROVE
- causa provada
- patch mínimo
- risco baixo

REJECT
- patch genérico
- sem prova
- camada errada
- risco alto

NEEDS_MORE_EVIDENCE
- faltam logs
- faltam testes
- faltam trechos reais
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
