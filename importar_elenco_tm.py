#!/usr/bin/env python3
"""
importar_elenco_tm.py — lê a página de elenco do Transfermarkt salva em disco.

POR QUE ISTO EXISTE
-------------------
As URLs de elenco do Transfermarkt (`/kader/verein/537?saison_id=AAAA`) são
inalcançáveis desta sessão: a política de egresso recusa o CONNECT para o host
`transfermarkt.*` inteiro, antes de qualquer caminho ser enviado. Testado em
.com.br, .com, .us, .co.uk, .de e no CDN de imagens. Mandar outra URL não muda
nada — o bloqueio não é de página, é de domínio.

O contorno é você abrir a página no seu navegador e salvar. Este script lê o
arquivo salvo e produz as linhas de `dados/elencos.csv`.

COMO SALVAR
-----------
No navegador, com a página de elenco aberta:

  Ctrl+S  →  "Página da Web, completa" ou "Página da Web, somente HTML"

Qualquer um dos dois serve — o parser só precisa do HTML. Salve um arquivo por
temporada e nomeie com o ano, por exemplo `elenco_2023.html`.

Use a aba **"Elenco detalhado"** (`/plus/1` na URL): ela traz data de
nascimento, nacionalidade, altura, pé e "no clube desde". A visão em galeria
(`/galerie/0`) tem menos colunas.

USO
---
  python importar_elenco_tm.py elenco_2023.html --temporada 2023
  python importar_elenco_tm.py *.html            # deduz o ano do nome do arquivo

O resultado é gravado em `dados/elencos_transfermarkt.csv`, com o schema
completo: número, nome, nascimento, idade, posição, nacionalidade (inclusive
dupla), altura e "no clube desde".

NÍVEL DE CONFIANÇA
------------------
Transfermarkt é **nível 2, CONFERÊNCIA**, conforme a seção 6 do CLAUDE.md.
Serve para montar o elenco e para saber quem investigar. A janela de registro
que vale para o claim continua sendo a do TMS.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from parser_tabelas import extrair_linhas, normalizar, parse_data

DIR_DADOS = Path("dados")
CSV_SAIDA = DIR_DADOS / "elencos_transfermarkt.csv"

CAMPOS = ["temporada", "numero", "nome", "nome_completo", "nascimento", "idade",
          "posicao", "nacionalidade", "altura", "pe", "no_clube_desde",
          "contrato_ate", "valor_mercado", "fonte", "bruto"]

# "23/07/1999 (26)" — assinatura da célula de nascimento no Transfermarkt.
RE_NASC_IDADE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})\s*\((\d{1,2})\)")
RE_ALTURA = re.compile(r"(\d[,.]\d{2})\s*m")
RE_LEGENDA = re.compile(r"\[([^\]]+)\]")
RE_NUMERO = re.compile(r"^\d{1,2}$")

POSICOES = [
    "goleiro", "zagueiro", "lateral-direito", "lateral-esquerdo", "lateral",
    "volante", "meio-campo defensivo", "meia-atacante", "meio-campo central",
    "meia direita", "meia esquerda", "ponta-direita", "ponta-esquerda",
    "segundo atacante", "centroavante", "atacante", "defensor", "meio-campo",
]

# Legendas de imagem que não são nacionalidade.
NAO_E_PAIS = ("transfermarkt", "logo", "escudo", "wappen", "botafogo", "clube")


def _achar_posicao(texto: str) -> str:
    n = normalizar(texto)
    for p in sorted(POSICOES, key=len, reverse=True):
        if p in n:
            return p
    return ""


def _achar_nacionalidade(celulas: list[str], nome: str) -> str:
    """As bandeiras são <img title="Brasil">; o coletor guarda como [Brasil].

    A foto do jogador também é <img title="...">, com o NOME dele. Sem excluir
    isso, o nome do atleta vira nacionalidade — e a dupla cidadania, que
    importa para saber por qual seleção ele pode ser cedido, se perde.
    """
    alvo = normalizar(nome)
    achadas = []
    for c in celulas:
        for leg in RE_LEGENDA.findall(c):
            n = normalizar(leg)
            if len(leg) < 3 or any(x in n for x in NAO_E_PAIS):
                continue
            if alvo and (n == alvo or n in alvo or alvo in n):
                continue                      # é a foto, não a bandeira
            if leg not in achadas:
                achadas.append(leg)
    return "/".join(achadas[:2])


def _limpar_nome(texto: str) -> str:
    t = RE_LEGENDA.sub(" ", texto)
    t = RE_NASC_IDADE.sub(" ", t)
    for p in POSICOES:
        t = re.sub(re.escape(p), " ", t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–|")
    # O TM repete o nome (link + tooltip): "VitinhoVitinho" ou "Vitinho Vitinho".
    metade = len(t) // 2
    if metade > 2 and t[:metade].strip() == t[metade:].strip():
        t = t[:metade].strip()
    return t.strip()


def extrair_elenco(html: str, temporada: str, fonte: str) -> list[dict]:
    saida: list[dict] = []
    vistos: set[str] = set()

    for l in extrair_linhas(html):
        linha = " | ".join(l.celulas)
        m = RE_NASC_IDADE.search(linha)
        if not m:
            continue                      # linha de elenco tem nascimento (idade)
        nascimento, idade = m.group(1), m.group(2)
        d = parse_data(nascimento)
        if d is None:
            continue

        # A célula do jogador é a maior que sobra depois de tirar data e números.
        candidatos = [c for c in l.celulas
                      if len(_limpar_nome(c)) >= 3 and not RE_NASC_IDADE.search(c)]
        nome = _limpar_nome(max(candidatos, key=len)) if candidatos else ""
        if not nome:
            continue

        numero = next((c.strip() for c in l.celulas[:2]
                       if RE_NUMERO.match(c.strip())), "")
        altura = next((am.group(1) for c in l.celulas
                       if (am := RE_ALTURA.search(c))), "")
        no_clube = ""
        for c in l.celulas:
            dd = parse_data(RE_LEGENDA.sub("", c).strip())
            if dd and dd != d:
                no_clube = dd.isoformat()
                break

        chave = f"{normalizar(nome)}|{d.isoformat()}"
        if chave in vistos:
            continue
        vistos.add(chave)

        saida.append({
            "temporada": temporada, "numero": numero, "nome": nome,
            "nome_completo": "", "nascimento": d.isoformat(), "idade": idade,
            "posicao": _achar_posicao(linha),
            "nacionalidade": _achar_nacionalidade(l.celulas, nome),
            "altura": altura, "pe": "", "no_clube_desde": no_clube,
            "contrato_ate": "", "valor_mercado": "", "fonte": fonte,
            "bruto": linha[:400],
        })

    return saida


def _temporada_do_nome(caminho: Path, informada: str | None) -> str:
    if informada:
        return informada
    m = re.search(r"(20\d{2})", caminho.name)
    return m.group(1) if m else "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivos", nargs="+", help="HTML(s) salvos do navegador")
    ap.add_argument("--temporada", help="ano; sem isso, deduz do nome do arquivo")
    args = ap.parse_args()

    todos: list[dict] = []
    for nome in args.arquivos:
        caminho = Path(nome)
        if not caminho.exists():
            print(f"  {caminho}: não encontrado")
            continue
        temporada = _temporada_do_nome(caminho, args.temporada)
        html = caminho.read_text(encoding="utf-8", errors="replace")
        linhas = extrair_elenco(html, temporada,
                                f"Transfermarkt (salvo do navegador) — {caminho.name}")
        com_nac = sum(1 for r in linhas if r["nacionalidade"])
        com_pos = sum(1 for r in linhas if r["posicao"])
        print(f"  {caminho.name}: temporada {temporada} · {len(linhas)} atletas "
              f"· {com_nac} com nacionalidade · {com_pos} com posição")
        if not linhas:
            print("     nenhuma linha reconhecida — confira se a página salva é a")
            print("     aba 'Elenco detalhado' e se o HTML veio completo")
        todos.extend(linhas)

    if not todos:
        print("\nNada extraído.")
        return 1

    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    with CSV_SAIDA.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(todos)
    print(f"\nGravado: {CSV_SAIDA} ({len(todos)} linhas)")

    nacs = sorted({r["nacionalidade"] for r in todos if r["nacionalidade"]})
    print(f"\nNacionalidades encontradas: {', '.join(nacs) if nacs else '(nenhuma)'}")
    print("\nConfira as estrangeiras contra selecoes_escopo.csv: nacionalidade")
    print("nova significa seleção nova no universo de partidas.")
    print("\nNível CONFERÊNCIA. A janela de registro que vale é a do TMS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
