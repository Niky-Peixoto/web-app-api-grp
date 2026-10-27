# -*- coding: utf-8 -*-
"""
BATERIA 1: Teste de Regressão e Integridade dos Dados Homologados
Valida se 100% das 64 chamadas e 512 payloads XML da base homologada estão íntegros e preservados.
"""

import unittest
from core.scenarios import default_scenarios


class TestRegressaoDados(unittest.TestCase):

    def setUp(self):
        self.scenarios = default_scenarios.load()

    def test_quantidade_total_chamadas(self):
        """Valida que exatamente 64 chamadas constam na base."""
        self.assertEqual(len(self.scenarios), 64, f"Esperado 64 cenários, encontrado {len(self.scenarios)}")

    def test_integridade_payloads_das_4_etapas(self):
        """Valida se todos os 512 payloads (64 chamadas x 4 etapas x 2 modos req/res) estão preenchidos."""
        stages = ["stage1", "stage2", "stage3", "stage4"]
        
        for scenario in self.scenarios:
            s_id = scenario.get("identificador")
            self.assertIsNotNone(s_id, "Cenário sem identificador")
            
            xml_data = scenario.get("xml_data", {})
            for stg in stages:
                self.assertIn(stg, xml_data, f"Etapa {stg} ausente em {s_id}")
                req = xml_data[stg].get("req", "")
                res = xml_data[stg].get("res", "")
                
                self.assertTrue(len(req) > 50, f"Payload 'req' de {stg} em {s_id} está vazio ou curto")
                self.assertTrue(len(res) > 50, f"Payload 'res' de {stg} em {s_id} está vazio ou curto")
                self.assertIn("<soap", req.lower(), f"Payload 'req' de {stg} em {s_id} não é envelope SOAP")
                self.assertIn("<soap", res.lower(), f"Payload 'res' de {stg} em {s_id} não é envelope SOAP")

    def test_status_homologacao(self):
        """Valida se todos os cenários estão marcados com TESTADO & HOMOLOGADO."""
        for scenario in self.scenarios:
            status = scenario.get("status_homologacao")
            self.assertEqual(status, "TESTADO & HOMOLOGADO", f"Status inválido em {scenario.get('identificador')}: {status}")


if __name__ == "__main__":
    unittest.main()
