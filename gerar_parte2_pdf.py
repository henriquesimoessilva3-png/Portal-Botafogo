#!/usr/bin/env python3
"""
gerar_parte2_pdf.py — monta a Parte 2 do levantamento e junta ao PDF original.

Lê `dados/parte2_cessao.json` (produzido por `parte2_cessao.py`), gera um HTML
com estilo de impressão A4, renderiza com o Chromium do Playwright e concatena
ao PDF da Parte 1.

  python parte2_cessao.py --pdf levantamento_fifa_botafogo.pdf
  python gerar_parte2_pdf.py --parte1 levantamento_fifa_botafogo.pdf

Saída: `levantamento_fifa_botafogo_completo.pdf`
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

VALOR = 2360
VALOR_DIA_COPA = 5000

CSS = """
@page { size: A4; margin: 14mm 13mm 12mm 13mm; }
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
       font-size: 9.2pt; line-height: 1.42; color: #17181c; margin: 0; }
h1 { font-size: 16pt; margin: 0 0 2px; letter-spacing: -.3px; }
h2 { font-size: 11pt; margin: 20px 0 7px; padding-bottom: 4px;
     border-bottom: 1.5px solid #17181c; letter-spacing: -.2px; }
h3 { font-size: 9.6pt; margin: 14px 0 5px; color: #17181c; }
.sub { color: #5d6068; font-size: 8pt; margin-bottom: 14px; }
.caixas { display: flex; gap: 8px; margin: 12px 0 4px; }
.caixa { flex: 1; border: 1px solid #d6d8de; border-radius: 3px;
         padding: 9px 10px; }
.caixa .rot { font-size: 6.8pt; letter-spacing: .9px; text-transform: uppercase;
              color: #6b6e76; }
.caixa .num { font-size: 15pt; font-weight: 700; margin: 2px 0 1px;
              letter-spacing: -.5px; }
.caixa .det { font-size: 7.4pt; color: #5d6068; line-height: 1.32; }
.caixa.forte { background: #17181c; border-color: #17181c; }
.caixa.forte .rot, .caixa.forte .det { color: #b9bcc4; }
.caixa.forte .num { color: #fff; }
.caixa.aberta { border-color: #b8860b; background: #fdfaf2; }
.caixa.aberta .num { color: #8a6508; }
table { width: 100%; border-collapse: collapse; margin: 7px 0 4px;
        font-size: 8.3pt; }
th { text-align: left; font-size: 6.9pt; letter-spacing: .7px;
     text-transform: uppercase; color: #6b6e76; font-weight: 600;
     border-bottom: 1px solid #17181c; padding: 4px 5px; }
td { padding: 3.6px 5px; border-bottom: .5px solid #e6e7eb;
     vertical-align: top; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
tr.tot td { border-top: 1.2px solid #17181c; border-bottom: none;
            font-weight: 700; padding-top: 5px; }
.nome { font-weight: 600; }
.dim { color: #6b6e76; }
blockquote { margin: 9px 0; padding: 9px 12px; background: #f5f6f8;
             border-left: 3px solid #9a9da5; font-size: 8.4pt;
             color: #2c2e34; }
blockquote p { margin: 0 0 5px; } blockquote p:last-child { margin: 0; }
.nota { font-size: 7.7pt; color: #5d6068; margin: 7px 0; }
.alerta { border: 1px solid #b8860b; background: #fdfaf2; border-radius: 3px;
          padding: 9px 11px; margin: 10px 0; font-size: 8.4pt; }
.alerta b { color: #8a6508; }
ol, ul { margin: 6px 0 6px 16px; padding: 0; }
li { margin-bottom: 3.5px; }
.rodape { position: fixed; bottom: -8mm; left: 0; right: 0;
          font-size: 6.8pt; color: #8b8e96;
          border-top: .5px solid #e6e7eb; padding-top: 3px; }
.quebra { page-break-before: always; }
.evita { page-break-inside: avoid; }
"""


# Os nomes de seleção vêm do partidas_universo sem acento, por serem chave.
# No documento eles são texto para o jurídico ler, não chave.
ACENTO = {"Nicaragua": "Nicarágua", "Colombia": "Colômbia", "Panama": "Panamá",
          "Bolivia": "Bolívia", "Espanha": "Espanha", "Finlandia": "Finlândia",
          "Belgica": "Bélgica", "Japao": "Japão", "Italia": "Itália",
          "Emirados Arabes Unidos": "Emirados Árabes Unidos"}


def sel(nome: str) -> str:
    return ACENTO.get(nome, nome)


def moeda(n: float) -> str:
    return f"USD {n:,.0f}".replace(",", ".")


def construir_html(d: dict) -> str:
    t = d["totais"]
    sumula = t["sumula"]
    cessao = t["cessao"]
    desconhecidas = t["desconhecidas"]
    nv = d["nao_verificados"]
    nv_partidas = sum(r["partidas"] for r in nv)
    aberto = desconhecidas + nv_partidas

    linhas_atletas = "\n".join(
        f"""<tr>
          <td class="nome">{a['nome']}</td>
          <td class="dim">{sel(a["selecao"])}</td>
          <td class="n">{a['sumula']}</td>
          <td class="n">{'+' + str(a['ganho_cessao']) if a['ganho_cessao'] else '—'}</td>
          <td class="n">{a['sumula'] + a['ganho_cessao']}</td>
          <td class="n">{a['desconhecidas'] or '—'}</td>
        </tr>"""
        for a in d["atletas"] if a["sumula"] or a["ganho_cessao"] or a["desconhecidas"])

    linhas_nv = "\n".join(
        f"""<tr>
          <td class="nome">{r['nome']}</td>
          <td class="dim">{sel(r["selecao"])}</td>
          <td class="n">{r['janelas']}</td>
          <td class="n">{r['partidas']}</td>
          <td class="n">{moeda(r['partidas'] * VALOR)}</td>
          <td class="dim" style="font-size:7.6pt">{r['vinculo']}</td>
        </tr>"""
        for r in nv)

    # detalhe por janela dos atletas que ganham com o critério de cessão
    ganhadores = [a for a in d["atletas"] if a["ganho_cessao"]]
    blocos = []
    for a in ganhadores:
        js = "\n".join(
            f"""<tr>
              <td>{j['rotulo']}</td>
              <td class="n">{j['partidas']}</td>
              <td class="n">{j['confirmadas']}</td>
              <td class="n">{'+' + str(j['ganho']) if j['ganho'] else '—'}</td>
              <td class="dim" style="font-size:7.6pt">{j['situacao']}</td>
            </tr>"""
            for j in a["janelas"] if j["confirmadas"] or j["ganho"])
        blocos.append(f"""<div class="evita">
          <h3>{a['nome']} · {sel(a['selecao'])} <span class="dim"
              style="font-weight:400">— {a['sumula']} pela súmula,
              {a['sumula'] + a['ganho_cessao']} pela cessão</span></h3>
          <table><thead><tr>
            <th>Janela de Data FIFA</th><th class="n">Jogos</th>
            <th class="n">Na escalação</th><th class="n">Acresce</th>
            <th>Por quê</th>
          </tr></thead><tbody>{js}</tbody></table></div>""")

    return f"""<style>{CSS}</style>
<div class="rodape">Levantamento FIFA — Botafogo · Parte 2: a visão por cessão</div>

<h1>Parte 2 — a visão por cessão</h1>
<div class="sub">Complementa a Parte 1. A Parte 1 conta <b>relação de partida</b>,
apurada na escalação oficial da FIFA. Esta parte pergunta se o critério do
programa não é outro — <b>cessão</b> — e mede quanto isso muda.</div>

<div class="caixas">
  <div class="caixa forte">
    <div class="rot">Parte 1 · critério súmula</div>
    <div class="num">{sumula}</div>
    <div class="det">{moeda(sumula * VALOR)}<br>partidas com escalação
    oficial confirmada</div>
  </div>
  <div class="caixa">
    <div class="rot">Critério cessão · já provado</div>
    <div class="num">{cessao}</div>
    <div class="det">{moeda(cessao * VALOR)}<br>+{cessao - sumula} partidas,
    {moeda((cessao - sumula) * VALOR)} a mais</div>
  </div>
  <div class="caixa aberta">
    <div class="rot">Em aberto · teto aritmético</div>
    <div class="num">{aberto}</div>
    <div class="det">até {moeda(aberto * VALOR)}<br>nunca conferido em
    escalação nenhuma</div>
  </div>
</div>

<h2>1. O critério do programa pode não ser o da súmula</h2>

<p>A Parte 1 respondeu à pergunta <i>"o atleta figurou na escalação oficial
daquela partida?"</i>. Mas o texto da própria plataforma da FIFA não fala em
escalação. Fala em <b>cessão</b>:</p>

<blockquote>
<p>"players … identified by FIFA as being <b>released by your club</b> for one or
more FIFA World Cup 26 Qualifying Matches, … prepared using data from the
<b>FIFA Transfer Matching System and national registration systems</b>"</p>
<p>"Reject any players … which you <b>did not release for the specific
match</b>"</p>
</blockquote>

<p><b>Cedido e relacionado não são a mesma coisa.</b> O atleta convocado que se
apresenta, fica à disposição da seleção e não entra na relação de 23 foi cedido
— o clube ficou sem ele durante toda a Data FIFA — mas não aparece em escalação
alguma. Pelo critério da súmula ele vale zero; pelo critério da cessão, vale a
janela inteira.</p>

<div class="alerta">
<b>A evidência de que o critério é cessão está na própria lista da FIFA.</b>
A FIFA atribuiu <b>1 partida a Cristhian Loor</b>. A conferência de escalação
oficial, feita na Parte 1, encontrou <b>zero</b>. Se a base da FIFA fosse
escalação, ela não teria atribuído nada — está contando outra coisa, e o texto
dela diz qual. O mesmo padrão aparece em <b>Thiago Almada: FIFA 9, escalação
8</b>. Nos dois casos em que o número da FIFA diverge sem explicação de janela
de registro, <b>a FIFA é maior</b>. É exatamente o que se espera se ela conta
cessão e a Parte 1 conta súmula.
</div>

<h2>2. Como esta parte calcula — e o que ela não faz</h2>

<p>A regra usada aqui é conservadora e ancorada em prova, não em suposição:</p>

<blockquote><p>Se a escalação oficial confirma o atleta em <b>pelo menos uma</b>
partida de uma janela de Data FIFA, então ele estava cedido naquela janela — e,
pelo critério de cessão, <b>todas</b> as partidas daquela janela contam.</p>
</blockquote>

<p>Isso não é estimativa: figurar numa escalação prova a cessão da janela
inteira. O que fica de fora é a janela em que o atleta foi cedido e não entrou
em nenhuma relação. Essa continua <b>desconhecida</b>, e está listada como tal —
só a convocação oficial da federação resolve.</p>

<p class="nota">Por isso a coluna "em aberto" é <b>teto aritmético</b>, não
expectativa. Convocação é decisão de técnico, não consequência de calendário.
O número diz quanto <i>caberia</i>, não quanto <i>há</i>.</p>

<h2>3. Efeito por atleta</h2>

<table><thead><tr>
  <th>Atleta</th><th>Seleção</th>
  <th class="n">Súmula</th><th class="n">Acresce</th>
  <th class="n">Cessão</th><th class="n">Janelas sem escalação</th>
</tr></thead><tbody>
{linhas_atletas}
<tr class="tot">
  <td colspan="2">TOTAL</td>
  <td class="n">{sumula}</td><td class="n">+{cessao - sumula}</td>
  <td class="n">{cessao}</td><td class="n">{desconhecidas}</td>
</tr>
</tbody></table>

<p class="nota">"Janelas sem escalação" são partidas de janelas em que o atleta
estava sob contrato e a seleção jogou, mas ele não figurou em nenhuma relação.
Não são reivindicáveis hoje, e também não estão descartadas: faltam as listas de
convocação.</p>

{"".join(blocos)}

<div class="quebra"></div>

<h2>4. Correção aritmética da Parte 1</h2>

<p>O cabeçalho da Parte 1 informa <b>44 jogos · {moeda(44 * VALOR)}</b>. Mas as
linhas de detalhe do próprio documento somam <b>{sumula}</b>, e os contadores por
atleta ("10 em Eliminatórias", "8 em Eliminatórias" …) também somam
<b>{sumula}</b>.</p>

<p>Como o rateio é <b>por jogador × partida</b>, o número correto é
<b>{sumula}</b> — <b>{moeda(sumula * VALOR)}</b>. O cabeçalho subestima em
<b>{moeda((sumula - 44) * VALOR)}</b>. (Contando partidas distintas seriam 36;
44 não corresponde a nenhum dos dois critérios, o que sugere erro de agregação
no gerador.)</p>

<table><thead><tr>
  <th>Bloco</th><th class="n">Unidades</th><th class="n">Valor</th>
</tr></thead><tbody>
<tr><td>Eliminatórias — critério súmula (corrigido)</td>
    <td class="n">{sumula} jogos</td><td class="n">{moeda(sumula * VALOR)}</td></tr>
<tr><td>Copa do Mundo — cota da fase final (Danilo)</td>
    <td class="n">{t['copa_dias']} dias</td>
    <td class="n">{moeda(t['copa_dias'] * VALOR_DIA_COPA)}</td></tr>
<tr class="tot"><td>TOTAL corrigido, critério súmula</td><td class="n"></td>
    <td class="n">{moeda(sumula * VALOR + t['copa_dias'] * VALOR_DIA_COPA)}</td></tr>
</tbody></table>

<h2>5. Atletas nunca conferidos</h2>

<p>Estes atletas estiveram no elenco enquanto a seleção deles disputava
Eliminatórias, e <b>não aparecem na Parte 1</b>. Ausência aqui não é prova de
nada: nenhum deles foi verificado em escalação. É lacuna, não descarte.</p>

<table><thead><tr>
  <th>Atleta</th><th>Seleção</th><th class="n">Janelas</th>
  <th class="n">Jogos</th><th class="n">Teto</th><th>Vínculo</th>
</tr></thead><tbody>
{linhas_nv}
<tr class="tot"><td colspan="3">TOTAL</td>
  <td class="n">{nv_partidas}</td>
  <td class="n">{moeda(nv_partidas * VALOR)}</td><td></td></tr>
</tbody></table>

<div class="alerta">
<b>Dois nomes pesam mais que os outros.</b> <b>Bastos</b> teve as
<b>10 Eliminatórias de Angola</b> dentro do vínculo, e o levantamento interno já
registrava convocações noticiadas por Angola em setembro e outubro de 2024,
<b>já como atleta do Botafogo</b>. <b>Kadir Barría</b> tem 8 das 10 do Panamá
dentro da janela; duas de novembro/2025 caem porque ele jogou pelo Botafogo em
18 e 22/11, mas as <b>seis de junho, setembro e outubro nunca foram
conferidas</b>.
</div>

<p class="nota">Todos os vínculos desta tabela vêm de fonte de conferência, não
do TMS, e estão marcados como estimados. O extrato do TMS pode alterar qualquer
linha — inclusive reduzir.</p>

<h2>6. O que fechar, em ordem</h2>

<ol>
<li><b>Definir o critério com a FIFA.</b> O Loor é o contraexemplo limpo para
perguntar: <i>por que este atleta consta com 1 partida se não figurou em nenhuma
escalação?</i> A resposta define o método do levantamento inteiro. Vale pedir
junto o regulamento do Club Benefits Programme 2026, que deve definir
<i>release period</i> com data de início e fim.</li>
<li><b>Corrigir o total da Parte 1</b> de 44 para {sumula} jogos.</li>
<li><b>Conferir os 14 atletas nunca verificados</b>, começando por Bastos (10
jogos) e Barría (8).</li>
<li><b>Pedir as listas de convocação</b> à CBF, FEF, APF, FVF, FPF, FAF e
FEPAFUT. Se o critério for cessão, é essa a prova — não a súmula.</li>
<li><b>Obter o extrato do TMS.</b> Todas as janelas de registro deste
levantamento vêm de fonte de conferência. É o único documento que fecha o
filtro da data.</li>
</ol>

<div class="alerta">
<b>Sobre rejeitar.</b> Se o critério for cessão, as rejeições ficam inseguras.
O 9º jogo do Almada pode ser cessão sem escalação — e aí não há o que rejeitar.
<b>A exceção são os 2 jogos excedentes do Luiz Henrique</b>, que não dependem
desta discussão: ele saiu para o Zenit em janeiro de 2025 e a FIFA contou a
janela de março. Isso é data de registro, e o TMS resolve.
</div>

<p class="nota" style="margin-top:14px">Parte 2 gerada por
<b>parte2_cessao.py</b> e <b>gerar_parte2_pdf.py</b>, sobre os dados da Parte 1
e a tabela <b>partidas_universo</b> (216 partidas de Eliminatórias, 22 seleções,
validada nas invariantes de cada confederação). A leitura do critério de cessão
é interpretação do texto da plataforma, <b>não confirmada pela FIFA</b>.</p>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default="dados/parte2_cessao.json")
    ap.add_argument("--parte1", required=True)
    ap.add_argument("--saida", default="levantamento_fifa_botafogo_completo.pdf")
    args = ap.parse_args()

    d = json.loads(Path(args.dados).read_text(encoding="utf-8"))
    html = construir_html(d)
    Path("dados/parte2.html").write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright
    exe = os.environ.get("CHROME_PATH")
    p2 = Path("dados/parte2.pdf")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True,
                                 **({"executable_path": exe} if exe else {}))
        pg = nav.new_page()
        pg.set_content(html, wait_until="load")
        pg.pdf(path=str(p2), format="A4", print_background=True,
               margin={"top": "14mm", "bottom": "12mm",
                       "left": "13mm", "right": "13mm"})
        nav.close()

    from pypdf import PdfWriter
    w = PdfWriter()
    w.append(args.parte1)
    w.append(str(p2))
    with open(args.saida, "wb") as fh:
        w.write(fh)
    print(f"Parte 2: {p2}")
    print(f"Documento completo: {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
