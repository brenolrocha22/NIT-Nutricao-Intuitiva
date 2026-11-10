"""Despensa: ritmo de consumo de cada item e previsão da próxima feira."""
from datetime import date, timedelta

# Itens que a pessoa confirma ter uma vez e que não entram na cobrança de
# "falta na despensa": cebola, alho, óleo de soja, azeite, cebolinha, salsa.
TEMPEROS_BASICOS = {107, 82, 272, 260, 108, 153}


def previsao_item(item, data_ultima_feira, hoje):
    """Quanto o item rende por dia e quando acaba, supondo o mesmo ritmo de consumo."""
    dias = max((hoje - data_ultima_feira).days, 1)
    consumido = item["comprado_g"] - item["restante_g"]
    por_dia = consumido / dias
    if item["restante_g"] <= 0:
        situacao, acaba_em = "acabou", hoje
    elif por_dia <= 0:
        situacao, acaba_em = "parado", None
    else:
        acaba_em = hoje + timedelta(days=int(item["restante_g"] / por_dia))
        situacao = "acabando" if (acaba_em - hoje).days <= 3 else "ok"
    return {
        "taco": item["taco"],
        "nome": item["nome"],
        "restante_g": item["restante_g"],
        "consumo_g_dia": round(por_dia),
        "acaba_em": acaba_em,
        "situacao": situacao,
    }


def resumo(despensa, hoje, periodo_feira_dias):
    """Previsão de todos os itens e a data sugerida para a próxima feira.

    A próxima feira é o dia em que o primeiro item em uso acaba, sem passar do
    período escolhido pela pessoa (15 ou 30 dias depois da última feira).
    """
    ultima = date.fromisoformat(despensa["data_ultima_feira"])
    itens = [previsao_item(i, ultima, hoje) for i in despensa["itens"]]
    limite = ultima + timedelta(days=periodo_feira_dias)
    em_uso = [i["acaba_em"] for i in itens if i["situacao"] in ("ok", "acabando")]
    proxima = min(em_uso + [limite])
    return {
        "itens": itens,
        "acabaram": [i["nome"] for i in itens if i["situacao"] == "acabou"],
        "parados": [i["nome"] for i in itens if i["situacao"] == "parado"],
        "proxima_feira": max(proxima, hoje),
        "motivo": "fim do período escolhido" if proxima == limite else "um item vai acabar",
    }


def registrar_feira(despensa, compras, data_feira):
    """Abre um novo período de feira: o que sobrou mais o que foi comprado.

    `compras` é uma lista de {"taco", "nome", "gramas"}. Para a previsão de
    consumo, 'comprado_g' passa a ser o estoque no dia da feira.
    """
    itens = {i["taco"]: {**i, "comprado_g": i["restante_g"]} for i in despensa["itens"] if i["restante_g"] > 0}
    for compra in compras:
        item = itens.setdefault(compra["taco"], {"taco": compra["taco"], "nome": compra["nome"], "comprado_g": 0, "restante_g": 0})
        item["comprado_g"] += compra["gramas"]
        item["restante_g"] += compra["gramas"]
    return {"data_ultima_feira": data_feira.isoformat(), "itens": list(itens.values())}


def receitas_com_a_despensa(receitas, despensa):
    """Ordena as receitas pelo que já tem em casa e lista o que falta em cada uma.

    Temperos básicos não contam como falta. Receitas que usam itens parados
    (comprados e ainda não usados) sobem na lista, para não deixar estragar.
    """
    em_casa = {i["taco"] for i in despensa["itens"] if i["restante_g"] > 0}
    parados = {i["taco"] for i in despensa["itens"] if i["restante_g"] == i["comprado_g"] > 0}
    resultado = []
    for receita in receitas:
        usados = {i["taco"] for i in receita["ingredientes"]}
        faltam = [i["nome"] for i in receita["ingredientes"]
                  if i["taco"] not in em_casa and i["taco"] not in TEMPEROS_BASICOS]
        tem = usados & em_casa
        if not tem:
            continue
        resultado.append({
            "id": receita["id"],
            "nome": receita["nome"],
            "faltam": faltam,
            "usa_item_parado": bool(usados & parados),
            "itens_de_casa": len(tem),
        })
    resultado.sort(key=lambda r: (len(r["faltam"]), not r["usa_item_parado"], -r["itens_de_casa"]))
    return resultado
