#!/usr/bin/env python3
"""
gerar_relatorio_web.py — a versão web do levantamento, para o hub.

Gera `docs/index.html`: página única, autossuficiente, sem nenhuma dependência
externa. Serve tanto para o servidor local do hub (:5066) quanto para GitHub
Pages, e imprime bem em A4.

  python parte2_cessao.py --pdf levantamento_fifa_botafogo.pdf
  python gerar_relatorio_web.py

DECISÕES DE DESENHO
-------------------
A identidade vem do próprio hub, não de fora: fundo de papel quente, títulos em
ouro, tudo em monoespaçada, rótulos em caixa alta espaçada. O que muda aqui é o
corpo de texto, em serifada — o hub é instrumentação, este documento é peça para
o jurídico ler e imprimir.

Cor semântica é separada do ouro de destaque: musgo para o que está provado,
âmbar para o que está em aberto, tijolo para divergência. Assim o estado se lê
antes do número.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

VALOR = 2360
VALOR_DIA_COPA = 5000
DIAS_COPA = 34

SAIDA = Path("docs/index.html")

CSS = """
:root{
  --papel:#f6f4ef; --papel-2:#fffefb; --tinta:#1b1a17; --tinta-2:#4a4740;
  --tinta-3:#7a766c; --ouro:#8a6a12; --ouro-fraco:#f0e7cd; --linha:#ddd9cf;
  --musgo:#2f6b4f; --musgo-fundo:#e9f1ec; --ambar:#9a6508; --ambar-fundo:#fbf3e2;
  --tijolo:#8f3327; --tijolo-fundo:#f8ebe8;
  --total-fundo:#1b1a17; --total-texto:#fffefb; --total-sub:#a8a396;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  --serifa:Charter,"Bitstream Charter","Iowan Old Style","Palatino Linotype",Georgia,serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --papel:#17171a; --papel-2:#1e1e22; --tinta:#e9e6df; --tinta-2:#b3afa5;
    --tinta-3:#87837a; --ouro:#d9ad3c; --ouro-fraco:#3a3218; --linha:#33333a;
    --musgo:#6bbf95; --musgo-fundo:#1b2a23; --ambar:#e0a545; --ambar-fundo:#2c2416;
    --tijolo:#e08a7c; --tijolo-fundo:#2e1e1b;
  --total-fundo:#e9e6df; --total-texto:#17171a; --total-sub:#5c5950;
  }
}
:root[data-theme="dark"]{
  --papel:#17171a; --papel-2:#1e1e22; --tinta:#e9e6df; --tinta-2:#b3afa5;
  --tinta-3:#87837a; --ouro:#d9ad3c; --ouro-fraco:#3a3218; --linha:#33333a;
  --musgo:#6bbf95; --musgo-fundo:#1b2a23; --ambar:#e0a545; --ambar-fundo:#2c2416;
  --tijolo:#e08a7c; --tijolo-fundo:#2e1e1b;
  --total-fundo:#e9e6df; --total-texto:#17171a; --total-sub:#5c5950;
}
:root[data-theme="light"]{
  --papel:#f6f4ef; --papel-2:#fffefb; --tinta:#1b1a17; --tinta-2:#4a4740;
  --tinta-3:#7a766c; --ouro:#8a6a12; --ouro-fraco:#f0e7cd; --linha:#ddd9cf;
  --musgo:#2f6b4f; --musgo-fundo:#e9f1ec; --ambar:#9a6508; --ambar-fundo:#fbf3e2;
  --tijolo:#8f3327; --tijolo-fundo:#f8ebe8;
  --total-fundo:#1b1a17; --total-texto:#fffefb; --total-sub:#a8a396;
}

*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
  font-family:var(--serifa);font-size:16px;line-height:1.62;
  -webkit-font-smoothing:antialiased}
.folha{max-width:1080px;margin:0 auto;padding:40px 24px 88px}
p,li{max-width:68ch}
a{color:var(--ouro);text-underline-offset:2px}
a:focus-visible,button:focus-visible{outline:2px solid var(--ouro);outline-offset:3px}

.rotulo{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--tinta-3)}

header.topo{border-bottom:2px solid var(--tinta);padding-bottom:22px;
  margin-bottom:26px}
header.topo h1{font-family:var(--mono);font-size:clamp(24px,4.4vw,38px);
  line-height:1.12;letter-spacing:-.02em;margin:10px 0 12px;text-wrap:balance}
header.topo h1 em{font-style:normal;color:var(--ouro)}
.meta{font-family:var(--mono);font-size:12px;color:var(--tinta-2);
  display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:4px}

.tiles{display:grid;gap:12px;margin:26px 0;
  grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.tile{background:var(--papel-2);border:1px solid var(--linha);border-radius:2px;
  padding:15px 16px 14px}
.tile .rotulo{display:block;margin-bottom:8px}
.tile .valor{font-family:var(--mono);font-size:30px;font-weight:600;
  letter-spacing:-.03em;font-variant-numeric:tabular-nums;line-height:1}
.tile .abaixo{font-family:var(--mono);font-size:12px;color:var(--tinta-2);
  margin-top:7px;line-height:1.45}
.tile.provado{border-color:var(--musgo);border-left-width:4px}
.tile.provado .valor{color:var(--musgo)}
.tile.aberto{border-color:var(--ambar);border-left-width:4px;background:var(--ambar-fundo)}
.tile.aberto .valor{color:var(--ambar)}
.tile.total{background:var(--total-fundo);border-color:var(--total-fundo)}
.tile.total .valor{color:var(--total-texto)}
.tile.total .rotulo,.tile.total .abaixo{color:var(--total-sub)}

.aviso{border:1px solid var(--tijolo);border-left-width:4px;
  background:var(--tijolo-fundo);border-radius:2px;padding:16px 18px;margin:24px 0}
.aviso h2{font-family:var(--mono);font-size:14px;letter-spacing:.02em;
  text-transform:none;margin:0 0 8px;color:var(--tijolo);border:0;padding:0}
.aviso p{margin:0 0 8px;font-size:15px}
.aviso p:last-child{margin-bottom:0}

.nota{border:1px solid var(--ambar);border-left-width:4px;
  background:var(--ambar-fundo);border-radius:2px;padding:15px 17px;margin:20px 0}
.nota strong{color:var(--ambar)}
.nota p{margin:0}

h2.secao{font-family:var(--mono);font-size:15px;letter-spacing:.03em;
  margin:44px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--tinta);
  display:flex;align-items:baseline;gap:12px}
h2.secao .num{color:var(--ouro);font-size:12px;letter-spacing:.1em}
h3.atleta{font-family:var(--mono);font-size:15px;margin:0 0 3px;
  letter-spacing:-.01em}
h3.atleta .sel{color:var(--ouro);font-weight:400}

.rolagem{overflow-x:auto;margin:14px 0 6px;
  border:1px solid var(--linha);border-radius:2px;background:var(--papel-2)}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:13px;
  min-width:520px}
th{text-align:left;font-size:10px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--tinta-3);font-weight:600;padding:10px 12px;
  border-bottom:1px solid var(--tinta);white-space:nowrap}
td{padding:8px 12px;border-bottom:1px solid var(--linha);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.soma td{border-top:2px solid var(--tinta);border-bottom:0;font-weight:700;
  background:var(--ouro-fraco)}
.dim{color:var(--tinta-3)}
.pos{color:var(--musgo)} .neg{color:var(--tijolo)}

.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;
  white-space:nowrap}
.chip::before{content:"";width:9px;height:9px;border-radius:1px;flex:none}
.chip.titular::before{background:var(--musgo)}
.chip.entrou::before{background:var(--musgo);opacity:.5}
.chip.banco::before{background:transparent;border:1.5px solid var(--musgo)}
.chip.fora::before{background:var(--tijolo);opacity:.55}

.cartao{border:1px solid var(--linha);border-radius:2px;background:var(--papel-2);
  padding:16px 18px;margin:14px 0;break-inside:avoid}
.cartao .linha-topo{display:flex;flex-wrap:wrap;gap:6px 16px;
  align-items:baseline;justify-content:space-between}
.cartao .sub{font-family:var(--mono);font-size:11.5px;color:var(--tinta-2);
  margin-top:4px}
.contagem{font-family:var(--mono);font-size:12px;display:flex;gap:14px;
  flex-wrap:wrap}
.contagem b{font-size:15px;font-variant-numeric:tabular-nums}
.cartao .rolagem{background:transparent;border-color:var(--linha)}

ol.passos{counter-reset:p;list-style:none;padding:0;margin:14px 0}
ol.passos li{counter-increment:p;position:relative;padding-left:34px;
  margin-bottom:13px}
ol.passos li::before{content:counter(p);position:absolute;left:0;top:1px;
  font-family:var(--mono);font-size:11px;color:var(--ouro);
  border:1px solid var(--ouro);border-radius:2px;width:21px;height:21px;
  display:grid;place-items:center;font-variant-numeric:tabular-nums}

footer{margin-top:52px;padding-top:20px;border-top:1px solid var(--linha);
  font-family:var(--mono);font-size:11.5px;color:var(--tinta-3);line-height:1.6}
footer p{max-width:none}

@media print{
  body{background:#fff;font-size:10.5pt}
  .folha{max-width:none;padding:0}
  .tile,.cartao,.rolagem{break-inside:avoid}
  h2.secao{break-after:avoid}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

CHIP = {
    "Titular": ("titular", "Titular"),
    "Suplente utilizado": ("entrou", "Entrou"),
    "Suplente não utilizado": ("banco", "No banco"),
}

ACENTO = {"Nicaragua": "Nicarágua", "Colombia": "Colômbia", "Panama": "Panamá",
          "Bolivia": "Bolívia", "Finlandia": "Finlândia",
          "Trinidad e Tobago": "Trinidad e Tobago"}

PAIS = {"Brazil": "Brasil", "Bolivia": "Bolívia", "Peru": "Peru",
        "Venezuela": "Venezuela", "Uruguay": "Uruguai", "Colombia": "Colômbia",
        "Argentina": "Argentina", "Chile": "Chile", "Paraguay": "Paraguai",
        "Ecuador": "Equador", "Montserrat": "Montserrat", "Belize": "Belize",
        "Nicaragua": "Nicarágua", "Morocco": "Marrocos", "Haiti": "Haiti",
        "Scotland": "Escócia", "Japan": "Japão", "Norway": "Noruega"}


def sel(n): return ACENTO.get(n, n)
def pais(n): return PAIS.get(n, n)
def moeda(v): return f"USD {v:,.0f}".replace(",", ".")
def dia(iso):
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def cartoes_atletas(d: dict) -> str:
    por_nome = {a["nome"]: a for a in d["atletas"]}
    saida = []
    for a in sorted(d["parte1"],
                    key=lambda x: -len([p for p in x["partidas"]
                                        if p["torneio"] == "Eliminatórias"])):
        elim = [p for p in a["partidas"] if p["torneio"] == "Eliminatórias"]
        copa = [p for p in a["partidas"] if p["torneio"] == "Copa"]
        ext = por_nome.get(a["nome"], {})
        ganho = ext.get("ganho_cessao", 0)
        desc = ext.get("desconhecidas", 0)

        linhas = "".join(
            f'<tr><td class="dim">{dia(p["data"])}</td>'
            f'<td>{pais(p["casa"])} <span class="dim">×</span> {pais(p["fora"])}</td>'
            f'<td><span class="chip {CHIP.get(p["status"],("banco",p["status"]))[0]}">'
            f'{CHIP.get(p["status"],("banco",p["status"]))[1]}</span></td>'
            f'<td class="dim">{"Copa" if p["torneio"]=="Copa" else "Eliminatórias"}</td></tr>'
            for p in a["partidas"])

        extras = []
        if ganho:
            extras.append(f'<span>Por cessão <b class="pos">+{ganho}</b></span>')
        if desc:
            extras.append(f'<span class="dim">Janelas sem escalação <b>{desc}</b></span>')

        saida.append(f"""<div class="cartao">
  <div class="linha-topo">
    <div>
      <h3 class="atleta">{a['nome']} <span class="sel">· {sel(a['selecao'])}</span></h3>
      <div class="sub">{a['nome_completo']} · {a['posicao']} ·
        nasc. {dia(a['nascimento'])} · vínculo {a['vinculo_texto']}</div>
    </div>
    <div class="contagem">
      <span>Eliminatórias <b>{len(elim)}</b></span>
      {'<span>Copa <b>' + str(len(copa)) + ' dias em jogo</b></span>' if copa else ''}
      {''.join(extras)}
    </div>
  </div>
  <div class="rolagem"><table><thead><tr>
    <th>Data</th><th>Partida</th><th>Na relação</th><th>Torneio</th>
  </tr></thead><tbody>{linhas}</tbody></table></div>
</div>""")
    return "\n".join(saida)


def construir(d: dict) -> str:
    t, rt = d["totais"], d["recon_totais"]
    sumula, cessao = t["sumula"], t["cessao"]
    nv = d["nao_verificados"]
    nv_p = sum(r["partidas"] for r in nv)
    aberto = t["desconhecidas"] + nv_p
    total_hoje = sumula * VALOR + DIAS_COPA * VALOR_DIA_COPA

    marca_ausente = '<span class="dim">(sem escalação)</span>'
    recon = "".join(
        f'<tr><td>{r["nome"]} {marca_ausente if r["ausente"] else ""}</td>'
        f'<td class="dim">{sel(r["selecao"])}</td>'
        f'<td class="n">{r["fifa"]}</td><td class="n">{r["sumula"]}</td>'
        f'<td class="n {"neg" if r["d_sumula"]<0 else ""}">{r["d_sumula"]:+d}</td>'
        f'<td class="n">{r["cessao"]}</td>'
        f'<td class="n {"neg" if r["d_cessao"]<0 else "pos" if r["d_cessao"]>0 else ""}">'
        f'{r["d_cessao"]:+d}</td></tr>'
        for r in d["reconciliacao"])

    naoverif = "".join(
        f'<tr><td>{r["nome"]}</td><td class="dim">{sel(r["selecao"])}</td>'
        f'<td class="n">{r["janelas"]}</td><td class="n">{r["partidas"]}</td>'
        f'<td class="n">{moeda(r["partidas"]*VALOR)}</td>'
        f'<td class="dim">{r["vinculo"]}</td></tr>'
        for r in nv)

    return f"""<title>Levantamento FIFA — Club Benefits 2026 · Botafogo</title>
<style>{CSS}</style>
<div class="folha">

<header class="topo">
  <div class="rotulo">Botafogo SAF · documento de apoio ao jurídico</div>
  <h1>Levantamento FIFA<br><em>Club Benefits Programme 2026</em></h1>
  <div class="meta">
    <span>Eliminatórias da Copa 2026 e cota da fase final</span>
    <span>·</span>
    <span>escalação oficial do match-centre da FIFA</span>
    <span>·</span>
    <span>atualizado em {date.today().strftime('%d/%m/%Y')}</span>
  </div>
</header>

<div class="aviso">
  <h2>Três totais diferentes estão em circulação</h2>
  <p>O card do hub informa <b>43 jogos</b> (≈{moeda(43*VALOR)}), o cabeçalho do
  PDF informa <b>44</b> ({moeda(44*VALOR)}), e o detalhe jogo a jogo do próprio
  PDF soma <b>{sumula}</b>.</p>
  <p>Como o rateio da FIFA é <b>por jogador × partida</b>, o número correto é
  <b>{sumula}</b> — {moeda(sumula*VALOR)}. As {sumula} linhas estão listadas
  adiante, uma a uma. Contando partidas distintas seriam 36, então nem 43 nem 44
  correspondem a algum critério: são erro de agregação, e devem ser corrigidos
  nas duas telas.</p>
</div>

<div class="tiles">
  <div class="tile provado">
    <span class="rotulo">Eliminatórias · confirmado</span>
    <div class="valor">{sumula}</div>
    <div class="abaixo">{moeda(sumula*VALOR)}<br>escalação oficial, uma a uma</div>
  </div>
  <div class="tile provado">
    <span class="rotulo">Copa · cota da fase final</span>
    <div class="valor">{DIAS_COPA}</div>
    <div class="abaixo">{moeda(DIAS_COPA*VALOR_DIA_COPA)}<br>dias de cessão · Danilo</div>
  </div>
  <div class="tile total">
    <span class="rotulo">Total hoje</span>
    <div class="valor">{moeda(total_hoje).replace('USD ','')}</div>
    <div class="abaixo">USD · os dois rateios somados</div>
  </div>
  <div class="tile aberto">
    <span class="rotulo">Em aberto · teto</span>
    <div class="valor">{aberto}</div>
    <div class="abaixo">até {moeda(aberto*VALOR)}<br>nunca conferido em escalação</div>
  </div>
</div>

<h2 class="secao"><span class="num">01</span> O que este documento responde</h2>

<p>Para cada par <b>atleta × partida</b>, uma resposta defensável a uma pergunta
só: <i>o Botafogo detinha o registro deste atleta na data desta partida de
Eliminatórias, e ele foi cedido para ela?</i></p>

<p>Cada linha adiante tem lastro na <b>escalação oficial do match-centre da
FIFA</b> — a mesma entidade que montou a lista a ser contestada. É o nível de
prova que o programa aceita. O que não tem esse lastro está separado, e
identificado como lacuna, não como descarte.</p>

<div class="nota"><p><strong>Uma ressalva vale para todos os números.</strong>
As janelas de registro vêm da data de transferência publicada em fonte de
conferência, não do registro federativo. <b>O extrato do TMS pode alterar
qualquer linha</b> — inclusive reduzir. A relação de cada partida, essa sim, é
oficial.</p></div>

<h2 class="secao"><span class="num">02</span> O critério: relação de partida ou cessão?</h2>

<p>Este levantamento contou <b>relação de partida</b>. Mas o texto da própria
plataforma da FIFA não fala em escalação — fala em <b>cessão</b>: <i>"players
identified by FIFA as being <b>released by your club</b> for one or more FIFA
World Cup 26 Qualifying Matches"</i>, e <i>"reject any players which you
<b>did not release for the specific match</b>"</i>.</p>

<p>Cedido e relacionado não são a mesma coisa. O atleta que se apresenta, fica à
disposição e não entra na relação de 23 <b>foi cedido</b> — o clube ficou sem
ele durante toda a Data FIFA — mas não aparece em escalação alguma.</p>

<p>Há como testar isso sem depender de interpretação: a FIFA já publicou os
números dela. Basta ver qual critério chega mais perto.</p>

<div class="rolagem"><table><thead><tr>
  <th>Atleta</th><th>Seleção</th><th class="n">FIFA atribuiu</th>
  <th class="n">Relação</th><th class="n">Δ</th>
  <th class="n">Cessão</th><th class="n">Δ</th>
</tr></thead><tbody>{recon}
<tr class="soma"><td colspan="2">Total</td><td class="n">{rt['fifa']}</td>
  <td class="n">{rt['sumula']}</td><td class="n neg">{rt['sumula']-rt['fifa']:+d}</td>
  <td class="n">{rt['cessao']}</td><td class="n neg">{rt['cessao']-rt['fifa']:+d}</td>
</tr></tbody></table></div>

<div class="nota"><p><strong>O critério de cessão reconcilia; o da relação
não.</strong> Medido contra os números da própria FIFA, o critério de relação
erra por {abs(rt['sumula']-rt['fifa'])} partidas; o de cessão, por
{abs(rt['cessao']-rt['fifa'])}. Não é prova do regulamento, mas é o tipo de
convergência que dificilmente acontece por acaso — e aponta na mesma direção do
texto da plataforma.</p></div>

<p><b>Cristhian Loor é a linha que mais fala.</b> A FIFA atribuiu 1 partida a
ele, e nenhum dos dois critérios a encontra: goleiro jovem, cedido, nunca
relacionado. Se a FIFA contasse escalação, ele não estaria na lista. <b>Ele
está.</b> Esse nome sozinho indica que a base dela é outra — e por isso a
partida dele deve ser <b>aceita</b>, não ignorada.</p>

<p>As demais divergências têm causas distintas, e convém não misturá-las:
<b>Luiz Henrique</b> (−2) é <i>data de registro</i>, não critério — saiu para o
Zenit em janeiro de 2025 e a FIFA contou a janela de março; o TMS resolve, e
essa rejeição vale de qualquer forma. <b>Adryelson</b> (+1) e <b>Savarino</b>
(+2) são o efeito da cessão: janelas em que a escalação prova a presença num
jogo, e o outro passa a contar.</p>

<h2 class="secao"><span class="num">03</span> Atletas com partida confirmada</h2>

<p>Cada linha foi conferida na escalação oficial. <b>As três situações contam
igual</b> para o cálculo — titular, quem entrou e quem ficou no banco sem
entrar. Minutos e titularidade são irrelevantes para o rateio.</p>

{cartoes_atletas(d)}

<h2 class="secao"><span class="num">04</span> Atletas nunca conferidos</h2>

<p>Estes estiveram no elenco enquanto a seleção deles disputava Eliminatórias, e
<b>não têm nenhuma escalação conferida</b>. Ausência aqui não é prova de nada: é
lacuna, não descarte.</p>

<div class="rolagem"><table><thead><tr>
  <th>Atleta</th><th>Seleção</th><th class="n">Janelas</th>
  <th class="n">Jogos</th><th class="n">Teto</th><th>Vínculo</th>
</tr></thead><tbody>{naoverif}
<tr class="soma"><td colspan="3">Total</td><td class="n">{nv_p}</td>
  <td class="n">{moeda(nv_p*VALOR)}</td><td></td></tr>
</tbody></table></div>

<div class="nota"><p><strong>Dois nomes pesam mais que os outros.</strong>
<b>Bastos</b> teve as 10 Eliminatórias de Angola dentro do vínculo, e o
levantamento já registrava convocações noticiadas em setembro e outubro de 2024
<b>já como atleta do Botafogo</b>. <b>Kadir Barría</b> tem 8 das 10 do Panamá
dentro da janela — duas de novembro/2025 caem porque ele jogou pelo Botafogo em
18 e 22/11, mas as <b>seis de junho, setembro e outubro nunca foram
conferidas</b>.</p></div>

<p>O teto desta tabela é <b>aritmético, não expectativa</b>. Convocação é decisão
de técnico, não consequência de calendário: o número diz quanto <i>caberia</i>,
não quanto <i>há</i>.</p>

<h2 class="secao"><span class="num">05</span> O que fechar, em ordem</h2>

<ol class="passos">
<li><b>Definir o critério com a FIFA.</b> O Loor é o contraexemplo limpo para
perguntar: <i>por que este atleta consta com 1 partida se não figurou em nenhuma
escalação?</i> A resposta define o método do levantamento inteiro. Vale pedir
junto o regulamento do Club Benefits Programme 2026, que deve definir o período
de cessão com data de início e fim.</li>
<li><b>Corrigir o total</b> para {sumula} jogos nas duas telas — no hub e no PDF.</li>
<li><b>Conferir os {len(nv)} atletas nunca verificados</b>, começando por Bastos
(10 jogos) e Barría (8). São {nv[0]['partidas']+nv[1]['partidas'] if len(nv)>1 else 0}
partidas nos dois primeiros nomes.</li>
<li><b>Pedir as listas de convocação</b> à CBF, FEF, APF, FVF, FPF, FAF e
FEPAFUT. Se o critério for cessão, é essa a prova — não a súmula.</li>
<li><b>Obter o extrato do TMS.</b> É o único documento que fecha o filtro da
data, e foi uma janela estimada errada que quase produziu a rejeição de três
partidas do Almada que não existiam.</li>
</ol>

<div class="nota"><p><strong>Sobre rejeitar.</strong> Se o critério for cessão,
as rejeições ficam inseguras — o 9º jogo do Almada pode ser cessão sem
escalação, e aí não há o que rejeitar. A exceção são os <b>2 jogos excedentes do
Luiz Henrique</b>, que não dependem desta discussão.</p></div>

<footer>
<p>Hierarquia de fontes — <b>prova:</b> escalação oficial do match-centre da FIFA
e extrato do TMS. <b>Conferência:</b> Transfermarkt e oGol, usados para montar
elenco e janela. <b>Contexto:</b> notícia, que data convocação e nunca decide
elegibilidade.</p>
<p style="margin-top:9px">Identidade confirmada por data de nascimento e ID, nunca
por nome — o levantamento já encontrou homônimos. A leitura do critério de cessão
é interpretação do texto da plataforma, <b>não confirmada pela FIFA</b>.</p>
<p style="margin-top:9px">Universo de partidas: 216 jogos de Eliminatórias de 22
seleções, validado nas invariantes de cada confederação. Gerado por
<b>parte2_cessao.py</b> e <b>gerar_relatorio_web.py</b>.</p>
</footer>

</div>"""


def main() -> int:
    d = json.loads(Path("dados/parte2_cessao.json").read_text(encoding="utf-8"))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(construir(d), encoding="utf-8")
    print(f"Gravado: {SAIDA} ({SAIDA.stat().st_size:,} bytes)")
    print(f"  Eliminatórias confirmadas: {d['totais']['sumula']}")
    print(f"  Em aberto: {d['totais']['desconhecidas'] + sum(r['partidas'] for r in d['nao_verificados'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
