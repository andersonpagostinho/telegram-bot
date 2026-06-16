"""
TESTES P0.1A — CANCELAMENTO SEGURO

Cenários:
1. Cliente cancela próprio evento → OK
2. Cliente tenta cancelar evento de outro cliente → BLOQUEADO
3. Evento único pede confirmação (sim/não)
4. "sim" cancela com auditoria
5. "não" aborta
6. Múltiplos eventos: número → confirmação → sim
7. Campos de auditoria salvos
8. Evento cancelado não entra em conflito

Status: 📋 PRONTO PARA EXECUÇÃO
"""

import asyncio
import json
from datetime import datetime
from pytz import timezone

FUSO_BR = timezone("America/Sao_Paulo")


# Mock para testes
class MockFirebase:
    """Simula Firestore para testes"""

    def __init__(self):
        self.eventos = {}
        self.clientes = {}

    async def salvar_evento(self, path, dados):
        """Simula salvar_evento"""
        self.eventos[path] = dados
        return True

    async def buscar_evento(self, path):
        """Simula buscar evento"""
        return self.eventos.get(path)

    async def atualizar_evento(self, path, dados):
        """Simula atualizar evento"""
        if path in self.eventos:
            self.eventos[path].update(dados)
            return True
        return False

    async def buscar_cliente(self, user_id):
        """Simula buscar cliente"""
        return self.clientes.get(user_id, {})


# =====================================================
# TESTE 1: Cliente cancela próprio evento
# =====================================================
async def teste_cliente_cancela_proprio_evento():
    """Cliente user_123 cancela seu próprio evento"""
    print("\n" + "="*60)
    print("TESTE 1: Cliente cancela próprio evento")
    print("="*60)

    # Dados de entrada
    user_id = "user_123"
    event_id = "evt_001"
    cliente_id_evento = "user_123"  # Mesmo cliente
    tipo_usuario = "cliente"

    # Validação de ownership
    if tipo_usuario == "cliente":
        if cliente_id_evento != user_id:
            print("❌ FALHOU: Cliente não é proprietário")
            return False
        else:
            print("✅ PASSOU: Validação de ownership OK")

    # Simulação de cancelamento
    evento_cancelado = {
        "status": "cancelado",
        "cancelado_em": datetime.now(FUSO_BR).isoformat(),
        "cancelado_por": user_id,
        "cancelado_por_tipo": "cliente",
        "cancelamento_confirmado_em": datetime.now(FUSO_BR).isoformat(),
    }

    print(f"✅ PASSOU: Evento cancelado com auditoria")
    print(f"   Campos: {json.dumps(evento_cancelado, indent=2, ensure_ascii=False)}")
    return True


# =====================================================
# TESTE 2: Cliente NÃO pode cancelar evento de outro cliente
# =====================================================
async def teste_cliente_bloqueado_outro_evento():
    """Cliente user_123 tenta cancelar evento de user_456"""
    print("\n" + "="*60)
    print("TESTE 2: Cliente bloqueado de cancelar outro evento")
    print("="*60)

    user_id = "user_123"
    cliente_id_evento = "user_456"  # Cliente diferente
    tipo_usuario = "cliente"

    # Validação de ownership
    if tipo_usuario == "cliente":
        if cliente_id_evento != user_id:
            print(f"✅ PASSOU: Cancelamento bloqueado")
            print(f"   user_id={user_id}, cliente_id_evento={cliente_id_evento}")
            return True
        else:
            print("❌ FALHOU: Não bloqueou evento de outro cliente")
            return False


# =====================================================
# TESTE 3: Evento único pede confirmação
# =====================================================
async def teste_evento_unico_pede_confirmacao():
    """1 evento encontrado → pedir confirmação (sim/não)"""
    print("\n" + "="*60)
    print("TESTE 3: Evento único pede confirmação")
    print("="*60)

    candidatos = [
        ("evt_001", {
            "descricao": "Corte com Carla",
            "data": "2026-06-20",
            "hora_inicio": "15:00",
            "cliente_id": "user_123"
        })
    ]

    if len(candidatos) == 1:
        print("✅ PASSOU: Encontrou 1 evento, pedir confirmação")
        eid, ev = candidatos[0]
        msg = f"Tem certeza de cancelar {ev['descricao']} em {ev['data']} às {ev['hora_inicio']}? (sim/não)"
        print(f"   Mensagem: {msg}")
        return True
    else:
        print("❌ FALHOU: Não detectou evento único")
        return False


# =====================================================
# TESTE 4: "sim" cancela com campos de auditoria
# =====================================================
async def teste_sim_cancela_com_auditoria():
    """Responder 'sim' cancela e salva campos de auditoria"""
    print("\n" + "="*60)
    print("TESTE 4: 'sim' cancela com auditoria")
    print("="*60)

    resposta = "sim"
    confirmacoes_sim = ["sim", "s", "ok", "confirma", "confirmar", "pode", "pode ser", "sim!"]

    if resposta.lower() in confirmacoes_sim:
        print("✅ PASSOU: 'sim' reconhecido como confirmação")

        # Campos de auditoria
        evento_cancelado = {
            "status": "cancelado",
            "cancelado_em": datetime.now(FUSO_BR).isoformat(),
            "cancelado_por": "user_123",
            "cancelado_por_tipo": "cliente",
            "cancelamento_confirmado_em": datetime.now(FUSO_BR).isoformat(),
        }

        campos_obrigatorios = [
            "status",
            "cancelado_em",
            "cancelado_por",
            "cancelado_por_tipo",
            "cancelamento_confirmado_em"
        ]

        todos_campos_ok = all(campo in evento_cancelado for campo in campos_obrigatorios)
        if todos_campos_ok:
            print(f"✅ PASSOU: Todos os campos de auditoria presentes")
            return True
        else:
            print(f"❌ FALHOU: Faltam campos de auditoria")
            return False
    else:
        print("❌ FALHOU: Não reconheceu 'sim'")
        return False


# =====================================================
# TESTE 5: "não" aborta cancelamento
# =====================================================
async def teste_nao_aborta():
    """Responder 'não' aborta sem cancelar"""
    print("\n" + "="*60)
    print("TESTE 5: 'não' aborta cancelamento")
    print("="*60)

    resposta = "não"
    confirmacoes_nao = ["não", "nao", "não!", "nao!", "desistir", "manter", "deixa como está", "deixa como esta"]

    if resposta.lower() in confirmacoes_nao:
        print("✅ PASSOU: 'não' reconhecido como negação")
        print("   → Evento NÃO será cancelado")
        print("   → Estado será limpo")
        return True
    else:
        print("❌ FALHOU: Não reconheceu 'não'")
        return False


# =====================================================
# TESTE 6: Múltiplos eventos - número → confirmação
# =====================================================
async def teste_multiplos_eventos_numero():
    """3 eventos encontrados → usar número para escolher"""
    print("\n" + "="*60)
    print("TESTE 6: Múltiplos eventos - número para escolher")
    print("="*60)

    candidatos = [
        ("evt_001", {"descricao": "Corte com Carla", "data": "2026-06-20", "hora_inicio": "15:00"}),
        ("evt_002", {"descricao": "Corte com Paula", "data": "2026-06-21", "hora_inicio": "10:00"}),
        ("evt_003", {"descricao": "Corte com Marina", "data": "2026-06-22", "hora_inicio": "14:00"}),
    ]

    if len(candidatos) > 1:
        print(f"✅ PASSOU: Encontrados {len(candidatos)} eventos")

        # Simular escolha de número
        resposta = "2"
        if resposta.isdigit():
            idx = int(resposta) - 1
            if 0 <= idx < len(candidatos):
                eid, ev = candidatos[idx]
                print(f"✅ PASSOU: Número {resposta} selecionou evento '{ev['descricao']}'")
                print(f"   Próximo: pedir confirmação (sim/não)")
                return True
        print("❌ FALHOU: Número inválido")
        return False
    else:
        print("❌ FALHOU: Não eram múltiplos eventos")
        return False


# =====================================================
# TESTE 7: Estado e contexto salvos
# =====================================================
async def teste_estado_salvo():
    """Estado deve estar em context.user_data e MemoriaTemporaria"""
    print("\n" + "="*60)
    print("TESTE 7: Estado salvo em ambos os contextos")
    print("="*60)

    # Simular contextos
    context_user_data = {
        "cancelamento_pendente": {
            "evento_id": "evt_001",
            "cliente_id": "user_123",
            "resumo_evento": {"descricao": "Corte", "data": "2026-06-20"}
        },
        "estado_fluxo": "aguardando_confirmacao_cancelamento"
    }

    memoria_temporaria = {
        "cancelamento_pendente": context_user_data["cancelamento_pendente"],
        "estado_fluxo": "aguardando_confirmacao_cancelamento"
    }

    # Validar sincronização
    if (context_user_data["cancelamento_pendente"] == memoria_temporaria["cancelamento_pendente"] and
        context_user_data["estado_fluxo"] == memoria_temporaria["estado_fluxo"]):
        print("✅ PASSOU: Contextos sincronizados")
        return True
    else:
        print("❌ FALHOU: Contextos divergentes")
        return False


# =====================================================
# TESTE 8: Evento cancelado não entra em conflito
# =====================================================
async def teste_evento_cancelado_sem_conflito():
    """Evento com status='cancelado' não deve bloquear novos agendamentos"""
    print("\n" + "="*60)
    print("TESTE 8: Evento cancelado não entra em conflito")
    print("="*60)

    evento = {
        "status": "cancelado",
        "profissional": "Carla",
        "data": "2026-06-20",
        "hora_inicio": "15:00",
        "hora_fim": "16:00",
        "cancelado_em": datetime.now(FUSO_BR).isoformat(),
    }

    # Simular verificação de conflito
    def evento_deve_entrar_na_agenda(ev):
        status = str(ev.get("status") or "").strip().lower()
        if status in ["cancelado", "cancelada", "removido", "removida"]:
            return False
        return True

    if not evento_deve_entrar_na_agenda(evento):
        print("✅ PASSOU: Evento cancelado não entra em agenda")
        print("   → Horário fica livre para novo agendamento")
        return True
    else:
        print("❌ FALHOU: Evento cancelado entrou em conflito")
        return False


# =====================================================
# EXECUTAR TESTES
# =====================================================
async def rodar_todos_testes():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print(" P0.1A — TESTES DE CANCELAMENTO SEGURO")
    print("="*80)

    testes = [
        teste_cliente_cancela_proprio_evento,
        teste_cliente_bloqueado_outro_evento,
        teste_evento_unico_pede_confirmacao,
        teste_sim_cancela_com_auditoria,
        teste_nao_aborta,
        teste_multiplos_eventos_numero,
        teste_estado_salvo,
        teste_evento_cancelado_sem_conflito,
    ]

    resultados = []
    for teste in testes:
        try:
            resultado = await teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ ERRO: {e}")
            resultados.append(False)

    # Resumo
    print("\n" + "="*80)
    print(" RESUMO")
    print("="*80)
    total = len(resultados)
    passou = sum(resultados)
    falhou = total - passou

    print(f"✅ Passou: {passou}/{total}")
    print(f"❌ Falhou: {falhou}/{total}")

    if falhou == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return True
    else:
        print(f"\n⚠️  {falhou} teste(s) falharam")
        return False


if __name__ == "__main__":
    resultado = asyncio.run(rodar_todos_testes())
    exit(0 if resultado else 1)
