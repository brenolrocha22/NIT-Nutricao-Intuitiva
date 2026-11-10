# NIT · Nutrição Intuitiva

Assistente de alimentação com IA generativa: cria receitas com o que você já tem em casa, monta um plano alimentar de acordo com seus objetivos e restrições, organiza a feira e acompanha o dia a dia.

> Projeto do Lab **"Construa seu Assistente Virtual com Inteligência Artificial"** da [DIO](https://www.dio.me/). O [repositório base do desafio](https://github.com/digitalinnovationone/dio-lab-bia-do-futuro) propõe um agente financeiro e permite adaptar a ideia para outro contexto. Aqui, o contexto é alimentação.

🚧 **Em construção.** O projeto está sendo feito por etapas, e este README é atualizado a cada uma.

> ⚠️ **O NIT não substitui um nutricionista.** Em casos de gestação, diabetes, doença renal, transtornos alimentares ou uso de medicação, ele não monta plano alimentar e orienta a procurar um profissional. Todos os usuários deste projeto são fictícios.

## O que o NIT faz

| # | Funcionalidade | Como funciona |
| --- | --- | --- |
| 1 | Receitas com o que tem em casa | Você informa os ingredientes, e o NIT sugere receitas que respeitam suas restrições |
| 2 | Plano alimentar | Um questionário levanta objetivo, restrições, rotina e nível de dedicação. Calorias e macronutrientes são calculados por fórmulas, não estimados pela IA |
| 3 | Lista de feira | Gerada a partir do plano, para 15 ou 30 dias, à sua escolha |
| 4 | Despensa | O que foi comprado entra, o que foi consumido sai |
| 5 | Checklist do dia | Refeições feitas e copos de água |
| 6 | Contador de calorias | Por descrição e peso ("150 g de arroz branco cozido"), com valores da TACO, ou pela foto da tabela nutricional da embalagem. Nos dois casos, você confere os dados antes de registrar |
| 7 | Previsão da próxima feira | Calculada pelo ritmo de consumo de cada item da despensa |
| 8 | Gastos reais | Você envia a foto do cupom fiscal, confere os itens lidos e o NIT calcula o custo médio da feira só com preços que você realmente pagou |
| 9 | Pontos e conquistas | Pontos por cumprir as tarefas do dia |
| 10 | Uso no celular | Interface que funciona no navegador do celular |

### Níveis de dedicação

| Nível | Para quem |
| --- | --- |
| Leve | Quer melhorar o que já come, sem mudar a rotina |
| Moderado | Segue um cardápio flexível |
| Intenso | Segue o plano com quantidades |
| Insano | "Eu sou uma máquina e não falho" |

### Princípios

- **Números vêm de dados, não da IA.** Valores nutricionais saem da Tabela Brasileira de Composição de Alimentos (TACO) ou da tabela nutricional da embalagem, e preços saem só dos cupons fiscais do próprio usuário. O NIT não inventa preço nem nutriente, e não estima calorias pela foto do prato, porque o peso da comida não dá para medir numa imagem.
- **Restrições são verificadas pelo código.** Um alimento proibido para a pessoa é retirado antes de qualquer sugestão chegar à IA.
- **Comida de verdade e acessível.** O NIT segue o Guia Alimentar para a População Brasileira, valoriza alimentos regionais e da época, a cultura alimentar indígena e afro-brasileira, e indica feiras e produtores da agricultura familiar e da reforma agrária como opção de compra mais barata e saudável.

## Etapas do desafio

| # | Etapa | Onde fica | Situação |
| --- | --- | --- | --- |
| 1 | Documentação do agente | [docs/01-documentacao-agente.md](docs/01-documentacao-agente.md) | ✅ Feita |
| 2 | Base de conhecimento | [data/](data/) e [docs/02-base-conhecimento.md](docs/02-base-conhecimento.md) | A fazer |
| 3 | Prompts do agente | [docs/03-prompts.md](docs/03-prompts.md) | A fazer |
| 4 | Aplicação funcional (Python + Streamlit + Gemini) | [src/](src/) | A fazer |
| 5 | Avaliação e métricas | [docs/04-metricas.md](docs/04-metricas.md) | A fazer |
| 6 | Pitch | [docs/05-pitch.md](docs/05-pitch.md) | A fazer |

## Próximos passos (fora do escopo do protótipo)

Estas funcionalidades exigem login, banco de dados compartilhado e regras de privacidade para dados de saúde de pessoas reais, e por isso ficam para uma versão futura:

- **Comunidade:** convidar pessoas para grupos fechados ou abertos, com ranking coletivo de tarefas cumpridas.
- **Acompanhamento por nutricionista:** profissionais se cadastram com o registro no CRN validado e acompanham remotamente os pacientes que autorizarem o acesso aos próprios dados.
- **Privacidade:** consentimento explícito e controle de quem vê cada dado, como a LGPD exige para dados de saúde, que são dados pessoais sensíveis.

## Estrutura

```text
NIT/
├── README.md     apresentação do projeto
├── data/         base de conhecimento (alimentos, receitas, usuários fictícios)
├── docs/         documentação de cada etapa
├── scripts/      ferramentas de preparação dos dados (ex.: extração da TACO)
└── src/          código da aplicação
```
