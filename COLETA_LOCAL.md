# Coleta na sua máquina — o que rodar e o que me mandar

O que falta no levantamento não é código: é acesso ao Transfermarkt e ao oGol,
que esta sessão não tem. Esta é a parte que só você consegue rodar.

O que ela destrava é o **filtro 3** do algoritmo — *o atleta constou da relação
daquela partida?* — que é o único que separa `PENDENTE` de dinheiro
reivindicável. Os filtros 1 e 2 já estão fechados.

---

## Antes de começar

```bash
pip install playwright pandas openpyxl
playwright install chromium
```

`HEADLESS = False` e a pausa de 4–9s continuam intencionais. Não reduza.

---

## Passo 1 — preencher as URLs

Abra `atletas.csv`. As colunas `url_transfermarkt` e `url_ogol` estão em branco
de propósito: precisam vir do navegador, uma por atleta.

- **url_transfermarkt**: página do atleta → aba **"Jogos pela seleção"**
  (`/nationalmannschaft/spieler/<id>`). É essa aba que separa competição por
  competição — foi o print dela que resolveu o segundo erro do Vitinho.
- **url_ogol**: página do atleta no ogol.com.br.

**Confira o ID e a data de nascimento de cada link antes de colar.** O Botafogo
teve dois "Vitinho" ao mesmo tempo — Victor Alexander da Silva (lateral,
23/07/1999) e Vitor da Silveira Rodrigues (atacante, 14/06/2007). O script tem
guarda contra isso, mas ela só funciona se o `nascimento` no CSV estiver certo.

Comece pelos 8 da lista da FIFA e pelos candidatos a claim com mais espaço
aritmético — `dados/checagem_aritmetica.csv` já está ordenado por isso.

---

## Passo 2 — uma passada capturando o HTML

```bash
python conferencia_selecoes.py --debug
```

Isso salva, para cada atleta e cada fonte, um `.html` e um `.json` em
`debug_html/`. **É esse par de arquivos que eu preciso.**

Uma passada só. Não rode de novo para testar ajuste — o passo 3 existe para isso.

---

## Passo 3 — iterar sem tocar mais no site

```bash
python conferencia_selecoes.py --from-html debug_html/
```

Reprocessa os dumps salvos, sem rede e sem navegador. Cada rodada leva segundos
e não gasta requisição. É aqui que os seletores se ajustam.

---

## O que me mandar

Qualquer um destes serve, em ordem de preferência:

1. **A pasta `debug_html/` inteira** (zipada). É o ideal — com o HTML real eu
   fecho os seletores de uma vez.
2. **Um `.html` só**, de um atleta cuja resposta certa a gente já conhece — o
   **Vitinho** é o melhor caso de teste: a planilha diz que são exatamente 2
   partidas (Chile 04/09/25, suplente não utilizado; Bolívia 09/09/25, titular,
   61 min), e os amistosos de outubro contra Coreia e Japão têm que ficar de
   fora. Se o parser reproduzir isso, os seletores estão certos.
3. **A saída do terminal** do passo 2 ou 3, se não der para mandar arquivo. Ajuda
   menos, mas os alertas dizem o que quebrou.

---

## O que olhar no resultado

`conferencia_selecoes.xlsx`:

- **Resumo** — só entra partida em que **as duas fontes concordam**. A coluna
  `depende_de_janela_estimada` marca o que ainda depende de janela de imprensa.
- **Reconciliacao** — `DIVERGENTE` e `SÓ EM UMA FONTE` são a fila de conferência
  na súmula. Divergência não é bug do script: é o sinal de alerta funcionando.
- **Fila de conferencia** — o que o parser não soube decidir, com a linha crua
  do site na coluna `bruto`.
- **Alertas** — URL faltando, timeout, e principalmente **nascimento que não
  confere**, que é possível homônimo.

---

## O outro pedido, que não é técnico

`atletas.csv` traz quase todas as janelas de registro marcadas
`ESTIMADA - substituir por TMS`, porque vieram de imprensa. **Peça o extrato do
TMS ao departamento de registro.** Enquanto ele não chegar, todo número que sai
daqui carrega a ressalva — inclusive o excedente do Almada, que é o argumento
mais forte que temos.

Duas perguntas que valem ser feitas junto:

1. **Jacob Montes** — a FIFA atribuiu 2 partidas pela Nicarágua a um atleta que
   não aparece em nenhum elenco de 2024 nem de 2025. Existe registro dele no TMS
   em nome do Botafogo? Se não existir, são 2 partidas a rejeitar.
2. **Danilo Santos** — a cota da fase final é por DIA de cessão, não por partida.
   Confirmar com a FIFA a data exata de abertura da janela.
