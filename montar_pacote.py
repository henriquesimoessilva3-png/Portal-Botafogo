#!/usr/bin/env python3
"""
montar_pacote.py — empacota o levantamento como um portal do hub.

Monta a pasta `Portal Fifa Club Benefits/`, no mesmo formato dos outros cards do
hub: um diretório que se serve sozinho numa porta, sem build e sem dependência
de rede.

  python montar_pacote.py

Gera a pasta e um .zip ao lado. Basta descompactar dentro de `analytics/`.

O QUE VAI DENTRO
----------------
  index.html          a página que o card abre — autossuficiente
  iniciar.command     duplo clique no macOS: sobe :5066 e abre o navegador
  iniciar.sh          o mesmo, pelo terminal
  LEIA-ME.md          o que é, como rodar, como regerar
  dados/              as tabelas do levantamento, em CSV e JSON
  codigo/             os geradores e os testes
  documentos/         o PDF completo e o contexto do projeto

Servir exige só `python3`. As bibliotecas de `codigo/` só entram se alguém for
regerar o levantamento.
"""

from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path

PASTA = Path("Portal Fifa Club Benefits")
PORTA = 5066

# Tabelas geradas ficam em dados/. As duas de ENTRADA ficam na raiz, como no
# repositório — é de lá que o código as lê, e misturar entrada com saída é o
# jeito mais rápido de alguém sobrescrever a errada.
DADOS = ["dados/partidas_universo.csv", "dados/relacoes.csv",
         "dados/partidas_a_conferir.csv", "dados/elencos_coletados.csv",
         "dados/elencos.csv", "dados/checagem_aritmetica.csv",
         "dados/parte2_cessao.json",
         "dados/tms_extrato.csv", "dados/conferencia_tms.json"]

ENTRADAS = ["atletas.csv", "selecoes_escopo.csv"]

CODIGO = ["parser_tabelas.py", "partidas_universo.py", "relacoes.py",
          "checagem_aritmetica.py", "parte2_cessao.py", "gerar_relatorio_web.py",
          "gerar_parte2_pdf.py", "importar_elenco.py", "importar_openfootball.py",
          "conferencia_selecoes.py", "elencos.py", "conferencia_tms.py",
          "montar_pacote.py",
          "test_parser.py", "test_universo.py"]

DOCUMENTOS = ["levantamento_fifa_botafogo_completo.pdf",
              "levantamento_fifa_botafogo.pdf",
              "CLAUDE.md", "STATUS.md", "HANDOFF_FIFA.md", "COLETA_LOCAL.md",
              "CONTEXTO_SESSAO_LOCAL.md",
              "FIFA_Club_Benefits_2026_Botafogo.xlsx"]

INICIAR_SH = f"""#!/bin/bash
# Levantamento FIFA — Club Benefits 2026
# Sobe a página em http://localhost:{PORTA}. Ctrl+C encerra.

cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 não encontrado. Instale o Python 3 e rode de novo."
  exit 1
fi

if lsof -nP -iTCP:{PORTA} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "A porta {PORTA} já está em uso — o portal provavelmente já está no ar."
  echo "Abra http://localhost:{PORTA}"
  exit 0
fi

echo "Levantamento FIFA · Club Benefits 2026"
echo "http://localhost:{PORTA}   (Ctrl+C encerra)"
echo

(sleep 1; command -v open >/dev/null && open "http://localhost:{PORTA}") &

exec python3 -m http.server {PORTA}
"""

LEIAME = f"""# Portal FIFA Club Benefits

Levantamento das cessões do Botafogo para as Eliminatórias da Copa 2026 e para a
fase final — quais atletas, quais partidas, quanto vale.

## Abrir uma sessão nova aqui no computador

`documentos/CONTEXTO_SESSAO_LOCAL.md` — cole na primeira mensagem. Traz o estado
atual, as seis tarefas em ordem de valor, o que a plataforma da FIFA revelou e os
erros que o projeto já cometeu.

## Rodar

**macOS:** duplo clique em `iniciar.command`.

**Terminal:**

```bash
./iniciar.sh
```

Sobe em <http://localhost:{PORTA}> e o card `LEVANTAMENTO FIFA` do hub vira
ONLINE. Serve com `python3` puro — sem build, sem instalar nada, sem rede.

Se o macOS bloquear o duplo clique na primeira vez: clique com o botão direito →
Abrir → Abrir.

## O que tem aqui

| | |
|---|---|
| `index.html` | a página que o card abre |
| `dados/` | as tabelas do levantamento, em CSV e JSON |
| `codigo/` | os geradores e os testes |
| `atletas.csv`, `selecoes_escopo.csv` | as duas tabelas de entrada |
| `documentos/` | o PDF completo e o contexto do projeto |

Com o servidor no ar, `http://localhost:{PORTA}/dados/` lista as tabelas para
baixar direto — útil para o jurídico puxar um CSV sem pedir.

## Os números

| | |
|---|---|
| Eliminatórias confirmadas na escalação oficial | **49 jogos** · USD 115.640 |
| Copa do Mundo, cota da fase final (Danilo) | **34 dias** · USD 170.000 |
| **Total hoje** | **USD 285.640** |
| Ainda em aberto, nunca conferido | 170 partidas · teto de USD 401.200 |

**O card do hub está desatualizado.** Ele diz `43 elegíveis (~USD 101 mil)`.
Texto correto:

```
264 pares fechados contra o match-centre · 49 elegíveis
(USD 115.640) + cota da Copa (USD 170.000) · 170 partidas
ainda em aberto
```

O rateio da FIFA é por *jogador × partida*: o detalhe jogo a jogo tem 49 linhas e
os contadores por atleta somam 49. Partidas distintas seriam 36. Nem 43 nem 44
correspondem a critério algum — é erro de agregação.

## O extrato do TMS

O extrato jogo a jogo, recebido do departamento de registro, revelou que a
plataforma tem **três estados**, não um: partidas já atribuídas a nós (botão
*Reject*), partidas em conflito com outro clube ("FIFA resolving conflict") e
partidas disponíveis para reivindicar (*Claim*).

| | |
|---|---|
| já atribuídas ao Botafogo | **32** |
| em conflito com outro clube | **7** |
| disponíveis, mas fora do vínculo | 12 |
| ilegíveis nos prints | 7 |

**A FIFA atribuiu um amistoso ao clube.** A única partida de Cristhian Loor é
Canadá × Equador, 13/11/2025 — o Canadá era anfitrião e não disputou
Eliminatória nenhuma. Deve ser rejeitada.

**Quatro conflitos do Almada valem disputa**: março e junho de 2025 caem dentro
do vínculo dele. Três conflitos de setembro de 2025 não — dois do Luiz Henrique
e um do Almada, todos depois da saída.

## Três pendências que o documento levanta

1. **O critério.** A plataforma da FIFA fala em *cessão*, não em escalação. Pela
   cessão, o levantamento reconcilia com os números da FIFA com erro de 1
   partida; pela escalação, erro de 4. Cristhian Loor é o contraexemplo limpo
   para perguntar à FIFA — ela atribuiu 1 partida a quem não figurou em
   escalação nenhuma.
2. **170 partidas nunca conferidas**, de 14 atletas. Bastos (10 de Angola) e
   Kadir Barría (8 do Panamá) na frente.
3. **O extrato do TMS.** Todas as janelas de registro vêm de fonte de
   conferência. Foi uma janela estimada errada que quase produziu a rejeição de
   três partidas do Almada que não existiam.

## Regerar

Só é preciso se os dados mudarem. Exige `pip install pypdf` (e `pandas openpyxl
playwright` para os scripts de coleta).

Rode **da raiz desta pasta**, não de dentro de `codigo/` — os caminhos são
relativos a ela:

```bash
python3 codigo/parte2_cessao.py --pdf documentos/levantamento_fifa_botafogo.pdf
python3 codigo/gerar_relatorio_web.py --saida index.html
```

Os dois são determinísticos: mesma entrada, mesma saída.

## Versão online

<https://claude.ai/code/artifact/750e7eb0-2ead-4ff9-a231-babe27409601>

Nasce privada — precisa ser compartilhada pelo menu da própria página. Serve para
mandar link ao jurídico sem depender deste computador estar ligado.
"""


def montar() -> Path:
    if PASTA.exists():
        shutil.rmtree(PASTA)
    (PASTA / "dados").mkdir(parents=True)
    (PASTA / "codigo").mkdir()
    (PASTA / "documentos").mkdir()

    shutil.copy2("docs/index.html", PASTA / "index.html")
    for e in ENTRADAS:
        shutil.copy2(e, PASTA / Path(e).name)

    for grupo, destino in ((DADOS, "dados"), (CODIGO, "codigo"),
                           (DOCUMENTOS, "documentos")):
        for origem in grupo:
            o = Path(origem)
            if o.exists():
                shutil.copy2(o, PASTA / destino / o.name)
            else:
                print(f"  aviso: {origem} não existe, pulado")

    (PASTA / "LEIA-ME.md").write_text(LEIAME, encoding="utf-8")
    for nome in ("iniciar.sh", "iniciar.command"):
        alvo = PASTA / nome
        alvo.write_text(INICIAR_SH, encoding="utf-8")
        alvo.chmod(alvo.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return PASTA


def compactar(pasta: Path) -> Path:
    zipe = Path(f"{pasta.name}.zip")
    with zipfile.ZipFile(zipe, "w", zipfile.ZIP_DEFLATED) as z:
        for item in sorted(pasta.rglob("*")):
            if item.is_symlink():
                continue          # o atalho não sobrevive ao zip; recriado abaixo
            if item.is_file():
                info = zipfile.ZipInfo(str(item))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (item.stat().st_mode & 0xFFFF) << 16
                z.writestr(info, item.read_bytes())
    return zipe


def main() -> int:
    pasta = montar()
    arquivos = [p for p in pasta.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in arquivos)
    print(f"Pasta montada: {pasta}/  —  {len(arquivos)} arquivos, "
          f"{total/1024:.0f} KB")
    for sub in ("", "dados", "codigo", "documentos"):
        d = pasta / sub if sub else pasta
        itens = sorted(x.name for x in d.iterdir() if x.is_file())
        print(f"  {sub or '.':<12} {len(itens):>2} · {', '.join(itens[:4])}"
              f"{'…' if len(itens) > 4 else ''}")
    zipe = compactar(pasta)
    print(f"\nPacote: {zipe}  ({zipe.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
