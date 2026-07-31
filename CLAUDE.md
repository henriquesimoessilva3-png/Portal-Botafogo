Contexto de projeto para continuidade. Leia inteiro antes de qualquer alteração.

---

## 1. O problema

A FIFA abriu uma plataforma chamada **"Player Releases for S.a.f. Botafogo"** onde o
clube precisa validar quais atletas foram cedidos para partidas das Eliminatórias da
Copa do Mundo 2026. Cada partida confirmada vale dinheiro. Cada nome esquecido é
dinheiro perdido.

Quem conduz é a **Tamires, do jurídico** do clube. A demanda chegou via **Brunno Noce**.
O papel desta análise é instrumentalizar o jurídico, não substituí-lo.

O objetivo final não é "listar jogadores". É produzir, para cada par
`(atleta, partida)`, uma resposta defensável para: *o Botafogo detinha o registro
deste atleta na data desta partida de Eliminatórias, e ele constou da relação?*

---

## 2. As regras do programa

Fonte: comunicado oficial da FIFA de 05/06/2026 e material do EFC.

| Item | Regra |
|---|---|
| Fundo total do ciclo | USD 355 milhões (+70% vs. Catar 2022) |
| Parcela **Eliminatórias** | USD 100 mi, rateio **por jogador × partida**. Com 905 jogos disputados, ~**USD 2.360 por jogador por partida** |
| Critério Eliminatórias | Ter sido **relacionado na súmula** / cedido para aquela partida. Minutos e titularidade são **irrelevantes** |
| Parcela **Copa do Mundo** | USD 250 mi, rateio **por jogador × dia**, piso estimado ~USD 5.000/dia |
| Janela da Copa | De ~10 dias antes do jogo de abertura até o dia seguinte à última partida da seleção do atleta |
| Quem recebe | O clube que **detinha o registro** na data da cessão. Venda posterior não transfere o direito |

### Texto literal da plataforma (transcrito do print)

> The list of players below have been identified by FIFA as being released by your club
> for one or more FIFA World Cup 26 Qualifying Matches, and was prepared using data from
> the **FIFA Transfer Matching System and national registration systems**. (...)
> 1. Review that the players listed are correct
> 2. Reject any players that have been assigned to your club, and which you did not
>    release **for the specific match**
> 3. Search for any players which are missing with the search function, and claim them
>
> (...) your club will not be able to view any actions undertaken by any other clubs in
> the platform. In addition, the actions undertaken by your club are **indicative**, and
> will assist FIFA with the calculation process, with the final entitlement (...) subject
> to FIFA's final calculation following the completion of the final tournament.

**Três implicações que mudam o trabalho:**

1. A lista foi montada a partir do **TMS**, não de súmula. Logo os erros são de
   **registro**, e a prova é documental: data de transferência no TMS + súmula oficial.
2. A rejeição é **por partida**, não por atleta. Nunca rejeite um nome inteiro.
3. Esta tela cobre **apenas Eliminatórias**. A cota da fase final é outro rateio.

---

## 3. Estado atual da lista da FIFA

Conferido em print de resolução cheia. Rodapé: `Page 1 of 1 — Total 8`. A lista está
completa, nada oculto por paginação. Soma: **39 partidas** (~USD 92 mil brutos).

| Atleta | Seleção | Assigned | Veredito | Fundamento |
|---|---|---|---|---|
| ALMADA Thiago | Argentina | 9 | **REJEITAR excedente** | No clube abr/2024–jan/2025. A Argentina só disputou 6 Eliminatórias nessa janela. 9 é aritmeticamente impossível |
| VITINHO | Brasil | 2 | **ACEITAR** | Chile 04/09/25 (suplente não utilizado) e Bolívia 09/09/25 (titular, LD, 61 min). Confirmado no Transfermarkt |
| LUCAS PERRI | Brasil | 6 | **ACEITAR** | Convocado set/2023 no lugar de Bento (Bolívia e Peru), ainda no Botafogo. 6 = as 3 janelas de 2023 |
| ADRYELSON | Brasil | 1 | **ACEITAR + conferir** | Convocado por Diniz em nov/2023. A janela teve 2 jogos — verificar se cabe reivindicar o segundo |
| LOOR Cristhian | Equador | 1 | **CONFERIR data** | Goleiro, no clube desde 2025 (veio do Independiente del Valle p/ o Mundial de Clubes) |
| MONTES Jacob | Nicarágua | 2 | **REJEITAR / investigar** | Não aparece no elenco de 2024 nem no de 2025. Vínculo não confirmado |
| LUIZ HENRIQUE | Brasil | 8 | **ACEITAR** | out/24 + nov/24 + mar/25 + jun/25 = 8. Para exatamente na ida ao Zenit (jul/2025) |
| SAVARINO Jefferson | Venezuela | 10 | **ACEITAR + conferir faltas** | Maior volume. O risco aqui é o inverso: faltar janela |

### Claims (nomes ausentes da lista)

| Atleta | Seleção | Janelas | Prioridade |
|---|---|---|---|
| IGOR JESUS | Brasil | out/2024 (Chile, Peru — titular, marcou na estreia) e nov/2024 (Venezuela, Uruguai) | ALTA |
| ALEX TELLES | Brasil | out/2024 **e set/2025** (relacionado contra Bolívia, não entrou) | ALTA |
| GATITO FERNÁNDEZ | Paraguai | out/2024 e janelas anteriores | ALTA |
| BASTOS | Angola | set e out/2024 + demais janelas CAF | ALTA — calendário CAF a levantar |
| DANILO SANTOS | Brasil | Copa do Mundo 2026, cota da fase final | ALTA — outro rateio |
| SANTI RODRÍGUEZ | Uruguai | set/2025 — não verificado | MÉDIA |
| LUIS SEGOVIA | Equador | 2023–2024 — não verificado | MÉDIA |

### Descartados com fundamento

| Atleta | Motivo |
|---|---|
| JOHN | Convocado out/2025, mas já no Nottingham Forest **e** para amistosos. Dupla desqualificação |
| NIKO HÄMÄLÄINEN | Só esteve no Botafogo em 2022 (empréstimo do QPR até julho). Eliminatórias começaram em set/2023 |
| NAHUEL FERRARESI | Chegou por empréstimo do São Paulo em 09/03/2026, com o ciclo encerrado |
| KADIR BARRÍA | Jogou por nós em 18/11 e 22/11/2025, dentro da janela FIFA — logo não estava com o Panamá. Caps de 2026 são amistosos. Conferir só out/2025 |

### Danilo Santos — cota da fase final

Brasil eliminado pela Noruega nas oitavas em **05/07/2026**. Janela de contagem
estimada: 01/06 a 06/07/2026 ≈ **36 dias**. Piso ≈ USD 180 mil. O valor por dia só é
fechado pela FIFA após o torneio, com base no total de player-days de todos os clubes.

---

## 4. Algoritmo de elegibilidade

Três filtros em cascata. Só é elegível quem passa nos três.

```
1. A competição daquela partida é Eliminatória?
   → Amistoso, Copa América, Nations League e Copa do Mundo NÃO contam,
     mesmo caindo dentro de Data FIFA.
2. A data está dentro da janela de registro do atleta no Botafogo?
   → Fonte da janela: TMS. Transfermarkt é só proxy.
3. O atleta constou da relação daquela partida?
   → "Suplente não utilizado" CONTA. "Fora da relação" não.
```

Janelas das Eliminatórias Sul-Americanas (18 rodadas, set/2023 a set/2025):

| Rodadas | Janela |
|---|---|
| 1–2 | 07–12/09/2023 |
| 3–4 | 12–17/10/2023 |
| 5–6 | 16–21/11/2023 |
| 7–8 | 05–10/09/2024 |
| 9–10 | 10–15/10/2024 |
| 11–12 | 14–19/11/2024 |
| 13–14 | 20–25/03/2025 |
| 15–16 | 04–10/06/2025 |
| 17–18 | 04–09/09/2025 |

CAF (Bastos/Angola), CONCACAF (Montes/Nicarágua, Barría/Panamá) e UEFA seguem
calendários próprios e ainda **não foram levantados**.

---

## 4b. Escopo ampliado — o universo de partidas

Decisão de escopo: em vez de partir dos 8 nomes da FIFA, **montar primeiro o universo
completo de partidas** e só depois cruzar com atletas. Assim o levantamento fica
auditável e nenhum claim é perdido por esquecimento.

O universo é: **todas as partidas de Eliminatórias da Copa 2026 de toda seleção que teve
ao menos um atleta daquela nacionalidade no elenco do Botafogo entre 2022 e 2026.**

O mapa está em `selecoes_escopo.csv`. Resumo:

| Confederação | Seleções em escopo | Partidas por seleção | Período |
|---|---|---|---|
| CONMEBOL | Brasil, Argentina, Uruguai, Paraguai, Equador, Venezuela, Colômbia | 18 cada | 07/09/2023 – 09/09/2025 |
| CAF | Angola, Marrocos (verificar) | ~10 (fase de grupos) | nov/2023 – out/2025 |
| CONCACAF | Nicarágua, Panamá | variável por rodada alcançada | 2024 – nov/2025 |
| UEFA | Finlândia, Espanha | variável | mar/2025 – nov/2025 + repescagem mar/2026 |

**As Eliminatórias Sul-Americanas têm 90 partidas no total** (10 seleções, turno e
returno, 18 rodadas × 5 jogos). Como 7 das 10 seleções estão em escopo, praticamente
todo o torneio precisa ser levantado.

Ressalvas de escopo, todas registradas no CSV:

- **2022 não gera direito.** As Eliminatórias começaram em set/2023. Atletas que só
  passaram pelo clube em 2022 entram no levantamento apenas para descarte documentado
  (caso do Hämäläinen).
- CAF, CONCACAF e UEFA estão marcados `A CONFIRMAR` — o número de partidas depende de
  quão longe cada seleção avançou. **Levantar na fonte oficial, não estimar.**
- El Arouch (nascido na França, elegível por Marrocos) e Chris Ramos (Espanha) entraram
  por completude. Provavelmente sem convocação à seleção principal, mas o descarte
  precisa ser documentado, não presumido.

### Entregável desta etapa

Uma tabela `partidas_universo` com uma linha por partida:

```
selecao | confederacao | competicao | rodada | data | mando | adversario | resultado | fonte
```

E, em cima dela, a tabela `relacoes` com uma linha por `(partida, atleta)`:

```
partida_id | atleta | status_na_sumula | posicao | minutos | clube_detentor | elegivel
```

`status_na_sumula` ∈ {Titular, Suplente utilizado, Suplente não utilizado, Fora da relação}.
Lembre: **suplente não utilizado conta**; fora da relação não.

### Fontes de fixture por confederação

| Confederação | Fonte primária | Alternativa |
|---|---|---|
| CONMEBOL | conmebol.com — hub das Eliminatórias Sul-Americanas | Wikipédia (fixture completo, tabelas limpas) |
| CAF | cafonline.com | Wikipédia |
| CONCACAF | concacaf.com | Wikipédia |
| UEFA | uefa.com | Wikipédia |

Para o fixture (quem jogou contra quem, quando), a Wikipédia é aceitável e fácil de
raspar. Para **relação de atletas por partida**, não é — aí só súmula oficial,
Transfermarkt ou oGol.

---

## 5. Erros já cometidos — não repita

Este projeto acumulou três erros de análise. Todos vieram da mesma causa: inferir
súmula a partir de notícia.

1. **Vitinho, primeira vez.** Concluí "homônimo, rejeitar" porque não achei convocação
   dele em notícia. Estava no elenco e foi convocado.
2. **Vitinho, segunda vez.** Ao achar a convocação de out/2025, concluí "são amistosos,
   rejeitar". Ele também estivera na janela de set/2025, que era Eliminatória. O print
   do Transfermarkt, que separa competição por competição, resolveu.
3. **Lucas Perri.** Chamei os 6 jogos de "erro sistemático" por assumir que eram as
   Eliminatórias de 2024. Ele saiu no fim de 2023 — os 6 são de 2023, quando era nosso.

**Regra derivada:** notícia cobre *convocação* e *estreia*, nunca *relação por partida*.
Não use notícia para decidir elegibilidade. Use para datar e para achar o que procurar.

**Armadilha de homônimo, já confirmada:** o Botafogo teve dois "Vitinho" ao mesmo tempo
— Victor Alexander da Silva (lateral, 23/07/1999) e Vitor da Silveira Rodrigues
(atacante, 14/06/2007). Sempre chaveie por ID + data de nascimento, nunca por nome.

---

## 6. Hierarquia de fontes

| Nível | Fonte | Serve para |
|---|---|---|
| **Prova** | TMS interno + súmula oficial CONMEBOL/CAF/CONCACAF | Único nível que a FIFA aceita |
| **Conferência** | Transfermarkt + oGol | Achar o que investigar; divergência entre as duas é sinal de alerta |
| **Contexto** | Notícia | Datar convocação, explicar cortes e substituições |

Transfermarkt bloqueia acesso automatizado por `robots.txt` — o bloqueio não é técnico,
um navegador real resolve. Wikipédia não serve: as tabelas de elenco não renderizam via
fetch. O arquivo histórico do Fogo na Rede só tem 2024 e 2025.

---

## 7. Artefatos no repositório

| Arquivo | O que é | Status |
|---|---|---|
| `FIFA_Club_Benefits_2026_Botafogo.xlsx` | Planilha mestre: regras, lista FIFA validada, claims, calendário, base de coleta, elencos 2024/2025, lacunas, veredito por atleta | Atual |
| `tm_selecoes.py` | Scraper Playwright, fonte única (Transfermarkt) | Sintaxe validada, **parser não testado contra o site ao vivo** |
| `conferencia_selecoes.py` | Scraper multi-fonte (Transfermarkt + oGol) com reconciliação, guarda anti-homônimo por data de nascimento e aba de divergências | Sintaxe validada, **parsers não testados**. Preferir este |

`conferencia_selecoes.py` só coloca no resumo a partida em que **as duas fontes
concordam**. O restante vai para a aba `Reconciliacao` marcado como `DIVERGENTE` ou
`SÓ EM UMA FONTE` — essa é a fila de conferência na súmula.

### Schema de `atletas.csv`

```csv
atleta,nascimento,url_transfermarkt,url_ogol,registro_inicio,registro_fim
Vitinho,1999-07-23,<url aba "Jogos pela seleção">,<url oGol>,2024-08-01,
```

`registro_fim` vazio = ainda no elenco. Datas em ISO.

### Setup

```bash
pip install playwright pandas openpyxl
playwright install chromium
python conferencia_selecoes.py --debug   # salva HTML em debug_html/
```

`HEADLESS = False` e pausa de 4–9s entre requisições são intencionais. Não reduza.

---

## 8. Backlog priorizado

1. **Testar os parsers.** Rodar com `--debug`, inspecionar o HTML salvo e ajustar
   `extrair_tabelas()`. É o gargalo de tudo abaixo.
2. **Popular `atletas.csv`** com os 8 da lista FIFA + os 7 candidatos a claim, com
   janelas de registro vindas do TMS (pedir ao departamento de registro, não estimar).
3. **Abrir jogo a jogo na plataforma da FIFA.** Clicar no nome abre as partidas
   atribuídas. Sem isso não dá para rejeitar partida específica do Almada.
4. **Levantar calendários CAF e CONCACAF** para Bastos, Montes e Barría.
5. **Verificar os dois pendentes:** Santi Rodríguez (set/2025) e Luis Segovia (2023–24).
6. **Fechar a cota da Copa** do Danilo — confirmar com a FIFA a data exata de início da
   janela de cessão.
7. **Decisão de política, não técnica:** as partidas excedentes do Almada nos favorecem
   financeiramente. A plataforma pede que sejam rejeitadas. Como o clube não vê a ação
   dos outros, o Lyon deve reivindicá-las de qualquer forma. Definir com o jurídico se
   a orientação é corrigir de ofício ou apenas não reivindicar.

---

## 9. Antes de afirmar qualquer coisa

- [ ] A fonte é súmula ou é notícia? Se for notícia, a afirmação é hipótese.
- [ ] O número bate com o máximo possível na janela de registro do atleta?
- [ ] A competição é Eliminatória mesmo, ou é amistoso dentro de Data FIFA?
- [ ] O atleta é o certo — ID e data de nascimento conferidos?
- [ ] Duas fontes independentes concordam?

Quando a resposta a qualquer uma delas for "não sei", diga que não sabe. Neste projeto
o custo de uma afirmação errada já se provou maior que o de uma lacuna assumida.
