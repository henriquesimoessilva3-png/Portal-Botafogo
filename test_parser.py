#!/usr/bin/env python3
"""
test_parser.py — testes do miolo de parsing.

O QUE ESTES TESTES PROVAM E O QUE NÃO PROVAM
--------------------------------------------
PROVAM: a camada de lógica está correta — classificação de competição, status
na súmula, janela de registro, cascata de veredito, guarda anti-homônimo e a
extração de linhas de tabelas (incluindo aninhadas, `th` e `colspan`).

NÃO PROVAM: que os seletores casam com o HTML real do Transfermarkt e do oGol.
As fixtures deste arquivo foram escritas à mão, a partir da descrição de
estrutura no CLAUDE.md, por quem NÃO teve acesso aos domínios. Elas são
representativas de *padrões de marcação* (cabeçalho de competição em `th` ou
`colspan`, linha de partida com data), não do markup real.

Enquanto ninguém rodar `--debug` numa máquina com acesso aos sites e conferir os
dumps de `debug_html/`, a extração de coluna (adversário, minutos) continua
sendo HIPÓTESE. Está tudo marcado como tal.

Rodar:  python test_parser.py     (ou: python conferencia_selecoes.py --self-test)
"""

from datetime import date

from parser_tabelas import (
    avaliar,
    classificar_competicao,
    conferir_nascimento,
    extrair_de_html,
    extrair_linhas,
    normalizar,
    parse_data,
    status_da_linha,
)

FALHAS: list[str] = []


def checar(condicao, rotulo, detalhe=""):
    if condicao:
        print(f"  ok   {rotulo}")
    else:
        print(f"  FALHA {rotulo}  {detalhe}")
        FALHAS.append(rotulo)


# --------------------------------------------------------------------------- #
# 1. Classificação de competição
# --------------------------------------------------------------------------- #

def teste_classificacao():
    print("\n[1] Classificação de competição")

    # BUG CORRIGIDO: o parser antigo aceitava o token solto "eliminatorias".
    # Bastos (Angola) e Chris Ramos (Espanha) jogam eliminatórias de OUTROS
    # torneios. Antes viravam ELEGÍVEL; era claim que a FIFA rejeita.
    for nome in ["Eliminatórias da Copa Africana das Nações",
                 "Eliminatórias do Campeonato Africano das Nações 2025",
                 "Eliminatórias da Eurocopa 2028",
                 "Eliminatórias do Campeonato Europeu",
                 "Eliminatórias Sul-Americano Sub-20"]:
        tipo, _ = classificar_competicao(nome)
        checar(tipo == "excluida", f"'{nome}' NÃO é Eliminatória de Copa", tipo)

    # BUG CORRIGIDO: "copa do mundo fifa" estava na lista de EXCLUÍDOS e era
    # testada primeiro, então "Eliminatórias da Copa do Mundo FIFA 2026" — o
    # nome mais provável da competição — era descartada como não elegível.
    for nome in ["Eliminatórias da Copa do Mundo FIFA 2026",
                 "Eliminatórias da Copa do Mundo",
                 "ELIMINATORIAS DA COPA DO MUNDO",       # sem acento, caixa alta
                 "Eliminatórias Copa do Mundo - América do Sul",
                 "Mundial 2026 (Q)",                      # formato oGol
                 "World Cup Qualifying - CONMEBOL",
                 "Clasificación Copa Mundial 2026"]:
        tipo, _ = classificar_competicao(nome)
        checar(tipo == "eliminatoria", f"'{nome}' É Eliminatória de Copa", tipo)

    # A fase final é outro rateio — não entra nesta tela.
    tipo, _ = classificar_competicao("Copa do Mundo FIFA 2026")
    checar(tipo == "excluida", "'Copa do Mundo FIFA 2026' (fase final) exclui", tipo)

    for nome in ["Amistosos", "Amistoso Internacional", "Copa América 2024",
                 "Liga das Nações da UEFA", "Finalíssima"]:
        tipo, _ = classificar_competicao(nome)
        checar(tipo == "excluida", f"'{nome}' exclui", tipo)

    # "Eliminatórias" sem dizer de quê é ambíguo. O seguro é CONFERIR, não
    # assumir Copa do Mundo.
    tipo, _ = classificar_competicao("Eliminatórias")
    checar(tipo == "indefinida", "'Eliminatórias' sozinho vira CONFERIR", tipo)

    tipo, _ = classificar_competicao("?")
    checar(tipo == "indefinida", "competição não capturada vira CONFERIR", tipo)


# --------------------------------------------------------------------------- #
# 2. Status na súmula
# --------------------------------------------------------------------------- #

def teste_status():
    print("\n[2] Status na súmula")

    checar(status_da_linha("Suplente não utilizado") == "Suplente não utilizado",
           "'suplente não utilizado' reconhecido")
    checar(status_da_linha("suplente nao utilizado") == "Suplente não utilizado",
           "sem acento também")
    checar(status_da_linha("unused substitute") == "Suplente não utilizado",
           "inglês também")
    checar(status_da_linha("Titular | 61'") == "Titular", "titular reconhecido")
    checar(status_da_linha("Não convocado") == "Fora da relação",
           "'não convocado' é fora da relação")
    checar(status_da_linha("Lesionado") == "Fora da relação", "lesionado é fora")

    # BUG CORRIGIDO: o default era "Titular". Toda linha que o parser não
    # entendia virava titular e, portanto, ELEGÍVEL — silêncio virava dinheiro
    # reivindicado sem base. Agora vira Indeterminado → CONFERIR.
    checar(status_da_linha("07/09/2023 | Bolívia | 5:1") == "Indeterminado",
           "linha sem pista de status NÃO vira Titular")


# --------------------------------------------------------------------------- #
# 3. Cascata de veredito
# --------------------------------------------------------------------------- #

def teste_veredito():
    print("\n[3] Cascata de veredito")

    checar(avaliar("eliminatoria", True, "Titular", True, False) == "ELEGÍVEL",
           "titular, dentro da janela, eliminatória → ELEGÍVEL")

    # Regra do programa: minutos e titularidade são irrelevantes.
    checar(avaliar("eliminatoria", True, "Suplente não utilizado", True, False)
           == "ELEGÍVEL", "suplente não utilizado CONTA")

    checar(avaliar("eliminatoria", True, "Fora da relação", True, False)
           .startswith("NÃO ELEGÍVEL"), "fora da relação NÃO conta")
    checar(avaliar("eliminatoria", False, "Titular", True, False)
           .startswith("NÃO ELEGÍVEL"), "fora da janela de registro não conta")
    checar(avaliar("excluida", True, "Titular", True, False)
           .startswith("NÃO ELEGÍVEL"), "competição excluída não conta")
    checar(avaliar("indefinida", True, "Titular", True, False)
           .startswith("CONFERIR"), "competição indefinida vira CONFERIR")
    checar(avaliar("eliminatoria", True, "Indeterminado", True, False)
           .startswith("CONFERIR"), "status indeterminado vira CONFERIR")

    # Exigência explícita do briefing: sinalizar resultado que depende de janela
    # estimada (as de atletas.csv vieram de imprensa, não do TMS).
    v = avaliar("eliminatoria", True, "Titular", True, True)
    checar(v.startswith("ELEGÍVEL") and "ESTIMADA" in v,
           "janela estimada é sinalizada no veredito", v)

    # Jacob Montes: vínculo não confirmado, sem janela nenhuma. O parser antigo
    # tratava janela ausente como "sempre dentro" → ELEGÍVEL.
    checar(avaliar("eliminatoria", True, "Titular", False, False)
           .startswith("CONFERIR"), "atleta sem janela de registro vira CONFERIR")

    # Guarda anti-homônimo tem precedência sobre tudo.
    checar(avaliar("eliminatoria", True, "Titular", True, False,
                   identidade_ok=False).startswith("CONFERIR"),
           "identidade não confirmada bloqueia ELEGÍVEL")


# --------------------------------------------------------------------------- #
# 4. Datas
# --------------------------------------------------------------------------- #

def teste_datas():
    print("\n[4] Parsing de data")

    checar(parse_data("07/09/2023") == date(2023, 9, 7), "dd/mm/aaaa")
    checar(parse_data("09.09.2025") == date(2025, 9, 9), "dd.mm.aaaa")
    checar(parse_data("2025-09-04") == date(2025, 9, 4), "ISO")
    checar(parse_data("sáb, 07/09/2023") == date(2023, 9, 7),
           "prefixo de dia da semana do Transfermarkt")

    # BUG CORRIGIDO: o original tentava %d/%m/%y ANTES de %d/%m/%Y. Sem âncora,
    # textos como "Rodada 12/18" ou "12/10" podiam virar data.
    checar(parse_data("Rodada 12/18") is None, "'Rodada 12/18' não é data")
    checar(parse_data("61'") is None, "minutagem não é data")
    checar(parse_data("5:1") is None, "placar não é data")
    checar(parse_data("") is None, "vazio não é data")


# --------------------------------------------------------------------------- #
# 5. Extração de linhas de tabela
# --------------------------------------------------------------------------- #

# FIXTURE SINTÉTICA — escrita à mão, NÃO é HTML capturado do Transfermarkt.
# Reproduz o padrão descrito no CLAUDE.md: cabeçalho de competição ocupando a
# linha inteira, seguido das partidas daquele bloco.
FIXTURE_CABECALHO_TH = """
<html><body>
<table>
  <tr><th colspan="6">Eliminatórias da Copa do Mundo FIFA 2026</th></tr>
  <tr><td>Rodada 17</td><td>04/09/2025</td><td>Chile</td><td>3:0</td>
      <td>Suplente não utilizado</td><td></td></tr>
  <tr><td>Rodada 18</td><td>09/09/2025</td><td>Bolívia</td><td>0:1</td>
      <td>Titular</td><td>61'</td></tr>
  <tr><th colspan="6">Amistosos</th></tr>
  <tr><td>-</td><td>10/10/2025</td><td>Coreia do Sul</td><td>5:0</td>
      <td>Titular</td><td>90'</td></tr>
</table>
</body></html>
"""

# Mesma informação, marcada com <td colspan> em vez de <th>.
FIXTURE_CABECALHO_COLSPAN = """
<html><body>
<table>
  <tr><td colspan="5">Eliminatórias da Copa do Mundo FIFA 2026</td></tr>
  <tr><td>04/09/2025</td><td>Chile</td><td>3:0</td>
      <td>Suplente não utilizado</td><td></td></tr>
</table>
</body></html>
"""

# Tabela dentro de célula — padrão do Transfermarkt para escudo + nome do clube.
FIXTURE_ANINHADA = """
<html><body>
<table>
  <tr><th colspan="4">Eliminatórias da Copa do Mundo FIFA 2026</th></tr>
  <tr>
    <td>09/09/2025</td>
    <td><table><tr><td><img src="x.png"></td><td>Bolívia</td></tr></table></td>
    <td>0:1</td>
    <td>Titular</td>
  </tr>
</table>
</body></html>
"""


def teste_extracao():
    print("\n[5] Extração de linhas de tabela")

    linhas = extrair_linhas(FIXTURE_CABECALHO_TH)
    checar(len(linhas) == 5, "5 linhas lidas da fixture", len(linhas))

    # BUG CORRIGIDO: o parser antigo contava só células `td`. Numa linha só de
    # `th` a contagem é ZERO e ela caía no `continue` antes de virar contexto.
    # A competição ficava "?" na página inteira e NADA era eliminatória.
    regs = extrair_de_html(FIXTURE_CABECALHO_TH, "Vitinho", "1999-07-23",
                           "Transfermarkt", date(2024, 8, 1), None,
                           janela_estimada=False)
    comps = {r.competicao for r in regs}
    checar(all(c != "?" for c in comps), "competição capturada de <th>", comps)
    checar(len(regs) == 3, "3 partidas dentro do ciclo", len(regs))

    por_data = {r.data: r for r in regs}
    checar(por_data["04/09/2025"].veredito == "ELEGÍVEL",
           "Chile 04/09/25 (supl. não utilizado) → ELEGÍVEL",
           por_data["04/09/2025"].veredito)
    checar(por_data["09/09/2025"].veredito == "ELEGÍVEL",
           "Bolívia 09/09/25 (titular) → ELEGÍVEL",
           por_data["09/09/2025"].veredito)
    checar(por_data["10/10/2025"].veredito.startswith("NÃO ELEGÍVEL"),
           "amistoso 10/10/25 → NÃO ELEGÍVEL",
           por_data["10/10/2025"].veredito)

    # Esse é o número que o CLAUDE.md diz estar certo na lista da FIFA: 2.
    eleg = [r for r in regs if r.veredito.startswith("ELEGÍVEL")]
    checar(len(eleg) == 2, "Vitinho fecha em 2 partidas elegíveis", len(eleg))

    regs2 = extrair_de_html(FIXTURE_CABECALHO_COLSPAN, "Vitinho", "1999-07-23",
                            "oGol", date(2024, 8, 1), None)
    checar(len(regs2) == 1 and regs2[0].veredito == "ELEGÍVEL",
           "cabeçalho por colspan também é capturado",
           [r.veredito for r in regs2])

    regs3 = extrair_de_html(FIXTURE_ANINHADA, "Vitinho", "1999-07-23",
                            "Transfermarkt", date(2024, 8, 1), None)
    checar(len(regs3) == 1, "tabela aninhada não duplica a partida", len(regs3))
    checar("Bolívia" in regs3[0].bruto, "texto da tabela interna é preservado",
           regs3[0].bruto)


# --------------------------------------------------------------------------- #
# 6. Janela de registro
# --------------------------------------------------------------------------- #

def teste_janela():
    print("\n[6] Janela de registro")

    # Lucas Perri: saiu no fim de 2023. As partidas de 2024 não são nossas.
    # (Erro nº 3 do CLAUDE.md foi exatamente confundir esses dois anos.)
    html = """
    <table>
      <tr><th colspan="4">Eliminatórias da Copa do Mundo FIFA 2026</th></tr>
      <tr><td>08/09/2023</td><td>Bolívia</td><td>5:1</td><td>Titular</td></tr>
      <tr><td>12/09/2023</td><td>Peru</td><td>1:0</td><td>Suplente não utilizado</td></tr>
      <tr><td>10/10/2024</td><td>Chile</td><td>2:1</td><td>Titular</td></tr>
    </table>
    """
    regs = extrair_de_html(html, "Lucas Perri", "1997-12-13", "Transfermarkt",
                           date(2023, 1, 1), date(2023, 12, 31))
    por_data = {r.data: r for r in regs}
    checar(por_data["08/09/2023"].veredito == "ELEGÍVEL", "set/2023 é nosso")
    checar(por_data["12/09/2023"].veredito == "ELEGÍVEL", "12/09/2023 é nosso")
    checar(por_data["10/10/2024"].veredito.startswith("NÃO ELEGÍVEL"),
           "out/2024 já não é nosso", por_data["10/10/2024"].veredito)

    # Mesmo conteúdo, mas janela marcada como ESTIMADA → tem que sinalizar.
    regs_est = extrair_de_html(html, "Lucas Perri", "1997-12-13", "Transfermarkt",
                               date(2023, 1, 1), date(2023, 12, 31),
                               janela_estimada=True)
    checar(all("ESTIMADA" in r.veredito for r in regs_est
               if r.veredito.startswith("ELEGÍVEL")),
           "veredito sinaliza dependência de janela estimada")


# --------------------------------------------------------------------------- #
# 7. Guarda anti-homônimo
# --------------------------------------------------------------------------- #

def teste_homonimo():
    print("\n[7] Guarda anti-homônimo")

    # Os dois Vitinho, o caso real do CLAUDE.md.
    lateral = date(1999, 7, 23)
    atacante = date(2007, 6, 14)

    checar(conferir_nascimento("Data de nascimento: 23/07/1999", lateral)
           == "confere", "acha a data no corpo da página")
    checar(conferir_nascimento("Data de nascimento: 14/06/2007", lateral)
           == "nao_confere", "detecta o Vitinho errado")
    checar(conferir_nascimento("Nascimento: 23 jul 1999", lateral) == "confere",
           "formato por extenso")

    # BUG CORRIGIDO: o original devolvia bool e falhava ABERTO — sem data na
    # página (ou com exceção), devolvia True e aceitava os dados. Para a
    # armadilha do homônimo isso é o avesso do que se precisa.
    checar(conferir_nascimento("página sem nenhuma data", lateral)
           == "nao_encontrada", "sem data na página → estado próprio, não True")
    checar(conferir_nascimento("", lateral) == "nao_encontrada",
           "corpo vazio → não_encontrada")
    checar(conferir_nascimento("qualquer coisa", None) == "nao_encontrada",
           "sem data esperada → não_encontrada")
    checar(conferir_nascimento("Data de nascimento: 14/06/2007", atacante)
           == "confere", "o outro Vitinho confere com a própria data")


def teste_normalizacao():
    print("\n[8] Normalização")
    checar(normalizar("ELIMINATÓRIAS  da\nCopa") == "eliminatorias da copa",
           "acento, caixa e espaço", normalizar("ELIMINATÓRIAS  da\nCopa"))


def main():
    print("=" * 70)
    print("TESTES DO PARSER — camada de lógica")
    print("=" * 70)
    teste_classificacao()
    teste_status()
    teste_veredito()
    teste_datas()
    teste_extracao()
    teste_janela()
    teste_homonimo()
    teste_normalizacao()

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} FALHA(S):")
        for f in FALHAS:
            print("  -", f)
        return 1
    print("Todos os testes de LÓGICA passaram.")
    print()
    print("LEMBRETE: isto NÃO valida os seletores contra o HTML real do")
    print("Transfermarkt/oGol. As fixtures são sintéticas. A extração de")
    print("coluna (adversário, minutos) segue sendo hipótese até alguém rodar")
    print("--debug com acesso aos domínios e conferir os dumps.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
