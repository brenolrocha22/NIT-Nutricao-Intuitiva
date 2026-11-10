"""Extrai a Tabela 1 da TACO (4a ed.) para data/taco.csv.

Fonte: Tabela Brasileira de Composicao de Alimentos, 4a edicao revisada e
ampliada, NEPA/UNICAMP, 2011. PDF usado:
https://www.cfn.org.br/wp-content/uploads/2017/03/taco_4_edicao_ampliada_e_revisada.pdf

Uso: python scripts/extrair_taco.py taco.pdf data/taco.csv

Cada pagina tem um cabecalho com as colunas; cada valor e atribuido a coluna
cujo cabecalho esta mais perto. A extracao de texto simples desalinha as
colunas vazias, por isso o script usa a posicao de cada palavra na pagina.
"""
import csv
import re
import sys
from collections import defaultdict

import pymupdf

pdf, out = sys.argv[1], sys.argv[2]
doc = pymupdf.open(pdf)

MACRO_HEAD = [("Umidade", "umidade_pct"), ("(kcal)", "energia_kcal"), ("(kJ)", "energia_kj"),
              ("Proteína", "proteina_g"), ("Lipídeos", "lipideos_g"), ("Colesterol", "colesterol_mg"),
              ("idrato", "carboidrato_g"), ("Alimentar", "fibra_g"), ("Cinzas", "cinzas_g"),
              ("Cálcio", "calcio_mg"), ("Magnésio", "magnesio_mg")]
MINERAL_HEAD = [("Manganês", "manganes_mg"), ("Fósforo", "fosforo_mg"), ("Ferro", "ferro_mg"),
                ("Sódio", "sodio_mg"), ("Potássio", "potassio_mg"), ("Cobre", "cobre_mg"),
                ("Zinco", "zinco_mg"), ("Retinol", "retinol_mcg"), ("RE", "re_mcg"), ("RAE", "rae_mcg"),
                ("Tiamina", "tiamina_mg"), ("Riboflavina", "riboflavina_mg"),
                ("Piridoxina", "piridoxina_mg"), ("Niacina", "niacina_mg"), ("C", "vitamina_c_mg")]
VALUE = re.compile(r"^(\d+(,\d+)?[a-z]?|Tr|NA|\*)$")

foods = defaultdict(dict)
group = "Cereais e derivados"  # o primeiro grupo fica acima da area de dados da 1a pagina
warnings = []

for page in doc:
    text = page.get_text()
    if "Tabela 1. Composição" not in text:
        continue
    raw = page.get_text("words")  # x0, y0, x1, y1, word, ...
    # paginas giradas: a linha da tabela corre na vertical. Normaliza para
    # (coluna_inicio, linha_inicio, coluna_fim, linha_fim, palavra)
    rotated = any(w[4] == "Tabela" and (w[3] - w[1]) > (w[2] - w[0]) for w in raw)
    if rotated:
        words = [(-w[3], w[0], -w[1], w[2], w[4]) for w in raw]
    else:
        words = [w[:5] for w in raw]
    kind = "mineral" if "Manganês" in text else "macro"
    head = MINERAL_HEAD if kind == "mineral" else MACRO_HEAD
    # centro horizontal de cada cabecalho
    centers = {}
    head_bottom = 0
    for label, key in head:
        cand = [w for w in words if w[4] == label]
        if label == "C":  # "Vitamina C": o C fica abaixo de "Vitamina"
            vit = [w for w in words if w[4] == "Vitamina"]
            cand = [w for w in cand if vit and abs(w[0] - vit[0][0]) < 30]
        if not cand:
            continue
        w = min(cand, key=lambda w: w[1])
        centers[key] = (w[0] + w[2]) / 2
        head_bottom = max(head_bottom, w[3])
    if units := [w for w in words if w[4] == "(mg)"]:
        # a linha de unidades mais alta fecha o cabecalho; outras "(mg)" soltas aparecem no meio dos dados
        head_bottom = max(head_bottom, min(units, key=lambda w: w[1])[3])
    if len(centers) < len(head) - 1:  # pagina sem o cabecalho completo: nao e pagina de dados
        continue
    desc_limit = min(centers.values()) - 15

    # agrupa palavras por linha (mesma altura)
    rows = defaultdict(list)
    for w in words:
        if (w[1] + w[3]) / 2 <= head_bottom:  # pelo centro: a 1a linha de dados pode encostar no cabecalho
            continue
        rows[round((w[1] + w[3]) / 2)].append(w)
    merged = []
    for y in sorted(rows):
        if merged and y - merged[-1][0] <= 2:
            merged[-1][1].extend(rows[y])
        else:
            merged.append([y, list(rows[y])])

    for _, ws in merged:
        ws.sort(key=lambda w: w[0])
        first = ws[0][4]
        if not first.isdigit():
            line = " ".join(w[4] for w in ws)
            if kind == "macro" and not re.search(r"\d", line) and len(line) < 45:
                group = line
            continue
        num = int(first)
        desc = " ".join(w[4] for w in ws[1:] if w[2] < desc_limit)
        vals = [w for w in ws[1:] if w[2] >= desc_limit]
        food = foods[num]
        food["numero"] = num
        if kind == "macro" and desc and "descricao" not in food:
            food["descricao"] = desc
            food["grupo"] = group
        for w in vals:
            if not VALUE.match(w[4]):
                warnings.append((num, kind, w[4]))
                continue
            cx = (w[0] + w[2]) / 2
            key = min(centers, key=lambda k: abs(centers[k] - cx))
            value = re.sub(r"(?<=\d)[a-z]$", "", w[4])  # tira letra de nota de rodape, preserva "Tr"
            if key in food:
                if food[key] != value:
                    warnings.append((num, key, food[key], value))
                continue
            food[key] = value

fields = ["numero", "descricao", "grupo"] + [k for _, k in MACRO_HEAD] + [k for _, k in MINERAL_HEAD]
with open(out, "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=fields)
    wr.writeheader()
    for num in sorted(foods):
        wr.writerow({k: foods[num].get(k, "") for k in fields})

core = ["descricao", "energia_kcal", "proteina_g", "lipideos_g", "carboidrato_g"]
missing = [n for n, f in foods.items() if not all(f.get(k) for k in core)]
print(f"alimentos: {len(foods)}  sem dados basicos: {len(missing)} {missing[:30]}")
print("avisos:", len(warnings), warnings[:30])
