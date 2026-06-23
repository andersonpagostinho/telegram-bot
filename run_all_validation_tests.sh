#!/bin/bash

# INFRA-03 Validação Completa com GOOGLE_APPLICATION_CREDENTIALS configurada

set -e

cd "$(dirname "$0")"

# Configurar GOOGLE_APPLICATION_CREDENTIALS
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/firebase_credentials.json"

echo "================================================================================"
echo "VALIDAÇÃO INFRA-03: Consolidação Firestore Client + P1 E2E + P0"
echo "================================================================================"
echo ""
echo "GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
echo ""

# Função para executar teste
run_test() {
    local name=$1
    local file=$2
    local expected=$3
    local timeout=${4:-600}

    echo "================================================================================"
    echo "[TEST] $name"
    echo "================================================================================"
    echo "Arquivo: tests/$file"
    echo "Esperado: $expected PASS"
    echo "Timeout: ${timeout}s"
    echo ""

    start_time=$(date +%s)

    if timeout $timeout python "tests/$file" 2>&1 | tee "test_${file%.*}_result.txt"
    then
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        echo ""
        echo "✅ $name completado em ${duration}s"
        echo ""
        return 0
    else
        end_time=$(date +%s)
        duration=$((end_time - start_time))

        echo ""
        echo "❌ $name falhou em ${duration}s"
        echo ""
        return 1
    fi
}

# Resultados
results=()

# Executar testes em sequência
echo "[SUITE] P1 E2E Tests (3 variações)"
echo ""

run_test "P1 E2E Identidade" "p1_e2e_onboarding_identidade_real.py" "14" "600" && results+=("P1_IDENTIDADE:PASS") || results+=("P1_IDENTIDADE:FAIL")
run_test "P1 E2E Operacional" "p1_e2e_onboarding_operacional_completo_real.py" "14" "600" && results+=("P1_OPERACIONAL:PASS") || results+=("P1_OPERACIONAL:FAIL")
run_test "P1 E2E Individual" "p1_e2e_onboarding_individual_real.py" "14" "600" && results+=("P1_INDIVIDUAL:PASS") || results+=("P1_INDIVIDUAL:FAIL")

echo ""
echo "[SUITE] P0 Regressão"
echo ""

run_test "P0 Regressão Completa" "runner_p0_regressao_completa.py" "174" "1200" && results+=("P0:PASS") || results+=("P0:FAIL")

# Resumo
echo ""
echo "================================================================================"
echo "RESUMO"
echo "================================================================================"

pass_count=0
fail_count=0

for result in "${results[@]}"; do
    echo "$result"
    if [[ $result == *":PASS" ]]; then
        ((pass_count++))
    else
        ((fail_count++))
    fi
done

echo ""
echo "Total: $pass_count PASS, $fail_count FAIL"
echo ""

if [ $fail_count -eq 0 ]; then
    echo "✅ TODOS OS TESTES PASSARAM"
    exit 0
else
    echo "❌ ALGUNS TESTES FALHARAM"
    exit 1
fi
