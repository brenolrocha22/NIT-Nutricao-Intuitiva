"""Barreiras de segurança: restrições, validação da resposta e fluxo do agente (com modelo falso)."""
from conftest import HOJE
from nit import agente, contexto, restricoes, validacao


# --- Restrições -----------------------------------------------------------------

def test_restricao_por_palavra_inteira():
    assert not restricoes.proibido("vegetariano", "Quibebe", "")
    assert restricoes.proibido("alergia_ovo", "Macarrão, trigo, cru, com ovos", "")


def test_excecoes_de_nome_enganoso():
    assert not restricoes.proibido("sem_lactose", "Leite, de coco", "")
    assert not restricoes.proibido("vegano", "Soja, queijo (tofu)", "")


def test_receita_adaptada_sem_o_opcional(usuarios):
    permitidas, _ = restricoes.filtrar_receitas(usuarios["alex"])
    baiao = next(r for r in permitidas if r["id"] == "baiao-de-dois")
    assert baiao["retirados"] == ["queijo minas frescal"]


def test_celiaca_nao_recebe_aveia(usuarios):
    _, bloqueadas = restricoes.filtrar_receitas(usuarios["fernanda"])
    assert {b["id"] for b in bloqueadas} == {"mingau-de-aveia-com-banana", "panqueca-de-banana"}


# --- Validação da resposta --------------------------------------------------------

def test_negacao_nao_conta_como_sugestao(usuarios):
    texto = "Faz um omelete sem queijo. Depois, um pão de queijo."
    assert restricoes.palavras_proibidas_no_texto(texto, usuarios["alex"]) == ["queijo"]


def test_numero_inventado_e_reprovado():
    contexto_ = "Arroz (pela TACO): 192 kcal · 3,8 g de proteína"
    assert validacao.numeros_inventados("São 192 kcal e 3,8 g de proteína.", contexto_) == []
    assert validacao.numeros_inventados("São 200 kcal.", contexto_) == ["200 kcal"]


def test_numero_em_formato_brasileiro():
    assert validacao.para_numero("1.100") == 1100
    assert validacao.para_numero("10,8") == 10.8
    assert validacao.numeros_inventados("Custou R$ 12,30.", "valor R$ 12,30") == []


def test_pode_repetir_o_que_a_pessoa_comeu(usuarios):
    problemas = validacao.problemas("Anotei o copo de leite!", usuarios["alex"], "", "tomei um copo de leite",
                                    "registrar_consumo")
    assert problemas == []


def test_recusa_pode_citar_o_alimento_pedido(usuarios):
    resposta = "Na doença celíaca, pão de trigo faz mal, então essa eu não vou passar. Que tal um cuscuz?"
    mensagem = "me passa uma receita com pão"
    assert validacao.problemas(resposta, usuarios["fernanda"], "", mensagem, "receita") == []


def test_sugestao_do_alimento_pedido_continua_reprovada(usuarios):
    resposta = "Claro! Que tal um sanduíche de pão francês com ovo?"
    mensagem = "me passa uma receita com pão"
    assert validacao.problemas(resposta, usuarios["fernanda"], "", mensagem, "receita")


def test_alimento_que_a_pessoa_nao_citou_continua_reprovado(usuarios):
    assert validacao.problemas("Anotei! Que tal um queijo depois?", usuarios["alex"], "", "comi arroz",
                               "registrar_consumo")


# --- Contexto ------------------------------------------------------------------------

def test_contexto_so_traz_a_propria_pessoa(usuarios, estado):
    interp = agente.limpar_interpretacao({"intencao": "conversa"})
    texto, _ = contexto.montar(interp, usuarios["alex"], estado("alex"), HOJE)
    for outra in ("Juliana", "Fernanda", "Matheus"):
        assert outra not in texto


def test_contexto_de_receita_nao_tem_ingrediente_proibido(usuarios, estado):
    interp = agente.limpar_interpretacao({"intencao": "receita"})
    texto, _ = contexto.montar(interp, usuarios["juliana"], estado("juliana"), HOJE)
    assert restricoes.palavras_proibidas_no_texto(texto, usuarios["juliana"]) == []


def test_pedido_de_alimento_proibido_e_marcado(usuarios, estado):
    interp = agente.limpar_interpretacao({"intencao": "receita", "alimentos": [{"descricao": "pão francês"}]})
    texto, _ = contexto.montar(interp, usuarios["fernanda"], estado("fernanda"), HOJE)
    assert "PEDIDO_BLOQUEADO: pão francês" in texto


def test_mencao_clinica_bloqueia_o_plano(usuarios, estado):
    interp = agente.limpar_interpretacao({"intencao": "plano", "menciona_condicao_clinica": "gestante"})
    texto, _ = contexto.montar(interp, usuarios["alex"], estado("alex"), HOJE)
    assert "PLANO_BLOQUEADO" in texto
    assert "Meta do dia" not in texto


def test_consumo_vira_proposta_sem_salvar(usuarios, estado):
    interp = agente.limpar_interpretacao({"intencao": "registrar_consumo", "alimentos": [
        {"descricao": "arroz branco cozido", "gramas": 150}, {"descricao": "feijão", "gramas": None}]})
    e = estado("alex")
    texto, propostas = contexto.montar(interp, usuarios["alex"], e, HOJE)
    assert "192 kcal" in texto
    assert "QUANTIDADE_FALTANDO" in texto
    assert len(propostas["consumo"]) == 2
    assert e["dias"].get(HOJE.isoformat(), {}).get("consumo", []) == []


def test_leite_sem_dados_pede_a_embalagem(usuarios, estado):
    interp = agente.limpar_interpretacao({"intencao": "registrar_consumo",
                                          "alimentos": [{"descricao": "leite", "gramas": 200}]})
    texto, _ = contexto.montar(interp, usuarios["matheus"], estado("matheus"), HOJE)
    assert "SEM_DADOS" in texto


# --- Fluxo do agente ---------------------------------------------------------------

def test_tom_insano_e_trocado_por_acolhimento(usuarios, estado, modelo_falso):
    llm = modelo_falso({"intencao": "risco"}, ["Ei, calma. Um dia não define nada."])
    r = agente.responder(llm, usuarios["fernanda"], estado("fernanda"), "sou um lixo", HOJE)
    assert "MODO_ACOLHIMENTO" in llm.sistemas[0]
    assert r["texto"] == "Ei, calma. Um dia não define nada."


def test_resposta_reprovada_e_refeita(usuarios, estado, modelo_falso):
    llm = modelo_falso({"intencao": "receita"}, ["Faz uma pizza de queijo!", "Faz um omelete de legumes."])
    r = agente.responder(llm, usuarios["alex"], estado("alex"), "o que eu cozinho?", HOJE)
    assert r["texto"] == "Faz um omelete de legumes."
    assert r["validacao"]["reprovada_na_primeira"]
    assert "reprovada pela validação" in llm.sistemas[1]


def test_reprovada_duas_vezes_vira_resposta_segura(usuarios, estado, modelo_falso):
    llm = modelo_falso({"intencao": "receita"}, ["Pizza de queijo!", "Lasanha com queijo!"])
    r = agente.responder(llm, usuarios["alex"], estado("alex"), "o que eu cozinho?", HOJE)
    assert r["texto"] == agente.RESPOSTA_SEGURA


def test_intencao_desconhecida_vira_conversa():
    assert agente.limpar_interpretacao({"intencao": "hackear"})["intencao"] == "conversa"
    limpa = agente.limpar_interpretacao({"intencao": "registrar_consumo", "alimentos": [
        {"descricao": "arroz", "gramas": "muito"}, {"descricao": ""}]})
    assert limpa["alimentos"] == [{"descricao": "arroz", "gramas": None}]
