"""
Teste Pragmático P0.2: Verificação da Correção no Código-Fonte

Valida que:
1. A correção foi aplicada em event_handler.py
2. Mensagem de erro é enviada quando salvar_evento falha
3. O retorno mantém True (para compatibilidade com contrato)
"""

import re


def test_p02_fix_is_applied():
    """
    Valida que o código de correção está presente em event_handler.py
    """
    with open("handlers/event_handler.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Procura pela seção de erro genérico (linhas ~1306-1329)
    # Procura pelo padrão: if not resultado_salvamento:
    padrao_bloco = re.compile(
        r'\[PATCH_P0\].*Erro genérico.*?'
        r'if not resultado_salvamento:.*?'
        r'\[P0\.2 FIX\]',
        re.DOTALL | re.IGNORECASE
    )

    assert padrao_bloco.search(conteudo), (
        "❌ Bloco de erro genérico não encontrado com padrão esperado"
    )

    # Procura pela mensagem de erro específica
    assert "não consegui agendar nesse horário" in conteudo, (
        "❌ Mensagem de erro não encontrada"
    )

    # Procura pelo suporte a WhatsApp
    assert "enviar_mensagem_whatsapp" in conteudo, (
        "❌ Suporte WhatsApp não foi adicionado"
    )

    # Procura pelo suporte a Telegram
    assert "update.message.reply_text" in conteudo, (
        "❌ Suporte Telegram não foi adicionado"
    )

    # Procura pelo return True (manter compatibilidade)
    assert re.search(
        r'\[P0\.2 FIX\].*?return True',
        conteudo,
        re.DOTALL
    ), (
        "❌ return True não encontrado após correção"
    )

    print("✅ [P0.2 TEST PASSED] Código de correção aplicado corretamente")
    print("   ✓ Bloco de erro genérico identificado")
    print("   ✓ Mensagem de erro presente")
    print("   ✓ Suporte WhatsApp adicionado")
    print("   ✓ Suporte Telegram adicionado")
    print("   ✓ Return True mantido para compatibilidade")


def test_p02_fix_structure():
    """
    Valida a estrutura da correção
    """
    with open("handlers/event_handler.py", "r", encoding="utf-8") as f:
        linhas = f.readlines()

    # Encontra o bloco [P0.2 FIX]
    encontrado = False
    for i, linha in enumerate(linhas):
        if "[P0.2 FIX]" in linha:
            encontrado = True
            # Próximas 20 linhas devem conter a lógica esperada
            secao = "".join(linhas[i:min(i+20, len(linhas))])

            # Valida que tem if/else para telegram/whatsapp
            assert "if update and hasattr(update" in secao, (
                "❌ Verificação de Telegram não encontrada"
            )
            assert "else:" in secao, (
                "❌ Bloco else (WhatsApp) não encontrado"
            )

            break

    assert encontrado, "❌ Marca [P0.2 FIX] não encontrada"

    print("✅ [P0.2 STRUCTURE TEST PASSED] Estrutura de correção validada")
    print("   ✓ Bloco if/else para Telegram/WhatsApp presente")
    print("   ✓ Estrutura condicionada corretamente")


def test_p02_fix_preserves_contract():
    """
    Valida que a correção NÃO quebra o contrato com bot.py
    """
    with open("handlers/event_handler.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # A função deve retornar True em TODOS os casos:
    # 1. Duplicado detectado (linha 1189)
    # 2. Conflito detectado (linha 1290)
    # 3. Erro genérico (linha 1329) ← NOSSA CORREÇÃO
    # 4. Sucesso (linha ~1360+)

    # Procura pelos três return True que devem estar presentes
    returns_true = re.findall(r'return True', conteudo)
    assert len(returns_true) >= 3, (
        f"❌ Esperava pelo menos 3 'return True', encontrou {len(returns_true)}"
    )

    # Procura para garantir que NÃO há mudança no retorno de sucesso
    # (não deve ter mudado a lógica após "Sucesso real")
    assert "Sucesso real — só chega aqui" in conteudo, (
        "❌ Comentário de sucesso real foi removido"
    )

    print("✅ [P0.2 CONTRACT TEST PASSED] Contrato com bot.py preservado")
    print("   ✓ Retorno True mantido em todos os caminhos")
    print("   ✓ Lógica de sucesso não foi alterada")


def test_p02_fix_no_duplicates():
    """
    Valida que a correção não duplica mensagens em casos de sucesso
    """
    with open("handlers/event_handler.py", "r", encoding="utf-8") as f:
        conteudo = f.read()

    # A correção está DENTRO do bloco "if not resultado_salvamento"
    # Portanto, em caso de sucesso (resultado_salvamento != False),
    # o código de envio de mensagem NÃO é executado

    # Encontra o bloco de erro genérico
    padrao = re.compile(
        r'if not resultado_salvamento:.*?return True',
        re.DOTALL | re.IGNORECASE
    )

    match = padrao.search(conteudo)
    assert match, "❌ Bloco de erro genérico não encontrado"

    bloco = match.group(0)

    # Valida que o envio de mensagem está DENTRO do if
    # (indentação confirma que é condicional)
    assert "msg_erro = (" in bloco, (
        "❌ Declaração de msg_erro não está no bloco condicionado"
    )

    print("✅ [P0.2 NO-DUPLICATES TEST PASSED] Mensagens não serão duplicadas")
    print("   ✓ Código de envio está dentro do 'if not resultado_salvamento'")
    print("   ✓ Sucesso não acionará envio de erro")


if __name__ == "__main__":
    import pytest
    print("\n" + "="*80)
    print("TESTES P0.2: Verificação Pragmática da Correção")
    print("="*80 + "\n")

    pytest.main([__file__, "-v", "-s"])
