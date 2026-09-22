# 📖 COMO USAR ESTE ROADMAP

**Guia de navegação dos documentos de development**

---

## 📚 TRÊS DOCUMENTOS PRINCIPAIS

### 1️⃣ **ROADMAP_OFICIAL_INTELIGENCIA.md** — REFERÊNCIA OFICIAL

**Quando usar:**
- Precisa entender a estratégia completa?
- Quer saber exatamente o que será desenvolvido?
- Precisa de detalhes técnicos sobre cada feature?
- Precisa se alinhar com o time?

**O que contém:**
- Princípio central (imutável)
- Todas as features P1, P2, P3
- Timeline completa (90 dias)
- Testes obrigatórios
- Regras de desenvolvimento

**Frequência de atualização:**
- Raramente (apenas se estratégia mudar)
- Máximo: 1x por mês

**Quando atualizar:**
- Se prioridade mudar
- Se nova feature for aprovada
- Se timeline for reajustada

---

### 2️⃣ **RASTREIO_PROGRESSO_SEMANAL.md** — TRACKING OPERACIONAL

**Quando usar:**
- TODA segunda-feira para atualizar progresso
- Quando precisa saber: "Em qual semana estamos?"
- Quando precisa verificar: "Já completamos X?"
- Quando precisa verificar bloqueadores

**O que contém:**
- Status de cada semana (12 semanas = 90 dias)
- % de progresso real por feature
- Bloqueadores encontrados
- Métricas alcançadas
- Próximos passos

**Frequência de atualização:**
- **Toda segunda-feira** (obrigatório)
- Máximo 5 minutos por atualização

**Como atualizar:**
1. Abrir arquivo
2. Encontrar semana atual
3. Preencher:
   ```
   ### Progresso Real:
   - [X] Dashboard: 30% pronto
   - [ ] WhatsApp: 20% pronto
   
   ### Bloqueadores:
   - (listar se houver)
   
   ### Próximos passos:
   - (listar)
   ```
4. Salvar

---

### 3️⃣ **STATUS_ATUAL_DEVELOPMENT.md** — QUICK CHECK

**Quando usar:**
- **TODA VEZ QUE VOCÊ ENTRAR** (primeira coisa)
- Quando tem 5 minutos
- Quando quer lembrar onde paramos
- Quando quer saber o que fazer agora

**O que contém:**
- Status em 1 página
- O que foi aprovado
- Onde estamos agora
- Próximos passos (esta semana)
- Checklist
- Links para documentos

**Frequência de atualização:**
- **Toda entrada do usuário** (atualizado automaticamente)
- Reflete o `RASTREIO_PROGRESSO_SEMANAL.md`

---

## 🚀 FLUXO DE USO

### PRIMEIRA VEZ (Agora)

```
1. Ler: STATUS_ATUAL_DEVELOPMENT.md (5 min)
   → Entender onde estamos
   
2. Ler: ROADMAP_OFICIAL_INTELIGENCIA.md (20 min)
   → Entender a estratégia completa
   
3. Ler: RASTREIO_PROGRESSO_SEMANAL.md (5 min)
   → Entender progresso da semana atual
```

**Tempo total:** 30 minutos para estar 100% aligned

---

### TODA SEMANA (Segunda-feira)

```
1. Abrir: RASTREIO_PROGRESSO_SEMANAL.md
   
2. Preencher seção da semana atual:
   - % de progresso
   - Bloqueadores
   - Métricas
   
3. Se houver desvio >20%:
   → Atualizar ROADMAP_OFICIAL_INTELIGENCIA.md
```

**Tempo total:** 5 minutos

---

### TODA ENTRADA (Você entrar no projeto)

```
1. Ler: STATUS_ATUAL_DEVELOPMENT.md
   → "Onde estamos agora?"
   → "O que fazer hoje?"
   
2. Se não sabe, consultar:
   → ROADMAP_OFICIAL_INTELIGENCIA.md (estratégia)
   → RASTREIO_PROGRESSO_SEMANAL.md (progresso)
```

**Tempo total:** 2-5 minutos

---

## 📍 ONDE ESTAMOS AGORA

**Semana:** 1 (01/07 - 07/07)

**O que fazer imediatamente:**

1. ✅ Ler `STATUS_ATUAL_DEVELOPMENT.md`
2. ✅ Ler `ROADMAP_OFICIAL_INTELIGENCIA.md` (seção P1.1)
3. ✅ Criar `services/dashboard_service.py` (arquivo vazio com funções)
4. ✅ Iniciar P1.1 (Dashboard do Dono)

---

## 🔄 CICLO DE ATUALIZAÇÃO

### Quando atualizar cada documento:

```
ROADMAP_OFICIAL_INTELIGENCIA.md
├─ Frequência: Mensal (ou quando estratégia muda)
├─ Quem: Tech Lead + Stakeholders
└─ Trigger: Mudança de prioridade, nova feature aprovada

RASTREIO_PROGRESSO_SEMANAL.md
├─ Frequência: TODA segunda-feira
├─ Quem: Developer responsável
└─ Trigger: Fim de semana (atualizar para próxima segunda)

STATUS_ATUAL_DEVELOPMENT.md
├─ Frequência: Quando RASTREIO é atualizado
├─ Quem: Developer responsável
└─ Trigger: Após atualizar RASTREIO
```

---

## 📋 TEMPLATE DE CHECKLIST

**Cada semana, verificar:**

```
[ ] P0/F3/F4/F8 ainda 100% em verde?
[ ] Dashboard (P1.1) avançou % esperado?
[ ] WhatsApp (F5) avançou % esperado?
[ ] Bloqueadores foram resolvidos?
[ ] Próximo objetivo da semana é claro?
[ ] RASTREIO_PROGRESSO_SEMANAL.md foi atualizado?
```

---

## 🚨 IMPORTANTE

### Princípio Central (IMUTÁVEL)

```
GPT → Interpreta linguagem
Motor → Executa TUDO

Se qualquer feature violar isso:
→ PARAR
→ Reavaliar
→ Seguir o princípio
```

### Regressão Obrigatória

```
Antes de mover para próxima semana:
- [ ] P0: 174/174 PASS
- [ ] F3: 39/39 PASS
- [ ] F4: 8/8 PASS
- [ ] F8: Funcional
- [ ] Nenhuma regressão
```

Se algum falhar:
→ Estender semana até resolver

---

## 💡 EXEMPLO: QUANDO CHEGAR À SEMANA 2

**Segunda-feira, 08/07:**

1. Abrir `STATUS_ATUAL_DEVELOPMENT.md`
   ```
   Próxima atualização: 2026-07-08
   ```

2. Abrir `RASTREIO_PROGRESSO_SEMANAL.md`
   ```
   ## SEMANA 2 (08/07 a 14/07)
   
   ### Progresso Real:
   - Dashboard (P1.1): 35% pronto
     ✅ Schema definido
     ✅ Funções estruturadas
     ✅ obter_resumo_hoje() implementado
     ⏳ obter_resumo_semana() em progresso
   
   - WhatsApp (F5): 25% pronto
     ✅ API configurada
     ⏳ Webhook em teste
   
   ### Bloqueadores:
   - Nenhum até agora
   
   ### Próximos passos:
   - Terminar obter_resumo_semana()
   - Iniciar obter_metricas_profissionais()
   - Fazer testes unitários
   ```

3. Atualizar `STATUS_ATUAL_DEVELOPMENT.md`
   ```
   Consultado em: 2026-07-08
   Próxima revisão: 2026-07-15
   ```

---

## 🎯 MÉTRICAS DE SUCESSO

**Semana 1 (esta):**
- [ ] Dashboard: 30% pronto (estrutura)
- [ ] WhatsApp: 20% pronto (setup)
- [ ] F8: Planejado
- [ ] Regressão: 100% PASS

**Semana 4:**
- [ ] Dashboard: 100% pronto + 8/8 testes
- [ ] WhatsApp: Piloto pronto
- [ ] F8: Validado
- [ ] Regressão: 100% PASS

---

## 📞 PERGUNTAS FREQUENTES

**P: Quando atualizar ROADMAP_OFICIAL_INTELIGENCIA.md?**  
R: Raramente. Apenas se a estratégia completamente mudar. Máximo 1x/mês.

**P: E se não conseguir terminar uma feature na semana planejada?**  
R: Atualizar `RASTREIO_PROGRESSO_SEMANAL.md` e estender para próxima semana. Documentar o bloqueador.

**P: Posso pular semanas?**  
R: Não. Cada semana constrói sobre a anterior. Manter sequência.

**P: O que fazer se descobrir que P1.1 é 50x maior do que esperado?**  
R: Documentar em `RASTREIO_PROGRESSO_SEMANAL.md`, sugerir split em 2 features, atualizar `ROADMAP_OFICIAL_INTELIGENCIA.md`.

**P: Preciso atualizar tudo toda semana?**  
R: Não. Apenas:
- `RASTREIO_PROGRESSO_SEMANAL.md` — toda segunda-feira
- `STATUS_ATUAL_DEVELOPMENT.md` — automaticamente quando RASTREIO muda
- `ROADMAP_OFICIAL_INTELIGENCIA.md` — raramente

---

## ✅ VOCÊ ESTÁ PRONTO

Se chegou até aqui, você entendeu:

1. ✅ Onde estamos (baseline 54/54)
2. ✅ Para onde vamos (roadmap 90 dias)
3. ✅ Como rastrear (3 documentos)
4. ✅ O que fazer agora (P1.1 + F5)
5. ✅ Como atualizar (checklist semanal)

**Próximo passo:**
→ Abrir `STATUS_ATUAL_DEVELOPMENT.md`  
→ Ler a seção "PRÓXIMOS PASSOS IMEDIATOS"  
→ Começar P1.1 (Dashboard do Dono)

---

**Documento criado:** 2026-07-01  
**Versão:** 1.0  
**Status:** Pronto para usar

