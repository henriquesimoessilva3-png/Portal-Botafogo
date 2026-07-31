#!/usr/bin/env python3
"""
checagem_aritmetica.py — quantas Eliminatórias cada atleta PODERIA ter jogado.

POR QUE ISTO EXISTE
-------------------
O veredito do Almada na aba 2 da planilha ("9 é aritmeticamente impossível") é
o argumento mais forte do levantamento inteiro, porque não depende de súmula,
de notícia nem de scraper: é contagem. A Argentina disputou 6 Eliminatórias na
janela em que ele era nosso; 9 não cabe.

Este script generaliza esse raciocínio para todos os atletas — inclusive os três
que estão com a coluna "Máximo possível" EM BRANCO na planilha (Loor, Montes e
Savarino), que é exatamente onde o risco de deixar dinheiro na mesa mora.

DE ONDE VEM CADA NÚMERO
------------------------
  * as 9 janelas da CONMEBOL: seção 4 do CLAUDE.md, marcada CONFIRMADO;
  * 2 partidas por janela: estrutura do torneio (18 rodadas em 9 janelas),
    declarada em selecoes_escopo.csv;
  * as janelas de registro: atletas.csv — quase todas marcadas ESTIMADA,
    vindas de imprensa. Toda saída que depende delas sai sinalizada.

CAF, CONCACAF e UEFA não têm calendário levantado. Para atletas dessas
confederações o script diz "não sei" em vez de estimar — que é o que o
CLAUDE.md manda fazer.

O QUE ISTO PROVA E O QUE NÃO PROVA
-----------------------------------
Um "máximo possível" menor que o número da FIFA é PROVA de erro de atribuição:
não existe leitura de súmula que salve. Serve direto como argumento de rejeição.

O contrário não vale: assigned < máximo NÃO prova que falta partida. Só mostra
que há espaço para faltar, e portanto que vale conferir. Convocação é decisão
do técnico, não consequência do calendário.

USO
---
  python checagem_aritmetica.py
  python checagem_aritmetica.py --csv dados/checagem_aritmetica.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from parser_tabelas import normalizar, parse_data
from partidas_universo import JANELAS_CONMEBOL

CSV_ATLETAS = Path("atletas.csv")
CSV_ESCOPO = Path("selecoes_escopo.csv")

PARTIDAS_POR_JANELA_CONMEBOL = 2

# Números apresentados pela FIFA na plataforma "Player Releases for S.a.f.
# Botafogo". Fonte: aba 2 da planilha mestre, conferida em print de resolução
# cheia (rodapé "Page 1 of 1 — Total 8").
ASSIGNED_FIFA = {
    "thiago almada": 9,
    "vitinho": 2,
    "lucas perri": 6,
    "adryelson": 1,
    "cristhian loor": 1,
    "jacob montes": 2,
    "luiz henrique": 8,
    "jefferson savarino": 10,
}

CONFEDERACAO_POR_SELECAO = {
    "brasil": "CONMEBOL", "argentina": "CONMEBOL", "uruguai": "CONMEBOL",
    "paraguai": "CONMEBOL", "equador": "CONMEBOL", "venezuela": "CONMEBOL",
    "colombia": "CONMEBOL", "angola": "CAF", "marrocos": "CAF",
    "nicaragua": "CONCACAF", "panama": "CONCACAF",
    "finlandia": "UEFA", "espanha": "UEFA",
}


def janelas_alcancadas(ini, fim) -> list[tuple]:
    """Janelas da CONMEBOL que a janela de registro do atleta toca.

    Sobreposição, não contenção: quem chegou no meio de uma Data FIFA pode ter
    sido cedido para o segundo jogo dela. Por isso é limite SUPERIOR.
    """
    tocadas = []
    for rodadas, jini, jfim in JANELAS_CONMEBOL:
        if (ini is None or ini <= jfim) and (fim is None or fim >= jini):
            tocadas.append((rodadas, jini, jfim))
    return tocadas


def analisar(a: dict) -> dict:
    nome = a["atleta"]
    selecao = normalizar(a.get("selecao", ""))
    confed = CONFEDERACAO_POR_SELECAO.get(selecao, "?")
    ini = parse_data(a.get("registro_inicio"))
    fim = parse_data(a.get("registro_fim"))
    estimada = "estimada" in (a.get("origem_da_janela") or "").lower()
    assigned = ASSIGNED_FIFA.get(normalizar(nome))

    r = {
        "atleta": nome, "selecao": a.get("selecao", ""), "confederacao": confed,
        "registro_inicio": a.get("registro_inicio", ""),
        "registro_fim": a.get("registro_fim", "") or "(ainda no elenco)",
        "janela_estimada": "S" if estimada else "N",
        "assigned_fifa": "" if assigned is None else str(assigned),
        "janelas_alcancadas": "", "maximo_possivel": "",
        "diagnostico": "", "acao": "",
    }

    if confed != "CONMEBOL":
        r["maximo_possivel"] = "NAO SEI"
        r["diagnostico"] = (f"calendário {confed} não levantado — impossível "
                            f"calcular o máximo")
        r["acao"] = f"levantar calendário {confed} na fonte oficial"
        return r

    if ini is None and fim is None:
        r["maximo_possivel"] = "NAO SEI"
        r["diagnostico"] = "sem janela de registro no CSV"
        r["acao"] = "obter janela no TMS antes de qualquer conta"
        return r

    janelas = janelas_alcancadas(ini, fim)
    maximo = len(janelas) * PARTIDAS_POR_JANELA_CONMEBOL
    r["janelas_alcancadas"] = str(len(janelas))
    r["maximo_possivel"] = str(maximo)

    if assigned is None:
        r["diagnostico"] = (f"fora da lista da FIFA; caberiam até {maximo} "
                            f"partidas na janela")
        r["acao"] = ("candidato a CLAIM — conferir convocação e súmula"
                     if maximo > 0 else "sem janela útil, nada a reivindicar")
    elif assigned > maximo:
        r["diagnostico"] = (f"IMPOSSIVEL: FIFA atribuiu {assigned}, cabem no "
                            f"máximo {maximo}. Excedente de {assigned - maximo}")
        r["acao"] = f"REJEITAR {assigned - maximo} partida(s), jogo a jogo"
    elif assigned == maximo:
        r["diagnostico"] = f"no teto: {assigned} de {maximo} possíveis"
        r["acao"] = "aceitar; nada a reivindicar"
    else:
        r["diagnostico"] = (f"{assigned} de {maximo} possíveis — sobra espaço "
                            f"para até {maximo - assigned}")
        r["acao"] = "conferir se FALTA partida (risco inverso)"

    if estimada and r["maximo_possivel"] not in ("NAO SEI",):
        r["diagnostico"] += " [janela ESTIMADA — confirmar no TMS]"
    return r


def _ordem_por_maximo(r: dict) -> tuple[int, int]:
    """Maior espaço primeiro; 'NAO SEI' por último, sem quebrar no int()."""
    valor = r["maximo_possivel"]
    if not valor.isdigit():
        return (1, 0)
    return (0, -int(valor))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", metavar="ARQUIVO")
    args = ap.parse_args()

    with CSV_ATLETAS.open(encoding="utf-8") as fh:
        atletas = [a for a in csv.DictReader(fh) if (a.get("atleta") or "").strip()]

    resultados = [analisar(a) for a in atletas]

    na_lista = [r for r in resultados if r["assigned_fifa"]]
    fora = [r for r in resultados if not r["assigned_fifa"]]

    print("=" * 96)
    print("CHECAGEM ARITMÉTICA — quantas Eliminatórias caberiam na janela de cada atleta")
    print("=" * 96)

    print("\nOS 8 DA LISTA DA FIFA")
    print("-" * 96)
    print(f"{'Atleta':<20}{'Seleção':<12}{'FIFA':>5}{'Máx':>9}  Diagnóstico")
    print("-" * 96)
    for r in sorted(na_lista, key=lambda x: x["atleta"]):
        print(f"{r['atleta']:<20}{r['selecao']:<12}{r['assigned_fifa']:>5}"
              f"{r['maximo_possivel']:>9}  {r['diagnostico']}")

    impossiveis = [r for r in na_lista if "IMPOSSIVEL" in r["diagnostico"]]
    sobra = [r for r in na_lista if "sobra espaço" in r["diagnostico"]]
    nao_sei = [r for r in na_lista if r["maximo_possivel"] == "NAO SEI"]

    print("\nLEITURA")
    print("-" * 96)
    if impossiveis:
        print("PROVA DE ERRO — o número da FIFA não cabe na janela. Rejeitar:")
        for r in impossiveis:
            print(f"  · {r['atleta']}: {r['acao']}")
    if sobra:
        print("\nRISCO INVERSO — sobra espaço, pode estar FALTANDO partida:")
        for r in sobra:
            falta = int(r["maximo_possivel"]) - int(r["assigned_fifa"])
            print(f"  · {r['atleta']}: {r['assigned_fifa']} de "
                  f"{r['maximo_possivel']} — conferir até {falta} partida(s)")
    if nao_sei:
        print("\nNÃO DÁ PARA CALCULAR — calendário da confederação não levantado:")
        for r in nao_sei:
            print(f"  · {r['atleta']} ({r['confederacao']}): {r['acao']}")

    print("\n\nFORA DA LISTA DA FIFA — espaço aritmético para claim")
    print("-" * 96)
    print(f"{'Atleta':<20}{'Seleção':<12}{'Máx':>8}  Ação")
    print("-" * 96)
    for r in sorted(fora, key=_ordem_por_maximo):
        print(f"{r['atleta']:<20}{r['selecao']:<12}{r['maximo_possivel']:>8}  "
              f"{r['acao']}")

    print("\n" + "=" * 96)
    print("O QUE ISTO PROVA: 'máximo' menor que o número da FIFA é prova de erro")
    print("de atribuição — nenhuma leitura de súmula salva. Serve de argumento")
    print("direto para rejeitar.")
    print()
    print("O QUE NÃO PROVA: 'máximo' maior NÃO quer dizer que falta partida.")
    print("Só quer dizer que há espaço para faltar, e que vale conferir.")
    print("Convocação é decisão de técnico, não consequência de calendário.")
    print()
    print("Quase toda janela de registro aqui está marcada ESTIMADA (imprensa).")
    print("O extrato do TMS pode mudar qualquer linha desta tabela.")
    print("=" * 96)

    if args.csv:
        destino = Path(args.csv)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(resultados[0].keys()))
            w.writeheader()
            w.writerows(resultados)
        print(f"\nGravado: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
