# 🔐 AUDITORIA: Configuração OpenAI

**Objetivo:** Rastrear qual configuração OpenAI está sendo usada
**Data:** 2026-06-02
**Método:** Análise de código e arquivos de configuração (sem alterar)

---

## 1. Clientes OpenAI Identificados

### Cliente Principal (PRODUÇÃO)

**Arquivo:** `services/gpt_client.py`  
**Linhas:** 1-7

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**Características:**
- ✅ Assíncrono (AsyncOpenAI)
- ✅ Carregamento direto: `os.getenv("OPENAI_API_KEY")`
- ✅ SEM load_dotenv() (depende de load_dotenv em main.py)
- ✅ SEM httpx customizado
- ✅ SEM verify=False
- ✅ SEM fallback configurado

**Uso:** Importado por `services/gpt_service.py` para chamadas ao GPT

---

### Cliente Secundário (AUDITORIA)

**Arquivo:** `auditoria_gpt.py`  
**Linhas:** 22-43

```python
from openai import OpenAI
from dotenv import load_dotenv

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
```

**Características:**
- ✅ Síncrono (OpenAI)
- ✅ load_dotenv() local (linhas 28-29)
- ✅ Validação se OPENAI_API_KEY existe (linhas 31-33)
- ⚠️ httpx com verify=False (SSL verification desabilidado!)
- ✅ Fallback para cliente padrão sem httpx (linhas 42-43)
- ⚠️ Apenas para auditoria, não para produção

**Uso:** Script separado, não usado em produção

---

## 2. Variável de Ambiente Principal

### OPENAI_API_KEY

**Origem:** `.env`  
**Localização de arquivo:** `.env` (raiz do projeto)  
**Linhas no .env:** Linha 15

**Estrutura:**
```
OPENAI_API_KEY=OPENAI_API_KEY_REMOVIDA
```

**Tipo:** API Key de projeto OpenAI (é uma chave de projeto da OpenAI)

**Como é carregada:**
1. `main.py` linha 39: `load_dotenv()`
2. `services/gpt_client.py` linha 6: `os.getenv("OPENAI_API_KEY")`
3. Valor é passado ao client AsyncOpenAI

**Cadeia de carregamento:**
```
.env (arquivo físico)
  ↓
load_dotenv() [main.py:39]
  ↓
sys.environ["OPENAI_API_KEY"]
  ↓
os.getenv("OPENAI_API_KEY") [gpt_client.py:6]
  ↓
AsyncOpenAI(api_key=...)
```

---

## 3. Configuração no Render

**Arquivo:** `render.yaml`  
**Status:** Conflito de merge (linhas 1-19)

**O que mostra:**
```yaml
services:
  - type: web
    name: telegram-bot
    env: python
    buildCommand: cd telegram-bot-organizado && pip install -r requirements.txt
    startCommand: cd telegram-bot-organizado && python main.py
    envVars:
      - key: RENDER_SERVICE_NAME
        value: telegram-bot-a7a7
```

**Achado:** OPENAI_API_KEY **NÃO** está configurada em render.yaml

**Implicação:** A variável OPENAI_API_KEY deve estar configurada no **painel web do Render** (não em render.yaml), ou o servidor em produção não teria acesso à chave.

---

## 4. Configuração em Produção (Render)

**Localização:** Painel do Render (não rastreável no código)

**Como configurar em Render:**
```
Render Dashboard
  ↓ Web Service: telegram-bot
  ↓ Environment
  ↓ Add Environment Variable
  ↓ OPENAI_API_KEY = <OPENAI_PROJECT_KEY>
```

**Status:** ⚠️ Não confirmado se está de fato configurada no Render

---

## 5. Múltiplas Chaves? Fallbacks?

### Resultado da Auditoria:

**Múltiplas chaves OpenAI:** ❌ NÃO

- Apenas uma variável `OPENAI_API_KEY` em todo o projeto
- Nenhuma variável alternativa (`OPENAI_API_KEY_BACKUP`, `OPENAI_API_KEY_FALLBACK`, etc)
- Nenhuma chave hardcoded

**Fallback para outra chave:** ❌ NÃO

- `gpt_client.py`: Sem fallback configurado
- `auditoria_gpt.py`: Fallback para cliente httpx padrão, mas MESMA chave

**Fallback para outro serviço:** ❌ NÃO

- Nenhuma referência a Anthropic, Cohere, ou outros modelos
- Nenhuma estratégia de fallback em caso de erro OpenAI

---

## 6. Configuração de Project_ID

**Resultado:** ❌ NÃO CONFIGURADO

- Nenhuma variável `OPENAI_PROJECT_ID`
- Nenhuma variável `OPENAI_ORG_ID`
- Nenhuma configuração de organização OpenAI explícita

**Implicação:** O projeto está usando a organização/projeto padrão da API Key.

---

## 7. Resumo da Configuração

### Em Desenvolvimento (Local)

```
.env (arquivo)
  ├─ OPENAI_API_KEY=<OPENAI_PROJECT_KEY>
  └─ Carregada por load_dotenv() em main.py

Fluxo:
main.py:39 → load_dotenv()
gpt_client.py:6 → os.getenv("OPENAI_API_KEY")
→ AsyncOpenAI(api_key=...)
```

### Em Produção (Render)

```
Render Environment Variables
  ├─ OPENAI_API_KEY=<OPENAI_PROJECT_KEY> (DEVE estar configurada no painel)
  └─ Carregada por load_dotenv() em main.py (tenta .env primeiro)

Fluxo:
main.py:39 → load_dotenv() (não achará .env em produção)
         → sys.environ (Render injeta OPENAI_API_KEY)
gpt_client.py:6 → os.getenv("OPENAI_API_KEY")
→ AsyncOpenAI(api_key=...)
```

**⚠️ Risco:** Se `OPENAI_API_KEY` não estiver no painel do Render, as chamadas GPT falharão em produção com erro de autenticação.

---

## 8. Achados Críticos

### ✅ Correto:

1. Apenas uma chave OpenAI em uso
2. Nenhuma chave hardcoded
3. Carregamento via variável de ambiente

### ⚠️ Atenção Requerida:

1. **No arquivo render.yaml**: OPENAI_API_KEY não está mapeada
   - Risco: Se .env não existir em produção, variável não será carregada
   - Solução: Adicionar a render.yaml OU confirmar que está no painel Render

2. **httpx com verify=False em auditoria_gpt.py** (linhas 39)
   - Risco: Desabilita verificação SSL
   - Não afeta produção, apenas script de auditoria
   - Considerar remover em produção

3. **Sem project_id explícito**
   - Usa projeto padrão da chave
   - Se há múltiplos projetos na mesma organização, pode causar confusão

4. **Sem fallback para falha de autenticação**
   - Se chave estiver errada/expirada, sistema falha completamente
   - Sem retry ou fallback

---

## 9. Verificação: Qual Variável Alimenta o Client

**Para Chamada 1 (gpt_service.py):**

```
Variável de Ambiente: OPENAI_API_KEY
Arquivo de Origem: .env (ou painel Render em produção)
Carregada por: load_dotenv() [main.py:39]
Lida por: os.getenv() [gpt_client.py:6]
Passada a: AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**Para Chamada 2 (gpt_service.py):**

```
MESMA variável, MESMO cliente que Chamada 1
(ambas usam services/gpt_client.py)
```

---

## 10. Comparação Entre Ambientes

| Aspecto | Desenvolvimento | Produção (Render) |
|---------|-----------------|-------------------|
| Arquivo .env | ✅ Presente | ❌ Ausente |
| load_dotenv() | ✅ Lê .env | ⚠️ Não acha .env |
| Variável OPENAI_API_KEY | ✅ .env | ❓ Painel Render? |
| Status da chave | ✅ Visível no repositório | ⚠️ Não rastreável no código |

---

## 11. Checklist de Segurança

- ✅ Chave não está hardcoded
- ✅ Chave é única (sem duplicatas)
- ✅ Chave é sensível (salva em variável de ambiente)
- ⚠️ Chave está visível em .env (commit histórico pode tê-la)
- ⚠️ Sem project_id (usa padrão)
- ⚠️ Sem fallback de autenticação
- ❌ verify=False em auditoria (não afeta produção)

---

## 12. Próximas Ações Recomendadas

1. **Confirmar configuração em Render**
   - Verificar painel: Environment Variables
   - Garantir OPENAI_API_KEY está lá
   - Testar deployado

2. **Considerar adicionar project_id**
   - Se há múltiplos projetos na organização OpenAI
   - Adicionar `project_id=os.getenv("OPENAI_PROJECT_ID")` em gpt_client.py

3. **Considerar adicionar fallback**
   - Se falha de autenticação, tentar com chave backup (se existir)

4. **Remover verify=False de auditoria_gpt.py**
   - Linha 39 desabilita SSL verification
   - Não crítico, mas não é seguro

---

**Status da Auditoria:** ✅ Completa. Apenas 1 cliente principal em uso. Configuração rastreada.

