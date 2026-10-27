# -*- coding: utf-8 -*-
"""
Exporta os dados que a árvore interativa usa para data/arvore/ (JSON versionado; o build não precisa do GRP-Tool).

    python scripts/exportar_dados_arvore.py --grp-tool ../grp-tool --evidencias Evidencias.txt

- catalogos/*.json: catálogos do GRP-Tool (elemento-item, classificação orçamentária, centros de custo e combinações
  usadas por UO), cada um com a data e a origem da coleta. São fotos de uma data: o GRP é quem decide.
- contrato.json: campos de cada tipo do contrato WSDL, lido do RESUMO.md gerado por baixar_contratos_wsdl.py.
- casos/*.xml: envios e respostas reais (CPFs mascarados), separados do arquivo de evidências do Assistente GRP.
  O índice dos casos (títulos, datas e lições) fica escrito à mão em data/arvore/casos.json.
"""

import argparse
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE_DIR, "data", "arvore")
sys.path.insert(0, BASE_DIR)


def salvar(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"  {os.path.relpath(caminho, BASE_DIR)} ({os.path.getsize(caminho) // 1024} KB)")


def exportar_catalogos(pasta_grp_tool):
    sys.path.insert(0, os.path.abspath(pasta_grp_tool))
    from grp_tool import catalogo_dados, classificacao_dados, centros_custo_dados, conexoes_dados

    pasta = os.path.join(SAIDA, "catalogos")
    salvar(os.path.join(pasta, "elemento_item.json"),
           {"origem": catalogo_dados.ORIGEM, "registros": catalogo_dados.REGISTROS})
    salvar(os.path.join(pasta, "classificacao.json"),
           {"origem": classificacao_dados.ORIGEM, "dados": classificacao_dados.DADOS})
    salvar(os.path.join(pasta, "centros_custo.json"),
           {"origem": centros_custo_dados.ORIGEM, "dados": centros_custo_dados.DADOS})
    conexoes = {ano: {uo: {ei: [list(c) for c in combos] for ei, combos in itens.items()}
                      for uo, itens in uos.items()}
                for ano, uos in conexoes_dados.CONEXOES.items()}
    salvar(os.path.join(pasta, "conexoes.json"),
           {"origem": "GRP, relatório de conexões elemento-item (" + conexoes_dados.ORIGEM + "), coletado em 16/10/2026",
            "conexoes": conexoes, "nomes_uo": conexoes_dados.NOMES_UO})


def exportar_contrato(resumo):
    """RESUMO.md -> {servico: {tipo: [[campo, tipo, min, max], ...]}} (ordem do contrato)."""
    contrato, servico, tipo = {}, None, None
    with open(resumo, encoding="utf-8") as f:
        texto = f.read()
    data = re.search(r"baixados em (\S+ \S+)", texto)
    for linha in texto.splitlines():
        if linha.startswith("## "):
            servico, tipo = linha[3:].strip(), None
            contrato[servico] = {}
        elif linha.startswith("### ") and servico:
            tipo = linha[4:].strip().strip("`")
            contrato[servico][tipo] = []
        elif linha.startswith("- ") and tipo:
            m = re.match(r"- (\S+) \(([^,]+), (\w+)\.\.(\w+)\)", linha)
            if m:
                contrato[servico][tipo].append(list(m.groups()))
    salvar(os.path.join(SAIDA, "contrato.json"),
           {"origem": f"Contrato WSDL da produção baixado em {data.group(1) if data else '?'}", "servicos": contrato})


_URL_GATEWAY = re.compile(r"(/v1/documento/)[A-Za-z0-9+/=_-]{8,}(/)")


def mascarar(xml):
    xml = _URL_GATEWAY.sub(r"\g<1>MASCARADO\2", xml)
    # máscara completa (nem os últimos dígitos ficam): o repositório pode ser público
    return re.sub(r"(<cpf\w*>)\d{11}(</)", r"\g<1>00000000000\2", xml)


def exportar_evidencias(arquivo):
    """Separa o arquivo de evidências (blocos "NN_nome", envio, "RESPOSTA:", resposta, "----") em XMLs."""
    with open(arquivo, encoding="utf-8") as f:
        texto = f.read().split("\nLEIA-ME")[0]
    pasta = os.path.join(SAIDA, "casos")
    os.makedirs(pasta, exist_ok=True)
    for bloco in re.split(r"\n-{3,}\n", texto):
        bloco = bloco.strip()
        if not bloco:
            continue
        nome, resto = bloco.split("\n", 1)
        envio, resposta = re.split(r"\nRESPOSTA:\s*\n", resto, maxsplit=1)
        for sufixo, xml in (("envio", envio), ("resposta", resposta)):
            caminho = os.path.join(pasta, f"{nome.strip()}_{sufixo}.xml")
            with open(caminho, "w", encoding="utf-8", newline="\n") as f:
                f.write(mascarar(xml.strip()) + "\n")
        print(f"  casos/{nome.strip()}_{{envio,resposta}}.xml")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grp-tool", help="pasta do repositório GRP-Tool (para os catálogos)")
    ap.add_argument("--evidencias", help="arquivo de evidências do Assistente GRP (XMLs reais)")
    ap.add_argument("--resumo", default=os.path.join(BASE_DIR, "contratos", "producao", "2026-10-26", "RESUMO.md"))
    args = ap.parse_args()
    if args.grp_tool:
        exportar_catalogos(args.grp_tool)
    if args.resumo and os.path.exists(args.resumo):
        exportar_contrato(args.resumo)
    if args.evidencias:
        exportar_evidencias(args.evidencias)


if __name__ == "__main__":
    main()
