"""O fluxo de uma mensagem: intérprete -> código -> redator -> validação.

`llm` é qualquer objeto com interpretar(), redigir() e ler_imagem() (ver llm.py).
"""
from . import contexto, memoria, prompts, validacao

INTENCOES = set(contexto.MONTADORES)

RESPOSTA_SEGURA = (
    "Desculpa, não consegui montar uma resposta confiável agora. "
    "Pode me contar de outro jeito o que você precisa?"
)
RESPOSTA_ACOLHIMENTO = (
    "Ei, tô aqui. Um dia difícil com a comida não define nada sobre você. "
    "Se isso está pesando, vale conversar com um profissional de saúde. "
    "E, se precisar falar com alguém agora, o CVV atende de graça, a qualquer hora, pelo 188 ou em cvv.org.br."
)


def limpar_interpretacao(bruta):
    """Garante o formato do JSON do intérprete, mesmo se o modelo errar um campo."""
    intencao = bruta.get("intencao")
    alimentos = []
    for item in bruta.get("alimentos") or []:
        if isinstance(item, dict) and item.get("descricao"):
            gramas = item.get("gramas")
            gramas = float(gramas) if isinstance(gramas, (int, float)) and gramas > 0 else None
            alimentos.append({"descricao": str(item["descricao"]), "gramas": gramas})
    agua = bruta.get("agua_ml")
    return {
        "intencao": intencao if intencao in INTENCOES else "conversa",
        "alimentos": alimentos,
        "agua_ml": float(agua) if isinstance(agua, (int, float)) and agua > 0 else None,
        "precisa_confirmar": bool(bruta.get("precisa_confirmar")),
        "menciona_condicao_clinica": bruta.get("menciona_condicao_clinica") or None,
    }


def sistema_do_redator(perfil, texto_contexto):
    return prompts.REDATOR.format(
        nome=perfil["nome"],
        nivel=perfil["nivel_dedicacao"],
        instrucao_de_tom=prompts.TOM[perfil["nivel_dedicacao"]],
        contexto=texto_contexto,
    )


def responder(llm, perfil, estado, mensagem, hoje):
    """Responde a uma mensagem. Não salva nada: registros voltam como propostas para a tela."""
    interp = limpar_interpretacao(llm.interpretar(mensagem, memoria.historico_texto(estado)))
    texto_contexto, propostas = contexto.montar(interp, perfil, estado, hoje)
    sistema = sistema_do_redator(perfil, texto_contexto)

    resposta = llm.redigir(sistema, mensagem)
    problemas_iniciais = validacao.problemas(resposta, perfil, texto_contexto, mensagem, interp["intencao"])
    problemas = problemas_iniciais
    if problemas:
        correcao = prompts.CORRECAO.format(problemas="\n".join(problemas))
        resposta = llm.redigir(sistema + correcao, mensagem)
        problemas = validacao.problemas(resposta, perfil, texto_contexto, mensagem, interp["intencao"])
    if problemas:
        resposta = RESPOSTA_ACOLHIMENTO if interp["intencao"] == "risco" else RESPOSTA_SEGURA

    return {
        "texto": resposta,
        "interpretacao": interp,
        "contexto": texto_contexto,
        "propostas": propostas,
        "validacao": {
            "reprovada_na_primeira": problemas_iniciais,
            "reprovada_na_segunda": problemas,
        },
    }
