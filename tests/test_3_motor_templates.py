# -*- coding: utf-8 -*-
"""
BATERIA 3: Validação do Motor de Templates Jinja2
Testa a renderização sintática e regras fiscobancárias de todos os 6 templates SOAP.
"""

import unittest
import xml.dom.minidom
from core.renderer import default_renderer


class TestMotorTemplates(unittest.TestCase):

    def _assert_valid_xml(self, xml_string: str, msg: str = ""):
        """Garante que a string é um XML bem-formado."""
        try:
            dom = xml.dom.minidom.parseString(xml_string)
            self.assertIsNotNone(dom, msg)
        except Exception as e:
            self.fail(f"XML mal formatado: {e}\nXML:\n{xml_string}")

    def test_template_stage1_processo(self):
        """Valida renderização e sintaxe da Etapa 1."""
        xml_out = default_renderer.render_stage1({"orgao_executor": "10190", "ua": "1019080124", "uo": "10191"})
        self._assert_valid_xml(xml_out, "Etapa 1 inválida")
        self.assertIn("<anoExercicio>2026</anoExercicio>", xml_out)
        self.assertIn("<codigoOrgao>10190</codigoOrgao>", xml_out)

    def test_template_stage2_empenho(self):
        """Valida renderização e sintaxe da Etapa 2."""
        params = {
            "uo": "10191",
            "orgao_executor": "10190",
            "ua": "1019080124",
            "cpf_ordenador": "00000000191",
            "cpf_operador": "00000000191",
            "justificativa": "Empenho ordinario",
            "credor_cpf_cnpj": "12345678901",
            "credor_classificacao": "BENEFICIÁRIOS DIVERSOS",
            "valor": "250.00"
        }
        xml_out = default_renderer.render_stage2(params, "2026-10190-00001")
        self._assert_valid_xml(xml_out, "Etapa 2 inválida")
        self.assertIn("<numeroProcessoGeral>2026-10190-00001</numeroProcessoGeral>", xml_out)
        self.assertIn("<valorEmpenho>250.00</valorEmpenho>", xml_out)

    def test_template_stage3_olp_com_e_sem_retencao(self):
        """Valida variações de retenção e regionalização na Etapa 3."""
        # Cenário 1: Sem retenção e sem regionalização
        params1 = {
            "uo": "10191", "orgao_executor": "10190", "ua": "1019080124",
            "cpf_ordenador": "00000000191", "cpf_operador": "00000000191",
            "justificativa": "Sem retencao", "credor_cpf_cnpj": "12345678901",
            "credor_classificacao": "BENEFICIÁRIOS DIVERSOS", "valor": "100.00",
            "ha_retencao": False, "exige_regionalizacao": False
        }
        xml1 = default_renderer.render_stage3(params1, "22575")
        self._assert_valid_xml(xml1)
        self.assertNotIn("<retencaoOlpRequestList>", xml1)
        self.assertNotIn("<regionalizacaoDespesaOlpRequestList>", xml1)

        # Cenário 2: Com retenção dupla (INSS + ISSQN) e com regionalização
        params2 = dict(params1)
        params2.update({
            "ha_retencao": True,
            "valor_retido": "16.00",
            "valor_liquido": "84.00",
            "retencoes_list": [
                {"codigo_tipo_retencao": "14", "valor_retencao": "11.00"},
                {"codigo_tipo_retencao": "15", "valor_retencao": "5.00"}
            ],
            "exige_regionalizacao": True,
            "codigo_municipio": "3106200"
        })
        xml2 = default_renderer.render_stage3(params2, "22575")
        self._assert_valid_xml(xml2)
        self.assertIn("<retencaoOlpRequestList>", xml2)
        self.assertIn("<tipoRetencao>14</tipoRetencao>", xml2)
        self.assertIn("<tipoRetencao>15</tipoRetencao>", xml2)
        self.assertIn("<codigoMunicipio>3106200</codigoMunicipio>", xml2)

    def test_template_stage4_op_regras_bancarias(self):
        """Valida regras de Conta Única vs Específica e DV de agência na Etapa 4."""
        # Cenário 1: Conta Única (omitir detalhes da conta de débito) e banco sem DV de agência
        params1 = {
            "uo": "10191", "orgao_executor": "10190", "ua": "1019080124",
            "cpf_ordenador": "00000000191", "cpf_operador": "00000000191",
            "justificativa": "OP Conta Unica", "credor_cpf_cnpj": "12345678901",
            "credor_classificacao": "BENEFICIÁRIOS DIVERSOS", "valor": "100.00",
            "tipo_conta_a_debitar": 1,
            "op_ag_cred": "0001",
            "op_dv_ag_cred": None, # Banco sem DV (ex: Nubank/Inter)
            "tipo_conta_a_creditar": 1,
            "op_conta_cred": "123456",
            "op_dv_conta_cred": "0"
        }
        xml1 = default_renderer.render_stage4(params1, "30001")
        self._assert_valid_xml(xml1)
        self.assertIn("<tipoContaADebitar>1</tipoContaADebitar>", xml1)
        self.assertNotIn("<codigoBancoADebitar>", xml1)
        self.assertNotIn("<dvAgenciaACreditar>", xml1)
        self.assertIn("<dvContaACreditar>0</dvContaACreditar>", xml1)

        # Cenário 2: Conta Específica com DV de agência
        params2 = dict(params1)
        params2.update({
            "tipo_conta_a_debitar": 2,
            "op_cod_banco_deb": "001",
            "op_ag_deb": "1615",
            "op_dv_ag_deb": "2",
            "op_conta_deb": "90004",
            "op_dv_conta_deb": "6",
            "op_dv_ag_cred": "5"
        })
        xml2 = default_renderer.render_stage4(params2, "30001")
        self._assert_valid_xml(xml2)
        self.assertIn("<tipoContaADebitar>2</tipoContaADebitar>", xml2)
        self.assertIn("<codigoBancoADebitar>001</codigoBancoADebitar>", xml2)
        self.assertIn("<dvAgenciaACreditar>5</dvAgenciaACreditar>", xml2)

    def test_templates_manutencao_reforco_e_anulacao(self):
        """Valida templates de Reforço e Anulação."""
        params_ref = {"numero_empenho": "49746", "valor_reforco": "50.00"}
        xml_ref = default_renderer.render_reforco(params_ref)
        self._assert_valid_xml(xml_ref)
        self.assertIn("<numeroEmpenho>49746</numeroEmpenho>", xml_ref)
        self.assertIn("<valorReforco>50.00</valorReforco>", xml_ref)

        # Teste com fallback default
        xml_ref_default = default_renderer.render_reforco({})
        self._assert_valid_xml(xml_ref_default)
        self.assertIn("<numeroEmpenho>49746</numeroEmpenho>", xml_ref_default)
        self.assertIn("<valorReforco>50.00</valorReforco>", xml_ref_default)

        params_anul = {"numero_empenho": "49746", "valor_anulacao": "30.00"}
        xml_anul = default_renderer.render_anulacao(params_anul)
        self._assert_valid_xml(xml_anul)
        self.assertIn("<numeroEmpenho>49746</numeroEmpenho>", xml_anul)
        self.assertIn("<valorAnulacaoEmpenho>30.00</valorAnulacaoEmpenho>", xml_anul)

        # Teste com fallback default
        xml_anul_default = default_renderer.render_anulacao({})
        self._assert_valid_xml(xml_anul_default)
        self.assertIn("<numeroEmpenho>49746</numeroEmpenho>", xml_anul_default)
        self.assertIn("<valorAnulacaoEmpenho>30.00</valorAnulacaoEmpenho>", xml_anul_default)

    def test_template_stage4_op_empenho_1_real_com_inss_e_issqn(self):
        """Valida a OP de R$ 1,00 simplificada (sem retenções na OP, pagando o valor líquido de R$ 0,84)."""
        params = {
            "uo": "10191", "orgao_executor": "10190", "ua": "1019080124",
            "cpf_ordenador": "00000000191", "cpf_operador": "00000000191",
            "justificativa": "PAGAMENTO DE PREMIO NOTA FISCAL MINEIRA COM RETENCAO DUPLA INSS E ISSQN",
            "credor_cpf_cnpj": "00000000272", "credor_classificacao": "BENEFICIÁRIOS DIVERSOS",
            "valor": "1.00", "valor_liquido": "0.84", "valor_retido": "0.16",
            "ha_retencao": True,
            "tipo_conta_a_debitar": 1,
            "tipo_conta_a_creditar": 1, "op_cod_banco_cred": "001", "op_ag_cred": "9012",
            "op_dv_ag_cred": "6", "op_conta_cred": "90006", "op_dv_conta_cred": "3"
        }
        xml_op = default_renderer.render_stage4(params, "42008")
        self._assert_valid_xml(xml_op)
        self.assertIn("<valorTotalAPagarDaOP>0.84</valorTotalAPagarDaOP>", xml_op)
        self.assertNotIn("<valorTotalRetencoes>", xml_op)
        self.assertNotIn("<retencaoList>", xml_op)
        self.assertIn("<valorLiquidoPagamento>0.84</valorLiquidoPagamento>", xml_op)
        self.assertIn("<anoNumeroDaOlpEEmpenho>2026/42008</anoNumeroDaOlpEEmpenho>", xml_op)
        self.assertIn("<valorAPagar>0.84</valorAPagar>", xml_op)
        self.assertIn("<valorTotalAPagar>0.84</valorTotalAPagar>", xml_op)
        self.assertIn("<valorLiquido>0.84</valorLiquido>", xml_op)


if __name__ == "__main__":
    unittest.main()
