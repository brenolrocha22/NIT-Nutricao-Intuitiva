"""Memória do NIT: o que cada pessoa registrou, salvo em memoria/<id>.json.

A pasta memoria/ fica fora do Git. Na primeira vez, a despensa começa com os
dados fictícios de data/despensa.json (quando houver) e o resto começa vazio.
"""
import copy
import json
from datetime import date
from pathlib import Path

from . import dados

PASTA = Path(__file__).resolve().parents[2] / "memoria"
LIMITE_CONVERSA = 40


def caminho(id_usuario):
    return PASTA / f"{id_usuario}.json"


def estado_inicial(id_usuario, hoje):
    semente = dados.despensas()["despensas"].get(id_usuario)
    despensa = copy.deepcopy(semente) if semente else {"data_ultima_feira": hoje.isoformat(), "itens": []}
    return {
        "perfil": None,    # preenchido só para quem fez o questionário no app
        "despensa": despensa,
        "dias": {},        # "AAAA-MM-DD": {"refeicoes": [...], "copos": n, "consumo": [...]}
        "cupons": [],
        "rotulos": {},     # tabelas nutricionais lidas das embalagens, por nome
        "conversa": [],
    }


def carregar(id_usuario, hoje=None):
    arquivo = caminho(id_usuario)
    if arquivo.exists():
        with open(arquivo, encoding="utf-8") as f:
            return json.load(f)
    return estado_inicial(id_usuario, hoje or date.today())


def salvar(id_usuario, estado):
    PASTA.mkdir(exist_ok=True)
    estado["conversa"] = estado["conversa"][-LIMITE_CONVERSA:]
    with open(caminho(id_usuario), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)


def apagar(id_usuario):
    caminho(id_usuario).unlink(missing_ok=True)


def perfis_criados():
    """Pessoas que fizeram o questionário no app (além das fictícias de data/)."""
    perfis = {}
    if PASTA.exists():
        for arquivo in PASTA.glob("*.json"):
            with open(arquivo, encoding="utf-8") as f:
                perfil = json.load(f).get("perfil")
            if perfil:
                perfis[perfil["id"]] = perfil
    return perfis


def dia(estado, data):
    return estado["dias"].setdefault(data.isoformat(), {"refeicoes": [], "copos": 0, "consumo": []})


def historico_texto(estado, ultimas=6):
    """As últimas mensagens, para o intérprete entender um 'sim' ou 'quero'."""
    linhas = [f"{m['papel']}: {m['texto']}" for m in estado["conversa"][-ultimas:]]
    return "\n".join(linhas)
