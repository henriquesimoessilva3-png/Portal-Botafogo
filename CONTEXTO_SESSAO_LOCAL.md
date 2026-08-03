# Contexto para abrir uma sessão nova no computador

> Cole este arquivo inteiro na primeira mensagem, ou aponte o Claude para ele.
> Leia junto o `documentos/CLAUDE.md` — é o contexto durável do projeto.

---

## Onde estamos

O Botafogo precisa validar, na plataforma da FIFA, quais atletas foram cedidos
para partidas das Eliminatórias da Copa 2026. Cada partida vale **USD 2.360**.
Há também a cota da fase final, por dia de cessão.

O levantamento já produziu:

| | |
|---|---|
| Universo de partidas | **216 jogos**, 22 seleções, validado nas invariantes de cada confederação |
| Elencos do Botafogo | **302 atletas**, temporadas 2021/22 a 2025/26, com ID do Transfermarkt |
| Partidas confirmadas em escalação oficial | **49** · USD 115.640 |
| Cota da Copa (Danilo) | 34 dias · USD 170.000 |
| Extrato do TMS conferido | 51 linhas legíveis de 58 |
| Ainda nunca conferido | 170 partidas · teto de USD 401.200 |

Tudo está em `Portal Fifa Club Benefits/`, que sobe em `localhost:5066` com
`./iniciar.sh` ou duplo clique em `iniciar.command`.

---

## O que esta sessão precisa fazer

Em ordem de valor. Os três primeiros são os que movem dinheiro.

### 1. Rejeitar o amistoso do Loor

A FIFA atribuiu ao Botafogo **Canadá × Equador, 13/11/2025**, como partida de
Eliminatórias de Cristhian Loor. **Não é.** O Canadá era anfitrião da Copa 2026 e
não disputou nenhuma classificatória; as Eliminatórias do Equador terminaram em
09/09/2025. É amistoso, e amistoso não gera direito.

Ação: abrir o Loor na plataforma e clicar em **Reject**.

### 2. Disputar os quatro conflitos do Almada

Estão marcados "FIFA resolving conflict" — outro clube reivindicou as mesmas
partidas. As quatro caem **dentro** do vínculo dele com o Botafogo
(03/07/2024 a 17/07/2025):

| Data | Partida |
|---|---|
| 21/03/2025 | Uruguay 0 × 1 Argentina |
| 25/03/2025 | Argentina 4 × 1 Brazil |
| 05/06/2025 | Chile 0 × 1 Argentina |
| 10/06/2025 | Argentina 1 × 1 Colombia |

São **USD 9.440**. Vale sustentar a posição com a data de registro do TMS.

Os outros três conflitos — 04/09 e 09/09/2025 do Luiz Henrique, 04/09/2025 do
Almada — caem **fora** do vínculo. Não vale disputar.

### 3. Reivindicar os quatro que já têm prova

Estes têm partida **confirmada em escalação oficial da FIFA** e **não aparecem**
na plataforma. Precisam ser buscados um a um pela função de pesquisa:

| Atleta | Partidas | Valor |
|---|---|---|
| Gatito Fernández | 6 | USD 14.160 |
| Igor Jesus | 4 | USD 9.440 |
| Alex Telles | 3 | USD 7.080 |
| Luis Segovia | 1 | USD 2.360 |

O detalhe jogo a jogo de cada um está em `index.html`, seção 04.

### 4. Completar os prints do TMS

Sete linhas ficaram fora do recorte — 5 do Almada e 2 do Luiz Henrique. Rolar a
lista até o fim e printar de novo. Depois acrescentar as linhas a
`dados/tms_extrato.csv` e rodar:

```bash
python3 codigo/conferencia_tms.py --json dados/conferencia_tms.json
python3 codigo/gerar_relatorio_web.py --saida index.html
```

### 5. Conferir os 14 atletas nunca verificados

`dados/partidas_a_conferir.csv` tem a fila, ordenada por retorno. Bastos (10
partidas de Angola) e Kadir Barría (8 do Panamá) na frente. A fonte é a aba
**ESCALAÇÃO** do match-centre: `fifa.com/pt/match-centre/match/...`

### 6. Pedir o extrato completo do TMS ao departamento de registro

Todas as janelas de registro do levantamento vêm de fonte de conferência, não do
registro federativo. Foi uma janela estimada errada que quase produziu a
rejeição de três partidas do Almada que não existiam.

---

## Três coisas que esta sessão descobriu e que não podem ser perdidas

**A plataforma tem três estados, não um.** Verde com botão *Reject* = já é nossa.
Âmbar "FIFA resolving conflict" = outro clube reivindicou a mesma partida.
Branca com botão *Claim* = do atleta, mas não atribuída a ninguém. O print
antigo mostrava só o total por atleta e escondia essa distinção inteira.

**O histórico traz todas as partidas do atleta pela seleção**, não só as nossas.
Savarino aparece com 16 — as 6 de 2023 são de antes de ele chegar, e estão
corretamente como disponíveis. Não reivindique o que está fora do vínculo.

**A FIFA já mexeu na lista desde o print original.** Ela dizia 39 partidas
atribuídas; o extrato mostra **32**. O Luiz Henrique caiu de 8 para 6 sozinho —
os dois de setembro/2025 viraram conflito, o que confirma que ele já estava no
Zenit.

---

## Uma correção que precisa ser respeitada

Uma versão anterior deste documento usava o Cristhian Loor como evidência de que
o critério da FIFA seria **cessão** e não **escalação** — o raciocínio era que a
FIFA lhe atribuíra 1 partida sem que ele figurasse em escalação nenhuma.

**Esse argumento caiu.** A partida dele nunca foi Eliminatória: é o amistoso do
item 1. A explicação é mais simples e mais mundana do que a hipótese.

A questão do critério **continua aberta** — o texto da plataforma fala em
*released by your club*, e cedido não é a mesma coisa que relacionado. Mas o
Loor não é mais prova disso. Se for perguntar à FIFA, use o texto do
regulamento, não esse caso.

---

## Erros que este projeto já cometeu

Estão na seção 5 do `documentos/CLAUDE.md`. Os que mais importam:

1. **Notícia não é súmula.** Convocação não prova que o atleta constou da
   relação. Três erros anteriores vieram todos daí.
2. **Chave é ID, nunca nome.** O Botafogo teve dois "Vitinho" ao mesmo tempo.
   `atletas.csv` tem a coluna `tm_id`.
3. **Amistoso dentro de Data FIFA não conta.** Nem Copa América, nem Nations
   League. Foi exatamente esse o erro do Loor — só que cometido pela FIFA.
4. **O rótulo da página não é o dado.** "Plantel detalhado 2024" do Transfermarkt
   tem `saison_id=2023`: é a temporada 2023/24. Confie no que a página declara
   internamente.

---

## Como rodar

```bash
cd "Portal Fifa Club Benefits"
./iniciar.sh                    # sobe :5066

# regerar, depois de mudar dados
python3 codigo/conferencia_tms.py --json dados/conferencia_tms.json
python3 codigo/parte2_cessao.py --pdf documentos/levantamento_fifa_botafogo.pdf
python3 codigo/gerar_relatorio_web.py --saida index.html

# testes, antes de commitar
cd codigo && python3 test_parser.py && python3 test_universo.py
```

Servir exige só `python3`. Regerar exige `pip install pypdf`.

---

## O padrão de trabalho que vale manter

Este projeto tem uma regra que já se pagou várias vezes: **quando não souber,
diga que não sabe em vez de inferir.** O custo de uma afirmação errada aqui já se
provou maior que o de uma lacuna assumida — foi assim que quase se rejeitaram
partidas do Almada que existiam, e que quase se descartou o Jacob Montes, que
estava no elenco com a camisa 32.

Toda tabela do levantamento distingue **o que está provado** do **que está em
aberto**. Nada de teto aritmético entra somado ao confirmado. Vale manter.
