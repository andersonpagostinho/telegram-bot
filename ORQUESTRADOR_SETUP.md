# 🚀 ORQUESTRADOR - SETUP E USO

## ✅ Arquivos Criados

```
raiz/
├── orquestrador.py                    (14 KB) - Script principal
├── requirements_orquestrador.txt      (52 B)  - Dependências
├── ORQUESTRADOR_README.md            (8 KB)  - Documentação completa
├── ORQUESTRADOR_SETUP.md             (este)  - Guia de setup
└── logs/                                     - Histórico de auditorias
    └── orquestrador_YYYYMMDD_HHMMSS.json     - Criado automaticamente
```

---

## 🔧 Instalação Rápida

### 1. Instalar Dependências

```bash
pip install -r requirements_orquestrador.txt
```

Ou manualmente:

```bash
pip install anthropic python-dotenv openai
```

### 2. Configurar ANTHROPIC_API_KEY

Editar `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Obter chave:**
- Ir em https://console.anthropic.com/keys
- Gerar nova API key
- Copiar e colar em `.env`

### 3. Verificar Auditoria GPT

Confirmar que `auditoria_gpt.py` existe:

```bash
ls auditoria_gpt.py
```

---

## 🚀 Uso Básico

### Formato

```bash
python orquestrador.py "descrição do problema"
```

### Exemplos

#### Investigar bug de consulta pura

```bash
python orquestrador.py "investigue por que consulta pura vira agendamento"
```

#### Revisar auto-profissional

```bash
python orquestrador.py "revise bloco auto-profissional pos-extracao"
```

#### Auditar slots

```bash
python orquestrador.py "audit slots e mesclar"
```

---

## 📊 Fluxo Completo

```
┌──────────────────────────────────────┐
│ 1. Recebe comando do usuário         │
│    "investigue consulta pura"        │
└─────────────┬────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ 2. Encontra arquivos relevantes      │
│    - principal_router.py             │
│    - event_handler.py                │
│    - contexto_temporario.py           │
└─────────────┬────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ 3. Claude Haiku gera análise inicial │
│    - Identifica causa raiz           │
│    - Caminho do código               │
│    - Linhas críticas                 │
│    - Hipótese de fix                 │
└─────────────┬────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ 4. GPT-4o faz auditoria (auditar)    │
│    - Diagnóstico                     │
│    - Risco (P0/P1/P2/P3)             │
│    - Causa raiz                      │
│    - Padrão detectado                │
│    - Patch mínimo                    │
│    - Aprovação                       │
└─────────────┬────────────────────────┘
              │
              ├─→ YES ✅
              │   (fim)
              │
              ├─→ NO ❌
              │   (exibe motivo, fim)
              │
              └─→ CONDITIONAL ⚠️
                  (refina, máx 3x)
                  │
                  ↓
              (volta ao passo 4)
```

---

## 📈 Exemplo de Execução

```bash
$ python orquestrador.py "investigue consulta pura"

================================================================================
ORQUESTRADOR DE AUDITORIA
================================================================================

Comando: investigue consulta pura
Timestamp: 20250531_143025

[ETAPA 1] Encontrando arquivos relevantes...

[OK] 1 arquivo(s) carregado(s):
   - principal_router.py

[ETAPA 2] Gerando analise inicial com Claude Haiku...

[HAIKU] Gerando analise inicial...

Analise detectada:
1. CAUSA RAIZ: Bloco AUTO-PROFISSIONAL reutiliza draft antigo
2. LINHAS: 8052-8177 (sobrescreve objetivo_conversacional)
3. HIPÓTESE: Adicionar guarda `if not eh_consulta_pura:`

[ETAPA 3.1] Auditoria com GPT-4o (rodada 1/3)...

[GPT-4O] Enviando para auditoria com GPT-4o...

[GPT-4O] Resposta recebida.

================================================================================
RESULTADO DA AUDITORIA
================================================================================

APROVACAO: [AVISO] CONDICIONAL
DIAGNOSTICO: Patch correto mas falta guarda em resolver_proximo_passo_real
RISCO: P1
CAUSA_RAIZ: Reutilização de draft antigo + falta de early return
PATCH_MINIMO: Adicionar eh_consulta_pura em duas localizacoes

[REFINAMENTO RODADA 1] Analisando feedback do GPT...

Analise refinada:
- Ambos os patches usam mesmo sinal
- Cobertura completa de pontos de entrada
- Sem regressoes esperadas

[ETAPA 3.2] Auditoria com GPT-4o (rodada 2/3)...

APROVACAO: [OK] APROVADO
...

[OK] APROVACAO CONCEDIDA!

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
    and tem_hora_real(data_hora_auto)
    ...
)

Deseja aplicar este patch? (s/n): n

[INFO] Patch nao aplicado.

[OK] Historico salvo: logs/orquestrador_20250531_143025.json

================================================================================
ORQUESTRACAO COMPLETADA
================================================================================
```

---

## 📝 Histórico (JSON)

Cada execução cria um arquivo em `logs/orquestrador_{timestamp}.json`:

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
    "analise": "CAUSA RAIZ: Bloco AUTO-PROFISSIONAL..."
  },
  {
    "etapa": "3_auditoria_gpt_r1",
    "resultado": {
      "aprovacao": "CONDITIONAL",
      "diagnostico": "Patch correto mas...",
      "risco": "P1",
      "causa_raiz": "Reutilização de draft antigo",
      "patch_minimo": "Adicionar guarda eh_consulta_pura",
      ...
    }
  },
  {
    "etapa": "3_refinamento_r1",
    "analise_refinada": "Ambos os patches..."
  },
  {
    "etapa": "3_auditoria_gpt_r2",
    "resultado": {
      "aprovacao": "YES",
      "patch_minimo": "..."
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

## 🔧 Troubleshooting

### Erro: "ANTHROPIC_API_KEY nao encontrada"

```
[ERROR] ANTHROPIC_API_KEY nao encontrada em .env
```

**Solução:**
1. Abrir `.env`
2. Adicionar: `ANTHROPIC_API_KEY=sk-ant-...`
3. Salvar

### Erro: "Instale: pip install anthropic"

```
[ERROR] Instale: pip install anthropic
```

**Solução:**
```bash
pip install -r requirements_orquestrador.txt
```

### Erro: "auditoria_gpt.py nao encontrado"

```
[ERROR] auditoria_gpt.py nao encontrado
```

**Solução:**
- Executar de dentro do diretório raiz do projeto

### Erro de conexão OpenAI

Se `auditoria_gpt.py` falhar na auditoria:

```
[FALLBACK] Retornando analise local...
```

Isso é normal — usa análise local como fallback.

---

## 📚 Documentação Completa

Ver `ORQUESTRADOR_README.md` para:
- Mapeamento automático de arquivos
- Configuração avançada
- Padrões de uso
- Segurança

---

## ✅ Checklist de Setup

- [ ] Instalar dependências: `pip install -r requirements_orquestrador.txt`
- [ ] Adicionar ANTHROPIC_API_KEY em `.env`
- [ ] Confirmar `auditoria_gpt.py` existe
- [ ] Testar: `python orquestrador.py "teste"`
- [ ] Ver resultado em `logs/orquestrador_*.json`

---

## 🎯 Próximos Passos

1. **Testar com um comando simples:**
   ```bash
   python orquestrador.py "revise slots"
   ```

2. **Verificar histórico:**
   ```bash
   cat logs/orquestrador_*.json | python -m json.tool
   ```

3. **Usar em produção:**
   ```bash
   python orquestrador.py "investigue seu bug aqui"
   ```

---

## 📞 Suporte

Dúvidas? Ver:
- `ORQUESTRADOR_README.md` - Documentação completa
- `logs/orquestrador_*.json` - Histórico da execução
- `auditoria_gpt.py` - Integração com GPT-4o
