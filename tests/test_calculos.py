"""Cálculos sem IA: nutrientes, metas, triagem, plano, feira, despensa, gastos e pontos."""
from datetime import date

from conftest import HOJE
from nit import busca, dados, despensa, feira, gastos, nutricao, plano, pontos, triagem


def receita(id_receita):
    return next(r for r in dados.receitas() if r["id"] == id_receita)


# --- Nutrição ------------------------------------------------------------------

def test_arroz_150g_pela_taco():
    n = nutricao.nutrientes(3, 150)  # Arroz, tipo 1, cozido
    assert n["energia_kcal"] == 192
    assert n["proteina_g"] == 3.8


def test_omelete_por_porcao():
    por_porcao = nutricao.nutrientes_receita(receita("omelete-de-legumes"))["por_porcao"]
    assert round(por_porcao["energia_kcal"]) == 146
    assert por_porcao["proteina_g"] == 10.8


def test_leite_integral_sem_dados_nao_vira_zero():
    n = nutricao.nutrientes(458, 200)  # Leite, de vaca, integral: marcado com * na TACO
    assert n["energia_kcal"] is None
    assert "energia_kcal" in n["sem_dados"]


def test_mifflin_st_jeor_do_alex(usuarios):
    # 10 x 92 + 6,25 x 178 - 5 x 34 + 5 = 1867,5
    assert nutricao.taxa_metabolica_basal(usuarios["alex"]) == 1867.5


def test_meta_nunca_abaixo_do_piso():
    perfil = {"peso_kg": 45, "altura_cm": 150, "idade": 60, "sexo_biologico": "feminino",
              "nivel_atividade": "sedentario", "objetivo": "emagrecer", "nivel_dedicacao": "insano"}
    assert nutricao.metas_do_dia(perfil)["kcal"] >= nutricao.PISO_KCAL["feminino"]


def test_modo_insano_nao_corta_mais_que_o_intenso():
    ajustes = nutricao.AJUSTE_OBJETIVO["emagrecer"]
    assert ajustes["insano"] >= ajustes["intenso"]


# --- Triagem e plano -------------------------------------------------------------

def test_triagem_bloqueia_casos_clinicos(usuarios):
    assert triagem.motivos_para_nutricionista(usuarios["jorge"]) == ["diabetes"]
    assert triagem.motivos_para_nutricionista(usuarios["aline"]) == ["gestação"]
    assert triagem.pode_montar_plano(usuarios["alex"])


def test_plano_bloqueado_para_gestante(usuarios):
    assert plano.montar(usuarios["aline"])["bloqueado"]


def test_feira_continua_disponivel_para_quem_foi_encaminhado(usuarios):
    p = plano.para_feira(usuarios["jorge"])
    assert plano.itens_para_feira(p)


def test_plano_vegano_so_tem_receitas_permitidas(usuarios):
    p = plano.montar(usuarios["juliana"])
    ids = {i["receita"] for i in plano.itens_para_feira(p)}
    for bloqueada in ("cuscuz-com-ovo", "omelete-de-legumes", "galinhada", "moqueca-de-sardinha"):
        assert bloqueada not in ids


def test_plano_tem_prato_principal_no_almoco(usuarios):
    p = plano.montar(usuarios["alex"])
    almoco = next(r for r in p["refeicoes"] if r["refeicao"] == "almoço")
    assert any(prato["papel"] == "prato principal" for prato in almoco["pratos"])


def test_porcao_ajustada_fica_perto_da_meta(usuarios):
    for id_usuario in ("alex", "matheus", "ricardo", "juliana", "fernanda"):
        p = plano.montar(usuarios[id_usuario])
        assert 0.75 <= p["fator_porcao"] <= 2.5
        assert abs(p["kcal_dia_ajustado"] - p["metas"]["kcal"]) / p["metas"]["kcal"] < 0.15


def test_cada_dia_da_semana_tem_uma_opcao():
    assert plano.distribuir(3) == [3, 2, 2]
    assert sum(plano.distribuir(2)) == 7


# --- Despensa e feira -------------------------------------------------------------

def test_previsao_da_proxima_feira_do_alex():
    r = despensa.resumo(dados.despensas()["despensas"]["alex"], HOJE, 15)
    assert r["acabaram"] == ["banana-nanica"]
    assert r["parados"] == ["abobrinha"]
    assert r["proxima_feira"] == date(2026, 11, 12)  # o frango acaba primeiro


def test_registrar_feira_soma_ao_que_sobrou():
    inicial = {"data_ultima_feira": "2026-11-01", "itens": [
        {"taco": 4, "nome": "arroz", "comprado_g": 2000, "restante_g": 500},
        {"taco": 179, "nome": "banana", "comprado_g": 1000, "restante_g": 0},
    ]}
    nova = despensa.registrar_feira(inicial, [{"taco": 4, "nome": "arroz", "gramas": 1000},
                                              {"taco": 157, "nome": "tomate", "gramas": 500}], HOJE)
    itens = {i["taco"]: i for i in nova["itens"]}
    assert itens[4]["restante_g"] == 1500 and itens[4]["comprado_g"] == 1500
    assert itens[157]["restante_g"] == 500
    assert 179 not in itens  # o que acabou sai da despensa
    assert nova["data_ultima_feira"] == "2026-11-10"


def test_lista_de_feira_desconta_a_despensa():
    cardapio = [{"receita": "arroz-soltinho", "vezes_por_semana": 7}]
    sem_despensa = feira.lista_de_feira(cardapio, dados.receitas(), 28, 1)
    com_despensa = feira.lista_de_feira(cardapio, dados.receitas(), 28, 1,
                                        {"itens": [{"taco": 4, "restante_g": 1000}]})
    arroz = lambda lista: next(i["gramas"] for i in lista if i["taco"] == 4)  # noqa: E731
    assert arroz(sem_despensa) == 1500  # 28 porções x 50 g = 1.400 g, arredondado para cima
    assert arroz(com_despensa) == 400


# --- Busca na TACO ----------------------------------------------------------------

def test_busca_acha_o_alimento_principal():
    assert busca.buscar("arroz branco cozido")[0]["descricao"] == "Arroz, tipo 1, cozido"
    assert busca.buscar("ovo")[0]["descricao"].startswith("Ovo, de galinha, inteiro")
    assert busca.buscar("carne moída")[0]["descricao"].startswith("Carne, bovina, acém, moído")


def test_busca_nao_confunde_maca_com_macarrao():
    assert all("Macarrão" not in a["descricao"] for a in busca.buscar("maçã"))


def test_busca_prefere_o_alimento_ao_processado():
    assert busca.buscar("leite")[0]["descricao"] == "Leite, de vaca, integral"
    assert busca.buscar("leite condensado")[0]["descricao"] == "Leite, condensado"


# --- Gastos e pontos ----------------------------------------------------------------

def test_gastos_so_com_cupons():
    assert gastos.resumo([]) is None
    cupons = [
        {"data": "2026-10-01", "mercado": "A", "itens": [{"descricao": "ARROZ", "valor": 30.0}]},
        {"data": "2026-10-31", "mercado": "B", "itens": [{"descricao": "ARROZ", "valor": 33.0},
                                                         {"descricao": "ILEGIVEL", "valor": None}]},
    ]
    r = gastos.resumo(cupons)
    assert r["media_por_feira"] == 31.5
    assert r["por_dia"] == 1.0  # só o primeiro cupom (R$ 30) dividido pelos 30 dias até o segundo
    assert gastos.precos_pagos(cupons)["ARROZ"]["valor"] == 33.0


def test_pontos_do_dia_completo():
    r = pontos.pontos_do_dia({"refeicoes": ["a", "b", "c", "d"], "copos": 8}, 4, 8)
    assert r["dia_completo"]
    assert r["pontos"] == 4 * 10 + 20 + 15


def test_conquistas_pela_melhor_sequencia():
    dias = [True] * 7 + [False] + [True] * 2
    assert pontos.sequencia_atual(dias) == 2
    assert [c["id"] for c in pontos.conquistas_obtidas(dias)] == ["primeiro_dia", "semana"]
