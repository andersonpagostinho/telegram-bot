# 🔒 MODO SEGURO - ALTERAÇÕES APLICADAS

## ✅ O que foi alterado?

### 1. **Remoção de Auto-Aplicação**

**ANTES:**
```python
def aplicar_patch(patch_sugerido):
    """Tenta aplicar patch (interativo)."""
    print("\n" + "="*80)
    print("PATCH SUGERIDO")
    print("="*80 + "\n")
    print(patch_sugerido)
    print()

    resposta = input("Deseja aplicar este patch? (s/n): ").strip().lower()

    if resposta == "s":
        # APLICAVA AUTOMATICAMENTE!
        return True
```

**DEPOIS:**
```python
# FUNCAO REMOVIDA COMPLETAMENTE
# Agora apenas gera arquivo .diff
# Zero modificação automática de código
```

---

### 2. **Proteção contra Flags --apply**

**NOVO:**
```python
if "--apply" in sys.argv or "-a" in sys.argv:
    print("[ERRO] Flags --apply e -a estao bloqueadas em modo seguro")
    sys.exit(1)
```

---

### 3. **Proteção contra Funções de Auto-Aplicação**

**NOVO:**
```python
BLOQUEADO_FUNCOES = [
    "aplicar_patch",
    "auto_apply",
    "apply_patch",
    "aplicar_automaticamente",
    "auto_aplicar"
]

for funcao in dir():
    if any(bloqueado in funcao.lower() for bloqueado in BLOQUEADO_FUNCOES):
        raise RuntimeError(f"[BLOQUEADO] Funcao de auto-aplicacao detectada: {funcao}")
```

---

### 4. **Novo Fluxo: Apenas Gera .diff**

**ANTES:**
```python
if resultado_gpt and resultado_gpt.get("aprovacao", "").upper() == "YES":
    print("\n[ETAPA 4] Patch foi aprovado!\n")
    patch_sugerido = resultado_gpt.get("patch_minimo", "Nenhum patch sugerido")
    if "sem patch" not in patch_sugerido.lower():
        aplicar_patch(patch_sugerido)  # ← APLICAVA!
```

**DEPOIS:**
```python
if resultado_gpt and resultado_gpt.get("aprovacao", "").upper() == "YES":
    print("\n[ETAPA 4] GERANDO ARQUIVO .diff\n")
    patch_sugerido = resultado_gpt.get("patch_minimo", "Nenhum patch sugerido")
    if "sem patch" not in patch_sugerido.lower():
        arquivo_patch = gerar_arquivo_diff(patch_sugerido, timestamp)
        # ↑ APENAS GERA, NUNCA APLICA
```

---

### 5. **Nova Função: gerar_arquivo_diff()**

**NOVO:**
```python
def gerar_arquivo_diff(patch_sugerido, timestamp):
    """GERA ARQUIVO .diff APENAS (sem aplicar)."""
    
    arquivo_patch = PATCHES_DIR / f"patch_{timestamp}.diff"
    
    conteudo_diff = f"""# PATCH SUGERIDO - {timestamp}
# MODO SEGURO: Aplicacao manual OBRIGATORIA
#
# Para aplicar este patch:
# 1. Revisar cuidadosamente
# 2. Executar: patch -p0 < {arquivo_patch.name}
# 3. Testar completamente

{patch_sugerido}
"""
    
    with open(arquivo_patch, "w", encoding="utf-8") as f:
        f.write(conteudo_diff)
    
    return arquivo_patch
```

---

### 6. **Novo Status: NEEDS_MORE_EVIDENCE**

**ANTES:**
```python
# Apenas YES, NO, CONDITIONAL
```

**DEPOIS:**
```python
elif aprovacao == "NEEDS_MORE_EVIDENCE":
    print("[AVISO] FALTAM EVIDENCIAS CONCRETAS")
    print(f"Solicita: {resultado_gpt.get('justificativa', 'Veja acima')}")
    historico.append({
        "etapa": "4_resultado_final",
        "status": "INCOMPLETO",
        "evidencias_faltantes": resultado_gpt.get('justificativa')
    })
    salvar_historico(historico, timestamp)
    print("\n[RESULTADO] Auditoria completada: EVIDENCIAS INSUFICIENTES")
    return
```

---

### 7. **Aviso Explícito em Modo Seguro**

**NOVO NO CABEÇALHO:**
```python
print("[MODO SEGURO] Carregando configuracoes...\n")
# ...
print("[AVISO] Patches serão APENAS GERADOS, nunca aplicados automaticamente\n")
# ...
print("[LEMBRETE] Aplicacao manual obrigatoria apos revisao humana")
```

---

### 8. **Diretório de Patches Criado**

**NOVO:**
```python
PATCHES_DIR = PROJECT_ROOT / "patches"
PATCHES_DIR.mkdir(exist_ok=True)
```

Arquivos gerados em: `patches/patch_{timestamp}.diff`

---

## 📊 Diferenças Principais

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Aplicação de patch | ✅ Automática | ❌ Bloqueada |
| Flag --apply | ✅ Permitida | ❌ Bloqueada |
| Função aplicar_patch() | ✅ Ativa | ❌ Removida |
| Output de patch | Aplicar direto | Gerar .diff |
| Edição de .env | Permitida | ❌ Bloqueada |
| Diretório patches/ | Não | ✅ Criado |
| Status NEEDS_MORE_EVIDENCE | Não | ✅ Adicionado |

---

## 🔐 Proteções Adicionadas

1. ✅ **Bloqueio de função de auto-aplicação**
   - Detecta ao iniciar
   - Erro fatal se encontrar

2. ✅ **Bloqueio de flags**
   - --apply
   - -a

3. ✅ **Aviso explícito**
   - No inicio da execução
   - No final da execução
   - Em cada arquivo .diff

4. ✅ **ANTHROPIC_API_KEY segura**
   - Carregada apenas de .env
   - Nunca é escrita de volta
   - Erro claro se faltar

5. ✅ **Histórico completo**
   - Modo seguro registrado
   - Patch não aplicado registrado
   - Evidências registradas

---

## 🚀 Como Usar (Modo Seguro)

```bash
# 1. Investigar
python orquestrador.py "investigue consulta pura"

# 2. Revisar arquivo .diff
cat patches/patch_20250531_143025.diff

# 3. Se aprovado, aplicar manualmente
cd router
patch -p0 < ../patches/patch_20250531_143025.diff

# 4. Testar
python -m pytest tests/
```

---

## 📝 Exemplo de Arquivo .diff

```diff
# PATCH SUGERIDO - 20250531_143025
# MODO SEGURO: Aplicacao manual OBRIGATORIA
#
# Para aplicar este patch:
# 1. Revisar cuidadosamente
# 2. Executar: patch -p0 < patch_20250531_143025.diff
# 3. Testar completamente

# PATCH 3 - Bloquear AUTO-PROFISSIONAL para consultas puras
# Linhas 8052-8071 em router/principal_router.py

--- a/router/principal_router.py
+++ b/router/principal_router.py
@@ -8050,6 +8050,20 @@ async def roteador_principal(user_id: str, mensagem: str, update=None, context
         flush=True
     )

+    # 🛡️ GUARDA CONTRA CONSULTA PURA
+    eh_consulta_pura = (
+        ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
+        or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
+    )
+
+    if eh_consulta_pura:
+        print(
+            "🛡️ [AUTO-PROF BLOQUEADO] consulta pura não pode virar agendamento",
+            flush=True
+        )
+
     if (
+        not eh_consulta_pura
         and data_hora_auto
         and tem_hora_real(data_hora_auto)
         and servico_auto
```

---

## ✅ Checklist de Segurança

- ✅ Nenhuma modificação automática de arquivos
- ✅ Apenas .diff gerado (não aplicado)
- ✅ ANTHROPIC_API_KEY nunca editada
- ✅ --apply bloqueado
- ✅ Funções de auto-aplicação removidas
- ✅ Aviso explícito em modo seguro
- ✅ Histórico completo em JSON
- ✅ NEEDS_MORE_EVIDENCE implementado

---

## 🎯 Fluxo Seguro

```
Comando
  ↓
Haiku Analisa
  ↓
GPT-4o Audita
  ↓
    ├─ YES? → Gera .diff → Para (aguarda revisão)
    ├─ NO? → Para (mostra motivo)
    ├─ NEEDS_MORE_EVIDENCE? → Para (solicita evidências)
    └─ CONDITIONAL? → Refina (até 3x)

FIM: Aplicação manual OBRIGATÓRIA
```

---

## 📌 Importante

**Em modo seguro:**
- ✅ Sistema ANALISA e AUDITA
- ✅ Sistema GERA patches (.diff)
- ❌ Sistema NÃO aplica automaticamente
- ❌ Sistema NÃO modifica código
- ❌ Sistema NÃO edita .env

**Aplicação:**
- Manual OBRIGATÓRIA
- Após revisão humana
- Com testes completos
- Em ambiente seguro primeiro

---

## 🔐 Conclusão

Orquestrador está em **MODO SEGURO** total:
- Investigador ✅
- Auditor ✅
- Gerador de patches ✅
- **Nunca modificador de código** ✅
