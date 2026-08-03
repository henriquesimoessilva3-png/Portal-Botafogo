#!/usr/bin/env python3
"""
conferencia_tms.py — confronta o extrato do TMS com a nossa base.

O QUE MUDOU COM O EXTRATO
--------------------------
Até aqui o levantamento trabalhava com um print que dava só o TOTAL por atleta
("ALMADA Thiago · 9"). O extrato abre o jogo a jogo e revela três coisas que o
total escondia:

1. **Três estados, não um.** Cada partida está num de três:
   `ATRIBUIDA` (verde, botão Reject — a FIFA já deu para nós),
   `DISPONIVEL_CLAIM` (branca, botão Claim — do atleta, mas não nossa),
   `EM_CONFLITO` (âmbar, "FIFA resolving conflict" — outro clube reivindicou a
   mesma partida e a FIFA está arbitrando).

2. **O histórico traz TODAS as partidas do atleta pela seleção**, não só as
   nossas. Savarino aparece com 16 — as 6 de 2023 são de quando ele não era
   nosso, e estão corretamente como `DISPONIVEL_CLAIM`.

3. **Nem tudo na lista é Eliminatória.** É o que este script checa contra
   `dados/partidas_universo.csv`.

Uso:
  python conferencia_tms.py
  python conferencia_tms.py --json dados/conferencia_tms.json
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from parser_tabelas import normalizar, parse_data
from partidas_universo import carregar_universo

CSV_TMS = Path("dados/tms_extrato.csv")
VALOR = 2360


def carregar_tms() -> list[dict]:
    with CSV_TMS.open(encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["data"]]


def datas_de_eliminatoria() -> set[str]:
    """Toda data em que houve Eliminatória de Copa, em qualquer seleção do
    escopo. Serve para o teste mais barato: a partida do TMS cai numa delas?"""
    return {p.data for p in carregar_universo()}


def indice_universo() -> dict[str, set[str]]:
    """seleção normalizada -> datas em que ela jogou Eliminatória."""
    idx = defaultdict(set)
    for p in carregar_universo():
        idx[normalizar(p.selecao)].add(p.data)
    return idx


def vinculos() -> dict[str, tuple]:
    """Janela de registro de cada atleta, como apurada na Parte 1."""
    d = json.loads(Path("dados/parte2_cessao.json").read_text(encoding="utf-8"))
    out = {}
    for a in d.get("parte1", []):
        ini, _, fim = a["vinculo_texto"].partition(" a ")
        out[normalizar(a["nome"])] = (
            parse_data(ini.strip()) if ini.strip()[:1].isdigit() else None,
            parse_data(fim.strip()) if fim.strip()[:1].isdigit() else None)
    return out


def conferir() -> dict:
    tms = carregar_tms()
    idx = indice_universo()
    todas = datas_de_eliminatoria()
    vinc = vinculos()

    linhas = []
    for r in tms:
        sel = normalizar(r["selecao"])
        data = r["data"]
        na_selecao = data in idx.get(sel, set())
        em_alguma = data in todas

        if na_selecao:
            veredito, motivo = "OK", "é Eliminatória da seleção do atleta"
        elif em_alguma:
            veredito = "CONFERIR"
            motivo = ("houve Eliminatória nessa data, mas não desta seleção — "
                      "conferir o adversário")
        else:
            veredito = "NAO E ELIMINATORIA"
            motivo = ("nenhuma Eliminatória de Copa nesta data, em nenhuma "
                      "seleção do escopo")

        # A data cai dentro do vínculo? É o que decide se um CONFLITO vale a
        # pena disputar e se um CLAIM disponível é nosso.
        ini, fim = vinc.get(normalizar(r["atleta"]), (None, None))
        d = parse_data(data)
        if ini is None and fim is None:
            dentro, nota_vinc = None, "vínculo desconhecido"
        else:
            dentro = ((ini is None or d >= ini) and (fim is None or d <= fim))
            nota_vinc = "dentro do vínculo" if dentro else "FORA do vínculo"

        acao = ""
        st = r["status_plataforma"]
        if st == "ATRIBUIDA" and veredito != "OK":
            acao = "REJEITAR — não é Eliminatória"
        elif st == "ATRIBUIDA" and dentro is False:
            acao = "REJEITAR — fora do vínculo"
        elif st == "ATRIBUIDA":
            acao = "manter"
        elif st == "EM_CONFLITO" and dentro:
            acao = "DISPUTAR — a data cai dentro do nosso vínculo"
        elif st == "EM_CONFLITO":
            acao = "desistir — fora do vínculo"
        elif st == "DISPONIVEL_CLAIM" and dentro:
            acao = "REIVINDICAR — cabe no vínculo e não está conosco"
        elif st == "DISPONIVEL_CLAIM":
            acao = "não reivindicar — fora do vínculo"

        linhas.append({**r, "veredito": veredito, "motivo": motivo,
                       "confere_no_universo": na_selecao,
                       "dentro_do_vinculo": dentro, "nota_vinculo": nota_vinc,
                       "acao": acao})

    por_atleta = defaultdict(lambda: defaultdict(int))
    for l in linhas:
        por_atleta[l["atleta"]][l["status_plataforma"]] += 1
        if l["veredito"] != "OK":
            por_atleta[l["atleta"]]["_suspeitas"] += 1

    resumo = []
    for atleta, c in por_atleta.items():
        exemplo = next(x for x in linhas if x["atleta"] == atleta)
        resumo.append({
            "atleta": atleta, "selecao": exemplo["selecao"],
            "total_declarado": int(exemplo["total_do_atleta"]),
            "atribuidas": c.get("ATRIBUIDA", 0),
            "conflito": c.get("EM_CONFLITO", 0),
            "claim": c.get("DISPONIVEL_CLAIM", 0),
            "legiveis": sum(v for k, v in c.items() if not k.startswith("_")),
            "suspeitas": c.get("_suspeitas", 0),
        })
    resumo.sort(key=lambda x: -x["total_declarado"])
    for r in resumo:
        r["nao_legiveis"] = r["total_declarado"] - r["legiveis"]

    return {"linhas": linhas, "resumo": resumo,
            "totais": {
                "atribuidas": sum(r["atribuidas"] for r in resumo),
                "conflito": sum(r["conflito"] for r in resumo),
                "claim": sum(r["claim"] for r in resumo),
                "nao_legiveis": sum(r["nao_legiveis"] for r in resumo),
                "suspeitas": sum(r["suspeitas"] for r in resumo),
            }}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", metavar="ARQUIVO")
    args = ap.parse_args()

    res = conferir()
    t = res["totais"]

    print("=" * 78)
    print("EXTRATO DO TMS × NOSSA BASE")
    print("=" * 78)
    print(f"\n{'Atleta':<20}{'Seleção':<12}{'total':>6}{'nossas':>7}"
          f"{'confl.':>7}{'claim':>6}{'ilegív.':>8}")
    print("-" * 78)
    for r in res["resumo"]:
        print(f"{r['atleta']:<20}{r['selecao']:<12}{r['total_declarado']:>6}"
              f"{r['atribuidas']:>7}{r['conflito']:>7}{r['claim']:>6}"
              f"{r['nao_legiveis']:>8}")
    print("-" * 78)
    print(f"{'TOTAL':<32}{sum(r['total_declarado'] for r in res['resumo']):>6}"
          f"{t['atribuidas']:>7}{t['conflito']:>7}{t['claim']:>6}"
          f"{t['nao_legiveis']:>8}")

    print("\n\nAÇÃO POR LINHA — o que fazer com cada partida")
    print("-" * 78)
    from collections import Counter
    for acao, n in Counter(l["acao"] for l in res["linhas"]).most_common():
        print(f"  {n:>3}  {acao}")
    disputar = [l for l in res["linhas"] if l["acao"].startswith("DISPUTAR")]
    if disputar:
        print("\n  CONFLITOS QUE VALE DISPUTAR (data dentro do nosso vínculo):")
        for l in disputar:
            print(f"    {l['atleta']} · {l['data']} · {l['partida']}")
    desistir = [l for l in res["linhas"] if l["acao"].startswith("desistir")]
    if desistir:
        print("\n  CONFLITOS A DESISTIR (fora do vínculo):")
        for l in desistir:
            print(f"    {l['atleta']} · {l['data']} · {l['partida']}")

    ruins = [l for l in res["linhas"] if l["veredito"] != "OK"]
    print(f"\n\nPARTIDAS DO TMS QUE NÃO CONFEREM COM A NOSSA BASE: {len(ruins)}")
    print("-" * 78)
    for l in ruins:
        print(f"  {l['atleta']} · {l['data']} · {l['partida']}")
        print(f"    status na plataforma: {l['status_plataforma']}")
        print(f"    {l['veredito']} — {l['motivo']}")
        if l["observacao"]:
            print(f"    nota: {l['observacao']}")
    if not ruins:
        print("  nenhuma")

    print(f"\n\nDINHEIRO EM JOGO")
    print("-" * 78)
    print(f"  já atribuídas a nós ....... {t['atribuidas']:>3} × USD {VALOR:,} = "
          f"USD {t['atribuidas']*VALOR:,}")
    print(f"  em conflito com outro clube {t['conflito']:>3} × USD {VALOR:,} = "
          f"USD {t['conflito']*VALOR:,}")
    print(f"  a rejeitar (não é Eliminatória) {len([l for l in ruins if l['status_plataforma']=='ATRIBUIDA']):>1}"
          f" × USD {VALOR:,}")
    print(f"\n  {t['nao_legiveis']} linhas ficaram fora do recorte dos prints e não "
          f"puderam ser lidas.")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        print(f"\nGravado: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
