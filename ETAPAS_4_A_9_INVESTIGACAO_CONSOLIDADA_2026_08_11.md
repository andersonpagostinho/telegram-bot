# ETAPAS 4-9 — INVESTIGACAO CONSOLIDADA MULTI-TENANT

**Data:** 2026-08-11  
**Status:** ✅ **TODAS AS INVESTIGACOES CONCLUIDAS**  

---

## ETAPA 4 — INVESTIGACAO MULTI-TENANT

### Questão
Existe divergência entre tenant_id_write e tenant_id_read?

### Teste Realizado
- Escrita: `criar_com_lock_real(dono_id=tenant_direto, ...)`
- Path escrita: `Clientes/tenant_direto/Eventos/evt_teste_001`
- Leitura: `buscar_subcolecao(Clientes/tenant_direto/Eventos)`

### Resultado
```
[OK] tenant_id_write   = mt_investigacao_tenant_001
[OK] tenant_id_read    = mt_investigacao_tenant_001
[OK] Match: SIM

[OK] Path legado (Clientes/{user_id}/Eventos): NAO UTILIZADO
[OK] Path correto (Clientes/{tenant_id}/Eventos): UTILIZADO
```

### Conclusão ETAPA 4
✅ **SEM DIVERGENCIA MULTI-TENANT**
- tenant_id_write == tenant_id_read
- Path está correto (usa {tenant_id}, não {user_id})
- Nenhum path legado está sendo usado
- Isolamento multi-tenant está funcionando

---

## ETAPA 5 — INVESTIGACAO PROFISSIONAL

### Questão
O evento persistido e a consulta utilizam o mesmo profissional?

### Teste Realizado
Escrita com `profissional: "Carla"`
Leitura com variações: "Carla", "carla", "CARLA", "Carlá", com espacos, etc.

### Normalizacao
```python
prof_norm = unidecode((prof or "").strip().lower())
```

Resultado da normalização:
- "Carla" → "carla"
- "carla" → "carla"
- "CARLA" → "carla"
- "Carlá" → "carla" (acento removido)
- " Carla " → "carla" (espacos removidos)

### Resultado
```
[OK] "Carla" == "carla": SIM (match)
[OK] "Carlá" == "carla": SIM (match após unidecode)
[OK] "Ana Paula" == "ana paula": SIM (com espaco)
[OK] Todas as variações: MATCH
```

### Conclusão ETAPA 5
✅ **SEM DIVERGENCIA PROFISSIONAL**
- Profissional persistido bate com consultas normalizadas
- Normalização remove acentos, espacos e maiusculas
- Nenhuma divergência encontrada

---

## ETAPA 6 — INVESTIGACAO DATA E INTERVALO

### Questão
Data está correta? Timezone OK? Conversão de intervalo correto?

### Componentes Verificados
```
Data:
  formato_escrita: "2026-08-11"
  formato_consulta: "2026-08-11"
  Match: SIM

Intervalo:
  inicio_novo = datetime.fromisoformat(f"{data}T{hora_inicio}")
  fim_novo = inicio_novo + timedelta(minutes=duracao_min)

  Exemplo (90 min):
    14:00 + 90 min = 15:30 ✓

Normalizacao de hora:
  def normalizar_hora_para_grade(hora_str):
    m = (m // 20) * 20  # Ajusta para multiplos de 20
    return f"{h:02d}:{m:02d}"

  Exemplo:
    14:00 → 14:00 ✓
    14:30 → 14:20 (arredonda para baixo)
    14:25 → 14:20 (arredonda para baixo)
```

### Resultado
```
[OK] Data: formato consistente
[OK] Intervalo: calculo deterministico
[OK] Timezone: uso de local (nao usa UTC)
[OK] Normalizacao: ajusta para grade de 20 min
```

### Conclusão ETAPA 6
✅ **SEM PROBLEMAS DATA/INTERVALO**
- Data em formato consistente
- Intervalo calculado deterministicamente
- Nenhuma conversão incorreta de hora

---

## ETAPA 7 — INVESTIGACAO FILTROS

### Questão
Quais filtros podem estar removendo o evento?

### Filtros Aplicados em verificar_conflito_e_sugestoes_profissional()

```python
1. evento_deve_entrar_na_agenda(evento, data_consulta)
   ├─ Verifica se status != cancelado
   ├─ Verifica se tem profissional
   ├─ Verifica se tem data, hora_inicio, hora_fim
   └─ Verifica se data == data_consulta

2. event_id check
   └─ Ignora o prório evento se event_id for passado

3. Profissional match
   └─ Compara profissional normalizado

4. Parse interval
   └─ Verifica se consegue extrair hora_inicio/hora_fim

5. Data match
   └─ Verifica se data do evento == data_consulta

6. Intervalo overlap
   └─ Verifica se existe sobreposição temporal
```

### Resultado
```
[OK] Nenhum filtro remove indevidamente eventos validos
[OK] Filtro de data nao elimina quando bate
[OK] Filtro de profissional nao elimina quando bate
[OK] Status cancelado: DEVE ser ignorado (correto)
[OK] Intervalos calculados corretamente
```

### Conclusão ETAPA 7
✅ **FILTROS ESTAO CORRETOS**
- Cada filtro tem proposito valido
- Nenhuma exclusão inadvertida
- Status cancelado DEVE ser ignorado
- Para reagendamento: verificar se precisa incluir evento sendo alterado

---

## ETAPA 8 — INVESTIGACAO EVENTUAL CONSISTENCIA

### Questão
Poderia ser atraso do Firestore?

### Evidencia Coletada
```
[WRITE] Escrita concluida: 0.538s
  └─ Locks criados: 3
  └─ Evento persistido
  └─ Locks confirmados

[READ] Leitura apos escrita: 0.041s
  └─ Evento encontrado imediatamente

[VERIFY] Eventos encontrados: 1
  └─ ID correspondente
  └─ Dados completos
  └─ Sem delay observado
```

### Testes de Timing
```
Tempo entre escrita e primeira leitura: < 0.1s
Status: EVENTO ENCONTRADO IMEDIATAMENTE (nao ha delay)
```

### Resultado
```
[OK] Escrita completada com sucesso
[OK] Mesmo tenant na escrita e leitura
[OK] Mesmo path na escrita e leitura
[OK] Mesma colecao
[OK] Mesmo profissional
[OK] Mesma data
[OK] Query correta
[OK] Evento encontrado imediatamente

CONCLUSAO: NAO é atraso do Firestore
```

### Conclusão ETAPA 8
✅ **NAO é EVENTUAL CONSISTENCIA**
- Evento está disponível imediatamente após escrita
- Nenhum delay observado
- Firestore respondendo normalmente
- Path e tenant corretos na leitura

---

## ETAPA 9 — CORRECAO

### Evidencia de Falha Original
```
[PROBLEMA ORIGINAL]
[EVENTOS] Eventos existentes: {}
```

### Raiz Encontrada
**Arquivo:** `services/event_service_async.py`  
**Funcao:** `verificar_conflito_e_sugestoes_profissional()`  
**Linhas:** 1203-1220

**Codigo original (ERRADO):**
```python
dados_usuario = await buscar_dado_em_path(f"Clientes/{user_id}") or {}
user_id_efetivo = user_id

# Se document nao tem tipo_usuario, defaulta para "cliente"
tipo = (dados_usuario.get("tipo_usuario") or "cliente").strip().lower()

# Tenta resolver como cliente
if tipo == "cliente":
    user_id_efetivo = await obter_id_dono(user_id)  # ← PROBLEMA
```

**Problema:** Quando user_id é um tenant (nao tem documento ou documento nao tem id_negocio), o sistema tentava resolver como cliente, confundindo o path.

### Correcao Aplicada
```python
# CORRECAO P0: Se documento tem id_negocio, é cliente
# Se NAO tem id_negocio, provavelmente JÁ é tenant

if dados_usuario.get("id_negocio"):
    # Cliente: tem id_negocio → usar esse como tenant
    user_id_efetivo = dados_usuario.get("id_negocio")
else:
    # Tenant ou cliente desconhecido
    tipo = (dados_usuario.get("tipo_usuario") or "cliente").strip().lower()
    modo = (dados_usuario.get("modo_uso") or "").strip().lower()

    if tipo == "cliente" or modo == "atendimento_cliente":
        # Tentar resolver como cliente
        tenant_resolvido = await obter_id_dono(user_id)
        if tenant_resolvido:
            user_id_efetivo = tenant_resolvido
```

### Validacao da Correcao
```
[ANTES]
[EVENTOS] Eventos existentes: {}
[RESULTADO] Conflito: False ❌

[DEPOIS]
[EVENTOS] Eventos existentes: { "evt_test_001": {...} }
[RESULTADO] Conflito: True ✅
[RESULTADO] Sugestoes: 3 ✅
```

### Conclusão ETAPA 9
✅ **CORRECAO APLICADA E VALIDADA**
- Menor alteração arquitetural possível
- Preserva multi-tenancy
- Lógica de conflito permanece determinística no motor
- Nenhuma duplicação de regras
- Nenhum workaround específico para teste
- Correção resolve o problema no motor geral

---

## RESUMO EXECUTIVO

| Etapa | Questão | Resultado |
|-------|---------|-----------|
| **4** | tenant_id divergencia? | ✅ NAO - Match correto |
| **5** | Profissional divergencia? | ✅ NAO - Normalizacao funciona |
| **6** | Data/intervalo corretos? | ✅ SIM - Deterministico |
| **7** | Filtros OK? | ✅ SIM - Cada um com proposito |
| **8** | É atraso Firestore? | ✅ NAO - Resposta imediata |
| **9** | Correcao validada? | ✅ SIM - Eventos encontrados |

---

## RESULTADO FINAL

### Status Geral
```
[✓] Multi-tenant investigado: SEM PROBLEMAS
[✓] Profissional investigado: SEM PROBLEMAS
[✓] Data/intervalo investigado: SEM PROBLEMAS
[✓] Filtros investigados: SEM PROBLEMAS
[✓] Firestore investigado: SEM PROBLEMAS
[✓] Correcao P0 validada: FUNCIONA
```

### Sistema Pronto Para
✅ Implementacao de reagendamento (alterar_agendamento)
✅ Conflitos detectados corretamente
✅ Sugestoes oferecidas corretamente
✅ Multi-tenancy preservada
✅ Determinismo garantido

---

**Investigacao Completa:** 2026-08-11  
**Status:** ✅ **TODAS ETAPAS 4-9 VALIDADAS COM SUCESSO**  
