"""Pontos e conquistas por cumprir as tarefas do dia."""

PONTOS = {
    "refeicao": 10,        # cada refeição marcada no checklist
    "meta_agua": 20,       # bebeu a meta de água do dia
    "dia_completo": 15,    # todas as refeições previstas e a água
    "registro_consumo": 5, # cada alimento registrado no contador
}

CONQUISTAS = [
    {"id": "primeiro_dia", "nome": "Primeiro passo", "regra": "1 dia completo", "dias": 1},
    {"id": "semana", "nome": "Uma semana firme", "regra": "7 dias completos seguidos", "dias": 7},
    {"id": "quinzena", "nome": "Quinzena de respeito", "regra": "15 dias completos seguidos", "dias": 15},
    {"id": "mes", "nome": "Máquina que não falha", "regra": "30 dias completos seguidos", "dias": 30},
]


def pontos_do_dia(registro, refeicoes_previstas, meta_copos):
    """Pontos de um dia. `registro` tem 'refeicoes' (lista), 'copos' e 'alimentos_registrados'."""
    feitas = len(registro.get("refeicoes", []))
    bateu_agua = registro.get("copos", 0) >= meta_copos
    completo = feitas >= refeicoes_previstas and bateu_agua
    pontos = (
        feitas * PONTOS["refeicao"]
        + (PONTOS["meta_agua"] if bateu_agua else 0)
        + (PONTOS["dia_completo"] if completo else 0)
        + registro.get("alimentos_registrados", 0) * PONTOS["registro_consumo"]
    )
    return {"pontos": pontos, "dia_completo": completo, "bateu_agua": bateu_agua}


def sequencia_atual(dias_completos):
    """Quantos dias completos seguidos, contando de trás para frente (lista de True/False)."""
    sequencia = 0
    for completo in reversed(dias_completos):
        if not completo:
            break
        sequencia += 1
    return sequencia


def conquistas_obtidas(dias_completos):
    melhor = atual = 0
    for completo in dias_completos:
        atual = atual + 1 if completo else 0
        melhor = max(melhor, atual)
    return [c for c in CONQUISTAS if melhor >= c["dias"]]
