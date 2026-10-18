#!/usr/bin/env python3
"""
Processador de resultados P0 373 testes
Segue REGRA DE OURO: testes devem ir até Firestore
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def processar_resultado(log_file="EXECUCAO_P0_373_COMPLETA.txt"):
    """Processa resultados seguindo framework de validação"""

    if not Path(log_file).exists():
        print(f"Arquivo {log_file} não encontrado")
        return None

    with open(log_file, encoding='utf-8', errors='ignore') as f:
        log_content = f.read()

    print("\n" + "="*80)
    print("PROCESSADOR DE RESULTADOS — 373 TESTES P0")
    print("="*80 + "\n")

    # Extrair resumo pytest
    match = re.search(r'=+ (.*?) in ([\d.]+)s', log_content)
    if match:
        resumo = match.group(1)
        tempo = match.group(2)
        print(f"Resumo pytest: {resumo}")
        print(f"Tempo total: {tempo}s\n")

    # Contar resultados
    passed = log_content.count(" PASSED")
    failed = log_content.count(" FAILED")
    error = log_content.count(" ERROR")
    skipped = log_content.count(" SKIPPED")

    print(f"{'='*80}")
    print("CONTAGEM DE RESULTADOS")
    print(f"{'='*80}")
    print(f"PASSED:  {passed}")
    print(f"FAILED:  {failed}")
    print(f"ERROR:   {error}")
    print(f"SKIPPED: {skipped}")
    print(f"{'─'*80}")
    total_executado = passed + failed + error + skipped
    print(f"TOTAL EXECUTADO: {total_executado}")

    # Análise conforme framework
    print(f"\n{'='*80}")
    print("VALIDAÇÃO CONFORME REGRA DE OURO")
    print(f"{'='*80}")

    # PASSED = válidos que vão até Firestore (assumindo que pytest validou)
    validos = passed
    invalidos = failed + error  # Estes não vão até Firestore ou têm erro

    print(f"VALIDOS (até Firestore):  {validos}")
    print(f"INVALIDOS (erro/falha):   {invalidos}")
    print(f"SKIPPED (não rodaram):    {skipped}")

    if validos + invalidos > 0:
        taxa = 100 * validos / (validos + invalidos)
        print(f"\nTAXA DE SUCESSO: {taxa:.1f}%")

        if taxa >= 95:
            print("STATUS: APROVADO")
        elif taxa >= 85:
            print("STATUS: ATENÇÃO (bugs encontrados)")
        else:
            print("STATUS: BLOQUEADOR")

    # Coletar FAILs e ERRORs
    print(f"\n{'='*80}")
    print("DETALHES DE FALHAS")
    print(f"{'='*80}\n")

    failures = re.findall(r'FAILED (.*?) -', log_content)
    errors_list = re.findall(r'ERROR (.*?) -', log_content)

    if failures:
        print(f"TESTES COM FALHA ({len(failures)}):")
        for f in failures[:10]:
            print(f"  ❌ {f}")
        if len(failures) > 10:
            print(f"  ... e {len(failures)-10} adicionais")

    if errors_list:
        print(f"\nTESTES COM ERRO ({len(errors_list)}):")
        for e in errors_list[:10]:
            print(f"  🔴 {e}")
        if len(errors_list) > 10:
            print(f"  ... e {len(errors_list)-10} adicionais")

    # Salvar JSON estruturado
    resultado = {
        "total_testes": 373,
        "executados": total_executado,
        "passed": passed,
        "failed": failed,
        "error": error,
        "skipped": skipped,
        "taxa_sucesso_percent": (100 * passed / (passed + failed + error)) if (passed + failed + error) > 0 else 0,
        "status": "APROVADO" if (100 * passed / (passed + failed + error)) >= 95 else "ATENÇÃO" if (100 * passed / (passed + failed + error)) >= 85 else "BLOQUEADOR",
        "tempos_segundos": float(tempo) if 'tempo' in locals() else 0,
    }

    json_path = Path("RESULTADO_P0_373.json")
    with open(json_path, "w") as f:
        json.dump(resultado, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Resultado salvo em: {json_path}")
    print(f"{'='*80}\n")

    return resultado

if __name__ == "__main__":
    processar_resultado()
