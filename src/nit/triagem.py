"""Triagem de segurança: decide, antes de tudo, se o NIT pode montar um plano alimentar."""
from . import dados


def motivos_para_nutricionista(perfil):
    """Lista as condições do perfil que exigem acompanhamento profissional.

    Lista vazia: o NIT pode montar o plano. Com qualquer motivo, o plano é
    bloqueado, mas receitas, feira e despensa continuam disponíveis.
    """
    condicoes = dados.restricoes()["encaminhamento_nutricionista"]["condicoes"]
    motivos = [condicoes[c] for c in perfil.get("condicoes_clinicas", []) if c in condicoes]
    if perfil.get("idade", 18) < 18:
        motivos.append(condicoes["menor_de_18"])
    return motivos


def pode_montar_plano(perfil):
    return not motivos_para_nutricionista(perfil)
