# Script para deletar primeira batch de clientes de teste
# Preserva: whatsapp:5511991382080 (é real, vinculado ao cliente 5511991382080)

$PROJECT = "projeto-agente-inteligente"
$KEEP = @("whatsapp:5511991382080")

$CLIENTES_TESTE = @(
    "user_regressao_3a51a102",
    "user_regressao_4130d950",
    "user_regressao_44887bf9",
    "user_regressao_4a871325",
    "user_regressao_4ea36bec",
    "user_regressao_50ca7692",
    "user_regressao_633b08ef",
    "user_regressao_6ba856cf",
    "user_regressao_70205ae6",
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

    "user_tenant_lote3_0e0c071b",
    "user_tenant_lote3_a489c9f0",
    "user_tenant_lote3_eae2d61d",
    "user_tenant_lote3_fc2d7816",

    "wa_5511991382080",

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
    "whatsapp:test_c312_t4_novo_2",

    "dono_tenant_lote3_007f9d4b",
    "dono_tenant_lote3_01547908",
    "dono_tenant_lote3_02bdb6f5",
    "dono_tenant_lote3_05aeb888",
    "dono_tenant_lote3_05c8465f",
    "dono_tenant_lote3_06fab9e5",
    "dono_tenant_lote3_07f2d5ca",
    "dono_tenant_lote3_07f48841",
    "dono_tenant_lote3_0823e0d1",
    "dono_tenant_lote3_083949a0",
    "dono_tenant_lote3_08e30b27",
    "dono_tenant_lote3_0c4c6466",
    "dono_tenant_lote3_0c970b60",
    "dono_tenant_lote3_102848d3",
    "dono_tenant_lote3_10526592",
    "dono_tenant_lote3_10d6ee27",
    "dono_tenant_lote3_110b68a9",
    "dono_tenant_lote3_13dcd448",
    "dono_tenant_lote3_160828ba",
    "dono_tenant_lote3_16715b98",
    "dono_tenant_lote3_17abbac3",
    "dono_tenant_lote3_188b0cd9",
    "dono_tenant_lote3_19ca5e5c",
    "dono_tenant_lote3_1b6220af"
)

Write-Host "========================================================================"
Write-Host "DELETANDO BATCH 1 DE CLIENTES DE TESTE"
Write-Host "========================================================================"
Write-Host ""
Write-Host "Total a deletar: $($CLIENTES_TESTE.Count)"
Write-Host ""

$deleted = 0
$failed = 0
$skipped = 0

foreach ($cliente in $CLIENTES_TESTE) {
    if ($KEEP -contains $cliente) {
        Write-Host "  ⊘ $cliente (mantido)"
        $skipped++
    } else {
        Write-Host -NoNewline "  $cliente... "
        $result = & firebase firestore:delete --project=$PROJECT "Clientes/$cliente" --recursive 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK"
            $deleted++
        } else {
            Write-Host "ERRO"
            $failed++
        }
    }
}

Write-Host ""
Write-Host "========================================================================"
Write-Host "RESUMO BATCH 1"
Write-Host "========================================================================"
Write-Host "Deletados: $deleted"
Write-Host "Falhados: $failed"
Write-Host "Mantidos: $skipped"
Write-Host "========================================================================"
