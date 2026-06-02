# 🔒 MODO SEGURO - README

## O que mudou?

O orquestrador foi **completamente reescrito em modo seguro**:

- ✅ **Apenas gera patches** em `.diff`
- ❌ **Nunca aplica automaticamente**
- ❌ **Nunca modifica código**
- ❌ **Nunca edita .env**

---

## 🚀 Como Usar

### 1. Investigar um Bug

```bash
python orquestrador.py "investigue consulta pura"
```

### 2. Ver o Patch Gerado

```bash
cat patches/patch_YYYYMMDD_HHMMSS.diff
```

### 3. Testar em Desenvolvimento

```bash
cd router
patch --dry-run -p0 < ../patches/patch_*.diff
```

### 4. Aplicar Manualmente

```bash
patch -p0 < ../patches/patch_*.diff
```

### 5. Testar Completamente

```bash
python -m pytest tests/
```

---

## 📊 Fluxo

```
Comando
  ↓
Claude Haiku (análise)
  ↓
GPT-4o (auditoria)
  ↓
┌─ YES? → Gera patch_*.diff → Para (aguarda revisão)
├─ NO? → Para (mostra motivo)
├─ NEEDS_MORE_EVIDENCE? → Para (solicita evidências)
└─ CONDITIONAL? → Refina (até 3x)
```

---

## ⚠️ Importante

**Patches são APENAS GERADOS, nunca aplicados automaticamente.**

### Aplicação Manual é OBRIGATÓRIA:

1. ✅ Revisar completamente o arquivo `.diff`
2. ✅ Testar em desenvolvimento com `patch --dry-run`
3. ✅ Aplicar apenas se tudo OK
4. ✅ Testar completo com suite de testes
5. ✅ Fazer commit em branch separada
6. ✅ Pull request para revisão de código

---

## 🔐 Proteções Ativas

| Proteção | Status |
|----------|--------|
| Auto-aplicação de patches | ❌ Bloqueada |
| Flag --apply | ❌ Bloqueada |
| Flag -a | ❌ Bloqueada |
| Edição de .env | ❌ Bloqueada |
| Edição de código | ❌ Bloqueada |
| Detecção de auto-apply | ✅ Ativa |
| Evidências exigidas | ✅ Ativa |

---

## 📝 Exemplo Completo

```bash
$ python orquestrador.py "investigue consulta pura"

[MODO SEGURO] Carregando configuracoes...
[OK] Protecoes contra auto-aplicacao ativadas

[ETAPA 1] Encontrando arquivos relevantes...
[OK] 1 arquivo(s) carregado(s):
   - principal_router.py

[ETAPA 2] Gerando analise inicial com Claude Haiku...
[HAIKU] Gerando analise inicial...

CAUSA RAIZ DETECTADA: Bloco AUTO-PROFISSIONAL ...

[ETAPA 3.1] Auditoria com GPT-4o...
[GPT-4O] Enviando para auditoria...

APROVACAO: [OK] APROVADO

[ETAPA 4] GERANDO ARQUIVO .diff

[OK] ARQUIVO PATCH GERADO
    Arquivo: patch_20250531_143025.diff
    Caminho: C:\...\patches\patch_20250531_143025.diff

[IMPORTANTE] Para aplicar este patch:
   1. REVISAR CUIDADOSAMENTE O ARQUIVO .diff
   2. TESTAR EM AMBIENTE DE DESENVOLVIMENTO
   3. Somente DEPOIS aplicar: patch -p0 < patch_*.diff

[AVISO] Nenhum arquivo sera modificado automaticamente

[OK] Historico salvo: logs/orquestrador_20250531_143025.json

════════════════════════════════════════════════════════════════════════════════
[MODO SEGURO] ORQUESTRACAO COMPLETADA
════════════════════════════════════════════════════════════════════════════════

[LEMBRETE] Aplicacao manual obrigatoria apos revisao humana
```

---

## 📂 Arquivos Gerados

```
.
├── logs/
│   └── orquestrador_20250531_143025.json    ← Histórico completo
│
└── patches/
    └── patch_20250531_143025.diff           ← Patch para aplicar
```

---

## 🎯 Próximos Passos Recomendados

1. **Ler a documentação:**
   - `MODO_SEGURO_ALTERACOES.md` → O que mudou
   - `EXEMPLO_SAIDA_MODO_SEGURO.txt` → Execução completa

2. **Testar em desenvolvimento:**
   ```bash
   python orquestrador.py "seu bug aqui"
   cat patches/patch_*.diff
   patch --dry-run -p0 < patches/patch_*.diff
   ```

3. **Revisar em equipe:**
   - Mostrar o `.diff` aos code reviewers
   - Discutir os testes necessários
   - Validar risco/benefício

4. **Aplicar com segurança:**
   ```bash
   git checkout -b fix/consulta-pura
   patch -p0 < patches/patch_*.diff
   pytest tests/
   git add -A
   git commit -m "Fix: bloquear consulta pura em auto-prof"
   git push -u origin fix/consulta-pura
   ```

5. **PR e merge:**
   - Criar pull request
   - Pedir revisão
   - Merge apenas após aprovação

---

## ✅ Checklist de Aplicação

- [ ] Revisar arquivo `.diff`
- [ ] Testar com `patch --dry-run`
- [ ] Entender todas as mudanças
- [ ] Verificar se há efeitos colaterais
- [ ] Criar branch de feature
- [ ] Aplicar patch
- [ ] Rodar suite de testes
- [ ] Fazer commit
- [ ] Criar pull request
- [ ] Pedir revisão de código
- [ ] Merge apenas após aprovação

---

## 🔒 Segurança Garantida

✅ **Zero modificação automática de código**
✅ **Zero edição de configuração**
✅ **Aplicação manual obrigatória**
✅ **Histórico completo para auditoria**
✅ **Evidências concretas exigidas**

---

## 📞 Perguntas?

Veja:
- `MODO_SEGURO_ALTERACOES.md` → Detalhes técnicos
- `EXEMPLO_SAIDA_MODO_SEGURO.txt` → Exemplo completo
- `orquestrador.py` → Código fonte

---

**MODO SEGURO GARANTIDO** 🔒
