#!/usr/bin/env python3
"""
parte2_cessao.py — a segunda parte do levantamento: a visão por CESSÃO.

O PROBLEMA QUE ESTA PARTE ATACA
--------------------------------
A Parte 1 do documento contou **relação de partida**: o atleta figurou na
escalação oficial daquele jogo. É prova, e é sólida.

Mas o texto da própria plataforma da FIFA não fala em escalação. Fala em
CESSÃO:

    "players ... identified by FIFA as being RELEASED by your club for one or
     more FIFA World Cup 26 Qualifying Matches, ... prepared using data from the
     FIFA Transfer Matching System and national registration systems"

    "Reject any players ... which you DID NOT RELEASE for the specific match"

Cedido e relacionado não são a mesma coisa. Um atleta convocado que se
apresenta, fica à disposição e não entra na relação de 23 foi **cedido** — o
clube ficou sem ele — mas não aparece em nenhuma escalação.

A EVIDÊNCIA DE QUE O CRITÉRIO É CESSÃO
---------------------------------------
Cristhian Loor. A FIFA atribuiu 1 partida a ele. A conferência de escalação
oficial achou ZERO. Se a base da FIFA fosse escalação, ela não teria atribuído
nada. Ela está contando outra coisa — e o texto dela diz qual.

O mesmo padrão no Thiago Almada: FIFA 9, escalação 8.

Nos dois casos em que o número da FIFA difere do da escalação sem explicação de
janela de registro, **a FIFA é maior**. É o que se espera se ela conta cessão.

COMO ESTA PARTE CALCULA
------------------------
Regra conservadora, ancorada em prova, não em suposição:

    Se a escalação oficial confirma o atleta em PELO MENOS UMA partida de uma
    janela de Data FIFA, então ele estava cedido naquela janela — e, pelo
    critério de cessão, TODAS as partidas daquela janela contam.

Isso não é chute: a presença numa escalação prova a cessão da janela inteira.
O que fica de fora é a janela em que ele foi cedido e não entrou em nenhuma
relação — essa continua desconhecida e sai listada como tal, porque só a
convocação oficial da federação resolve.

Uso:
  python parte2_cessao.py --pdf levantamento_fifa_botafogo.pdf
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from parser_tabelas import normalizar, parse_data
from partidas_universo import carregar_universo

VALOR_POR_PARTIDA = 2360

# Números da lista original da plataforma "Player Releases for S.a.f. Botafogo".
# Fonte: aba 2 da planilha mestre, conferida em print (rodapé "Page 1 of 1 —
# Total 8"). É contra isto que os dois critérios são medidos.
ASSIGNED_FIFA = {
    "Thiago Almada": 9, "Vitinho": 2, "Lucas Perri": 6, "Adryelson": 1,
    "Cristhian Loor": 1, "Jacob Montes": 2, "Luiz Henrique": 8,
    "Jefferson Savarino": 10,
}

# Nome da seleção no cabeçalho do atleta (PT) -> nome no partidas_universo.
SELECAO_PT = {
    "venezuela": "Venezuela", "argentina": "Argentina", "paraguai": "Paraguai",
    "brasil": "Brasil", "nicaragua": "Nicaragua", "equador": "Equador",
    "uruguai": "Uruguai", "colombia": "Colombia", "angola": "Angola",
    "panama": "Panama", "espanha": "Espanha", "finlandia": "Finlandia",
    "bolivia": "Bolivia", "trinidad e tobago": "Trinidad e Tobago",
}

RE_ATLETA = re.compile(
    r"^(?P<nome>[^·\n]+?) · (?P<completo>[^\n]+)\n"
    r"(?P<selecao>[^ ]+(?: [^ ]+)?) · (?P<posicao>[^·]+) · nasc\. (?P<nasc>\d{4}-\d{2}-\d{2})"
    r"[^\n]*?vínculo: (?P<vinculo>[^·]+) · (?P<n_elim>\d+) em Eliminatórias, (?P<n_copa>\d+) na Copa",
    re.M)

RE_PARTIDA = re.compile(
    r"(Eliminatórias|Copa) (\d{4}-\d{2}-\d{2}) ([A-Za-zÀ-ÿ ]+?) × ([A-Za-zÀ-ÿ ]+?) "
    r"(?:(\d{1,2}) ?)?(Titular|Suplente utilizado|Suplente não utilizado)")


# --------------------------------------------------------------------------- #
# Leitura da Parte 1
# --------------------------------------------------------------------------- #

def ler_parte1(caminho: Path) -> list[dict]:
    from pypdf import PdfReader
    txt = "\n".join(p.extract_text() or "" for p in PdfReader(caminho).pages)

    cabecalhos = list(RE_ATLETA.finditer(txt))
    atletas = []
    for i, m in enumerate(cabecalhos):
        fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(txt)
        trecho = txt[m.start():fim]
        partidas = [{"torneio": t, "data": d, "casa": a.strip(), "fora": b.strip(),
                     "status": s}
                    for t, d, a, b, _, s in RE_PARTIDA.findall(trecho)]
        vinc = m.group("vinculo").strip()
        ini, _, fim_v = vinc.partition(" a ")
        atletas.append({
            "nome": m.group("nome").strip(),
            "nome_completo": m.group("completo").strip(),
            "selecao": m.group("selecao").strip(),
            "posicao": m.group("posicao").strip(),
            "nascimento": m.group("nasc"),
            "vinculo_texto": vinc,
            "vinculo_ini": parse_data(ini.strip()) if ini.strip()[:1].isdigit() else None,
            "vinculo_fim": parse_data(fim_v.strip()) if fim_v.strip()[:1].isdigit() else None,
            "n_elim_declarado": int(m.group("n_elim")),
            "n_copa": int(m.group("n_copa")),
            "partidas": partidas,
        })
    return atletas


# --------------------------------------------------------------------------- #
# Janelas de Data FIFA
# --------------------------------------------------------------------------- #

def agrupar_em_janelas(datas: list[date], folga_dias: int = 12) -> list[list[date]]:
    """Agrupa partidas de uma seleção em janelas de Data FIFA.

    Não usa a tabela fixa da CONMEBOL: deriva do próprio calendário, para valer
    também na CAF, na CONCACAF e na UEFA, cujos formatos são outros.
    """
    janelas: list[list[date]] = []
    for d in sorted(datas):
        if janelas and (d - janelas[-1][-1]) <= timedelta(days=folga_dias):
            janelas[-1].append(d)
        else:
            janelas.append([d])
    return janelas


def rotulo_janela(js: list[date]) -> str:
    MES = ["jan", "fev", "mar", "abr", "mai", "jun",
           "jul", "ago", "set", "out", "nov", "dez"]
    a, b = js[0], js[-1]
    if a == b:
        return f"{a.day:02d}/{MES[a.month-1]}/{a.year}"
    return f"{a.day:02d}–{b.day:02d}/{MES[a.month-1]}/{a.year}"


# --------------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------------- #

def analisar(atletas_pdf: list[dict]) -> dict:
    universo = defaultdict(list)
    for p in carregar_universo():
        d = parse_data(p.data)
        if d:
            universo[normalizar(p.selecao)].append((d, p))

    linhas = []
    for a in atletas_pdf:
        sel = SELECAO_PT.get(normalizar(a["selecao"]), a["selecao"])
        jogos = universo.get(normalizar(sel), [])
        ini, fim = a["vinculo_ini"], a["vinculo_fim"]
        no_vinculo = [(d, p) for d, p in jogos
                      if (ini is None or d >= ini) and (fim is None or d <= fim)]
        if not no_vinculo:
            continue

        confirmadas = {parse_data(x["data"]) for x in a["partidas"]
                       if x["torneio"] == "Eliminatórias"}
        janelas = agrupar_em_janelas([d for d, _ in no_vinculo])

        detalhe = []
        for js in janelas:
            n_total = len(js)
            n_conf = len([d for d in js if d in confirmadas])
            detalhe.append({
                "rotulo": rotulo_janela(js),
                "partidas": n_total,
                "confirmadas": n_conf,
                "ganho": (n_total - n_conf) if n_conf > 0 else 0,
                "situacao": ("cessão provada pela escalação" if n_conf > 0
                             else "nenhuma escalação — cessão desconhecida"),
                "desconhecidas": n_total if n_conf == 0 else 0,
            })

        linhas.append({
            "nome": a["nome"], "selecao": sel, "posicao": a["posicao"],
            "vinculo": a["vinculo_texto"],
            "sumula": sum(d["confirmadas"] for d in detalhe),
            "ganho_cessao": sum(d["ganho"] for d in detalhe),
            "desconhecidas": sum(d["desconhecidas"] for d in detalhe),
            "janelas": detalhe,
        })

    linhas.sort(key=lambda x: (-x["ganho_cessao"], -x["sumula"]))
    return {"atletas": linhas}


def nao_verificados(atletas_pdf: list[dict]) -> list[dict]:
    """Atletas do atletas.csv cuja seleção jogou dentro do vínculo e que não
    aparecem na Parte 1. Ausência aqui não é prova de nada — é lacuna."""
    presentes = {normalizar(a["nome"]) for a in atletas_pdf}
    universo = defaultdict(list)
    for p in carregar_universo():
        d = parse_data(p.data)
        if d:
            universo[normalizar(p.selecao)].append(d)

    saida = []
    for a in csv.DictReader(open("atletas.csv", encoding="utf-8")):
        nome = a["atleta"]
        if normalizar(nome) in presentes:
            continue
        if any(normalizar(nome) in p or p in normalizar(nome) for p in presentes):
            continue
        sel = normalizar(a.get("selecao", ""))
        jogos = universo.get(sel, [])
        ini, fim = parse_data(a["registro_inicio"]), parse_data(a["registro_fim"])
        if ini is None and fim is None:
            continue
        dentro = [d for d in jogos
                  if (ini is None or d >= ini) and (fim is None or d <= fim)]
        if not dentro:
            continue
        janelas = agrupar_em_janelas(dentro)
        saida.append({
            "nome": nome, "selecao": a.get("selecao", ""),
            "vinculo": f"{a['registro_inicio'] or '?'} a {a['registro_fim'] or 'hoje'}",
            "partidas": len(dentro), "janelas": len(janelas),
            "estimada": "estimada" in (a.get("origem_da_janela") or "").lower(),
        })
    saida.sort(key=lambda x: -x["partidas"])
    return saida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--saida", default="dados/parte2_cessao.json")
    args = ap.parse_args()

    atletas = ler_parte1(Path(args.pdf))
    print(f"Parte 1: {len(atletas)} atletas lidos do PDF")
    total_decl = sum(a["n_elim_declarado"] for a in atletas)
    total_lin = sum(len([p for p in a["partidas"] if p["torneio"] == "Eliminatórias"])
                    for a in atletas)
    print(f"  soma declarada por atleta: {total_decl}")
    print(f"  linhas de partida no detalhe: {total_lin}")

    res = analisar(atletas)
    res["nao_verificados"] = nao_verificados(atletas)

    # Reconciliação contra a lista original da FIFA. É o teste mais direto de
    # qual critério a FIFA usou: o que aproxima mais dos números dela?
    por = {a["nome"]: a for a in res["atletas"]}
    # Quem está ausente da Parte 1 não tem seleção vinda do PDF — a linha dele é
    # justamente a mais importante da tabela, então não pode sair em branco.
    sel_csv = {r["atleta"]: r.get("selecao", "")
               for r in csv.DictReader(open("atletas.csv", encoding="utf-8"))}
    recon = []
    for nome, atribuidas in ASSIGNED_FIFA.items():
        a = por.get(nome)
        sml = a["sumula"] if a else 0
        ces = (a["sumula"] + a["ganho_cessao"]) if a else 0
        recon.append({"nome": nome,
                      "selecao": (a or {}).get("selecao") or sel_csv.get(nome, ""),
                      "fifa": atribuidas, "sumula": sml, "cessao": ces,
                      "d_sumula": sml - atribuidas, "d_cessao": ces - atribuidas,
                      "ausente": a is None})
    res["reconciliacao"] = recon
    res["recon_totais"] = {
        "fifa": sum(r["fifa"] for r in recon),
        "sumula": sum(r["sumula"] for r in recon),
        "cessao": sum(r["cessao"] for r in recon),
    }
    res["totais"] = {
        "sumula": sum(a["sumula"] for a in res["atletas"]),
        "ganho_cessao": sum(a["ganho_cessao"] for a in res["atletas"]),
        "desconhecidas": sum(a["desconhecidas"] for a in res["atletas"]),
        "copa_dias": 34,
    }
    res["totais"]["cessao"] = res["totais"]["sumula"] + res["totais"]["ganho_cessao"]

    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(json.dumps(res, ensure_ascii=False, indent=2,
                                           default=str), encoding="utf-8")

    t = res["totais"]
    print(f"\n{'Atleta':<22}{'Seleção':<12}{'súmula':>8}{'+cessão':>9}{'?':>5}")
    print("-" * 60)
    for a in res["atletas"]:
        print(f"{a['nome']:<22}{a['selecao']:<12}{a['sumula']:>8}"
              f"{a['ganho_cessao']:>9}{a['desconhecidas']:>5}")
    print("-" * 60)
    print(f"{'TOTAL':<34}{t['sumula']:>8}{t['ganho_cessao']:>9}{t['desconhecidas']:>5}")
    print(f"\n  critério súmula:  {t['sumula']} × USD {VALOR_POR_PARTIDA:,} = "
          f"USD {t['sumula']*VALOR_POR_PARTIDA:,}")
    print(f"  critério cessão:  {t['cessao']} × USD {VALOR_POR_PARTIDA:,} = "
          f"USD {t['cessao']*VALOR_POR_PARTIDA:,}")
    print(f"  diferença:        USD {t['ganho_cessao']*VALOR_POR_PARTIDA:,}")
    print(f"\n  janelas sem nenhuma escalação (cessão desconhecida): "
          f"{t['desconhecidas']} partidas")
    print(f"\n  atletas não verificados: {len(res['nao_verificados'])}")
    print(f"\nGravado: {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
