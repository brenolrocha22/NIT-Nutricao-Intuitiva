"""Monta o CONTEXTO que o redator recebe: só o que interessa à mensagem, já calculado e filtrado.

Cada intenção do intérprete tem uma função aqui. Os números saem formatados do
jeito que o redator deve repeti-los, para a validação poder conferir.
"""
from datetime import date

from . import busca, dados, despensa, feira, gastos, memoria, nutricao, plano, restricoes, triagem

NOMES_RESTRICAO = {k: v["nome"] for k, v in dados.restricoes()["restricoes"].items()}
CONDICOES = dados.restricoes()["encaminhamento_nutricionista"]["condicoes"]
OBJETIVOS = dados.carregar_json("usuarios.json")["opcoes"]["objetivo"]


def num(valor, casas=1):
    """Número no formato brasileiro, sem zeros sobrando: 1.100 · 10,8 · 192 · 1,5."""
    if valor is None:
        return "sem dado"
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto.rstrip("0").rstrip(",") if casas else texto


def reais(valor):
    """Dinheiro sempre com centavos: R$ 12,30."""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(d):
    return d.strftime("%d/%m/%Y")


def linha_nutrientes(n):
    """'192 kcal · 3,8 g de proteína · 42,1 g de carboidrato · 0,3 g de gordura'"""
    return (f"{num(n['energia_kcal'], 0)} kcal · {num(n['proteina_g'])} g de proteína · "
            f"{num(n['carboidrato_g'])} g de carboidrato · {num(n['lipideos_g'])} g de gordura")


# --- Partes comuns -----------------------------------------------------------

def cabecalho(perfil, estado, hoje, interp):
    restr = [NOMES_RESTRICAO.get(r, r) for r in perfil.get("restricoes", [])]
    linhas = [
        f"PESSOA: {perfil['nome']} · objetivo: {OBJETIVOS.get(perfil['objetivo'], perfil['objetivo'])} · "
        f"dedicação: {perfil['nivel_dedicacao']}",
        f"HOJE: {data_br(hoje)}",
        f"RESTRIÇÕES: {', '.join(restr) if restr else 'nenhuma'}"
        + (" (tudo abaixo já foi filtrado)" if restr else ""),
    ]
    if perfil.get("nao_gosta"):
        linhas.append(f"NÃO GOSTA DE: {', '.join(perfil['nao_gosta'])}")
    linhas.append(resumo_do_dia(perfil, estado, hoje))

    condicao = interp.get("menciona_condicao_clinica")
    if condicao:
        nome = CONDICOES.get(condicao, condicao)
        linhas.append(
            f"ALERTA_CLINICO: a pessoa mencionou {nome}. Não dê metas nem plano alimentar: oriente "
            "procurar um nutricionista. Receitas, feira e água continuam disponíveis."
        )
    return "\n".join(linhas)


def resumo_do_dia(perfil, estado, hoje):
    registro = memoria.dia(estado, hoje)
    meta_copos = nutricao.metas_do_dia(perfil)["agua_copos"]
    kcal = sum(item.get("energia_kcal") or 0 for item in registro["consumo"])
    feitas = registro["refeicoes"]
    partes = [
        f"refeições marcadas: {', '.join(feitas) if feitas else 'nenhuma'} ({len(feitas)} de {len(plano.ESTRUTURA)})",
        f"água: {registro['copos']} de {meta_copos} copos",
        f"registrado no contador: {num(kcal, 0)} kcal",
    ]
    if triagem.pode_montar_plano(perfil):
        partes[-1] += f" (meta do dia: {num(nutricao.metas_do_dia(perfil)['kcal'], 0)} kcal)"
    return "DIA DE HOJE: " + " · ".join(partes)


def alimentos_bloqueados(interp, perfil):
    """Alimentos citados na mensagem que a pessoa não pode comer."""
    bloqueados = []
    for alimento in interp.get("alimentos", []):
        proibidas = restricoes.palavras_proibidas_no_texto(alimento["descricao"], perfil)
        if proibidas:
            bloqueados.append(alimento["descricao"])
    return bloqueados


def descrever_receita(receita, completa=True):
    n = nutricao.nutrientes_receita(receita)["por_porcao"]
    linhas = [f"- {receita['nome']} · {receita['tempo_min']} min · rende {receita['porcoes']} porções · "
              f"por porção, pela TACO: {num(n['energia_kcal'], 0)} kcal e {num(n['proteina_g'])} g de proteína"]
    if receita.get("retirados"):
        linhas.append(f"  Adaptada: sem {', '.join(receita['retirados'])} (por causa das restrições)")
    if completa:
        ingredientes = ", ".join(f"{i['nome']} ({num(i['gramas'], 0)} g)" for i in receita["ingredientes"])
        extras = receita.get("sem_calculo") or []
        linhas.append(f"  Ingredientes: {ingredientes}" + (f"; {', '.join(extras)} a gosto" if extras else ""))
        linhas.append("  Preparo: " + " ".join(f"{n}) {p}" for n, p in enumerate(receita["preparo"], 1)))
        if receita.get("veja_tambem"):
            linhas.append(f"  Receita parecida da Ana Maria Braga: {receita['veja_tambem']}")
    return "\n".join(linhas)


# --- Uma função por intenção ---------------------------------------------------

def ctx_receita(perfil, estado, hoje, interp):
    permitidas, _ = restricoes.filtrar_receitas(perfil)
    por_id = {r["id"]: r for r in permitidas}
    linhas = []

    bloqueados = alimentos_bloqueados(interp, perfil)
    if bloqueados:
        linhas.append(f"PEDIDO_BLOQUEADO: {', '.join(bloqueados)} fere as restrições da pessoa. "
                      "Explique o motivo em uma frase e ofereça uma troca da lista abaixo.")

    citados = [a["descricao"] for a in interp.get("alimentos", []) if a["descricao"] not in bloqueados]
    if citados:
        def acertos(r):
            nomes = " ".join(i["nome"] for i in r["ingredientes"])
            return sum(1 for c in citados if any(busca.mesma_palavra(p, q) for p in busca.palavras(c) for q in busca.palavras(nomes)))
        ordem = sorted(permitidas, key=lambda r: (-acertos(r), r["tempo_min"]))
        escolhidas = [r for r in ordem if acertos(r)][:3] or ordem[:3]
        linhas.append(f"RECEITAS COM {', '.join(citados).upper()} (já filtradas):")
        faltas = {}
    else:
        com_despensa = despensa.receitas_com_a_despensa(permitidas, estado["despensa"])
        escolhidas = [por_id[r["id"]] for r in com_despensa[:3]]
        faltas = {r["id"]: r for r in com_despensa}
        linhas.append("RECEITAS QUE USAM A DESPENSA (já filtradas):")
        parados = [i["nome"] for i in estado["despensa"]["itens"] if i["restante_g"] == i["comprado_g"] > 0]
        if parados:
            linhas.append(f"Itens comprados e ainda não usados (priorize): {', '.join(parados)}")

    for receita in escolhidas:
        linhas.append(descrever_receita(receita))
        info = faltas.get(receita["id"])
        if info and info["faltam"]:
            linhas.append(f"  Falta na despensa: {', '.join(info['faltam'])} (pergunte se a pessoa tem)")
    linhas.append("Ofereça uma receita por vez. Se a pessoa aceitar, passe ingredientes e preparo como estão acima.")
    return "\n".join(linhas), {}


def ctx_plano(perfil, estado, hoje, interp):
    if interp.get("menciona_condicao_clinica") or not triagem.pode_montar_plano(perfil):
        motivos = triagem.motivos_para_nutricionista(perfil)
        if interp.get("menciona_condicao_clinica"):
            motivos.append(CONDICOES.get(interp["menciona_condicao_clinica"], interp["menciona_condicao_clinica"]))
        return (f"PLANO_BLOQUEADO: {', '.join(motivos)}. O plano precisa ser feito por um nutricionista. "
                "Ofereça receitas, lista de feira e controle da água."), {}

    p = plano.montar(perfil)
    m = p["metas"]
    linhas = [
        "PLANO (calculado pelo código; o cardápio da semana completo está na aba Plano):",
        f"- Meta do dia: {num(m['kcal'], 0)} kcal · proteína {num(m['proteina_g'], 0)} g · "
        f"carboidrato {num(m['carboidrato_g'], 0)} g · gordura {num(m['gordura_g'], 0)} g · "
        f"fibra {num(m['fibra_g'], 0)} g · água {m['agua_copos']} copos",
        f"- Como foi calculado: equação de Mifflin-St Jeor ({num(m['tmb_kcal'], 0)} kcal em repouso), "
        f"vezes o nível de atividade ({num(m['gasto_total_kcal'], 0)} kcal por dia), ajustado ao objetivo.",
    ]
    if m["piso_aplicado"]:
        linhas.append("- A meta foi elevada ao mínimo seguro de calorias.")
    linhas.append(f"- Porção sugerida: {num(p['fator_porcao'], 2)} porção de cada receita")
    linhas.append("DIA DE EXEMPLO:")
    for refeicao, receitas in p["dia_de_exemplo"]:
        linhas.append(f"- {refeicao}: {', '.join(r['nome'] for r in receitas)}")
    return "\n".join(linhas), {}


def ctx_registrar_consumo(perfil, estado, hoje, interp):
    linhas = ["REGISTRO DE CONSUMO (ainda NÃO foi salvo: a pessoa confere e confirma na tela, logo abaixo da resposta):"]
    propostas = []
    for alimento in interp.get("alimentos", []):
        descricao, gramas = alimento["descricao"], alimento.get("gramas")
        rotulo = achar_rotulo(estado, descricao)
        candidatos = busca.buscar(descricao)
        propostas.append({
            "descricao": descricao,
            "gramas": gramas,
            "rotulo": rotulo,
            "candidatos": [(a["numero"], a["descricao"]) for a in candidatos],
        })
        if rotulo:
            if gramas:
                n = nutrientes_rotulo(estado["rotulos"][rotulo], gramas)
                linhas.append(f"- {num(gramas, 0)} g de {descricao} → {rotulo} (pela embalagem): {linha_nutrientes(n)}")
            else:
                linhas.append(f"- {descricao}: QUANTIDADE_FALTANDO. Pergunte quantos gramas (ou uma medida caseira).")
        elif not candidatos:
            linhas.append(f"- {descricao}: NÃO_ENCONTRADO na TACO. Ofereça registrar pela foto da tabela nutricional da embalagem.")
        elif gramas is None:
            linhas.append(f"- {descricao}: QUANTIDADE_FALTANDO. Pergunte quantos gramas (ou uma medida caseira).")
        else:
            n = nutricao.nutrientes(candidatos[0]["numero"], gramas)
            if n["energia_kcal"] is None:
                linhas.append(f"- {descricao} → {n['alimento']}: SEM_DADOS na TACO (análise sendo reavaliada). "
                              "Não chute: peça a foto da tabela nutricional da embalagem.")
            else:
                linhas.append(f"- {num(gramas, 0)} g de {descricao} → {n['alimento']} (pela TACO): {linha_nutrientes(n)}")
    if not propostas:
        linhas.append("- Nenhum alimento identificado. Pergunte o que a pessoa comeu e quanto.")
    return "\n".join(linhas), {"consumo": propostas}


def ctx_registrar_agua(perfil, estado, hoje, interp):
    ml = interp.get("agua_ml")
    meta = nutricao.metas_do_dia(perfil)["agua_copos"]
    antes = memoria.dia(estado, hoje)["copos"]
    if not ml:
        return f"ÁGUA: quantidade não informada. Pergunte quantos copos. Hoje: {antes} de {meta} copos.", {}
    copos = max(1, round(ml / nutricao.COPO_ML))
    return (f"ÁGUA (ainda NÃO foi salvo: a pessoa confirma na tela): {num(ml, 0)} ml = {copos} copos de "
            f"{nutricao.COPO_ML} ml. Com isso, hoje fica em {antes + copos} de {meta} copos."), {"copos": copos}


def ctx_feira(perfil, estado, hoje, interp):
    r = despensa.resumo(estado["despensa"], hoje, perfil["periodo_feira_dias"])
    p = plano.para_feira(perfil)
    lista = feira.lista_de_feira(plano.itens_para_feira(p), p["receitas"], perfil["periodo_feira_dias"],
                                 plano.porcoes_da_casa(perfil, p), estado["despensa"])
    linhas = [
        f"PRÓXIMA FEIRA: {data_br(r['proxima_feira'])} (motivo: {r['motivo']})",
        f"Já acabou: {', '.join(r['acabaram']) or 'nada'}",
        "Acabando em até 3 dias: " + (", ".join(i["nome"] for i in r["itens"] if i["situacao"] == "acabando") or "nada"),
        f"LISTA DE FEIRA PARA {perfil['periodo_feira_dias']} DIAS (já descontado o que tem em casa; completa na aba Feira):",
    ]
    linhas += [f"- {i['nome']}: {num(i['gramas'], 0)} g" for i in lista[:12]]
    if len(lista) > 12:
        linhas.append(f"- e mais {len(lista) - 12} itens")
    linhas.append("Dica do Guia Alimentar: prefira alimentos da época e feiras, que costumam sair mais baratos.")
    return "\n".join(linhas), {}


def ctx_despensa(perfil, estado, hoje, interp):
    r = despensa.resumo(estado["despensa"], hoje, perfil["periodo_feira_dias"])
    linhas = [f"DESPENSA (última feira em {data_br(date.fromisoformat(estado['despensa']['data_ultima_feira']))}; "
              "para registrar compras ou corrigir quantidades, use a aba Feira e despensa):"]
    for i in r["itens"]:
        if i["situacao"] == "acabou":
            linhas.append(f"- {i['nome']}: acabou")
        elif i["situacao"] == "parado":
            linhas.append(f"- {i['nome']}: {num(i['restante_g'], 0)} g · ainda não foi usado")
        else:
            linhas.append(f"- {i['nome']}: {num(i['restante_g'], 0)} g · acaba por volta de {i['acaba_em'].strftime('%d/%m')}")
    return "\n".join(linhas), {}


def ctx_gastos(perfil, estado, hoje, interp):
    r = gastos.resumo(estado["cupons"])
    if not r:
        return ("SEM_CUPONS: o NIT não conhece preços de mercado e não inventa. Só usa os preços dos cupons "
                "fiscais que a pessoa enviar pela aba Gastos."), {}
    linhas = [
        "GASTOS (só com os cupons fiscais da pessoa):",
        f"- {r['feiras']} cupons, de {r['primeira']} a {r['ultima']} · total {reais(r['total'])} · "
        f"média por feira {reais(r['media_por_feira'])}",
    ]
    if r["por_mes"]:
        linhas.append(f"- Gasto estimado com comida: {reais(r['por_dia'])} por dia, {reais(r['por_mes'])} por mês")
    else:
        linhas.append("- Com um cupom só ainda não dá para calcular o gasto por mês: faltam mais feiras.")
    citados = [a["descricao"] for a in interp.get("alimentos", [])]
    for descricao, preco in gastos.precos_pagos(estado["cupons"]).items():
        if any(busca.mesma_palavra(p, q) for c in citados for p in busca.palavras(c) for q in busca.palavras(descricao)):
            linhas.append(f"- Preço pago: {descricao} · {reais(preco['valor'])} "
                          f"({preco['quantidade']} {preco['unidade']}) em {preco['data']}")
    if citados:
        linhas.append("Se o alimento perguntado não estiver acima, diga que não sabe o preço e não invente.")
    return "\n".join(linhas), {}


def ctx_onde_comprar(perfil, estado, hoje, interp):
    fontes = dados.carregar_json("onde_comprar.json")
    linhas = ["ONDE COMPRAR (só estas fontes, com o link oficial; NÃO invente endereços):"]
    linhas += [f"- {f['nome']}: {f['o_que_e']} {f['como_usar']} {f['url']}" for f in fontes["fontes"]]
    linhas.append("DICAS: " + " ".join(fontes["dicas_gerais"]))
    linhas.append("LOCALIZAÇÃO: o protótipo não acessa a localização. Se a pessoa disser a cidade, "
                  "indique buscar a cidade nos links acima.")
    return "\n".join(linhas), {}


def ctx_duvida(perfil, estado, hoje, interp):
    guia = dados.carregar_json("guia_alimentar.json")
    linhas = [
        f"GUIA ALIMENTAR PARA A POPULAÇÃO BRASILEIRA (Ministério da Saúde, {guia['fonte']['ano']}):",
        f"- Regra de ouro: {guia['regra_de_ouro']}",
    ]
    linhas += [f"- Passo {p['n']}: {p['titulo']}" for p in guia["dez_passos"]]
    linhas += [f"- {p}" for p in guia["principios_do_nit"]]
    for alimento in interp.get("alimentos", []):
        candidatos = busca.buscar(alimento["descricao"], 1)
        if candidatos:
            n = nutricao.nutrientes(candidatos[0]["numero"], 100)
            if n["energia_kcal"] is not None:
                linhas.append(f"- {n['alimento']}, em 100 g (pela TACO): {linha_nutrientes(n)} · "
                              f"{num(n['fibra_g'])} g de fibra")
    return "\n".join(linhas), {}


def ctx_conversa(perfil, estado, hoje, interp):
    return "Pergunte como está o dia, se ainda não souber. Use o resumo do dia acima.", {}


def ctx_fora_do_escopo(perfil, estado, hoje, interp):
    return "FORA_DO_ESCOPO: diga com leveza que seu assunto é alimentação e puxe a conversa para a comida.", {}


def ctx_risco(perfil, estado, hoje, interp):
    return ("MODO_ACOLHIMENTO: a pessoa pode estar sofrendo. Sem sarcasmo, sem cobrança, sem números. "
            "Não ajude com jejum, vômito, laxante, remédio para emagrecer nem com 'compensar' o que comeu. "
            "Acolha, diga que um dia não define nada e sugira conversar com um profissional de saúde. "
            "Se houver sofrimento intenso, indique o CVV: 188, de graça, 24 horas, ou cvv.org.br."), {}


MONTADORES = {
    "receita": ctx_receita,
    "plano": ctx_plano,
    "registrar_consumo": ctx_registrar_consumo,
    "registrar_agua": ctx_registrar_agua,
    "feira": ctx_feira,
    "despensa": ctx_despensa,
    "gastos": ctx_gastos,
    "onde_comprar": ctx_onde_comprar,
    "duvida": ctx_duvida,
    "conversa": ctx_conversa,
    "fora_do_escopo": ctx_fora_do_escopo,
    "risco": ctx_risco,
}


def montar(interp, perfil, estado, hoje):
    """Devolve o texto do CONTEXTO e as propostas de registro para a tela confirmar."""
    especifico, propostas = MONTADORES[interp["intencao"]](perfil, estado, hoje, interp)
    contexto = cabecalho(perfil, estado, hoje, interp) + "\n\n" + especifico
    contexto += "\n\nREGRAS: use só os dados acima. Não cite valores que não estejam aqui."
    return contexto, propostas


# --- Tabelas nutricionais lidas das embalagens ---------------------------------

def achar_rotulo(estado, descricao):
    """Nome do rótulo salvo que corresponde à descrição, se houver."""
    pedidas = busca.palavras(descricao)
    for nome in estado.get("rotulos", {}):
        existentes = busca.palavras(nome)
        if pedidas and all(any(busca.mesma_palavra(p, e) for e in existentes) for p in pedidas):
            return nome
    return None


def nutrientes_rotulo(rotulo, gramas):
    """Nutrientes de uma quantidade, a partir dos valores por 100 g da embalagem."""
    resultado = {"alimento": rotulo.get("nome"), "gramas": gramas, "fonte": "embalagem"}
    for chave in ("energia_kcal", "proteina_g", "carboidrato_g", "lipideos_g", "fibra_g", "sodio_mg"):
        valor = rotulo.get(chave)
        resultado[chave] = None if valor is None else round(valor * gramas / 100, 1)
    return resultado
