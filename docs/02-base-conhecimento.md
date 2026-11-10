# Base de Conhecimento

## Dados Utilizados

O desafio original usa dados financeiros. Como o NIT é um assistente de alimentação, a base foi construída do zero, com fontes oficiais sempre que o dado precisa ser exato.

| Arquivo | Formato | Origem | Utilização no Agente |
| --- | --- | --- | --- |
| [`taco.csv`](../data/taco.csv) | CSV | TACO, 4ª edição (NEPA/UNICAMP), extraída do PDF oficial | Calorias, macronutrientes, minerais e vitaminas de 597 alimentos, por 100 g |
| [`receitas.json`](../data/receitas.json) | JSON | Escritas para o NIT | 25 receitas simples e baratas; cada ingrediente aponta para um alimento da TACO |
| [`restricoes.json`](../data/restricoes.json) | JSON | Regras do NIT | O que cada restrição proíbe, e quando encaminhar ao nutricionista |
| [`usuarios.json`](../data/usuarios.json) | JSON | Fictícios | Respostas do questionário de 7 pessoas com perfis diferentes |
| [`despensa.json`](../data/despensa.json) | JSON | Fictícios | O que cada pessoa comprou e o que sobrou, para prever a próxima feira |
| [`guia_alimentar.json`](../data/guia_alimentar.json) | JSON | Guia Alimentar para a População Brasileira (Ministério da Saúde, 2014) | Os 10 passos, a regra de ouro e os princípios do NIT |
| [`onde_comprar.json`](../data/onde_comprar.json) | JSON | Sites oficiais, verificados em 10/11/2026 | Feiras orgânicas, Armazém do Campo, arroz orgânico do MST e calendário de sazonalidade |

---

## Adaptações nos Dados

### TACO: do PDF para o CSV

A TACO oficial só está disponível em PDF. O script [`scripts/extrair_taco.py`](../scripts/extrair_taco.py) lê o PDF e gera o CSV, para que qualquer pessoa possa refazer o processo e conferir o resultado.

- **Por que usar a posição das palavras:** a extração de texto simples desalinhava as colunas vazias, e a extração de tabelas tirava a vírgula decimal do lugar. A versão final atribui cada número à coluna cujo cabeçalho está mais perto na página.
- **Validação:** as calorias de cada alimento foram comparadas com 4 × proteína + 4 × carboidrato + 9 × gordura. A conta fecha em 588 dos 597 alimentos; os 9 restantes são hortaliças com fatores próprios, bebidas alcoólicas e fermento químico.
- **Valores especiais mantidos como na TACO:** `Tr` (traço, quantidade pequena demais para medir), `NA` (não se aplica), `*` (análise sendo reavaliada) e vazio (análise não feita). O código trata cada um; nunca os troca por zero sem avisar.
- **Lacuna importante:** o leite de vaca integral e o desnatado estão marcados com `*`, sem valores. O NIT não inventa esses números: pede a foto da tabela nutricional da embalagem.

### Receitas próprias, com link para a Ana Maria Braga

As 25 receitas foram escritas para o NIT, com ingredientes baratos, da cultura alimentar brasileira (cuscuz, angu, quibebe, baião de dois, moqueca, feijão-tropeiro) e de preparo curto. Cada ingrediente aponta para o número do alimento na TACO, então as calorias são calculadas pelo código, não escritas à mão.

O campo `veja_tambem` leva a uma receita parecida no site oficial da Ana Maria Braga (13 das 25 receitas têm um par). O conteúdo de lá não é copiado: o modo de preparo é protegido por direito autoral, então o NIT só indica o link. Todos os links foram abertos e conferidos.

Ingredientes marcados com `"opcional": true` (como o queijo do baião) podem ser retirados para atender a uma restrição.

### Restrições: grupos, palavras inteiras e exceções

Uma restrição proíbe um alimento se ele pertencer a um grupo da TACO ou tiver uma palavra-chave na descrição. Os testes revelaram três cuidados necessários:

| Problema encontrado | Exemplo | Solução |
| --- | --- | --- |
| Os grupos da TACO não bastam | "Pão de queijo" está no grupo das verduras | Palavras-chave além dos grupos |
| Buscar pedaços de palavra bloqueia por engano | "quibe" bloqueava o **Quibebe**; "mel" bloqueava o **Melado**; "torrada" bloqueava a **farinha de mandioca torrada** | Busca por palavra inteira |
| Palavra inteira deixa passar o plural | "ovo" não pegava "macarrão com **ovos**", um risco para quem tem alergia | Plurais nas palavras-chave |
| Nomes enganosos | "Leite de coco" e "couve-manteiga" não têm lactose; "Soja, queijo (tofu)" é vegano | Lista de exceções |

### Usuários fictícios

Sete pessoas, cada uma criada para testar um comportamento:

| Pessoa | Perfil | O que testa |
| --- | --- | --- |
| Alex | Quer emagrecer, sem lactose, dedicação moderada | Restrição respeitada |
| Matheus | Ganhar massa, treina pesado, não gosta de quiabo, dedicação intensa | Cálculo de proteína e preferências |
| Ricardo | Vegetariano, 15 minutos para cozinhar, dedicação leve | Receitas rápidas |
| Jorge | Diabético | Encaminhamento ao nutricionista |
| Juliana | Vegana, mãe solo de duas crianças, orçamento apertado | Feira barata e onde comprar |
| Fernanda | Celíaca, corredora, modo Insano | Restrição grave, alto gasto de energia e tom enérgico |
| Aline | Gestante | Encaminhamento ao nutricionista |

---

## Estratégia de Integração

### Como os dados são carregados?

Os arquivos são lidos uma vez quando o aplicativo abre e ficam na memória. São pequenos (a TACO inteira tem cerca de 100 KB), então não é preciso banco de dados neste protótipo.

### Como os dados são usados no prompt?

A base **não** vai inteira para o Gemini. O código consulta os arquivos, faz os cálculos e os filtros, e só depois monta um contexto curto com o que interessa para aquela pergunta:

1. **Perfil:** nome, objetivo, nível de dedicação (que define o tom) e restrições.
2. **Dados já filtrados:** só as receitas permitidas para a pessoa, com os ingredientes proibidos já retirados.
3. **Números já calculados:** calorias, metas e previsões vêm prontas do código, com a fonte indicada.
4. **Regras:** o Gemini só pode usar o que está no contexto, e precisa dizer quando a informação não estiver lá.

Isso tem três vantagens: a IA não tem como sugerir um alimento proibido que nem recebeu, os números não dependem dela, e o contexto menor deixa as respostas mais rápidas e baratas.

---

## Exemplo de Contexto Montado

Pergunta do Alex: *"O que eu faço hoje com o que tem em casa?"*

O código filtra as receitas pela restrição (sem lactose), cruza com a despensa e calcula a previsão. O Gemini recebe só isto:

```text
PESSOA: Alex · objetivo: emagrecer · dedicação: moderado (tom tranquilo e organizado)
RESTRIÇÕES: sem lactose (os itens abaixo já foram filtrados)

DESPENSA (referência 10/11/2026, fonte: registros do Alex):
- arroz branco: 1.100 g · acaba por volta de 21/11
- feijão carioca: 550 g · acaba por volta de 21/11
- peito de frango: 300 g · acaba por volta de 12/11
- ovos: 600 g (cerca de 12 unidades) · acaba por volta de 16/11
- tomate: 350 g · acaba por volta de 14/11
- abobrinha: 600 g · ainda não foi usada
- banana-nanica: acabou

RECEITAS QUE USAM A DESPENSA (calorias calculadas pela TACO):
- Omelete de legumes · 15 min · 146 kcal e 10,8 g de proteína por porção · falta: cebola, salsa
- Abobrinha refogada com tomate · 15 min · 53 kcal por porção · falta: cebola, alho, óleo
- Galinhada com milho · 50 min · 340 kcal e 22,8 g de proteína por porção · falta: milho-verde, cebola, alho, óleo, cebolinha

REGRAS: use só os dados acima. Não cite valores que não estejam aqui.
Se faltar um ingrediente, diga qual e pergunte se a pessoa tem.
A abobrinha está parada: priorize-a.
```

O Gemini então escreve a resposta no tom do Alex, por exemplo: *"Opa, bora usar essa abobrinha antes que ela passe do ponto? Um omelete de legumes com abobrinha e tomate sai em 15 minutos. Você tem cebola aí? Ela não está na sua despensa."*

Repare que cebola, alho e óleo aparecem como "falta" porque o Alex não os registrou. Na Etapa 4, os temperos básicos (cebola, alho, óleo, azeite, cebolinha e salsa) passaram a ser tratados como itens que a pessoa tem em casa, sem cobrar o registro de cada dente de alho. No aplicativo, o contexto real de cada resposta aparece em "Por trás da resposta", abaixo da mensagem do NIT.
