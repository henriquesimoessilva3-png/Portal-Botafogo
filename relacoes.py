#!/usr/bin/env python3
"""
relacoes.py — cruza partidas_universo com atletas.csv.

Gera uma linha por (partida, atleta), conforme a seção 4b do CLAUDE.md:

  partida_id | atleta | status_na_sumula | posicao | minutos | clube_detentor |
  elegivel

O QUE ESTE SCRIPT DECIDE E O QUE ELE NÃO DECIDE
------------------------------------------------
Ele decide os filtros 1 e 2 do algoritmo de elegibilidade — competição e janela
de registro —, porque ambos são derivação de dado que já está nas tabelas.

Ele NÃO decide o filtro 3: se o atleta constou da relação daquela partida.
Isso só sai de súmula oficial (prova) ou, como pista, do Transfermarkt/oGol via
conferencia_selecoes.py. Por isso `status_na_sumula` nasce vazio e `elegivel`
nasce PENDENTE. Uma linha PENDENTE não é um claim: é uma pergunta a responder.

Com `--do-scraper conferencia_selecoes.xlsx` o status é pré-preenchido a partir
do que as duas fontes concordaram — e fica marcado como origem CONFERÊNCIA, não
PROVA.

USO
---
  python relacoes.py                                   # gera dados/relacoes.csv
  python relacoes.py --do-scraper conferencia_selecoes.xlsx
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, asdict
from pathlib import Path

from parser_tabelas import normalizar, parse_data
from partidas_universo import DIR_DADOS, carregar_universo

CSV_ATLETAS = Path("atletas.csv")
CSV_SAIDA = DIR_DADOS / "relacoes.csv"

CAMPOS = ["partida_id", "selecao", "data", "adversario", "atleta", "nascimento",
          "status_na_sumula", "posicao", "minutos", "clube_detentor",
          "elegivel", "origem_do_status", "janela_estimada", "observacao"]

# Como o CSV de atletas escreve o nome da seleção nem sempre bate com como a
# tabela de partidas escreve. Chave é sempre normalizada.
SINONIMOS_SELECAO = {
    "nicaragua": "nicaragua", "panama": "panama",
    "colombia": "colombia", "equador": "equador",
    "espanha": "espanha", "finlandia": "finlandia",
}


@dataclass
class Relacao:
    partida_id: str
    selecao: str
    data: str
    adversario: str
    atleta: str
    nascimento: str
    status_na_sumula: str
    posicao: str
    minutos: str
    clube_detentor: str
    elegivel: str
    origem_do_status: str
    janela_estimada: str
    observacao: str


def carregar_atletas() -> list[dict]:
    if not CSV_ATLETAS.exists():
        return []
    with CSV_ATLETAS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _chave_selecao(s: str) -> str:
    n = normalizar(s)
    return SINONIMOS_SELECAO.get(n, n)


def gerar(partidas, atletas) -> tuple[list[Relacao], list[str]]:
    """Uma linha para cada atleta cuja seleção jogou aquela partida E cuja
    janela de registro no Botafogo cobre a data."""
    saida: list[Relacao] = []
    avisos: list[str] = []

    por_selecao: dict[str, list[dict]] = {}
    for a in atletas:
        if not (a.get("atleta") or "").strip():
            continue
        por_selecao.setdefault(_chave_selecao(a.get("selecao", "")), []).append(a)

    for p in partidas:
        d = parse_data(p.data)
        if d is None:
            continue
        for a in por_selecao.get(_chave_selecao(p.selecao), []):
            ini = parse_data(a.get("registro_inicio"))
            fim = parse_data(a.get("registro_fim"))
            estimada = "estimada" in (a.get("origem_da_janela") or "").lower()

            if ini is None and fim is None:
                elegivel = "CONFERIR - atleta sem janela de registro"
                obs = "vínculo/janela não confirmados no TMS"
            elif (ini is None or d >= ini) and (fim is None or d <= fim):
                # Passou nos filtros 1 e 2. O 3 é que ainda falta.
                elegivel = "PENDENTE - falta confirmar relação na súmula"
                obs = ("janela ESTIMADA (imprensa) — confirmar no TMS"
                       if estimada else "")
            else:
                # Fora da janela: não gera direito, mas a linha fica registrada
                # para o descarte ser documentado, não presumido.
                elegivel = "NAO ELEGIVEL - fora da janela de registro"
                obs = "mantido para descarte documentado"

            saida.append(Relacao(
                partida_id=p.partida_id, selecao=p.selecao, data=p.data,
                adversario=p.adversario, atleta=a["atleta"],
                nascimento=a.get("nascimento", ""), status_na_sumula="",
                posicao="", minutos="", clube_detentor="",
                elegivel=elegivel, origem_do_status="",
                janela_estimada="S" if estimada else "N", observacao=obs,
            ))

    selecoes_com_atleta = set(por_selecao)
    selecoes_com_partida = {_chave_selecao(p.selecao) for p in partidas}
    orfas = sorted(selecoes_com_atleta - selecoes_com_partida)
    if orfas:
        avisos.append(
            "Seleções com atleta no CSV mas SEM partida no universo: "
            + ", ".join(orfas)
            + ". Enquanto o universo não for coletado, nenhum claim dessas "
              "seleções pode ser levantado.")
    return saida, avisos


def aplicar_scraper(relacoes: list[Relacao], xlsx: Path) -> int:
    """Pré-preenche status a partir do resultado do conferencia_selecoes.py.

    Só usa o que as DUAS fontes viram igual. Marca a origem como CONFERÊNCIA —
    nível 2 da hierarquia, não prova. Nenhuma linha vira ELEGÍVEL por aqui.
    """
    import pandas as pd

    df = pd.read_excel(xlsx, sheet_name="Partidas")
    rec = pd.read_excel(xlsx, sheet_name="Reconciliacao")
    ok = {(str(r["atleta"]), str(r["data"]))
          for _, r in rec.iterrows() if r.get("divergencia") == "OK"}

    mapa: dict[tuple[str, str], dict] = {}
    for _, r in df.iterrows():
        d = parse_data(str(r["data"]))
        if d is None or (str(r["atleta"]), str(r["data"])) not in ok:
            continue
        mapa[(normalizar(str(r["atleta"])), d.isoformat())] = r

    n = 0
    for rel in relacoes:
        r = mapa.get((normalizar(rel.atleta), rel.data))
        if r is None:
            continue
        rel.status_na_sumula = str(r.get("status") or "")
        rel.minutos = str(r.get("minutos") or "")
        rel.origem_do_status = "CONFERENCIA (Transfermarkt+oGol concordam)"
        if rel.elegivel.startswith("PENDENTE"):
            rel.elegivel = ("PENDENTE - conferencia indica "
                            f"'{rel.status_na_sumula}'; confirmar na súmula")
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--do-scraper", metavar="XLSX",
                    help="pré-preenche status com a saída de conferencia_selecoes.py")
    args = ap.parse_args()

    partidas = carregar_universo()
    atletas = carregar_atletas()

    print(f"{len(partidas)} linhas em partidas_universo · {len(atletas)} atletas")
    if not partidas:
        print()
        print("partidas_universo está VAZIO — não há o que cruzar.")
        print("Rode `python partidas_universo.py --status` para ver o que falta")
        print("e importe a coleta com --importar / --importar-html.")
        return 1

    relacoes, avisos = gerar(partidas, atletas)

    if args.do_scraper:
        n = aplicar_scraper(relacoes, Path(args.do_scraper))
        print(f"{n} linhas pré-preenchidas a partir do scraper (nível CONFERÊNCIA)")

    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    with CSV_SAIDA.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        for r in relacoes:
            w.writerow(asdict(r))

    print(f"\nGravado: {CSV_SAIDA} ({len(relacoes)} linhas)")
    contagem: dict[str, int] = {}
    for r in relacoes:
        chave = r.elegivel.split(" - ")[0]
        contagem[chave] = contagem.get(chave, 0) + 1
    for k, v in sorted(contagem.items()):
        print(f"  {k:<16} {v}")
    for a in avisos:
        print("\naviso:", a)
    print("\nNenhuma linha sai ELEGÍVEL por este script: o filtro 3 do algoritmo")
    print("(constou da relação da partida) só se fecha com súmula oficial.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
