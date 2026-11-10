"""Plano alimentar: cardápio da semana com as receitas permitidas e porções para bater a meta.

Tudo aqui é regra fixa, sem IA: as mesmas respostas do questionário geram
sempre o mesmo cardápio.
"""
from . import nutricao, restricoes, triagem

# Arroz e feijão acompanham o almoço todo dia. São feitos em quantidade para
# vários dias, por isso não passam pelo limite de tempo de cozinha.
ACOMPANHAMENTOS_FIXOS = ["arroz-soltinho", "feijao-carioca-caseiro"]

# Receita com pelo menos isto de proteína por porção conta como prato principal
PROTEINA_PRATO_PRINCIPAL_G = 9

# O que compõe cada refeição. None: qualquer receita indicada para aquela refeição.
ESTRUTURA = [
    ("café da manhã", [None]),
    ("almoço", ["prato principal", "acompanhamento"]),
    ("lanche", [None]),
    ("jantar", ["prato principal", "acompanhamento"]),
]

OPCOES_POR_PRATO = 3


def papel(receita):
    proteina = nutricao.nutrientes_receita(receita)["por_porcao"]["proteina_g"]
    return "prato principal" if proteina >= PROTEINA_PRATO_PRINCIPAL_G else "acompanhamento"


def distribuir(n_opcoes, dias=7):
    """Divide os dias da semana entre as opções: 3 opções -> 3, 2 e 2 vezes."""
    base, resto = divmod(dias, n_opcoes)
    return [base + (1 if i < resto else 0) for i in range(n_opcoes)]


def escolher(candidatas, tempo_limite, ja_usadas):
    """As opções mais rápidas e baratas, de preferência dentro do tempo da pessoa.

    Evita repetir o que já entrou em outra refeição; se não sobrar nada, repete.
    """
    novas = [r for r in candidatas if r["id"] not in ja_usadas] or candidatas
    ordem = sorted(novas, key=lambda r: (r["tempo_min"] > tempo_limite, r["custo"] != "baixo", r["tempo_min"], r["id"]))
    return ordem[:OPCOES_POR_PRATO]


def cardapio(perfil):
    """Cardápio da semana: para cada refeição, os pratos e quantas vezes cada opção aparece."""
    permitidas, _ = restricoes.filtrar_receitas(perfil)
    por_id = {r["id"]: r for r in permitidas}
    tempo = perfil.get("tempo_cozinha_min", 60)
    variaveis = [r for r in permitidas if r["id"] not in ACOMPANHAMENTOS_FIXOS]

    usadas = set()
    refeicoes = []
    for refeicao, papeis in ESTRUTURA:
        pratos = []
        for p in papeis:
            candidatas = [r for r in variaveis if refeicao in r["refeicoes"] and (p is None or papel(r) == p)]
            if not candidatas:
                continue
            opcoes = escolher(candidatas, tempo, usadas)
            usadas |= {r["id"] for r in opcoes}
            vezes = distribuir(len(opcoes))
            pratos.append({
                "papel": p or refeicao,
                "opcoes": [{"receita": r, "vezes_por_semana": v} for r, v in zip(opcoes, vezes)],
            })
        if pratos:
            fixas = [por_id[i] for i in ACOMPANHAMENTOS_FIXOS if i in por_id] if refeicao == "almoço" else []
            refeicoes.append({"refeicao": refeicao, "fixas": fixas, "pratos": pratos})
    return {"refeicoes": refeicoes, "receitas": permitidas}


def dia_de_exemplo(refeicoes):
    """Receitas de um dia: os acompanhamentos fixos e a primeira opção de cada prato."""
    dia = []
    for refeicao in refeicoes:
        receitas = refeicao["fixas"] + [prato["opcoes"][0]["receita"] for prato in refeicao["pratos"]]
        dia.append((refeicao["refeicao"], receitas))
    return dia


def montar(perfil):
    """Plano completo: metas do dia, cardápio e o tamanho da porção.

    A porção é ajustada para o dia de exemplo chegar perto da meta de calorias,
    em passos de 1/4 de porção, entre 0,75 e 2,5 porções.
    """
    if not triagem.pode_montar_plano(perfil):
        return {"bloqueado": True, "motivos": triagem.motivos_para_nutricionista(perfil)}

    metas = nutricao.metas_do_dia(perfil)
    menu = cardapio(perfil)
    exemplo = dia_de_exemplo(menu["refeicoes"])
    kcal_dia = sum(
        nutricao.nutrientes_receita(r)["por_porcao"]["energia_kcal"] for _, receitas in exemplo for r in receitas
    )
    fator = 1.0
    if kcal_dia > 0:
        fator = min(max(round(metas["kcal"] / kcal_dia * 4) / 4, 0.75), 2.5)

    return {
        "bloqueado": False,
        "metas": metas,
        "refeicoes": menu["refeicoes"],
        "receitas": menu["receitas"],
        "dia_de_exemplo": exemplo,
        "kcal_dia_exemplo": round(kcal_dia),
        "fator_porcao": fator,
        "kcal_dia_ajustado": round(kcal_dia * fator),
    }


def para_feira(perfil):
    """O plano, ou, para quem foi encaminhado ao nutricionista, o cardápio com porções
    normais: receitas, feira e despensa continuam disponíveis mesmo sem plano."""
    plano = montar(perfil)
    if not plano["bloqueado"]:
        return plano
    return {**cardapio(perfil), "fator_porcao": 1.0}


def itens_para_feira(plano):
    """Receitas e vezes por semana no formato de feira.lista_de_feira."""
    itens = []
    for refeicao in plano["refeicoes"]:
        for receita in refeicao["fixas"]:
            itens.append({"receita": receita["id"], "vezes_por_semana": 7})
        for prato in refeicao["pratos"]:
            for opcao in prato["opcoes"]:
                itens.append({"receita": opcao["receita"]["id"], "vezes_por_semana": opcao["vezes_por_semana"]})
    return itens


def porcoes_da_casa(perfil, plano):
    """Porções por refeição: a da pessoa, ajustada, mais uma para cada outra pessoa da casa."""
    return plano["fator_porcao"] + max(perfil.get("pessoas_na_casa", 1) - 1, 0)
