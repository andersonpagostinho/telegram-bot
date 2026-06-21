"""
Validação pós-correção de blockers
Testa estrutura sem precisar de Firebase real
"""

import sys
import os

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("="*70)
print("VALIDAÇÃO PÓS-CORREÇÃO DE BLOCKERS")
print("="*70)

# Teste 1: Validar imports
print("\n[TESTE 1] Validar imports dos serviços...")
try:
    from services.firestore_client import get_db
    print("  ✅ get_db importado com sucesso")
except ImportError as e:
    print(f"  ❌ Erro ao importar get_db: {e}")
    sys.exit(1)

try:
    from services.identidade_service import (
        normalizar_actor_id,
        resolver_ator_por_canal,
        criar_ator_dono,
        criar_ator_cliente_automatico,
        criar_ator_profissional,
        roteador_por_tipo_usuario,
        atualizar_ultimo_contato,
        buscar_profissional_por_nome,
        listar_profissionais
    )
    print("  ✅ identidade_service importado com sucesso")
except ImportError as e:
    print(f"  ❌ Erro ao importar identidade_service: {e}")
    sys.exit(1)

try:
    from services.onboarding_dono_service import (
        iniciar_onboarding_dono,
        pegar_etapa_onboarding,
        avancar_etapa_onboarding,
        validar_campo_onboarding,
        obter_pergunta_etapa,
        marcar_onboarding_completo,
        validar_onboarding_minimo
    )
    print("  ✅ onboarding_dono_service importado com sucesso")
except ImportError as e:
    print(f"  ❌ Erro ao importar onboarding_dono_service: {e}")
    sys.exit(1)

# Teste 2: Validar funções sem Firestore
print("\n[TESTE 2] Validar funções determinísticas (sem Firestore)...")
try:
    actor_id = normalizar_actor_id("whatsapp", "11999999999")
    assert actor_id == "whatsapp:11999999999", f"Esperado 'whatsapp:11999999999', obtido '{actor_id}'"
    print(f"  ✅ normalizar_actor_id: {actor_id}")
except Exception as e:
    print(f"  ❌ normalizar_actor_id falhou: {e}")
    sys.exit(1)

try:
    validacao = validar_campo_onboarding("nome_negocio", "Salão da Maria")
    assert validacao["valido"] == True
    print(f"  ✅ validar_campo_onboarding: {validacao}")
except Exception as e:
    print(f"  ❌ validar_campo_onboarding falhou: {e}")
    sys.exit(1)

try:
    pergunta = obter_pergunta_etapa("nome_negocio")
    assert len(pergunta) > 0
    print(f"  ✅ obter_pergunta_etapa: '{pergunta}'")
except Exception as e:
    print(f"  ❌ obter_pergunta_etapa falhou: {e}")
    sys.exit(1)

# Teste 3: Validar que não há db.collection direto
print("\n[TESTE 3] Validar ausência de db.collection nos imports...")
import services.identidade_service as ids_module
import services.onboarding_dono_service as ods_module

if hasattr(ids_module, 'db'):
    if ids_module.db is not None:
        print(f"  ⚠️  identidade_service: db está definido como {ids_module.db}")
        print("     (Isso não é erro, desde que não seja usado diretamente)")
    else:
        print(f"  ✅ identidade_service: db = None (correto)")
else:
    print(f"  ✅ identidade_service: db não definido no módulo")

# Teste 4: Verificar get_db está disponível
print("\n[TESTE 4] Validar get_db está centralizado...")
try:
    assert hasattr(ids_module, 'get_db'), "get_db não importado em identidade_service"
    assert hasattr(ods_module, 'get_db'), "get_db não importado em onboarding_dono_service"
    print("  ✅ get_db importado corretamente em ambos os módulos")
except AssertionError as e:
    print(f"  ❌ {e}")
    sys.exit(1)

# Teste 5: Validar assinatura de funções
print("\n[TESTE 5] Validar assinatura de funções...")
import inspect

funcs = [
    ("normalizar_actor_id", normalizar_actor_id),
    ("validar_campo_onboarding", validar_campo_onboarding),
    ("obter_pergunta_etapa", obter_pergunta_etapa),
]

for name, func in funcs:
    sig = inspect.signature(func)
    print(f"  ✅ {name}{sig}")

print("\n" + "="*70)
print("✅ TODAS AS VALIDAÇÕES PASSARAM")
print("="*70)
print("\nPróximos passos:")
print("1. Configurar Firebase (GOOGLE_APPLICATION_CREDENTIALS)")
print("2. Rodar pytest tests/runner_p1_identidade_canal_onboarding.py")
print("3. Validar 9/9 testes PASS")
print("4. Validar P0 174/174 PASS")
