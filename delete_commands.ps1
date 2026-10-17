# Script PowerShell para deletar todos os clientes de teste
# Gerado automaticamente
# ATENCAO: Revise antes de rodar!

$PROJECT = "projeto-agente-inteligente"
$deleted = 0
$failed = 0

Write-Host -NoNewline "  Deletando fernanda... "
$result = & firebase firestore:delete --project=$PROJECT "Clientes/fernanda" --recursive --yes 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓"
    $deleted++
} else {
    Write-Host "✗"
    $failed++
}

Write-Host -NoNewline "  Deletando whatsapp:55119999006... "
$result = & firebase firestore:delete --project=$PROJECT "Clientes/whatsapp:55119999006" --recursive --yes 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓"
    $deleted++
} else {
    Write-Host "✗"
    $failed++
}

Write-Host ""
Write-Host "Deletados: $deleted"
Write-Host "Falhados: $failed"
