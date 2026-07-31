# HANDOFF — buscar as escalações na FIFA

> Para a sessão que rodar numa máquina com acesso a `fifa.com`.
> Leia o `CLAUDE.md` inteiro antes de começar. Este arquivo é só a tarefa.

---

## Por que esta sessão existe

O levantamento inteiro está travado num único ponto: **o filtro 3 do algoritmo
de elegibilidade** — *o atleta constou da relação daquela partida?*

Os filtros 1 e 2 estão fechados:

- **filtro 1 (é Eliminatória de Copa do Mundo?)** — `dados/partidas_universo.csv`
  tem as 216 partidas, validadas;
- **filtro 2 (a data cai na janela de registro?)** — `dados/relacoes.csv` já
  cruzou tudo.

Sobraram **264 pares `(atleta, partida)`** marcados `PENDENTE`. Cada um vale
~USD 2.360 se confirmado. Nenhum pode virar claim sem súmula.

A sessão anterior rodou num ambiente sem rota de rede para nenhuma fonte de
futebol. Esta provavelmente tem.

---

## A fonte, e por que ela é melhor que todas as outras

`https://www.fifa.com/pt/match-centre/match/...` → aba **ESCALAÇÃO**.

Exemplo real, Brasil 5–1 Bolívia (08/09/2023, rodada 1):
`https://www.fifa.com/pt/match-centre/match/520/288315/288316/400017279`

Índice de todas as partidas, por confederação:
`https://www.fifa.com/pt/tournaments/mens/worldcup/canadamexicousa2026/qualifiers/conmebol/scores-fixtures`
(troque `conmebol` por `caf`, `concacaf`, `uefa`, `afc`)

Pela hierarquia da seção 6 do `CLAUDE.md`, isto é **nível 1 — PROVA**. É a
própria FIFA, a mesma entidade que montou a lista a ser contestada. Melhor que
Transfermarkt e oGol, que são nível 2.

**Isso muda o que se pode afirmar.** Com Transfermarkt, uma partida confirmada
continua sendo "conferência" e precisa de súmula depois. Com a escalação da
FIFA, ela está fechada.

---

## A fila de trabalho

`dados/partidas_a_conferir.csv` — **121 partidas**, já ordenadas por retorno
(quantos atletas do Botafogo dependem daquela partida).

| Confederação | Partidas |
|---|---|
| CONMEBOL | 78 |
| CONCACAF | 27 |
| CAF | 10 |
| UEFA | 6 |

As de maior retorno, para começar por elas:

| Data | Partida | Atletas |
|---|---|---|
| 19/11/2024 | Brasil × Uruguai | 7 |
| 21/03/2025 | Argentina × Uruguai | 7 |
| 25/03/2025 | Argentina × Brasil | 7 |
| 10/09/2024 | Brasil × Paraguai | 6 |
| 20/03/2025 | Brasil × Colômbia | 6 |
| 25/03/2025 | Bolívia × Uruguai | 6 |
| 05/06/2025 | Brasil × Equador | 6 |
| 10/06/2025 | Uruguai × Venezuela | 6 |

A coluna `atletas` de cada linha diz exatamente quem procurar naquela escalação.
Não precisa ler a escalação inteira — só confirmar presença ou ausência desses
nomes.

---

## O que preencher

Para cada par `(atleta, partida)`, a coluna `status_na_sumula` de
`dados/relacoes.csv`:

| Valor | Quando | Conta? |
|---|---|---|
| `Titular` | na equipa inicial | **sim** |
| `Suplente utilizado` | entrou durante o jogo | **sim** |
| `Suplente não utilizado` | no banco, não entrou | **sim** |
| `Fora da relação` | não consta da escalação | não |

**Minutos e titularidade são irrelevantes para o cálculo.** O dado é binário:
constou da relação ou não. "Suplente não utilizado" vale exatamente o mesmo que
"titular, 90 minutos".

Preencha também `origem_do_status` com `FIFA match-centre` e a URL da partida —
é a referência documental do claim.

---

## Como fazer

### Se o acesso funcionar direto

Confirme antes de escrever qualquer código:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://www.fifa.com/
```

Se der 200, escreva o coletor. Reaproveite o que já existe:

- `parser_tabelas.extrair_linhas(html)` — lê qualquer tabela, inclusive
  aninhada, e captura `title`/`alt` de imagem e `href` de link;
- `parser_tabelas.normalizar()` e `parse_data()`;
- o padrão de `conferencia_selecoes.py`: `--debug` salva o HTML, `--from-html`
  reprocessa sem rede. **Faça igual.** Foi isso que permitiu consertar o parser
  sem gastar requisição.

A escalação da FIFA provavelmente vem de uma API JSON por trás da página. Se
vier, é melhor que raspar HTML — procure na aba Network do navegador.

### Se o acesso não funcionar

Salve as páginas pelo navegador (Ctrl+S) e leia do disco. Foi assim que os
elencos do Transfermarkt entraram. `importar_elenco.py` é o modelo.

---

## Erros que este projeto já cometeu — não repita

Estão na seção 5 do `CLAUDE.md`, mas os três que mais importam aqui:

1. **Notícia não é súmula.** Convocação não prova que o atleta constou da
   relação daquela partida. Todos os erros anteriores vieram de inferir súmula a
   partir de notícia.
2. **Chave é ID, nunca nome.** O Botafogo teve dois "Vitinho" ao mesmo tempo —
   Victor Alexander da Silva (lateral, 23/07/1999, TM 468249) e Vitor da Silveira
   Rodrigues (atacante, 14/06/2007). `atletas.csv` tem a coluna `tm_id`.
3. **Amistoso dentro de Data FIFA não conta.** Nem Copa América, nem Nations
   League, nem a própria Copa do Mundo. O `partidas_universo.csv` já está
   filtrado, mas se você coletar direto do índice da FIFA, confira.

E um erro que esta sessão cometeu, que vale como aviso geral:

4. **O ano no título da página não é o ano do dado.** "Plantel detalhado 2024"
   do Transfermarkt tem `saison_id=2023` — é a temporada 2023/24. Confie no que
   a página declara internamente, não no rótulo.

---

## Duas correções recentes, para não reverter sem querer

- **Jacob Montes: ACEITAR, não rejeitar.** O documento antigo dizia que ele não
  aparecia em elenco nenhum. O Transfermarkt mostra camisa 32 em 2022/23 e
  2023/24 (ID 497494). A Nicarágua disputou exatamente 2 Eliminatórias antes de
  julho/2024 — 05/06 e 08/06/2024 —, que são as 2 atribuídas pela FIFA.
  **Confirmar essas duas escalações é prioridade: ~USD 4.720.**
- **Trinidad e Tobago entrou no escopo.** Darius Lewis esteve no elenco 2022/23 e
  a seleção disputou Eliminatórias da CONCACAF. Estava fora do levantamento.

---

## Depois de coletar

```bash
python partidas_universo.py --validar    # invariantes do torneio
python relacoes.py                        # regenera o cruzamento
python checagem_aritmetica.py             # confronta com a lista da FIFA
python test_parser.py && python test_universo.py
```

O que sair confirmado pela escalação da FIFA pode ir para a planilha do jurídico
como **fechado**. O resto continua `PENDENTE`.

---

## O que NÃO fazer

- Não preencha `status_na_sumula` por dedução. Se a escalação não abrir, deixe
  `PENDENTE` e diga que não abriu.
- Não trate as janelas de registro do `atletas.csv` como verdade — estão
  marcadas `ESTIMADA` porque vieram de imprensa. Se um resultado depender de
  uma delas, sinalize.
- Não reduza `HEADLESS = False` nem a pausa de 4–9s em `conferencia_selecoes.py`.

Quando não souber, diga que não sabe. Neste projeto o custo de uma afirmação
errada já se provou maior que o de uma lacuna assumida.
