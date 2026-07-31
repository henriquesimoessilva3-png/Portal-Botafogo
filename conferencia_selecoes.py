#!/usr/bin/env python3
"""
conferencia_selecoes.py — levantamento multi-fonte de jogos por seleção,
para o FIFA Club Benefits Programme 2026 (Botafogo SAF).

Lê a mesma informação em DUAS fontes independentes (Transfermarkt e oGol),
cruza com a janela de registro do atleta no clube e aponta onde as fontes
DIVERGEM. Divergência não é erro do script: é exatamente o que precisa ir
para conferência na súmula oficial.

HIERARQUIA DE FONTES (leia antes de usar o resultado)
-----------------------------------------------------
  1. PROVA      — TMS interno do clube + súmula oficial CONMEBOL/CAF/CONCACAF.
                  É o único nível que a FIFA aceita. O script NÃO cobre isso.
  2. CONFERÊNCIA — Transfermarkt e oGol. É o que este script faz. Serve para
                  achar o que investigar e para detectar erro de uma fonte só.
  3. CONTEXTO   — notícia. Data a convocação e explica cortes/substituições,
                  mas não é súmula. Não use notícia para decidir elegibilidade.

ARMADILHA CONHECIDA — HOMÔNIMO
------------------------------
O Botafogo teve dois "Vitinho" ao mesmo tempo: Victor Alexander da Silva
(lateral, 23/07/1999) e Vitor da Silveira Rodrigues (atacante, 14/06/2007).
Por isso o CSV exige ID e data de nascimento, e o script confere a data na
página antes de aceitar os dados. Nunca chave por nome.

USO
---
  pip install playwright pandas openpyxl && playwright install chromium

  python conferencia_selecoes.py                    # roda contra os sites
  python conferencia_selecoes.py --debug            # + dumpa o HTML em debug_html/
  python conferencia_selecoes.py --from-html DIR    # reprocessa dumps, SEM rede
  python conferencia_selecoes.py --self-test        # testa o parser, SEM rede

O modo --from-html é o que fecha o ciclo de conserto do parser: rode uma vez
com --debug para capturar o HTML, depois itere em cima dos dumps quantas vezes
precisar sem tocar de novo no Transfermarkt.

O parsing propriamente dito mora em parser_tabelas.py, como função pura de
HTML → Registros, para poder ser testado sem navegador e sem rede.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from parser_tabelas import (
    VALOR_POR_PARTIDA,
    Registro,
    conferir_nascimento,
    extrair_de_html,
    extrair_linhas,
    interpretar_linhas,
    parse_data,
)

CSV_ENTRADA = Path("atletas.csv")
XLSX_SAIDA = Path("conferencia_selecoes.xlsx")
DIR_DEBUG = Path("debug_html")

# Intencional: navegador visível e pausa longa entre requisições. Não reduza —
# o bloqueio do Transfermarkt não é técnico, é de comportamento.
PAUSA = (4.0, 9.0)
HEADLESS = False

MODELO_CSV = (
    "atleta,nascimento,selecao,url_transfermarkt,url_ogol,"
    "registro_inicio,registro_fim,origem_da_janela\n"
    "Vitinho,1999-07-23,Brasil,,,2024-08-01,,ESTIMADA - substituir por TMS\n"
    "Lucas Perri,1997-12-13,Brasil,,,2023-01-01,2023-12-31,ESTIMADA - substituir por TMS\n"
    "Igor Jesus,2001-01-01,Brasil,,,2024-07-01,2025-08-31,ESTIMADA - substituir por TMS\n"
)


def janela_e_estimada(linha: dict) -> bool:
    """A coluna origem_da_janela marca o que veio de imprensa.

    O briefing é explícito: se um resultado depende de janela estimada, isso
    tem que aparecer no resultado — não pode sair como fato.
    """
    return "estimada" in (linha.get("origem_da_janela") or "").strip().lower()


def slug_de(atleta: str, fonte: str) -> str:
    return re.sub(r"\W+", "_", f"{atleta}_{fonte}")


def carregar() -> list[dict]:
    if not CSV_ENTRADA.exists():
        CSV_ENTRADA.write_text(MODELO_CSV, encoding="utf-8")
        print(f"Criei {CSV_ENTRADA}. Preencha as URLs e rode de novo.")
        print("  url_transfermarkt: aba 'Jogos pela seleção' do atleta")
        print("  url_ogol:          página do atleta no ogol.com.br")
        print("  registro_fim vazio = ainda no elenco")
        sys.exit(0)
    with CSV_ENTRADA.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def aceitar_cookies(page) -> None:
    for sel in ("#onetrust-accept-btn-handler", "button:has-text('Aceitar')",
                "button:has-text('ACEITO')", "button:has-text('Concordo')",
                "button:has-text('Aceitar todos')"):
        try:
            page.locator(sel).first.click(timeout=2500)
            page.wait_for_timeout(700)
            return
        except Exception:
            continue


# --------------------------------------------------------------------------- #
# Coleta ao vivo
# --------------------------------------------------------------------------- #

def coletar_ao_vivo(entradas: list[dict], debug: bool
                    ) -> tuple[list[Registro], list[str]]:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    registros: list[Registro] = []
    alertas: list[str] = []

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=HEADLESS)
        ctx = navegador.new_context(
            locale="pt-BR", viewport={"width": 1400, "height": 1000},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        )
        page = ctx.new_page()

        for linha in entradas:
            atleta = (linha.get("atleta") or "").strip()
            if not atleta:
                continue
            nasc = parse_data(linha.get("nascimento"))
            ini = parse_data(linha.get("registro_inicio"))
            fim = parse_data(linha.get("registro_fim"))
            estimada = janela_e_estimada(linha)
            if nasc is None:
                alertas.append(
                    f"{atleta}: sem data de nascimento no CSV — a guarda "
                    f"anti-homônimo não pode rodar. Tudo vira CONFERIR.")
            print(f"\n→ {atleta}")

            for fonte, chave in (("Transfermarkt", "url_transfermarkt"),
                                 ("oGol", "url_ogol")):
                url = (linha.get(chave) or "").strip()
                if not url:
                    alertas.append(f"{atleta}: sem URL de {fonte}")
                    print(f"   {fonte}: url ausente")
                    continue
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                    aceitar_cookies(page)
                    page.wait_for_selector("table", timeout=20_000)
                except PWTimeout:
                    alertas.append(f"{atleta}: {fonte} não carregou (timeout)")
                    print(f"   {fonte}: timeout")
                    # A pausa vale para QUALQUER requisição, não só as que deram
                    # certo — o site conta o acesso do mesmo jeito.
                    time.sleep(random.uniform(*PAUSA))
                    continue
                except Exception as e:
                    alertas.append(f"{atleta}: {fonte} falhou — {type(e).__name__}")
                    print(f"   {fonte}: erro {type(e).__name__}")
                    time.sleep(random.uniform(*PAUSA))
                    continue

                html = page.content()
                try:
                    corpo = page.inner_text("body")
                except Exception:
                    corpo = ""

                # O dump é salvo ANTES de qualquer decisão de descarte: se a
                # identidade não confere, é justamente o HTML que explica por quê.
                if debug:
                    DIR_DEBUG.mkdir(exist_ok=True)
                    base = DIR_DEBUG / slug_de(atleta, fonte)
                    base.with_suffix(".html").write_text(html, encoding="utf-8")
                    base.with_suffix(".json").write_text(json.dumps({
                        "atleta": atleta, "fonte": fonte, "url": url,
                        "nascimento": linha.get("nascimento", ""),
                        "registro_inicio": linha.get("registro_inicio", ""),
                        "registro_fim": linha.get("registro_fim", ""),
                        "origem_da_janela": linha.get("origem_da_janela", ""),
                    }, ensure_ascii=False, indent=2), encoding="utf-8")

                identidade = conferir_nascimento(corpo, nasc)
                if identidade == "nao_confere":
                    alertas.append(
                        f"{atleta}: {fonte} — data de nascimento NÃO confere. "
                        f"Possível homônimo. Dados descartados.")
                    print(f"   {fonte}: nascimento não confere — descartado")
                    time.sleep(random.uniform(*PAUSA))
                    continue
                if identidade == "nao_encontrada":
                    alertas.append(
                        f"{atleta}: {fonte} — data de nascimento não localizada "
                        f"na página. Identidade NÃO confirmada; registros vão "
                        f"para conferência.")

                achados = extrair_de_html(
                    html, atleta, linha.get("nascimento", ""), fonte, ini, fim,
                    janela_estimada=estimada,
                    identidade_ok=(identidade == "confere"))
                if not achados:
                    alertas.append(
                        f"{atleta}: {fonte} — nenhuma linha reconhecida. "
                        f"Rode com --debug e confira o dump.")
                eleg = sum(1 for r in achados if r.veredito.startswith("ELEGÍVEL"))
                print(f"   {fonte}: {len(achados)} no ciclo · {eleg} elegíveis")
                registros.extend(achados)
                time.sleep(random.uniform(*PAUSA))

        navegador.close()

    return registros, alertas


# --------------------------------------------------------------------------- #
# Reprocessamento offline
# --------------------------------------------------------------------------- #

def coletar_de_dumps(diretorio: Path, entradas: list[dict]
                     ) -> tuple[list[Registro], list[str]]:
    """Reprocessa os HTML salvos por --debug. Sem rede, sem navegador.

    É este modo que torna o conserto do parser um ciclo de segundos. O
    metadado de cada dump vem do .json irmão; se ele não existir, cai para o
    atletas.csv casando pelo nome do arquivo.
    """
    registros: list[Registro] = []
    alertas: list[str] = []

    por_slug = {}
    for linha in entradas:
        atleta = (linha.get("atleta") or "").strip()
        for fonte in ("Transfermarkt", "oGol"):
            por_slug[slug_de(atleta, fonte)] = (atleta, fonte, linha)

    arquivos = sorted(diretorio.glob("*.html"))
    if not arquivos:
        alertas.append(f"Nenhum .html em {diretorio}")
        return registros, alertas

    for caminho in arquivos:
        slug = caminho.stem
        meta_path = caminho.with_suffix(".json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            atleta, fonte = meta["atleta"], meta["fonte"]
            linha = meta
        elif slug in por_slug:
            atleta, fonte, linha = por_slug[slug]
        else:
            alertas.append(f"{caminho.name}: não dá para saber de quem é. Pulado.")
            continue

        html = caminho.read_text(encoding="utf-8", errors="replace")
        nasc = parse_data(linha.get("nascimento"))
        ini = parse_data(linha.get("registro_inicio"))
        fim = parse_data(linha.get("registro_fim"))
        estimada = janela_e_estimada(linha)

        # Sem navegador não há inner_text; o texto cru do HTML serve para a
        # guarda de nascimento (que só procura a data no corpo).
        texto = re.sub(r"<[^>]+>", " ", html)
        identidade = conferir_nascimento(texto, nasc)
        if identidade == "nao_confere":
            alertas.append(f"{atleta}: {fonte} — nascimento não confere no dump. "
                           f"Descartado.")
            continue
        if identidade == "nao_encontrada":
            alertas.append(f"{atleta}: {fonte} — nascimento não localizado no dump.")

        linhas = extrair_linhas(html)
        achados = interpretar_linhas(
            linhas, atleta, linha.get("nascimento", ""), fonte, ini, fim,
            janela_estimada=estimada, identidade_ok=(identidade == "confere"))
        eleg = sum(1 for r in achados if r.veredito.startswith("ELEGÍVEL"))
        print(f"  {caminho.name}: {len(linhas)} linhas · {len(achados)} partidas "
              f"· {eleg} elegíveis")
        if not achados:
            alertas.append(f"{atleta}: {fonte} — dump não produziu nenhuma partida.")
        registros.extend(achados)

    return registros, alertas


# --------------------------------------------------------------------------- #
# Relatório
# --------------------------------------------------------------------------- #

def gerar_relatorio(registros: list[Registro], alertas: list[str]) -> None:
    df = pd.DataFrame([asdict(r) for r in registros])

    # ---- reconciliação: mesma partida vista por fontes diferentes ---------- #
    piv = (df.pivot_table(index=["atleta", "data"], columns="fonte",
                          values="veredito", aggfunc="first")
             .reset_index())
    # O código original só criava a coluna 'divergencia' quando AS DUAS fontes
    # existiam no DataFrame; com uma fonte só, a planilha saía sem a marcação.
    for col in ("Transfermarkt", "oGol"):
        if col not in piv.columns:
            piv[col] = pd.NA

    def classificar(r):
        tm, og = r["Transfermarkt"], r["oGol"]
        if pd.isna(tm) or pd.isna(og):
            return "SÓ EM UMA FONTE"
        return "OK" if tm == og else "DIVERGENTE"

    piv["divergencia"] = piv.apply(classificar, axis=1)

    concordantes = piv[piv["divergencia"] == "OK"][["atleta", "data"]]
    base = df[df["veredito"].str.startswith("ELEGÍVEL")].merge(
        concordantes, on=["atleta", "data"])

    if base.empty:
        resumo = pd.DataFrame(columns=["atleta", "partidas_confirmadas",
                                       "estimativa_usd",
                                       "depende_de_janela_estimada"])
    else:
        unicos = base.drop_duplicates(subset=["atleta", "data"])
        resumo = unicos.groupby("atleta").agg(
            partidas_confirmadas=("data", "size"),
            depende_de_janela_estimada=("janela_estimada", "any"),
        ).reset_index()
        resumo["estimativa_usd"] = resumo["partidas_confirmadas"] * VALOR_POR_PARTIDA
        resumo = resumo[["atleta", "partidas_confirmadas", "estimativa_usd",
                         "depende_de_janela_estimada"]]

    fila = df[df["veredito"].str.startswith("CONFERIR")][
        ["atleta", "fonte", "data", "competicao", "status", "veredito", "bruto"]]

    with pd.ExcelWriter(XLSX_SAIDA, engine="openpyxl") as xls:
        resumo.to_excel(xls, sheet_name="Resumo", index=False)
        piv.to_excel(xls, sheet_name="Reconciliacao", index=False)
        fila.to_excel(xls, sheet_name="Fila de conferencia", index=False)
        df.to_excel(xls, sheet_name="Partidas", index=False)
        pd.DataFrame({"alerta": alertas or ["nenhum"]}).to_excel(
            xls, sheet_name="Alertas", index=False)

    print(f"\nPronto: {XLSX_SAIDA}")
    print("\nSó entram no resumo as partidas em que AS DUAS FONTES concordam.")
    print("Abra a aba Reconciliacao: DIVERGENTE e SÓ EM UMA FONTE são as que")
    print("precisam de conferência na súmula oficial antes de qualquer claim.")
    print("A aba 'Fila de conferencia' lista o que o parser não soube decidir.\n")
    print(resumo.to_string(index=False) if not resumo.empty
          else "(nenhuma partida confirmada pelas duas fontes)")
    if not resumo.empty and resumo["depende_de_janela_estimada"].any():
        print("\nATENÇÃO: linhas com depende_de_janela_estimada = True usam janela")
        print("de registro vinda de imprensa, não do TMS. Confirme antes do claim.")
    if alertas:
        print("\nAlertas:")
        for a in alertas:
            print("  -", a)


# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true",
                    help="salva o HTML de cada página em debug_html/")
    ap.add_argument("--from-html", metavar="DIR",
                    help="reprocessa dumps já salvos, sem rede nem navegador")
    ap.add_argument("--self-test", action="store_true",
                    help="roda os testes do parser e sai")
    args = ap.parse_args()

    if args.self_test:
        import test_parser
        raise SystemExit(test_parser.main())

    entradas = carregar()

    if args.from_html:
        print(f"Reprocessando dumps de {args.from_html} (sem rede)\n")
        registros, alertas = coletar_de_dumps(Path(args.from_html), entradas)
    else:
        registros, alertas = coletar_ao_vivo(entradas, args.debug)

    if not registros:
        print("\nNada extraído. Rode com --debug e confira o HTML salvo,")
        print("depois itere com --from-html debug_html/ (sem gastar requisição).")
        if alertas:
            print("\nAlertas:")
            for a in alertas:
                print("  -", a)
        return

    gerar_relatorio(registros, alertas)


if __name__ == "__main__":
    main()
