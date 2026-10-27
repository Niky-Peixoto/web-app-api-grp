# -*- coding: utf-8 -*-
"""
Baixa os contratos WSDL/XSD atuais dos serviços SOAP do GRP e confere os endpoints.

Só faz GET em "<endpoint>?wsdl" (e nos arquivos importados por ele). Nenhum POST, nenhuma solicitação é criada no
GRP. Precisa rodar de dentro da rede da SEF/VPN (de fora, o GRP não responde).

Uso (no PowerShell, na pasta onde está este arquivo, ou na raiz do repositório com scripts/ na frente):
    python scripts/baixar_contratos_wsdl.py                       # produção e desenvolvimento
    python scripts/baixar_contratos_wsdl.py --ambiente producao
    python scripts/baixar_contratos_wsdl.py --transporte requests # padrão: curl (curl.exe do Windows)

Saída: contratos/<ambiente>/<AAAA-MM-DD>/
    <Servico>.wsdl e os arquivos importados (?wsdl=..., ?xsd=...)
    RESUMO.md  - situação de cada endpoint (HTTP, redirecionamento, operações) e os campos de cada tipo do contrato

Transporte: por padrão usa o curl.exe nativo (o mesmo cliente que a borda da PRODEMGE aceita em todas as máquinas
testadas); --transporte requests usa a biblioteca requests. Nada de imitar navegador.
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse, parse_qs

_PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
# Dentro do repositório (pasta scripts/) os contratos vão para a raiz; copiado sozinho, para a pasta do script.
BASE_DIR = os.path.dirname(_PASTA_SCRIPT) if os.path.basename(_PASTA_SCRIPT) == "scripts" else _PASTA_SCRIPT

AMBIENTES = {
    "producao": "https://www.grp.servicos.mg.gov.br/serviceBus",
    "desenvolvimento": "https://desenvolvimento.grp.servicos.mg.gov.br/serviceBus",
}

# (caminho a partir de /serviceBus, nome funcional) - os 8 serviços documentados
SERVICOS = [
    ("institucional/GerarNumeroProcessoGrpWS", "Geração de número de processo"),
    ("empenho/SolicitacaoEmpenhoWS", "Solicitação de empenho"),
    ("empenho/SolicitacaoReforcoDeEmpenhoWS", "Reforço de empenho"),
    ("empenho/SolicitacaoAnulacaoEmpenhoWS", "Anulação de empenho"),
    ("empenho/SolicitacaoOlpWS", "Solicitação de OLP"),
    ("empenho/SolicitacaoAnulacaoValoresNaOlpWS", "Anulação de valores na OLP"),
    ("pagBancarioEEscritural/SolicOrdemPagamentoBancariaWS", "OP bancária"),
    ("pagBancarioEEscritural/CancelamentoOrdemPagamentoBancariaWS", "Cancelamento de OP bancária"),
]

NS = {
    "wsdl": "http://schemas.xmlsoap.org/wsdl/",
    "xsd": "http://www.w3.org/2001/XMLSchema",
    "soap": "http://schemas.xmlsoap.org/wsdl/soap/",
}


def baixar(url, transporte, timeout=30):
    """GET sem seguir redirecionamento. Retorna (status, location, corpo)."""
    if transporte == "requests":
        import requests
        try:
            import truststore
            truststore.inject_into_ssl()
        except ImportError:
            pass
        r = requests.get(url, timeout=timeout, allow_redirects=False)
        return r.status_code, r.headers.get("Location", ""), r.text
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        sys.exit("curl não encontrado. Use --transporte requests.")
    proc = subprocess.run(
        [curl, "-sS", "--max-time", str(timeout), "-D", "-", url],
        capture_output=True, timeout=timeout + 10,
    )
    if proc.returncode != 0:
        return 0, "", proc.stderr.decode("utf-8", "replace")
    bruto = proc.stdout.decode("utf-8", "replace")
    cabecalho, _, corpo = bruto.partition("\r\n\r\n")
    while corpo.startswith("HTTP/"):  # proxy (CONNECT) ou 100 Continue: o cabeçalho que vale é o último
        cabecalho, _, corpo = corpo.partition("\r\n\r\n")
    status = int(re.search(r"HTTP/[\d.]+ (\d+)", cabecalho).group(1)) if cabecalho.startswith("HTTP") else 0
    local = re.search(r"(?im)^location:\s*(\S+)", cabecalho)
    return status, local.group(1) if local else "", corpo


def nome_arquivo(url, servico):
    """SolicitacaoOlpWS?wsdl -> SolicitacaoOlpWS.wsdl; ?wsdl=X.wsdl -> X.wsdl; ?xsd=1 -> SolicitacaoOlpWS_xsd1.xsd"""
    qs = parse_qs(urlparse(url).query, keep_blank_values=True)
    if qs.get("wsdl") and qs["wsdl"][0]:
        return qs["wsdl"][0] if qs["wsdl"][0].endswith(".wsdl") else qs["wsdl"][0] + ".wsdl"
    if "xsd" in qs:
        return f"{servico}_xsd{qs['xsd'][0] or ''}.xsd"
    return f"{servico}.wsdl"


def importados(xml_texto, url_base):
    """URLs de wsdl:import / xsd:import / xsd:include no mesmo servidor."""
    try:
        raiz = ET.fromstring(xml_texto.encode("utf-8"))
    except ET.ParseError:
        return []
    urls = []
    for el in raiz.iter():
        local = el.tag.split("}")[-1]
        if local in ("import", "include"):
            alvo = el.get("location") or el.get("schemaLocation")
            if alvo:
                url = urljoin(url_base, alvo)
                if urlparse(url).hostname == urlparse(url_base).hostname:
                    urls.append(url)
    return urls


def resumir_tipos(textos):
    """{tipo: [campo (tipo, min..max)]} de todos os complexType dos arquivos baixados."""
    tipos, operacoes, enderecos = {}, set(), set()
    for texto in textos:
        try:
            raiz = ET.fromstring(texto.encode("utf-8"))
        except ET.ParseError:
            continue
        for op in raiz.iterfind(".//wsdl:portType/wsdl:operation", NS):
            operacoes.add(op.get("name"))
        for end in raiz.iterfind(".//soap:address", NS):
            enderecos.add(end.get("location"))
        for ct in raiz.iter(f"{{{NS['xsd']}}}complexType"):
            nome = ct.get("name")
            if not nome:
                continue
            campos = []
            for el in ct.iter(f"{{{NS['xsd']}}}element"):
                minimo = el.get("minOccurs", "1")
                maximo = el.get("maxOccurs", "1")
                campos.append(f"{el.get('name') or el.get('ref')} ({el.get('type', '-')}, {minimo}..{maximo})")
            tipos[nome] = campos
    return tipos, sorted(operacoes), sorted(enderecos)


def processar_servico(base, caminho, transporte, pasta):
    servico = caminho.split("/")[-1]
    url = f"{base}/{caminho}?wsdl"
    status, local, corpo = baixar(url, transporte)
    linha = {"servico": servico, "url": url, "status": status, "redirecionamento": local, "arquivos": [],
             "textos": [], "situacao": ""}
    if status in (301, 302, 303, 307, 308):
        linha["situacao"] = "indisponível (redireciona)" if "indisponivel" in local else "redireciona"
        return linha
    if status != 200 or "definitions" not in corpo[:2000]:
        linha["situacao"] = f"sem contrato (HTTP {status})"
        return linha
    fila, vistos = [(url, corpo)], {url}
    while fila:
        u, texto = fila.pop(0)
        arquivo = nome_arquivo(u, servico)
        with open(os.path.join(pasta, arquivo), "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        linha["arquivos"].append(arquivo)
        linha["textos"].append(texto)
        for imp in importados(texto, u):
            if imp not in vistos:
                vistos.add(imp)
                st, _, tx = baixar(imp, transporte)
                if st == 200:
                    fila.append((imp, tx))
    linha["situacao"] = "ok"
    return linha


def escrever_resumo(pasta, ambiente, base, linhas):
    hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    md = [f"# Contratos WSDL - {ambiente} - baixados em {hoje}", "", f"Base: `{base}`", "",
          "| Serviço | HTTP | Situação | Operações | Endereço declarado no contrato |", "|---|---|---|---|---|"]
    detalhes = []
    for ln in linhas:
        tipos, ops, ends = resumir_tipos(ln["textos"])
        situacao = ln["situacao"] + (f" → `{ln['redirecionamento']}`" if ln["redirecionamento"] else "")
        md.append(f"| `{ln['servico']}` | {ln['status']} | {situacao} | {', '.join(ops) or '-'} | "
                  f"{', '.join(f'`{e}`' for e in ends) or '-'} |")
        if tipos:
            detalhes += ["", f"## {ln['servico']}", "", "Arquivos: " + ", ".join(f"`{a}`" for a in ln["arquivos"])]
            for nome in sorted(tipos):
                detalhes += ["", f"### `{nome}`", ""] + [f"- {c}" for c in tipos[nome]]
    with open(os.path.join(pasta, "RESUMO.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md + detalhes) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ambiente", choices=[*AMBIENTES, "todos"], default="todos")
    ap.add_argument("--transporte", choices=["curl", "requests"], default="curl")
    args = ap.parse_args()
    data = datetime.date.today().isoformat()
    for ambiente in (AMBIENTES if args.ambiente == "todos" else [args.ambiente]):
        base = AMBIENTES[ambiente]
        pasta = os.path.join(BASE_DIR, "contratos", ambiente, data)
        os.makedirs(pasta, exist_ok=True)
        print(f"\n== {ambiente}: {base}")
        linhas = []
        for caminho, funcional in SERVICOS:
            ln = processar_servico(base, caminho, args.transporte, pasta)
            print(f"  {funcional:<32} HTTP {ln['status']:<4} {ln['situacao']}  {len(ln['arquivos'])} arquivo(s)")
            linhas.append(ln)
        escrever_resumo(pasta, ambiente, base, linhas)
        print(f"  Resumo: {os.path.join(pasta, 'RESUMO.md')}")


if __name__ == "__main__":
    main()
