"""Restrições alimentares: decide o que cada pessoa não pode comer.

Esta é a principal barreira de segurança do NIT. O filtro roda ANTES de a IA
receber qualquer dado, e a validação roda DEPOIS, no texto que ela escreveu.
"""
import re
import unicodedata

from . import dados


def normalizar(texto):
    """Minúsculas e sem acentos, para comparar 'Pão' com 'pao'."""
    decomposto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def tem_palavra(palavra, texto):
    """Procura a palavra inteira: 'quibe' não pode bater em 'quibebe'."""
    padrao = r"(?<![\w-])" + re.escape(normalizar(palavra)) + r"(?![\w-])"
    return re.search(padrao, normalizar(texto)) is not None


def regras(chave):
    """Junta grupos, palavras e exceções de uma restrição e das que ela herda."""
    todas = dados.restricoes()["restricoes"]
    regra = todas[chave]
    grupos = set(regra["grupos"])
    palavras = list(regra["palavras"])
    excecoes = list(regra["excecoes"])
    for herdada in regra.get("herda", []):
        g, p, e = regras(herdada)
        grupos |= g
        palavras += p
        excecoes += e
    return grupos, palavras, excecoes


def proibido(chave, descricao, grupo="", nome=""):
    """True se o alimento fere a restrição.

    `descricao` e `grupo` vêm da TACO; `nome` é como a receita chama o ingrediente.
    Os dois textos são verificados, porque a receita pode dizer "manteiga" para um
    item da TACO de outra descrição.
    """
    grupos, palavras, excecoes = regras(chave)
    texto = f"{descricao} {nome}"
    if any(normalizar(e) in normalizar(texto) for e in excecoes):
        return False
    return grupo in grupos or any(tem_palavra(p, texto) for p in palavras)


def ingrediente_proibido(ingrediente, perfil):
    """Lista as restrições (ou 'nao_gosta') que barram um ingrediente de receita."""
    alimento = dados.taco()[ingrediente["taco"]]
    motivos = [
        chave for chave in perfil.get("restricoes", [])
        if proibido(chave, alimento["descricao"], alimento["grupo"], ingrediente["nome"])
    ]
    for item in perfil.get("nao_gosta", []):
        if tem_palavra(item, f"{alimento['descricao']} {ingrediente['nome']}"):
            motivos.append("nao_gosta")
    return motivos


def filtrar_receitas(perfil, receitas=None):
    """Separa as receitas em permitidas e bloqueadas para a pessoa.

    Uma receita é permitida se nenhum ingrediente for barrado, ou se todos os
    barrados forem opcionais: nesse caso ela volta adaptada, sem esses itens.
    """
    receitas = dados.receitas() if receitas is None else receitas
    permitidas, bloqueadas = [], []
    for receita in receitas:
        barrados = [i for i in receita["ingredientes"] if ingrediente_proibido(i, perfil)]
        if not barrados:
            permitidas.append({**receita, "retirados": []})
        elif all(i.get("opcional") for i in barrados):
            restantes = [i for i in receita["ingredientes"] if i not in barrados]
            permitidas.append({**receita, "ingredientes": restantes, "retirados": [i["nome"] for i in barrados]})
        else:
            bloqueadas.append({"id": receita["id"], "motivo": [i["nome"] for i in barrados]})
    return permitidas, bloqueadas


def palavras_proibidas_no_texto(texto, perfil):
    """Valida a resposta da IA: procura alimentos proibidos citados no texto.

    Ignora menções negadas logo antes ("sem queijo", "não tem leite"), que são
    justamente o jeito certo de falar da restrição.
    """
    texto = normalizar(texto)
    encontradas = []
    for chave in perfil.get("restricoes", []):
        _, palavras, excecoes = regras(chave)
        for palavra in palavras:
            padrao = r"(?<![\w-])" + re.escape(normalizar(palavra)) + r"(?![\w-])"
            for achado in re.finditer(padrao, texto):
                antes = texto[max(0, achado.start() - 25):achado.start()]
                depois = texto[achado.start():achado.start() + 40]
                if re.search(r"\b(sem|nao|nada de|nenhum|nenhuma|zero)\b[\w ,]*$", antes):
                    continue
                if any(normalizar(e) in depois for e in excecoes):
                    continue
                encontradas.append(palavra)
    return sorted(set(encontradas))
