# -*- coding: utf-8 -*-
"""
Bateria 6: Testes Automatizados do Universal Test Runner (tests.test_6_universal_runner)
Valida a resolução dinâmica de parâmetros dos 64 cenários, overrides via linha de comando,
execução de etapas/cadeias em modo simulação e persistência de arquivos JSON em output/runs/.
"""

import os
import json
import unittest
from core.config import OUTPUT_RUNS_DIR
from core.scenarios import default_scenarios
from core.runner import default_runner


class TestUniversalRunner(unittest.TestCase):
    """Testes de conformidade do Universal Runner e resolução dinâmica de parâmetros."""

    def test_resolucao_parametros_cenario_sem_retencao(self):
        """Valida derivação de parâmetros para cenário simples (Chamada-01)."""
        p = default_scenarios.resolve_scenario_params("Chamada-01")
        self.assertEqual(p["scenario_id"], "Chamada-01")
        self.assertEqual(p["credor_cpf_cnpj"], "00000000272")
        self.assertFalse(p["exige_regionalizacao"])
        self.assertEqual(p["tipo_conta_a_debitar"], 1)
        self.assertEqual(p["tipo_conta_a_creditar"], 1)
        self.assertFalse(p["ha_retencao"])
        self.assertEqual(p["valor"], "1.00")
        self.assertEqual(p["valor_liquido"], "1.00")
        self.assertEqual(p["valor_retido"], "0.00")

    def test_resolucao_parametros_cenario_com_retencao_dupla(self):
        """Valida derivação de parâmetros para cenário com INSS + ISSQN (Chamada-04)."""
        p = default_scenarios.resolve_scenario_params("Chamada-04")
        self.assertEqual(p["scenario_id"], "Chamada-04")
        self.assertTrue(p["ha_retencao"])
        self.assertEqual(p["valor"], "1.00")
        self.assertEqual(p["valor_retido"], "0.16")
        self.assertEqual(p["valor_liquido"], "0.84")
        self.assertEqual(len(p["retencoes_list_olp"]), 2)
        self.assertEqual(len(p["retencoes_list_op"]), 0)
        # Tipos OLP: 14 e 13
        self.assertEqual(p["retencoes_list_olp"][0]["codigo_tipo_retencao"], "14")
        self.assertEqual(p["retencoes_list_olp"][1]["codigo_tipo_retencao"], "13")

    def test_resolucao_com_overrides_dinamicos(self):
        """Valida que overrides aplicados recalculam os valores fiscobancários."""
        overrides = {
            "valor": "100.00",
            "retencao_inss": "11.00",
            "retencao_issqn": "5.00",
            "credor_cpf_cnpj": "12345678901"
        }
        p = default_scenarios.resolve_scenario_params("Chamada-04", overrides=overrides)
        self.assertEqual(p["valor"], "100.00")
        self.assertEqual(p["credor_cpf_cnpj"], "12345678901")
        self.assertEqual(p["valor_retido"], "16.00")
        self.assertEqual(p["valor_liquido"], "84.00")
        self.assertEqual(len(p["retencoes_list_op"]), 0)

    def test_execucao_simulada_cenario_e_persistencia(self):
        """Valida execução offline de cenário e gravação do log JSON."""
        res = default_runner.run_scenario("Chamada-04", overrides={"valor": "1.00"}, live=False)
        self.assertTrue(res["sucesso"])
        self.assertEqual(res["modo"], "simulacao_offline")
        self.assertIn("stage1_processo", res["etapas"])
        self.assertIn("stage4_op", res["etapas"])
        self.assertIn("<valorTotalAPagarDaOP>0.84</valorTotalAPagarDaOP>", res["etapas"]["stage4_op"]["request_xml"])
        self.assertNotIn("<retencaoList>", res["etapas"]["stage4_op"]["request_xml"])
        self.assertNotIn("<valorTotalRetencoes>", res["etapas"]["stage4_op"]["request_xml"])

        # Valida gravação do arquivo de log
        saved_path = res.get("saved_log_path")
        self.assertIsNotNone(saved_path)
        self.assertTrue(os.path.exists(saved_path))
        with open(saved_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["scenario_id"], "Chamada-04")
            self.assertTrue(data["sucesso"])

    def test_execucao_simulada_etapas_avulsas(self):
        """Valida execução simulada de etapas individuais (reforço, anulação, op)."""
        # Reforço
        res_ref = default_runner.run_stage("reforco", params={"valor_reforco": "50.00", "numero_empenho": "49746"}, live=False)
        self.assertTrue(res_ref["sucesso"])
        self.assertIn("<valorReforco>50.00</valorReforco>", res_ref["request_xml"])

        # Anulação
        res_anul = default_runner.run_stage("anulacao", params={"valor_anulacao": "30.00", "numero_empenho": "49746"}, live=False)
        self.assertTrue(res_anul["sucesso"])
        self.assertIn("<valorAnulacaoEmpenho>30.00</valorAnulacaoEmpenho>", res_anul["request_xml"])

        # OP
        res_op = default_runner.run_stage("op", params={"olp": "49993", "valor": "1.00"}, live=False)
        self.assertTrue(res_op["sucesso"])
        self.assertIn("<anoNumeroDaOlpEEmpenho>2026/49993</anoNumeroDaOlpEEmpenho>", res_op["request_xml"])

    def test_execucao_simulada_cadeia_customizada(self):
        """Valida execução de cadeia customizada encadeada."""
        res_chain = default_runner.run_chain(stages=["processo", "empenho", "olp", "op"], params={"valor": "1.00"}, live=False)
        self.assertTrue(res_chain["sucesso"])
        self.assertEqual(len(res_chain["documentos"]), 4)
        self.assertIn("processo", res_chain["documentos"])
        self.assertIn("empenho", res_chain["documentos"])
        self.assertIn("olp", res_chain["documentos"])
        self.assertIn("op", res_chain["documentos"])


if __name__ == "__main__":
    unittest.main()
