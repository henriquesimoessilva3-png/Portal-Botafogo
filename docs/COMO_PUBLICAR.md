# Como pôr o Levantamento FIFA online no hub

O card `LEVANTAMENTO FIFA` do hub aponta para `:5066` e está **OFFLINE**. Este
diretório tem a página que fica nesse endereço.

`docs/index.html` é autossuficiente — um arquivo só, sem CSS externo, sem fonte
remota, sem JavaScript. Serve em qualquer lugar que entregue arquivo estático,
e imprime em A4 (9 páginas) direto do navegador.

---

## 1. Subir em `:5066`

Da raiz do repositório:

```bash
python3 -m http.server 5066 --directory docs
```

O card fica ONLINE e o botão **RELATÓRIO PARA O JURÍDICO** abre
`http://localhost:5066`.

Para subir junto com o resto do hub, é a mesma receita dos outros cards — um
servidor estático apontando para `docs/`. Não há build, não há dependência.

## 2. Versão online, para mandar por fora

Já publicada, no mesmo padrão do card que tem "VERSÃO ONLINE":

<https://claude.ai/code/artifact/750e7eb0-2ead-4ff9-a231-babe27409601>

Nasce privada — precisa ser compartilhada pelo menu da própria página para a
Tamires abrir. Serve para mandar link em vez de anexar PDF.

Quando o repositório tiver branch padrão, `docs/` também funciona direto no
GitHub Pages, sem nenhuma alteração.

## 3. Atualizar o texto do card

Os números do card estão **desatualizados** e divergem do documento. Hoje ele diz
`43 elegíveis (~USD 101 mil)`. O correto é:

```
Club Benefits 2026 — quais atletas o clube cedeu para
Eliminatórias e Copa, partida a partida

264 pares fechados contra o match-centre · 49 elegíveis
(USD 115.640) + cota da Copa (USD 170.000) · 170 partidas
ainda em aberto
```

**Por que 49 e não 43 nem 44.** O rateio da FIFA é por *jogador × partida*. O
detalhe jogo a jogo do levantamento tem 49 linhas, e os contadores por atleta
somam 49. Contando partidas distintas seriam 36. Nem 43 nem 44 correspondem a
algum critério — são erro de agregação, e estão em duas telas diferentes.

Vale trocar também o rótulo do botão de `RELATÓRIO PARA O JURÍDICO` para algo que
diga o estado, já que o documento agora tem uma pendência aberta em destaque:
sugestão, **`RELATÓRIO · 3 PENDÊNCIAS`**.

## 4. Regerar depois de qualquer mudança

```bash
python parte2_cessao.py --pdf levantamento_fifa_botafogo.pdf
python gerar_relatorio_web.py
```

O primeiro relê a Parte 1 do PDF e recalcula a visão por cessão; o segundo
reescreve `docs/index.html`. Os dois são determinísticos: mesma entrada, mesma
saída.

Para regerar o PDF completo (Parte 1 + Parte 2):

```bash
python gerar_parte2_pdf.py --parte1 levantamento_fifa_botafogo.pdf
```

---

## O que a página mostra

| Bloco | Conteúdo |
|---|---|
| Aviso de topo | os três totais divergentes, e qual é o certo |
| Números | 49 confirmadas · 34 dias de Copa · USD 285.640 · 170 em aberto |
| §2 | o critério — relação de partida ou cessão — com a reconciliação contra a lista da FIFA |
| §3 | os 12 atletas, jogo a jogo, com a situação na relação |
| §4 | os 14 nunca conferidos, com Bastos e Barría na frente |
| §5 | o que fechar, em ordem |

A página distingue, o tempo todo, **o que está provado** do **que está em
aberto**. Nada de teto aritmético aparece somado ao confirmado.
