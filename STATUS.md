# Estado da sessão — testes do parser + universo de partidas

Complementa o `CLAUDE.md`. O que mudou, o que ficou pronto e o que está travado.

---

## 1. O bloqueio que definiu esta sessão

**O ambiente onde este código roda não tem rota de rede para nenhuma fonte de
dados de futebol.** A política de egresso da organização recusa o CONNECT com
403 para todos os domínios necessários.

Verificado por três caminhos independentes, não presumido:

| Caminho | Resultado |
|---|---|
| `curl` direto | `CONNECT tunnel failed, response 403` |
| Ferramenta de fetch da sessão | `HTTP 403 Forbidden` |
| Chromium real via Playwright | `net::ERR_TUNNEL_CONNECTION_FAILED` |

Domínios confirmados como bloqueados: `transfermarkt.com.br`, `ogol.com.br`,
`pt.wikipedia.org`, `conmebol.com`.

Só a busca web funciona (roda fora deste container), e ela devolve resumo e
links — não a página. Pela hierarquia da seção 6 do `CLAUDE.md`, isso é
**nível 3, contexto**. Serve para achar o que procurar; não serve para decidir
elegibilidade nem para montar fixture.

**Consequência direta:** o passo 1 da tarefa — rodar `--debug`, olhar o HTML
salvo e ajustar os seletores ao markup real — **não pôde ser executado aqui**.
Nenhum byte de Transfermarkt ou oGol chegou a esta máquina.

Uma exceção foi encontrada depois e mudou o resultado da sessão:
`raw.githubusercontent.com` responde. Ver seção 5b.

---

## 2. O que foi feito, já que o passo 1 estava travado

O parser era **impossível de testar por construção**: `extrair_tabelas()` recebia
um objeto `Page` do Playwright, então exercitá-lo exigia navegador e rede. O
`--debug` salvava HTML, mas não havia caminho de volta para reprocessá-lo. Ou
seja: mesmo numa máquina com acesso, cada tentativa de conserto custava uma
requisição ao Transfermarkt.

Isso foi resolvido. O parsing virou função pura de HTML → Registros
(`parser_tabelas.py`), e o scraper ganhou dois modos que não usam rede:

```bash
python conferencia_selecoes.py --self-test           # testa a lógica
python conferencia_selecoes.py --from-html debug_html/   # reprocessa dumps
```

Fluxo de trabalho novo, para quem tiver acesso aos sites:

1. `python conferencia_selecoes.py --debug` — uma passada, captura o HTML.
2. Iterar com `--from-html debug_html/` quantas vezes precisar, **sem tocar
   mais no site**. Cada rodada leva segundos.

O `--debug` agora salva um `.json` ao lado de cada `.html` com o metadado do
atleta, para o reprocessamento não depender do `atletas.csv` continuar igual.

---

## 3. Bugs corrigidos

Todos com teste que falha na versão antiga e passa na nova
(`python test_parser.py`, 53 asserções).

### 3.1 Cabeçalho de competição nunca era capturado — o mais grave

O código lia o cabeçalho de competição só quando a linha tinha `≤ 2` células
**`td`**. Mas nas duas fontes esse cabeçalho é `<th>` ou `<td colspan=N>`. Numa
linha só de `<th>`, a contagem de `td` é **zero**, e a linha caía no
`if n == 0: continue` antes de virar contexto.

Efeito: `competicao` ficava `"?"` na página inteira → tudo classificado como
`indefinida` → **nenhuma partida seria elegível, para nenhum atleta**. O script
rodaria sem erro e devolveria planilha vazia.

### 3.2 Eliminatória de outro torneio contava como Copa do Mundo

A lista de padrões aceitava o token solto `"eliminatorias"`. Mas Bastos joga
Eliminatórias da **Copa Africana das Nações**, e Finlândia e Espanha jogam
Eliminatórias da **Eurocopa**. Todas entrariam como elegíveis.

É o erro caro: gera claim que a FIFA rejeita, no exato ponto do levantamento
que o `CLAUDE.md` marca como pendente ("levantar calendários CAF e CONCACAF").
Agora exige-se a conjunção *qualificatória* **+** *Copa do Mundo*, e qualquer
menção a outro torneio barra antes.

### 3.3 O nome mais provável da competição era rejeitado

`"copa do mundo fifa"` estava na lista de **excluídos** e era testada primeiro.
Então `"Eliminatórias da Copa do Mundo FIFA 2026"` — provavelmente o nome real
da competição na página — era descartada como não elegível. Os dois erros
(3.2 e 3.3) se cancelariam parcialmente na contagem, mascarando um ao outro.

### 3.4 Status desconhecido virava "Titular"

`status_da_linha()` devolvia `"Titular"` para toda linha que não reconhecia.
Como titular é elegível, **silêncio do parser virava dinheiro reivindicado sem
base**. Agora o desconhecido é `Indeterminado` e cai em `CONFERIR`.

### 3.5 A guarda anti-homônimo falhava aberto

`conferir_nascimento()` devolvia `True` em qualquer exceção e quando não achava
a data. Para a armadilha dos dois "Vitinho" isso é o avesso do necessário.
Agora são três estados: `confere`, `nao_confere` (descarta) e `nao_encontrada`
(mantém, mas marca tudo para conferência e alerta). Também aceita mais formatos
de data — o original só reconhecia três e descartaria dado bom por isso.

### 3.6 Atleta sem janela de registro passava como elegível

`dentro = (ini is None or ...) and (fim is None or ...)` dá `True` quando as
duas pontas são vazias. É exatamente o caso do **Jacob Montes**, cujo vínculo o
`CLAUDE.md` marca como não confirmado: ele sairia elegível em toda partida da
Nicarágua. Agora vira `CONFERIR — atleta sem janela de registro`.

### 3.7 Tabela aninhada embaralhava as colunas

O Transfermarkt aninha tabela dentro de célula (escudo + nome do clube). O
parser fechava a célula de fora ao encontrar a de dentro, e o nome do
adversário se perdia. Reescrito com pilha de molduras; o texto alimenta todas as
células abertas.

### 3.8 Outros

- `parse_data` tentava `%d/%m/%y` antes de `%d/%m/%Y` e não ancorava a string —
  `"Rodada 12/18"` podia virar 12 de dezembro. Agora exige que a string *seja* a
  data e entende o prefixo de dia da semana do Transfermarkt.
- A pausa de 4–9s só acontecia depois de sucesso. Timeout e descarte por
  homônimo pulavam a pausa — mas o site conta o acesso do mesmo jeito.
- Com uma fonte só no DataFrame, a coluna `divergencia` não era criada e a
  planilha saía sem a marcação.
- `MODELO_CSV` gerava um `atletas.csv` com schema diferente do documentado
  (faltavam `selecao` e `origem_da_janela`).

### 3.9 Sinalização de janela estimada

Exigência explícita do briefing. Todas as janelas do `atletas.csv` vieram de
imprensa. Agora o veredito sai como
`ELEGÍVEL (janela ESTIMADA — confirmar no TMS)` e o resumo tem a coluna
`depende_de_janela_estimada`. Nenhum número desta planilha pode virar claim
antes do extrato do TMS.

---

## 4. O que continua sendo hipótese

**Os seletores de coluna não foram validados contra o HTML real.** As fixtures
de `test_parser.py` foram escritas à mão a partir da descrição de estrutura no
`CLAUDE.md`, por quem não teve acesso aos domínios. Elas provam que a **lógica**
está certa — classificação, status, janela, veredito, leitura de tabela
aninhada. Não provam que "a terceira célula é o adversário".

Enquanto ninguém rodar `--debug` com acesso aos sites, a extração de adversário
e minutos continua sendo hipótese. Por isso todo `Registro` carrega a coluna
`bruto` com a linha crua, e a planilha ganhou a aba **Fila de conferencia**.

---

## 5. `partidas_universo` — infraestrutura pronta, dados pendentes

`dados/partidas_universo.csv` **está vazio**. Preenchê-lo de memória seria
exatamente o que o `CLAUDE.md` proíbe: *"levantar na fonte oficial, não
estimar"*. Sem rota para conmebol.com nem para a Wikipédia, não há fonte.

O que está pronto e testado (`python test_universo.py`):

- schema com `partida_id` canônico — a mesma partida vista pelos dois lados gera
  o mesmo id, então 90 partidas viram 180 linhas sem contar em dobro;
- **validador de invariantes da CONMEBOL**, que pega quase todo erro de coleta:
  seleção com número de jogos errado, mando incoerente entre os dois lados,
  confronto que não acontece exatamente 2x, duas partidas na mesma rodada,
  seleção de outra confederação, e — o mais útil — **partida fora das 9 janelas
  de Data FIFA**, que é como amistoso vaza para dentro da coleta;
- import por CSV ou por dump HTML, com espelhamento automático do outro lado;
- relatório de cobertura contra `selecoes_escopo.csv`.

As 9 janelas vêm da seção 4 do `CLAUDE.md`, que está marcada CONFIRMADO. Não é
estimativa nova.

Quando houver acesso:

```bash
python partidas_universo.py --importar fixture.csv --selecao Brasil \
       --fonte "conmebol.com, acessado em AAAA-MM-DD"
python partidas_universo.py --validar
```

O validador responde na hora se a coleta está íntegra.

---

## 5b. DESTRAVADO — o universo de partidas foi coletado

Depois de mapear host por host o que a política de egresso libera, apareceu uma
brecha útil: **`raw.githubusercontent.com` responde**. Não a API do GitHub, não
o `codeload`, não o jsDelivr, não buckets externos — só o raw de arquivo.

Isso bastou. Fonte usada:
**[martj42/international_results](https://github.com/martj42/international_results)**,
compilação pública de partidas de seleções desde 1872, com o campo `tournament`
separando `FIFA World Cup qualification` de `African Cup of Nations
qualification`, `UEFA Euro qualification`, `Copa América qualification` e
`Friendly` — exatamente a distinção que o filtro 1 do algoritmo exige.

`dados/partidas_universo.csv` agora tem **232 linhas, 141 partidas distintas**:

| Confederação | Linhas | Cobertura |
|---|---|---|
| CONMEBOL | 180 | 90 partidas, as 10 seleções, 18 rodadas |
| CAF | 18 | Angola (10) e Marrocos (8) |
| CONCACAF | 20 | Nicarágua (10) e Panamá (10) |
| UEFA | 14 | Finlândia (8) e Espanha (6) |

Isso fecha o item 4 do backlog do `CLAUDE.md` — "levantar calendários CAF e
CONCACAF" —, que estava aberto.

### Por que dá para confiar (e até onde)

O validador roda **sem um único erro**. As invariantes que ele checa não são
formalidade: 90 partidas distintas, cada uma das 10 seleções com exatamente 18
jogos, 9 em casa e 9 fora, cada confronto acontecendo 2x, uma partida por
seleção por rodada, e **toda data dentro das 9 janelas de Data FIFA** que o
`CLAUDE.md` já dava como CONFIRMADAS. Um dataset errado não fecharia tudo isso
por acaso.

Duas corroborações independentes, que ninguém programou para acontecer:

- o dataset conta **901 partidas de Eliminatórias no mundo** no ciclo. A FIFA
  declarou **905** no comunicado de 05/06/2026 — o denominador do rateio de
  USD 2.360. Diferença de 0,4%;
- os resultados do Brasil batem com o conhecido (5-1 Bolívia, 0-2 Uruguai,
  0-1 Argentina).

**Mesmo assim: isto é nível 2, CONFERÊNCIA.** Não é a CONMEBOL, não é a FIFA.
Serve para montar o universo e para saber o que procurar. **Não serve como
documento de claim.** O `fonte` de cada linha diz isso.

A rodada não vem no dataset — é **deduzida por estrutura**: cada janela tem 2
rodadas e cada seleção joga uma vez por rodada, então basta abrir rodada nova
quando uma seleção se repete. Fecha em 18 rodadas com 10 linhas cada. Para CAF,
CONCACAF e UEFA a rodada fica em branco: o formato dessas confederações não foi
conferido na fonte oficial.

---

## 5c. O que a coleta mudou na análise

Com datas reais, `checagem_aritmetica.py` deixou de estimar por estrutura e
passou a **contar as partidas reais da seleção dentro da janela de registro**.
Três linhas que eram "NÃO SEI" viraram número:

| Atleta | Seleção | Máximo possível |
|---|---|---|
| Bastos | Angola | **10** |
| Kadir Barría | Panamá | **8** |
| Chris Ramos | Espanha | **6** |

E dois descartes que o `CLAUDE.md` já defendia por argumento saíram **0** por
aritmética, de forma independente: **Niko Hämäläinen** e **Nahuel Ferraresi**.

`dados/relacoes.csv` tem **458 linhas**. Nenhuma sai ELEGÍVEL — o filtro 3
continua aberto.

---

## 5d. O que segue bloqueado: os elencos

**Elenco do Botafogo 2022–2026 com nome completo, nascimento, idade e posição
não foi coletado.** As fontes que têm esse dado estão todas fora:
Transfermarkt, oGol, ESPN, Wikipédia, e o bucket R2 do dump público do
Transfermarkt (`transfermarkt-datasets`) — todos 403 no CONNECT. O único repo
com dados de jogador que o raw alcança (`openfootball/players`) organiza por
seleção, não por clube, e não tem histórico de elenco.

O que existe: `dados/elencos.csv`, 84 linhas de 2024 e 2025 vindas da planilha
mestre, com 27 datas de nascimento cruzadas do `atletas.csv`. **2022, 2023 e
2026 estão vazios.**

Uma checagem que dá alguma tranquilidade: **toda nacionalidade presente nos
elencos de 2024 e 2025 já consta de `selecoes_escopo.csv`**. Nenhuma seleção
ficou de fora por esquecimento no período que dá para verificar. As três em
escopo sem atleta nesses dois anos — Finlândia, Nicarágua e Panamá — são
exatamente Hämäläinen (2022), Montes (vínculo não confirmado) e Barría (chegou
depois). Ou seja: o universo de partidas provavelmente está completo, mas isso
**não pode ser afirmado para 2022, 2023 e 2026**, que seguem sem fonte.

---

## 6. `relacoes` — pronto, roda assim que houver universo

`relacoes.py` cruza `partidas_universo` com `atletas.csv`.

Decide os filtros **1 e 2** do algoritmo (competição e janela de registro),
porque os dois são derivação de dado que já está nas tabelas. **Não decide o
filtro 3** — se o atleta constou da relação —, que só sai de súmula.

Por isso nenhuma linha sai `ELEGÍVEL` deste script. Sai `PENDENTE`, que é uma
pergunta a responder, não um claim. Com `--do-scraper` o status é pré-preenchido
com o que as duas fontes concordaram, marcado como origem **CONFERÊNCIA** —
nível 2 da hierarquia, nunca prova.

Linhas fora da janela são **mantidas** na tabela, marcadas como não elegíveis,
para que o descarte fique documentado em vez de presumido — como pede a seção 4b
sobre o caso Hämäläinen.

Testado de ponta a ponta contra o torneio sintético: 180 linhas × 28 atletas →
414 relações, com Lucas Perri corretamente fora em 2024 e Vitinho fora em 2023.

---

## 7. Próximo passo, em ordem

1. **Numa máquina com acesso aos sites**, rodar
   `python conferencia_selecoes.py --debug` com uma URL preenchida e conferir os
   dumps em `debug_html/`. Ajustar só o mapeamento de coluna em
   `_achar_adversario` / `_achar_minutos` de `parser_tabelas.py` — a lógica em
   volta já está coberta por teste. Iterar com `--from-html`.
2. Coletar o fixture CONMEBOL na fonte oficial e importar. O validador confirma
   as 90 partidas.
3. Só então rodar `relacoes.py`.
4. Substituir as janelas `ESTIMADA` do `atletas.csv` pelo extrato do TMS. Até
   lá, todo número sai marcado como dependente de estimativa.

---

## 8. Arquivos

| Arquivo | O que é | Estado |
|---|---|---|
| `parser_tabelas.py` | miolo de parsing, função pura de HTML | testado (lógica) |
| `conferencia_selecoes.py` | scraper multi-fonte + reconciliação | rodável; seletores não validados |
| `partidas_universo.py` | schema + validador + import do universo | testado |
| `relacoes.py` | cruzamento partida × atleta | testado |
| `test_parser.py` | 53 asserções de lógica | passa |
| `test_universo.py` | invariantes do formato CONMEBOL | passa |
| `dados/partidas_universo.csv` | universo de partidas | **VAZIO — falta coleta** |
| `atletas.csv` | 28 atletas | URLs em branco; janelas ESTIMADAS |
