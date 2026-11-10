import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nit import dados, memoria  # noqa: E402

HOJE = date(2026, 11, 10)  # data de referência de data/despensa.json


@pytest.fixture
def usuarios():
    return dados.usuarios()


@pytest.fixture
def estado():
    """Estado inicial de uma pessoa, sem ler nem gravar nada em memoria/."""
    return lambda id_usuario: memoria.estado_inicial(id_usuario, HOJE)


class ModeloFalso:
    """Substitui o Gemini: devolve respostas fixas e guarda o que recebeu."""

    def __init__(self, interpretacao, respostas):
        self.interpretacao = interpretacao
        self.respostas = list(respostas)
        self.sistemas = []

    def interpretar(self, mensagem, historico=""):
        return self.interpretacao

    def redigir(self, sistema, mensagem):
        self.sistemas.append(sistema)
        return self.respostas.pop(0)

    def ler_imagem(self, conteudo, tipo_mime):
        raise NotImplementedError


@pytest.fixture
def modelo_falso():
    return ModeloFalso
