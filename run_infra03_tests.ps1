# INFRA-03: Script de Validação Completa
# Executa P1 E2E (3 variações) e P0 em sequência

param(
    [string]$Mode = "all"  # all, p1_only, p0_only
)

$ErrorActionPreference = "Stop"

Write-Host "`n" + "="*70
Write-Host "INFRA-03: VALIDAÇÃO DE CONSOLIDAÇÃO FIRESTORE CLIENT"
Write-Host "="*70 + "`n"

$startTime = Get-Date

# Função para executar teste e registrar resultado
function Run-Test {
    param(
        [string]$TestName,
        [string]$TestFile,
        [int]$ExpectedTests
    )

    Write-Host "[TEST] Iniciando $TestName..."
    Write-Host "File: tests/$TestFile"
    Write-Host "Expected: $ExpectedTests PASS`n"

    $testStart = Get-Date

    try {
        $output = & python "tests/$TestFile" 2>&1
        $testEnd = Get-Date
        $duration = ($testEnd - $testStart).TotalSeconds

        # Procurar por resultado
        if ($output -match "(\d+)/(\d+) PASS") {
            $passed = [int]$matches[1]
            $total = [int]$matches[2]

            if ($passed -eq $ExpectedTests -and $total -eq $ExpectedTests) {
                Write-Host "✅ $TestName: $passed/$total PASS (${duration}s)" -ForegroundColor Green
                return $true
            } else {
                Write-Host "❌ $TestName: $passed/$total PASS (expected $ExpectedTests/$ExpectedTests)" -ForegroundColor Red
                Write-Host "STDOUT:`n$output`n"
                return $false
            }
        } elseif ($output -match "PASSED") {
            Write-Host "✅ $TestName: PASSED (${duration}s)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ $TestName: FAILED or unclear result" -ForegroundColor Red
            Write-Host "STDOUT:`n$output`n"
            return $false
        }
    } catch {
        Write-Host "❌ $TestName: ERROR - $_" -ForegroundColor Red
        return $false
    }
}

# Executar testes
$results = @()

if ($Mode -eq "all" -or $Mode -eq "p1_only") {
    Write-Host "`n[SUITE] P1 E2E Tests (3 variações)`n"

    $results += (New-Object PSObject -Property @{
        Name = "P1 E2E Identidade"
        Passed = Run-Test "P1 E2E Identidade" "p1_e2e_onboarding_identidade_real.py" 14
    })

    $results += (New-Object PSObject -Property @{
        Name = "P1 E2E Operacional"
        Passed = Run-Test "P1 E2E Operacional" "p1_e2e_onboarding_operacional_completo_real.py" 14
    })

    $results += (New-Object PSObject -Property @{
        Name = "P1 E2E Individual"
        Passed = Run-Test "P1 E2E Individual" "p1_e2e_onboarding_individual_real.py" 14
    })
}

if ($Mode -eq "all" -or $Mode -eq "p0_only") {
    Write-Host "`n[SUITE] P0 Regressão`n"

    $results += (New-Object PSObject -Property @{
        Name = "P0 Regressão"
        Passed = Run-Test "P0 Regressão" "runner_p0_regressao_completa.py" 174
    })
}

# Resumo
Write-Host "`n" + "="*70
Write-Host "RESUMO"
Write-Host "="*70 + "`n"

$totalTests = $results.Count
$passedTests = ($results | Where-Object { $_.Passed -eq $true }).Count

foreach ($result in $results) {
    $status = if ($result.Passed) { "✅ PASS" } else { "❌ FAIL" }
    Write-Host "$status — $($result.Name)"
}

Write-Host "`nTotal: $passedTests/$totalTests testes passaram`n"

$endTime = Get-Date
$totalDuration = ($endTime - $startTime).TotalMinutes

Write-Host "Duração total: ${totalDuration:F1} minutos`n"

if ($passedTests -eq $totalTests) {
    Write-Host "🎉 SUCESSO: Todos os testes passaram!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️ FALHA: Alguns testes não passaram" -ForegroundColor Red
    exit 1
}
