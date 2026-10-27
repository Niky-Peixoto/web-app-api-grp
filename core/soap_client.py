# -*- coding: utf-8 -*-
"""
Conector e Test Runner SOAP (core.soap_client)
Executa testes reais contra os WebServices da PRODEMGE ou simulações via cache/fixtures homologadas.
"""

import re
import warnings
import requests
from urllib3.exceptions import InsecureRequestWarning
from core.config import (
    SOAP_HEADERS, DEFAULT_TIMEOUT,
    URL_GERAR_PROCESSO, URL_EMPENHO, URL_OLP,
    URL_OP_BANCARIA, URL_REFORCO_EMPENHO, URL_ANULACAO_EMPENHO
)
from core.renderer import default_renderer
from core.scenarios import default_scenarios

warnings.simplefilter('ignore', InsecureRequestWarning)


class GRPSoapClient:
    """Cliente SOAP para comunicação com os WebServices do GRP."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False  # Desativa interferência de proxy do sistema operacional

    def _post(self, url: str, payload_xml: str) -> dict:
        """Executa um POST SOAP síncrono e retorna status e resposta."""
        try:
            resp = self.session.post(
                url,
                data=payload_xml.encode('utf-8'),
                headers=SOAP_HEADERS,
                verify=False,
                timeout=self.timeout
            )
            text = resp.text
            status_code = resp.status_code
            
            # Análise de sucesso nos padrões GRP
            tem_erro_negocio = ("<mensagens>" in text and not ("41040" in text or "51424" in text))
            tem_fault = "faultcode" in text or "faultstring" in text
            if tem_fault or tem_erro_negocio:
                sucesso = False
            else:
                sucesso = ("41040" in text) or ("51424" in text) or ("numeroDocumento" in text) or ("<return>" in text and "</return>" in text)
            
            return {
                "sucesso": sucesso,
                "status_code": status_code,
                "response_xml": default_renderer.pretty_xml(text),
                "erro": None if sucesso else self._extrair_mensagem_erro(text)
            }
        except Exception as e:
            return {
                "sucesso": False,
                "status_code": 0,
                "response_xml": f"<!-- Erro de conexão com {url}: {str(e)} -->",
                "erro": str(e)
            }

    @staticmethod
    def _extrair_mensagem_erro(xml_str: str) -> str:
        """Extrai mensagem de erro da tag <descricao> ou <faultstring>."""
        match_desc = re.search(r'<descricao>(.*?)</descricao>', xml_str)
        if match_desc:
            return match_desc.group(1)
        match_fault = re.search(r'<faultstring>(.*?)</faultstring>', xml_str)
        if match_fault:
            return match_fault.group(1)
        return "Erro retornado sem detalhamento na tag <descricao>"

    def test_live_stage1(self, params: dict) -> dict:
        """Executa chamada real no GerarNumeroProcessoGrpWS."""
        req_xml = default_renderer.render_stage1(params)
        res = self._post(URL_GERAR_PROCESSO, req_xml)
        res["request_xml"] = req_xml
        
        # Extrai número do processo
        match_ret = re.search(r'<return>(.*?)</return>', res["response_xml"])
        res["documento"] = match_ret.group(1) if match_ret else None
        return res

    def test_live_stage2(self, params: dict, numero_processo: str) -> dict:
        """Executa chamada real no SolicitacaoEmpenhoWS."""
        req_xml = default_renderer.render_stage2(params, numero_processo)
        res = self._post(URL_EMPENHO, req_xml)
        res["request_xml"] = req_xml
        
        match_doc = re.search(r'<numeroDocumento>(.*?)</numeroDocumento>', res["response_xml"])
        res["documento"] = match_doc.group(1) if match_doc else None
        return res

    def test_live_stage3(self, params: dict, numero_empenho: str) -> dict:
        """Executa chamada real no SolicitacaoOlpWS."""
        req_xml = default_renderer.render_stage3(params, numero_empenho)
        res = self._post(URL_OLP, req_xml)
        res["request_xml"] = req_xml
        
        match_doc = re.search(r'<numeroDocumento>(.*?)</numeroDocumento>', res["response_xml"])
        res["documento"] = match_doc.group(1) if match_doc else None
        return res

    def test_live_stage4(self, params: dict, numero_olp: str) -> dict:
        """Executa chamada real no SolicOrdemPagamentoBancariaWS."""
        req_xml = default_renderer.render_stage4(params, numero_olp)
        res = self._post(URL_OP_BANCARIA, req_xml)
        res["request_xml"] = req_xml
        
        match_doc = re.search(r'<numeroDocumento>(.*?)</numeroDocumento>', res["response_xml"])
        res["documento"] = match_doc.group(1) if match_doc else None
        match_sol = re.search(r'<numeroSolicitacao>(.*?)</numeroSolicitacao>', res["response_xml"])
        res["numero_solicitacao"] = match_sol.group(1) if match_sol else None
        match_sit = re.search(r'<situacaoSolicitacao>(.*?)</situacaoSolicitacao>', res["response_xml"])
        res["situacao"] = match_sit.group(1) if match_sit else None
        return res

    def test_live_reforco(self, params: dict) -> dict:
        """Executa chamada real no SolicitacaoReforcoDeEmpenhoWS."""
        req_xml = default_renderer.render_reforco(params)
        res = self._post(URL_REFORCO_EMPENHO, req_xml)
        res["request_xml"] = req_xml
        match_doc = re.search(r'<numeroDocumento>(.*?)</numeroDocumento>', res["response_xml"])
        res["documento"] = match_doc.group(1) if match_doc else params.get("numero_empenho")
        match_sit = re.search(r'<situacaoSolicitacao>(.*?)</situacaoSolicitacao>', res["response_xml"])
        res["situacao"] = match_sit.group(1) if match_sit else None
        return res

    def test_live_anulacao(self, params: dict) -> dict:
        """Executa chamada real no SolicitacaoAnulacaoEmpenhoWS."""
        req_xml = default_renderer.render_anulacao(params)
        res = self._post(URL_ANULACAO_EMPENHO, req_xml)
        res["request_xml"] = req_xml
        match_doc = re.search(r'<numeroDocumento>(.*?)</numeroDocumento>', res["response_xml"])
        res["documento"] = match_doc.group(1) if match_doc else params.get("numero_empenho")
        match_sit = re.search(r'<situacaoSolicitacao>(.*?)</situacaoSolicitacao>', res["response_xml"])
        res["situacao"] = match_sit.group(1) if match_sit else None
        return res
    def test_offline_scenario(self, scenario_id: str) -> dict:
        """
        Retorna o resultado homologado em cache para o cenário solicitado.
        Garante fidelidade de 100% aos dados testados e zero chamadas na rede.
        """
        scenario = default_scenarios.get_scenario(scenario_id)
        if not scenario:
            return {"sucesso": False, "erro": f"Cenário {scenario_id} não encontrado."}
        return {
            "sucesso": True,
            "identificador": scenario.get("identificador"),
            "status_homologacao": scenario.get("status_homologacao"),
            "xml_data": scenario.get("xml_data"),
            "modo": "cache_offline"
        }


# Instância singleton padrão
default_soap_client = GRPSoapClient()
