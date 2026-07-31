#!/usr/bin/env python3
"""
partidas_universo.py — o universo de partidas de Eliminatórias 2026.

O QUE É
-------
Uma linha por (seleção, partida), conforme a seção 4b do CLAUDE.md:

  partida_id | selecao | confederacao | competicao | rodada | data | mando |
  adversario | resultado | fonte

`partida_id` é canônico: mesma partida vista pelos dois lados gera o mesmo id.
Assim as 90 partidas das Eliminatórias Sul-Americanas viram 180 linhas
(uma por seleção) sem risco de contar duas vezes.

ESTADO DOS DADOS
----------------
`dados/partidas_universo.csv` está VAZIO. Não foi possível coletá-lo: o
ambiente onde este código foi escrito não tem rota de rede para conmebol.com,
nem para as Wikipédias, nem para qualquer fonte de fixture (bloqueio de
política de egresso, 403 no CONNECT). Preencher a tabela de memória seria
exatamente o que o CLAUDE.md proíbe — "levantar na fonte oficial, não estimar".

O que ESTÁ pronto e testado é a infraestrutura em volta:

  * o schema e o id canônico de partida;
  * o validador de invariantes do formato CONMEBOL, que pega a maior parte dos
    erros de coleta (rodada faltando, seleção com número errado de jogos,
    confronto duplicado, jogo fora das janelas de Data FIFA);
  * o import a partir de CSV ou de dump HTML;
  * o relatório de cobertura contra selecoes_escopo.csv.

Quem tiver acesso à rede roda o import e o validador diz na hora se a coleta
está íntegra. Sem isso, é chute com cara de tabela.

USO
---
  python partidas_universo.py --status
  python partidas_universo.py --importar fixture.csv --selecao Brasil
  python partidas_universo.py --importar-html dump.html --selecao Brasil
  python partidas_universo.py --validar
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

from parser_tabelas import extrair_linhas, normalizar, parse_data

DIR_DADOS = Path("dados")
CSV_UNIVERSO = DIR_DADOS / "partidas_universo.csv"
CSV_ESCOPO = Path("selecoes_escopo.csv")

CAMPOS = ["partida_id", "selecao", "confederacao", "competicao", "rodada",
          "data", "mando", "adversario", "resultado", "fonte"]

# Janelas das Eliminatórias Sul-Americanas.
# Fonte: CLAUDE.md §4, marcado CONFIRMADO. Não é estimativa minha — é a tabela
# que o próprio projeto já validou. Serve de invariante: partida de Eliminatória
# da CONMEBOL que caia fora de uma destas janelas é sinal de coleta errada
# (tipicamente um amistoso que entrou junto).
JANELAS_CONMEBOL = [
    ((1, 2), date(2023, 9, 7), date(2023, 9, 12)),
    ((3, 4), date(2023, 10, 12), date(2023, 10, 17)),
    ((5, 6), date(2023, 11, 16), date(2023, 11, 21)),
    ((7, 8), date(2024, 9, 5), date(2024, 9, 10)),
    ((9, 10), date(2024, 10, 10), date(2024, 10, 15)),
    ((11, 12), date(2024, 11, 14), date(2024, 11, 19)),
    ((13, 14), date(2025, 3, 20), date(2025, 3, 25)),
    ((15, 16), date(2025, 6, 4), date(2025, 6, 10)),
    ((17, 18), date(2025, 9, 4), date(2025, 9, 9)),
]

# As 10 seleções da CONMEBOL. Fato estrutural do torneio, declarado no
# selecoes_escopo.csv ("10 selecoes, 18 rodadas").
SELECOES_CONMEBOL = {
    "argentina", "bolivia", "brasil", "chile", "colombia",
    "equador", "paraguai", "peru", "uruguai", "venezuela",
}

TOTAL_RODADAS_CONMEBOL = 18
JOGOS_POR_SELECAO_CONMEBOL = 18
PARTIDAS_CONMEBOL = 90


@dataclass
class Partida:
    partida_id: str
    selecao: str
    confederacao: str
    competicao: str
    rodada: str
    data: str
    mando: str          # 'casa' ou 'fora'
    adversario: str
    resultado: str
    fonte: str


def id_canonico(selecao: str, adversario: str, data_iso: str) -> str:
    """Mesma partida, vista dos dois lados, tem o mesmo id.

    Sem isto, Brasil x Bolívia e Bolívia x Brasil viram duas partidas e o total
    de 90 vira 180 sem ninguém perceber.
    """
    a, b = sorted([normalizar(selecao), normalizar(adversario)])
    return f"{data_iso}|{a}|{b}"


# --------------------------------------------------------------------------- #
# Leitura / escrita
# --------------------------------------------------------------------------- #

def carregar_universo(caminho: Path = CSV_UNIVERSO) -> list[Partida]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as fh:
        return [Partida(**{c: (r.get(c) or "").strip() for c in CAMPOS})
                for r in csv.DictReader(fh)]


def gravar_universo(partidas: list[Partida], caminho: Path = CSV_UNIVERSO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        for p in sorted(partidas, key=lambda x: (x.data, x.selecao)):
            w.writerow(asdict(p))


def carregar_escopo() -> list[dict]:
    if not CSV_ESCOPO.exists():
        return []
    with CSV_ESCOPO.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- #
# Validação
# --------------------------------------------------------------------------- #

def _janela_de(d: date) -> tuple | None:
    for rodadas, ini, fim in JANELAS_CONMEBOL:
        if ini <= d <= fim:
            return rodadas
    return None


def validar(partidas: list[Partida]) -> tuple[list[str], list[str]]:
    """Devolve (erros, avisos).

    Erro = a tabela está internamente inconsistente, não use.
    Aviso = pode estar certo, mas merece olhada.
    """
    erros: list[str] = []
    avisos: list[str] = []

    if not partidas:
        avisos.append("Tabela vazia — nada a validar.")
        return erros, avisos

    # -- integridade linha a linha ----------------------------------------- #
    vistos: set[tuple[str, str]] = set()
    for i, p in enumerate(partidas, start=2):   # +1 do cabeçalho
        if not p.selecao or not p.adversario:
            erros.append(f"linha {i}: seleção ou adversário em branco")
            continue
        if normalizar(p.selecao) == normalizar(p.adversario):
            erros.append(f"linha {i}: {p.selecao} jogando contra si mesma")
        if p.mando not in ("casa", "fora"):
            erros.append(f"linha {i}: mando '{p.mando}' não é 'casa' nem 'fora'")
        d = parse_data(p.data)
        if d is None:
            erros.append(f"linha {i}: data '{p.data}' não reconhecida")
            continue
        esperado = id_canonico(p.selecao, p.adversario, d.isoformat())
        if p.partida_id != esperado:
            erros.append(f"linha {i}: partida_id fora do padrão canônico "
                         f"({p.partida_id!r} ≠ {esperado!r})")
        chave = (normalizar(p.selecao), p.partida_id)
        if chave in vistos:
            erros.append(f"linha {i}: {p.selecao} duplicada na mesma partida")
        vistos.add(chave)
        if not p.fonte:
            avisos.append(f"linha {i}: sem fonte declarada")

    # -- consistência dos dois lados --------------------------------------- #
    por_id: dict[str, list[Partida]] = {}
    for p in partidas:
        por_id.setdefault(p.partida_id, []).append(p)
    for pid, lados in por_id.items():
        if len(lados) == 2:
            mandos = sorted(l.mando for l in lados)
            if mandos != ["casa", "fora"]:
                erros.append(f"{pid}: os dois lados declaram mando {mandos}")

    # -- invariantes do formato CONMEBOL ----------------------------------- #
    conmebol = [p for p in partidas if normalizar(p.confederacao) == "conmebol"]
    if conmebol:
        erros_c, avisos_c = _validar_conmebol(conmebol)
        erros += erros_c
        avisos += avisos_c

    return erros, avisos


def _validar_conmebol(partidas: list[Partida]) -> tuple[list[str], list[str]]:
    erros: list[str] = []
    avisos: list[str] = []

    ids = {p.partida_id for p in partidas}
    selecoes = {normalizar(p.selecao) for p in partidas}

    fora_do_torneio = selecoes - SELECOES_CONMEBOL
    if fora_do_torneio:
        erros.append(f"CONMEBOL: seleção fora do torneio: {sorted(fora_do_torneio)}")

    # Cada seleção joga 18, sendo 9 em casa e 9 fora.
    for s in sorted(selecoes & SELECOES_CONMEBOL):
        dela = [p for p in partidas if normalizar(p.selecao) == s]
        n = len(dela)
        if n != JOGOS_POR_SELECAO_CONMEBOL:
            erros.append(f"CONMEBOL/{s}: {n} jogos, esperado "
                         f"{JOGOS_POR_SELECAO_CONMEBOL}")
        casa = sum(1 for p in dela if p.mando == "casa")
        fora = sum(1 for p in dela if p.mando == "fora")
        if n == JOGOS_POR_SELECAO_CONMEBOL and (casa, fora) != (9, 9):
            erros.append(f"CONMEBOL/{s}: {casa} em casa e {fora} fora, "
                         f"esperado 9 e 9")

        # Turno e returno: encontra cada adversário exatamente 2 vezes.
        adv: dict[str, int] = {}
        for p in dela:
            adv[normalizar(p.adversario)] = adv.get(normalizar(p.adversario), 0) + 1
        for a, c in sorted(adv.items()):
            if c != 2:
                erros.append(f"CONMEBOL/{s}: enfrenta {a} {c}x, esperado 2")

        # Uma partida por rodada.
        rodadas = [p.rodada for p in dela if p.rodada]
        if len(set(rodadas)) != len(rodadas):
            erros.append(f"CONMEBOL/{s}: mais de uma partida na mesma rodada")

    # Totais só fazem sentido com o torneio inteiro coletado.
    if selecoes >= SELECOES_CONMEBOL:
        if len(ids) != PARTIDAS_CONMEBOL:
            erros.append(f"CONMEBOL: {len(ids)} partidas distintas, esperado "
                         f"{PARTIDAS_CONMEBOL}")
        rodadas = {p.rodada for p in partidas if p.rodada}
        if len(rodadas) != TOTAL_RODADAS_CONMEBOL:
            erros.append(f"CONMEBOL: {len(rodadas)} rodadas, esperado "
                         f"{TOTAL_RODADAS_CONMEBOL}")
    else:
        faltam = sorted(SELECOES_CONMEBOL - selecoes)
        avisos.append(f"CONMEBOL: coleta parcial, faltam {faltam}. "
                      f"Os totais (90 partidas, 18 rodadas) só são checados "
                      f"com o torneio inteiro.")

    # Toda partida tem que cair numa janela de Data FIFA. Amistoso que vazou na
    # coleta quase sempre cai fora — este é o filtro que pega.
    for p in partidas:
        d = parse_data(p.data)
        if d and _janela_de(d) is None:
            erros.append(f"{p.selecao} x {p.adversario} em {p.data}: fora de "
                         f"todas as janelas de Eliminatórias. Amistoso na coleta?")

    return erros, avisos


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #

_ALIAS_MANDO = {"casa": "casa", "h": "casa", "home": "casa", "c": "casa",
                "fora": "fora", "a": "fora", "away": "fora", "f": "fora"}


def _normalizar_linha(bruto: dict, selecao_padrao: str, confed: str,
                      competicao: str, fonte: str) -> Partida | None:
    selecao = (bruto.get("selecao") or selecao_padrao or "").strip()
    adversario = (bruto.get("adversario") or "").strip()
    d = parse_data(bruto.get("data") or "")
    if not (selecao and adversario and d):
        return None
    mando = _ALIAS_MANDO.get(normalizar(bruto.get("mando") or ""), "")
    return Partida(
        partida_id=id_canonico(selecao, adversario, d.isoformat()),
        selecao=selecao,
        confederacao=(bruto.get("confederacao") or confed).strip(),
        competicao=(bruto.get("competicao") or competicao).strip(),
        rodada=(bruto.get("rodada") or "").strip(),
        data=d.isoformat(),
        mando=mando,
        adversario=adversario,
        resultado=(bruto.get("resultado") or "").strip(),
        fonte=(bruto.get("fonte") or fonte).strip(),
    )


def importar_csv(caminho: Path, selecao: str, confed: str, competicao: str,
                 fonte: str) -> list[Partida]:
    with caminho.open(encoding="utf-8") as fh:
        brutos = list(csv.DictReader(fh))
    saida = []
    for b in brutos:
        p = _normalizar_linha({k.strip().lower(): v for k, v in b.items()},
                              selecao, confed, competicao, fonte)
        if p:
            saida.append(p)
    return saida


def importar_html(caminho: Path, selecao: str, confed: str, competicao: str,
                  fonte: str) -> list[Partida]:
    """Extrai fixture de um dump HTML usando o mesmo leitor de tabelas do scraper.

    ATENÇÃO: o mapeamento de colunas aqui é hipótese, igual ao do scraper de
    atletas — não foi conferido contra o HTML real de nenhuma fonte de fixture.
    Rode sempre --validar depois de importar: as invariantes da CONMEBOL pegam
    a maior parte dos erros de mapeamento.
    """
    html = caminho.read_text(encoding="utf-8", errors="replace")
    saida: list[Partida] = []
    for l in extrair_linhas(html):
        idx = next((i for i, c in enumerate(l.celulas) if parse_data(c)), None)
        if idx is None:
            continue
        textos = [c for c in l.celulas if c]
        nomes = [c for i, c in enumerate(l.celulas)
                 if i != idx and len(c) > 2 and not parse_data(c)
                 and any(ch.isalpha() for ch in c)]
        if len(nomes) < 2:
            continue
        p = _normalizar_linha({
            "selecao": nomes[0], "adversario": nomes[1],
            "data": l.celulas[idx], "mando": "casa",
            "resultado": next((c for c in textos
                               if any(x in c for x in (":", "–", "-"))
                               and any(ch.isdigit() for ch in c)), ""),
        }, selecao, confed, competicao, fonte)
        if p:
            saida.append(p)
    return saida


def espelhar(partidas: list[Partida]) -> list[Partida]:
    """Gera a linha do outro lado de cada partida que só tem um.

    O universo é por seleção: Brasil x Bolívia precisa aparecer também na
    perspectiva da Bolívia, senão o validador acusa 9 jogos em vez de 18.
    """
    por_id: dict[str, list[Partida]] = {}
    for p in partidas:
        por_id.setdefault(p.partida_id, []).append(p)
    saida = list(partidas)
    for pid, lados in por_id.items():
        if len(lados) != 1:
            continue
        o = lados[0]
        saida.append(Partida(
            partida_id=pid, selecao=o.adversario, confederacao=o.confederacao,
            competicao=o.competicao, rodada=o.rodada, data=o.data,
            mando="fora" if o.mando == "casa" else "casa",
            adversario=o.selecao,
            resultado=_inverter_placar(o.resultado), fonte=o.fonte,
        ))
    return saida


def _inverter_placar(res: str) -> str:
    partes = (res or "").replace("–", ":").replace("-", ":").split(":")
    if len(partes) == 2 and all(p.strip().isdigit() for p in partes):
        return f"{partes[1].strip()}:{partes[0].strip()}"
    return res


# --------------------------------------------------------------------------- #
# Relatórios
# --------------------------------------------------------------------------- #

def relatorio_status(partidas: list[Partida]) -> None:
    escopo = carregar_escopo()
    print("COBERTURA DO UNIVERSO DE PARTIDAS")
    print("=" * 74)
    if not partidas:
        print("dados/partidas_universo.csv está VAZIO.\n")
    por_selecao: dict[str, int] = {}
    for p in partidas:
        por_selecao[normalizar(p.selecao)] = por_selecao.get(normalizar(p.selecao), 0) + 1

    print(f"{'Seleção':<14}{'Confed.':<11}{'Esperado':<10}{'Coletado':<10}Situação")
    print("-" * 74)
    for e in escopo:
        s = e["selecao"]
        esperado = (e.get("jogos_da_selecao") or "").strip() or "?"
        n = por_selecao.get(normalizar(s), 0)
        if n == 0:
            situacao = "PENDENTE"
        elif esperado != "?" and str(n) == esperado:
            situacao = "completo"
        else:
            situacao = "parcial"
        print(f"{s:<14}{e['confederacao']:<11}{esperado:<10}{n:<10}{situacao}")
    print("-" * 74)
    ids = {p.partida_id for p in partidas}
    print(f"Linhas (seleção × partida): {len(partidas)}")
    print(f"Partidas distintas:         {len(ids)}")
    print(f"Alvo CONMEBOL:              {PARTIDAS_CONMEBOL} partidas "
          f"({PARTIDAS_CONMEBOL * 2} linhas)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--importar", metavar="CSV")
    ap.add_argument("--importar-html", metavar="HTML")
    ap.add_argument("--selecao", default="")
    ap.add_argument("--confederacao", default="CONMEBOL")
    ap.add_argument("--competicao", default="Eliminatórias da Copa do Mundo FIFA 2026")
    ap.add_argument("--fonte", default="")
    args = ap.parse_args()

    partidas = carregar_universo()

    if args.importar or args.importar_html:
        if not args.fonte:
            print("ERRO: --fonte é obrigatório no import. Toda linha precisa "
                  "dizer de onde veio.", file=sys.stderr)
            return 2
        if args.importar:
            novas = importar_csv(Path(args.importar), args.selecao,
                                 args.confederacao, args.competicao, args.fonte)
        else:
            novas = importar_html(Path(args.importar_html), args.selecao,
                                  args.confederacao, args.competicao, args.fonte)
        print(f"{len(novas)} linhas lidas.")
        existentes = {(p.partida_id, normalizar(p.selecao)) for p in partidas}
        todas = partidas + [p for p in espelhar(novas)
                            if (p.partida_id, normalizar(p.selecao)) not in existentes]
        gravar_universo(todas)
        print(f"Gravado em {CSV_UNIVERSO} ({len(todas)} linhas).")
        partidas = todas
        args.validar = True

    if args.status or not (args.validar or args.importar or args.importar_html):
        relatorio_status(partidas)
        print()

    if args.validar:
        erros, avisos = validar(partidas)
        print("VALIDAÇÃO")
        print("=" * 74)
        for a in avisos:
            print("  aviso:", a)
        for e in erros:
            print("  ERRO: ", e)
        if not erros:
            print("  Sem erros de integridade.")
        return 1 if erros else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
