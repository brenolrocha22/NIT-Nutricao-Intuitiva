"""Cálculos nutricionais: gasto de energia, metas do dia e nutrientes de alimentos e receitas.

Todas as fórmulas e referências estão citadas aqui, para que qualquer número
mostrado pelo NIT possa ser conferido.
"""
from . import dados

# Fatores de atividade usados com a equação de Mifflin-St Jeor
FATOR_ATIVIDADE = {
    "sedentario": 1.2,
    "leve": 1.375,
    "moderado": 1.55,
    "intenso": 1.725,
    "muito_intenso": 1.9,
}

# Ajuste de calorias por objetivo e nível de dedicação (fração do gasto total).
# O modo Insano não ganha um déficit maior que o Intenso: mais esforço não
# justifica cortar mais comida.
AJUSTE_OBJETIVO = {
    "emagrecer": {"leve": -0.10, "moderado": -0.15, "intenso": -0.20, "insano": -0.20},
    "ganhar_massa": {"leve": 0.05, "moderado": 0.10, "intenso": 0.10, "insano": 0.15},
    "manter": {"leve": 0.0, "moderado": 0.0, "intenso": 0.0, "insano": 0.0},
    "comer_melhor": {"leve": 0.0, "moderado": 0.0, "intenso": 0.0, "insano": 0.0},
}

# Mínimo de calorias que o plano nunca ultrapassa para baixo, por sexo biológico.
# Escolha conservadora, na faixa usada para dietas de baixa caloria sem acompanhamento.
PISO_KCAL = {"feminino": 1200, "masculino": 1500}

GORDURA_FRACAO = 0.25        # 25% das calorias, dentro da faixa de 20% a 35% (IOM)
FIBRA_G_POR_1000_KCAL = 14   # recomendação de fibra do IOM
AGUA_ML_POR_KG = 35          # estimativa usual de 30 a 35 ml por kg de peso
COPO_ML = 250


def taxa_metabolica_basal(perfil):
    """Equação de Mifflin-St Jeor (1990): energia gasta em repouso, em kcal/dia."""
    base = 10 * perfil["peso_kg"] + 6.25 * perfil["altura_cm"] - 5 * perfil["idade"]
    return base + 5 if perfil["sexo_biologico"] == "masculino" else base - 161


def gasto_total(perfil):
    return taxa_metabolica_basal(perfil) * FATOR_ATIVIDADE[perfil["nivel_atividade"]]


def proteina_g_por_kg(perfil):
    """Faixas da Sociedade Internacional de Nutrição Esportiva (1,4 a 2,0 g/kg para
    quem treina) e a recomendação mínima de 0,8 g/kg para adultos (IOM)."""
    objetivo = perfil["objetivo"]
    if objetivo == "ganhar_massa":
        return 1.8
    if objetivo == "emagrecer":
        return 1.6
    if perfil["nivel_atividade"] in ("moderado", "intenso", "muito_intenso"):
        return 1.4
    return 1.0


def metas_do_dia(perfil):
    """Calorias, macronutrientes, fibra e água do dia para a pessoa."""
    tmb = taxa_metabolica_basal(perfil)
    get = gasto_total(perfil)
    ajuste = AJUSTE_OBJETIVO[perfil["objetivo"]][perfil["nivel_dedicacao"]]
    piso = max(tmb, PISO_KCAL[perfil["sexo_biologico"]])
    kcal = max(get * (1 + ajuste), piso)

    proteina = proteina_g_por_kg(perfil) * perfil["peso_kg"]
    gordura = kcal * GORDURA_FRACAO / 9
    carboidrato = max(kcal - proteina * 4 - gordura * 9, 0) / 4
    agua_ml = perfil["peso_kg"] * AGUA_ML_POR_KG
    return {
        "tmb_kcal": round(tmb),
        "gasto_total_kcal": round(get),
        "kcal": round(kcal),
        "piso_aplicado": kcal == piso and get * (1 + ajuste) < piso,
        "proteina_g": round(proteina),
        "gordura_g": round(gordura),
        "carboidrato_g": round(carboidrato),
        "fibra_g": round(kcal / 1000 * FIBRA_G_POR_1000_KCAL),
        "agua_ml": round(agua_ml),
        "agua_copos": round(agua_ml / COPO_ML),
        "micronutrientes": metas_micronutrientes(perfil),
    }


def metas_micronutrientes(perfil):
    """Recomendações diárias (RDA) do Institute of Medicine para adultos.

    Sódio é um limite máximo (OMS: menos de 2.000 mg por dia), não uma meta.
    Para vegetarianos e veganos, a recomendação de ferro é 1,8 vez maior,
    porque o ferro dos vegetais é menos absorvido (IOM).
    """
    mulher = perfil["sexo_biologico"] == "feminino"
    idade = perfil["idade"]
    calcio = 1200 if (mulher and idade > 50) or (not mulher and idade > 70) else 1000
    ferro = 18 if mulher and idade <= 50 else 8
    if {"vegetariano", "vegano"} & set(perfil.get("restricoes", [])):
        ferro = round(ferro * 1.8, 1)
    return {
        "calcio_mg": calcio,
        "ferro_mg": ferro,
        "vitamina_c_mg": 75 if mulher else 90,
        "sodio_mg_maximo": 2000,
    }


def nutrientes(numero_taco, gramas):
    """Nutrientes de uma quantidade de alimento, pela TACO.

    Devolve 'sem_dados' com os nutrientes que a TACO não tem para o alimento,
    para o NIT avisar a pessoa em vez de supor zero.
    """
    alimento = dados.taco()[numero_taco]
    resultado = {"alimento": alimento["descricao"], "gramas": gramas, "fonte": "TACO", "sem_dados": []}
    for coluna in dados.NUTRIENTES:
        valor = alimento[coluna]
        if valor is None:
            resultado[coluna] = None
            resultado["sem_dados"].append(coluna)
        else:
            resultado[coluna] = round(valor * gramas / 100, 1)
    return resultado


def nutrientes_receita(receita):
    """Total da receita e valor por porção, somando os ingredientes pela TACO."""
    total = {coluna: 0.0 for coluna in dados.NUTRIENTES}
    sem_dados = []
    for ingrediente in receita["ingredientes"]:
        item = nutrientes(ingrediente["taco"], ingrediente["gramas"])
        for coluna in dados.NUTRIENTES:
            if item[coluna] is None:
                sem_dados.append(f"{ingrediente['nome']} ({coluna})")
            else:
                total[coluna] += item[coluna]
    porcoes = receita["porcoes"]
    return {
        "porcoes": porcoes,
        "total": {k: round(v, 1) for k, v in total.items()},
        "por_porcao": {k: round(v / porcoes, 1) for k, v in total.items()},
        "sem_dados": sem_dados,
    }
