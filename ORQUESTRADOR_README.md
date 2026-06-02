# 🤖 ORQUESTRADOR DE AUDITORIA

Automação de auditoria de código com loop de refinamento usando Claude Haiku + GPT-4o.

---

## 📋 O que é?

Sistema que:
1. Recebe um comando descritivo
2. Localiza arquivos relevantes automaticamente
3. Usa Claude Haiku para análise inicial
4. Passa para GPT-4o (auditoria_gpt.py)
5. Refina em loop (máx 3 rodadas) se houver condições
6. Aplica patches se aprovado
7. Salva histórico em JSON

---

## 🚀 Instalação

### 1. Instalar dependências

```bash
pip install anthropic python-dotenv
```

### 2. Configurar ANTHROPIC_API_KEY

Editar `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Obter chave em: https://console.anthropic.com/keys

---

## 📖 Uso

### Sintaxe Básica

```bash
python orquestrador.py "descrição do problema"
```

### Exemplos

#### Investigar bug de consulta pura

```bash
python orquestrador.py "investigue por que consulta pura vira agendamento"
```

**Fluxo:**
1. Carrega `principal_router.py`
2. Haiku analisa o código
3. GPT-4o faz auditoria
4. Se CONDITIONAL, refina até 3 vezes
5. Se YES, sugere patch

#### Revisar bloco auto-profissional

```bash
python orquestrador.py "revise bloco auto-profissional pos-extracao"
```

#### Auditar slots

```bash
python orquestrador.py "audit slots e contexto"
```

---

## 🔄 Fluxo de Aprovação

```
┌─────────────────────────────┐
│ Claude Haiku               │
│ (análise inicial)          │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ GPT-4o Audit               │
│ (auditoria_gpt.py)         │
└──────────────┬──────────────┘
               │
        ┌──────┴──────┐
        ↓             ↓
    CONDITIONAL      YES/NO
        │
        ↓ (refina até 3x)
    Claude Haiku
    (refinamento)
        │
        ↓
    GPT-4o novamente
        │
        └──→ converge para YES/NO
```

### Possíveis Saídas

| Resultado | Ação |
|-----------|------|
| **YES** ✅ | Exibe patch sugerido, oferece aplicação |
| **NO** ❌ | Para e exibe motivo da rejeição |
| **CONDITIONAL** ⚠️ | Refina análise e tenta novamente (máx 3x) |

---

## 📊 Histórico

Cada execução salva em `logs/orquestrador_{timestamp}.json`:

```json
[
  {
    "timestamp": "20250531_143025",
    "comando": "investigue consulta pura",
    "etapa": "1_arquivos",
    "arquivos_carregados": ["principal_router.py"]
  },
  {
    "etapa": "2_analise_haiku",
    "analise": "... análise completa ..."
  },
  {
    "etapa": "3_auditoria_gpt_r1",
    "resultado": {
      "aprovacao": "CONDITIONAL",
      "diagnóstico": "...",
      "causa_raiz": "...",
      ...
    }
  },
  {
    "etapa": "4_resultado_final",
    "status": "APROVADO",
    "patch_sugerido": "..."
  }
]
```

---

## 🎯 Mapeamento Automático de Arquivos

O orquestrador identifica automaticamente arquivos baseado em palavras-chave:

| Palavra-chave | Arquivo |
|---|---|
| `router` | `principal_router.py` |
| `handler` | `event_handler.py` |
| `contexto` | `contexto_temporario.py` |
| `consulta` | `principal_router.py` |
| `auto-prof` | `principal_router.py` |
| `agendamento` | `principal_router.py` |
| `slots` | `principal_router.py` |
| `draft` | `principal_router.py` |

---

## ⚙️ Configuração Avançada

### Modificar limites

**Em `orquestrador.py`:**

```python
max_rodadas = 3  # Máx de rodadas de refinamento
LIMITE_CHARS_ARQUIVO = 3000  # Truncar arquivos grandes
```

### Personalizar prompts

Edite `gerar_analise_inicial()` ou `refinar_analise()` para ajustar comportamento.

---

## 🔧 Troubleshooting

### Erro: "ANTHROPIC_API_KEY não encontrada"

```
❌ ANTHROPIC_API_KEY não encontrada em .env
```

**Solução:**
1. Editar `.env`
2. Adicionar `ANTHROPIC_API_KEY=sk-ant-...`
3. Obter chave em https://console.anthropic.com/keys

### Erro: "auditoria_gpt.py não encontrado"

```
❌ auditoria_gpt.py não encontrado
```

**Solução:**
- Executar do diretório raiz do projeto

### Erro de conexão OpenAI

Se `auditoria_gpt.py` falhar, verá:

```
[FALLBACK] Retornando análise local...
```

Isso é normal — usa análise local como fallback.

---

## 📈 Fluxo Completo de Exemplo

```bash
$ python orquestrador.py "investigue consulta pura virar agendamento"

████████████████████████████████████████████████████████████████████████████
ORQUESTRADOR DE AUDITORIA
████████████████████████████████████████████████████████████████████████████

Comando: investigue consulta pura virar agendamento
Timestamp: 20250531_143025

[ETAPA 1] Encontrando arquivos relevantes...

✅ 1 arquivo(s) carregado(s):
   - principal_router.py

[ETAPA 2] Gerando análise inicial com Claude Haiku...

[HAIKU] Gerando análise inicial...

🔍 ANÁLISE INICIAL:
1. CAUSA RAIZ: Bloco AUTO-PROFISSIONAL (linhas 8052-8177)
2. CAMINHO: extrair_slots_e_mesclar → AUTO-PROF → sobrescreve objetivo
3. LINHAS CRÍTICAS:
   - Linha 8113: ctx["servico"] = servico_auto
   - Linha 8118: ctx["objetivo_conversacional"] = None
4. HIPÓTESE: Adicionar guarda `if not eh_consulta_pura:`

[ETAPA 3.1] Auditoria com GPT-4o (rodada 1/3)...

[GPT-4O] Enviando para auditoria com GPT-4o...

[GPT-4O] Resposta recebida.

================================================================================
RESULTADO DA AUDITORIA
================================================================================

APROVACAO: ⚠️  CONDICIONAL
DIAGNÓSTICO: Patch correto mas falta guarda em resolver_proximo_passo_real
...

⚠️  APROVAÇÃO CONDICIONAL - Refinando análise...

[REFINAMENTO RODADA 1] Analisando feedback do GPT...

🔍 ANÁLISE REFINADA:
Baseado no feedback, o patch proposto precisa de:
1. Guarda em AUTO-PROFISSIONAL (8052) ✅
2. Guarda em resolver_proximo_passo_real (143) ✅
3. Ambos usam mesmo sinal de consulta pura ✅

[ETAPA 3.2] Auditoria com GPT-4o (rodada 2/3)...

APROVACAO: ✅ APROVADO
...

✅ APROVAÇÃO CONCEDIDA!

[ETAPA 4] Patch foi aprovado!

================================================================================
PATCH SUGERIDO
================================================================================

# Linha 8052-8071
eh_consulta_pura = (
    ctx.get("objetivo_conversacional") == "consultar_disponibilidade_por_servico"
    or ctx.get("intencao_conversacional") == "consulta_disponibilidade_servico"
)

if (
    not eh_consulta_pura
    and data_hora_auto
    ...
)

Deseja aplicar este patch? (s/n): n

❌ Patch não aplicado.

✅ Histórico salvo: logs/orquestrador_20250531_143025.json

████████████████████████████████████████████████████████████████████████████
ORQUESTRAÇÃO COMPLETADA
████████████████████████████████████████████████████████████████████████████
```

---

## 📝 Notas

- **Claude Haiku**: Análise rápida e barata (entrada)
- **GPT-4o**: Auditoria precisa via `auditoria_gpt.py`
- **Loop de refinamento**: Máximo 3 rodadas para convergência
- **Histórico**: JSON com todas as etapas para auditoria
- **Sem aplicação automática**: Patches são sugeridos mas aplicados manualmente (segurança)

---

## 🔐 Segurança

- ✅ ANTHROPIC_API_KEY em `.env` (não versionado)
- ✅ Histórico em JSON (rastreável)
- ✅ Patches sugeridos mas não aplicados automaticamente
- ✅ Loop de refinamento limitado (máx 3 rodadas)

---

## 📞 Suporte

Se encontrar issues:
1. Verifique `logs/orquestrador_{timestamp}.json`
2. Confirme ANTHROPIC_API_KEY em `.env`
3. Verifique conexão com OpenAI (para auditoria_gpt)
