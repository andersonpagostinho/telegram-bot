# Diagnóstico: Autenticação Firebase Corrompida

**Data:** 2026-06-21  
**Teste:** `tests/validacao_firebase_auth.py`  
**Status:** 🔴 FALHA - Credenciais Corrompidas  

---

## 📊 Resultados

| Estratégia | Status | Detalhe |
|-----------|--------|---------|
| firebaseConfig.json (local) | ❌ CORRUPTO | Invalid control character at column 2048 |
| FIREBASE_CREDENTIALS (env var) | ❌ TRUNCADO | 2047 chars, faltam ~1000+ |
| GOOGLE_APPLICATION_CREDENTIALS | ❌ NÃO CONFIGURADA | Variável não definida |
| Application Default Credentials | ❌ SEM CREDENCIAIS | GCP não disponível |

---

## 🔍 Análise Detalhada

### Problema 1: firebaseConfig.json Corrompido

```
Arquivo encontrado: 2 locais
├── C:\...\Projeto Mercado Digital\...\firebaseConfig.json
└── C:\...\Projeto Mercado Digital\...\tests\..\firebaseConfig.json

Status: ❌ CORRUPTO
Erro: "Invalid control character at: line 1 column 2048 (char 2047)"

Causa: 
- Arquivo foi truncado (cortado no meio)
- OU foi gravado com encoding incorreto (não UTF-8)
- OU contém caracteres de controle não imprimíveis
```

**Solução:** Recriar o arquivo com credenciais válidas e encoding UTF-8 sem BOM.

### Problema 2: FIREBASE_CREDENTIALS Truncada

```
Status: ❌ TRUNCADA
Tamanho encontrado: 2047 chars
Tamanho esperado: >2500 chars
Faltam: ~1000+ caracteres

Erro: "Unterminated string starting at: line 1 column 2017 (char 2016)"

Causa:
- Variável de ambiente foi truncada ao ser atribuída
- Limite de buffer ou caracteres especiais interromperam a atribuição
- PowerShell/Bash pode ter cortado a string
```

**Solução:** Usar `GOOGLE_APPLICATION_CREDENTIALS` ao invés (mais confiável).

### Problema 3: GOOGLE_APPLICATION_CREDENTIALS Não Configurada

```
Status: ❌ NÃO CONFIGURADA
Esperado: Variável de ambiente apontando para arquivo .json

Causa:
- Não foi configurada durante setup
- Desenvolvedor precisa configurar manualmente
```

**Solução:** Configurar conforme `GUIA_CONFIGURACAO_FIREBASE_LOCAL.md`.

---

## ✅ Solução Recomendada

### Opção 1: GOOGLE_APPLICATION_CREDENTIALS (RECOMENDADO)

**Por que:** Mais confiável, não trunca, suportado por Google.

```powershell
# 1. Obter credenciais válidas do Firebase Console
# Console Firebase → Seu Projeto → ⚙️ Configurações
# Guia "Contas de Serviço" → "Gerar Nova Chave Privada"

# 2. Salve em local seguro (ex: C:\Firebase\neoeve-prod.json)
# ⚠️ CERTIFIQUE-SE: Arquivo deve ter ENCODING UTF-8 SEM BOM

# 3. Configure variável de ambiente (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Firebase\neoeve-prod.json"

# 4. Verifique se foi configurada
$env:GOOGLE_APPLICATION_CREDENTIALS

# 5. Execute validação
python tests/validacao_firebase_auth.py

# RESULTADO ESPERADO:
# [OK] Firebase inicializado com GOOGLE_APPLICATION_CREDENTIALS
# [OK] Conseguiu listar coleções
```

### Opção 2: firebaseConfig.json Local

**Por que:** Simples, arquivo único.

```powershell
# 1. Obter credenciais (mesma forma)

# 2. Salve na RAIZ do projeto como "firebaseConfig.json"
# ⚠️ CERTIFIQUE-SE: Encoding UTF-8 SEM BOM

# 3. Adicione ao .gitignore
Add-Content .gitignore "firebaseConfig.json"

# 4. Execute validação
python tests/validacao_firebase_auth.py

# RESULTADO ESPERADO:
# [OK] Firebase inicializado com credenciais locais: ...firebaseConfig.json
```

---

## 🛠️ Verificação de Encoding

**O arquivo está corrompido porque tem encoding inválido ou caracteres de controle.**

Verificar encoding de arquivo existente:

```powershell
# PowerShell - Verificar encoding
$file = Get-Content -Path "firebaseConfig.json" -Raw
$encoding = [System.Text.Encoding]::GetEncoding($file)
Write-Host "Encoding: $encoding"

# Se for diferente de UTF-8: RECRIE O ARQUIVO
```

Criar arquivo com encoding correto:

```powershell
# 1. Obter JSON válido do Firebase Console

# 2. Salvar com encoding UTF-8 (sem BOM)
$json = @'
{
  "type": "service_account",
  "project_id": "seu-projeto",
  ...JSON completo...
}
'@

# Salvar sem BOM (importante!)
$utf8NoBOM = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText("firebaseConfig.json", $json, $utf8NoBOM)

# Verificar resultado
python tests/validacao_firebase_auth.py
```

---

## 📋 Próximos Passos Obrigatórios

### Passo 1: Obter Credenciais Válidas

```
1. Ir para: https://console.firebase.google.com/
2. Selecionar projeto NeoEve
3. Clique em ⚙️ (Configurações do projeto)
4. Guia "Contas de Serviço"
5. Botão "Gerar Nova Chave Privada"
6. Arquivo JSON será baixado automaticamente
```

### Passo 2: Configurar Variável de Ambiente

**Opção A: PowerShell (Recomendado)**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\Users\ANDERSON\Firebase\neoeve-prod.json"
```

**Opção B: Salvar na Raiz do Projeto**
```bash
# Copie o arquivo baixado para: NeoEve - Empresarial/firebaseConfig.json
# Adicione ao .gitignore
```

### Passo 3: Validar

```bash
python tests/validacao_firebase_auth.py

# Resultado esperado:
# [OK] Firebase inicializado com ...
# [OK] Conseguiu listar coleções
# [SUCESSO] Firebase autenticado e funcional!
```

### Passo 4: Rodar Testes Completos

Se validação passar:

```bash
# P1 Identidade + Onboarding (esperado: 9/9 PASS)
python -m pytest tests/runner_p1_identidade_canal_onboarding.py -v

# P0 Regressão (esperado: 174/174 PASS)
python -m pytest tests/runner_p0_regressao_completa.py -v
```

---

## 📝 Checklist

- [ ] Credenciais válidas obtidas do Firebase Console
- [ ] Arquivo JSON baixado localmente
- [ ] Encoding verificado (UTF-8 sem BOM)
- [ ] GOOGLE_APPLICATION_CREDENTIALS configurada
- [ ] `validacao_firebase_auth.py` passou com [SUCESSO]
- [ ] `runner_p1_identidade_canal_onboarding.py` (9/9 PASS)
- [ ] `runner_p0_regressao_completa.py` (174/174 PASS)

---

## 🚨 Resumo Executivo

```
PROBLEMA: Credenciais Firebase corrompidas/truncadas
├─ firebaseConfig.json: Corrompido (caracteres inválidos)
├─ FIREBASE_CREDENTIALS: Truncada (faltam 1000+ chars)
└─ GOOGLE_APPLICATION_CREDENTIALS: Não configurada

SOLUÇÃO: 
1. Obter credenciais válidas do Firebase Console
2. Configurar GOOGLE_APPLICATION_CREDENTIALS (recomendado)
3. Validar com: python tests/validacao_firebase_auth.py
4. Rodar P1 + P0 para confirmar

BLOQUEANTE: Não é bug de código
             É configuração de ambiente (credenciais)
```

---

**Auditado em:** 2026-06-21  
**Tipo:** Diagnóstico de Autenticação  
**Ação:** Reconfigurar Firebase com credenciais válidas  
**Tempo Estimado:** 5-10 minutos
