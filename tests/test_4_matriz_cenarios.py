# -*- coding: utf-8 -*-
"""
BATERIA 4: Validação da Matriz Combinatória de Cenários
Valida a completude matemática das 64 combinações (5 variáveis) e o mapeamento dos 46 Grupos Mães.
"""

import unittest
from core.scenarios import default_scenarios


class TestMatrizCenarios(unittest.TestCase):

    def setUp(self):
        self.scenarios = default_scenarios.load()

    def test_unicidade_identificadores(self):
        """Valida que todos os IDs (Chamada-01 a Chamada-64) são estritamente únicos."""
        ids = [s["identificador"] for s in self.scenarios]
        self.assertEqual(len(ids), 64)
        self.assertEqual(len(set(ids)), 64)

        for i in range(1, 65):
            expected_id = f"Chamada-{i:02d}"
            self.assertIn(expected_id, ids, f"Identificador {expected_id} ausente na matriz")

    def test_combinacoes_das_5_variaveis(self):
        """Valida se todas as 64 combinações possíveis das 5 variáveis estão presentes."""
        clientes = ["CPF", "CNPJ"]
        regionalizacoes = ["Sem Regionalização", "Com Regionalização"]
        contas_deb = ["1 - Conta Única (Tesouro)", "2 - Conta Específica"]
        contas_cred = ["1 - Conta Corrente", "2 - Poupança"]
        retencoes = ["Sem Retenção", "INSS", "ISSQN", "INSS + ISSQN"]

        combinacoes_encontradas = 0

        for c in clientes:
            for reg in regionalizacoes:
                for c_deb in contas_deb:
                    for c_cred in contas_cred:
                        for ret in retencoes:
                            node = default_scenarios.find_scenario(c, reg, c_deb, c_cred, ret)
                            self.assertIsNotNone(node, f"Combinação não encontrada: {c}, {reg}, {c_deb}, {c_cred}, {ret}")
                            combinacoes_encontradas += 1

        self.assertEqual(combinacoes_encontradas, 64)

    def test_grupos_maes(self):
        """Valida se todos os 46 Grupos Mães estão corretamente associados."""
        grupos = {s.get("grupo_mae") for s in self.scenarios}
        self.assertEqual(len(grupos), 46, f"Esperado 46 grupos mães distintos, encontrado {len(grupos)}")


if __name__ == "__main__":
    unittest.main()
