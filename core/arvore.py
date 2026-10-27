# -*- coding: utf-8 -*-
"""
Gerador da árvore interativa (core.arvore)

Junta web/arvore.html, web/arvore.css, web/grp_xml.js, web/arvore.js e os dados de data/arvore/ (catálogos datados,
casos reais, contrato) num único arvore_interativa_grp.html, que abre sem servidor e sem internet.
"""

import json
import os
from datetime import datetime

from core.contrato import atualizar, contrato, resumo_tag
from core.config import (BASE_DIR, DATA_DIR, FAVICON_GRP, LOGO_GRP, LOGO_TESOURO, OUTPUT_HTML_PATH,
                         VERSAO_DOCUMENTACAO)
from core.markdown_generator import generate_markdown_manual
from core.registry import default_registry
from core.sanitizer import sanitize_xml_text

WEB_DIR = os.path.join(BASE_DIR, "web")
ARVORE_DIR = os.path.join(DATA_DIR, "arvore")


def _ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def _json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def carregar_casos() -> list:
    """Índice data/arvore/casos.json com o envio e a resposta de cada caso (CPFs mascarados)."""
    casos = []
    for caso in _json(os.path.join(ARVORE_DIR, "casos.json")):
        pasta = os.path.join(ARVORE_DIR, "casos")
        extensao = caso.get("formato_resposta", "xml")
        original = sanitize_xml_text(_ler(os.path.join(pasta, f"{caso['id']}_envio.xml")).strip())
        # Envio antigo (campo que saiu do contrato, ordem diferente): a página mostra o formato atual, com os mesmos
        # valores, e guarda o original para consulta.
        envio, ajustes = atualizar(original) if contrato().validar(original) else (original, [])
        casos.append({**caso, "envio": envio, "envio_original": original if ajustes else "", "ajustes": ajustes,
                      "resposta": sanitize_xml_text(_ler(os.path.join(pasta, f"{caso['id']}_resposta.{extensao}")).strip())})
    return casos


def montar_dados() -> dict:
    pasta = os.path.join(ARVORE_DIR, "catalogos")
    return {
        "catalogos": {nome: _json(os.path.join(pasta, f"{nome}.json"))
                      for nome in ("elemento_item", "classificacao", "centros_custo", "conexoes")},
        "versao": VERSAO_DOCUMENTACAO,
        "casos": carregar_casos(),
        "contrato": _json(os.path.join(ARVORE_DIR, "contrato.json")),
        "dicionario": [{"tag": t["name"].strip("<>"), "conceito": t["conceito"], "regra": t["regra"],
                        "contrato": resumo_tag(t["name"])}
                       for t in default_registry.get_all_tags()],
        "manual": generate_markdown_manual(),
        "ajudante": _ler(os.path.join(WEB_DIR, "ajudante_envio.ps1")),
    }


def gerar_html(agora: datetime | None = None) -> str:
    agora = agora or datetime.now()
    dados = json.dumps(montar_dados(), ensure_ascii=False, separators=(",", ":"))
    # Dentro de <script>, "</" fecharia a tag antes da hora.
    dados = dados.replace("</", "<\\/")
    trocas = {
        "{{CSS}}": _ler(os.path.join(WEB_DIR, "arvore.css")),
        "{{GRP_XML_JS}}": _ler(os.path.join(WEB_DIR, "grp_xml.js")),
        "{{ARVORE_JS}}": _ler(os.path.join(WEB_DIR, "arvore.js")),
        "{{DADOS_JSON}}": dados,
        "{{FAVICON}}": FAVICON_GRP,
        "{{LOGO_GRP}}": LOGO_GRP,
        "{{LOGO_TESOURO}}": LOGO_TESOURO,
        "{{VERSAO}}": VERSAO_DOCUMENTACAO,
        "{{BUILD}}": agora.strftime("%d/%m/%Y %H:%M"),
        "{{BUILD_ISO}}": agora.isoformat(timespec="seconds"),
    }
    html = _ler(os.path.join(WEB_DIR, "arvore.html"))
    for marcador, valor in trocas.items():
        html = html.replace(marcador, valor)
    return html


def gerar_arvore(caminho: str = OUTPUT_HTML_PATH) -> str:
    html = gerar_html()
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return caminho
