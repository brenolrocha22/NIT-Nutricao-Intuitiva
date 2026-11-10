"""Carrega a base de conhecimento de data/ e traduz os valores especiais da TACO."""
import csv
import json
from functools import lru_cache
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parents[2] / "data"

# Colunas numéricas da TACO que o NIT usa nos cálculos
NUTRIENTES = [
    "energia_kcal", "proteina_g", "lipideos_g", "carboidrato_g", "fibra_g",
    "calcio_mg", "ferro_mg", "sodio_mg", "vitamina_c_mg",
]


def valor_taco(texto):
    """Converte um valor da TACO em número.

    - "Tr" (traço: quantidade pequena demais para medir) e "NA" (não se aplica) viram 0.
    - "*" (análise sendo reavaliada) e vazio (análise não feita) viram None:
      o dado não existe, e quem chamar precisa avisar a pessoa em vez de supor zero.
    """
    texto = (texto or "").strip()
    if texto in ("Tr", "NA"):
        return 0.0
    if texto in ("", "*"):
        return None
    return float(texto.replace(",", "."))


@lru_cache(maxsize=None)
def taco():
    """Tabela TACO indexada pelo número do alimento."""
    with open(PASTA_DADOS / "taco.csv", encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    tabela = {}
    for linha in linhas:
        alimento = {"numero": int(linha["numero"]), "descricao": linha["descricao"], "grupo": linha["grupo"]}
        for coluna in NUTRIENTES:
            alimento[coluna] = valor_taco(linha[coluna])
        tabela[alimento["numero"]] = alimento
    return tabela


@lru_cache(maxsize=None)
def carregar_json(nome):
    with open(PASTA_DADOS / nome, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def receitas():
    return carregar_json("receitas.json")["receitas"]


def restricoes():
    return carregar_json("restricoes.json")


def usuarios():
    return {u["id"]: u for u in carregar_json("usuarios.json")["usuarios"]}


def despensas():
    return carregar_json("despensa.json")
