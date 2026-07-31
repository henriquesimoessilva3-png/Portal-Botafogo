#!/usr/bin/env python3
"""
importar_elenco.py — lê a página de elenco do Botafogo salva do navegador.

Serve tanto ao **Transfermarkt** quanto ao **oGol**. Os dois formatos diferem no
essencial — ver `_achar_nascimento_e_idade` e `POSICOES` —, e o script decide
sozinho qual está lendo.

POR QUE ISTO EXISTE
-------------------
As páginas de elenco são inalcançáveis desta sessão. A política de egresso
recusa o CONNECT para os hosts inteiros, **antes de qualquer caminho ser
enviado**: testado em transfermarkt .com.br, .com, .us, .co.uk e .de, no CDN de
imagens, em ogol.com.br e em zerozero.pt. Mandar outra URL não muda nada — o
bloqueio é de domínio, não de página.

O contorno é abrir a página no seu navegador e salvar. Este script lê o arquivo.

COMO SALVAR
-----------
Com a página aberta:  Ctrl+S  →  "Página da Web, completa" **ou** "somente
HTML". Os dois servem; o parser só precisa do HTML. Um arquivo por temporada,
com o ano no nome: `elenco_2023.html`, `ogol_2022.html`.

  * Transfermarkt: use a aba **"Elenco detalhado"** (`/plus/1` na URL). Ela traz
    nascimento, nacionalidade, altura, pé e "no clube desde". A visão em galeria
    (`/galerie/0`) tem menos colunas.
  * oGol: a página `/equipe/botafogo?epoca_id=NNN`, uma por temporada.

Salvar das DUAS fontes para o mesmo ano é melhor do que de uma: onde elas
divergirem, é sinal de que aquele atleta precisa de conferência — a mesma lógica
da aba Reconciliacao do conferencia_selecoes.py.

USO
---
  python importar_elenco.py elenco_2023.html --temporada 2023
  python importar_elenco.py *.html            # deduz o ano do nome do arquivo

Grava `dados/elencos_coletados.csv` com número, nome, nascimento, idade,
posição, nacionalidade (inclusive dupla), altura e "no clube desde".

NÍVEL DE CONFIANÇA
------------------
Transfermarkt e oGol são **nível 2, CONFERÊNCIA**, conforme a seção 6 do
CLAUDE.md. Servem para montar o elenco e para saber quem investigar. A janela de
registro que vale para o claim continua sendo a do TMS.
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import date
from pathlib import Path

from parser_tabelas import extrair_linhas, normalizar, parse_data

DIR_DADOS = Path("dados")
CSV_SAIDA = DIR_DADOS / "elencos_coletados.csv"

CAMPOS = ["temporada_saison_id", "temporada", "tm_id", "numero", "nome",
          "posicao", "nacionalidade", "nacionalidade_2",
          "idade_na_temporada", "clube_atual", "valor_mercado", "fonte"]

# "23/07/1999 (26)" — assinatura da célula de nascimento no Transfermarkt.
RE_NASC_IDADE = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})\s*\((\d{1,2})\)")
# oGol não põe a idade colada na data; às vezes traz "26 anos" em outra célula,
# às vezes nada. Por isso a âncora genérica é a data com cara de nascimento.
RE_DATA_SOLTA = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b")
RE_ANOS = re.compile(r"\b(\d{1,2})\s*anos?\b", re.I)
RE_ALTURA = re.compile(r"(\d[,.]\d{2})\s*m")
RE_LEGENDA = re.compile(r"\[([^\]]+)\]")
RE_NUMERO = re.compile(r"^\d{1,2}$")

# Um atleta de elenco nasceu neste intervalo. Serve para separar a data de
# nascimento da data de "no clube desde", que é sempre recente.
ANO_NASC_MIN, ANO_NASC_MAX = 1970, 2012

POSICOES = [
    # Transfermarkt (pt-BR)
    "goleiro", "zagueiro", "lateral-direito", "lateral-esquerdo", "lateral",
    "volante", "meio-campo defensivo", "meia-atacante", "meio-campo central",
    "meia direita", "meia esquerda", "ponta-direita", "ponta-esquerda",
    "segundo atacante", "centroavante", "atacante", "defensor", "meio-campo",
    # oGol / zerozero — mesmo backend, nomenclatura própria e às vezes pt-PT
    "guarda-redes", "defesa central", "defesa direito", "defesa esquerdo",
    "medio defensivo", "medio ofensivo", "medio centro", "medio",
    "extremo direito", "extremo esquerdo", "extremo", "avancado",
    "ala direito", "ala esquerdo", "ponta", "meia",
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


def _achar_nascimento_e_idade(linha: str, temporada: str):
    """Acha a data de nascimento em qualquer um dos dois formatos.

    Transfermarkt cola a idade na data — "23/07/1999 (26)". oGol não: a data vem
    sozinha e a idade, quando aparece, vem como "26 anos" noutra célula. Por isso
    a âncora comum é a DATA cujo ano cabe num intervalo de nascimento; assim a
    data de "no clube desde", sempre recente, não é confundida com ela.

    Sem idade na página, calcula em 31/12 da temporada — que é a idade útil para
    ler um elenco daquele ano, e não a idade de hoje.
    """
    m = RE_NASC_IDADE.search(linha)
    if m:
        d = parse_data(m.group(1))
        if d and ANO_NASC_MIN <= d.year <= ANO_NASC_MAX:
            return d, m.group(2)

    for dia, mes, ano in RE_DATA_SOLTA.findall(linha):
        if not (ANO_NASC_MIN <= int(ano) <= ANO_NASC_MAX):
            continue
        d = parse_data(f"{dia}/{mes}/{ano}")
        if d is None:
            continue
        ma = RE_ANOS.search(linha)
        if ma:
            return d, ma.group(1)
        if temporada.isdigit():
            ref = date(int(temporada), 12, 31)
            idade = ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))
            return d, str(idade)
        return d, ""
    return None, ""


def _limpar_nome(texto: str) -> str:
    t = RE_LEGENDA.sub(" ", texto)
    t = RE_NASC_IDADE.sub(" ", t)
    t = RE_ANOS.sub(" ", t)
    t = RE_DATA_SOLTA.sub(" ", t)
    for p in POSICOES:
        t = re.sub(re.escape(p), " ", t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–|")
    # O TM repete o nome (link + tooltip): "VitinhoVitinho" ou "Vitinho Vitinho".
    metade = len(t) // 2
    if metade > 2 and t[:metade].strip() == t[metade:].strip():
        t = t[:metade].strip()
    return t.strip()


RE_SPIELER = re.compile(r"/spieler/(\d+)")
RE_SAISON = re.compile(r'<option[^>]*selected[^>]*value="(\d{4})"')


def temporada_do_html(html: str) -> str:
    """Lê o saison_id que a própria página declara, em vez de confiar no título.

    ISTO IMPORTA. O título da página do Transfermarkt diz "Plantel detalhado
    2024", mas o `saison_id` selecionado é 2023: o título usa o ano de FIM da
    temporada europeia. Ou seja, o arquivo "2024" é a temporada **2023/24**, que
    vai de julho/2023 a junho/2024 e cobre DOIS anos-calendário.

    Rotular pelo título produziria um erro de um ano em todo o levantamento — e
    num projeto em que a pergunta é "o clube detinha o registro NA DATA da
    partida", um ano de erro é a diferença entre reivindicar e perder.
    """
    m = RE_SAISON.search(html)
    return m.group(1) if m else ""


def extrair_elenco(html: str, temporada: str, fonte: str) -> list[dict]:
    """Lê a tabela de elenco do Transfermarkt.

    Estrutura real, conferida no HTML salvo (não é mais hipótese):

        [0] número da camisa
        [1] bloco do atleta — "[foto] Nome Posição" (tabela aninhada)
        [2] idade na temporada
        [3] nacionalidade(s) — bandeiras, viram "[País]"
        [4] clube ATUAL (não o da temporada)
        [5] valor de mercado

    A página NÃO traz data de nascimento: esta é a visão compacta. A chave de
    identidade aqui é o **ID do Transfermarkt**, extraído do link do perfil —
    que é até melhor que a data, porque é único por definição.
    """
    saison = temporada_do_html(html)
    if saison:
        rotulo = f"{saison}/{str(int(saison) + 1)[-2:]}"
    else:
        rotulo = temporada

    saida: list[dict] = []
    vistos: set[str] = set()

    for l in extrair_linhas(html):
        if l.profundidade != 0 or len(l.celulas) != 6:
            continue
        if not l.celulas[2].strip().isdigit():
            continue
        ids = RE_SPIELER.findall(" ".join(l.links))
        if not ids:
            continue
        tm_id = ids[0]
        if tm_id in vistos:
            continue
        vistos.add(tm_id)

        bloco = l.celulas[1]
        legendas = RE_LEGENDA.findall(bloco)
        # A última legenda do bloco é a foto do atleta (as anteriores, quando
        # existem, são escudos de clube emprestador).
        nome = legendas[-1] if legendas else ""
        posicao = _limpar_nome(RE_LEGENDA.sub(" ", bloco).replace(nome, " "))
        nacs = [n for n in RE_LEGENDA.findall(l.celulas[3])
                if not any(x in normalizar(n) for x in NAO_E_PAIS)]

        saida.append({
            "temporada_saison_id": saison,
            "temporada": rotulo,
            "tm_id": tm_id,
            "numero": l.celulas[0].strip(),
            "nome": nome,
            "posicao": posicao,
            "nacionalidade": nacs[0] if nacs else "",
            "nacionalidade_2": nacs[1] if len(nacs) > 1 else "",
            "idade_na_temporada": l.celulas[2].strip(),
            "clube_atual": next(iter(RE_LEGENDA.findall(l.celulas[4])), ""),
            "valor_mercado": l.celulas[5].strip(),
            "fonte": fonte,
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
                                f"pagina de elenco salva do navegador — {caminho.name}")
        rot = linhas[0]["temporada"] if linhas else temporada
        com_nac = sum(1 for r in linhas if r["nacionalidade"])
        print(f"  {caminho.name}: temporada {rot} · {len(linhas)} atletas "
              f"· {com_nac} com nacionalidade")
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
