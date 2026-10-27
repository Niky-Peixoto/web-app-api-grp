# -*- coding: utf-8 -*-
"""
BATERIA 2: Auditoria de Schemas e Dicionário de Tags XML
Valida a integridade do arquivo dic-tags-api.xlsx (138 tags) e audita os templates Jinja2.
"""

import unittest
from core.registry import default_registry
from core.renderer import default_renderer


class TestSchemasEDicionario(unittest.TestCase):

    def setUp(self):
        self.tags = default_registry.load()

    def test_total_tags_excel(self):
        """Valida que exatamente 138 tags estão cadastradas na planilha oficial."""
        self.assertEqual(len(self.tags), 138, f"Esperado 138 tags, encontrado {len(self.tags)}")

    def test_formato_e_delimitadores_das_tags(self):
        """Valida se todas as tags possuem os delimitadores < e > e conceitos/regras preenchidos."""
        nomes_unicos = set()
        for idx, tag in enumerate(self.tags):
            name = tag.get("name", "")
            self.assertTrue(name.startswith("<") and name.endswith(">"), f"Tag #{idx+1} '{name}' não possui delimitadores < e >")
            self.assertNotIn(name, nomes_unicos, f"Tag duplicada: {name}")
            nomes_unicos.add(name)

            conceito = tag.get("conceito", "")
            regra = tag.get("regra", "")
            self.assertTrue(len(conceito) >= 1, f"Tag {name} com conceito vazio")
            self.assertTrue(len(regra) >= 5, f"Tag {name} com regra WSDL vazia ou muito curta")

    def test_auditoria_cruzada_templates_vs_dicionario(self):
        """Valida se todas as tags XML geradas pelos templates Jinja2 constam no Dicionário."""
        params_mock = {
            "num_requisicao": "1019080124202600000000000000000000000001",
            "ano_exercicio": "2026",
            "orgao_executor": "10190",
            "uo": "10191",
            "ua": "1019080124",
            "cpf_ordenador": "00000000191",
            "cpf_operador": "00000000191",
            "justificativa": "Teste de auditoria de tags",
            "credor_cpf_cnpj": "00000000191",
            "credor_classificacao": "BENEFICIÁRIOS DIVERSOS",
            "valor": "100.00",
            "valor_liquido": "89.00",
            "valor_retido": "11.00",
            "ha_retencao": True,
            "retencoes_list": [{
                "codigo_tipo_retencao": "14",
                "valor_retencao": "11.00",
                "credor_retencao": "00000000191",
                "mes_competencia": "8",
                "ano_competencia": "2026"
            }],
            "exige_regionalizacao": True,
            "tipo_conta_a_debitar": 2,
            "op_cod_banco_deb": "001",
            "op_ag_deb": "1615",
            "op_dv_ag_deb": "2",
            "op_conta_deb": "90004",
            "op_dv_conta_deb": "6",
            "tipo_conta_a_creditar": 1,
            "op_cod_banco_cred": "001",
            "op_ag_cred": "1615",
            "op_dv_ag_cred": "2",
            "op_conta_cred": "90004",
            "op_dv_conta_cred": "0"
        }

        # Renderiza todos os 6 templates
        xml1 = default_renderer.render_stage1(params_mock)
        xml2 = default_renderer.render_stage2(params_mock, "2026-10190-00001")
        xml3 = default_renderer.render_stage3(params_mock, "22575")
        xml4 = default_renderer.render_stage4(params_mock, "30001")
        xml_ref = default_renderer.render_reforco(params_mock)
        xml_anul = default_renderer.render_anulacao(params_mock)

        todos_xmls = f"{xml1}\n{xml2}\n{xml3}\n{xml4}\n{xml_ref}\n{xml_anul}"
        resultado_auditoria = default_registry.audit_xml(todos_xmls)

        # Tags de suporte/wrapper permitidas caso existam
        nao_registradas = set(resultado_auditoria["nao_registradas"])
        self.assertEqual(len(nao_registradas), 0, f"Tags nos templates Jinja2 não cadastradas na planilha: {nao_registradas}")


if __name__ == "__main__":
    unittest.main()
