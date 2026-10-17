# Script PowerShell para deletar clientes de teste via Firebase CLI
# Preserva: 5511991382080, 7371670478, 7394370553

$PROJECT = "projeto-agente-inteligente"
$KEEP = @("5511991382080", "7371670478", "7394370553")

Write-Host "========================================================================"
Write-Host "DELETANDO CLIENTES DE TESTE VIA FIREBASE CLI"
Write-Host "========================================================================"
Write-Host ""
Write-Host "Clientes a manter:"
foreach ($client in $KEEP) {
    Write-Host "  ✓ $client"
}
Write-Host ""

# Lista de clientes de teste (extraída do Firebase Console)
$CLIENTES_TESTE = @(
    # user_regressao_*
    "user_regressao_7023f5fd",
    "user_regressao_704c55ff",
    "user_regressao_7e3cc062",
    "user_regressao_a4afc70c",
    "user_regressao_ad87c80a",
    "user_regressao_aeaf8ba3",
    "user_regressao_c4d9fbec",
    "user_regressao_e23e9822",
    "user_regressao_e77b97f4",
    "user_regressao_ed5c4f82",
    "user_regressao_f53979af",

    # user_tenant_lote3_*
    "user_tenant_lote3_0e0c071b",
    "user_tenant_lote3_a489c9f0",
    "user_tenant_lote3_eae2d61d",
    "user_tenant_lote3_fc2d7816",

    # wa_* (teste)
    "wa_5511991382080",

    # whatsapp:* (testes - mantém só whatsapp:5511991382080)
    "whatsapp:11900000001",
    "whatsapp:11999999999",
    "whatsapp:5511966666666",
    "whatsapp:5511977777777",
    "whatsapp:5511988888888",
    "whatsapp:55119999001",
    "whatsapp:55119999002",
    "whatsapp:55119999003",
    "whatsapp:55119999004",
    "whatsapp:55119999005",
    "whatsapp:55119999006",
    "whatsapp:55119999007",
    "whatsapp:55119999008",
    "whatsapp:55119999009",
    "whatsapp:55119999010",
    "whatsapp:55119999011",
    "whatsapp:55119999012",
    "whatsapp:55119999013",
    "whatsapp:5511999999999",
    "whatsapp:551991791231114.09420",
    "whatsapp:551991791231127.79841",
    "whatsapp:551991791231267.55664",
    "whatsapp:551991791231285.68485",
    "whatsapp:551991791231351.28687",
    "whatsapp:551991791231365.23864",
    "whatsapp:551991791231377.84281",
    "whatsapp:551991791231398.94311",
    "whatsapp:551991791232973.77994",
    "whatsapp:551991791232993.05944",
    "whatsapp:551991791233295.44399",
    "whatsapp:551991791233462.71181",
    "whatsapp:551991791233774.65300",
    "whatsapp:551991791233965.25171",
    "whatsapp:551991791234070.67218",
    "whatsapp:551991791933722.29918",
    "whatsapp:test_c312_novo_1",
    "whatsapp:test_c312_novo_2",
    "whatsapp:test_c312_t1_novo_1",
    "whatsapp:test_c312_t3_novo_1",
    "whatsapp:test_c312_t4_novo_1",
    "whatsapp:test_c312_t4_novo_"
)

Write-Host "Deletando $($CLIENTES_TESTE.Count) clientes de teste..."
Write-Host ""

$deleted = 0
$failed = 0

foreach ($cliente in $CLIENTES_TESTE) {
    if ($KEEP -contains $cliente) {
        Write-Host "  ⊘ $cliente (mantido)"
    } else {
        Write-Host -NoNewline "  Deletando $cliente... "
        $result = & firebase firestore:delete --project=$PROJECT "Clientes/$cliente" --recursive --yes 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓"
            $deleted++
        } else {
            Write-Host "✗"
            $failed++
        }
    }
}

Write-Host ""
Write-Host "========================================================================"
Write-Host "RESUMO"
Write-Host "========================================================================"
Write-Host "Deletados: $deleted"
Write-Host "Falhados: $failed"
Write-Host "========================================================================"
