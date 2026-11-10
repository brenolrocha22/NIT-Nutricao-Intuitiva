"""Validação da resposta do redator, antes de ela chegar à pessoa.

Duas verificações: alimento proibido para a pessoa e número de nutriente ou
preço que não veio do contexto (ou seja, que a IA inventou ou recalculou).
"""
import re

from .restricoes import normalizar, palavras_proibidas_no_texto, tem_palavra

# Número com unidade de nutriente ou de dinheiro: "192 kcal", "10,8 g", "R$ 12,30"
NUMERO_COM_UNIDADE = re.compile(
    r"(?:R\$\s*(?P<preco>\d[\d.]*(?:,\d+)?))"
    r"|(?:(?P<valor>\d[\d.]*(?:,\d+)?)\s*(?:kcal|mg|g)\b)",
    re.I,
)
QUALQUER_NUMERO = re.compile(r"\d[\d.]*(?:,\d+)?")


def para_numero(texto):
    """'1.100' -> 1100, '10,8' -> 10.8, '10.8' -> 10.8."""
    texto = texto.strip(".")
    if "," in texto:
        return float(texto.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        return float(texto.replace(".", ""))
    return float(texto)


def numeros_do_texto(texto):
    return {para_numero(n) for n in QUALQUER_NUMERO.findall(texto)}


def numeros_inventados(resposta, *fontes):
    """Números de nutriente ou preço na resposta que não aparecem em nenhuma fonte."""
    conhecidos = set()
    for fonte in fontes:
        conhecidos |= numeros_do_texto(fonte)
    inventados = []
    for achado in NUMERO_COM_UNIDADE.finditer(resposta):
        bruto = achado.group("preco") or achado.group("valor")
        if para_numero(bruto) not in conhecidos:
            inventados.append(achado.group(0).strip())
    return inventados


SINAIS_DE_RECUSA = re.compile(
    r"\b(nao|sem|nada de|evite|evitar|faz mal|proibid\w*|nao pode|restricao|celiac\w*|alergi\w*|intoleran\w*)\b"
)
INTENCOES_QUE_SUGEREM = {"receita", "plano"}


def frases(texto):
    return [f for f in re.split(r"(?<=[.!?\n])\s+", texto) if f.strip()]


def citacao_tolerada(palavra, resposta, mensagem, intencao, pedidas):
    """A resposta pode citar um alimento proibido que a PRÓPRIA pessoa escreveu.

    Ao registrar o que ela comeu ("anotei o copo de leite") ou acolher um relato,
    repetir o alimento é necessário. Quando a intenção é pedir sugestão (receita
    ou plano), cada frase que cita o alimento precisa ser uma recusa: ter um sinal
    de recusa e falar do alimento que a pessoa pediu. Assim "na doença celíaca,
    pão de trigo faz mal" passa, mas "que tal um pão de queijo?" não.

    `pedidas` são as palavras proibidas que aparecem na mensagem da pessoa.
    """
    if intencao not in INTENCOES_QUE_SUGEREM:
        return palavra in pedidas
    citadas = [f for f in frases(normalizar(resposta)) if tem_palavra(palavra, f)]
    return bool(pedidas) and all(
        SINAIS_DE_RECUSA.search(f) and any(tem_palavra(p, f) for p in pedidas) for f in citadas
    )


def problemas(resposta, perfil, contexto, mensagem, intencao="conversa"):
    """Lista de problemas em linguagem clara, para pedir a correção ao redator."""
    encontrados = []
    pedidas = [p for p in palavras_proibidas_no_texto(resposta, perfil) if tem_palavra(p, mensagem)]
    proibidas = [
        p for p in palavras_proibidas_no_texto(resposta, perfil)
        if not citacao_tolerada(p, resposta, mensagem, intencao, pedidas)
    ]
    if proibidas:
        encontrados.append(f"Cita alimentos proibidos para a pessoa: {', '.join(proibidas)}.")
    inventados = numeros_inventados(resposta, contexto, mensagem)
    if inventados:
        encontrados.append(f"Cita números que não estão no contexto: {', '.join(inventados)}. Use só os números do contexto.")
    return encontrados
