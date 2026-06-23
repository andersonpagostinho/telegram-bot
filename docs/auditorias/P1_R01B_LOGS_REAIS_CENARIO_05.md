# P1-R01B — AUDITORIA TÉCNICA COM LOGS REAIS DO CENÁRIO 05
## Execução Bloqueada: OPENAI_API_KEY Não Configurada

**Status:** BLOQUEADO — Aguardando Configuração  
**Data:** 2026-06-23  
**Baseline:** baseline-216-pass (69d9c9e)  
**Regra Aplicada:** Auditoria Técnica (logs reais)  

---

## BLOQUEIO TÉCNICO

### Verificação Inicial

```
Comando: $env:OPENAI_API_KEY
Resultado: (vazio/nao definida)
Status: BLOQUEADO
```

### Razao do Bloqueio

A execução do cenário 05 requer:

```
Fluxo:
  1. roteador_principal() é chamado
  2. Importa: router/principal_router.py
  3. Que importa: services/gpt_service.py
  4. Que importa: services/gpt_client.py
  5. Que tenta inicializar: AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
  6. Se OPENAI_API_KEY não existe → ERRO: OpenAIError
  7. Traceback interrompe execução antes de qualquer log capturável
```

### Prova do Bloqueio

Tentativa anterior resultou em:

```
openai.OpenAIError: The api_key client option must be set either by passing 
api_key to the client or by setting the OPENAI_API_KEY environment variable
```

---

## IMPEDIMENTOS CONHECIDOS

1. **OPENAI_API_KEY não está em ambiente local**
   - Não há arquivo `.env` com a chave
   - Variável de ambiente não foi setada

2. **Não há bypass seguro**
   - GPT é uma dependência crítica do fluxo
   - Mockando GPT removeria a evidência que precisamos capturar
   - Objetivo é capturar logs REAIS, não simulados

3. **Não há chave dummy disponível**
   - Usar chave falsa causaria erro HTTP (401 Unauthorized)
   - Não permitiria chegar às etapas de logging

---

## O QUE SERIA CAPTURADO SE DESBLOQUEADO

### Etapa 1: Texto Original
```python
entrada = "Olá! Tudo bem? Meu fim de semana foi ótimo! " * 30 + "e queria marcar corte com a Bruna amanhã às 15h"
```

### Etapa 2: Texto Normalizado
```python
# Saída esperada de:
from utils.normalizador_humano import normalizar_mensagem
normalizado = normalizar_mensagem(entrada)
print(f"Original: {len(entrada)} chars → Normalizado: {len(normalizado)} chars")
```

### Etapa 3: Saída do Classificador Conversacional
```python
# Saída esperada de:
from services.classificador_conversa import ClassificadorConversa
classificador = ClassificadorConversa()
classificacao = await classificador.classificar(normalizado, tenant_id)
print(json.dumps(classificacao, indent=2))
```

### Etapa 4: Prompt Enviado ao GPT
```python
# Capturado em:
# services/gpt_executor.py - antes da chamada asyncio
# services/gpt_service.py - função que cria o prompt
```

### Etapa 5: JSON Bruto do GPT
```python
# Resposta raw:
response = await client.chat.completions.create(...)
resposta_bruta = response.choices[0].message.content
print(f"Raw JSON from GPT:\n{resposta_bruta}")
```

### Etapa 6-8: Parser, Slots, Router
```python
# Processamento:
slots_extraidos = json.loads(resposta_bruta)
servico = slots_extraidos.get("servico")
profissional = slots_extraidos.get("profissional")
# ... decisão router ...
```

---

## PREREQUISITOS PARA DESBLOQUEAR

### Opção A: Usar Chave Real (Recomendado para Produção)

Se tiver acesso à chave OpenAI:

```powershell
# Configurar no PowerShell local:
$env:OPENAI_API_KEY = "sk-..."

# Ou em arquivo .env (depois carregar):
# OPENAI_API_KEY=sk-...
```

**Após configurar, script de auditoria executará:**

```bash
python audit_cenario_05_com_logs_completos.py
```

### Opção B: Carregar de Arquivo Seguro

Se a chave está em arquivo credentials:

```python
# No script:
import os
from pathlib import Path

creds = Path("firebase_credentials.json").read_text()
# Extrair chave OpenAI de sistema externo
os.environ["OPENAI_API_KEY"] = chave_recuperada
```

---

## SCRIPT PRONTO PARA USAR (QUANDO DESBLOQUEADO)

Arquivo: `audit_cenario_05_com_logs_reais.py` (pronto para criar)

```python
#!/usr/bin/env python3
"""
Auditoria Técnica Cenário 05 — Logs Reais em Cada Etapa
Captura:
  1. Texto original
  2. Texto normalizado
  3. Saída classificador
  4. Prompt para GPT
  5. JSON bruto GPT
  6. Slots extraídos
  7. Decisão router
  8. Estado final
"""

import asyncio
import json
import os
from datetime import datetime

# Prerequisito: OPENAI_API_KEY já configurada
if not os.getenv("OPENAI_API_KEY"):
    print("[ERRO] OPENAI_API_KEY não está configurada")
    print("Configure com: $env:OPENAI_API_KEY = 'sk-...'")
    exit(1)

# Setup
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(os.getcwd(), 'firebase_credentials.json')

# ... execução do cenário com logging ...
```

---

## DOCUMENTO A GERAR (QUANDO DESBLOQUEADO)

Este arquivo será substituído por:

```
P1_R01B_LOGS_REAIS_CENARIO_05.md

Conteúdo esperado:
  - TABELA: etapa | valor real | status | evidência
  - CLASSIFICAÇÃO FINAL: A/B/C/D/E comprovada
  - RECOMENDAÇÃO DE PATCH: Com causa raiz confirmada
```

---

## CHECKLIST DE DESBLOQUIO

- [ ] OPENAI_API_KEY configurada localmente
- [ ] Acesso à chave OpenAI verificado
- [ ] Script `audit_cenario_05_com_logs_reais.py` criado
- [ ] Execução do script sem erros
- [ ] Logs capturados em JSON estruturado
- [ ] Documento final gerado com tabela de evidência
- [ ] Classificação final definida (A/B/C/D/E)
- [ ] Patch mínimo recomendado (se comprovado)

---

## AÇÕES RECOMENDADAS

### Ação Imediata

1. **Configurar OPENAI_API_KEY:**
   ```powershell
   # Se você tem a chave:
   $env:OPENAI_API_KEY = "sk-your-actual-key-here"
   ```

2. **Verificar:**
   ```powershell
   echo $env:OPENAI_API_KEY  # Deve retornar a chave
   ```

3. **Re-executar auditoria:**
   ```bash
   python audit_cenario_05_com_logs_reais.py
   ```

### Se Não Houver Chave

Opções:
- [ ] Solicitar chave OpenAI ao administrador
- [ ] Usar chave de teste/sandbox do OpenAI
- [ ] Aguardar disponibilidade de chave

### Prazo Estimado

- Desbloquio (configurar chave): 2 minutos
- Auditoria técnica completa: 5-10 minutos
- Documentação de resultado: 5 minutos
- **Total:** ~15 minutos

---

## STATUS FINAL

**Auditoria P1-R01B:** ⏸️ PAUSADA  
**Motivo:** OPENAI_API_KEY não configurada  
**Bloqueio Tipo:** Técnico (sem bypass seguro)  
**Próximo Passo:** Configurar variável de ambiente  

**Não há especulação** — Conforme regra: "Se OPENAI_API_KEY faltar, parar e registrar bloqueio, sem inferir."

---

**Documentado em:** 2026-06-23T10:45:00Z  
**Assinatura:** Claude Code — Auditoria Técnica (Bloqueada)  
**Referência:** baseline-216-pass | P1-R01 (auditoria preliminar)
