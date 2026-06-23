# INFRA-04: Script de Restauração Segura de Credenciais Firebase
#
# Uso:
#   .\restore_firebase_credentials.ps1
#
# Este script oferece 3 opções para restaurar credenciais Firebase
# sem truncamento de PowerShell

param(
    [ValidateSet("help", "option-a", "option-b", "option-c")]
    [string]$Option = "help"
)

function Show-Help {
    Write-Host @"
================================================================================
INFRA-04: Restaurar FIREBASE_CREDENTIALS (truncado)
================================================================================

PROBLEMA DETECTADO:
  - FIREBASE_CREDENTIALS tem 2047 chars (truncado em PowerShell)
  - Termina em "...gle.com/o/" (não fechado)
  - JSON inválido: "Unterminated string"

OPÇÕES DE SOLUÇÃO:

  1. option-a  - [RECOMENDADO] Usar GOOGLE_APPLICATION_CREDENTIALS + arquivo
  2. option-b  - Usar Base64 (requer alteração de código)
  3. option-c  - Restaurar JSON completa em FIREBASE_CREDENTIALS

EXECUÇÃO:
  .\restore_firebase_credentials.ps1 -Option option-a
  .\restore_firebase_credentials.ps1 -Option option-b
  .\restore_firebase_credentials.ps1 -Option option-c

VERIFICAÇÃO:
  python tests/validacao_firebase_auth.py

================================================================================
"@
}

function Option-A {
    Write-Host @"
================================================================================
OPÇÃO A: GOOGLE_APPLICATION_CREDENTIALS + Arquivo (RECOMENDADO)
================================================================================

PASSO 1: Localizar ou criar arquivo de credenciais
  - Nome esperado: firebase_credentials.json
  - Locais: Diretório raiz do projeto
  - Ou use variável de ambiente existente

PASSO 2: Apontar GOOGLE_APPLICATION_CREDENTIALS para o arquivo

Executar:
"@

    # Procurar arquivo
    $credFile = Get-ChildItem -Path "firebase_credentials.json" -ErrorAction SilentlyContinue

    if ($credFile) {
        $fullPath = (Resolve-Path $credFile).Path
        Write-Host "  [OK] Arquivo encontrado: $fullPath`n"

        Write-Host "EXECUTANDO:"
        Write-Host "  > `$env:GOOGLE_APPLICATION_CREDENTIALS = '$fullPath'"

        $env:GOOGLE_APPLICATION_CREDENTIALS = $fullPath

        Write-Host "  > Variável definida`n"

        Write-Host "VALIDAR:"
        Write-Host "  > python tests/validacao_firebase_auth.py"

    } else {
        Write-Host "  [ERRO] Arquivo firebase_credentials.json não encontrado`n"
        Write-Host "SOLUÇÃO:"
        Write-Host "  1. Colocar credenciais JSON em: ./firebase_credentials.json"
        Write-Host "  2. Ou usar path completo:"
        Write-Host "     `$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\\caminho\\credenciais.json'"
        Write-Host "  3. Depois executar validacao:"
        Write-Host "     python tests/validacao_firebase_auth.py`n"
    }
}

function Option-B {
    Write-Host @"
================================================================================
OPÇÃO B: Base64 (Alternativa com código alterado)
================================================================================

PASSO 1: Codificar credencial JSON em Base64

PASSO 2: Definir variável FIREBASE_CREDENTIALS_B64

PASSO 3: Atualizar código para decodificar

ATENÇÃO: Esta opção requer alteração em:
  - services/firestore_client.py
  - config/firebase_config.py
  - services/firebase_service.py

Se deseja prosseguir:
  1. Codificar: `base64 firebase_credentials.json > creds.b64`
  2. Ler: `[System.IO.File]::ReadAllText('creds.b64')`
  3. Definir: `$env:FIREBASE_CREDENTIALS_B64 = '...'`

Não recomendado a menos que tenha motivo específico.

================================================================================
"@
}

function Option-C {
    Write-Host @"
================================================================================
OPÇÃO C: Restaurar JSON Completa em FIREBASE_CREDENTIALS
================================================================================

PROBLEMA: PowerShell tem limite de ~2048 caracteres

SOLUÇÃO: Usar arquivo ou Base64 (Opção A ou B)

Se insistir em FIREBASE_CREDENTIALS:
  1. Verificar tamanho do JSON: deve ser ~2500+ chars
  2. Se exceder 2048, não funcionará em PowerShell
  3. PowerShell não consegue armazenar strings maiores que 2048 chars
  4. Usar Opção A (arquivo) é mais confiável

PARA TESTES LOCAIS:
  - Use GOOGLE_APPLICATION_CREDENTIALS (Opção A)
  - Não use FIREBASE_CREDENTIALS
  - Arquivo é mais seguro e confiável

================================================================================
"@
}

# Executar opção selecionada
switch ($Option) {
    "help" {
        Show-Help
    }
    "option-a" {
        Option-A
    }
    "option-b" {
        Option-B
    }
    "option-c" {
        Option-C
    }
    default {
        Show-Help
    }
}

Write-Host @"

PRÓXIMOS PASSOS:
  1. Executar: .\restore_firebase_credentials.ps1 -Option option-a
  2. Depois: python tests/validacao_firebase_auth.py
  3. Se OK, executar: python tests/p1_e2e_onboarding_identidade_real.py

DÚVIDAS:
  - Verificar: docs/auditorias/INFRA_04_DIAGNOSTICO_FIREBASE_CREDENTIALS.md

================================================================================
"@
