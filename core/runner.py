# -*- coding: utf-8 -*-
"""
Motor Universal de Execução e Testes (core.runner)
Orquestra cenários, etapas individuais e cadeias completas em modo Simulação ou Live (SOAP real).
Garante persistência automática dos logs e XMLs de cada execução em output/runs/.
"""

import os
import json
import time
from datetime import datetime
from core.config import OUTPUT_RUNS_DIR
from core.renderer import default_renderer
from core.scenarios import default_scenarios
from core.soap_client import default_soap_client


class UniversalRunner:
    """Orquestrador universal de testes e execução da API GRP."""

    def __init__(self, runs_dir: str = OUTPUT_RUNS_DIR):
        self.runs_dir = runs_dir
        os.makedirs(self.runs_dir, exist_ok=True)

    def save_run_result(self, result: dict) -> str:
        """Salva o resultado estruturado da execução em JSON no diretório output/runs/."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ident = result.get("scenario_id") or result.get("stage") or result.get("tipo") or "execucao"
        filename = f"run_{timestamp}_{ident}.json"
        filepath = os.path.join(self.runs_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        result["saved_log_path"] = filepath
        return filepath

    def run_scenario(self, scenario_id: str, overrides: dict = None, live: bool = False) -> dict:
        """
        Executa um cenário combinatório completo (1. Processo ➔ 2. Empenho ➔ 3. OLP ➔ 4. OP).
        Em modo live=False, gera e valida todos os XMLs offline.
        Em modo live=True, dispara a cadeia sequencial contra o GRP PRODEMGE.
        """
        p = default_scenarios.resolve_scenario_params(scenario_id, overrides)

        if live:
            res = self.run_chain(stages=["processo", "empenho", "olp", "op"], params=p, live=True)
            res["scenario_id"] = scenario_id
            self.save_run_result(res)
            return res
        else:
            # Modo Simulação / Offline
            num_proc_mock = "101901800000240202611"
            num_emp_mock = "41918"
            num_olp_mock = "42008"

            p_olp = dict(p)
            if "retencoes_list_olp" in p:
                p_olp["retencoes_list"] = p["retencoes_list_olp"]

            p_op = dict(p)
            if "retencoes_list_op" in p:
                p_op["retencoes_list"] = p["retencoes_list_op"]

            req1 = default_renderer.render_stage1(p)
            req2 = default_renderer.render_stage2(p, num_proc_mock)
            req3 = default_renderer.render_stage3(p_olp, num_emp_mock)
            req4 = default_renderer.render_stage4(p_op, num_olp_mock)

            res = {
                "tipo": "cenario_completo",
                "scenario_id": scenario_id,
                "modo": "simulacao_offline",
                "sucesso": True,
                "data_execucao": datetime.now().isoformat(),
                "parametros": p,
                "documentos_simulados": {
                    "processo": num_proc_mock,
                    "empenho": num_emp_mock,
                    "olp": num_olp_mock,
                    "op": "64621"
                },
                "etapas": {
                    "stage1_processo": {"request_xml": req1},
                    "stage2_empenho": {"request_xml": req2},
                    "stage3_olp": {"request_xml": req3},
                    "stage4_op": {"request_xml": req4}
                }
            }
            self.save_run_result(res)
            return res

    def run_stage(self, stage_name: str, params: dict = None, live: bool = False) -> dict:
        """
        Executa uma etapa individual da esteira:
        'processo', 'empenho', 'olp', 'op', 'reforco', 'anulacao'.
        """
        if params is None:
            params = {}

        st = stage_name.lower().strip()
        p = dict(params)

        # Preenchimento de defaults mínimos se ausentes
        p.setdefault("ano_exercicio", "2026")
        p.setdefault("orgao_executor", "10190")
        p.setdefault("uo", "10191")
        p.setdefault("ua", "1019080124")
        p.setdefault("cpf_ordenador", "00000000191")
        p.setdefault("cpf_operador", "00000000191")
        p.setdefault("credor_cpf_cnpj", "00000000272")
        p.setdefault("credor_classificacao", "BENEFICIÁRIOS DIVERSOS")
        p.setdefault("valor", "1.00")
        p.setdefault("tipo_conta_a_debitar", 1)
        p.setdefault("tipo_conta_a_creditar", 1)
        p.setdefault("op_cod_banco_cred", "001")
        p.setdefault("op_ag_cred", "9012")
        p.setdefault("op_dv_ag_cred", "6")
        p.setdefault("op_conta_cred", "90006")
        p.setdefault("op_dv_conta_cred", "3")
        p.setdefault("codigo_forma_pagamento", "001")
        p.setdefault("data_programada_pagamento", "2026-08-20T00:00:00")
        p.setdefault("finalidade_pagamento", "01")

        # Normalização de Retenções e Valores Fiscobancários
        v_inss = float(p.get("retencao_inss", 0.0)) if p.get("retencao_inss") else 0.0
        v_issqn = float(p.get("retencao_issqn", 0.0)) if p.get("retencao_issqn") else 0.0
        if v_inss > 0 or v_issqn > 0 or p.get("ha_retencao"):
            p["ha_retencao"] = True
            v_bruto = float(p.get("valor", "1.00"))
            v_tot_ret = v_inss + v_issqn
            v_liq = v_bruto - v_tot_ret
            p["valor_retido"] = f"{v_tot_ret:.2f}"
            p["valor_liquido"] = f"{v_liq:.2f}"

            if not p.get("retencoes_list_olp"):
                r_olp = []
                if v_inss > 0:
                    r_olp.append({"codigo_tipo_retencao": "14", "valor_retencao": f"{v_inss:.2f}", "credor_retencao": "29979036000140"})
                if v_issqn > 0:
                    r_olp.append({"codigo_tipo_retencao": "13", "valor_retencao": f"{v_issqn:.2f}", "credor_retencao": "18715383000140"})
                p["retencoes_list_olp"] = r_olp

            p["retencoes_list_op"] = []
        else:
            p.setdefault("valor_retido", "0.00")
            p.setdefault("valor_liquido", p["valor"])

        if st in ("stage1", "processo"):
            if live:
                res_soap = default_soap_client.test_live_stage1(p)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "processo",
                    "modo": "live_soap",
                    "sucesso": res_soap["sucesso"],
                    "documento": res_soap.get("documento"),
                    "request_xml": res_soap.get("request_xml"),
                    "response_xml": res_soap.get("response_xml"),
                    "erro": res_soap.get("erro")
                }
            else:
                req = default_renderer.render_stage1(p)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "processo",
                    "modo": "simulacao_offline",
                    "sucesso": True,
                    "documento_simulado": "101901800000240202611",
                    "request_xml": req
                }

        elif st in ("stage2", "empenho"):
            num_proc = p.get("numero_processo") or p.get("processo") or "101901800000240202611"
            if live:
                res_soap = default_soap_client.test_live_stage2(p, num_proc)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "empenho",
                    "modo": "live_soap",
                    "sucesso": res_soap["sucesso"],
                    "numero_processo_vinculado": num_proc,
                    "documento": res_soap.get("documento"),
                    "request_xml": res_soap.get("request_xml"),
                    "response_xml": res_soap.get("response_xml"),
                    "erro": res_soap.get("erro")
                }
            else:
                req = default_renderer.render_stage2(p, num_proc)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "empenho",
                    "modo": "simulacao_offline",
                    "sucesso": True,
                    "numero_processo_vinculado": num_proc,
                    "documento_simulado": "41918",
                    "request_xml": req
                }

        elif st in ("stage3", "olp"):
            num_emp = p.get("numero_empenho") or p.get("empenho") or "41918"
            p_olp = dict(p)
            if "retencoes_list_olp" in p:
                p_olp["retencoes_list"] = p["retencoes_list_olp"]
            if live:
                res_soap = default_soap_client.test_live_stage3(p_olp, num_emp)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "olp",
                    "modo": "live_soap",
                    "sucesso": res_soap["sucesso"],
                    "numero_empenho_vinculado": num_emp,
                    "documento": res_soap.get("documento"),
                    "request_xml": res_soap.get("request_xml"),
                    "response_xml": res_soap.get("response_xml"),
                    "erro": res_soap.get("erro")
                }
            else:
                req = default_renderer.render_stage3(p_olp, num_emp)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "olp",
                    "modo": "simulacao_offline",
                    "sucesso": True,
                    "numero_empenho_vinculado": num_emp,
                    "documento_simulado": "42008",
                    "request_xml": req
                }

        elif st in ("stage4", "op"):
            num_olp = p.get("numero_olp") or p.get("olp") or "42008"
            p_op = dict(p)
            if "retencoes_list_op" in p:
                p_op["retencoes_list"] = p["retencoes_list_op"]
            if live:
                res_soap = default_soap_client.test_live_stage4(p_op, num_olp)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "op",
                    "modo": "live_soap",
                    "sucesso": res_soap["sucesso"],
                    "numero_olp_vinculada": num_olp,
                    "documento": res_soap.get("documento"),
                    "numero_solicitacao": res_soap.get("numero_solicitacao"),
                    "request_xml": res_soap.get("request_xml"),
                    "response_xml": res_soap.get("response_xml"),
                    "erro": res_soap.get("erro")
                }
            else:
                req = default_renderer.render_stage4(p_op, num_olp)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "op",
                    "modo": "simulacao_offline",
                    "sucesso": True,
                    "numero_olp_vinculada": num_olp,
                    "documento_simulado": "64621",
                    "request_xml": req
                }

        elif st == "reforco":
            if live:
                res_soap = default_soap_client.test_live_reforco(p)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "reforco",
                    "modo": "live_soap",
                    "sucesso": res_soap["sucesso"],
                    "empenho": p.get("numero_empenho"),
                    "documento": res_soap.get("documento"),
                    "request_xml": res_soap.get("request_xml"),
                    "response_xml": res_soap.get("response_xml"),
                    "erro": res_soap.get("erro")
                }
            else:
                req = default_renderer.render_reforco(p)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "reforco",
                    "modo": "simulacao_offline",
                    "sucesso": True,
                    "empenho": p.get("numero_empenho", "49746"),
                    "request_xml": req
                }

        elif st == "anulacao":
            if live:
                res_soap = default_soap_client.test_live_anulacao(p)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "anulacao",
                    "modo": "live_soap",
                    "sucesso": res_soap["sucesso"],
                    "empenho": p.get("numero_empenho"),
                    "documento": res_soap.get("documento"),
                    "request_xml": res_soap.get("request_xml"),
                    "response_xml": res_soap.get("response_xml"),
                    "erro": res_soap.get("erro")
                }
            else:
                req = default_renderer.render_anulacao(p)
                res = {
                    "tipo": "etapa_avulsa",
                    "stage": "anulacao",
                    "modo": "simulacao_offline",
                    "sucesso": True,
                    "empenho": p.get("numero_empenho", "49746"),
                    "request_xml": req
                }
        else:
            raise ValueError(f"Etapa desconhecida: '{stage_name}'. Opções: processo, empenho, olp, op, reforco, anulacao.")

        res["data_execucao"] = datetime.now().isoformat()
        res["parametros"] = p
        self.save_run_result(res)
        return res

    def run_chain(self, stages: list = None, params: dict = None, live: bool = False) -> dict:
        """
        Executa uma cadeia completa encadeada de etapas com herança automática de identificadores.
        """
        if stages is None:
            stages = ["processo", "empenho", "olp", "op"]
        if params is None:
            params = {}

        p = dict(params)
        resultado_etapas = {}
        documentos = {}
        sucesso_geral = True
        etapa_falha = None
        erro_msg = None

        for stage in stages:
            st = stage.lower().strip()
            res_st = self.run_stage(st, p, live=live)
            resultado_etapas[st] = res_st

            if not res_st.get("sucesso", False):
                sucesso_geral = False
                etapa_falha = st
                erro_msg = res_st.get("erro")
                break

            doc = res_st.get("documento") or res_st.get("documento_simulado")
            if st in ("processo", "stage1"):
                documentos["processo"] = doc
                p["numero_processo"] = doc
            elif st in ("empenho", "stage2"):
                documentos["empenho"] = doc
                p["numero_empenho"] = doc
            elif st in ("olp", "stage3"):
                documentos["olp"] = doc
                p["numero_olp"] = doc
            elif st in ("op", "stage4"):
                documentos["op"] = doc
                if res_st.get("numero_solicitacao"):
                    documentos["solicitacao_op"] = res_st.get("numero_solicitacao")

        res_final = {
            "tipo": "cadeia_encadeada",
            "modo": "live_soap" if live else "simulacao_offline",
            "sucesso": sucesso_geral,
            "data_execucao": datetime.now().isoformat(),
            "etapas_executadas": stages,
            "documentos": documentos,
            "etapa_falha": etapa_falha,
            "erro": erro_msg,
            "resultados_etapas": resultado_etapas,
            "parametros_finais": p
        }

        self.save_run_result(res_final)
        return res_final


# Instância singleton padrão
default_runner = UniversalRunner()
