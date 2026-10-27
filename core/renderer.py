# -*- coding: utf-8 -*-
"""
Motor de Renderização de Templates XML Jinja2 (core.renderer)
Renderiza os envelopes SOAP para todas as operações e cenários da esteira.
"""

import os
import time
import xml.dom.minidom
from jinja2 import Environment, FileSystemLoader, select_autoescape
from core.config import TEMPLATES_DIR


class XMLRenderer:
    """Motor de renderização de contratos SOAP com Jinja2."""

    def __init__(self, templates_dir: str = TEMPLATES_DIR):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(['xml', 'html']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    @staticmethod
    def pretty_xml(xml_str: str) -> str:
        """Formata a string XML com indentação limpa de 2 espaços."""
        if not xml_str:
            return ""
        try:
            dom = xml.dom.minidom.parseString(xml_str)
            pretty = dom.toprettyxml(indent="  ")
            lines = [line for line in pretty.split('\n') if line.strip()]
            return '\n'.join(lines)
        except Exception:
            return xml_str

    def render(self, template_name: str, context: dict) -> str:
        """Renderiza um template Jinja2 específico com o contexto fornecido."""
        template = self.env.get_template(template_name)
        raw_xml = template.render(**context)
        return self.pretty_xml(raw_xml)

    def render_stage1(self, params: dict) -> str:
        """Renderiza o XML de envio da Etapa 1 (GerarNumeroProcessoGrpWS)."""
        ctx = {
            "ano_exercicio": params.get("ano_exercicio", "2026"),
            "orgao_executor": params.get("orgao_executor", "10190"),
            "codigo_processo": params.get("codigo_processo", "18"),
            "ua": params.get("ua", "1019080124"),
            "uo": params.get("uo", "10191"),
            "codigo_sistema_solicitante": params.get("codigo_sistema_solicitante", "51")
        }
        return self.render("stage1_processo.xml.j2", ctx)

    def render_stage2(self, params: dict, numero_processo: str = "2026-10190-00001") -> str:
        """Renderiza o XML de envio da Etapa 2 (SolicitacaoEmpenhoWS)."""
        ctx = dict(params)
        ctx["numero_processo"] = numero_processo
        if "num_requisicao" not in ctx:
            ctx["num_requisicao"] = str(int(time.time()))
        return self.render("stage2_empenho.xml.j2", ctx)

    def render_stage3(self, params: dict, numero_empenho: str = "22575") -> str:
        """Renderiza o XML de envio da Etapa 3 (SolicitacaoOlpWS)."""
        ctx = dict(params)
        ctx["numero_empenho"] = numero_empenho
        if "retencoes_list_olp" in ctx and "retencoes_list" not in params:
            ctx["retencoes_list"] = ctx["retencoes_list_olp"]
        if "num_requisicao" not in ctx:
            ctx["num_requisicao"] = str(int(time.time()) + 1)
        return self.render("stage3_olp.xml.j2", ctx)

    def render_stage4(self, params: dict, numero_olp: str = "30001") -> str:
        """Renderiza o XML de envio da Etapa 4 (SolicOrdemPagamentoBancariaWS)."""
        ctx = dict(params)
        ctx["numero_olp"] = numero_olp
        if "retencoes_list_op" in ctx and "retencoes_list" not in params:
            ctx["retencoes_list"] = ctx["retencoes_list_op"]
        if "num_requisicao" not in ctx:
            ctx["num_requisicao"] = str(int(time.time()) + 2)
        return self.render("stage4_op.xml.j2", ctx)

    def render_reforco(self, params: dict) -> str:
        """Renderiza o XML de envio da operação de Reforço de Empenho."""
        ctx = dict(params)
        if "num_requisicao" not in ctx:
            ctx["num_requisicao"] = str(int(time.time()) + 3)
        if not ctx.get("numero_empenho"):
            ctx["numero_empenho"] = "49746"
        return self.render("manut_reforco.xml.j2", ctx)

    def render_anulacao(self, params: dict) -> str:
        """Renderiza o XML de envio da operação de Anulação de Saldo de Empenho."""
        ctx = dict(params)
        if "num_requisicao" not in ctx:
            ctx["num_requisicao"] = str(int(time.time()) + 4)
        if not ctx.get("numero_empenho"):
            ctx["numero_empenho"] = "49746"
        return self.render("manut_anulacao.xml.j2", ctx)


# Instância singleton padrão
default_renderer = XMLRenderer()
