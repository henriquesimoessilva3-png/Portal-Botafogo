#!/usr/bin/env python3
"""
test_universo.py — testes do validador de partidas_universo.

O torneio usado aqui é GERADO, não coletado: um turno-e-returno de 10 seleções
montado pelo método do círculo. Os confrontos e as datas NÃO são os das
Eliminatórias reais e não devem ser usados como dado. Serve só para exercitar
as invariantes — inclusive quebrando-as de propósito e conferindo se o
validador acusa.

Rodar:  python test_universo.py
"""

from datetime import date

from partidas_universo import (
    JANELAS_CONMEBOL,
    Partida,
    espelhar,
    id_canonico,
    validar,
)

FALHAS: list[str] = []


def checar(condicao, rotulo, detalhe=""):
    if condicao:
        print(f"  ok   {rotulo}")
    else:
        print(f"  FALHA {rotulo}  {detalhe}")
        FALHAS.append(rotulo)


TIMES = ["Argentina", "Bolivia", "Brasil", "Chile", "Colombia",
         "Equador", "Paraguai", "Peru", "Uruguai", "Venezuela"]


def _data_da_rodada(r: int) -> date:
    """Rodadas 1-2 caem na 1ª janela, 3-4 na 2ª, e assim por diante."""
    janela = JANELAS_CONMEBOL[(r - 1) // 2]
    return janela[1] if r % 2 == 1 else janela[2]


def torneio_sintetico() -> list[Partida]:
    """Turno e returno de 10 times pelo método do círculo. Estrutura real,
    confrontos fictícios."""
    fixo, rodam = TIMES[0], TIMES[1:]
    linhas: list[Partida] = []

    for rodada in range(1, 19):
        r = rodada if rodada <= 9 else rodada - 9
        volta = rodada > 9
        giro = rodam[r - 1:] + rodam[:r - 1]
        pares = [(fixo, giro[0])]
        for i in range(1, 5):
            pares.append((giro[i], giro[9 - i]))

        d = _data_da_rodada(rodada)
        for casa, fora in pares:
            if volta:
                casa, fora = fora, casa
            pid = id_canonico(casa, fora, d.isoformat())
            for selecao, adversario, mando in ((casa, fora, "casa"),
                                               (fora, casa, "fora")):
                linhas.append(Partida(
                    partida_id=pid, selecao=selecao, confederacao="CONMEBOL",
                    competicao="Eliminatórias da Copa do Mundo FIFA 2026",
                    rodada=str(rodada), data=d.isoformat(), mando=mando,
                    adversario=adversario, resultado="",
                    fonte="SINTÉTICO - teste",
                ))
    return linhas


def teste_torneio_valido():
    print("\n[1] Torneio estruturalmente completo")
    p = torneio_sintetico()
    checar(len(p) == 180, "180 linhas (90 partidas × 2 lados)", len(p))
    checar(len({x.partida_id for x in p}) == 90, "90 partidas distintas",
           len({x.partida_id for x in p}))
    erros, avisos = validar(p)
    checar(not erros, "validador não acusa erro", erros[:3])


def teste_deteccao_de_erros():
    print("\n[2] O validador acusa coleta quebrada")

    base = torneio_sintetico()

    # Faltou uma partida na coleta.
    p = [x for x in base if x.partida_id != base[0].partida_id]
    erros, _ = validar(p)
    checar(any("jogos, esperado 18" in e for e in erros),
           "partida faltando é detectada", erros[:2])

    # Amistoso vazou na coleta (data fora de toda janela de Data FIFA).
    p = list(base)
    p.append(Partida(
        partida_id=id_canonico("Brasil", "Japao", "2025-10-14"),
        selecao="Brasil", confederacao="CONMEBOL",
        competicao="Eliminatórias da Copa do Mundo FIFA 2026",
        rodada="", data="2025-10-14", mando="casa", adversario="Japao",
        resultado="", fonte="teste"))
    erros, _ = validar(p)
    checar(any("fora de todas as janelas" in e for e in erros),
           "amistoso fora de janela é detectado", erros[:2])

    # Os dois lados dizendo que jogaram em casa.
    p = [Partida(**{**x.__dict__, "mando": "casa"}) if x.partida_id == base[0].partida_id
         else x for x in base]
    erros, _ = validar(p)
    checar(any("os dois lados declaram mando" in e for e in erros),
           "mando incoerente é detectado", erros[:2])

    # partida_id fora do padrão canônico — o risco é contar a mesma partida 2x.
    p = [Partida(**{**x.__dict__, "partida_id": "qualquer-coisa"})
         if x is base[0] else x for x in base]
    erros, _ = validar(p)
    checar(any("fora do padrão canônico" in e for e in erros),
           "partida_id não canônico é detectado", erros[:2])

    # Seleção que não é da CONMEBOL entrando no bloco da CONMEBOL.
    p = list(base) + [Partida(
        partida_id=id_canonico("Angola", "Brasil", "2025-09-04"),
        selecao="Angola", confederacao="CONMEBOL", competicao="x",
        rodada="17", data="2025-09-04", mando="casa", adversario="Brasil",
        resultado="", fonte="teste")]
    erros, _ = validar(p)
    checar(any("fora do torneio" in e for e in erros),
           "seleção de outra confederação é detectada", erros[:2])

    # Coleta parcial não deve virar erro — só aviso.
    p = [x for x in base if x.selecao in ("Brasil", "Argentina")]
    erros, avisos = validar(p)
    checar(any("coleta parcial" in a for a in avisos),
           "coleta parcial vira aviso, não erro")


def teste_espelhar():
    print("\n[3] Espelhamento de partida")
    uma = [Partida(
        partida_id=id_canonico("Brasil", "Bolivia", "2023-09-08"),
        selecao="Brasil", confederacao="CONMEBOL",
        competicao="Eliminatórias da Copa do Mundo FIFA 2026",
        rodada="1", data="2023-09-08", mando="casa", adversario="Bolivia",
        resultado="5:1", fonte="teste")]
    dois = espelhar(uma)
    checar(len(dois) == 2, "uma linha vira duas", len(dois))
    outro = [p for p in dois if p.selecao == "Bolivia"][0]
    checar(outro.mando == "fora", "mando é invertido", outro.mando)
    checar(outro.resultado == "1:5", "placar é invertido", outro.resultado)
    checar(outro.partida_id == uma[0].partida_id, "mesmo partida_id nos dois lados")
    checar(not validar(dois)[0] or all("coleta parcial" not in e
                                       for e in validar(dois)[0]),
           "espelhada não gera erro de mando")


def main():
    print("=" * 70)
    print("TESTES DO VALIDADOR DE partidas_universo")
    print("=" * 70)
    teste_torneio_valido()
    teste_deteccao_de_erros()
    teste_espelhar()
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} FALHA(S):")
        for f in FALHAS:
            print("  -", f)
        return 1
    print("Validador OK.")
    print()
    print("LEMBRETE: o torneio destes testes é GERADO. Os confrontos e datas")
    print("não são os das Eliminatórias reais. dados/partidas_universo.csv")
    print("segue vazio — falta a coleta na fonte oficial.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
