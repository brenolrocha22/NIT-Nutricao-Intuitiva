"""NIT · Nutrição Intuitiva: interface em Streamlit.

Rodar a partir da raiz do projeto:  streamlit run src/app.py
"""
import re
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from nit import (agente, busca, contexto, dados, despensa, feira, gastos, llm, memoria, nutricao, plano,
                 pontos, restricoes, triagem)

st.set_page_config(page_title="NIT · Nutrição Intuitiva", page_icon="🥗", layout="centered")

HOJE = date.today()
OPCOES = dados.carregar_json("usuarios.json")["opcoes"]
NOMES_RESTRICAO = contexto.NOMES_RESTRICAO
CONDICOES = contexto.CONDICOES
num, reais = contexto.num, contexto.reais


# --- Recursos compartilhados ---------------------------------------------------------

@st.cache_resource(show_spinner=False)
def modelo():
    return llm.Gemini() if llm.chave_api() else None


def todos_os_perfis():
    return {**dados.usuarios(), **memoria.perfis_criados()}


def salvar():
    memoria.salvar(uid, estado)


def ler_foto(rotulo, chave):
    """Foto pela câmera (celular) ou por arquivo. Devolve (bytes, tipo) ou None."""
    origem = st.radio(rotulo, ["Enviar arquivo", "Tirar foto"], horizontal=True, key=f"origem_{chave}")
    if origem == "Tirar foto":
        foto = st.camera_input("Câmera", key=f"camera_{chave}", label_visibility="collapsed")
    else:
        foto = st.file_uploader("Arquivo", type=["jpg", "jpeg", "png", "webp"], key=f"arquivo_{chave}",
                                label_visibility="collapsed")
    return (foto.getvalue(), foto.type) if foto else None


def chamar_gemini(chamada):
    """Chama o Gemini e mostra um aviso claro se ele falhar, em vez de quebrar a tela."""
    if modelo() is None:
        st.error("Falta a chave do Gemini. Coloque GEMINI_API_KEY no arquivo .env e reinicie o app.")
        return None
    try:
        return chamada()
    except Exception as erro:  # noqa: BLE001 - qualquer falha da API vira um aviso na tela
        st.error(f"O Gemini não respondeu agora ({type(erro).__name__}). Tente de novo em instantes.")
        return None


# --- Questionário ------------------------------------------------------------------------

def questionario():
    st.header("Vamos nos conhecer")
    st.caption("Umas perguntas rápidas. As respostas ficam só neste computador, na pasta memoria/.")
    with st.form("questionario"):
        nome = st.text_input("Como você quer ser chamado?")
        c1, c2 = st.columns(2)
        idade = c1.number_input("Idade", 10, 100, 30)
        sexo = c2.selectbox("Sexo biológico (para a fórmula de gasto de energia)", ["feminino", "masculino"])
        peso = c1.number_input("Peso (kg)", 30.0, 250.0, 70.0, step=0.5)
        altura = c2.number_input("Altura (cm)", 120, 220, 168)
        objetivo = st.selectbox("Seu objetivo", list(OPCOES["objetivo"]), format_func=OPCOES["objetivo"].get)
        atividade = st.selectbox("Atividade física", list(OPCOES["nivel_atividade"]),
                                 format_func=OPCOES["nivel_atividade"].get)
        dedicacao = st.radio("Quanto da rotina você topa mudar?", list(OPCOES["nivel_dedicacao"]),
                             format_func=lambda k: f"{k.capitalize()}: {OPCOES['nivel_dedicacao'][k]}")
        restr = st.multiselect("Restrições alimentares", list(NOMES_RESTRICAO), format_func=NOMES_RESTRICAO.get)
        nao_gosta = st.text_input("Algum alimento que você não come de jeito nenhum? (separe por vírgula)")
        condicoes = st.multiselect(
            "Alguma destas situações? (se sim, o NIT não monta plano e indica um nutricionista)",
            [c for c in CONDICOES if c != "menor_de_18"], format_func=CONDICOES.get)
        c1, c2, c3 = st.columns(3)
        tempo = c1.number_input("Minutos para cozinhar por dia", 5, 180, 30, step=5)
        periodo = c2.selectbox("Feira a cada", OPCOES["periodo_feira_dias"], format_func=lambda d: f"{d} dias")
        pessoas = c3.number_input("Pessoas na casa", 1, 12, 1)
        if st.form_submit_button("Começar", type="primary"):
            if not nome.strip():
                st.error("Me diz seu nome para começar.")
                return
            novo_id = "u_" + re.sub(r"[^a-z0-9]+", "_", restricoes.normalizar(nome)).strip("_")
            perfil = {
                "id": novo_id, "nome": nome.strip(), "idade": int(idade), "sexo_biologico": sexo,
                "peso_kg": float(peso), "altura_cm": float(altura), "nivel_atividade": atividade,
                "objetivo": objetivo, "restricoes": restr,
                "nao_gosta": [n.strip() for n in nao_gosta.split(",") if n.strip()],
                "condicoes_clinicas": condicoes, "tempo_cozinha_min": int(tempo), "nivel_dedicacao": dedicacao,
                "periodo_feira_dias": periodo, "pessoas_na_casa": int(pessoas),
            }
            novo = memoria.carregar(novo_id, HOJE)
            novo["perfil"] = perfil
            memoria.salvar(novo_id, novo)
            st.session_state["proxima_pessoa"] = novo_id  # aplicada antes de a lista de pessoas ser criada
            st.rerun()


# --- Barra lateral: quem está usando -------------------------------------------------------

perfis = todos_os_perfis()
NOVA = "__nova__"
with st.sidebar:
    st.markdown("### 🥗 NIT")
    escolhas = list(perfis) + [NOVA]
    if "proxima_pessoa" in st.session_state:
        st.session_state["pessoa"] = st.session_state.pop("proxima_pessoa")
    if st.session_state.get("pessoa") not in escolhas:
        st.session_state["pessoa"] = escolhas[0]
    uid = st.selectbox(
        "Quem está usando?", escolhas, key="pessoa",
        format_func=lambda k: "➕ Nova pessoa (questionário)" if k == NOVA else perfis[k]["nome"],
    )
    if uid != NOVA and perfis[uid].get("o_que_testa"):
        st.caption(f"Pessoa fictícia. Testa: {perfis[uid]['o_que_testa']}")
    st.divider()
    st.caption("⚠️ O NIT não substitui um nutricionista. Todos os usuários de exemplo são fictícios.")
    if modelo() is None:
        st.warning("Sem chave do Gemini: a conversa e a leitura de fotos ficam desligadas. O resto funciona.")

if uid == NOVA:
    questionario()
    st.stop()

perfil = perfis[uid]
estado = memoria.carregar(uid, HOJE)
registro = memoria.dia(estado, HOJE)
metas = nutricao.metas_do_dia(perfil)
pode_plano = triagem.pode_montar_plano(perfil)
plano_feira = plano.para_feira(perfil)

with st.sidebar:
    st.divider()
    restr = [NOMES_RESTRICAO.get(r, r) for r in perfil.get("restricoes", [])]
    st.markdown(f"**{perfil['nome']}** · dedicação *{perfil['nivel_dedicacao']}*")
    st.caption(f"Restrições: {', '.join(restr) or 'nenhuma'}")
    if st.button("Apagar os registros desta pessoa", help="Volta ao estado inicial: conversa, checklist, "
                 "contador, cupons e despensa."):
        perfil_salvo = estado.get("perfil")
        memoria.apagar(uid)
        if perfil_salvo:  # quem fez o questionário continua existindo
            novo = memoria.estado_inicial(uid, HOJE)
            novo["perfil"] = perfil_salvo
            memoria.salvar(uid, novo)
        st.session_state.pop("pendente", None)
        st.rerun()

st.title(f"Oi, {perfil['nome']}!")
abas = st.tabs(["💬 Conversa", "✅ Hoje", "🍽️ Receitas", "📋 Plano", "🛒 Feira", "🧾 Gastos", "🏆 Pontos"])


# --- Registro de consumo, usado pela conversa e pelo contador -------------------------------

def registrar_alimento(numero_taco=None, rotulo=None, gramas=0.0, descricao=""):
    """Calcula os nutrientes e grava no dia. Devolve o item ou None se faltarem dados."""
    if rotulo:
        n = contexto.nutrientes_rotulo(estado["rotulos"][rotulo], gramas)
    else:
        n = nutricao.nutrientes(numero_taco, gramas)
    if n["energia_kcal"] is None:
        return None
    item = {"hora": datetime.now().strftime("%H:%M"), "descricao": descricao or n["alimento"], **n}
    registro["consumo"].append(item)
    return item


def confirmar_consumo(propostas, chave):
    st.markdown("**Confira antes de registrar:**")
    with st.form(f"confirmar_{chave}"):
        escolhas = []
        for i, p in enumerate(propostas):
            opcoes = ([("rotulo", p["rotulo"])] if p["rotulo"] else []) + [("taco", n) for n, _ in p["candidatos"]]
            nomes = {("rotulo", p["rotulo"]): f"🏷️ {p['rotulo']} (embalagem)"}
            nomes.update({("taco", n): f"{d} (TACO)" for n, d in p["candidatos"]})
            if not opcoes:
                st.caption(f"“{p['descricao']}” não está na TACO. Use a foto da embalagem, na aba Hoje.")
                continue
            c1, c2, c3 = st.columns([4, 2, 1])
            escolha = c1.selectbox(p["descricao"], opcoes, format_func=nomes.get, key=f"{chave}_a{i}")
            gramas = c2.number_input("gramas", 0.0, 3000.0, float(p["gramas"] or 0), step=10.0, key=f"{chave}_g{i}")
            incluir = c3.checkbox("incluir", value=True, key=f"{chave}_c{i}")
            escolhas.append((escolha, gramas, incluir, p["descricao"]))
        if st.form_submit_button("Registrar", type="primary"):
            salvos, sem_dados = [], []
            for (tipo, valor), gramas, incluir, descricao in escolhas:
                if not incluir or gramas <= 0:
                    continue
                item = registrar_alimento(numero_taco=valor if tipo == "taco" else None,
                                          rotulo=valor if tipo == "rotulo" else None, gramas=gramas, descricao=descricao)
                (salvos if item else sem_dados).append(item or descricao)
            salvar()
            st.session_state.pop("pendente", None)
            if sem_dados:
                st.session_state["aviso"] = (f"A TACO não tem os valores de: {', '.join(sem_dados)}. "
                                             "Registre pela foto da embalagem, na aba Hoje.")
            st.rerun()


# --- 💬 Conversa -----------------------------------------------------------------------------

with abas[0]:
    if not estado["conversa"]:
        st.info("Me conta como está sua alimentação hoje, ou peça uma receita com o que tem em casa. "
                "Também dá para registrar: “comi 150 g de arroz” ou “bebi 2 copos de água”.")
    for msg in estado["conversa"]:
        with st.chat_message("user" if msg["papel"] == "pessoa" else "assistant", avatar=None if msg["papel"] == "pessoa" else "🥗"):
            st.markdown(msg["texto"])
            if msg.get("bastidores"):
                with st.expander("Por trás da resposta"):
                    b = msg["bastidores"]
                    st.caption(f"Intenção: **{b['intencao']}** · modelo: {b['modelo']}")
                    if b["reprovada"]:
                        st.caption("A primeira resposta foi reprovada pela validação e refeita: "
                                   + " ".join(b["reprovada"]))
                    st.code(b["contexto"], language=None)

    if st.session_state.get("aviso"):
        st.warning(st.session_state.pop("aviso"))

    pendente = st.session_state.get("pendente")
    if pendente and pendente["uid"] == uid:
        if pendente["propostas"].get("consumo"):
            confirmar_consumo(pendente["propostas"]["consumo"], f"conv_{pendente['n']}")
        if pendente["propostas"].get("copos"):
            copos = pendente["propostas"]["copos"]
            c1, c2 = st.columns(2)
            if c1.button(f"Registrar {copos} copo(s) de água", type="primary"):
                registro["copos"] += copos
                salvar()
                st.session_state.pop("pendente")
                st.rerun()
            if c2.button("Não registrar"):
                st.session_state.pop("pendente")
                st.rerun()

    mensagem = st.chat_input("Escreva aqui...")
    if mensagem:
        with st.spinner("Pensando..."):
            r = chamar_gemini(lambda: agente.responder(modelo(), perfil, estado, mensagem, HOJE))
        if r:
            estado["conversa"].append({"papel": "pessoa", "texto": mensagem})
            estado["conversa"].append({"papel": "NIT", "texto": r["texto"], "bastidores": {
                "intencao": r["interpretacao"]["intencao"], "modelo": modelo().modelo,
                "reprovada": r["validacao"]["reprovada_na_primeira"], "contexto": r["contexto"]}})
            salvar()
            st.session_state.pop("pendente", None)
            if r["propostas"]:
                st.session_state["pendente"] = {"uid": uid, "propostas": r["propostas"], "n": len(estado["conversa"])}
            st.rerun()


# --- ✅ Hoje: checklist, água e contador ----------------------------------------------------

with abas[1]:
    st.subheader(f"Hoje, {HOJE.strftime('%d/%m')}")
    st.markdown("**Refeições**")
    colunas = st.columns(len(plano.ESTRUTURA))
    for coluna, (refeicao, _) in zip(colunas, plano.ESTRUTURA):
        feita = coluna.checkbox(refeicao, value=refeicao in registro["refeicoes"], key=f"ref_{uid}_{refeicao}")
        if feita != (refeicao in registro["refeicoes"]):
            registro["refeicoes"] = [r for r, _ in plano.ESTRUTURA
                                     if (r in registro["refeicoes"]) != (r == refeicao)]
            salvar()
            st.rerun()

    st.markdown(f"**Água:** {registro['copos']} de {metas['agua_copos']} copos de {nutricao.COPO_ML} ml")
    st.progress(min(registro["copos"] / metas["agua_copos"], 1.0))
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("＋ 1 copo", width="stretch"):
        registro["copos"] += 1
        salvar()
        st.rerun()
    if c2.button("－ 1 copo", width="stretch", disabled=registro["copos"] == 0):
        registro["copos"] -= 1
        salvar()
        st.rerun()

    st.divider()
    st.markdown("**Contador de calorias**")
    total = {k: sum(i.get(k) or 0 for i in registro["consumo"])
             for k in ("energia_kcal", "proteina_g", "carboidrato_g", "lipideos_g")}
    c1, c2, c3, c4 = st.columns(4)
    meta_kcal = f" de {num(metas['kcal'], 0)}" if pode_plano else ""
    c1.metric("kcal", num(total["energia_kcal"], 0) + meta_kcal)
    c2.metric("proteína", f"{num(total['proteina_g'], 0)} g")
    c3.metric("carboidrato", f"{num(total['carboidrato_g'], 0)} g")
    c4.metric("gordura", f"{num(total['lipideos_g'], 0)} g")
    if registro["consumo"]:
        tabela = pd.DataFrame([{
            "hora": i["hora"], "alimento": i["alimento"], "g": i["gramas"], "kcal": i["energia_kcal"],
            "proteína (g)": i["proteina_g"], "fonte": i["fonte"]} for i in registro["consumo"]])
        st.dataframe(tabela, hide_index=True)
        if st.button("Desfazer o último registro"):
            registro["consumo"].pop()
            salvar()
            st.rerun()

    with st.expander("Registrar pela TACO"):
        consulta = st.text_input("O que você comeu?", placeholder="ex.: feijão carioca cozido", key=f"busca_{uid}")
        if consulta:
            candidatos = busca.buscar(consulta, 8)
            if not candidatos:
                st.caption("Não achei na TACO. Tente outro nome ou use a foto da embalagem.")
            else:
                with st.form(f"manual_{uid}"):
                    alimento = st.selectbox("Alimento da TACO", candidatos, format_func=lambda a: a["descricao"])
                    gramas = st.number_input("Quantidade (g)", 1.0, 3000.0, 100.0, step=10.0)
                    if st.form_submit_button("Registrar", type="primary"):
                        if registrar_alimento(numero_taco=alimento["numero"], gramas=gramas):
                            salvar()
                            st.rerun()
                        st.warning("A TACO não tem os valores deste alimento (análise sendo reavaliada). "
                                   "Use a foto da tabela nutricional da embalagem.")

    with st.expander("Registrar pela embalagem (foto da tabela nutricional)"):
        st.caption("O NIT lê a coluna de 100 g. Você confere os números antes de salvar.")
        foto = ler_foto("Foto da tabela nutricional", f"rotulo_{uid}")
        if foto and st.button("Ler a tabela"):
            lido = chamar_gemini(lambda: modelo().ler_imagem(*foto))
            if lido:
                if lido.get("tipo") != "tabela_nutricional":
                    st.warning("Não parece uma tabela nutricional. Tente outra foto, com a tabela inteira e reta.")
                else:
                    st.session_state["rotulo_lido"] = {**lido.get("dados", {}),
                                                       "ilegiveis": lido.get("campos_ilegiveis", [])}
        lido = st.session_state.get("rotulo_lido")
        if lido:
            if lido.get("ilegiveis"):
                st.warning(f"Campos que não deu para ler: {', '.join(lido['ilegiveis'])}. Preencha olhando a embalagem.")
            with st.form(f"rotulo_{uid}"):
                nome_rotulo = st.text_input("Nome do produto", placeholder="ex.: leite sem lactose integral")
                campos = {"energia_kcal": "kcal", "carboidrato_g": "carboidrato (g)", "proteina_g": "proteína (g)",
                          "lipideos_g": "gorduras totais (g)", "fibra_g": "fibra (g)", "sodio_mg": "sódio (mg)"}
                st.caption("Valores por 100 g (ou 100 ml), como estão na embalagem:")
                cols = st.columns(3)
                valores = {k: cols[i % 3].number_input(r, 0.0, 5000.0, float(lido.get(k) or 0), key=f"rot_{k}")
                           for i, (k, r) in enumerate(campos.items())}
                gramas = st.number_input("Quanto você consumiu (g ou ml)?", 0.0, 3000.0, 0.0, step=10.0)
                if st.form_submit_button("Salvar produto e registrar", type="primary"):
                    if not nome_rotulo.strip():
                        st.error("Dê um nome ao produto.")
                    else:
                        estado["rotulos"][nome_rotulo.strip()] = {"nome": nome_rotulo.strip(), **valores}
                        if gramas > 0:
                            registrar_alimento(rotulo=nome_rotulo.strip(), gramas=gramas)
                        salvar()
                        st.session_state.pop("rotulo_lido")
                        st.rerun()
        if estado["rotulos"]:
            st.caption("Produtos salvos (o NIT usa estes valores quando você citar o produto na conversa): "
                       + ", ".join(estado["rotulos"]))

    st.divider()
    p = pontos.pontos_do_dia({**registro, "alimentos_registrados": len(registro["consumo"])},
                             len(plano.ESTRUTURA), metas["agua_copos"])
    st.markdown(f"**Pontos de hoje: {p['pontos']}**" + (" · dia completo! 🎉" if p["dia_completo"] else ""))


# --- 🍽️ Receitas ------------------------------------------------------------------------------

with abas[2]:
    permitidas, bloqueadas = restricoes.filtrar_receitas(perfil)
    st.caption("Só aparecem receitas que respeitam suas restrições. Calorias calculadas pela TACO.")
    so_despensa = st.toggle("Priorizar o que tenho em casa", value=True)
    tempo_max = st.slider("Tempo máximo (min)", 10, 60, 60, step=5)
    if so_despensa:
        ordem = despensa.receitas_com_a_despensa(permitidas, estado["despensa"])
        info = {r["id"]: r for r in ordem}
        por_id = {r["id"]: r for r in permitidas}
        lista = [por_id[r["id"]] for r in ordem] + [r for r in permitidas if r["id"] not in info]
    else:
        info, lista = {}, sorted(permitidas, key=lambda r: r["tempo_min"])
    for receita in [r for r in lista if r["tempo_min"] <= tempo_max]:
        n = nutricao.nutrientes_receita(receita)["por_porcao"]
        selo = " · 🧺 usa item parado" if info.get(receita["id"], {}).get("usa_item_parado") else ""
        with st.expander(f"{receita['nome']} · {receita['tempo_min']} min · {num(n['energia_kcal'], 0)} kcal/porção{selo}"):
            if receita["id"] in info and info[receita["id"]]["faltam"]:
                st.caption(f"Falta em casa: {', '.join(info[receita['id']]['faltam'])}")
            if receita["retirados"]:
                st.info(f"Adaptada para você: sem {', '.join(receita['retirados'])}.")
            st.caption(f"Rende {receita['porcoes']} porções. Por porção, pela TACO: {num(n['energia_kcal'], 0)} kcal · "
                       f"{num(n['proteina_g'])} g de proteína · {num(n['carboidrato_g'])} g de carboidrato · "
                       f"{num(n['lipideos_g'])} g de gordura · {num(n['fibra_g'])} g de fibra")
            st.markdown("**Ingredientes**\n" + "\n".join(
                f"- {i['nome']}: {num(i['gramas'], 0)} g" for i in receita["ingredientes"])
                + "".join(f"\n- {s} a gosto" for s in receita.get("sem_calculo", [])))
            st.markdown("**Preparo**\n" + "\n".join(f"{k}. {passo}" for k, passo in enumerate(receita["preparo"], 1)))
            if receita.get("veja_tambem"):
                st.markdown(f"Receita parecida no site da Ana Maria Braga: [abrir]({receita['veja_tambem']})")
    if bloqueadas:
        with st.expander(f"{len(bloqueadas)} receitas escondidas por causa das suas restrições"):
            for b in bloqueadas:
                st.caption(f"{b['id']}: leva {', '.join(b['motivo'])}")


# --- 📋 Plano ---------------------------------------------------------------------------------

with abas[3]:
    p = plano.montar(perfil)
    if p["bloqueado"]:
        st.warning(f"Por causa de {', '.join(p['motivos'])}, o plano alimentar precisa ser feito por um "
                   "nutricionista, que acompanha você de perto. Receitas, feira, água e contador continuam "
                   "disponíveis aqui.")
    else:
        m = p["metas"]
        st.subheader("Metas do dia")
        c1, c2, c3 = st.columns(3)
        c1.metric("Calorias", f"{num(m['kcal'], 0)} kcal")
        c2.metric("Proteína", f"{m['proteina_g']} g")
        c3.metric("Água", f"{m['agua_copos']} copos")
        c1.metric("Carboidrato", f"{m['carboidrato_g']} g")
        c2.metric("Gordura", f"{m['gordura_g']} g")
        c3.metric("Fibra", f"{m['fibra_g']} g")
        with st.expander("Como estes números foram calculados"):
            st.markdown(
                f"- **Gasto em repouso:** {num(m['tmb_kcal'], 0)} kcal (equação de Mifflin-St Jeor, com peso, "
                "altura, idade e sexo biológico)\n"
                f"- **Gasto do dia:** {num(m['gasto_total_kcal'], 0)} kcal (gasto em repouso × fator de atividade "
                f"{nutricao.FATOR_ATIVIDADE[perfil['nivel_atividade']]})\n"
                f"- **Ajuste ao objetivo:** {num(nutricao.AJUSTE_OBJETIVO[perfil['objetivo']][perfil['nivel_dedicacao']] * 100, 0)}%"
                + (" (a meta foi elevada ao mínimo seguro)" if m["piso_aplicado"] else "") + "\n"
                f"- **Proteína:** {nutricao.proteina_g_por_kg(perfil)} g por kg · **gordura:** 25% das calorias · "
                "**carboidrato:** o restante\n"
                f"- **Fibra:** 14 g a cada 1.000 kcal · **água:** 35 ml por kg\n"
                f"- **Micronutrientes (IOM):** cálcio {m['micronutrientes']['calcio_mg']} mg · ferro "
                f"{num(m['micronutrientes']['ferro_mg'])} mg · vitamina C {m['micronutrientes']['vitamina_c_mg']} mg · "
                f"sódio até {num(m['micronutrientes']['sodio_mg_maximo'], 0)} mg")

        st.subheader("Cardápio da semana")
        st.caption(f"Porção sugerida: **{num(p['fator_porcao'], 2)} porção** de cada receita, para o dia de "
                   f"exemplo chegar perto da meta ({num(p['kcal_dia_ajustado'], 0)} kcal). "
                   "Cada opção indica quantas vezes ela aparece na semana.")
        if perfil["nivel_dedicacao"] in ("leve", "moderado"):
            st.caption("No seu nível de dedicação, use o cardápio como ideia, sem pesar nada.")
        for refeicao in p["refeicoes"]:
            st.markdown(f"**{refeicao['refeicao'].capitalize()}**")
            linhas = [f"- todo dia: {r['nome']}" for r in refeicao["fixas"]]
            for prato in refeicao["pratos"]:
                opcoes = " · ".join(f"{o['receita']['nome']} ({o['vezes_por_semana']}x)" for o in prato["opcoes"])
                rotulo = "" if prato["papel"] == refeicao["refeicao"] else f"{prato['papel']}: "
                linhas.append(f"- {rotulo}{opcoes}")
            st.markdown("\n".join(linhas))


# --- 🛒 Feira e despensa ---------------------------------------------------------------------------

with abas[4]:
    resumo = despensa.resumo(estado["despensa"], HOJE, perfil["periodo_feira_dias"])
    st.metric("Próxima feira", resumo["proxima_feira"].strftime("%d/%m"), help=f"Motivo: {resumo['motivo']}")
    st.caption(f"Motivo: {resumo['motivo']}. A previsão usa o ritmo de consumo desde a última feira "
               f"({date.fromisoformat(estado['despensa']['data_ultima_feira']).strftime('%d/%m')}).")

    st.subheader("Despensa")
    situacao = {"ok": "✅", "acabando": "⚠️ acabando", "acabou": "❌ acabou", "parado": "🧺 parado"}
    tabela = pd.DataFrame([{
        "item": i["nome"], "restante (g)": i["restante_g"], "consumo/dia (g)": i["consumo_g_dia"],
        "acaba em": i["acaba_em"].strftime("%d/%m") if i["acaba_em"] else "-",
        "situação": situacao[i["situacao"]]} for i in resumo["itens"]])
    editada = st.data_editor(tabela, hide_index=True, key=f"despensa_{uid}",
                             disabled=["item", "consumo/dia (g)", "acaba em", "situação"])
    if st.button("Salvar quantidades da despensa"):
        for item, restante in zip(estado["despensa"]["itens"], editada["restante (g)"]):
            item["restante_g"] = max(int(restante), 0)
        salvar()
        st.rerun()
    st.caption("Para registrar uma compra nova, use a aba Gastos: o cupom fiscal atualiza a despensa.")

    st.subheader("Lista de feira")
    dias = st.radio("Para quantos dias?", OPCOES["periodo_feira_dias"], horizontal=True,
                    index=OPCOES["periodo_feira_dias"].index(perfil["periodo_feira_dias"]),
                    format_func=lambda d: f"{d} dias")
    lista = feira.lista_de_feira(plano.itens_para_feira(plano_feira), plano_feira["receitas"], dias,
                                 plano.porcoes_da_casa(perfil, plano_feira), estado["despensa"])
    st.caption(f"Pelo cardápio, para {perfil['pessoas_na_casa']} pessoa(s), já descontando o que tem em casa.")
    st.dataframe(pd.DataFrame([{"item": i["nome"], "quantidade": f"{num(i['gramas'], 0)} g"} for i in lista]),
                 hide_index=True)

    st.subheader("Onde comprar mais barato")
    fontes = dados.carregar_json("onde_comprar.json")
    for f in fontes["fontes"]:
        st.markdown(f"- [{f['nome']}]({f['url']}): {f['o_que_e']}")
    for dica in fontes["dicas_gerais"]:
        st.caption(f"💡 {dica}")


# --- 🧾 Gastos --------------------------------------------------------------------------------------

def tabela_do_cupom(itens):
    """Prepara os itens lidos para conferência, com a sugestão de alimento da TACO para a despensa."""
    linhas = []
    for i in itens:
        sugestao = busca.buscar(i.get("descricao") or "", 1)
        unidade = (i.get("unidade") or "").lower()
        quantidade = i.get("quantidade")
        gramas = None
        if quantidade is not None and unidade in ("kg", "g", "l", "ml"):
            gramas = quantidade * (1000 if unidade in ("kg", "l") else 1)
        linhas.append({
            "descrição": i.get("descricao"), "quantidade": quantidade, "unidade": i.get("unidade"),
            "valor (R$)": i.get("valor"), "alimento (TACO)": sugestao[0]["descricao"] if sugestao else "",
            "gramas": gramas, "despensa": gramas is not None and bool(sugestao),
        })
    return pd.DataFrame(linhas)


with abas[5]:
    r = gastos.resumo(estado["cupons"])
    if r:
        c1, c2 = st.columns(2)
        c1.metric("Média por feira", reais(r["media_por_feira"]))
        c2.metric("Gasto por mês", reais(r["por_mes"]) if r["por_mes"] else "faltam cupons",
                  help="Calculado com os cupons anteriores ao último, divididos pelos dias entre a primeira "
                       "e a última compra.")
        st.caption(f"{r['feiras']} cupom(ns), de {r['primeira']} a {r['ultima']}. Só preços que você pagou.")
    else:
        st.info("O NIT não inventa preços. Envie a foto do cupom fiscal da sua feira, e ele calcula quanto "
                "você gasta com comida.")

    st.subheader("Novo cupom")
    modo = st.radio("Como?", ["Foto do cupom", "Digitar"], horizontal=True, key=f"modo_cupom_{uid}")
    if modo == "Foto do cupom":
        foto = ler_foto("Foto do cupom", f"cupom_{uid}")
        if foto and st.button("Ler o cupom"):
            lido = chamar_gemini(lambda: modelo().ler_imagem(*foto))
            if lido:
                if lido.get("tipo") != "cupom":
                    st.warning("Não parece um cupom fiscal. Tente uma foto com o cupom inteiro e bem iluminado.")
                else:
                    st.session_state["cupom_lido"] = {**lido.get("dados", {}), "ilegiveis": lido.get("campos_ilegiveis", [])}
    elif "cupom_lido" not in st.session_state:
        st.session_state["cupom_lido"] = {"mercado": "", "data": HOJE.isoformat(),
                                          "itens": [{"descricao": "", "quantidade": None, "unidade": "kg", "valor": None}]}

    lido = st.session_state.get("cupom_lido")
    if lido:
        if lido.get("ilegiveis"):
            st.warning(f"Não deu para ler: {', '.join(lido['ilegiveis'])}. Corrija na tabela.")
        st.caption("Confira e corrija os itens. Marque “despensa” para o item entrar na despensa com as gramas indicadas.")
        c1, c2 = st.columns(2)
        mercado = c1.text_input("Mercado", lido.get("mercado") or "")
        try:
            data_lida = date.fromisoformat(lido.get("data") or "")
        except ValueError:
            data_lida = HOJE
        data_cupom = c2.date_input("Data da compra", data_lida, max_value=HOJE, format="DD/MM/YYYY")
        itens = st.data_editor(tabela_do_cupom(lido.get("itens", [])), num_rows="dynamic", hide_index=True,
                               key=f"cupom_editor_{uid}")
        c1, c2 = st.columns(2)
        validos = itens[itens["descrição"].fillna("").astype(str).str.strip() != ""]
        if c1.button("Salvar cupom", type="primary", disabled=validos.empty,
                     help="Preencha pelo menos um item." if validos.empty else None):
            cupom = {"mercado": mercado, "data": data_cupom.isoformat(), "itens": [
                {"descricao": l["descrição"], "quantidade": None if pd.isna(l["quantidade"]) else float(l["quantidade"]),
                 "unidade": l["unidade"], "valor": None if pd.isna(l["valor (R$)"]) else float(l["valor (R$)"])}
                for _, l in validos.iterrows()]}
            compras = []
            for _, l in validos.iterrows():
                if l["despensa"] and not pd.isna(l["gramas"]) and l["gramas"] > 0:
                    alimento = l["alimento (TACO)"] if isinstance(l["alimento (TACO)"], str) else ""
                    achado = busca.buscar(alimento, 1)
                    if achado:
                        compras.append({"taco": achado[0]["numero"], "nome": l["descrição"].lower(), "gramas": int(l["gramas"])})
            estado["cupons"].append(cupom)
            if compras:
                estado["despensa"] = despensa.registrar_feira(estado["despensa"], compras, data_cupom)
            salvar()
            st.session_state.pop("cupom_lido")
            st.success(f"Cupom salvo ({reais(gastos.total_cupom(cupom))}). {len(compras)} item(ns) entraram na despensa.")
            st.rerun()
        if c2.button("Descartar"):
            st.session_state.pop("cupom_lido")
            st.rerun()

    if estado["cupons"]:
        st.subheader("Cupons salvos")
        for c in sorted(estado["cupons"], key=lambda c: c["data"], reverse=True):
            with st.expander(f"{c['data']} · {c.get('mercado') or 'mercado'} · {reais(gastos.total_cupom(c))}"):
                st.dataframe(pd.DataFrame(c["itens"]), hide_index=True)


# --- 🏆 Pontos -------------------------------------------------------------------------------------

with abas[6]:
    inicio = min([date.fromisoformat(d) for d in estado["dias"]] + [HOJE])
    historico = []
    dia_atual = inicio
    while dia_atual <= HOJE:
        reg = estado["dias"].get(dia_atual.isoformat(), {"refeicoes": [], "copos": 0, "consumo": []})
        historico.append((dia_atual, pontos.pontos_do_dia({**reg, "alimentos_registrados": len(reg["consumo"])},
                                                          len(plano.ESTRUTURA), metas["agua_copos"])))
        dia_atual += timedelta(days=1)
    completos = [p["dia_completo"] for _, p in historico]
    c1, c2 = st.columns(2)
    c1.metric("Pontos no total", sum(p["pontos"] for _, p in historico))
    c2.metric("Dias completos seguidos", pontos.sequencia_atual(completos))
    st.caption("Ganha pontos: refeição marcada (10), meta de água (20), dia completo (15), "
               "alimento registrado no contador (5). Dia completo = todas as refeições e a água.")
    obtidas = {c["id"] for c in pontos.conquistas_obtidas(completos)}
    for c in pontos.CONQUISTAS:
        st.markdown(f"{'🏅' if c['id'] in obtidas else '🔒'} **{c['nome']}**: {c['regra']}")
