#!/usr/bin/env python3
"""
parser_tabelas.py — o miolo de parsing do levantamento, SEM Playwright.

Por que este arquivo existe
---------------------------
A versão original de `extrair_tabelas()` recebia um objeto `Page` do Playwright.
Isso a tornava impossível de testar sem abrir um navegador e alcançar o site: o
único jeito de exercitar uma mudança era rodar o scraper inteiro contra a rede.
O `--debug` salvava o HTML, mas não havia caminho de volta para reprocessá-lo.

Aqui o parsing é função pura de `str` (HTML) para `list[Registro]`. Com isso:

  * dá para testar com fixture (`python conferencia_selecoes.py --self-test`);
  * dá para reprocessar os dumps de `debug_html/` sem rede
    (`python conferencia_selecoes.py --from-html debug_html/`);
  * o ciclo de conserto vira segundos em vez de minutos, e não consome
    requisição contra Transfermarkt/oGol.

LIMITE DESTE ARQUIVO — leia antes de confiar no resultado
----------------------------------------------------------
As heurísticas de *seleção de coluna* (qual célula é o adversário, quais são os
minutos) NÃO foram validadas contra o HTML real do Transfermarkt nem do oGol.
Elas continuam sendo hipótese até alguém rodar `--debug` numa máquina com acesso
aos domínios e conferir os dumps. O que foi corrigido e testado aqui é a camada
de LÓGICA — classificação de competição, status na súmula, janela de registro e
veredito — que não depende do formato da página.

Por isso todo Registro carrega `bruto`: a linha crua, para conferência humana.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser

# --------------------------------------------------------------------------- #
# Constantes do ciclo
# --------------------------------------------------------------------------- #

CICLO_INICIO = date(2023, 9, 1)
CICLO_FIM = date(2026, 3, 31)      # inclui repescagens de março/2026
VALOR_POR_PARTIDA = 2360           # USD, estimativa FIFA


# --------------------------------------------------------------------------- #
# Normalização
# --------------------------------------------------------------------------- #

def normalizar(txt: str) -> str:
    """Minúsculas, sem acento, espaços colapsados.

    O parser original comparava strings acentuadas cruas, então
    'Eliminatórias' casava e 'ELIMINATORIAS' não. Aqui tudo passa por isto
    antes de qualquer comparação.
    """
    t = unicodedata.normalize("NFKD", txt or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def parse_data(txt: str) -> date | None:
    """Aceita os formatos que Transfermarkt e oGol usam nas suas várias locales.

    Exige que a string SEJA a data (após limpar dia-da-semana e lixo em volta),
    não que a contenha — senão 'Rodada 12/18' vira 12 de dezembro.
    """
    t = (txt or "").strip()
    if not t:
        return None
    # tira prefixo de dia da semana usado pelo Transfermarkt ("sáb, 07/09/2023")
    t = re.sub(r"^[A-Za-zÀ-ÿ]{2,3}[.,]?\s+", "", t).strip()
    t = t.replace(" ", " ").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y",
                "%Y-%m-%d", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Classificação de competição
# --------------------------------------------------------------------------- #
# Uma partida só gera direito se for Eliminatória DA COPA DO MUNDO. O parser
# original aceitava o token solto "eliminatorias", o que faz Eliminatórias da
# Copa Africana das Nações (Bastos/Angola) e Eliminatórias da Eurocopa
# (Hämäläinen/Finlândia, Chris Ramos/Espanha) entrarem como ELEGÍVEL. Esse é o
# erro caro: gera claim que a FIFA rejeita. Agora exige-se a conjunção
# "qualificatória" + "copa do mundo".

TOKENS_QUALIFICATORIA = [
    "eliminatoria", "eliminatorias", "qualificacao", "qualificatoria",
    "qualifying", "qualifiers", "qualif.", "clasificacion", "classificatorias",
    "preliminar", "(q)",
]

TOKENS_COPA_DO_MUNDO = [
    "copa do mundo", "copa mundial", "mundial", "world cup", "wm ",
    "weltmeisterschaft", "wc qualif", "copa do mundo fifa",
]

# Outros torneios que TAMBÉM têm eliminatórias. Se aparecer qualquer um destes,
# não é Eliminatória de Copa do Mundo, ponto — mesmo que a string diga
# "eliminatórias".
TOKENS_OUTRO_TORNEIO = [
    "eurocopa", "campeonato europeu", "euro 2024", "euro 2028",
    "copa africana", "campeonato africano", "afcon", "can 2025", "can 2027",
    "copa asiatica", "copa ouro", "gold cup", "concacaf nations",
    "sul-americano", "pre-olimpico", "olimpic", "olympic",
    "sub-17", "sub-20", "sub-21", "sub-23", "u17", "u20", "u21", "u23",
]

# Blocos que nunca geram direito, mesmo caindo dentro de Data FIFA.
TOKENS_EXCLUIDOS = [
    "amistoso", "amistosos", "friendly", "friendlies",
    "copa america", "liga das nacoes", "nations league",
    "finalissima", "torneio", "taca",
]


def classificar_competicao(nome: str) -> tuple[str, str]:
    """Devolve (tipo, motivo). tipo ∈ {'eliminatoria','excluida','indefinida'}.

    Ordem importa:
      1. Outro torneio (Euro/CAN/etc.) barra antes de tudo — inclusive quando a
         string contém "eliminatórias".
      2. Eliminatória de Copa do Mundo exige os DOIS tokens. "Eliminatórias da
         Copa do Mundo FIFA 2026" é eliminatória; "Copa do Mundo FIFA 2026"
         sozinha (a fase final) não é.
      3. Só depois aplicam-se as exclusões de amistoso/Copa América/etc.
      4. Qualquer outra coisa vira 'indefinida' → CONFERIR. Nunca ELEGÍVEL.
    """
    c = normalizar(nome)
    if not c or c == "?":
        return "indefinida", "competição não capturada na página"

    for tok in TOKENS_OUTRO_TORNEIO:
        if tok in c:
            return "excluida", f"eliminatória de outro torneio ({tok})"

    tem_qualif = any(tok in c for tok in TOKENS_QUALIFICATORIA)
    tem_copa = any(tok in c for tok in TOKENS_COPA_DO_MUNDO)
    if tem_qualif and tem_copa:
        return "eliminatoria", "eliminatória de Copa do Mundo"

    for tok in TOKENS_EXCLUIDOS:
        if tok in c:
            return "excluida", f"competição não elegível ({tok})"

    if tem_copa and not tem_qualif:
        return "excluida", "fase final de Copa do Mundo (outro rateio)"
    if tem_qualif and not tem_copa:
        return "indefinida", "diz 'eliminatórias' mas não diz de qual torneio"
    return "indefinida", "competição não reconhecida"


# --------------------------------------------------------------------------- #
# Status na súmula
# --------------------------------------------------------------------------- #
# Regra do programa: "suplente não utilizado" CONTA; "fora da relação" não.
# O parser original devolvia "Titular" para toda linha não reconhecida, o que
# transformava silêncio em ELEGÍVEL. Agora o desconhecido é "Indeterminado" e
# cai em CONFERIR.

_PADROES_STATUS = [
    ("Suplente não utilizado", ["nao utilizado", "suplente nao usado", "unused",
                                "no banco", "banco sem entrar", "nao entrou",
                                "sem entrar"]),
    ("Fora da relação", ["nao convocado", "nao relacionado", "fora da relacao",
                         "nicht im kader", "not in squad", "ausencia",
                         "lesionado", "suspenso", "desfalque"]),
    ("Suplente utilizado", ["suplente", "entrou", "substituto", "banco"]),
    ("Titular", ["titular", "11 inicial", "onze inicial", "starting"]),
]


def status_da_linha(texto: str) -> str:
    t = normalizar(texto)
    for rotulo, padroes in _PADROES_STATUS:
        if any(p in t for p in padroes):
            return rotulo
    return "Indeterminado"


# --------------------------------------------------------------------------- #
# Registro e veredito
# --------------------------------------------------------------------------- #

@dataclass
class Registro:
    atleta: str
    nascimento: str
    fonte: str
    competicao: str
    tipo: str
    motivo_tipo: str
    data: str
    adversario: str
    status: str
    minutos: str
    dentro_do_registro: bool
    janela_estimada: bool
    veredito: str
    bruto: str = field(default="")


def avaliar(tipo: str, dentro: bool, status: str, tem_janela: bool,
            janela_estimada: bool, identidade_ok: bool = True) -> str:
    """Cascata de elegibilidade. Só devolve ELEGÍVEL quando os três filtros
    passam E a identidade do atleta foi confirmada."""
    if not identidade_ok:
        return "CONFERIR — identidade do atleta não confirmada"
    if tipo == "excluida":
        return "NÃO ELEGÍVEL — competição não é Eliminatória de Copa do Mundo"
    if tipo == "indefinida":
        return "CONFERIR — competição não reconhecida"
    if not tem_janela:
        return "CONFERIR — atleta sem janela de registro informada"
    if not dentro:
        return "NÃO ELEGÍVEL — fora da janela de registro"
    if status == "Fora da relação":
        return "NÃO ELEGÍVEL — fora da relação da partida"
    if status == "Indeterminado":
        return "CONFERIR — status na súmula não identificado"
    # Titular, Suplente utilizado e Suplente não utilizado contam igual.
    if janela_estimada:
        return "ELEGÍVEL (janela ESTIMADA — confirmar no TMS)"
    return "ELEGÍVEL"


# --------------------------------------------------------------------------- #
# Extração de tabelas a partir de HTML cru
# --------------------------------------------------------------------------- #

@dataclass
class LinhaBruta:
    tabela: int
    profundidade: int
    indice: int
    celulas: list[str]
    tags: list[str]
    colspans: list[int]
    # Todos os href da linha. É daqui que sai o ID do atleta no Transfermarkt
    # (`/spieler/576028`) — e o CLAUDE.md é explícito: a chave é ID + data de
    # nascimento, nunca o nome.
    links: list[str] = field(default_factory=list)

    @property
    def texto(self) -> str:
        return " | ".join(self.celulas)


class _ColetorDeTabelas(HTMLParser):
    """Extrai linhas de todas as tabelas, inclusive aninhadas.

    O Transfermarkt aninha tabelas dentro de células (o bloco com escudo + nome
    do clube é uma tabela dentro de um `<td>`). Um parser que ignora isso
    embaralha as colunas. Aqui a pilha mantém a profundidade e o texto de uma
    célula inclui o conteúdo das tabelas internas.
    """

    _IGNORAR = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.linhas: list[LinhaBruta] = []
        # Uma "moldura" por tabela aberta. Sem a pilha, o `<td>` de uma tabela
        # aninhada fechava a célula da tabela de fora e o texto interno — o nome
        # do adversário, no Transfermarkt — se perdia.
        self._pilha: list[dict] = []
        self._n_tabelas = 0
        self._ignorando = 0

    def _nova_moldura(self, tid: int) -> dict:
        return {"tid": tid, "indice": 0, "celulas": None, "tags": None,
                "colspans": None, "buffer": None, "tag_celula": None,
                "links": None}

    # -- estrutura -------------------------------------------------------- #
    def handle_starttag(self, tag, attrs):
        if tag in self._IGNORAR:
            self._ignorando += 1
            return
        if tag == "table":
            self._n_tabelas += 1
            self._pilha.append(self._nova_moldura(self._n_tabelas))
            return
        if not self._pilha:
            return
        m = self._pilha[-1]
        if tag == "tr":
            self._fechar_linha(m)
            m["celulas"], m["tags"], m["colspans"] = [], [], []
            m["links"] = []
        elif tag in ("td", "th"):
            if m["celulas"] is None:          # `<td>` sem `<tr>` explícito
                m["celulas"], m["tags"], m["colspans"] = [], [], []
            self._fechar_celula(m)
            m["buffer"] = []
            m["tag_celula"] = tag
            try:
                cs = int(dict(attrs).get("colspan") or 1)
            except (TypeError, ValueError):
                cs = 1
            m["colspans"].append(max(1, cs))
        elif tag == "br":
            for f in self._pilha:
                if f["buffer"] is not None:
                    f["buffer"].append(" ")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                # O link vale para a linha de fora também: no Transfermarkt o
                # perfil do atleta está numa tabela aninhada dentro da célula.
                for f in self._pilha:
                    if f["links"] is not None and href not in f["links"]:
                        f["links"].append(href)
        elif tag == "img":
            # A nacionalidade no Transfermarkt é a BANDEIRA, não texto: sem ler
            # o title/alt da imagem, a coluna sai vazia.
            d = dict(attrs)
            legenda = (d.get("title") or d.get("alt") or "").strip()
            if legenda:
                for f in self._pilha:
                    if f["buffer"] is not None:
                        f["buffer"].append(f" [{legenda}] ")

    def handle_endtag(self, tag):
        if tag in self._IGNORAR:
            self._ignorando = max(0, self._ignorando - 1)
            return
        if not self._pilha:
            return
        if tag in ("td", "th"):
            self._fechar_celula(self._pilha[-1])
        elif tag == "tr":
            self._fechar_linha(self._pilha[-1])
        elif tag == "table":
            self._fechar_linha(self._pilha[-1])
            self._pilha.pop()

    def handle_data(self, dados):
        if self._ignorando:
            return
        # O texto alimenta TODAS as células abertas na pilha: a da tabela
        # interna e também a da externa que a contém.
        for f in self._pilha:
            if f["buffer"] is not None:
                f["buffer"].append(dados)

    # -- montagem --------------------------------------------------------- #
    def _fechar_celula(self, m: dict):
        if m["buffer"] is None:
            return
        texto = re.sub(r"\s+", " ", "".join(m["buffer"])).strip()
        m["celulas"].append(texto)
        m["tags"].append(m["tag_celula"] or "td")
        m["buffer"] = None
        m["tag_celula"] = None

    def _fechar_linha(self, m: dict):
        self._fechar_celula(m)
        if m["celulas"] is None:
            return
        if m["celulas"]:
            m["indice"] += 1
            while len(m["colspans"]) < len(m["celulas"]):
                m["colspans"].append(1)
            self.linhas.append(LinhaBruta(
                tabela=m["tid"],
                profundidade=self._pilha.index(m) if m in self._pilha else 0,
                indice=m["indice"],
                celulas=list(m["celulas"]),
                tags=list(m["tags"]),
                colspans=list(m["colspans"][:len(m["celulas"])]),
                links=list(m["links"] or []),
            ))
        m["celulas"] = m["tags"] = m["colspans"] = m["links"] = None

    def close(self):
        while self._pilha:
            self._fechar_linha(self._pilha[-1])
            self._pilha.pop()
        super().close()


def extrair_linhas(html: str) -> list[LinhaBruta]:
    p = _ColetorDeTabelas()
    p.feed(html or "")
    p.close()
    return p.linhas


# --------------------------------------------------------------------------- #
# Interpretação das linhas
# --------------------------------------------------------------------------- #

_RE_MINUTOS = re.compile(r"^'?(\d{1,3})\s*'$")
_RE_PLACAR = re.compile(r"^\d{1,2}\s*[:x\-]\s*\d{1,2}(\s*\(.*\))?$")
_RE_SO_SIMBOLOS = re.compile(r"^[\d\s:'.,\-x/()+%]*$")


def _eh_cabecalho_de_competicao(l: LinhaBruta) -> bool:
    """Linha que anuncia a competição do bloco seguinte.

    O código original só reconhecia isso quando a linha tinha <= 2 células `td`.
    Mas nas duas fontes esse cabeçalho costuma ser `<th>` ou um `<td colspan=N>`
    — e a contagem de `td` numa linha só de `th` é ZERO, então a linha era
    descartada antes de virar contexto. Resultado: `competicao` ficava "?" para
    a página inteira e nada era classificado como Eliminatória.
    """
    if not l.celulas:
        return False
    nao_vazias = [c for c in l.celulas if c]
    if not nao_vazias:
        return False
    if any(parse_data(c) for c in l.celulas):
        return False
    # linha inteiramente de <th>
    if all(t == "th" for t in l.tags):
        return True
    # célula única esticada por colspan
    if len(nao_vazias) == 1 and max(l.colspans or [1]) >= 3:
        return True
    # poucas células e nenhuma data (regra original, mantida)
    if len(nao_vazias) <= 2:
        return True
    return False


def _achar_minutos(celulas: list[str]) -> str:
    for c in reversed(celulas):
        m = _RE_MINUTOS.match(c.strip())
        if m:
            return m.group(1)
    return ""


def _achar_adversario(celulas: list[str], idx_data: int) -> str:
    """Heurística NÃO validada contra o HTML real — ver aviso no topo."""
    def plausivel(c: str) -> bool:
        c = c.strip()
        if len(c) < 3 or parse_data(c):
            return False
        if _RE_PLACAR.match(c) or _RE_MINUTOS.match(c) or _RE_SO_SIMBOLOS.match(c):
            return False
        n = normalizar(c)
        if any(p in n for p in ("utilizado", "titular", "suplente", "casa", "fora",
                                "vitoria", "derrota", "empate")):
            return False
        return any(ch.isalpha() for ch in c)

    for c in celulas[idx_data + 1:]:
        if plausivel(c):
            return c.strip()
    for c in celulas:
        if plausivel(c):
            return c.strip()
    return ""


def interpretar_linhas(
    linhas: list[LinhaBruta],
    atleta: str,
    nascimento: str,
    fonte: str,
    ini: date | None,
    fim: date | None,
    janela_estimada: bool = False,
    identidade_ok: bool = True,
) -> list[Registro]:
    """Converte linhas cruas em Registros, mantendo o contexto de competição."""
    out: list[Registro] = []
    competicao_por_tabela: dict[int, str] = {}

    for l in linhas:
        if _eh_cabecalho_de_competicao(l):
            texto = " ".join(c for c in l.celulas if c).strip()
            if texto:
                competicao_por_tabela[l.tabela] = texto
            continue

        idx_data = next((i for i, c in enumerate(l.celulas) if parse_data(c)), None)
        if idx_data is None:
            continue
        d = parse_data(l.celulas[idx_data])
        if not (CICLO_INICIO <= d <= CICLO_FIM):
            continue

        competicao = competicao_por_tabela.get(l.tabela, "?")
        tipo, motivo = classificar_competicao(competicao)
        status = status_da_linha(l.texto)
        tem_janela = ini is not None or fim is not None
        dentro = (ini is None or d >= ini) and (fim is None or d <= fim)

        out.append(Registro(
            atleta=atleta,
            nascimento=nascimento,
            fonte=fonte,
            competicao=competicao,
            tipo=tipo,
            motivo_tipo=motivo,
            data=d.strftime("%d/%m/%Y"),
            adversario=_achar_adversario(l.celulas, idx_data),
            status=status,
            minutos=_achar_minutos(l.celulas),
            dentro_do_registro=dentro,
            janela_estimada=janela_estimada,
            veredito=avaliar(tipo, dentro, status, tem_janela,
                             janela_estimada, identidade_ok),
            bruto=l.texto,
        ))

    return _deduplicar(out)


def _deduplicar(registros: list[Registro]) -> list[Registro]:
    """Tabela aninhada faz a mesma partida aparecer duas vezes.

    Um atleta não joga duas partidas no mesmo dia, então (atleta, fonte, data)
    é chave suficiente. Mantém-se a ocorrência com mais informação bruta.
    """
    melhor: dict[tuple, Registro] = {}
    for r in registros:
        k = (r.atleta, r.fonte, r.data)
        atual = melhor.get(k)
        if atual is None or len(r.bruto) > len(atual.bruto):
            melhor[k] = r
    return sorted(melhor.values(), key=lambda r: parse_data(r.data) or date.min)


def extrair_de_html(html: str, atleta: str, nascimento: str, fonte: str,
                    ini: date | None, fim: date | None,
                    janela_estimada: bool = False,
                    identidade_ok: bool = True) -> list[Registro]:
    """Ponto de entrada puro: HTML em texto → lista de Registros."""
    return interpretar_linhas(extrair_linhas(html), atleta, nascimento, fonte,
                              ini, fim, janela_estimada, identidade_ok)


# --------------------------------------------------------------------------- #
# Guarda anti-homônimo
# --------------------------------------------------------------------------- #

def conferir_nascimento(corpo: str, esperado: date | None) -> str:
    """Devolve 'confere', 'nao_confere' ou 'nao_encontrada'.

    O original devolvia bool e falhava ABERTO: qualquer exceção virava True e os
    dados eram aceitos. Para a armadilha dos dois "Vitinho" isso é exatamente o
    avesso do necessário. Aqui 'nao_encontrada' é um terceiro estado: os dados
    não são descartados, mas todo Registro sai marcado para conferência.
    """
    if esperado is None:
        return "nao_encontrada"
    texto = corpo or ""
    normalizado = normalizar(texto)
    formatos = [
        esperado.strftime("%d/%m/%Y"), esperado.strftime("%d.%m.%Y"),
        esperado.strftime("%Y-%m-%d"), esperado.strftime("%d-%m-%Y"),
        esperado.strftime("%d/%m/%y"),
    ]
    meses = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]
    formatos.append(f"{esperado.day} {meses[esperado.month - 1]} {esperado.year}")
    formatos.append(f"{esperado.day:02d} {meses[esperado.month - 1]} {esperado.year}")
    if any(normalizar(f) in normalizado for f in formatos):
        return "confere"
    # Só se pode afirmar "não confere" quando HÁ alguma data de nascimento na
    # página. Sem nenhuma, o correto é dizer que não se sabe.
    if re.search(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}", texto):
        return "nao_confere"
    return "nao_encontrada"
