# 🚨 CASO CRÍTICO — ALTERAÇÃO COM MUDANÇA DE DURAÇÃO
**Data:** 2026-08-11  
**Classificação:** P0 — Validação Necessária  
**Escopo:** Determinar viabilidade de implementar alteração de agendamento

---

## ⚠️ O PROBLEMA

Quando um cliente quer alterar o **serviço** de um agendamento existente, a **duração pode mudar**.

Isso tem implicações CRÍTICAS:

```
Novo serviço
  ↓
Nova duração (tabelada)
  ↓
Novo intervalo (hora_inicio + nova duração)
  ↓
Revalidação de conflito
  ↓
Disponibilidade pode mudar
```

**Exemplo prático:**

```
Estado ATUAL:
  Evento: Corte com Carla
  Data: Segunda 14:00
  Duração: 45 min
  Intervalo: 14:00-14:45
  Conflito: Nenhum ✅

Cliente quer ALTERAR para:
  "Quero corte + hidratação"
  → Serviço = "corte + hidratação"
  → Duração = 90 min (diferente!)
  → Novo intervalo = 14:00-15:30

REVALIDAÇÃO NECESSÁRIA:
  14:00-14:45: Estava livre ✅
  14:45-15:30: Estava livre? ❓
    Se houver evento 15:00-15:30 (outro cliente com Carla):
      → CONFLITO! 
      → Precisa oferecer alternativas
      → Não pode simplesmente alterar
```

---

## 🔍 ANÁLISE

### Cenários Possíveis

#### Cenário 1: Mesma duração
```
Antes: Corte 45 min (14:00-14:45)
Depois: Barba 45 min (14:00-14:45)

Recálculo: Apenas valida disponibilidade do novo serviço
Impacto: Baixo — sem risco de conflito novo
```

#### Cenário 2: Duração aumenta
```
Antes: Corte 45 min (14:00-14:45)
Depois: Corte + Hidratação 90 min (14:00-15:30)

Recálculo: CRÍTICO
  - 14:45-15:30 estava livre?
  - Se não, CONFLITO
  - Precisa oferecer novo horário
Impacto: Alto — pode requerer reagendamento
```

#### Cenário 3: Duração diminui
```
Antes: Coloração 90 min (14:00-15:30)
Depois: Corte 45 min (14:00-14:45)

Recálculo: Sempre funciona
  - Menos tempo ocupado
  - Libera slot 14:45-15:30
Impacto: Baixo — sempre funciona
```

#### Cenário 4: Muda profissional E serviço
```
Antes: Corte com Carla 45 min (14:00-14:45)
Depois: Escova com Bruna 40 min (14:00-14:40)

Recálculo: CRÍTICO
  - Nova duração: 40 min
  - Nova profissional: Bruna
  - Bruna tem disponibilidade em 14:00-14:40?
  - Horário 14:00 ainda é ideal para Bruna?
Impacto: Alto — múltiplas variáveis
```

---

## 🔑 QUESTÃO CRÍTICA: QUEM VALIDA?

### ❌ **NÃO pode ser GPT**

```
Motivo: Regra de negócio determinística

Exemplo ERRADO:
  Cliente: "Quero mudar para corte + hidratação"
    ↓
  GPT: "Interpreta e calcula duração"
    ↓
  Motor: "Persiste se GPT disser OK"

Problema:
  - GPT pode calcular duração errada
  - GPT pode não validar conflito corretamente
  - GPT pode não saber duração exata de serviço
  - Lógica fica dispersa
```

### ✅ **DEVE ser Motor Determinístico**

```
Fluxo CORRETO:
  Cliente: "Quero mudar para corte + hidratação"
    ↓
  GPT: "Extrai: serviço = 'corte + hidratação'"
    ↓
  Motor: 
    1. Busca evento original
    2. Busca duração do novo serviço (tabela)
    3. Recalcula intervalo
    4. Valida conflito com novo intervalo
    5. Se OK: persiste
       Se conflito: oferece alternativas
    ↓
  Resultado: 100% determinístico
```

---

## 📋 ESPECIFICAÇÃO DE IMPLEMENTAÇÃO

### Assinatura Necessária

```python
async def alterar_agendamento(
    tenant_id: str,
    evento_id: str,
    campos_alterados: dict,  # {"servico": "corte + hidratacao"}
) -> dict:
    """
    Altera um agendamento existente com recálculo completo.
    
    Campos possíveis:
    - servico: str (dispara recálculo de duração)
    - profissional: str (revalida disponibilidade)
    - data: str (revalida expediente)
    - hora_inicio: str (revalida intervalo)
    
    Retorno:
    {
        "status": "ok" | "conflito" | "erro",
        "evento_alterado": {...},  # se sucesso
        "alternativas": [...],      # se conflito
        "erro": str                 # se erro
    }
    """
```

### Algoritmo de Validação

```python
async def alterar_agendamento(tenant_id, evento_id, campos_alterados):
    
    # 1. BUSCAR EVENTO ORIGINAL
    evento_original = await buscar_evento(tenant_id, evento_id)
    if not evento_original:
        return {"status": "erro", "erro": "Evento não encontrado"}
    
    # 2. APLICAR ALTERAÇÕES
    evento_novo = evento_original.copy()
    evento_novo.update(campos_alterados)
    
    # 3. RECALCULAR DURAÇÃO (se serviço mudou)
    if "servico" in campos_alterados:
        tabela_duracao = await buscar_tabela_servicos(tenant_id)
        novo_servico = campos_alterados["servico"]
        nova_duracao = tabela_duracao.get(novo_servico)
        
        if not nova_duracao:
            return {"status": "erro", "erro": f"Serviço '{novo_servico}' inválido"}
        
        evento_novo["duracao_minutos"] = nova_duracao
    
    # 4. RECALCULAR INTERVALO (se hora ou duração mudou)
    if "hora_inicio" in campos_alterados or "servico" in campos_alterados:
        hora_ini = evento_novo["hora_inicio"]
        duracao = evento_novo["duracao_minutos"]
        hora_fim = calcular_hora_fim(hora_ini, duracao)
        evento_novo["hora_fim"] = hora_fim
    
    # 5. VALIDAR EXPEDIENTE (se data/hora/prof mudou)
    if "data" in campos_alterados or "hora_inicio" in campos_alterados:
        valido_expediente = await validar_horario_funcionamento(
            tenant_id,
            evento_novo["data"],
            evento_novo["hora_inicio"],
            evento_novo["duracao_minutos"],
            evento_novo.get("profissional")
        )
        if not valido_expediente.get("permitido"):
            return {
                "status": "erro",
                "erro": f"Horário fora do expediente: {valido_expediente.get('motivo')}"
            }
    
    # 6. VALIDAR CONFLITO (CRÍTICO)
    # Busca TODOS os eventos no intervalo NOVO
    # EXCLUINDO o evento original (senão conflita consigo mesmo)
    
    conflito = await verificar_conflito_e_sugestoes_profissional(
        tenant_id,
        evento_novo["data"],
        evento_novo["hora_inicio"],
        evento_novo["duracao_minutos"],
        evento_novo.get("profissional"),
        evento_novo.get("servico"),
        evento_id_ignorar=evento_id  # NÃO contar com o evento original
    )
    
    if conflito.get("conflito"):
        # Se houve conflito, oferece alternativas
        return {
            "status": "conflito",
            "evento_original": evento_original,
            "evento_proposto": evento_novo,
            "alternativas": conflito.get("sugestoes", []),
            "motivo": "Novo horário gera conflito com cliente/profissional"
        }
    
    # 7. REGISTRAR HISTÓRICO (antes de alterar)
    historico = {
        "timestamp": datetime.now(),
        "tipo": "alteracao",
        "evento_id": evento_id,
        "campos_alterados": campos_alterados,
        "evento_antes": evento_original,
        "evento_depois": evento_novo
    }
    await registrar_historico(tenant_id, historico)
    
    # 8. PERSISTIR ALTERAÇÃO (NÃO deletar + criar)
    # Apenas atualizar campos
    await atualizar_evento(tenant_id, evento_id, evento_novo)
    
    # 9. NOTIFICAR
    await notificar_alteracao(
        tenant_id,
        evento_novo,
        mudancas=campos_alterados,
        historico=historico
    )
    
    return {
        "status": "ok",
        "evento_alterado": evento_novo,
        "historico": historico
    }
```

---

## 🧪 CASOS DE TESTE CRÍTICOS

### Teste 1: Aumentar Duração (CONFLITO)

```
Setup:
  Evento A: Corte com Carla, 14:00-14:45 ✅
  Evento B: Manicure com Bruna, 14:00-14:30 ✅ (outro cliente)

Teste:
  Cliente A: "Quero corte + hidratação" (90 min)
  Nova duração: 14:00-15:30
  
Validação Esperada:
  ❌ CONFLITO: 14:30-14:45 ocupado por Evento B
  ✅ Oferece alternativas: "Terça 14h", "Quarta 10h"
  
Resultado:
  ✅ Se cliente aceita alternativa: altera para nova data
  ✅ Se cliente recusa: cancela operação
```

### Teste 2: Diminuir Duração (OK)

```
Setup:
  Evento A: Coloração com Carla, 14:00-15:30 ✅

Teste:
  Cliente A: "Só corte então" (45 min)
  Nova duração: 14:00-14:45
  
Validação Esperada:
  ✅ Sem conflito: 14:00-14:45 agora livre
  ✅ Libera slot 14:45-15:30
  
Resultado:
  ✅ Altera com sucesso
  ✅ Notifica liberação de horário
```

### Teste 3: Mudar Duração E Profissional

```
Setup:
  Evento A: Corte com Carla, 14:00-14:45 ✅
  Evento B: Escova com Bruna, 14:00-14:40 ✅

Teste:
  Cliente A: "Prefiro com Bruna, tipo escova" (40 min)
  Novo serviço: Escova
  Nova profissional: Bruna
  Nova duração: 14:00-14:40
  
Validação Esperada:
  ❌ CONFLITO: Bruna ocupada 14:00-14:40 (Evento B)
  ✅ Oferece: "Bruna terça 14h", "Carla quarta 10h"
  
Resultado:
  ✅ Motor recalcula tudo deterministicamente
```

### Teste 4: Mesma Duração, Mesmo Profissional, Novo Serviço

```
Setup:
  Evento A: Corte com Carla, 14:00-14:45 ✅

Teste:
  Cliente A: "Barba em vez de corte" (45 min)
  
Validação Esperada:
  ✅ Sem conflito: intervalo idêntico
  ✅ Apenas valida disponibilidade de serviço Barba
  
Resultado:
  ✅ Altera com sucesso
```

### Teste 5: Duração Aumenta + Horário Diferente

```
Setup:
  Evento A: Corte com Carla, 14:00-14:45 ✅
  Evento B: Manicure com Bruna, 15:00-15:30 ✅

Teste:
  Cliente A: "Quer corte + hidratação mas prefiro 15h"
  Nova hora: 15:00
  Nova duração: 90 min (15:00-16:30)
  
Validação Esperada:
  ❌ CONFLITO: Evento B em 15:00-15:30
  ✅ Oferece alternativas com Carla em outro horário
  
Resultado:
  ✅ Motor detecta conflito corretamente
  ✅ Oferece slots reais livres
```

---

## 🎯 DECISÃO NECESSÁRIA

### Pergunta Crítica:

**Existe tabela de duração de serviços em Firestore?**

```python
Clientes/{tenant_id}/configuracao/servicos
  ├─ "corte": {"duracao": 45, "preco": 50}
  ├─ "escova": {"duracao": 40, "preco": 80}
  ├─ "coloracao": {"duracao": 90, "preco": 150}
  ├─ "hidratacao": {"duracao": 45, "preco": 60}
  ├─ "corte + hidratacao": {"duracao": 90, "preco": 100}
  └─ ...
```

**Se NÃO existe:**
→ Não é possível implementar alteração de serviço deterministicamente
→ Precisa criar tabela ANTES

**Se EXISTE:**
→ Implementação é viável
→ Motor recalcula tudo
→ Fluxo funciona

---

## ✅ CONCLUSÃO

**Alteração de agendamento é viável SOMENTE SE:**

1. ✅ Existir tabela de duração de serviços
2. ✅ Motor validar conflitos com novo intervalo
3. ✅ Oferecer alternativas se houver conflito
4. ✅ Persistir como ALTERAÇÃO, não cancelar + criar
5. ✅ Registrar histórico de mudanças

**Esta é a validação CRÍTICA que precisa acontecer antes de implementar reagendamento.**

