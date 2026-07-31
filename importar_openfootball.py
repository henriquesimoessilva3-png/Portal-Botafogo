#!/usr/bin/env python3
"""
importar_openfootball.py — popula partidas_universo a partir de um dataset
público de resultados de seleções.

FONTE E NÍVEL DE CONFIANÇA — leia antes de usar
------------------------------------------------
Fonte: https://github.com/martj42/international_results (`results.csv`),
compilação comunitária de partidas de seleções desde 1872, com o campo
`tournament` separando Eliminatórias de amistoso e de fase final.

Pela hierarquia da seção 6 do CLAUDE.md isto é **nível 2 — CONFERÊNCIA**, não
prova. Não é a CONMEBOL, não é a FIFA. Serve para montar o universo de partidas
e para saber o que procurar. **Não serve como documento de claim.**

O que dá confiança extra: o resultado passa nas invariantes estruturais do
torneio sem nenhum ajuste — exatamente 90 partidas, cada uma das 10 seleções
com 18 jogos, 9 em casa e 9 fora, cada confronto acontecendo 2x, uma partida por
seleção por rodada, e toda data dentro das 9 janelas de Data FIFA que o
CLAUDE.md já dá como CONFIRMADAS. Um dataset errado dificilmente fecharia tudo
isso por acaso. Ainda assim, é conferência, não prova.

POR QUE O CAMPO `tournament` IMPORTA
-------------------------------------
Ele separa `FIFA World Cup qualification` de `African Cup of Nations
qualification`, `UEFA Euro qualification`, `Copa América qualification` e
`Friendly`. É exatamente a distinção que o filtro 1 do algoritmo de
elegibilidade exige, e exatamente onde o parser antigo errava.

USO
---
  python importar_openfootball.py            # baixa, importa e valida
  python importar_openfootball.py --arquivo results.csv   # de um CSV local
"""

from __future__ import annotations

import argparse
import csv
import io
import urllib.request
from datetime import date
from pathlib import Path

from partidas_universo import (
    JANELAS_CONMEBOL,
    Partida,
    gravar_universo,
    id_canonico,
    validar,
)

URL = ("https://raw.githubusercontent.com/martj42/international_results/"
       "master/results.csv")
FONTE = "martj42/international_results (results.csv) — nivel CONFERENCIA"

TORNEIO = "FIFA World Cup qualification"
COMPETICAO = "Eliminatórias da Copa do Mundo FIFA 2026"

CICLO_INICIO = "2023-01-01"
CICLO_FIM = "2026-04-30"    # cobre repescagem de março/2026

# Seleções em escopo, conforme selecoes_escopo.csv. Nome no dataset -> nome do
# projeto. As três CONMEBOL sem atleta do Botafogo (Chile, Peru, Bolívia) entram
# porque são adversárias e porque sem elas o validador não consegue checar as
# invariantes do torneio.
CONMEBOL = {
    "Brazil": "Brasil", "Argentina": "Argentina", "Uruguay": "Uruguai",
    "Paraguay": "Paraguai", "Ecuador": "Equador", "Venezuela": "Venezuela",
    "Colombia": "Colombia", "Chile": "Chile", "Peru": "Peru",
    "Bolivia": "Bolivia",
}

OUTRAS = {
    "Angola": ("Angola", "CAF"),
    "Morocco": ("Marrocos", "CAF"),
    "Nicaragua": ("Nicaragua", "CONCACAF"),
    "Panama": ("Panama", "CONCACAF"),
    "Finland": ("Finlandia", "UEFA"),
    "Spain": ("Espanha", "UEFA"),
}


def baixar(destino: Path | None) -> list[dict]:
    if destino and destino.exists():
        print(f"Lendo {destino}")
        texto = destino.read_text(encoding="utf-8")
    else:
        print(f"Baixando {URL}")
        with urllib.request.urlopen(URL, timeout=120) as r:
            texto = r.read().decode("utf-8")
        print(f"  {len(texto):,} bytes")
    return list(csv.DictReader(io.StringIO(texto)))


def _rodadas_conmebol(partidas: list[dict]) -> dict[str, str]:
    """Deduz o número da rodada de cada partida da CONMEBOL.

    O dataset traz data, não rodada. Mas a estrutura resolve: cada janela de
    Data FIFA tem exatamente 2 rodadas, e dentro de uma rodada cada seleção
    joga uma única vez. Então basta varrer as partidas da janela em ordem de
    data e abrir uma rodada nova assim que uma seleção se repetir.
    """
    rodada_de: dict[str, str] = {}
    numero = 0

    for _, jini, jfim in JANELAS_CONMEBOL:
        na_janela = sorted(
            [p for p in partidas if jini <= date.fromisoformat(p["date"]) <= jfim],
            key=lambda p: p["date"])
        atual: set[str] = set()
        numero += 1
        for p in na_janela:
            casa, fora = p["home_team"], p["away_team"]
            if casa in atual or fora in atual:
                numero += 1
                atual = set()
            atual.update((casa, fora))
            rodada_de[_chave(p)] = str(numero)
    return rodada_de


def _chave(p: dict) -> str:
    return f"{p['date']}|{p['home_team']}|{p['away_team']}"


def importar(brutos: list[dict]) -> tuple[list[Partida], list[str]]:
    notas: list[str] = []
    elim = [r for r in brutos
            if r["tournament"] == TORNEIO
            and CICLO_INICIO <= r["date"] <= CICLO_FIM]
    notas.append(f"{len(elim)} partidas de '{TORNEIO}' no ciclo, em todo o mundo")

    conmebol = [r for r in elim
                if r["home_team"] in CONMEBOL and r["away_team"] in CONMEBOL]
    rodada_de = _rodadas_conmebol(conmebol)

    saida: list[Partida] = []

    # -- CONMEBOL: as duas pontas estão em escopo, gera as duas linhas -------- #
    for r in conmebol:
        casa = CONMEBOL[r["home_team"]]
        fora = CONMEBOL[r["away_team"]]
        pid = id_canonico(casa, fora, r["date"])
        placar = f"{r['home_score']}:{r['away_score']}"
        rodada = rodada_de.get(_chave(r), "")
        for selecao, adversario, mando, res in (
                (casa, fora, "casa", placar),
                (fora, casa, "fora", f"{r['away_score']}:{r['home_score']}")):
            saida.append(Partida(
                partida_id=pid, selecao=selecao, confederacao="CONMEBOL",
                competicao=COMPETICAO, rodada=rodada, data=r["date"],
                mando=mando, adversario=adversario, resultado=res, fonte=FONTE))

    # -- demais confederações: só a linha da seleção em escopo ---------------- #
    # O adversário não entra como linha própria porque não há atleta do Botafogo
    # daquela nacionalidade — o universo é definido pelo elenco, não pelo grupo.
    for r in elim:
        for lado, mando in (("home_team", "casa"), ("away_team", "fora")):
            nome = r[lado]
            if nome not in OUTRAS:
                continue
            selecao, confed = OUTRAS[nome]
            outro = r["away_team"] if lado == "home_team" else r["home_team"]
            gm = r["home_score"] if lado == "home_team" else r["away_score"]
            gs = r["away_score"] if lado == "home_team" else r["home_score"]
            saida.append(Partida(
                partida_id=id_canonico(selecao, outro, r["date"]),
                selecao=selecao, confederacao=confed, competicao=COMPETICAO,
                rodada="", data=r["date"], mando=mando, adversario=outro,
                resultado=f"{gm}:{gs}", fonte=FONTE))

    notas.append("Rodada deduzida por estrutura para a CONMEBOL; em branco nas "
                 "demais confederações, cujo formato ainda não foi conferido "
                 "na fonte oficial.")
    return saida, notas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo", metavar="CSV",
                    help="usa um results.csv local em vez de baixar")
    args = ap.parse_args()

    brutos = baixar(Path(args.arquivo) if args.arquivo else None)
    print(f"  {len(brutos):,} linhas no dataset\n")

    partidas, notas = importar(brutos)
    for n in notas:
        print("  ·", n)

    gravar_universo(partidas)
    print(f"\nGravado dados/partidas_universo.csv — {len(partidas)} linhas, "
          f"{len({p.partida_id for p in partidas})} partidas distintas\n")

    por_conf: dict[str, int] = {}
    for p in partidas:
        por_conf[p.confederacao] = por_conf.get(p.confederacao, 0) + 1
    for c, n in sorted(por_conf.items()):
        print(f"  {c:<10} {n} linhas")

    erros, avisos = validar(partidas)
    print("\nVALIDAÇÃO")
    print("-" * 70)
    for a in avisos:
        print("  aviso:", a)
    for e in erros[:20]:
        print("  ERRO: ", e)
    if not erros:
        print("  Sem erros de integridade — as invariantes do torneio fecham.")
    print()
    print("Nível CONFERÊNCIA, não prova. A súmula oficial continua sendo o")
    print("único documento que a FIFA aceita.")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
