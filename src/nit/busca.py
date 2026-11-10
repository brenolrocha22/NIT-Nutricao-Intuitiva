"""Busca de alimentos na TACO a partir da descrição livre ("arroz branco cozido").

A busca sugere candidatos; quem decide é a pessoa, na tela de confirmação.
"""
import re

from . import dados
from .restricoes import normalizar

PALAVRAS_VAZIAS = {"de", "do", "da", "dos", "das", "com", "e", "em", "a", "o", "um", "uma", "tipo"}
ESTADOS_PRONTOS = ("cozid", "assad", "grelhad", "refogad")
# Na dúvida, "ovo" é o ovo inteiro e "leite" é o de vaca
PREFERIDAS = {"inteir", "vac"}  # já no radical usado por palavras()
# Versões processadas só aparecem primeiro se a pessoa pedir por elas
PROCESSADAS = {"achocolat", "condensad", "po", "extrat", "pure", "instantane", "barr", "conserv"}


def mesma_palavra(pedida, existente):
    """'ovo' casa com 'ovo' e 'ovos', 'cozid' com 'cozido', mas 'maca' não casa com 'macarrao'."""
    return existente.startswith(pedida) and len(existente) - len(pedida) <= 2


def palavras(texto):
    """Radical aproximado das palavras relevantes: 'ovos' -> 'ov', 'moída' e 'moído' -> 'moid'."""
    resultado = []
    for p in re.findall(r"[a-z0-9]+", normalizar(texto)):
        if p in PALAVRAS_VAZIAS or len(p) < 2:
            continue
        if len(p) > 3 and p.endswith("s"):
            p = p[:-1]
        if len(p) > 3 and p[-1] in "oa":
            p = p[:-1]
        resultado.append(p)
    return resultado


def pontuar(consulta, descricao):
    pedidas = palavras(consulta)
    existentes = palavras(descricao)
    if not pedidas or not existentes:
        return 0
    achadas = sum(1 for p in pedidas if any(mesma_palavra(p, e) for e in existentes))
    if achadas == 0:
        return 0
    pontos = achadas + 0.3 * len(PREFERIDAS & set(existentes))
    processadas = {
        e for e in existentes
        if any(e == p or (len(p) > 3 and e.startswith(p)) for p in PROCESSADAS)
        and not any(mesma_palavra(q, e) for q in pedidas)
    }
    pontos -= 0.6 * len(processadas)
    if mesma_palavra(pedidas[0], existentes[0]):
        pontos += 1  # a TACO começa pelo alimento principal: "Arroz, tipo 1, cozido"
    texto = normalizar(descricao)
    if "cru" not in pedidas and any(e in texto for e in ESTADOS_PRONTOS):
        pontos += 0.5  # quem conta o que comeu, em geral comeu pronto
    return pontos - 0.02 * len(existentes)  # desempate: descrição mais simples


def buscar(consulta, limite=5):
    """Candidatos da TACO, do mais provável ao menos provável."""
    pontuados = [(pontuar(consulta, a["descricao"]), a) for a in dados.taco().values()]
    pontuados = [(p, a) for p, a in pontuados if p > 0]
    pontuados.sort(key=lambda par: -par[0])
    return [a for _, a in pontuados[:limite]]
