#!/usr/bin/env python3
"""
elencos.py — consolida os elencos do Botafogo 2022–2026 numa tabela única.

O QUE ESTE SCRIPT FAZ
---------------------
Junta o que o projeto JÁ TEM, sem inventar nada:

  * abas "6. Elenco 2024" e "7. Elenco 2025" da planilha mestre
    (posição, nacionalidade, no clube desde) — fonte: arquivo Fogo na Rede;
  * datas de nascimento do `atletas.csv`, casadas por nome normalizado;
  * a aba "8. Lacunas 2022-2023", que documenta por que 2022 e 2023 não existem.

Campos que a planilha não tem — nome completo, altura, naturalidade, número da
camisa — saem em branco e marcados em `lacunas`. Não são preenchidos por
inferência: nome completo e data de nascimento são justamente o que separa os
dois "Vitinho", e errar isso é o erro nº 1 da seção 5 do CLAUDE.md.

O QUE ESTE SCRIPT NÃO FAZ
--------------------------
Não coleta. Os elencos de **2022, 2023 e 2026 não existem em nenhuma fonte
local** — a aba 8 da planilha registra isso: o Fogo na Rede só mantém arquivo de
2024 e 2025, e o Transfermarkt exige navegador real.

Para completar, é preciso rodar a coleta numa máquina com acesso aos domínios.
`--modelo-coleta` gera o CSV em branco com o schema certo para isso.

USO
---
  python elencos.py                    # consolida o que existe
  python elencos.py --modelo-coleta    # gera dados/elencos_a_coletar.csv
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path

from parser_tabelas import normalizar, parse_data

PLANILHA = Path("FIFA_Club_Benefits_2026_Botafogo.xlsx")
CSV_ATLETAS = Path("atletas.csv")
DIR_DADOS = Path("dados")
CSV_SAIDA = DIR_DADOS / "elencos.csv"
CSV_MODELO = DIR_DADOS / "elencos_a_coletar.csv"

CAMPOS = ["temporada", "nome", "nome_completo", "nascimento", "posicao",
          "nacionalidade", "no_clube_desde", "selecao_com_eliminatorias",
          "fonte", "lacunas"]

# Temporadas que o levantamento precisa cobrir e o que existe de fonte local.
TEMPORADAS = {
    "2022": None,   # sem fonte local — ver aba 8 da planilha
    "2023": None,   # idem
    "2024": "6. Elenco 2024",
    "2025": "7. Elenco 2025",
    "2026": None,   # temporada corrente, sem aba na planilha
}

# Nacionalidades cuja seleção disputou Eliminatórias 2026 e que, portanto,
# geram linha no universo de partidas. Vem de selecoes_escopo.csv.
NACIONALIDADES_EM_ESCOPO = {
    "brasil": "Brasil", "argentina": "Argentina", "uruguai": "Uruguai",
    "paraguai": "Paraguai", "equador": "Equador", "venezuela": "Venezuela",
    "colombia": "Colombia", "angola": "Angola", "nicaragua": "Nicaragua",
    "panama": "Panama", "finlandia": "Finlandia", "espanha": "Espanha",
    "marrocos": "Marrocos", "franca/marrocos": "Marrocos",
}


def sem_acento(s: str) -> str:
    t = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in t if not unicodedata.combining(c))


def apelido(nome: str) -> str:
    """'Vitinho (Victor Alexander da Silva)' -> 'Vitinho'."""
    return (nome or "").split("(")[0].strip()


def nome_entre_parenteses(nome: str) -> str:
    if "(" in (nome or "") and ")" in nome:
        return nome.split("(", 1)[1].rsplit(")", 1)[0].strip()
    return ""


def carregar_atletas() -> list[dict]:
    if not CSV_ATLETAS.exists():
        return []
    with CSV_ATLETAS.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def casar_atleta(nome: str, atletas: list[dict]) -> dict | None:
    """Casa o nome do elenco com uma linha de atletas.csv.

    Deliberadamente conservador: só aceita igualdade normalizada ou o nome do
    elenco contido no do CSV (ou vice-versa) quando o casamento é ÚNICO. Se
    duas linhas casam, devolve None — nome ambíguo é exatamente a armadilha do
    homônimo, e o certo é deixar em branco para conferência humana.
    """
    alvos = {normalizar(apelido(nome)), normalizar(nome_entre_parenteses(nome))}
    alvos.discard("")

    exatos = [a for a in atletas if normalizar(a["atleta"]) in alvos]
    if len(exatos) == 1:
        return exatos[0]
    if len(exatos) > 1:
        return None

    parciais = []
    for a in atletas:
        na = normalizar(a["atleta"])
        for alvo in alvos:
            if len(alvo) >= 5 and (alvo in na or na in alvo):
                parciais.append(a)
                break
    return parciais[0] if len(parciais) == 1 else None


def ler_aba(aba: str) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(PLANILHA, data_only=True)
    ws = wb[aba]
    linhas = []
    cabecalho_visto = False
    for row in ws.iter_rows(values_only=True):
        vals = [(str(c).strip() if c is not None else "") for c in row]
        if not any(vals):
            continue
        if not cabecalho_visto:
            if vals[0].strip().lower() == "posicao":
                cabecalho_visto = True
            continue
        if vals[0].lower().startswith("total de atletas"):
            continue
        linhas.append({"posicao": vals[0], "nome": vals[1],
                       "nacionalidade": vals[2], "no_clube_desde": vals[3]})
    return linhas


def consolidar() -> tuple[list[dict], list[str]]:
    atletas = carregar_atletas()
    saida: list[dict] = []
    notas: list[str] = []

    for temporada, aba in TEMPORADAS.items():
        if aba is None:
            notas.append(f"{temporada}: sem fonte local — nenhuma linha gerada.")
            continue
        if not PLANILHA.exists():
            notas.append(f"{temporada}: planilha {PLANILHA} não encontrada.")
            continue

        for r in ler_aba(aba):
            nome = r["nome"]
            if not nome:
                continue
            a = casar_atleta(nome, atletas)
            nasc = (a or {}).get("nascimento", "")
            nac = normalizar(r["nacionalidade"])

            lacunas = []
            if not nasc:
                lacunas.append("sem data de nascimento")
            lacunas.append("sem nome completo")
            if not nome_entre_parenteses(nome) and not nasc:
                lacunas.append("IDENTIDADE NAO CONFIRMADA")

            saida.append({
                "temporada": temporada,
                "nome": apelido(nome),
                "nome_completo": nome_entre_parenteses(nome),
                "nascimento": nasc,
                "posicao": r["posicao"],
                "nacionalidade": r["nacionalidade"],
                "no_clube_desde": r["no_clube_desde"],
                "selecao_com_eliminatorias":
                    NACIONALIDADES_EM_ESCOPO.get(nac, ""),
                "fonte": f"planilha mestre, aba '{aba}' (Fogo na Rede)",
                "lacunas": "; ".join(lacunas),
            })

    return saida, notas


def gerar_modelo() -> None:
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    with CSV_MODELO.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        for t in ("2022", "2023", "2026"):
            w.writerow({"temporada": t, "nome": "", "nome_completo": "",
                        "nascimento": "", "posicao": "", "nacionalidade": "",
                        "no_clube_desde": "",
                        "selecao_com_eliminatorias": "", "fonte": "",
                        "lacunas": "A COLETAR"})
    print(f"Modelo gravado em {CSV_MODELO}")
    print("Preencha com a coleta de Transfermarkt/oGol e junte ao elencos.csv.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo-coleta", action="store_true")
    args = ap.parse_args()

    if args.modelo_coleta:
        gerar_modelo()
        return 0

    linhas, notas = consolidar()
    DIR_DADOS.mkdir(parents=True, exist_ok=True)
    with CSV_SAIDA.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(linhas)

    print(f"Gravado: {CSV_SAIDA} ({len(linhas)} linhas)\n")

    por_temp: dict[str, int] = {}
    for r in linhas:
        por_temp[r["temporada"]] = por_temp.get(r["temporada"], 0) + 1
    print("Atletas por temporada:")
    for t in TEMPORADAS:
        n = por_temp.get(t, 0)
        marca = "" if n else "   <- SEM FONTE LOCAL"
        print(f"  {t}: {n}{marca}")

    com_nasc = sum(1 for r in linhas if r["nascimento"])
    print(f"\nCom data de nascimento: {com_nasc}/{len(linhas)}")
    print(f"Com nome completo:      "
          f"{sum(1 for r in linhas if r['nome_completo'])}/{len(linhas)}")

    estrangeiros = sorted({r["selecao_com_eliminatorias"] for r in linhas
                           if r["selecao_com_eliminatorias"]})
    print(f"\nSeleções em escopo representadas no elenco: {', '.join(estrangeiros)}")

    if notas:
        print("\nLacunas:")
        for n in notas:
            print("  -", n)
    print("\nNome completo e altura não constam de nenhuma fonte local.")
    print("Rode --modelo-coleta e complete numa máquina com acesso aos sites.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
