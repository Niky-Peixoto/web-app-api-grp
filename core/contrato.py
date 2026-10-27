# -*- coding: utf-8 -*-
"""
Validação de XML pelo contrato WSDL atual (core.contrato)

Usa data/arvore/contrato.json (campos de cada tipo, na ordem do contrato, com tipo e cardinalidade), gerado a partir
do RESUMO.md de scripts/baixar_contratos_wsdl.py. Confere o que o XSD confere para os nossos envelopes:
- ordem dos elementos (a sequência do contrato);
- elementos obrigatórios (minOccurs 1) e elementos fora do contrato;
- repetição só onde o contrato permite (maxOccurs unbounded);
- formato dos tipos simples (xs:int/long, xs:decimal, xs:dateTime).

O RESUMO.md lista as listas anônimas assim: "fooList (-)" seguido do item ("Foo (tns:fooRequest)") e, às vezes, dos
campos do item repetidos em linha; esses campos repetidos são ignorados aqui.
"""

import json
import os
import re
import xml.etree.ElementTree as ET

from core.config import DATA_DIR

CONTRATO_PATH = os.path.join(DATA_DIR, "arvore", "contrato.json")

_FORMATOS = {
    "xs:int": re.compile(r"-?\d+"),
    "xs:long": re.compile(r"-?\d+"),
    "xs:decimal": re.compile(r"-?\d+(\.\d+)?"),
    "xs:dateTime": re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?"),
}


def _sem_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


class Contrato:
    def __init__(self, path: str = CONTRATO_PATH):
        with open(path, encoding="utf-8") as f:
            self.dados = json.load(f)
        # nome do tipo -> (serviço, campos)
        self.tipos = {}
        for servico, tipos in self.dados["servicos"].items():
            for nome, campos in tipos.items():
                self.tipos.setdefault(nome, (servico, campos))

    def sequencia(self, tipo: str):
        """Campos de um tipo como (nome, tipo, min, max, item); item = (nome, tipo) nas listas anônimas."""
        campos = self.tipos[tipo][1]
        seq, i = [], 0
        while i < len(campos):
            nome, t, mn, mx = campos[i]
            if t == "-" and i + 1 < len(campos):
                item = campos[i + 1]
                seq.append((nome, t, mn, mx, (item[0], item[1], item[3])))
                i += 2
                # campos do item repetidos em linha logo depois dele
                if item[1].startswith("tns:") and item[1][4:] in self.tipos:
                    nomes_item = [c[0] for c in self.tipos[item[1][4:]][1]]
                    if [c[0] for c in campos[i:i + len(nomes_item)]] == nomes_item:
                        i += len(nomes_item)
                continue
            seq.append((nome, t, mn, mx, None))
            i += 1
        return seq

    def validar(self, xml: str):
        """Lista de problemas (vazia = o envelope segue o contrato)."""
        try:
            raiz = ET.fromstring(xml.strip().encode("utf-8"))
        except ET.ParseError as e:
            return [f"XML mal formado: {e}"]
        corpo = next((e for e in raiz.iter() if _sem_ns(e.tag) == "Body"), None)
        if corpo is None or len(corpo) == 0:
            return ["envelope sem soap:Body"]
        operacao = corpo[0]
        nome = _sem_ns(operacao.tag)
        if nome not in self.tipos:
            return [f"operação {nome} não está no contrato"]
        problemas = []
        self._elemento(operacao, nome, nome, problemas)
        return problemas

    def _elemento(self, el, tipo, caminho, problemas):
        seq = self.sequencia(tipo)
        nomes = [s[0] for s in seq]
        ultimo, vistos = -1, set()
        for filho in el:
            nome = _sem_ns(filho.tag)
            if nome not in nomes:
                problemas.append(f"{caminho}/{nome}: elemento fora do contrato")
                continue
            k = next((i for i in range(max(ultimo, 0), len(seq)) if nomes[i] == nome), None)
            if k is None:
                anterior = nomes[ultimo]
                problemas.append(f"{caminho}/{nome}: fora da ordem do contrato (deve vir antes de {anterior})")
                continue
            if k == ultimo and seq[k][3] != "unbounded":
                problemas.append(f"{caminho}/{nome}: repetido (o contrato permite um só)")
            for j in range(ultimo + 1, k):
                if seq[j][2] != "0" and j not in vistos:
                    problemas.append(f"{caminho}/{nomes[j]}: obrigatório e ausente")
            vistos.add(k)
            ultimo = k
            self._conteudo(filho, seq[k], f"{caminho}/{nome}", problemas)
        for j in range(ultimo + 1, len(seq)):
            if seq[j][2] != "0":
                problemas.append(f"{caminho}/{nomes[j]}: obrigatório e ausente")

    def _conteudo(self, el, campo, caminho, problemas):
        _, tipo, _, _, item = campo
        if item is not None:
            nome_item, tipo_item, _ = item
            for filho in el:
                if _sem_ns(filho.tag) != nome_item:
                    problemas.append(f"{caminho}/{_sem_ns(filho.tag)}: a lista só aceita {nome_item}")
                elif tipo_item.startswith("tns:"):
                    self._elemento(filho, tipo_item[4:], f"{caminho}/{nome_item}", problemas)
            return
        if tipo.startswith("tns:"):
            if tipo[4:] in self.tipos:
                self._elemento(el, tipo[4:], caminho, problemas)
            return
        formato = _FORMATOS.get(tipo)
        valor = (el.text or "").strip()
        if formato and len(el) == 0 and not formato.fullmatch(valor):
            problemas.append(f"{caminho}: '{valor}' não é {tipo}")


# =============================================================================
# Atualizar um envio antigo para o formato atual, preservando o texto (recuo, prefixos, valores)
# =============================================================================

_LINHA_FOLHA = re.compile(r"^\s*<([\w.-]+:)?([\w.-]+)(\s[^>]*)?(/>|>.*</(?:[\w.-]+:)?\2>)\s*$", re.DOTALL)
_LINHA_ABRE = re.compile(r"^\s*<([\w.-]+:)?([\w.-]+)(\s[^>]*)?>\s*$", re.DOTALL)
_LINHA_FECHA = re.compile(r"^\s*</([\w.-]+:)?([\w.-]+)>\s*$")


def _linhas_logicas(xml: str):
    """Junta as linhas de uma tag de abertura quebrada em várias (ex.: Envelope com dois xmlns)."""
    saida, atual = [], ""
    for linha in xml.split("\n"):
        atual = f"{atual}\n{linha}" if atual else linha
        if atual.strip().startswith("<") and not atual.rstrip().endswith(">"):
            continue
        saida.append(atual)
        atual = ""
    if atual:
        saida.append(atual)
    return saida


def _arvore_de_linhas(xml: str):
    """[nome, linha de abertura, filhos, linha de fechamento] por elemento; None se o XML não tiver um elemento por linha."""
    raiz = ["#", "", [], ""]
    pilha = [raiz]
    for linha in _linhas_logicas(xml.strip("\n")):
        texto = linha.strip()
        if not texto or texto.startswith("<?"):
            pilha[-1][2].append(["#texto", linha, [], ""])
            continue
        if _LINHA_FECHA.match(linha):
            if len(pilha) == 1 or _LINHA_FECHA.match(linha).group(2) != pilha[-1][0]:
                return None
            pilha[-1][3] = linha
            pilha.pop()
        elif _LINHA_FOLHA.match(linha):
            pilha[-1][2].append([_LINHA_FOLHA.match(linha).group(2), linha, [], None])
        elif _LINHA_ABRE.match(linha):
            no = [_LINHA_ABRE.match(linha).group(2), linha, [], ""]
            pilha[-1][2].append(no)
            pilha.append(no)
        else:
            return None
    return raiz if len(pilha) == 1 else None


def _texto(no) -> list:
    if no[0] == "#texto":
        return [no[1]]
    linhas = [no[1]] if no[0] != "#" else []
    for filho in no[2]:
        linhas += _texto(filho)
    if no[3]:
        linhas.append(no[3])
    return linhas


def atualizar(xml: str, c: "Contrato" = None):
    """Leva um envio antigo ao formato do contrato atual: tira campos que saíram do contrato e põe os campos na
    ordem do contrato, sem mexer em valores, recuo ou prefixos. Devolve (xml atualizado, lista do que mudou)."""
    c = c or contrato()
    raiz = _arvore_de_linhas(xml)
    if raiz is None:
        raise ValueError("XML sem um elemento por linha: não dá para atualizar preservando o texto")
    mudancas = []

    def visitar(no, tipo):
        seq = c.sequencia(tipo)
        ordem = {s[0]: i for i, s in enumerate(seq)}
        filhos = [f for f in no[2] if f[0] != "#texto"]
        removidos = [f[0] for f in filhos if f[0] not in ordem]
        if "retencaoList" in removidos and tipo == "solicitacaoOrdemPagamentoBancariaRequest":
            mudancas.append("`retencaoList` saiu do contrato da OP (19/10/2026): INSS e ISSQN ficam só na OLP")
            tem_irrf = any(item[0] == "retencao" for lista in filhos if lista[0] == "itemDePagamentoList"
                           for it in lista[2] for item in it[2])
            if not tem_irrf and "valorTotalRetencoes" in [f[0] for f in filhos]:
                removidos.append("valorTotalRetencoes")
                mudancas.append("`valorTotalRetencoes` sai junto: sem IRRF, a OP não declara retenção")
        for nome in removidos:
            if nome != "retencaoList" and nome != "valorTotalRetencoes":
                mudancas.append(f"`{nome}` não existe no contrato atual e foi retirado")
        filhos = [f for f in filhos if f[0] not in removidos]
        antes = [f[0] for f in filhos]
        filhos.sort(key=lambda f: ordem[f[0]])
        depois = [f[0] for f in filhos]
        for nome in _fora_de_ordem([ordem[n] for n in antes], antes):
            i = depois.index(nome)
            onde = f"depois de `{depois[i - 1]}`" if i > 0 else f"antes de `{depois[1]}`"
            texto = f"`{nome}` foi para a posição do contrato atual ({onde})"
            if texto not in mudancas:
                mudancas.append(texto)
        no[2] = filhos
        for f in filhos:
            campo = seq[ordem[f[0]]]
            if campo[4] is not None and campo[4][1].startswith("tns:"):
                for item in f[2]:
                    if item[0] == campo[4][0]:
                        visitar(item, campo[4][1][4:])
            elif campo[1].startswith("tns:") and campo[1][4:] in c.tipos and f[2]:
                visitar(f, campo[1][4:])

    corpo = next((n for n in _todos(raiz) if n[0] == "Body"), None)
    if corpo is None or not [f for f in corpo[2] if f[0] != "#texto"]:
        raise ValueError("envelope sem soap:Body")
    operacao = [f for f in corpo[2] if f[0] != "#texto"][0]
    visitar(operacao, operacao[0])
    novo = "\n".join(_texto(raiz))
    if xml.endswith("\n"):
        novo += "\n"
    return novo, [m for i, m in enumerate(mudancas) if m not in mudancas[:i]]


def _fora_de_ordem(posicoes, nomes):
    """Nomes que ficam fora da maior subsequência já ordenada: são os que de fato mudaram de lugar."""
    n = len(posicoes)
    comprimento, anterior = [1] * n, [-1] * n
    for i in range(n):
        for j in range(i):
            if posicoes[j] <= posicoes[i] and comprimento[j] + 1 > comprimento[i]:
                comprimento[i], anterior[i] = comprimento[j] + 1, j
    fica, i = set(), (max(range(n), key=lambda k: comprimento[k]) if n else -1)
    while i >= 0:
        fica.add(i)
        i = anterior[i]
    return [nomes[k] for k in range(n) if k not in fica]


def _todos(no):
    yield no
    for f in no[2]:
        yield from _todos(f)


contrato_atual = None


def contrato() -> Contrato:
    global contrato_atual
    if contrato_atual is None:
        contrato_atual = Contrato()
    return contrato_atual


# Nomes curtos dos serviços, para o dicionário.
NOME_CURTO = {
    "GerarNumeroProcessoGrpWS": "Processo",
    "SolicitacaoEmpenhoWS": "Empenho",
    "SolicitacaoReforcoDeEmpenhoWS": "Reforço",
    "SolicitacaoAnulacaoEmpenhoWS": "Anulação de empenho",
    "SolicitacaoOlpWS": "OLP",
    "SolicitacaoAnulacaoValoresNaOlpWS": "Anulação na OLP",
    "SolicOrdemPagamentoBancariaWS": "OP",
    "CancelamentoOrdemPagamentoBancariaWS": "Cancelamento de OP",
}


def _rotulo_tipo(tipo: str) -> str:
    if tipo == "-":
        return "lista"
    if tipo.startswith("tns:"):
        return "grupo de campos"
    return tipo


def resumo_tag(tag: str, c: "Contrato" = None) -> str:
    """Tipo e obrigatoriedade de uma tag no contrato atual, por serviço; envio e resposta separados.
    Ex.: 'Envio — OP: xs:int, obrigatório · Empenho, OLP: xs:long, obrigatório'."""
    c = c or contrato()
    tag = tag.strip("<>")
    operacoes = [s for nome, (s, _) in c.tipos.items() if nome == tag]
    grupos = {}  # (direção, rótulo do tipo, obrigatoriedade) -> serviços
    for nome_tipo, (servico, campos) in c.tipos.items():
        direcao = "Resposta" if "Response" in nome_tipo else "Envio"
        for nome, tipo, mn, mx in campos:
            if nome != tag:
                continue
            obrig = "obrigatório" if mn != "0" else "opcional"
            if mx == "unbounded":
                obrig += ", repetível"
            chave = (direcao, _rotulo_tipo(tipo), obrig)
            nome_servico = NOME_CURTO.get(servico, servico)
            grupos.setdefault(chave, [])
            if nome_servico not in grupos[chave]:
                grupos[chave].append(nome_servico)
    if not grupos:
        if operacoes:
            return "Operação (primeiro elemento dentro do Body)"
        return "Não está no contrato atual (26/10/2026)"
    partes = []
    for direcao in ("Envio", "Resposta"):
        ordem = list(NOME_CURTO.values())
        itens = [f"{', '.join(sorted(serv, key=ordem.index))}: {tipo}, {obrig}"
                 for (d, tipo, obrig), serv in sorted(grupos.items(), key=lambda g: min(ordem.index(s) for s in g[1]))
                 if d == direcao]
        if itens:
            partes.append(f"{direcao} — " + " · ".join(itens))
    return " | ".join(partes)
