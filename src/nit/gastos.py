"""Gastos reais com comida, só com os preços dos cupons fiscais que a pessoa enviou."""
from datetime import date


def total_cupom(cupom):
    return round(sum(i["valor"] for i in cupom["itens"] if i.get("valor") is not None), 2)


def resumo(cupons):
    """Média por feira e, com dois cupons ou mais, o gasto por dia e por mês.

    O gasto por dia usa os cupons ANTERIORES ao último, divididos pelos dias entre
    a primeira e a última compra: a comida do último cupom ainda está sendo consumida.
    """
    if not cupons:
        return None
    ordenados = sorted(cupons, key=lambda c: c["data"])
    totais = [total_cupom(c) for c in ordenados]
    resultado = {
        "feiras": len(ordenados),
        "total": round(sum(totais), 2),
        "media_por_feira": round(sum(totais) / len(totais), 2),
        "por_dia": None,
        "por_mes": None,
        "primeira": ordenados[0]["data"],
        "ultima": ordenados[-1]["data"],
    }
    if len(ordenados) >= 2:
        dias = (date.fromisoformat(ordenados[-1]["data"]) - date.fromisoformat(ordenados[0]["data"])).days
        if dias > 0:
            por_dia = sum(totais[:-1]) / dias
            resultado["por_dia"] = round(por_dia, 2)
            resultado["por_mes"] = round(por_dia * 30, 2)
    return resultado


def precos_pagos(cupons):
    """Último preço pago por item, com a data e o mercado."""
    precos = {}
    for cupom in sorted(cupons, key=lambda c: c["data"]):
        for item in cupom["itens"]:
            if item.get("valor") is None:
                continue
            precos[item["descricao"]] = {
                "valor": item["valor"],
                "quantidade": item.get("quantidade"),
                "unidade": item.get("unidade"),
                "data": cupom["data"],
                "mercado": cupom.get("mercado"),
            }
    return precos
