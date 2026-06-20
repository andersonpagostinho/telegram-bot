# BATERIA P0 REAL — Teste de Ponta a Ponta com Firestore

## 📋 O que é

Teste **100% real** com Firestore que valida o fluxo completo:

```
Conflito detectado → Sugestões geradas → Usuário escolhe → Evento criado → Limpeza
```

## 🎯 7 Etapas Testadas

1. **Conflito Detectado** — lock_existente quando Bruna está ocupada
2. **Lock Bloqueado** — Múltiplas tentativas no mesmo horário falham
3. **Sugestões Geradas** — Sistema oferece horários alternativos
4. **Aceite de Sugestão** — Usuário escolhe novo horário
5. **Confirmação Final** — Usuário confirma agendamento
6. **Criação do Evento** — Evento criado no novo horário
7. **Limpeza de Contexto** — Campos removidos com DELETE_FIELD

## ✅ Validações

Cada etapa valida:
- ✅ Dados corretos antes (pré-condição)
- ✅ Operação executada
- ✅ Dados corretos depois (pós-condição)
- ✅ Resultado JSON com PASS/FAIL

## 🚀 Como Executar

### Pré-requisitos

```bash
# Firebase configurado e rodando
# Python 3.7+
# Dependências instaladas
pip install firebase-admin google-cloud-firestore
```

### Executar o teste

```bash
cd "C:\Users\ANDERSON\iCloudDrive\Projeto Mercado Digital\Agente Bot\NeoEve - Empresarial"

python tests/p0_bateria_real_fluxo_completo_conflito_a_criacao.py
```

### Resultado

Arquivo gerado: `tests/resultado_bateria_p0_fluxo.json`

Exemplo de resultado:
```json
{
  "timestamp": "2026-06-19T...",
  "tenant_id": "bateria_p0_dono_teste",
  "actor_id": "bateria_p0_user_teste_001",
  "etapas": [
    {
      "numero": 1,
      "nome": "Conflito Detectado (lock_existente)",
      "status": "PASSOU",
      "detalhes": {...}
    },
    ...
  ],
  "conclusao": {
    "total_etapas": 7,
    "passaram": 7,
    "falharam": 0,
    "sucesso_geral": true,
    "fluxo_validado": true
  }
}
```

## 📊 Interpretação dos Resultados

### ✅ Cenário SUCESSO (fluxo_validado=true)

Significa:
- ✅ Lock realmente bloqueia conflito
- ✅ Sugestões são geradas corretamente
- ✅ Usuário consegue aceitar sugestão
- ✅ Novo evento é criado
- ✅ Contexto é limpo corretamente

### ❌ Cenário FALHA em Etapa X

**Se etapa 3 falhou (sugestões não geradas):**
- Problema: `verificar_conflito_e_sugestoes_profissional()` não retorna dados
- Verificar: Função existe? Firestore tem eventos?

**Se etapa 6 falhou (evento não criado):**
- Problema: Novo horário ainda tem conflito
- Verificar: Locks não foram removidos?

**Se etapa 7 falhou (contexto não limpo):**
- Problema: DELETE_FIELD não funcionou
- Verificar: `limpar_contexto_agendamento_v2()` implementou DELETE_FIELD?

## 🔍 O que o Teste Prova

1. **Lock funciona com Firestore real**
   - Não é mock em memória
   - Usa Firestore atomicidade

2. **Sugestões funcionam com dados reais**
   - Não é mock hardcoded
   - Busca eventos reais do Firestore

3. **Fluxo inteiro funciona**
   - Conflito → Sugestão → Criação
   - Sem saltos ou desvios

4. **Limpeza realmente remove campos**
   - DELETE_FIELD funciona
   - Campos não ficam como None/[]

## 🎯 Próximas Validações

Após este teste passar, fazer:

1. **Teste de stress (múltiplos usuários)**
   - 5 usuários tentando agendar simultaneamente

2. **Teste de expediente**
   - Validar que sistema respeita horário de funcionamento

3. **Teste de profissional alternativo**
   - Validar que Carla/Marina aparecem nas sugestões

## 🐛 Debug

Se algo falhar, adicione prints:

```python
# No arquivo do teste
print(f"[DEBUG] Resultado: {resultado}")
print(f"[DEBUG] Contexto: {contexto}")
```

E leia o JSON gerado com pretty-print:

```bash
python -m json.tool tests/resultado_bateria_p0_fluxo.json | less
```

## 📚 Relacionados

- **Análise de desvio:** `docs/auditorias/MAPEAMENTO_DESVIO_FLUXO_CONFLITO_SUGESTAO.md`
- **Auditoria de mocks:** `docs/auditorias/AUDITORIA_FINAL_MOCKS_VS_FIREBASE_REAL.md`
- **Patch P0:** `docs/auditorias/AUDITORIA_CONFLITO_SEM_SUGESTAO.md`

---

**Status:** 🟢 Teste pronto para executar com Firestore real

