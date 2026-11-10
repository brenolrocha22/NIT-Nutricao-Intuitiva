"""Lista de feira: soma os ingredientes do cardápio para o período e desconta a despensa."""
from collections import defaultdict


def lista_de_feira(cardapio, receitas, dias, pessoas, despensa=None):
    """Quantidade de cada ingrediente para o período.

    `cardapio` é uma lista de {"receita": id, "vezes_por_semana": n}. Cada vez
    que a receita entra no cardápio, conta uma porção por pessoa da casa.
    Os temperos sem cálculo ("sal a gosto") não entram na lista com peso.
    """
    por_id = {r["id"]: r for r in receitas}
    total = defaultdict(float)
    nomes = {}
    for item in cardapio:
        receita = por_id[item["receita"]]
        porcoes = item["vezes_por_semana"] * dias / 7 * pessoas
        for ingrediente in receita["ingredientes"]:
            total[ingrediente["taco"]] += ingrediente["gramas"] / receita["porcoes"] * porcoes
            nomes.setdefault(ingrediente["taco"], ingrediente["nome"])

    em_casa = {i["taco"]: i["restante_g"] for i in (despensa or {}).get("itens", [])}
    lista = []
    for numero, gramas in total.items():
        comprar = max(gramas - em_casa.get(numero, 0), 0)
        if comprar > 0:
            lista.append({"taco": numero, "nome": nomes[numero], "gramas": arredondar_compra(comprar)})
    return sorted(lista, key=lambda i: -i["gramas"])


def arredondar_compra(gramas):
    """Arredonda para cima em múltiplos práticos: ninguém compra 437 g de arroz."""
    passo = 50 if gramas < 1000 else 250
    return int(-(-gramas // passo) * passo)
