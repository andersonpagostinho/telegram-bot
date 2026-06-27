# PROTOCOLO DE EVIDÊNCIA E EXECUÇÃO DE TESTES

**Data**: 2026-06-23  
**Razão**: Estabelecer padrão rigoroso de governança de evidências — evitar confusão entre evidência documental lida vs. testes executados realmente.

---

## 1. TIPOS DE EVIDÊNCIA

### Evidência Primária (Confiável)
Gerada por execução direta no ambiente local:

- **Comando executado** — linha exata rodada
- **stdout/stderr relevante** — saída completa ou trechos críticos
- **Exit code** — 0 para sucesso, valor específico para falha
- **Arquivo gerado** — JSON, TXT, log com caminho e timestamp
- **Timestamp** — data/hora da execução
- **git status** — estado do repo antes/depois (se aplicável)

### Evidência Secundária (Não-Confiável)
Documento ou análise sem execução local:

- Relatório markdown escrito previamente
- Memória/anotação de conversas passadas
- Resumo de execução anterior
- Texto de conversa anterior

---

## 2. O QUE CONTA COMO PASS

### Conta como PASS real:
- ✅ Saída stdout contém "PASSED" ou "passed" ou "OK" (e exit code = 0)
- ✅ Relatório JSON com `"status": "PASSED"` gerado localmente com timestamp
- ✅ Log de teste com data/hora da máquina local + command + exit 0
- ✅ Firestore/DB retorna confirmação com timestamp

### NÃO conta como PASS real:
- ❌ "Arquivo diz que passou" (documentação apenas lida)
- ❌ "Memória do usuário mostra P0 174/174" (conversas anteriores)
- ❌ "Relatório markdown menciona sucesso" (relatório sem execução)
- ❌ "Análise de código sugere que funciona" (sem teste real)
- ❌ "Usuario rodou ontem e funcionou" (histórico, não evidência atual)

---

## 3. FORMATO MÍNIMO DE RELATÓRIO

Quando relatar resultado de teste:

```
**Teste**: [nome completo]
**Comando**: [linha rodada]
**Saída**: [stdout/stderr crítico]
**Exit Code**: [0 ou valor específico]
**Arquivo gerado**: [caminho + timestamp]
**Git status**: [clean/modified]
**Timestamp local**: [data-hora ISO 8601]
**Conclusão**: [PASS/FAIL + explicação]
```

Exemplo:
```
**Teste**: P1 Onboarding DONO - determinist first-actor
**Comando**: pytest tests/p1_onboarding_dono.py -v
**Saída**: test_first_actor_becomes_dono PASSED
**Exit Code**: 0
**Arquivo gerado**: .pytest_cache/v/P1_20260623_143015.json
**Git status**: clean
**Timestamp local**: 2026-06-23T14:30:15Z
**Conclusão**: PASS — primeira transação no tenant atribui role DONO corretamente
```

---

## 4. LINGUAGEM OBRIGATÓRIA

| Situação | Linguagem |
|----------|-----------|
| Executei teste real com evidência primária | "**PASS**: [resultado primário]" |
| Li relatório/memória de execução anterior | "**Evidência documental lida**: P0 174/174 (data 2026-06-21, arquivo fase_1_tier1_resultado.md)" |
| Fiz análise de código sem teste | "**Análise**: [achado técnico] (não validado em execução)" |
| Não executei pytest/Firestore | "Aguardando validação local" (nunca "PASS presumido") |
| Patch mínimo sem full validation | "Status: implementação sem declaração de PASS — aguardando validação local" |

---

## 5. REGRAS PARA CLAIMS FUTUROS

### Antes de abrir nova issue/fase:
- [ ] Só reivindicar PASS se tiver evidência primária (comando + stdout + exit code + arquivo + timestamp)
- [ ] Se apenas lido em documentação anterior: citar data e arquivo documental
- [ ] Não declarar "PASS real" para pytest/Firestore/integração sem execução local
- [ ] Para patches: marcar como "aguardando validação local" até ter evidência primária

### Antes de abrir SEG-05C:
- [ ] Resultado primário de G1 (infra tests) OU
- [ ] Resultado primário de G2 (core tests) OU
- [ ] Resultado primário de P1 (first-actor rules) OU
- [ ] Resultado primário de P0 (baseline compliance)

### Implementação de SEG-05B:
- [ ] Fazer patch mínimo
- [ ] Status final: "aguardando validação local"
- [ ] **NÃO** commitar implementação funcional antes de validação local
- [ ] **NÃO** abrir SEG-05C sem resultado primário

---

## Referências

- [NeoEve Critical Rules](../../memory/project_neoeve_rules.md)
- [FASE 1 Tier 1](../../memory/fase_1_tier1_resultado.md) — última execução com evidência primária
- [FASE 4 Aprovada](../../memory/fase_4_aprovada_final.md) — constatado como "evidência documental lida"
