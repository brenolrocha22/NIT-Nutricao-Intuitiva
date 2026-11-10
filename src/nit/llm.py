"""Conexão com o Gemini, um método por papel (intérprete, leitor de imagens, redator).

O resto do NIT recebe um objeto com estes três métodos, e não o SDK. Assim os
testes usam um modelo falso, e trocar de modelo não muda o resto do código.
"""
import json
import os
import re
from pathlib import Path

from . import dados, prompts

# O primeiro disponível é usado. Se ele estiver sobrecarregado (erro 429 ou 5xx),
# o NIT tenta o próximo. GEMINI_MODEL, no .env, entra na frente da lista.
MODELOS = [
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
]
RAIZ = Path(__file__).resolve().parents[2]


def chave_api():
    """Lê a chave do .env (ou das variáveis de ambiente). Nunca fica no código."""
    try:
        from dotenv import load_dotenv
        load_dotenv(RAIZ / ".env")
    except ImportError:
        pass
    return os.getenv("GEMINI_API_KEY", "").strip()


def extrair_json(texto):
    """Lê o JSON da resposta, mesmo se o modelo o embrulhar em ```json ... ```."""
    texto = (texto or "").strip()
    bloco = re.search(r"\{.*\}", texto, re.S)
    if not bloco:
        raise ValueError(f"A resposta não trouxe JSON: {texto[:200]}")
    return json.loads(bloco.group(0))


class Gemini:
    def __init__(self, api_key=None, modelo=None):
        # Importado aqui para que os testes não dependam do SDK
        from google import genai
        from google.genai import types

        self._tipos = types
        # Uma tentativa por modelo e no máximo 60 s de espera: sobrecarregado ou
        # travado, passa logo para o próximo da lista
        opcoes = types.HttpOptions(timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1))
        self.cliente = genai.Client(api_key=api_key or chave_api(), http_options=opcoes)
        preferido = modelo or os.getenv("GEMINI_MODEL", "").strip()
        self.modelos = [preferido] + [m for m in MODELOS if m != preferido] if preferido else list(MODELOS)
        self.modelo = self.modelos[0]  # o último que respondeu

    def _gerar(self, sistema, partes, temperatura, json_saida):
        config = self._tipos.GenerateContentConfig(
            system_instruction=sistema,
            temperature=temperatura,
            response_mime_type="application/json" if json_saida else "text/plain",
        )
        from google.genai import errors

        ultimo_erro = None
        for modelo in self.modelos:
            try:
                resposta = self.cliente.models.generate_content(model=modelo, contents=partes, config=config)
                self.modelo = modelo
                return resposta.text or ""
            except errors.APIError as erro:
                if erro.code != 429 and erro.code < 500:
                    raise
                ultimo_erro = erro
            except (TimeoutError, OSError) as erro:  # tempo esgotado ou falha de rede
                ultimo_erro = erro
            except Exception as erro:  # noqa: BLE001 - o httpx usa exceções próprias para tempo esgotado
                if "timeout" not in type(erro).__name__.lower():
                    raise
                ultimo_erro = erro
        raise ultimo_erro

    def interpretar(self, mensagem, historico=""):
        condicoes = ", ".join(dados.restricoes()["encaminhamento_nutricionista"]["condicoes"])
        sistema = prompts.INTERPRETE.format(condicoes=condicoes)
        entrada = f"Conversa recente:\n{historico or '(nenhuma)'}\n\nMensagem: {mensagem}"
        return extrair_json(self._gerar(sistema, [entrada], 0, True))

    def ler_imagem(self, conteudo, tipo_mime):
        parte = self._tipos.Part.from_bytes(data=conteudo, mime_type=tipo_mime)
        return extrair_json(self._gerar(prompts.LEITOR_IMAGENS, [parte, "Leia esta imagem."], 0, True))

    def redigir(self, sistema, mensagem):
        return self._gerar(sistema, [mensagem], 0.7, False).strip()
