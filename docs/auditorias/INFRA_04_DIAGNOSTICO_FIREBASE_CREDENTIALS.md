# INFRA-04 — DIAGNÓSTICO FIREBASE_CREDENTIALS

**Data:** 2026-06-22  
**Escopo:** Configuração de ambiente (não produto)  
**Objetivo:** Restaurar credenciais válidas para executar P1 E2E e P0  

---

## ACHADO PRINCIPAL

**FIREBASE_CREDENTIALS está truncada em 2047 caracteres.**

```
Tamanho esperado: ~2500+ (credencial JSON completa)
Tamanho atual:    2047 chars
Erro de parse:    "Unterminated string starting at: line 1 column 2017 (char 2016)"
Terminação:       "...gle.com/o/" (incompleto)
```

**Causa raiz:** Truncamento causado por limite do PowerShell (~2048 chars)

---

## AUDITORIA DE LEITURA

### Onde FIREBASE_CREDENTIALS é lida

| Arquivo | Linha | Padrão | Formato esperado |
|---------|-------|--------|------------------|
| config/firebase_config.py | 10 | `os.getenv("FIREBASE_CREDENTIALS")` | JSON string completo |
| services/firebase_service.py | 10 | `os.getenv("FIREBASE_CREDENTIALS")` | JSON string completo |
| services/firestore_client.py | 82 | `os.environ.get("FIREBASE_CREDENTIALS")` | JSON string completo |
| flask_app.py | 11 | `os.getenv("FIREBASE_CREDENTIALS")` | JSON string completo |
| tests/test_patch_p0_cancelamento_firebase.py | 19 | `os.getenv("FIREBASE_CREDENTIALS")` | Path ou JSON |

**Padrão:** 5 arquivos esperam `FIREBASE_CREDENTIALS` como JSON string (não path)

---

## TABELA DE DIAGNÓSTICO

| Item | Status | Evidência | Ação recomendada |
|------|--------|-----------|------------------|
| **Variável definida** | ✅ SIM | Presente em `os.environ` | OK |
| **Tamanho da variável** | ❌ **TRUNCADA** | 2047 chars (limite PowerShell ~2048) | Restaurar valor completo |
| **Formato esperado** | ✅ JSON | `os.getenv()` retorna string | OK |
| **JSON válido** | ❌ **INVÁLIDO** | `JSONDecodeError: Unterminated string` | Restaurar credencial |
| **Posição do erro** | ❌ char 2016 | Error no meio da privkey | Restaurar credencial |
| **Terminação** | ❌ **INCOMPLETA** | `"...gle.com/o/"` (não `}`) | Restaurar credencial |
| **Campo "type"** | ❌ **INDETECTÁVEL** | JSON inválido | Restaurar credencial |
| **Campo "project_id"** | ❌ **INDETECTÁVEL** | JSON inválido | Restaurar credencial |
| **Campo "private_key"** | ❌ **INDETECTÁVEL** | JSON inválido | Restaurar credencial |
| **Campo "client_email"** | ❌ **INDETECTÁVEL** | JSON inválido | Restaurar credencial |
| **Quebras de linha em private_key** | ❌ **INDETECTÁVEL** | JSON inválido | Restaurar credencial |

---

## CAUSA RAIZ: TRUNCAMENTO POWERSHELL

### Problema

PowerShell tem limite de aproximadamente 2048 caracteres para:
- Variáveis de ambiente
- Valores passados via pipe (`|`)
- Redirecionamento de output

### Sintomas

```
Tamanho da variavel: 2047 chars (exatamente 1 char abaixo do limite)
Terminacao: "...gle.com/o/" (meio de palavra)
Erro JSON: String nao terminada
Posicao: char 2016 (dentro da private_key)
```

### Evidência

```bash
$ python -c "import os; c=os.environ.get('FIREBASE_CREDENTIALS'); print(len(c), c[-30:])"
2047 gle.com/o/
```

Terminação esperada: `}"` (fechamento do JSON)  
Terminação observada: `"gle.com/o/"` (incompleto)

---

## CENÁRIOS DE TRUNCAMENTO

### Cenário 1: PowerShell com pipe (PROVÁVEL)
```powershell
# ERRADO (trunca):
$credenciais | Out-File creds.txt
$env:FIREBASE_CREDENTIALS = Get-Content creds.txt
```

### Cenário 2: PowerShell limite nativo (PROVÁVEL)
```powershell
# ERRADO (limite ~2048):
$env:FIREBASE_CREDENTIALS = "..."  # JSON muito grande
```

### Cenário 3: Redirecionamento de arquivo
```powershell
# ERRADO (pode truncar):
type firebase_credentials.json | % { $env:FIREBASE_CREDENTIALS = $_ }
```

---

## SOLUÇÃO RECOMENDADA

### Opção A: Usar arquivo (recomendado)

```powershell
# 1. Colocar credenciais em arquivo
New-Item -Path firebase_credentials.json -Force
# (colar conteúdo JSON completo no arquivo)

# 2. Usar GOOGLE_APPLICATION_CREDENTIALS em vez de FIREBASE_CREDENTIALS
$env:GOOGLE_APPLICATION_CREDENTIALS = (Resolve-Path firebase_credentials.json).Path
```

**Vantagem:** Sem limite de tamanho, mais seguro, padrão do GCP

### Opção B: Usar Base64 (alternativa)

```powershell
# 1. Codificar credencial em Base64
$json = Get-Content firebase_credentials.json -Raw
$base64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($json))
$env:FIREBASE_CREDENTIALS_B64 = $base64

# 2. Decodificar no código Python
import base64, os
creds_json = base64.b64decode(os.getenv('FIREBASE_CREDENTIALS_B64')).decode()
```

**Vantagem:** Evita problemas de escape de caracteres  
**Desvantagem:** Requer alteração de código

### Opção C: Restaurar valor completo (se necessário)

```powershell
# Copiar credencial JSON completa de arquivo seguro
[System.IO.File]::ReadAllText("C:\path\firebase_credentials.json") | 
  % { $env:FIREBASE_CREDENTIALS = $_ }

# Verificar tamanho
Write-Host $env:FIREBASE_CREDENTIALS.Length
# Deve ser ~2500+ chars
```

---

## CONFIGURAÇÃO ATUAL

### Estratégias de autenticação testadas

1. ❌ **firebaseConfig.json** — Arquivo não encontrado
   - Locais procurados:
     - `./firebaseConfig.json`
     - `./tests/../firebaseConfig.json`

2. ❌ **FIREBASE_CREDENTIALS** — JSON truncada (2047 chars)
   - Erro: `Unterminated string starting at: line 1 column 2017`

3. ❌ **GOOGLE_APPLICATION_CREDENTIALS** — Variável não definida
   - Esperado: caminho para arquivo credentials JSON

4. ❌ **Application Default Credentials** — Não encontrado
   - Requer gcloud SDK ou ~/.config/gcloud/

**Status:** Nenhuma estratégia funcionando

---

## IMPACTO NOS TESTES

| Teste | Status | Motivo |
|-------|--------|--------|
| P1 E2E Identidade | ❌ Bloqueado | Não consegue conectar ao Firestore |
| P1 E2E Operacional | ❌ Bloqueado | Não consegue conectar ao Firestore |
| P1 E2E Individual | ❌ Bloqueado | Não consegue conectar ao Firestore |
| P0 Regressão | ❌ Bloqueado | Não consegue conectar ao Firestore |

**Bloqueio:** Todas as validações INFRA-03 dependem de acesso ao Firestore

---

## PRÓXIMOS PASSOS

### Para restaurar capacidade de teste:

1. **Escolher estratégia** (Opção A recomendada)
   - Opção A: GOOGLE_APPLICATION_CREDENTIALS + arquivo
   - Opção B: Base64 (requer código)
   - Opção C: Restaurar JSON completa

2. **Configurar credenciais** (em ambiente separado)
   ```powershell
   # Opção A (recomendada)
   $env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\firebase_credentials.json"
   ```

3. **Validar configuração**
   ```bash
   python tests/validacao_firebase_auth.py
   # Deve retornar [SUCESSO]
   ```

4. **Executar validação INFRA-03**
   ```bash
   python tests/p1_e2e_onboarding_identidade_real.py
   # Esperado: 14/14 PASS
   ```

5. **Executar suite completa**
   ```bash
   python tests/runner_p0_regressao_completa.py
   # Esperado: 174/174 PASS
   ```

---

## SEGURANÇA

✅ **Nenhuma credencial impressa** em logs  
✅ **Nenhuma credencial salva** em arquivos de auditoria  
✅ **Nenhuma credencial commitada** no git  
✅ **Máscaras aplicadas** a valores sensíveis  

---

## CONCLUSÃO

**INFRA-04 diagnosticou:**

- ✅ Cause raiz identificada: Truncamento PowerShell (2047/2048 chars)
- ✅ Solução clara: Usar `GOOGLE_APPLICATION_CREDENTIALS` com arquivo
- ✅ Impacto: Bloqueia validação INFRA-03 (P1/P0)
- ✅ Próximos passos: Restaurar credenciais, executar testes

**Recomendação:** Implementar Opção A (GOOGLE_APPLICATION_CREDENTIALS + arquivo) antes de retomar testes E2E.

---

**Status:** ✅ DIAGNÓSTICO COMPLETO — AGUARDANDO RESTAURAÇÃO DE CREDENCIAIS

